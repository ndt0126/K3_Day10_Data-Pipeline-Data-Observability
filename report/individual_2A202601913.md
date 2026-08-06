# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin                     | Nội dung                                     |
| ------------------------------ | --------------------------------------------- |
| Họ và tên                   | Lại Duy Đông                               |
| MSSV                           | 2A202601913                                   |
| Khóa/Lớp                     | K3                                            |
| Tên nhóm                     | Nhóm B4                                      |
| Vai trò chính                | Thành viên 2 — Data Model & Eval Set Owner |
| Repository                     | `K3_Day10_Data-Pipeline-Data-Observability` |
| Ngày hoàn thành phần việc | 2026-08-06                                    |

## 2. Vai trò và phạm vi công việc

Role 2 nhận raw-record snapshot theo contract của Thành viên 1, làm sạch dữ liệu thành clean dataset dùng chung và tạo evaluation set cố định cho baseline, corrupted và repaired.

| Module/deliverable             | File/hàm phụ trách                                      | Input nhận vào                                                 | Output bàn giao                                                  | Trạng thái |
| ------------------------------ | ---------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------- | ------------ |
| Cleaning & feature engineering | `src/ingestion/cleaning.py` — `build_clean_dataframe` | Danh sách`PaperRecord` từ `data/raw/crossref_records.json` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Evaluation-set generation      | `src/evaluation/testset.py` — `build_test_set`        | Clean dataframe                                                  | `data/eval/test_set.json`                                       | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện          | File/hàm/artifact liên quan                                                                      | Kết quả bàn giao                            | Cách xác minh                                                      |
| ------------------------------------ | -------------------------------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------- |
| Lọc và chuẩn hóa raw records     | `src/ingestion/cleaning.py`                                                                      | 24 clean records                               | Kiểm tra`paper_id` unique/non-null và clean schema               |
| Tạo feature cho index/observability | `text_for_embedding`, `authors_joined`, `categories_joined`, `summary_chars`, `age_days` | Đủ cột contract cho Role 3 và Role 4       | Đọc lại`papers_clean.json` sau khi ghi                          |
| Đóng băng evaluation set          | `data/eval/test_set.json`                                                                        | 16 samples: summary, authors, date, categories | Kiểm tra mọi`ground_truth_doc_ids` tồn tại trong clean dataset |

Artifact cụ thể đã tạo:

- `data/clean/papers_clean.csv`
- `data/clean/papers_clean.json`
- `data/eval/test_set.json`

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Raw data từ Crossref có thể thiếu field, chứa chuỗi không chuẩn hoặc không có category. Role 2 phải tạo một schema ổn định để vector index, evaluator và quality checks đều sử dụng cùng một nguồn dữ liệu sạch.

### Cách triển khai

`build_clean_dataframe` chỉ giữ record có `paper_id`, title, summary và ngày published hợp lệ. Hàm chuẩn hóa whitespace; chuẩn hóa danh sách authors/categories; loại trùng theo `paper_id`; ưu tiên bản ghi có `updated` mới hơn và summary dài hơn. Sau đó hàm tạo `text_for_embedding` gồm title, authors, categories, ngày xuất bản và summary; đồng thời tính `age_days` từ ngày chạy pipeline.

Vì 24 raw records hiện tại không có Crossref `subject`, `categories_joined` được gán fallback minh bạch là `General`, trùng với `primary_category` đã khai báo. Nhờ vậy downstream contract không có category rỗng và câu hỏi category trong evaluation set có ground truth rõ ràng.

`build_test_set` chọn ổn định bốn clean documents theo `paper_id` và tạo bốn dạng câu hỏi factual cho mỗi document: summary, authors, date và categories. Mỗi sample lưu `ground_truth_doc_ids` là `paper_id` thật, không tạo ID giả.

### Input, output và contract

| Thành phần            | Mô tả                                                                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | JSON list`PaperRecord` từ `data/raw/crossref_records.json`                                                                                                            |
| Output clean            | CSV/JSON có`paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`, `abs_url`, `pdf_url` |
| Output evaluation       | JSON có`id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`                                                                                |
| Module phụ thuộc      | `src/ingestion/crossref.py`, `src/core/utils.py`                                                                                                                       |
| Module sử dụng output | `src/retrieval/index.py`, `src/evaluation/metrics.py`, `src/observability/quality.py`                                                                                |
| Điều kiện lỗi       | Thiếu cột contract, ít hơn bốn clean documents hoàn chỉnh hoặc`ground_truth_doc_ids` không tồn tại                                                            |

