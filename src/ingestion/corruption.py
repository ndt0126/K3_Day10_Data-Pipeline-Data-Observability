from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import random

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import _embedding_text


_NOISE_PHRASES = (
    "[REDACTED]",
    "lorem ipsum dolor sit amet",
    "??? corrupted payload ???",
    " ​ random tokens xyz123 ​",
)
_TRUNCATION_RATIO = 0.5
_DROP_LATEST_FRACTION = 0.2
_DUPLICATE_FRACTION = 0.15
_STALE_SHIFT_DAYS = 365
_RANDOM_SEED = 20251104


def _rebuild_embedding_text(row: pd.Series) -> str:
    """Rebuild text_for_embedding using the cleaning contract."""
    return _embedding_text(
        title=str(row.get("title", "")),
        summary=str(row.get("summary", "")),
        authors_joined=str(row.get("authors_joined", "")),
        categories_joined=str(row.get("categories_joined", "")),
        published=str(row.get("published", "")),
    )


def _shift_published(value: object, days: int) -> str:
    """Shift an ISO date string back by ``days`` days; empty stays empty."""
    if not isinstance(value, str) or not value:
        return ""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    shifted = parsed - timedelta(days=days)
    return shifted.date().isoformat()


def _drop_latest_records(
    df: pd.DataFrame,
    fraction: float,
    rng: random.Random,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Drop the most recently published fraction of rows.

    The RNG argument is accepted for signature symmetry with the other
    scenario helpers but unused here: this scenario uses deterministic
    ordering on ``published`` so the corruption stays stable across reruns.
    The ``del`` statement below is a deliberate marker to silence
    unused-argument diagnostics.
    """
    del rng
    if df.empty or fraction <= 0:
        return df, {"requested": 0, "dropped": 0}
    n_drop = max(1, int(round(len(df) * fraction)))
    sorted_df = df.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
    keep = sorted_df.iloc[n_drop:]
    scenario = {"requested": n_drop, "dropped": int(len(df) - len(keep))}
    return keep.reset_index(drop=True), scenario


def _blank_summaries(df: pd.DataFrame, fraction: float, rng: random.Random) -> tuple[pd.DataFrame, dict[str, int]]:
    """Blank a fraction of summary cells so downstream embedding loses content."""
    if df.empty or fraction <= 0:
        return df, {"requested": 0, "blanked": 0}
    indices = list(df.index)
    n = max(1, int(round(len(indices) * fraction)))
    targets = rng.sample(indices, k=min(n, len(indices)))
    df = df.copy()
    df.loc[targets, "summary"] = ""
    df.loc[targets, "summary_chars"] = 0
    return df, {"requested": n, "blanked": len(targets)}


def _inject_summary_noise(df: pd.DataFrame, fraction: float, rng: random.Random) -> tuple[pd.DataFrame, dict[str, int]]:
    """Append noise phrases into a fraction of summaries."""
    if df.empty or fraction <= 0:
        return df, {"requested": 0, "noised": 0}
    indices = list(df.index)
    n = max(1, int(round(len(indices) * fraction)))
    targets = rng.sample(indices, k=min(n, len(indices)))
    df = df.copy()
    for idx in targets:
        original = df.at[idx, "summary"] if isinstance(df.at[idx, "summary"], str) else ""
        if not original:
            original = ""
        noise = rng.choice(_NOISE_PHRASES)
        df.at[idx, "summary"] = f"{original} {noise}".strip()
        df.at[idx, "summary_chars"] = len(df.at[idx, "summary"])
    return df, {"requested": n, "noised": len(targets)}


def _truncate_titles(df: pd.DataFrame, fraction: float, rng: random.Random) -> tuple[pd.DataFrame, dict[str, int]]:
    """Truncate a fraction of titles to ``_TRUNCATION_RATIO`` of their length."""
    if df.empty or fraction <= 0:
        return df, {"requested": 0, "truncated": 0}
    indices = list(df.index)
    n = max(1, int(round(len(indices) * fraction)))
    targets = rng.sample(indices, k=min(n, len(indices)))
    df = df.copy()
    for idx in targets:
        title = df.at[idx, "title"]
        if not isinstance(title, str) or not title:
            continue
        keep = max(1, int(len(title) * _TRUNCATION_RATIO))
        df.at[idx, "title"] = title[:keep].rstrip() + "…"
    return df, {"requested": n, "truncated": len(targets)}


def _stale_published_dates(df: pd.DataFrame, fraction: float, rng: random.Random) -> tuple[pd.DataFrame, dict[str, int]]:
    """Push a fraction of rows' ``published`` and ``updated`` columns back one year."""
    if df.empty or fraction <= 0:
        return df, {"requested": 0, "stale": 0}
    indices = list(df.index)
    n = max(1, int(round(len(indices) * fraction)))
    targets = rng.sample(indices, k=min(n, len(indices)))
    df = df.copy()
    for idx in targets:
        df.at[idx, "published"] = _shift_published(df.at[idx, "published"], _STALE_SHIFT_DAYS)
        df.at[idx, "updated"] = _shift_published(df.at[idx, "updated"], _STALE_SHIFT_DAYS)
    return df, {"requested": n, "stale": len(targets)}


def _duplicate_rows(df: pd.DataFrame, fraction: float, rng: random.Random) -> tuple[pd.DataFrame, dict[str, int]]:
    """Duplicate a fraction of rows so retrieval hits the same record twice."""
    if df.empty or fraction <= 0:
        return df, {"requested": 0, "duplicated": 0}
    n = max(1, int(round(len(df) * fraction)))
    sample = df.sample(n=n, random_state=rng.randint(0, 2**31 - 1))
    return pd.concat([df, sample], ignore_index=True), {"requested": n, "duplicated": int(len(sample))}


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply a fixed sequence of corruption scenarios to the clean dataframe.

    Each scenario mutates a deterministic fraction of rows using a seeded RNG so
    reruns produce identical corruption logs (helpful for debugging and for
    matching the corruption report).  ``text_for_embedding`` is rebuilt after
    every text mutation so the embedding index reflects the corrupted content.
    A JSON log describing the scenarios is written to ``output_log_path``.
    """
    if df.empty:
        log = {
            "schema_version": 1,
            "input_rows": 0,
            "output_rows": 0,
            "scenarios": [],
            "note": "Input dataframe was empty; no corruption applied.",
        }
        write_json(Path(output_log_path), log)
        return df.copy()

    rng = random.Random(_RANDOM_SEED)
    start_rows = len(df)
    log: dict[str, object] = {
        "schema_version": 1,
        "input_rows": start_rows,
        "output_rows": start_rows,
        "scenarios": [],
    }

    # 1. Drop the most recently published fraction so recall drops immediately.
    df, scenario = _drop_latest_records(df, _DROP_LATEST_FRACTION, rng)
    log["scenarios"].append({"name": "drop_latest_records", **scenario})
    log["output_rows"] = len(df)

    # 2. Blank summary text to weaken embeddings.
    df, scenario = _blank_summaries(df, 0.25, rng)
    log["scenarios"].append({"name": "blank_summaries", **scenario})

    # 3. Inject noise phrases into surviving summaries.
    df, scenario = _inject_summary_noise(df, 0.20, rng)
    log["scenarios"].append({"name": "inject_summary_noise", **scenario})

    # 4. Truncate titles to break exact title lookups.
    df, scenario = _truncate_titles(df, 0.25, rng)
    log["scenarios"].append({"name": "truncate_titles", **scenario})

    # 5. Stale publication dates to trip the freshness monitor.
    df, scenario = _stale_published_dates(df, 0.20, rng)
    log["scenarios"].append({"name": "stale_published_dates", **scenario})

    # 6. Duplicate rows so retrieval returns repeated hits.
    df, scenario = _duplicate_rows(df, _DUPLICATE_FRACTION, rng)
    log["scenarios"].append({"name": "duplicate_rows", **scenario})

    # Recompute age_days to match the new published dates, then rebuild text.
    if "age_days" in df.columns:
        parsed = pd.to_datetime(df["published"], errors="coerce", utc=True)
        reference = pd.Timestamp.utcnow().normalize()
        df = df.copy()
        df["age_days"] = parsed.apply(
            lambda value: max(0, (reference - value.normalize()).days) if pd.notna(value) else 0
        ).astype(int)
    df = df.copy()
    df["text_for_embedding"] = df.apply(_rebuild_embedding_text, axis=1)
    if "summary_chars" in df.columns:
        df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()

    log["output_rows"] = len(df)
    write_json(Path(output_log_path), log)
    return df.reset_index(drop=True)
