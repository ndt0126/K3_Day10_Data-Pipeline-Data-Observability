from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_DATA_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


def _clean_text(value: object) -> str:
    """Normalize a scalar text value without turning null-like values into text."""
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _clean_text_list(values: object) -> list[str]:
    """Normalize a list and remove repeated values while preserving its order."""
    if not isinstance(values, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _parse_utc_date(value: object) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else pd.Timestamp(parsed)


def _as_utc_timestamp(value: datetime) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(UTC)
    return timestamp.tz_convert(UTC)


def _embedding_text(
    title: str,
    summary: str,
    authors_joined: str,
    categories_joined: str,
    published: str,
) -> str:
    """Create one consistent document body for embedding and later inspection."""
    return "\n".join(
        [
            f"Title: {title}",
            f"Authors: {authors_joined}",
            f"Categories: {categories_joined}",
            f"Published: {published}",
            f"Summary: {summary}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Return a deterministic, index-ready dataframe from raw Crossref records.

    A record is retained only when it has a stable ID, a title, a non-empty
    abstract and a valid publication date.  The resulting dataframe is the
    data contract shared with indexing, evaluation and observability.
    """
    run_timestamp = _as_utc_timestamp(run_date).normalize()
    rows: list[dict[str, Any]] = []
    rejected = {"missing_required_text": 0, "invalid_published": 0}

    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        if not paper_id or not title or not summary:
            rejected["missing_required_text"] += 1
            continue

        published_at = _parse_utc_date(record.published)
        if published_at is None:
            rejected["invalid_published"] += 1
            continue

        updated_at = _parse_utc_date(record.updated) or published_at
        authors = _clean_text_list(record.authors)
        categories = _clean_text_list(record.categories)
        authors_joined = compact_join(authors)
        primary_category = _clean_text(record.primary_category) or (
            categories[0] if categories else "General"
        )
        # Crossref does not populate ``subject`` for many valid works.  Keep a
        # truthful, explicit fallback instead of emitting an unusable blank
        # category into the downstream data contract.
        categories_joined = compact_join(categories) or primary_category
        published = published_at.date().isoformat()
        age_days = max(0, (run_timestamp - published_at.normalize()).days)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated_at.date().isoformat(),
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": _embedding_text(
                    title, summary, authors_joined, categories_joined, published
                ),
            }
        )

    cleaned = pd.DataFrame(rows, columns=CLEAN_DATA_COLUMNS)
    before_deduplication = len(cleaned)
    if not cleaned.empty:
        # Prefer the most recently updated and most informative duplicate.
        cleaned = cleaned.sort_values(
            ["paper_id", "updated", "summary_chars"],
            ascending=[True, False, False],
            kind="stable",
        )
        cleaned = cleaned.drop_duplicates(subset="paper_id", keep="first")
        cleaned = cleaned.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
        cleaned = cleaned.reset_index(drop=True)

    cleaned.attrs["cleaning_summary"] = {
        "input_records": len(records),
        "output_records": len(cleaned),
        "dropped_missing_required_text": rejected["missing_required_text"],
        "dropped_invalid_published": rejected["invalid_published"],
        "dropped_duplicate_paper_id": before_deduplication - len(cleaned),
    }
    return cleaned
