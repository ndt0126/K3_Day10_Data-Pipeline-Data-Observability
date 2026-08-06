from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


_METRIC_KEYS = (
    "samples",
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)


def _format_float(value: Any, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return "n/a"


def _format_rate(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value) * 100:.1f}%"
    return "n/a"


def _format_status(value: Any) -> str:
    return "✅" if value == "PASS" else "❌" if value == "FAIL" else str(value)


def _format_check_table(checks: list[dict[str, Any]] | None) -> str:
    if not checks:
        return "_(no checks recorded)_"
    rows = ["| Check | Status | Observed / Details |", "| --- | --- | --- |"]
    for check in checks:
        rows.append(
            f"| {check.get('name', '?')} "
            f"| {_format_status(check.get('status'))} "
            f"| {check.get('details', '')} |"
        )
    return "\n".join(rows)


def _format_metric_table(metrics: dict[str, Any] | None) -> str:
    if not metrics:
        return "_(no metrics available)_"
    rows = ["| Metric | Value |", "| --- | --- |"]
    for key in _METRIC_KEYS:
        if key not in metrics:
            continue
        value = metrics[key]
        if key == "samples":
            rows.append(f"| samples | {value} |")
        elif key in {"retrieval_hit_rate", "judge_accuracy"}:
            rows.append(f"| {key} | {_format_rate(value)} |")
        else:
            rows.append(f"| {key} | {_format_float(value)} |")
    ragas = metrics.get("ragas")
    if isinstance(ragas, dict) and ragas and not ragas.get("skipped"):
        rows.append("| ragas (subset) | _see artifact_ |")
    return "\n".join(rows)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline (Phase 1) markdown report to ``report_path``."""
    query = source_summary.get("source_query", "n/a")
    filter_ = source_summary.get("source_filter", "n/a")
    max_results = source_summary.get("max_results", "n/a")
    fetched = source_summary.get("fetched_records", "n/a")
    kept = source_summary.get("cleaned_records", "n/a")

    lines: list[str] = [
        "# Phase 1 — Baseline Data Pipeline Report",
        "",
        "_Auto-generated. Numbers come from the artifacts in `data/`._",
        "",
        "## 1. Source",
        "",
        f"- Provider: {source_summary.get('source_api', 'Crossref REST API')}",
        f"- Query: `{query}`",
        f"- Filter: `{filter_}`",
        f"- Requested rows: `{max_results}`",
        f"- Fetched records: **{fetched}**",
        f"- Cleaned records: **{kept}**",
        "",
        "## 2. RAG evaluation",
        "",
        _format_metric_table(metrics),
        "",
        "## 3. Data quality",
        "",
        f"- Rows checked: **{quality.get('row_count', 'n/a')}**",
        f"- Pass rate: **{_format_rate(quality.get('success_rate'))}** "
        f"({quality.get('passed', 0)}/{(quality.get('passed', 0) + quality.get('failed', 0))} checks passed)",
        "",
        _format_check_table(quality.get("checks")),
        "",
        "## 4. Freshness",
        "",
        f"- Total rows: **{freshness.get('total_rows', 'n/a')}**",
        f"- Latest published: **{freshness.get('latest_published', 'n/a')}**",
        f"- Oldest published: **{freshness.get('oldest_published', 'n/a')}**",
        f"- Stale rows (> {freshness.get('freshness_threshold_days', 'n/a')} days): "
        f"**{freshness.get('stale_rows', 'n/a')}**",
        f"- Is fresh: **{'✅' if freshness.get('is_fresh') else '❌'}**",
        "",
        f"> {freshness.get('details', '')}",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


def _delta(baseline: Any, current: Any, *, multiplier: float = 1.0, higher_is_better: bool = True) -> str:
    if not isinstance(baseline, (int, float)) or not isinstance(current, (int, float)):
        return "n/a"
    delta = (current - baseline) * multiplier
    arrow = "🟢" if (delta >= 0) == higher_is_better else "🔴"
    return f"{arrow} {delta:+.3f}"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a comparison markdown report spanning baseline, corrupted and repaired."""
    rows: list[str] = [
        "| Metric | Baseline | Corrupted | Repaired | Δ repaired vs baseline |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key in _METRIC_KEYS:
        base = baseline_metrics.get(key)
        corr = corrupted_metrics.get(key)
        rep = repaired_metrics.get(key)
        if key == "samples":
            rows.append(f"| samples | {base} | {corr} | {rep} | — |")
        elif key in {"retrieval_hit_rate", "judge_accuracy"}:
            rows.append(
                f"| {key} "
                f"| {_format_rate(base)} | {_format_rate(corr)} | {_format_rate(rep)} "
                f"| {_delta(base, rep, multiplier=100, higher_is_better=True)} |"
            )
        else:
            rows.append(
                f"| {key} "
                f"| {_format_float(base)} | {_format_float(corr)} | {_format_float(rep)} "
                f"| {_delta(base, rep)} |"
            )

    lines: list[str] = [
        "# Corruption Report — Baseline vs Corrupted vs Repaired",
        "",
        "_Auto-generated. All numbers come from the artifacts under `data/`._",
        "",
        "## 1. Metric comparison",
        "",
        "\n".join(rows),
        "",
        "## 2. Data quality",
        "",
        "### Corrupted",
        "",
        f"- Pass rate: **{_format_rate(corrupted_quality.get('success_rate'))}**",
        f"- Passed: **{corrupted_quality.get('passed', 0)}**, "
        f"failed: **{corrupted_quality.get('failed', 0)}**",
        "",
        _format_check_table(corrupted_quality.get("checks")),
        "",
        "### Repaired",
        "",
        f"- Pass rate: **{_format_rate(repaired_quality.get('success_rate'))}**",
        f"- Passed: **{repaired_quality.get('passed', 0)}**, "
        f"failed: **{repaired_quality.get('failed', 0)}**",
        "",
        _format_check_table(repaired_quality.get("checks")),
        "",
        "## 3. Freshness",
        "",
        "| Stage | Total | Latest | Oldest | Stale | Is fresh |",
        "| --- | --- | --- | --- | --- | --- |",
        "| Corrupted "
        f"| {corrupted_freshness.get('total_rows', 'n/a')} "
        f"| {corrupted_freshness.get('latest_published', 'n/a')} "
        f"| {corrupted_freshness.get('oldest_published', 'n/a')} "
        f"| {corrupted_freshness.get('stale_rows', 'n/a')} "
        f"| {_format_status(corrupted_freshness.get('is_fresh'))} |",
        "| Repaired "
        f"| {repaired_freshness.get('total_rows', 'n/a')} "
        f"| {repaired_freshness.get('latest_published', 'n/a')} "
        f"| {repaired_freshness.get('oldest_published', 'n/a')} "
        f"| {repaired_freshness.get('stale_rows', 'n/a')} "
        f"| {_format_status(repaired_freshness.get('is_fresh'))} |",
        "",
        "## 4. Interpretation",
        "",
        "- **Corruption should drag retrieval and judge scores below baseline.** "
        "Quality and freshness checks should also flip to `❌`.",
        "- **Repair should bring metrics back close to baseline.**",
        "- Use the deltas above to size the impact of data quality on the RAG agent.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))
