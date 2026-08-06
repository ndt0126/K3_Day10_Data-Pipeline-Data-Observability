# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| ------------------ | -------------------------------------------------------------------- |
| Khóa/Lớp | K3 |
| Tên nhóm | B4 |
| Repository | https://github.com/ndt0126/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | ------------ | ------ | --------------- | --------------------------- |
| 1 | Nguyễn Đức Trung | 2A202601725 | Trưởng nhóm (Pipeline Integrator) | `src/core/config.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `group_report.md` |
| 2 | Nguyễn Tuấn Nam | 2A202602039 | Thành viên 1 (Source Ingestion Owner) | `src/ingestion/crossref.py`, `data/raw/` |
| 3 | Lại Duy Đông | 2A202601913 | Thành viên 2 (Data Cleaning & Eval Set Owner) | `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, `data/clean/` |
| 4 | Nguyễn Quang Vinh | 2A202601049 | Thành viên 3 (RAG & Agent Owner) | `src/retrieval/index.py`, `src/retrieval/agent.py`, `data/embeddings/` |
| 5 | Đinh Quang Minh | 2A202601347 | Thành viên 4 (Observability, Corruption & Reporting Owner) | `src/observability/quality.py`, `src/observability/reporting.py`, `src/ingestion/corruption.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ hệ thống Data Pipeline và Data Observability end-to-end cho RAG Agent. Ở giai đoạn Baseline, pipeline tự động thu thập bài báo thô từ Crossref API, làm sạch dữ liệu thành 24 bài báo chuẩn hóa, dựng ChromaDB Vector Store (`papers-baseline`) và đánh giá trên bộ test set gồm 16 câu hỏi. Kết quả Baseline đạt hiệu năng tối đa: Retrieval Hit Rate 100%, Token F1 1.0, Judge Accuracy 100% và Judge Score 5.0/5.0 với 100% Data Quality Checks vượt qua.

Khi thực hiện 6 giả lập Data Corruption (xóa record mới nhất, xóa summary, chèn nhiễu, cắt title, làm cũ ngày và lặp dòng), hiệu năng của Agent sụt giảm nghiêm trọng: Retrieval Hit Rate giảm còn 50.0%, Token F1 giảm xuống 0.438, Judge Accuracy còn 43.8%, Judge Score còn 2.750 và Quality Pass Rate chỉ đạt 50% (thất bại 3 bài check). Sau khi tiến hành khôi phục dữ liệu (Repair) trực tiếp từ raw records, toàn bộ các chỉ số đã phục hồi về mức baseline. Các judge metrics hiện được tạo bởi fallback heuristic do LLM evaluator không khả dụng; RAGAS chưa được bật.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response / raw records (data/raw/)
    -> cleaning & data modeling (data/clean/)
    -> embedding + ChromaDB index (data/embeddings/ & data/chroma/)
    -> evaluation baseline (data/results/ & data/eval/)
    -> quality/freshness reports (data/quality/)
    -> corruption simulation (data/clean/ & data/results/corruption_log.json)
    -> re-index & re-evaluate (corrupted stage)
    -> repair từ dữ liệu nguồn raw
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref REST API | Fetch, retry/backoff, parse payload thành `PaperRecord` | `data/raw/crossref_records.json` | Nguyễn Tuấn Nam |
| Cleaning | Raw `PaperRecord` | Filter, chuẩn hóa text, tính `age_days`, sinh `text_for_embedding` | `data/clean/papers_clean.csv` | Lại Duy Đông |
| Embedding/index | Clean DataFrame | Vectorize `MiniLM`, dựng HNSW Cosine ChromaDB Index | `data/embeddings/papers_embeddings.json` | Nguyễn Quang Vinh |
| Evaluation | Clean DF, Chroma Index | Sinh bộ câu hỏi testset (16 câu), chấm điểm Hit Rate, Token F1 và answer judge (LLM khi khả dụng, fallback heuristic trong artifact hiện tại) | `data/eval/test_set.json`, `data/results/` | Lại Duy Đông & Nguyễn Quang Vinh |
| Observability | Clean DF, Settings | Kiểm tra 6 quy tắc chất lượng (Null, Dup, Row Count, Summary Length) & Freshness | `data/quality/` | Đinh Quang Minh |
| Corruption/repair | Clean DF, Raw Records | Chèn nhiễu, rỗng summary, lặp dòng, làm cũ ngày; sau đó repair từ raw | `data/results/corruption_log.json`, `data/reports/` | Đinh Quang Minh |
| Orchestration | Main Settings | Điều phối flow Phase 1 Baseline & Corruption Flow end-to-end | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Nguyễn Đức Trung |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `gemini` (hoặc fallback heuristic judge) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` |
| Retrieval `top_k` | `4` |
| Freshness threshold | `180` ngày |
| Random seed | `20251104` |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline pipeline:
```bash
uv run python script/run_phase1.py
```

