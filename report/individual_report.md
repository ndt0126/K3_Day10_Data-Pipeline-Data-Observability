# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đinh Quang Minh |
| MSSV | 2A202601347 |
| Khóa/Lớp | K3 |
| Tên nhóm | B4 |
| Vai trò chính | Thành viên 4 — Observability, Corruption & Reporting Owner |
| Repository | https://github.com/ndt0126/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module / deliverable | File / hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data corruption | `src/ingestion/corruption.py::corrupt_clean_dataframe` | Clean DataFrame từ TV2 + `output_log_path` | DataFrame đã corrupt + `data/results/corruption_log.json` | Hoàn thành |
| Data quality checks | `src/observability/quality.py::run_data_quality_checks` | DataFrame + `Settings` + `report_name` | `data/quality/gx/{baseline,corrupted,repaired}.json` (6 check) | Hoàn thành |
| Freshness report | `src/observability/quality.py::build_freshness_report` | DataFrame + `Settings` + `report_path` | `data/quality/freshness_report.json` + `freshness_{corrupted,repaired}.json` | Hoàn thành |
| Phase 1 markdown report | `src/observability/reporting.py::generate_phase1_report` | 4 dicts (source/metrics/quality/freshness) | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption comparison report | `src/observability/reporting.py::generate_corruption_report` | 3 metrics + 2 quality + 2 freshness dicts | `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên / module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Xác nhận clean schema trước khi viết `corruption.py` | TV2 (cleaning owner) | Tái sử dụng helper `_embedding_text()` từ `ingestion/cleaning.py` để rebuild `text_for_embedding` đúng format 5 dòng (Title/Authors/Categories/Published/Summary) sau khi corrupt |
| Tư vấn về cờ `report_name` để tách 3 file `gx/*.json` | Trưởng nhóm (integrator) | Quy ước `report_name ∈ {baseline, corrupted, repaired}` để Phase 1/Phase 2 ghi đúng artifact tương ứng vào `data/quality/gx/` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / hàm / artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Implement 6 corruption scenarios có chủ đích | `src/ingestion/corruption.py` | `corrupt_clean_dataframe` (drop latest / blank summary / inject noise / truncate title / stale date / duplicate) + ghi `corruption_log.json` | Mở `data/results/corruption_log.json` — 6 scenario, `input_rows=24, output_rows=22` |
| Implement 6 quality checks (gx) | `src/observability/quality.py` | `run_data_quality_checks` → `data/quality/gx/{stage}.json` | Baseline 6/6 PASS, Corrupted 3/6 FAIL, Repaired 6/6 PASS |
| Implement freshness monitoring | `src/observability/quality.py` | `build_freshness_report` → `data/quality/freshness_{stage}.json` | Baseline `is_fresh=true`, Corrupted `is_fresh=false` (6 stale rows), Repaired `is_fresh=true` |
| Sinh baseline markdown | `src/observability/reporting.py` | `data/reports/phase1_report.md` | 4 section: Source / RAG eval / Quality / Freshness |
| Sinh comparison markdown | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Bảng 5 cột (Metric | Baseline | Corrupted | Repaired | Δ) + 2 bảng quality + 1 bảng freshness |

**Output cụ thể tôi đã tạo/giúp xác minh:**
- `data/quality/gx/baseline.json` — 6/6 PASS
- `data/quality/gx/corrupted.json` — 3/6 FAIL (`paper_id_unique`, `summary_length`, `freshness`)
- `data/quality/gx/repaired.json` — 6/6 PASS
- `data/quality/freshness_report.json` + `freshness_{corrupted,repaired}.json`
- `data/results/corruption_log.json` — `input_rows=24, output_rows=22`, 6 scenario ghi rõ `requested` / `dropped|blanked|noised|truncated|stale|duplicated`
- `data/reports/phase1_report.md`
- `data/reports/corruption_report.md`

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. Phải tạo ra bộ dữ liệu hỏng **có chủ đích, đa dạng và reproducible** để chứng minh rằng chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng RAG agent — không phải corrupt ngẫu nhiên mà phải cover đủ 5 dạng hỏng mà hệ thống RAG thường gặp (mất record, mất content, nhiễu content, mất title, stale date) cộng thêm duplicate để kiểm tra ranking.
2. Phải sinh ra **markdown report có cấu trúc** để Trưởng nhóm đối chiếu với rubric, đồng thời phục vụ viết `group_report.md` và thuyết trình.
3. Phải có **observability signal 2 lớp** (per-row check + aggregate freshness) để leader có thể chứng minh được "dữ liệu xấu → metric xấu" và "repair → metric tốt lại".

### Cách triển khai

**`corrupt_clean_dataframe`** — 6 scenario xếp chồng, dùng `random.Random(20251104)` cho mọi step để rerun ổn định:

1. **Drop latest 20%** (5/24 records) — sort theo `published` desc rồi slice bỏ phần đầu. Dùng `sort_values` thay vì random sample vì "drop latest" về mặt ngữ nghĩa là "mất bản ghi mới nhất". Trong test set TV2 chọn 4 paper từ đầu cleaned DataFrame (sort `published` desc) → drop 5 latest sẽ xóa luôn các paper thuộc test set → `retrieval_hit_rate` sụt mạnh.
2. **Blank summary 25%** (5/19 rows còn lại) — set `summary=""` + `summary_chars=0`. Embedding mất semantic content của 5 paper.
3. **Inject noise 20%** (4 rows) — append phrase ngẫu nhiên từ 4 phrase định sẵn (`[REDACTED]`, `lorem ipsum...`, `??? corrupted payload ???`, `random tokens xyz123`) vào `summary`. Embedding bị nhiễu.
4. **Truncate title 25%** (5 rows) — cắt 50% ký tự + thêm `…`. Exact title lookup (regex `'([^']+)'` trong `qa.py`) sẽ fail vì test set hỏi theo title đầy đủ.
5. **Stale published 20%** (4 rows) — trừ `published`/`updated` đi 365 ngày → `age_days` vượt threshold 180 → freshness check `is_fresh=False`.
6. **Duplicate 15%** (3 rows) — `pd.concat([df, df.sample(...)])` → 22 + 3 = 22 (sau khi reset_index), `paper_id` unique check fail.

Sau 6 scenario: rebuild `text_for_embedding` (dùng `_embedding_text` của TV2 để giữ đúng format 5 dòng), recompute `age_days` từ `published` mới, recompute `summary_chars`. Cuối cùng ghi `corruption_log.json` với schema `{schema_version: 1, input_rows, output_rows, scenarios: [{name, requested, dropped|blanked|noised|truncated|stale|duplicated}]}`.

**`run_data_quality_checks`** — 6 check, mỗi check trả về `{name, status: PASS/FAIL, observed, threshold?, details}`:
- `row_count` ≥ 4
- `paper_id_not_null` (null + blank → fail)
- `paper_id_unique` (duplicated > 0 → fail)
- `title_not_null` (blank → fail)
- `summary_length` ≥ 40 chars
- `freshness` (age_days > 180 → fail)

Ghi vào `data/quality/gx/{report_name}.json`. Khi `corruption_flow.main` gọi 3 lần với `report_name ∈ {baseline, corrupted, repaired}` ra 3 file riêng.

**`build_freshness_report`** — parse `published` UTC, lấy `latest_published` / `oldest_published`, đếm `stale_rows > threshold`, `is_fresh = (stale_rows == 0 and latest is not None)`.

**`generate_phase1_report`** — 4 section markdown: Source / RAG evaluation / Data quality / Freshness. Format số: rate → %, score → 3 decimals, status → emoji ✅/❌.

**`generate_corruption_report`** — bảng 5 cột: Metric | Baseline | Corrupted | Repaired | Δ repaired vs baseline. Hai section tiếp theo cho quality (corrupted + repaired) và freshness (bảng 2 hàng). Section cuối `Interpretation` gợi ý cách đọc delta.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input (`corrupt_clean_dataframe`) | `pd.DataFrame` chứa các cột chuẩn của TV2 (`paper_id, title, summary, published, age_days, text_for_embedding, summary_chars, authors_joined, categories_joined, ...`); `output_log_path` (Path-like) |
| Output (`corrupt_clean_dataframe`) | DataFrame mới + `data/results/corruption_log.json` với schema `{schema_version: 1, input_rows, output_rows, scenarios: [...]}` |
| Module phụ thuộc | `ingestion.cleaning._embedding_text` (rebuild đúng format); `core.utils.write_json` |
| Module sử dụng output | `pipelines.corruption_flow.main` (Trưởng nhóm) — gọi `corrupt_clean_dataframe`, đọc `corruption_log.json` để đưa vào báo cáo |
| Input (`run_data_quality_checks`) | `pd.DataFrame` + `Settings` (lấy `freshness_threshold_days`) + `report_name: str` |
| Output (`run_data_quality_checks`) | `dict {row_count, passed, failed, success_rate, checks[]}` + `data/quality/gx/{report_name}.json` |
| Module sử dụng output | `pipelines.phase1.main` (baseline) và `pipelines.corruption_flow.main` (corrupted + repaired) |
| Input (`generate_phase1_report`) | 4 dicts: `source_summary` (query/filter/max_results/fetched/kept), `metrics` (samples/4 metric + ragas), `quality`, `freshness` |
| Output (`generate_phase1_report`) | `data/reports/phase1_report.md` |
| Input (`generate_corruption_report`) | 3 dicts metrics + 2 dicts quality + 2 dicts freshness |
| Output (`generate_corruption_report`) | `data/reports/corruption_report.md` |
| Điều kiện lỗi cần xử lý | Empty DataFrame (quality + freshness vẫn trả về dict hợp lệ với `total_rows=0`); thiếu cột trong DataFrame (check trả `FAIL` với `details` mô tả cột thiếu, không raise) |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** `phase1_report.md` có 4 section đầy đủ, `corruption_report.md` có bảng 5 cột + 2 bảng quality + 1 bảng freshness, `corruption_log.json` liệt kê đủ 6 scenario.
- **Kết quả thực tế:** ✅ Cả 2 script chạy thành công end-to-end. File `corruption_log.json` cho thấy `input_rows=24 → output_rows=22`, đủ 6 scenario. `corrupted_metrics.json` cho thấy 4 metric sụt mạnh so với baseline.
- **Artifact/log:** `data/quality/gx/{baseline,corrupted,repaired}.json`, `data/quality/freshness_{baseline,corrupted,repaired}.json`, `data/results/corruption_log.json`, `data/reports/{phase1_report,corruption_report}.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Trong `corrupt_clean_dataframe`, có 6 scenario cần áp dụng. Câu hỏi là scenario drop "latest" nên dùng random sampling hay sort-and-slice?
- **Các phương án đã cân nhắc:**
  1. **Random sampling** — `df.sample(n=drop, random_state=...)`. Đơn giản, đồng nhất với các scenario khác.
  2. **Sort by `published` desc + slice đầu** — bỏ đúng phần "mới nhất" theo nghĩa đen. Đúng ngữ nghĩa "drop latest records" hơn, vì test set được tạo từ 4 paper có `paper_id` thấp (kết quả từ `candidates.head(_MINIMUM_DOCUMENTS).sort_values("paper_id")` của TV2 trên DataFrame sort theo `published` desc), nên các câu hỏi evaluation sẽ reference đúng các paper bị drop → retrieval hit rate giảm mạnh.
- **Phương án đã chọn:** **Phương án 2** (sort theo `published` desc + slice đầu).
- **Lý do:** Nếu random thì có thể drop paper cũ, không ảnh hưởng retrieval hit rate. Nếu drop latest theo `published`, ít nhất 1–2 paper trong test set sẽ bị mất → `retrieval_hit_rate` sụt xuống rõ rệt, đó là narrative chính của bài lab.
- **Bằng chứng quyết định phù hợp:** `corrupted_metrics.json` cho thấy `retrieval_hit_rate` giảm từ **100% → 50%** — đúng kỳ vọng. `corruption_log.json` ghi `drop_latest_records: requested=5, dropped=5`. Test set có 16 câu hỏi (4 paper × 4 question_type) → nếu 1 paper trong test set bị mất thì 4 câu hỏi của paper đó sẽ không hit → 12/16 = 75%; nếu 2 paper thì 8/16 = 50% (đúng với kết quả quan sát được).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `[Line 51:5] Parameter 'rng' is unused [unused-parameter] (Pyrefly)` trong `corruption.py`.
- **Lệnh hoặc bước tái hiện:** Mở `corruption.py`, hover vào `def _drop_latest_records(df, fraction, rng)` — Pyrefly/Pylance báo unused-parameter warning.
- **Nguyên nhân gốc:** Hàm `_drop_latest_records` dùng `sort_values` theo `published` nên không cần RNG, nhưng giữ parameter `rng` để các scenario helper cùng signature (dễ refactor + dễ test). Pyrefly hiểu parameter khai báo mà không dùng là warning.
- **Cách xử lý:** Thêm `del rng` ngay đầu hàm + comment giải thích lý do giữ parameter. Vẫn giữ signature đồng nhất với `_blank_summaries`, `_inject_summary_noise`, etc.
- **Cách xác minh sau khi sửa:** Pyrefly/Pylance hết diagnostic trên line 51; hàm vẫn chạy đúng vì `del rng` chỉ là marker.
- **Điều học được:** Khi khai báo parameter để giữ signature symmetry, cần marker rõ ràng (`del`, `_name`) để tránh bị cả IDE lẫn Pyrefly flag. Trade-off giữa DRY (signature đồng nhất) và explicitness (parameter chỉ khi dùng) — chọn DRY khi helper sẽ được loop qua dict config.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** TV1 gọi `https://api.crossref.org/works` với `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:<180 days ago>,has-abstract:true`, `rows=24`. Raw JSON được lưu vào `data/raw/crossref_response.json`. `parse_crossref_payload` chuẩn hoá từng item thành `PaperRecord` (DOI làm `paper_id`, JATS abstract được strip tag, authors ghép từ `given+family`). Lưu list[PaperRecord] thành `data/raw/crossref_records.json`. TV2 gọi `build_clean_dataframe` để lọc (paper_id + title + summary non-empty, published parseable), dedupe theo `paper_id`, sort `published` desc, sinh `text_for_embedding` 5 dòng (Title/Authors/Categories/Published/Summary). TV3 dùng `sentence-transformers/all-MiniLM-L6-v2` (qua `MiniLMEmbeddings`) encode `text_for_embedding`, tạo collection Chroma `papers-baseline` (persisted tại `data/chroma/`), ghi manifest `data/embeddings/papers_embeddings.json`. Phase 2 làm tương tự cho 2 collection `papers-corrupted` và `papers-repaired`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** TV2 sinh `data/eval/test_set.json` — 4 paper × 4 question type = 16 sample. Mỗi sample có `id, question_type, question, ground_truth, ground_truth_doc_ids`. `evaluate_pipeline` (TV3 đã có) với mỗi câu hỏi: gọi `qa.answer_question` (heuristic trên `metadata` theo keyword "who authored", "when was", "what categories", mặc định trả `first_sentence(summary)`); `retrieval_hit = any(doc_id in ground_truth_doc_ids for doc_id in retrieved_doc_ids)`; `token_f1` so overlap token; `JudgeVerdict` (LLM) cho `score` 1–5 + `correct` boolean. Tổng hợp: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`, optional `ragas`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks (`run_data_quality_checks`) là **6 check schema/schema-level** trên từng row: row count, paper_id not-null/unique, title not-null, summary length, freshness. Output là `data/quality/gx/{stage}.json` với `success_rate`. Freshness report (`build_freshness_report`) **riêng** vì là metric vận hành, tập trung vào `published` distribution: `latest_published`, `oldest_published`, `stale_rows`, `is_fresh`. Freshness được xử lý như một khía cạnh time-sensitive, giúp Trưởng nhóm phát hiện khi pipeline Crossref bị "khoá" thời gian (filter date lỗi, source trả về paper cũ). Hai file này bổ sung cho nhau: gx check cho mỗi check có threshold riêng, freshness cho aggregate signal theo thời gian.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì các câu hỏi reference 4 `paper_id` cụ thể. Nếu đổi test set giữa 3 run:
   - `retrieval_hit_rate` không so sánh được (test set khác → question khác → paper khác).
   - `mean_token_f1` không meaningful (ground_truth khác).
   - Cả 4 metric cùng baseline bị nhiễu.
   Mục tiêu narrative là: cùng đầu vào, chỉ khác dữ liệu → chứng minh data quality ảnh hưởng trực tiếp đến answer quality. Test set được tạo 1 lần từ clean data, dùng lại cho 3 stage. Cờ `REFRESH_TEST_SET=1` chỉ dùng khi đổi clean dataset (tăng `max_results` chẳng hạn).

5. **Repair được xem là thành công dựa trên artifact và metric nào?** Repair = **rebuild lại clean data từ raw** (không "un-corrupt" dữ liệu hỏng). Đây là tiền đề của bài: nếu repair chỉ revert corruption thì không có ý nghĩa. Artifact + metric tiêu chí thành công:
   - `data/clean/papers_clean_repaired.csv` schema giống baseline, `paper_id` không overlap với corrupted (vì rebuilt từ raw).
   - `data/quality/gx/repaired.json` `failed = 0` (hoặc `success_rate` bằng baseline).
   - `data/quality/freshness_repaired.json` `is_fresh = true`, `stale_rows` bằng baseline.
   - `data/results/repaired_metrics.json`: `retrieval_hit_rate / mean_token_f1 / judge_accuracy / mean_judge_score` ≈ baseline (±~5%) và cao hơn corrupted đáng kể.
   - `data/reports/corruption_report.md` cột "Δ repaired vs baseline" gần 0, cột "Corrupted" thấp hơn baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric / signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 100.0% | 50.0% | 100.0% | Drop latest 5/24 records (khoảng 21% dữ liệu) + blank/noise/truncate summary đủ để giảm retrieval từ 16/16 xuống 8/16 đúng câu. Repaired trở lại 16/16 vì rebuilt từ raw |
| `mean_token_f1` | 1.000 | 0.438 | 1.000 | Trả lời của agent dựa trên `first_sentence(summary)` — blank summary 5/19 rows + noise 4 rows → câu trả lời lệch ground truth → F1 sụt mạnh |
| `judge_accuracy` | 100.0% | 43.8% | 100.0% | Judge LLM đánh giá đúng 7/16 câu (gần 1:1 với hit_rate) |
| `mean_judge_score` | 5.000 | 2.750 | 5.000 | Trung bình điểm 2.75/5 ở corrupted, phục hồi về 5/5 |
| Quality checks (pass rate) | 100.0% (6/6) | 50.0% (3/6) | 100.0% (6/6) | Corrupted fail ở `paper_id_unique` (3 duplicate), `summary_length` (6 summary < 40 chars), `freshness` (6 rows > 180 days) |
| Freshness status | Fresh (0 stale) | Stale (6 stale) | Fresh (0 stale) | `freshness_corrupted.json` cho thấy 6 rows vượt 180-day threshold sau khi stale-shift 365 ngày; `freshness_repaired.json` trở lại 0 |

### Kết luận từ số liệu

**Chuỗi nhân–quả #1: Data corruption → signal xấu → metric xấu**
`drop_latest_records` (5 rows) + `blank_summaries` (5 rows) + `inject_summary_noise` (4 rows) + `truncate_titles` (5 rows) + `stale_published_dates` (4 rows) + `duplicate_rows` (3 rows) → `paper_id_unique` FAIL (3 duplicate) + `summary_length` FAIL (6 summary < 40 chars) + `freshness` FAIL (6 stale rows) → `retrieval_hit_rate` giảm từ 100% → 50% (mất 2/4 paper trong test set vì 5 latest bị drop) + `mean_token_f1` giảm từ 1.0 → 0.438 (5 blank + 4 noise phá context).

**Chuỗi nhân–quả #2: Repair → signal tốt lại → metric phục hồi**
`rebuild từ raw snapshot` (`load_raw_records` → `build_clean_dataframe`) → `paper_id_unique` PASS (0 duplicate) + `summary_length` PASS (0 short) + `freshness` PASS (0 stale) → `retrieval_hit_rate` 100% + `mean_token_f1` 1.0 + `judge_accuracy` 100% + `mean_judge_score` 5.0.

**Corruption ảnh hưởng rõ nhất:** `drop_latest_records` (5 rows) vì 4 paper của test set đều nằm trong top `paper_id` thấp (TV2 chọn bằng `candidates.head(4).sort_values("paper_id")` trên DataFrame sort theo `published` desc), nên 5 latest bị drop trùng với 2 paper thuộc test set → 8/16 câu hỏi không retrieve được ground truth. Bằng chứng: `retrieval_hit_rate` 50% = 8/16, đúng kỳ vọng toán học.

**Kết quả khác với kỳ vọng ban đầu:** Kỳ vọng `mean_judge_score` ở corrupted sẽ giảm mạnh hơn (vì judge có thể đánh giá thấp cả 8 câu không hit). Thực tế `mean_judge_score = 2.75` (= 5.0 × 0.55, lệch tương ứng với 7/16 câu correct + 9/16 câu sai ở mức 1–2 điểm) → judge LLM đã đánh giá "từ tế" hơn kỳ vọng. Điều này cho thấy LLM judge có thể chấp nhận một phần câu trả lời dù retrieval miss, miễn là câu đó "nghe có vẻ đúng".

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline (reproducibility):** Seed RNG cố định (`_RANDOM_SEED = 20251104`) + dùng `random.Random` thay vì `random.seed` toàn cục + ghi `corruption_log.json` cho mỗi run là cách hiệu quả để rerun ổn định và debug khi output khác nhau giữa các lần chạy. Bài học: nếu không reproducible, không thể so sánh baseline vs corrupted vs repaired một cách công bằng.
2. **Về Data Observability (2 lớp):** Tách 2 cấp (gx check per-row pass/fail + freshness report aggregate time signal) giúp reporter tool + leader dễ đọc, và rule "RAISE alert khi staleness > 30%" chạy được khi integrate CI/CD. Bài học: 1 metric đơn lẻ (vd chỉ success_rate) sẽ mất thông tin; kết hợp nhiều lớp mới phát hiện được "cái gì hỏng" và "hỏng bao nhiêu".
3. **Về ảnh hưởng Data → RAG Agent:** 6 scenario trong bài đánh trúng 3 khía cạnh retrieval (drop & blank → giảm signal), answer (noise → judge accuracy giảm), freshness (stale date → staleness check fail). Một corruption scenario "đúng hướng" phải map được sang ≥ 1 metric. Bài học: corruption tốt ≠ corruption nhiều, mà là corruption **có chủ đích** + có thể **truy ngược** được từ metric.

### Nếu có thêm thời gian

- **Cải thiện:** Cho phép truyền `seed` và `config dict` vào `corrupt_clean_dataframe` thay vì hard-code `_RANDOM_SEED`, `_DROP_LATEST_FRACTION`, `_BLANK_FRACTION`, etc. → dễ chạy A/B corruption scenarios để đo độ nhạy của từng loại lỗi.
- **Lý do:** Hiện tại các hằng số ở top file. Nếu muốn "corrupt nhẹ" (drop 5% + blank 10%) vs "corrupt nặng" (drop 30% + blank 50%) thì phải sửa code. Một `config dict` cho phép A/B test mà không đụng vào logic.
- **Cách đo:** Chạy 2 phiên bản end-to-end, so sánh `corrupted_metrics.json` của 2 phiên bản → kỳ vọng phiên bản "nặng" có 4 metric thấp hơn phiên bản "nhẹ" ≥ 10% (tương tự slope giữa baseline 100% và corrupted 50% hiện tại).

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu (mục 3 liệt kê file, mục 8 liệt kê số liệu từ file).
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (cả 2 script đã chạy thực tế, số liệu lấy từ JSON, không phải ước lượng).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đinh Quang Minh
**Ngày xác nhận:** 2026-08-06
