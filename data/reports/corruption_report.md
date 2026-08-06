# Corruption Report — Baseline vs Corrupted vs Repaired

_Auto-generated. All numbers come from the artifacts under `data/`._

## 1. Metric comparison

| Metric | Baseline | Corrupted | Repaired | Δ repaired vs baseline |
| --- | --- | --- | --- | --- |
| samples | 16 | 16 | 16 | — |
| retrieval_hit_rate | 100.0% | 50.0% | 100.0% | 🟢 +0.000 |
| mean_token_f1 | 1.000 | 0.438 | 1.000 | 🟢 +0.000 |
| judge_accuracy | 100.0% | 43.8% | 100.0% | 🟢 +0.000 |
| mean_judge_score | 5.000 | 3.062 | 5.000 | 🟢 +0.000 |

## 2. Data quality

### Corrupted

- Pass rate: **50.0%**
- Passed: **3**, failed: **3**

| Check | Status | Observed / Details |
| --- | --- | --- |
| row_count | ✅ | Found 22 rows; minimum 4 required. |
| paper_id_not_null | ✅ | 0 rows have a missing or empty paper_id (0 null, 0 blank). |
| paper_id_unique | ❌ | 3 duplicate paper_id values found. |
| title_not_null | ✅ | 0 blank titles. |
| summary_length | ❌ | 6 summaries are shorter than 40 characters. |
| freshness | ❌ | 6 rows exceed the 180-day freshness threshold. |

### Repaired

- Pass rate: **100.0%**
- Passed: **6**, failed: **0**

| Check | Status | Observed / Details |
| --- | --- | --- |
| row_count | ✅ | Found 24 rows; minimum 4 required. |
| paper_id_not_null | ✅ | 0 rows have a missing or empty paper_id (0 null, 0 blank). |
| paper_id_unique | ✅ | 0 duplicate paper_id values found. |
| title_not_null | ✅ | 0 blank titles. |
| summary_length | ✅ | 0 summaries are shorter than 40 characters. |
| freshness | ✅ | 0 rows exceed the 180-day freshness threshold. |

## 3. Freshness

| Stage | Total | Latest | Oldest | Stale | Is fresh |
| --- | --- | --- | --- | --- | --- |
| Corrupted | 22 | 2026-07-02 | 2025-02-26 | 6 | False |
| Repaired | 24 | 2026-08-01 | 2026-02-12 | 0 | True |

## 4. Interpretation

- **Corruption should drag retrieval and judge scores below baseline.** Quality and freshness checks should also flip to `❌`.
- **Repair should bring metrics back close to baseline.**
- Use the deltas above to size the impact of data quality on the RAG agent.