Corruption & Repair flow:
```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 10:53:19 | `data/results/baseline_metrics.json` |
| Corruption flow | Thành công | 2026-08-06 10:53:39 | `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query="agentic retrieval augmented generation large language model"`, `from-pub-date: 180 days` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được | 24 records |
| Cơ chế retry/backoff | Tự động retry khi gặp HTTP status code 429 hoặc 503 |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | String (DOI) | Có | Định danh bài báo unique | Trích xuất từ DOI; loại bỏ nếu rỗng |
| `title` | String | Có | Tiêu đề bài báo | Chuẩn hóa khoảng trắng, loại bỏ tag HTML |
| `summary` | String | Có | Tóm tắt bài báo | Giữ abstract sạch; nếu ngắn hơn 40 ký tự sẽ đánh dấu lỗi quality |
| `authors_joined` | String | Có | Danh sách tác giả | Nối các tên tác giả bằng dấu phẩy |
| `categories_joined` | String | Có | Thể loại bài báo | Nối danh sách thể loại |
| `published` | String (ISO Date) | Có | Ngày xuất bản | Parse ISO 8601 UTC date |
| `age_days` | Integer | Có | Số ngày tính đến hiện tại | Tính `(run_date - published).days` |
| `text_for_embedding` | String | Có | Chuỗi văn bản dùng cho vector store | Format: `Title: ... \n Authors: ... \n Categories: ... \n Published: ... \n Summary: ...` |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bỏ record trùng lặp `paper_id` | Uniqueness | 0 | `df.duplicated(subset=['paper_id'])` |
| Lọc record thiếu `title` hoặc `summary` | Completeness | 0 | `df['title'].isna()` / `df['summary'].isna()` |
| Chuẩn hóa ngày xuất bản & tính `age_days` | Timeliness / Validity | 24 | So sánh `published` với `run_date` |

**Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:**
- `text_for_embedding`: Kết hợp các trường tiêu đề, tác giả, thể loại, ngày xuất bản và tóm tắt theo cấu trúc chuẩn để giữ ngữ cảnh đầy đủ cho MiniLM embeddings.
- Document ID: Có dạng `{paper_id}::{index}` nhằm duy trì liên kết trực tiếp với bài báo gốc.
- `age_days`: Tính bằng chênh lệch số ngày giữa `run_date` (hiện tại) và ngày `published` của bài báo.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 16 câu hỏi |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | `paper_id` chuẩn lấy từ `papers_clean.csv` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k` | `4` |
| LLM provider/model | `gemini` / `gemini-2.5-flash` (kèm fallback heuristic judge) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Việc giữ cố định bộ `test_set.json` cho cả 3 trạng thái đảm bảo tính khách quan và tính so sánh được (apples-to-apples comparison). Mọi sự thay đổi về điểm số Hit Rate hay F1-score đều phản ánh chính xác tác động của chất lượng dữ liệu lên hệ thống RAG chứ không bị nhiễu do thay đổi câu hỏi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/crossref_records.json` | Có | 24 raw records |
| Cleaned dataset | `data/clean/papers_clean.csv` | Có | 24 cleaned records |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | Có | Collection `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | Có | 16 samples |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit rate 100%, F1 1.0 |
| Quality/freshness | `data/quality/gx/baseline.json`, `data/quality/freshness_report.json` | Có | 6/6 checks PASS, Fresh |
| Baseline report | `data/reports/phase1_report.md` | Có | Đã xuất báo cáo |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 100.0% (1.0) | Top-4 retrieval luôn chứa đúng tài liệu chứa câu trả lời |
| `mean_token_f1` | 1.000 | Câu trả lời của Agent khớp hoàn toàn với Ground Truth |
| `judge_accuracy` | 100.0% (1.0) | Fallback heuristic đánh giá 100% câu trả lời baseline đúng |
| `mean_judge_score` | 5.000 / 5.0 | Điểm fallback heuristic đạt 5/5 trên toàn bộ test set |
| Ragas, nếu có | Skipped | Đã tắt Ragas để tối ưu tốc độ chạy |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count` | Completeness | $\ge 4$ rows | PASS (24 rows) | `data/quality/gx/baseline.json` |
| `paper_id_not_null` | Validity | 0 null/empty | PASS (0 null) | `data/quality/gx/baseline.json` |
| `paper_id_unique` | Uniqueness | 0 duplicate | PASS (0 duplicate) | `data/quality/gx/baseline.json` |
| `title_not_null` | Validity | 0 blank title | PASS (0 blank) | `data/quality/gx/baseline.json` |
| `summary_length` | Completeness | $\ge 40$ chars | PASS (0 short) | `data/quality/gx/baseline.json` |
| `freshness` | Timeliness | $\le 180$ days | PASS (0 stale) | `data/quality/freshness_report.json` |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.csv` |
| Timestamp mới nhất | 2026-08-01 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | Fresh |
| Lý do | Toàn bộ 24 bài báo đều có ngày xuất bản trong vòng 180 ngày trở lại đây. |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop latest records | Xóa 20% bài báo mới nhất | 5 records | Cảnh báo stale date | Hit rate giảm do thiếu ngữ cảnh | Nạp lại từ `crossref_records.json` |
| Blank summary | Xóa tóm tắt của một số bài | 5 records | Fail check `summary_length` | Agent trả lời sai/không có context | Phục hồi tóm tắt từ raw JSON |
| Inject noise | Chèn chuỗi rác `[REDACTED]` | 4 records | Không fail check thô nhưng giảm Token F1 | Token F1 sụt giảm | Clean lại văn bản từ nguồn gốc |
| Truncate title | Cắt còn 50% tiêu đề và thêm dấu `…` | 5 records | Có thể làm exact-title lookup thất bại | Giảm khả năng tìm đúng tài liệu | Phục hồi title từ raw JSON |
| Stale publication date | Lùi ngày xuất bản 365 ngày | 4 records trực tiếp; quality phát hiện 6 dòng stale sau duplicate | Fail check `freshness` | Freshness status chuyển thành Stale | Parse lại đúng timestamp gốc |
| Duplicate rows | Nhân bản một số dòng | 3 records | Fail check `paper_id_unique` | Tốn token & gây nhiễu ranking | Dedupe theo `paper_id` |

