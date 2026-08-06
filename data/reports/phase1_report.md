# Phase 1 — Baseline Data Pipeline Report

_Auto-generated. Numbers come from the artifacts in `data/`._

## 1. Source

- Provider: Crossref REST API
- Query: `n/a`
- Filter: `n/a`
- Requested rows: `n/a`
- Fetched records: **n/a**
- Cleaned records: **n/a**

## 2. RAG evaluation

| Metric | Value |
| --- | --- |
| samples | 16 |
| retrieval_hit_rate | 100.0% |
| mean_token_f1 | 1.000 |
| judge_accuracy | 100.0% |
| mean_judge_score | 5.000 |

## 3. Data quality

- Rows checked: **24**
- Pass rate: **100.0%** (6/6 checks passed)

| Check | Status | Observed / Details |
| --- | --- | --- |
| row_count | ✅ | Found 24 rows; minimum 4 required. |
| paper_id_not_null | ✅ | 0 rows have a missing or empty paper_id (0 null, 0 blank). |
| paper_id_unique | ✅ | 0 duplicate paper_id values found. |
| title_not_null | ✅ | 0 blank titles. |
| summary_length | ✅ | 0 summaries are shorter than 40 characters. |
| freshness | ✅ | 0 rows exceed the 180-day freshness threshold. |

## 4. Freshness

- Total rows: **24**
- Latest published: **2026-08-01**
- Oldest published: **2026-02-12**
- Stale rows (> 180 days): **0**
- Is fresh: **✅**

> 0 rows older than 180 days; latest publication is 2026-08-01.