### Cách xác minh

Kết quả kiểm tra artifact thực tế:

- Raw records: 24.
- Clean records: 24; `paper_id` unique và không rỗng.
- Evaluation set: 16 samples, bao phủ đủ bốn `question_type`.
- Mọi `ground_truth_doc_ids` trong `test_set.json` đều thuộc tập `paper_id` của clean dataset.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref không trả field `subject` cho cả 24 records, làm `categories_joined` rỗng và không thể tạo câu hỏi category có ground truth đáng tin cậy.
- **Các phương án đã cân nhắc:** Bỏ toàn bộ câu hỏi category; loại các record không có category; dùng fallback category có nhãn rõ ràng.
- **Phương án đã chọn:** Dùng `General` làm fallback trong `primary_category` và `categories_joined`.
- **Lý do:** Giữ được toàn bộ dữ liệu hợp lệ, vẫn cho downstream một giá trị không rỗng, đồng thời không nhầm fallback này là subject gốc của Crossref.
- **Bằng chứng:** Sau khi áp dụng, 24/24 records có `categories_joined`; `test_set.json` được tạo thành công với 16 samples.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `ValueError: At least 4 complete clean documents are required to build the evaluation set; found 0.`
- **Nguyên nhân gốc:** `categories_joined` trống vì raw Crossref response không có `subject`, khiến mọi record không đạt điều kiện dữ liệu đầy đủ cho evaluation set.
- **Cách xử lý:** Sửa cleaning rule để dùng `primary_category`/`General` làm fallback cho `categories_joined`, sau đó tạo lại clean dataset và evaluation set.
- **Cách xác minh sau khi sửa:** Tạo thành công 24 clean records và 16 evaluation samples; toàn bộ ground-truth document IDs hợp lệ.
- **Điều học được:** Cần kiểm tra distribution của field nguồn thật trước khi biến field đó thành điều kiện bắt buộc của data contract.

## 7. Hiểu biết về luồng end-to-end

1. Crossref được Role 1 fetch và lưu raw response/raw records. Role 2 làm sạch các records đó, tạo feature embedding rồi bàn giao clean dataset cho Role 3 xây Chroma index.
2. Evaluation set liên kết câu hỏi với `ground_truth_doc_ids`. Evaluator so sánh document IDs retrieve được với IDs này để tính retrieval hit rate, đồng thời dùng ground truth để chấm câu trả lời.
3. Quality checks kiểm tra tính hợp lệ/cấu trúc như null, duplicate và row count. Freshness monitoring dùng `published`/`age_days` để đánh giá độ mới của corpus.
4. Baseline, corrupted và repaired phải dùng cùng test set để metric thay đổi chỉ phản ánh dữ liệu/index, không phản ánh việc thay đổi câu hỏi hay ground truth.
5. Repair chỉ được coi là thành công khi cleaned/repaired artifact được tái tạo từ raw source và metrics, quality/freshness signals được đối chiếu với baseline/corrupted.

## 8. Phân tích kết quả

Role 2 đã kiểm tra data contract và evaluation-set artifact. Các metrics baseline/corrupted/repaired chưa được điền ở thời điểm báo cáo này vì pipeline index, evaluation và corruption thuộc các bước tích hợp tiếp theo; không có metric nào được suy diễn hoặc ghi nhận là đã chạy.

## 9. Điều học được và hướng cải thiện

1. Clean-data contract phải được chốt trước khi index/evaluation chạy song song.
2. Missing field từ nguồn thực tế cần được đo và xử lý minh bạch, không giả định mọi API record đều đầy đủ.
3. Ground truth phải trỏ đến `paper_id` thật để retrieval metrics có thể audit.

Nếu có thêm thời gian, có thể ghi riêng cleaning-rejection log thành artifact JSON để theo dõi lý do loại record qua từng pipeline run.

## 10. Cam kết của thành viên

- [X] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của Role 2.
- [X] Mọi kết luận về Role 2 đều có artifact hoặc kết quả kiểm tra để đối chiếu.
- [X] Không ghi “đã chạy thành công” cho baseline/corruption metrics chưa được kiểm chứng.
- [X] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** [Họ và tên]
**Ngày xác nhận:** 2026-08-06
