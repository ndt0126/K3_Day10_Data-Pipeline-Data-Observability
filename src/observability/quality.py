from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


_MIN_SUMMARY_CHARS = 40
_MIN_ROW_COUNT = 4


def _safe_published(series: pd.Series) -> pd.Series:
    """Parse ``published`` to UTC timestamps; coerce failures to ``NaT``."""
    return pd.to_datetime(series, errors="coerce", utc=True)


def _check_row_count(df: pd.DataFrame) -> dict[str, Any]:
    total = int(len(df))
    ok = total >= _MIN_ROW_COUNT
    return {
        "name": "row_count",
        "status": "PASS" if ok else "FAIL",
        "observed": total,
        "threshold": _MIN_ROW_COUNT,
        "details": f"Found {total} rows; minimum {_MIN_ROW_COUNT} required.",
    }


def _check_paper_id_not_null(df: pd.DataFrame) -> dict[str, Any]:
    if "paper_id" not in df.columns:
        return {"name": "paper_id_not_null", "status": "FAIL", "observed": 0, "details": "Column 'paper_id' missing."}
    nulls = int(df["paper_id"].isna().sum())
    empty = int((df["paper_id"].astype(str).str.strip() == "").sum())
    bad = nulls + empty
    return {
        "name": "paper_id_not_null",
        "status": "PASS" if bad == 0 else "FAIL",
        "observed": bad,
        "details": f"{bad} rows have a missing or empty paper_id ({nulls} null, {empty} blank).",
    }


def _check_paper_id_unique(df: pd.DataFrame) -> dict[str, Any]:
    if "paper_id" not in df.columns:
        return {"name": "paper_id_unique", "status": "FAIL", "observed": 0, "details": "Column 'paper_id' missing."}
    non_null = df["paper_id"].dropna().astype(str)
    duplicates = int(non_null.duplicated().sum())
    return {
        "name": "paper_id_unique",
        "status": "PASS" if duplicates == 0 else "FAIL",
        "observed": duplicates,
        "details": f"{duplicates} duplicate paper_id values found.",
    }


def _check_title_not_null(df: pd.DataFrame) -> dict[str, Any]:
    if "title" not in df.columns:
        return {"name": "title_not_null", "status": "FAIL", "observed": 0, "details": "Column 'title' missing."}
    blanks = int(df["title"].astype(str).str.strip().eq("").sum())
    return {
        "name": "title_not_null",
        "status": "PASS" if blanks == 0 else "FAIL",
        "observed": blanks,
        "details": f"{blanks} blank titles.",
    }


def _check_summary_length(df: pd.DataFrame) -> dict[str, Any]:
    if "summary" not in df.columns:
        return {"name": "summary_length", "status": "FAIL", "observed": 0, "details": "Column 'summary' missing."}
    lengths = df["summary"].fillna("").astype(str).str.len()
    too_short = int((lengths < _MIN_SUMMARY_CHARS).sum())
    return {
        "name": "summary_length",
        "status": "PASS" if too_short == 0 else "FAIL",
        "observed": too_short,
        "threshold": _MIN_SUMMARY_CHARS,
        "details": f"{too_short} summaries are shorter than {_MIN_SUMMARY_CHARS} characters.",
    }


def _check_freshness(df: pd.DataFrame, threshold_days: int) -> dict[str, Any]:
    if "age_days" not in df.columns:
        return {
            "name": "freshness",
            "status": "FAIL",
            "observed": 0,
            "threshold": threshold_days,
            "details": "Column 'age_days' missing.",
        }
    age = pd.to_numeric(df["age_days"], errors="coerce")
    stale = int((age > threshold_days).sum())
    return {
        "name": "freshness",
        "status": "PASS" if stale == 0 else "FAIL",
        "observed": stale,
        "threshold": threshold_days,
        "details": f"{stale} rows exceed the {threshold_days}-day freshness threshold.",
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the full data quality check battery and persist the report."""
    threshold = settings.freshness_threshold_days
    checks = [
        _check_row_count(df),
        _check_paper_id_not_null(df),
        _check_paper_id_unique(df),
        _check_title_not_null(df),
        _check_summary_length(df),
        _check_freshness(df, threshold),
    ]
    passed = sum(1 for check in checks if check["status"] == "PASS")
    failed = len(checks) - passed
    summary = {
        "schema_version": 1,
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": int(len(df)),
        "passed": passed,
        "failed": failed,
        "success_rate": passed / len(checks) if checks else 0.0,
        "checks": checks,
    }

    gx_dir: Path = settings.paths.gx_dir
    gx_dir.mkdir(parents=True, exist_ok=True)
    output_path = gx_dir / f"{report_name}.json"
    write_json(output_path, summary)
    return summary


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise freshness signals and write them to ``report_path``."""
    if df.empty:
        summary = {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_rows": 0,
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
            "details": "Empty dataframe; freshness cannot be evaluated.",
        }
        write_json(Path(report_path), summary)
        return summary

    published = _safe_published(df["published"]) if "published" in df.columns else pd.to_datetime([], utc=True)
    valid = published.dropna()
    latest = valid.max().date().isoformat() if not valid.empty else None
    oldest = valid.min().date().isoformat() if not valid.empty else None

    threshold = settings.freshness_threshold_days
    age = pd.to_numeric(df.get("age_days", pd.Series([], dtype="float64")), errors="coerce")
    stale_rows = int((age > threshold).sum())
    is_fresh = bool(stale_rows == 0 and latest is not None)

    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": int(len(df)),
        "latest_published": latest,
        "oldest_published": oldest,
        "stale_rows": stale_rows,
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
        "details": (
            f"{stale_rows} rows older than {threshold} days; latest publication is {latest}."
        ),
    }
    write_json(Path(report_path), summary)
    return summary
