from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import html
import json
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"
_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_RETRIES = 3
_REQUEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _normalise_doi(value: object) -> str:
    """Return a canonical DOI identifier, or an empty string when unavailable."""
    if not isinstance(value, str):
        return ""
    doi = html.unescape(value).strip()
    doi = re.sub(r"^doi\s*:\s*", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.rstrip(".,;)").strip().lower() if doi.lower().startswith("10.") else ""


def _clean_jats_abstract(abstract_raw: object) -> str:
    if not isinstance(abstract_raw, str) or not abstract_raw:
        return ""
    text = re.sub(r"<[^>]*>", " ", abstract_raw)
    return " ".join(html.unescape(text).split())


def _first_text(value: object) -> str:
    if isinstance(value, list):
        value = next((item for item in value if isinstance(item, str) and item.strip()), "")
    return " ".join(value.split()) if isinstance(value, str) else ""


def _extract_iso_date(item: dict[str, Any], *date_keys: str) -> str:
    """Extract the first valid Crossref date-parts value as YYYY-MM-DD."""
    for key in date_keys:
        date_info = item.get(key)
        date_parts = date_info.get("date-parts") if isinstance(date_info, dict) else None
        if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
            continue
        parts = date_parts[0]
        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (IndexError, TypeError, ValueError):
            continue
    return ""


def _extract_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = " ".join(
            part.strip()
            for part in (author.get("given"), author.get("family"))
            if isinstance(part, str) and part.strip()
        )
        if name:
            authors.append(name)
    return authors


def _extract_pdf_url(links: object) -> str:
    if not isinstance(links, list):
        return ""
    for link in links:
        if not isinstance(link, dict):
            continue
        url = link.get("URL")
        content_type = str(link.get("content-type", "")).lower()
        if isinstance(url, str) and url and (
            "pdf" in content_type or url.lower().split("?", 1)[0].endswith(".pdf")
        ):
            return url
    return ""


def _extract_abs_url(item: dict[str, Any], doi_url: str) -> str:
    """Prefer Crossref landing URL while retaining DOI fallback."""
    url = item.get("URL")
    return url.strip() if isinstance(url, str) and url.strip() else doi_url


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref /works response into valid, normalized paper records."""
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        paper_id = _normalise_doi(item.get("DOI"))
        title = _first_text(item.get("title"))
        if not paper_id or not title:
            continue

        subjects = item.get("subject", [])
        if not isinstance(subjects, list):
            subjects = [subjects]
        categories = [subject.strip() for subject in subjects if isinstance(subject, str) and subject.strip()]
        published = _extract_iso_date(
            item, "published-print", "published-online", "published", "issued", "created"
        )
        updated = _extract_iso_date(item, "updated", "deposited", "indexed", "created") or published
        doi_url = f"https://doi.org/{paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=_clean_jats_abstract(item.get("abstract")),
                authors=_extract_authors(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "General",
                published=published,
                updated=updated,
                abs_url=_extract_abs_url(item, doi_url),
                pdf_url=_extract_pdf_url(item.get("link")),
                comment=_first_text(item.get("container-title")),
            )
        )
    return records


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, preserving both the API response and parsed snapshot."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": "DataPipelineObservabilityLab/1.0 (mailto:lab@example.com)"}
    response: requests.Response | None = None
    last_error: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            candidate = requests.get(
                CROSSREF_API_URL, params=params, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS
            )
            if candidate.status_code == 200:
                response = candidate
                break
            if candidate.status_code not in _RETRYABLE_STATUS_CODES:
                candidate.raise_for_status()
            last_error = RuntimeError(f"Crossref returned HTTP {candidate.status_code}")
        except requests.RequestException as error:
            last_error = error

        if attempt < _MAX_RETRIES - 1:
            time.sleep(2**attempt)

    if response is None:
        raise RuntimeError("Failed to fetch Crossref records after retries") from last_error

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Crossref returned an invalid JSON response") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Crossref returned a JSON payload that is not an object")

    _write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    _write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a parsed raw-record snapshot into PaperRecord instances."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Raw records snapshot must contain a JSON list: {path}")
    try:
        return [PaperRecord(**item) for item in data if isinstance(item, dict)]
    except TypeError as error:
        raise ValueError(f"Raw records snapshot has an invalid record: {path}") from error