Corruption log:
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ 6 loại corruption, random seed cố định trong code, số record được yêu cầu/tác động và số lượng dòng thay đổi từ 24 xuống 22.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy:**
Quy trình Repair không thực hiện sửa tay hoặc vá file kết quả. Thay vào đó, hàm `build_clean_dataframe` được gọi lại trực tiếp trên tập dữ liệu thô ban đầu (`data/raw/crossref_records.json`), chạy lại toàn bộ quy trình làm sạch và phân tích đặc trưng chuẩn, giúp dữ liệu được phục hồi 100% nguyên bản.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | 100.0% | 50.0% | 100.0% | 🔻 -50.0% | 🟢 +50.0% | Phục hồi hoàn toàn về 100% |
| `mean_token_f1` | 1.000 | 0.438 | 1.000 | 🔻 -0.562 | 🟢 +0.562 | Phục hồi hoàn toàn về 1.000 |
| `judge_accuracy` | 100.0% | 43.8% | 100.0% | 🔻 -56.2% | 🟢 +56.2% | Fallback heuristic phục hồi về 100% |
| `mean_judge_score` | 5.000 | 2.750 | 5.000 | 🔻 -2.250 | 🟢 +2.250 | Điểm fallback heuristic phục hồi về 5.0 |
| Quality checks pass/fail | 6 / 0 | 3 / 3 | 6 / 0 | 🔻 3 checks fail | 🟢 Pass 100% (6/6) | Khôi phục toàn bộ quality checks |
| Freshness status | Fresh | Stale | Fresh | 🔻 Chuyển thành Stale | 🟢 Trở lại trạng thái Fresh | Phục hồi độ tươi dữ liệu |

**Hai kết luận có quan hệ nhân quả:**
1. **Data Corruption $\rightarrow$ Observability Signal $\rightarrow$ Agent Performance:** Khi tiến hành xóa summary và chèn nhiễu, bài check `summary_length` chuyển sang `FAIL` và `freshness` báo `Stale`. Đồng thời, `retrieval_hit_rate` của RAG Agent giảm 50% và điểm judge heuristic giảm từ 5.0 xuống 2.75.
2. **Repair Action $\rightarrow$ Quality Recovery $\rightarrow$ Agent Recovery:** Việc thực hiện re-cleaning dữ liệu từ nguồn gốc `data/raw/` đã đưa Quality Pass Rate trở lại 100%, đồng thời khôi phục `retrieval_hit_rate` và `judge_accuracy` về lại 100%.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Trong lần chạy đầu tiên, script dừng ở bước Data Quality do file `src/observability/quality.py` chưa được implement.
- **Nguyên nhân:** Thiếu sự đồng bộ thời điểm push code giữa các thành viên.
- **Cách xử lý:** Trưởng nhóm đã phân định rõ ranh giới module, chờ Thành viên 4 hoàn thiện code `quality.py`, `reporting.py`, `corruption.py` và cho re-run lại script end-to-end.
- **Cách xác minh:** Chạy `uv run python script/run_corruption_flow.py` và kiểm tra file `data/reports/corruption_report.md` xuất ra thành công.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Quy mô dữ liệu nhỏ (24 papers) | Chưa kiểm thử được hiệu năng khi scale lớn | Mở rộng max_results lên 500+ records trong config |
| Đánh giá RAGAS chưa bật mặc định | Chưa có chỉ số Faithfulness chi tiết của Ragas | Bật `RUN_RAGAS=1` khi có môi trường hỗ trợ API key đầy đủ |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (cần rà soát các báo cáo cá nhân còn lại trước khi nộp).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
