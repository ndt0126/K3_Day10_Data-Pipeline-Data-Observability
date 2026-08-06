# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | Nguyễn Đức Trung |
| MSSV | 2A202601725 |
| Khóa/Lớp | K3 |
| Tên nhóm | B4 |
| Vai trò chính | Trưởng nhóm (Pipeline Integrator) |
| Repository | https://github.com/ndt0126/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Configuration & Settings | `src/core/config.py` | Environment variables, `.env` | File cấu hình `Settings` & `Paths` | Hoàn thành |
| Baseline Orchestration | `src/pipelines/phase1.py` | Raw, Clean, Index, Eval modules | Kết quả Phase 1 Baseline pipeline | Hoàn thành |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py` | Clean DF, Raw JSON, Corruption module | Báo cáo so sánh `corruption_report.md` | Hoàn thành |
| Group Report Management | `report/group_report.md` | Kết quả thực thi từ 4 thành viên | Báo cáo nhóm tổng hợp hoàn chỉnh | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đánh giá & Phân công Data Contract | Cả nhóm 5 thành viên | Thống nhất được hợp đồng dữ liệu giữa Ingestion, Cleaning và Evaluation |
| Kiểm tra & Xử lý Git Merge | Thành viên 1, 2 & 4 | Đảm bảo code của cả nhóm được merge và rebase an toàn, không bị mất commit |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng Phase 1 Baseline Pipeline | `src/pipelines/phase1.py` | Running baseline workflow end-to-end | `uv run python script/run_phase1.py` |
| Triển khai Corruption & Repair Flow | `src/pipelines/corruption_flow.py` | Comparison metrics & report | `uv run python script/run_corruption_flow.py` |
| Thiết lập cấu hình dự án | `src/core/config.py` | Load settings, paths, env | `load_settings()` |

Artifacts cụ thể tạo ra:
- `data/results/baseline_metrics.json`
- `data/reports/phase1_report.md`
- `data/reports/corruption_report.md`

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Với vai trò Trưởng nhóm (Pipeline Integrator), tôi phải đảm bảo các module độc lập do 4 thành viên khác viết (Ingestion, Cleaning, Vector Index, Observability) hoạt động hài hòa thành một luồng dữ liệu tự động, không bị đè artifact, có khả năng đo lường tác động của dữ liệu lỗi và phục hồi dữ liệu về mức chuẩn.

### Cách triển khai
- Trong `phase1.py`: Gọi tuần tự `load_settings()` $\rightarrow$ `load_raw_records()` $\rightarrow$ `build_clean_dataframe()` $\rightarrow$ `LocalEmbeddingIndex.build()` $\rightarrow$ `evaluate_pipeline()` $\rightarrow$ `run_data_quality_checks()` $\rightarrow$ `generate_phase1_report()`.
- Trong `corruption_flow.py`: Gọi `corrupt_clean_dataframe()`, re-build index `papers-corrupted`, re-evaluate. Sau đó gọi `load_raw_records()`, re-clean `papers-repaired`, re-build index `papers-repaired`, re-evaluate và sinh báo cáo so sánh `generate_corruption_report()`.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Cấu hình `Settings`, `Paths`, các module trong `src/` |
| Output | Executable scripts `run_phase1.py`, `run_corruption_flow.py`, `baseline_metrics.json`, `corruption_report.md` |
| Module phụ thuộc | All `src/` modules (`ingestion`, `cleaning`, `retrieval`, `evaluation`, `observability`) |
| Module sử dụng output | Giảng viên / Evaluator chấm bài |
| Điều kiện lỗi cần xử lý | Xử lý `NotImplementedError` từ module thành viên khi chưa hoàn thiện code |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 2 script chạy thành công end-to-end không bị throw exception.
- **Kết quả thực tế:** Cả 2 script đều báo `COMPLETED SUCCESSFULLY`.
- **Artifact/log:** `data/reports/corruption_report.md` và `data/results/baseline_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quản lý 3 trạng thái dữ liệu (Baseline, Corrupted, Repaired) mà không làm đè dữ liệu hoặc làm hỏng ChromaDB vector store.
- **Các phương án đã cân nhắc:**
  1. Ghi đè file `papers_clean.csv` và collection ChromaDB cũ ở mỗi bước.
  2. Tạo đường dẫn file riêng biệt (`papers_clean.csv`, `papers_clean_corrupted.csv`, `papers_clean_repaired.csv`) và đặt tên Chroma collection riêng (`papers-baseline`, `papers-corrupted`, `papers-repaired`).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo tính cô lập dữ liệu (data isolation), cho phép truy vết lineage và so sánh kết quả chính xác giữa 3 trạng thái.
