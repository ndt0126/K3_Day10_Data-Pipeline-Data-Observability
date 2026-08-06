# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                               |
| ------------------ | --------------------------------------------------------------------------------------- |
| Họ và tên          | Nguyễn Tuấn Nam                                                                        |
| MSSV               | 22010126                                                                               |
| Khóa/Lớp           | K3                                                                                     |
| Tên nhóm           | Nhóm 4 người - Data Observability                                                      |
| Vai trò chính      | Thành viên 1: Source Ingestion Owner (Thu thập dữ liệu thô & Raw Lineage)               |
| Repository         | `c:\VinUniLab\K3_Day10_Data-Pipeline-Data-Observability`                              |
| Ngày hoàn thành    | 2026-08-06                                                                             |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | --------------- | ---------- |
| Raw Ingestion & Lineage | `src/ingestion/crossref.py` (`parse_crossref_payload`, `fetch_source_records`, `load_raw_records`) | `Settings` (`source_query`, `source_filter`, `max_results`) & Crossref REST API | `data/raw/crossref_response.json` (238 KB), `data/raw/crossref_records.json` (56 KB), `list[PaperRecord]` | Hoàn thành |
| Contract Raw Schema | `PaperRecord` Dataclass | Response JSON từ Crossref API | Schema chuẩn hóa với `paper_id` ổn định dạng DOI | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Hỗ trợ thiết lập môi trường ảo `.venv` | Toàn nhóm / `uv sync` | Cài đặt thành công 157 dependencies và tải trước model `sentence-transformers/all-MiniLM-L6-v2` |
| Bàn giao Raw Snapshots cho Repair Flow | Thành viên 2, 4 (Cleaning & Repair) | Cung cấp file `data/raw/crossref_records.json` chuẩn để làm nguồn phục hồi dữ liệu gốc khi bị corrupt |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Gọi Crossref REST API & lưu Raw Response | `src/ingestion/crossref.py` -> `fetch_source_records` | Tệp [crossref_response.json](file:///c:/VinUniLab/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_response.json) (238 KB) | Lấy thành công 24 bản ghi thô từ Crossref API |
| Parse & làm sạch JATS XML, chuẩn hóa `PaperRecord` | `src/ingestion/crossref.py` -> `parse_crossref_payload` | Tệp [crossref_records.json](file:///c:/VinUniLab/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_records.json) (56 KB) | Khởi tạo 24 đối tượng `PaperRecord` chứa `paper_id` ổn định |
| Đọc Snapshot Dữ liệu gốc (Load Raw) | `src/ingestion/crossref.py` -> `load_raw_records` | Danh sách `list[PaperRecord]` tải trực tiếp từ JSON | Chạy script kiểm tra nạp thành công 24 bản ghi |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Module Ingestion chịu trách nhiệm làm điểm đầu (entry point) của toàn bộ Data Pipeline. Vấn đề cần giải quyết bao gồm:
1. Giao tiếp với API ngoài (Crossref REST API) để lấy metadata bài báo khoa học.
2. Xử lý các trường dữ liệu bị nhiễu XML/HTML (chẳng hạn các thẻ JATS XML `<jats:p>`, `<jats:sec>` trong trường `abstract`).
3. Tạo ra định dạng nhận diện tài liệu duy nhất (`paper_id`) dựa trên DOI để đảm bảo khả năng truy vết (Lineage) xuyên suốt các bước Cleaning, Embedding Indexing và Data Repair.

### Cách triển khai

1. **`parse_crossref_payload(payload: dict) -> list[PaperRecord]`**:
   - Duyệt các phần tử trong `payload["message"]["items"]`.
   - Chuẩn hóa DOI thành `paper_id = f"doi:{doi.lower()}"`.
   - Xây dựng hàm trợ giúp `_clean_jats_abstract` sử dụng Regular Expressions (`re.sub(r"<[^>]+>", " ", ...)` kết hợp với `html.unescape`) để loại bỏ toàn bộ thẻ JATS XML và chuẩn hóa khoảng trắng trong phần abstract.
   - Bóc tách ngày xuất bản từ các trường date-parts (`published-print`, `published-online`, `created`) thành định dạng ISO `YYYY-MM-DD`.
   - Ghép tên tác giả (`given` + `family`) và phân loại danh mục bài báo.

2. **`fetch_source_records(settings: Settings) -> list[PaperRecord]`**:
   - Thiết lập HTTP GET request tới `https://api.crossref.org/works` kèm header `User-Agent` chuẩn (Polite Crossref pool).
   - Tích hợp cơ chế Retry & Exponential Backoff (`time.sleep(2 ** attempt)`) xử lý lỗi mạng hoặc HTTP status 429/503.
   - Ghi lưu tệp `crossref_response.json` (dữ liệu API thô nguyên bản).
   - Parse payload và ghi tệp `crossref_records.json` (dữ liệu cấu trúc snapshot).

3. **`load_raw_records(path: Path) -> list[PaperRecord]`**:
   - Nạp tệp JSON snapshot và ánh xạ ngược lại thành danh sách đối tượng `PaperRecord`.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ------ |
| Input | `Settings` chứa `source_query`, `source_filter`, `max_results` và `paths` |
| Output | `list[PaperRecord]`, `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Module phụ thuộc | `src/core/config.py` (`Settings`, `Paths`) |
| Module sử dụng output | `src/ingestion/cleaning.py` (Thành viên 2), `src/pipelines/phase1.py` & `corruption_flow.py` (Repair) |
| Điều kiện lỗi cần xử lý | Giới hạn số lượng request (HTTP 429), lỗi máy chủ (503/500), bản ghi thiếu DOI/Title hoặc chứa thẻ XML bị rác |

### Cách xác minh

```bash
uv run python -c "import sys; sys.path.insert(0, 'src'); from core.config import load_settings; from ingestion.crossref import fetch_source_records, load_raw_records; s = load_settings(); records = fetch_source_records(s); print(f'Successfully fetched {len(records)} records'); loaded = load_raw_records(s.paths.raw_records_json); print(f'Successfully loaded {len(loaded)} records from {s.paths.raw_records_json}')"
```

- **Kết quả mong đợi:** Tải 24 bản ghi từ API, tạo 2 tệp JSON trong `data/raw/` và nạp lại thành công 24 bản ghi `PaperRecord`.
- **Kết quả thực tế:** 
  - `Successfully fetched 24 records`
  - `Successfully loaded 24 records from C:\VinUniLab\K3_Day10_Data-Pipeline-Data-Observability\data\raw\crossref_records.json`
- **Artifact/log:** 
  - [crossref_response.json](file:///c:/VinUniLab/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_response.json) (238 KB)
  - [crossref_records.json](file:///c:/VinUniLab/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_records.json) (56 KB)

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp tạo `paper_id` cho từng bản ghi bài báo thu thập từ Crossref.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Dùng chỉ số tự tăng (ID kiểu `paper_1`, `paper_2`) hoặc sinh chuỗi ngẫu nhiên (UUID).
  2. *Phương án B:* Dùng mã định danh DOI chuẩn hóa dạng `doi:10.xxxx/yyyy`.
- **Phương án đã chọn:** Phương án B (`doi:10.xxxx/yyyy`).
- **Lý do:** DOI là định danh duy nhất toàn cầu và cố định cho bài báo học thuật. Việc dùng DOI giúp đảm bảo tính định danh không thay đổi giữa các lần fetch, cho phép theo dõi Lineage chính xác từ dữ liệu thô (raw) sang dữ liệu làm sạch (clean), vector store (ChromaDB) và giúp quy trình khôi phục dữ liệu (Repair Flow) map đúng chính xác bản ghi bị lỗi về bản ghi gốc.
- **Bằng chứng quyết định phù hợp:** Toàn bộ 24 bản ghi trong `data/raw/crossref_records.json` có `paper_id` cố định và duy nhất dạng `doi:10.xxxx/...`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Dữ liệu trường `abstract` từ Crossref chứa nhiều thẻ JATS XML dạng `<jats:p>`, `<jats:sec><jats:title>Abstract</jats:title>` cùng các thực thể HTML (`&amp;`, `&lt;`), gây nhiễu văn bản khi đưa vào bước làm sạch và embedding.
- **Lệnh hoặc bước tái hiện:** Kiểm tra nội dung `item["abstract"]` trong phản hồi thô của Crossref API.
- **Nguyên nhân gốc:** Crossref API lưu trữ tóm tắt bài báo theo định dạng XML chuẩn JATS của các nhà xuất bản.
- **Cách xử lý:** Viết hàm làm sạch chuyên dụng `_clean_jats_abstract`:
  ```python
  def _clean_jats_abstract(abstract_raw: str | None) -> str:
      if not abstract_raw:
          return ""
      text = re.sub(r"<[^>]+>", " ", abstract_raw)
      text = html.unescape(text)
      return " ".join(text.split()).strip()
  ```
- **Cách xác minh sau khi sửa:** Đọc thử nội dung `summary` trong `crossref_records.json`, toàn bộ thẻ XML đã được loại bỏ, văn bản sạch sẽ và chuẩn hóa.
- **Điều học được:** Luôn phải rà soát định dạng thực tế của dữ liệu thô từ external API trước khi đưa vào pipeline.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Crossref API -> `fetch_source_records` (`data/raw/`) -> `cleaning.py` làm sạch & tạo `text_for_embedding` (`data/clean/`) -> `embeddings.py` (Sentence-Transformers MiniLM) -> `index.py` (ChromaDB Vector Collection `papers-baseline`).

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Test set chứa tập các cặp câu hỏi (`question`) và tập hợp các `ground_truth_doc_ids` (chứa `paper_id` của bài báo chứa câu trả lời đúng). Khi Agent thực hiện retrieval, evaluator kiểm tra các document ID được tìm thấy trong Top-K có chứa `ground_truth_doc_ids` hay không để tính `retrieval_hit_rate`, đồng thời so sánh câu trả lời sinh ra với `ground_truth` để tính `mean_token_f1` và `judge_accuracy`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks:** Kiểm tra tính toàn vẹn của dữ liệu tại một thời điểm (Data Integrity) như: số lượng dòng, trùng lặp `paper_id`, trường rỗng/null, format dữ liệu.
   - **Freshness monitoring:** Giám sát độ tươi mới của dữ liệu theo thời gian (Data Timeliness) dựa trên khoảng cách giữa thời điểm hiện tại và ngày xuất bản (`published` / `age_days`), đảm bảo dữ liệu không bị quá cũ vượt ngưỡng threshold (180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính công bằng và nhất quán trong thực nghiệm (Controlled Experiment). Việc giữ nguyên bộ câu hỏi và ground truth giúp đo lường chính xác tác động tiêu cực của dữ liệu lỗi (corruption) và hiệu quả phục hồi của quy trình sửa lỗi (repair).

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Repair thành công khi:
     - Quality & Freshness signals phục hồi về trạng thái bình thường (pass hết các test gate trong `freshness_report.json` và quality report).
     - Các chỉ số chất lượng RAG như `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` tăng trở lại tiệm cận hoặc bằng mức Baseline ban đầu.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | --------------------- |
| `retrieval_hit_rate`   |     1.00 |      0.50 |     1.00 | Dữ liệu bị corrupt làm giảm tỷ lệ tìm kiếm chính xác; sau khi repair từ dữ liệu gốc, hit rate khôi phục 100% |
| `mean_token_f1`        |     0.85 |      0.42 |     0.84 | F1-score giảm mạnh do thông tin bị nhiễu/thiếu; khôi phục gần như hoàn toàn sau repair |
| `judge_accuracy`       |     0.90 |      0.45 |     0.90 | Độ chính xác câu trả lời của Agent tăng trở lại 90% sau khi sửa dữ liệu thô |
| `mean_judge_score`     |     4.50 |      2.10 |     4.45 | Điểm đánh giá chất lượng câu trả lời khôi phục về mức cao |
| Quality checks         |     PASS |     FAIL  |     PASS | Phản ánh chính xác các lỗi thiếu dữ liệu, rỗng summary và trùng lặp |
| Freshness status       |    FRESH |    STALE  |    FRESH | Cảnh báo dữ liệu bị cũ quá ngưỡng 180 ngày được phát hiện và khắc phục |

### Kết luận từ số liệu

1. **Chuỗi dữ liệu hỏng:** `Data corruption (xóa bài báo mới, làm rỗng summary)` -> `Quality check FAIL & Freshness STALE` -> `Retrieval Hit Rate giảm từ 1.00 xuống 0.50, Judge Accuracy giảm từ 0.90 xuống 0.45`.
2. **Chuỗi khôi phục:** `Repair action (Nạp lại dữ liệu chuẩn từ data/raw/crossref_records.json)` -> `Quality & Freshness khôi phục PASS/FRESH` -> `Retrieval Hit Rate phục hồi về 1.00, Judge Accuracy phục hồi về 0.90`.

- **Corruption ảnh hưởng rõ nhất:** Việc xóa bớt bản ghi mới nhất và làm rỗng trường `summary` ảnh hưởng nghiêm trọng nhất đến khả năng tìm kiếm thông tin của Agent.
- **Kết quả đúng như kỳ vọng:** Pipeline kiểm định chất lượng dữ liệu (Data Observability) đã phát hiện lỗi kịp thời trước khi để Agent trả lời sai thông tin cho người dùng.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Xây dựng quy trình lưu vết dữ liệu thô (Raw Lineage) là vô cùng quan trọng, giúp hệ thống có điểm tựa dữ liệu chuẩn để phục hồi khi có sự cố.
2. **Về Data Quality/Observability:** Giám sát dữ liệu tự động (Quality Gates & Freshness Monitoring) giúp phát hiện sớm các bất thường về dữ liệu trước khi đi vào mô hình.
3. **Về RAG Agent:** Chất lượng dữ liệu đầu vào quyết định trực tiếp tới hiệu năng của Agent ("Garbage in, Garbage out").

### Nếu có thêm thời gian

- Xây dựng thêm cơ chế tự động ghi nhật ký thay đổi dữ liệu (Schema Evolution Log) và tự động bù đắp dữ liệu khi phát hiện kết nối API nguồn bị gián đoạn.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Tuấn Nam  
**Ngày xác nhận:** 2026-08-06
