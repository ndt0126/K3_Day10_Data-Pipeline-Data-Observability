# Member Role Report — TV4: Observability, Corruption & Reporting

> Báo cáo cá nhân của Thành viên 4 (Observability, Corruption & Reporting Owner) cho bài lab Day 10. Tập trung vào phần việc đã làm, quyết định kỹ thuật và đóng góp vào luồng end-to-end. Phần Metrics/Analysis ở mục 8 sẽ được cập nhật sau khi pipeline chạy end-to-end.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | [TV4 — Observability, Corruption & Reporting Owner] |
| MSSV | [MSSV] |
| Khóa/Lớp | [K3 hoặc K4] |
| Tên nhóm | [Tên nhóm] |
| Vai trò chính | Observability, Corruption & Reporting Owner (TV4) |
| Repository | [https://github.com/ndt0126/K3_Day10_Data-Pipeline-Data-Observability] |
| Ngày hoàn thành (code) | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module / deliverable | File / hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data corruption | `src/ingestion/corruption.py::corrupt_clean_dataframe` | Clean DataFrame từ TV2 (`papers_clean.csv`/`json`) + `output_log_path` | DataFrame đã corrupt + `corruption_log.json` | Hoàn thành (code) |
| Data quality checks | `src/observability/quality.py::run_data_quality_checks` | DataFrame + `Settings` + `report_name` | `data/quality/gx/{report_name}.json` (6 checks) | Hoàn thành (code) |
| Freshness report | `src/observability/quality.py::build_freshness_report` | DataFrame + `Settings` + `report_path` | `data/quality/freshness_report.json` | Hoàn thành (code) |
| Phase 1 markdown report | `src/observability/reporting.py::generate_phase1_report` | `source_summary`, `metrics`, `quality`, `freshness` dicts | `data/reports/phase1_report.md` | Hoàn thành (code) |
| Corruption comparison report | `src/observability/reporting.py::generate_corruption_report` | 3 metrics dicts + 2 quality + 2 freshness dicts | `data/reports/corruption_report.md` | Hoàn thành (code) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên / module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Xác nhận clean schema trước khi viết `corruption.py` | TV2 (cleaning owner) | Dùng các cột `paper_id, title, summary, published, age_days, text_for_embedding, summary_chars, authors_joined, categories_joined` (đối chiếu với `CLEAN_DATA_COLUMNS` của TV2) để đảm bảo rebuild `text_for_embedding` đúng format |
| Tư vấn về determinism của corruption scenarios | Leader (báo cáo nhóm) | Đặt `_RANDOM_SEED = 20251104` và phần lớn scenario dùng cùng `random.Random` để rerun ra log y hệt |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File / hàm / artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Implement 6 corruption scenarios | `src/ingestion/corruption.py` | Hàm `corrupt_clean_dataframe` + `corruption_log.json` schema | End-to-end: chạy `script/run_corruption_flow.py` rồi mở `data/results/corruption_log.json` — phải liệt kê đúng 6 scenario và `output_rows` |
| Implement 6 quality checks | `src/observability/quality.py` | `run_data_quality_checks` → `data/quality/gx/{report_name}.json` | Mở file JSON, kiểm tra `passed/failed/checks[]` |
| Implement freshness report | `src/observability/quality.py` | `build_freshness_report` → `data/quality/freshness_report.json` | Mở JSON, kiểm tra `latest_published, oldest_published, stale_rows, is_fresh` |
| Sinh baseline markdown | `src/observability/reporting.py` | `data/reports/phase1_report.md` | Đọc file, kiểm tra 4 section + bảng metric + bảng check |
| Sinh comparison markdown | `src/observability/reporting.py` | `data/reports/corruption_report.md` | Đọc file, kiểm tra bảng 3 cột metric + delta + 2 bảng quality + bảng freshness |

**Output cụ thể tôi đã tạo/giúp xác minh:**
- `data/quality/gx/*` (6 check pass/fail per stage)
- `data/quality/freshness_report.json` (latest/oldest/stale)
- `data/results/corruption_log.json` (6 scenario, schema v1)
- `data/reports/phase1_report.md` (4 section markdown)
- `data/reports/corruption_report.md` (bảng so sánh 3 trạng thái + delta)

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

1. Phải tạo ra bộ dữ liệu hỏng **có chủ đích** để chứng minh rằng chất lượng dữ liệu ảnh hưởng trực tiếp đến chất lượng RAG agent — không phải corrupt ngẫu nhiên mà phải cover đủ 5 dạng hỏng mà hệ thống RAG thường gặp (mất record, mất content, nhiễu, mất title, stale).
2. Phải sinh ra **markdown report có cấu trúc** để leader đối chiếu với rubric, đồng thời phục vụ viết `group_report.md`.

### Cách triển khai

**`corrupt_clean_dataframe`** — 6 scenario xếp chồng, dùng `random.Random(20251104)` cho mọi step để rerun ổn định:

1. **Drop latest 20%** records — sort theo `published` desc rồi bỏ phần đầu. Đây là scenario duy nhất dùng `sort_values` thay vì random (vì drop "theo thời gian" vốn đã deterministic).
2. **Blank summary 25%** — set `summary = ""` + `summary_chars = 0`. Embedding mất semantic content, retrieval hit rate giảm rõ rệt.
3. **Inject noise 20%** — append phrase ngẫu nhiên từ 4 phrase định sẵn (`[REDACTED]`, `lorem ipsum...`, `??? corrupted payload ???`, `random tokens xyz123`). Embedding bị nhiễu.
4. **Truncate title 25%** — cắt 50% ký tự + thêm `…`. Exact title lookup (regex `'([^']+)'` trong `qa.py`) sẽ fail.
5. **Stale published 20%** — trừ `published` đi 365 ngày. `age_days` vượt threshold 180 → freshness check `is_fresh = False`.
6. **Duplicate 15%** — `pd.concat([df, df.sample(...)])`. Retrieval trả về trùng nhau, `mean_token_f1` có thể giảm vì context lặp.

Sau 6 scenario: rebuild `text_for_embedding` (dùng `_embedding_text` của TV2 để giữ đúng format 5 dòng), recompute `age_days` từ `published` mới, recompute `summary_chars`. Cuối cùng ghi `corruption_log.json` với schema `{schema_version: 1, input_rows, output_rows, scenarios: [{name, requested, ...}]}`.

**`run_data_quality_checks`** — 6 check, mỗi check trả về `{name, status: PASS/FAIL, observed, threshold?, details}`:
- `row_count` ≥ 4
- `paper_id_not_null` (null + blank → fail)
- `paper_id_unique` (duplicated > 0 → fail)
- `title_not_null` (blank → fail)
- `summary_length` ≥ 40 chars
- `freshness` (age_days > threshold → fail)

Ghi vào `data/quality/gx/{report_name}.json`. `report_name` dùng để phân biệt 3 stage: `baseline`, `corrupted`, `repaired`.

**`build_freshness_report`** — parse `published` UTC, lấy `latest_published` / `oldest_published`, đếm `stale_rows > threshold`, `is_fresh = (stale_rows == 0 and latest is not None)`.

**`generate_phase1_report`** — 4 section markdown: Source / RAG evaluation / Data quality / Freshness. Format số: rate → %, score → 3 decimals, status → emoji ✅/❌.

**`generate_corruption_report`** — bảng 5 cột: Metric | Baseline | Corrupted | Repaired | Δ repaired vs baseline. Hai section tiếp theo cho quality (corrupted + repaired) và freshness (bảng 2 hàng). Section cuối `Interpretation` gợi ý cách đọc delta.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input (`corrupt_clean_dataframe`) | `pd.DataFrame` chứa các cột chuẩn của TV2 (`paper_id, title, summary, published, age_days, text_for_embedding, summary_chars, ...`); `output_log_path` (Path-like) |
| Output (`corrupt_clean_dataframe`) | DataFrame mới + `data/results/corruption_log.json` với schema `{schema_version: 1, input_rows, output_rows, scenarios: [...]}` |
| Module phụ thuộc | `ingestion.cleaning._embedding_text` (rebuild đúng format); `core.utils.write_json` |
| Module sử dụng output | `pipelines.corruption_flow.main` (TV3) — gọi `corrupt_clean_dataframe`, dùng `corruption_log.json` cho báo cáo |
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
# Cú pháp dự kiến (cần TV3 + leader chạy end-to-end):
uv run python script/run_phase1.py            # sau đó mở data/reports/phase1_report.md
uv run python script/run_corruption_flow.py   # sau đó mở data/reports/corruption_report.md
```

- **Kết quả mong đợi:** `phase1_report.md` có 4 section đầy đủ, `corruption_report.md` có bảng 5 cột + 2 bảng quality + 1 bảng freshness, `corruption_log.json` liệt kê đủ 6 scenario.
- **Kết quả thực tế:** _chưa chạy end-to-end_ — cần TV3 chốt `pipelines/phase1.py` + `corruption_flow.py` rồi leader chạy tích hợp.
- **Artifact/log:** `data/quality/gx/{baseline,corrupted,repaired}.json`, `data/quality/freshness_report.json`, `data/results/corruption_log.json`, `data/reports/{phase1_report,corruption_report}.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Trong `corrupt_clean_dataframe`, có 6 scenario cần áp dụng. Câu hỏi là scenario drop "latest" nên dùng random sampling hay sort-and-slice?
- **Các phương án đã cân nhắc:**
  - **A: Random sampling** — `df.sample(n=drop, random_state=...)`. Đơn giản, đồng nhất với các scenario khác.
  - **B: Sort by `published` desc + slice đầu** — bỏ đúng phần "mới nhất" theo nghĩa đen. Đúng ngữ nghĩa "drop latest records" hơn, vì test set được tạo từ 4 paper mới nhất (theo `candidates.head(_MINIMUM_DOCUMENTS).sort_values("paper_id")` của TV2), các câu hỏi evaluation sẽ reference đúng các paper bị drop → retrieval hit rate giảm mạnh.
- **Phương án đã chọn:** **B** (sort theo `published` desc + slice đầu).
- **Lý do:** Nếu random thì có thể drop paper cũ, không ảnh hưởng retrieval hit rate. Nếu drop latest, ít nhất 1–2 paper trong test set TV2 (chọn từ head của cleaned DataFrame sort theo `paper_id` ascending — gần nhất với đầu cleaned DataFrame sort theo `published` desc) sẽ bị mất → `retrieval_hit_rate` sụt xuống rõ rệt, đó là narrative chính của bài lab.
- **Bằng chứng quyết định phù hợp:** Chưa chạy — cần end-to-end để đối chiếu `corruption_log.json.scenarios[drop_latest_records].dropped` với `retrieval_hit_rate` trong `corrupted_metrics.json`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `[Line 51:5] Parameter 'rng' is unused [unused-parameter] (Pyrefly)` trong `corruption.py`.
- **Lệnh hoặc bước tái hiện:** Mở `corruption.py`, hover vào `def _drop_latest_records(df, fraction, rng)` — Pyrefly/Pylance báo _unused-parameter_.
- **Nguyên nhân gốc:** Hàm `_drop_latest_records` dùng `sort_values` theo `published` nên không cần RNG, nhưng giữ parameter `rng` để các scenario helper cùng signature (dễ refactor + dễ test). Pyrefly hiểu parameter khai báo mà không dùng là warning.
- **Cách xử lý:** Thêm `del rng` ngay đầu hàm + comment giải thích lý do giữ parameter. Vẫn giữ signature đồng nhất.
- **Cách xác minh sau khi sửa:** Pyrefly/Pylance hết diagnostic trên line 51.
- **Điều học được:** Khi khai báo parameter để giữ signature symmetry, cần marker rõ ràng (`del`, `_name`) để tránh bị cả IDE lẫn Pyrefly flag.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** TV1 gọi `https://api.crossref.org/works` với `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:<180 days ago>,has-abstract:true`, `rows=24`. Raw JSON được lưu vào `data/raw/crossref_response.json`. `parse_crossref_payload` chuẩn hoá từng item thành `PaperRecord` (DOI làm `paper_id`, JATS abstract được strip tag, authors ghép từ `given+family`). Lưu list[PaperRecord] thành `data/raw/crossref_records.json`. TV2 gọi `build_clean_dataframe` để lọc (paper_id + title + summary non-empty, published parseable), dedupe theo `paper_id`, sort `published` desc, sinh `text_for_embedding` 5 dòng (Title/Authors/Categories/Published/Summary). TV3 dùng `sentence-transformers/all-MiniLM-L6-v2` (qua `MiniLMEmbeddings`) encode `text_for_embedding`, tạo collection Chroma `papers-baseline` (persisted tại `data/chroma/`), ghi manifest `data/embeddings/papers_embeddings.json`.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** TV2 sinh `data/eval/test_set.json` — 4 paper × 4 question type = 16 sample. Mỗi sample có `id, question_type, question, ground_truth, ground_truth_doc_ids`. `evaluate_pipeline` (TV3 đã có) với mỗi câu hỏi: gọi `qa.answer_question` (heuristic trên `metadata` theo keyword "who authored", "when was", "what categories", mặc định trả `first_sentence(summary)`); `retrieval_hit = any(doc_id in ground_truth_doc_ids for doc_id in retrieved_doc_ids)`; `token_f1` so overlap token; `JudgeVerdict` (LLM) cho `score` 1–5 + `correct` boolean. Tổng hợp: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`, optional `ragas`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks (`run_data_quality_checks`) là **6 check schema/schema-level** trên từng row: row count, paper_id not-null/unique, title not-null, summary length, freshness. Output là `data/quality/gx/{stage}.json` với `success_rate`. Freshness report (`build_freshness_report`) **riêng** vì là metric vận hành, tập trung vào `published` distribution: `latest_published`, `oldest_published`, `stale_rows`, `is_fresh`. Freshness được xử lý như một khía cạnh time-sensitive, giúp leader phát hiện khi pipeline crossref bị "khoá" thời gian (filter date lỗi, source trả về paper cũ).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì các câu hỏi reference 4 `paper_id` cụ thể. Nếu đổi test set giữa 3 run:
   - `retrieval_hit_rate` không so sánh được (test set khác → question khác → paper khác).
   - `mean_token_f1` không meaningful (ground_truth khác).
   - Cả 4 metric cùng baseline bị nhiễu.
   Mục tiêu narrative là: cùng đầu vào, chỉ khác dữ liệu → chứng minh data quality ảnh hưởng trực tiếp đến answer quality. Test set được tạo 1 lần từ clean data, dùng lại cho 3 stage. Cờ `REFRESH_TEST_SET=1` chỉ dùng khi đổi clean dataset (tăng `max_results` chẳng hạn).

5. **Repair được xem là thành công dựa trên artifact và metric nào?** Repair = **rebuild lại clean data từ raw** (không "un-corrupt" dữ liệu hỏng). Đây là tiền đề của bài: nếu repair chỉ revert corruption thì không có ý nghĩa. Artifact + metric tiêu chí thành công:
   - `data/clean/papers_clean_repaired.csv` schema giống baseline, `paper_id` không overlap với corrupted (vì rebuilt từ raw).
   - `data/quality/gx/repaired.json` `failed = 0` (hoặc `success_rate` bằng baseline).
   - `data/quality/freshness_report.json` (repaired) `is_fresh = true`, `stale_rows` bằng baseline.
   - `data/results/repaired_metrics.json`: `retrieval_hit_rate / mean_token_f1 / judge_accuracy / mean_judge_score` ≈ baseline (±~5%) và cao hơn corrupted đáng kể.
   - `data/reports/corruption_report.md` cột "Δ repaired vs baseline" gần 0, cột "Corrupted" thấp hơn baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | _pending_ | _pending_ | _pending_ | _Sẽ cập nhật sau khi chạy end-to-end. Kỳ vọng: Corrupted giảm rõ (drop latest 20% + blank summary), Repaired phục hồi về baseline do rebuild từ raw._ |
| `mean_token_f1` | _pending_ | _pending_ | _pending_ | _Sẽ cập nhật._ |
| `judge_accuracy` | _pending_ | _pending_ | _pending_ | _Sẽ cập nhật._ |
| `mean_judge_score` | _pending_ | _pending_ | _pending_ | _Sẽ cập nhật._ |
| Quality checks (pass rate) | _pending_ | _pending_ | _pending_ | _Kỳ vọng: baseline 100% → corrupted ~50% (freshness + summary length fail) → repaired ~100%._ |
| Freshness status | _pending_ | _pending_ | _pending_ | _Kỳ vọng: baseline `is_fresh=true` → corrupted `is_fresh=false` (stale date 20% + duplicate + drop) → repaired `is_fresh=true`._ |

### Kết luận từ số liệu

_Chưa có số liệu end-to-end — sẽ cập nhật sau khi leader chạy `script/run_phase1.py` + `script/run_corruption_flow.py` rồi leader dán kết quả vào `group_report.md`._

**Hai chuỗi nhân–quả dự kiến:**

1. **[Corruption]** Drop latest 20% + blank summary 25% + noise 20% → **freshness check FAIL** (stale date 20%) + **summary_length FAIL** (blank 25%) + **retrieval_hit_rate giảm** (drop chứa paper trong test set + blank summary phá embedding) → **mean_token_f1 + judge_accuracy giảm** (context bị nhiễu hoặc mất).
2. **[Repair]** Rebuild clean data từ raw → **freshness check PASS** + **summary_length PASS** + **paper_id unique** → **retrieval_hit_rate ≈ baseline** + **mean_token_f1 + judge_accuracy ≈ baseline**.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline reproducibility**: Seed RNG + dùng `random.Random` thay vì `random.seed` toàn cục + ghi `corruption_log.json` cho mỗi run là cách hiệu quả để rerun ổn định và debug khi output khác nhau giữa các lần chạy.
2. **Data observability schema**: Tách 2 cấp (gx check: per-row pass/fail; freshness report: aggregate tín hiệu time) giúp reporter tool + leader dễ đọc, và giúp rule "RAISE alert khi staleness > 30%" chạy được khi integrate CI/CD.
3. **Data quality ảnh hưởng RAG**: 6 scenario đánh trúng 3 khía cạnh retrieval (drop & blank → giảm signal), answer (noise → judge accuracy giảm), freshness (stale date → staleness check fail). Một corruption scenario "đúng hướng" phải map được sang ≥ 1 metric.

### Nếu có thêm thời gian

- **Cải thiện:** Cho phép truyền `seed` và `config` vào `corrupt_clean_dataframe` thay vì hard-code `_RANDOM_SEED`, `_DROP_LATEST_FRACTION`, etc. → dễ chạy A/B corruption scenarios để đo độ nhạy của từng loại lỗi.
- **Lý do:** Hiện tại các hằng số ở top file. Nếu leader muốn "corrupt nhẹ" (drop 5% + blank 10%) vs "corrupt nặng" (drop 30% + blank 50%) thì phải sửa code.
- **Cách đo:** Chạy 2 phiên bản end-to-end, so `corrupted_metrics.json` của 2 phiên bản → kỳ vọng phiên bản "nặng" có 4 metric thấp hơn phiên bản "nhẹ" ≥ 10%.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết quả / output mô tả trong báo cáo đều có file/artifact tương ứng (cột 3 mục 3).
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (mục 4 "Cách xác minh" và mục 8 đã ghi rõ _pending_ / _chưa chạy end-to-end_).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [TV4 — Observability, Corruption & Reporting Owner]
**Ngày xác nhận:** 2026-08-06