- **Bằng chứng quyết định phù hợp:** File `data/reports/corruption_report.md` xuất ra được bảng so sánh trực quan cả 3 cột dữ liệu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement quality checks.` khi chạy `run_phase1.py`.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py`.
- **Nguyên nhân gốc:** Module `quality.py` của Thành viên 4 chưa được implement tại thời điểm test ban đầu.
- **Cách xử lý:** Đã liên hệ và chờ Thành viên 4 đẩy commit `feat(tv4)` hoàn thiện các hàm check chất lượng, sau đó re-run script thành công.
- **Cách xác minh sau khi sửa:** Chạy lại `uv run python script/run_phase1.py` và script hoàn thành 100%.
- **Bài học kỹ thuật:** Cần làm rõ Data Contract và thứ tự phụ thuộc giữa các module trước khi cho chạy script tích hợp.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Crossref API trả về JSON raw $\rightarrow$ `parse_crossref_payload()` biến đổi thành `PaperRecord` $\rightarrow$ `build_clean_dataframe()` chuẩn hóa text và sinh `text_for_embedding` $\rightarrow$ `MiniLMEmbeddings` mã hóa văn bản thành vector $\rightarrow$ Lưu vào ChromaDB Collection HNSW.
2. **Evaluation set và ground-truth document IDs:** `test_set.json` cố định bộ câu hỏi và danh sách `ground_truth_doc_ids` đúng. Khi Agent trả lời, evaluator so sánh tài liệu được retrieve với doc IDs chuẩn để tính $Hit Rate$, và so sánh câu trả lời với ground truth để tính $Token F1$ / $LLM Judge Score$.
3. **Quality checks vs freshness monitoring:** Quality checks kiểm tra tính toàn vẹn của dữ liệu tại một thời điểm (Null, Duplicate, Summary Length), trong khi Freshness Monitoring giám sát thuộc tính thời gian (`published`, `age_days`) để phát hiện dữ liệu lỗi thời.
4. **Vì sao dùng cùng test set:** Đảm bảo tính công bằng khi so sánh. Mọi thay đổi về chỉ số đều phản ánh đúng chất lượng dữ liệu chứ không bị ảnh hưởng do độ khó câu hỏi thay đổi.
5. **Repair thành công:** Được công nhận khi $Hit Rate$ và $Judge Score$ phục hồi về mức ngang với Baseline (100% / 5.0) và Data Quality Pass Rate đạt lại 100%.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 100.0% | 50.0% | 100.0% | Corruption làm sụt 50% khả năng tìm kiếm |
| `mean_token_f1` | 1.000 | 0.438 | 1.000 | Phục hồi hoàn toàn sau khi repair |
| `judge_accuracy` | 100.0% | 43.8% | 100.0% | Tác động dữ liệu xấu làm Agent trả lời sai |
| `mean_judge_score` | 5.000 | 3.0625 | 5.000 | LLM judge giảm khi corrupted và phục hồi về điểm tuyệt đối 5/5 |
| Quality checks | PASS (6/6) | FAIL (3/6) | PASS (6/6) | Phản ánh chính xác sự cố dữ liệu |
| Freshness status | Fresh | Stale | Fresh | Cảnh báo kịp thời khi ngày công bố bị làm cũ |

### Kết luận từ số liệu

1. `Data Corruption` (xóa summary, chèn rác) $\rightarrow$ `Quality check FAIL` $\rightarrow$ `Retrieval hit rate giảm từ 100% xuống 50%`.
2. `Repair action` (nạp lại từ raw) $\rightarrow$ `Quality check PASS 100%` $\rightarrow$ `Agent metric phục hồi về 100%`.

Corruption ảnh hưởng rõ nhất là việc xóa `summary` và chèn chuỗi nhiễu `[REDACTED]`, khiến Vector Index mất đi thông tin cốt lõi làm Agent không thể tìm đúng tài liệu.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Về Data Pipeline:** Quản lý đường ống dữ liệu chặt chẽ từ Raw $\rightarrow$ Clean $\rightarrow$ Embedding là yếu tố sống còn quyết định sự thành bại của hệ thống AI/RAG.
2. **Về Data Observability:** Thường xuyên chạy Quality Checks và Freshness Monitoring giúp phát hiện sớm các bất thường dữ liệu trước khi chúng gây hại cho Model/Agent.
3. **Về ảnh hưởng của Data đến Agent:** "Garbage in, garbage out" - Dữ liệu xấu ngay lập tức làm suy giảm 50% hiệu năng RAG Agent dù mô hình LLM có mạnh đến đâu.

### Nếu có thêm thời gian
Tôi sẽ xây dựng cơ chế tự động hóa Data Observability với Great Expectations và thiết lập Dashboard hiển thị cảnh báo theo thời gian thực (Real-time alerting).

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Trung
**Ngày xác nhận:** 2026-08-06
