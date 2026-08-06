# Role 2 — Hoàn thành công việc

## Vai trò

**Data Model & Eval Set Owner**

Phạm vi: làm sạch dữ liệu, feature engineering và tạo bộ câu hỏi đánh giá cố định.

## Đầu việc đã hoàn thành

- Hoàn thiện `src/ingestion/cleaning.py`.
  - Lọc record thiếu `paper_id`, title, summary hoặc ngày published không hợp lệ.
  - Chuẩn hóa title, summary, authors và categories.
  - Loại duplicate theo `paper_id`, ưu tiên bản ghi mới hơn và có summary đầy đủ hơn.
  - Tạo các feature: `authors_joined`, `categories_joined`, `summary_chars`, `age_days` và `text_for_embedding`.
  - Dùng `General` làm category fallback minh bạch khi Crossref không trả về `subject`.
- Hoàn thiện `src/evaluation/testset.py`.
  - Tạo test set có tính tái lập từ clean dataset.
  - Mỗi câu hỏi có `id`, `question_type`, `question`, `ground_truth` và `ground_truth_doc_ids`.
  - Bao phủ bốn loại câu hỏi: summary, authors, date và categories.
- Tạo các artifact bàn giao từ raw snapshot của Role 1.
  - `data/clean/papers_clean.csv`
  - `data/clean/papers_clean.json`
  - `data/eval/test_set.json`

## Kết quả bàn giao đã kiểm tra

- Raw records: 24.
- Clean records: 24, `paper_id` không trùng và không rỗng.
- Evaluation set: 16 samples (4 tài liệu × 4 question types).
- Mọi `ground_truth_doc_ids` trong test set đều tồn tại trong clean dataset.
- Clean dataset có đủ các field contract: `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`, `abs_url`, `pdf_url`.
