# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin          | Nội dung                                                                    |
| ------------------ | --------------------------------------------------------------------------- |
| Họ và tên          | Nguyen Quang Vinh                                                                |
| MSSV               | 2A202601049                                                                      |
| Khóa/Lớp           | K3                                                                          |
| Tên nhóm           | B4                                                         |
| Vai trò chính      | Thành viên 3 — RAG & Agent Operation                                        |
| Repository         | https://github.com/ndt0126/K3_Day10_Data-Pipeline-Data-Observability        |
| Ngày hoàn thành    | 2026-08-06                                                                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Vai trò của tôi là **vận hành** (operation), không phải phát triển module mới. Toàn bộ
`src/retrieval/` (`index.py`, `embeddings.py`, `agent.py`, `llm.py`, `qa.py`) đã được cung cấp sẵn
trong starter và **không chứa `TODO(student)` nào** — cả 12 marker đều nằm ở ingestion, cleaning,
testset, observability, corruption và hai pipeline. Vì vậy tôi **không nhận ownership cho code
trong `src/`**. Phần việc tôi trực tiếp thực hiện là toàn bộ tooling vận hành, kiểm chứng và chạy
đánh giá dưới đây.

| Module/deliverable                | File/hàm phụ trách                                  | Input nhận vào                              | Output bàn giao                                                      | Trạng thái                    |
| --------------------------------- | --------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------- | ----------------------------- |
| Quản lý ChromaDB collections      | `script/check_retrieval.py`, `script/_tv3_common.py` | `data/clean/papers_clean.json` (TV2)        | `data/embeddings/papers_embeddings.json`, collection `papers-baseline` trong `data/chroma/` | Hoàn thành (baseline)         |
| Kiểm chứng LLM provider           | `script/check_llm.py`                               | `.env`                                      | Xác nhận provider + structured output hoạt động                      | Hoàn thành                    |
| Smoke test semantic search/lookup | `script/check_retrieval.py`                         | Clean dataset + index                       | Log kiểm chứng, exit code gate                                       | Hoàn thành (baseline)         |
| Agent demo & hallucination test   | `script/run_agent_demo.py`                          | Index + LLM provider                        | `data/results/agent_demo_answers.json`                               | Hoàn thành                    |
| Thực thi evaluation metrics       | `script/run_evaluation.py`                          | `data/eval/test_set.json` (TV2) + index     | `data/results/baseline_metrics.json`, `baseline_answers.json`        | Hoàn thành (baseline)         |
| Evaluation corrupted/repaired     | `script/run_evaluation.py --all`                    | Corrupted/repaired dataset (TV4)            | `corrupted_metrics.json`, `repaired_metrics.json`, 3 collection phân biệt | Hoàn thành                    |
| Audit tính toàn vẹn metrics       | `script/run_evaluation.py --audit`                  | `*_answers.json`, `*_metrics.json`          | Phát hiện 48/48 verdict dùng fallback judge; kiểm tra metrics khớp answers | Hoàn thành                    |
| RAGAS metrics                     | `RUN_RAGAS=1`                                       | Answers + LLM                               | Trường `ragas` trong metrics JSON                                    | **Chưa chạy**                 |
| Tài liệu vận hành                 | `docs/` (gitignored)                                | —                                           | Runbook, data contract, ghi chú kỹ thuật                             | Hoàn thành                    |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                              | Thành viên/module được hỗ trợ | Kết quả                                                                                                                                |
| ------------------------------------------------------ | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Kiểm chứng Clean Dataset Schema và Evaluation Set       | TV1, TV2                      | Xác nhận 10/10 cột bắt buộc, 16/16 sample đúng contract và đúng nhánh keyword của `qa.py`                                               |
| Cảnh báo NaN trong `pdf_url` khi đọc CSV                | TV2 / mọi người đọc CSV        | 15/24 dòng `pdf_url` rỗng bị `pd.read_csv` chuyển thành NaN; ChromaDB metadata không nhận NaN. JSON đúng, chỉ CSV cần `keep_default_na=False` |
| Cảnh báo giới hạn 256 token của MiniLM                  | TV4 (corruption)              | 20/24 document vượt ngưỡng ~200 từ; corruption thêm nhiễu vào **cuối** summary sẽ nằm trong vùng bị cắt và không tới được vector         |
| Phát hiện `papers_clean_corrupted.json` vi phạm contract | TV4                           | 15/22 dòng có `pdf_url` là `null` thay vì `""`. Baseline và repaired đều đúng, chỉ nhánh corruption sai — pandas ghi `NaN` thành `null` khi xuất JSON |
| Phát hiện LLM judge chưa từng chạy trong pipeline nhóm   | Trưởng nhóm, TV4              | 48/48 verdict ở cả 3 state dùng fallback heuristic; `judge_accuracy` và `mean_judge_score` trong artifact không phải chỉ số LLM        |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                            | File/hàm/artifact liên quan                  | Kết quả bàn giao                                                    | Cách xác minh                              |
| ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------ |
| Build collection `papers-baseline`               | `data/embeddings/papers_embeddings.json`     | 24 vector, 384 chiều, cosine space                                   | `uv run python script/check_retrieval.py`  |
| Kiểm chứng semantic search                       | Log của `check_retrieval.py`                 | 5/5 paper tự truy hồi chính nó ở **rank 1**, score 0.7263–0.8608     | `uv run python script/check_retrieval.py`  |
| Kiểm chứng exact lookup                          | Log của `check_retrieval.py`                 | 5/5 paper resolve bằng cả `paper_id` và title; key sai trả về `None` | `uv run python script/check_retrieval.py`  |
| Kiểm chứng LLM provider + structured output      | Log của `check_llm.py`                       | `openai` / `gpt-4o-mini` PASS cả 5 stage                             | `uv run python script/check_llm.py`        |
| Agent demo + hallucination test                  | `data/results/agent_demo_answers.json`       | 4/4 câu in-corpus có tool call; 3/3 câu out-of-corpus bị từ chối     | `uv run python script/run_agent_demo.py`   |
| Chạy evaluation baseline                         | `data/results/baseline_metrics.json`         | 16 sample, cả 4 metric = 1.0                                         | `uv run python script/run_evaluation.py`   |
| Kiểm chứng judge thật sự là LLM                  | `data/results/baseline_answers.json`         | Lần tôi chạy: 16/16 verdict từ LLM. Lần pipeline của nhóm chạy: 48/48 dùng fallback | Mục "Judge integrity" trong log            |
| Xác minh 3 collection tách biệt                  | `data/embeddings/*.json`                     | `papers-baseline` 24 doc, `papers-corrupted` 22, `papers-repaired` 24 | `uv run python script/check_retrieval.py --all` |
| Chạy evaluation corrupted + repaired             | `corrupted_metrics.json`, `repaired_metrics.json` | hit_rate 1.00 → 0.50 → 1.00; token_f1 1.0000 → 0.4375 → 1.0000  | `uv run python script/run_evaluation.py --all` |
| Audit tính toàn vẹn artifact                     | Toàn bộ `data/results/`                      | Phát hiện fallback judge; xác nhận metrics khớp answers ở cả 3 state | `uv run python script/run_evaluation.py --audit` |

Một output cụ thể mà phần việc của tôi tạo ra:

`data/results/agent_demo_answers.json` — chứa 7 lượt hỏi agent kèm **toàn bộ tool call** đã ghi
lại. Bốn câu in-corpus đều gọi `lookup_paper` hoặc `semantic_search_papers` trước khi trả lời (agent
không tự bịa mà thật sự truy hồi). Ba câu out-of-corpus hỏi về những bài báo không tồn tại
(*"Quantum Tunneling Effects in Avian Magnetoreception"*, …) và agent đều trả lời *"I couldn't find
a paper titled … in the indexed corpus"*. Đây là bằng chứng trực tiếp cho Mục 5 của rubric: agent
bị ràng buộc vào corpus chứ không hallucinate.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Tầng retrieval nằm ở **giữa** pipeline: nó nhận cleaned dataset từ TV2 và cung cấp index cho
evaluation. Nếu tầng này sai, mọi metric phía sau đều vô nghĩa nhưng **vẫn ra số trông hợp lý** —
đây mới là rủi ro thật. Ba chế độ hỏng âm thầm mà tôi phải chặn:

1. **Collection bị ghi đè.** `LocalEmbeddingIndex.build()` suy ra tên collection từ đường dẫn
   manifest qua `_derive_collection_name()`. Nếu gọi mà không truyền đúng path cho từng state, cả ba
   state đều ghi vào `papers-baseline`; khi đó corrupted metrics thực chất được đo trên vector của
   baseline và toàn bộ thí nghiệm vô nghĩa mà không có lỗi nào được ném ra.
2. **NaN trong metadata.** ChromaDB chỉ nhận `str/int/float/bool` trong metadata. Một `NaN` từ ô CSV
   rỗng sẽ làm hỏng bước index — hoặc tệ hơn, lọt vào metadata dưới dạng float NaN.
3. **Judge giả.** `metrics.py::_judge_answer` bọc lời gọi LLM trong `except Exception` trống rồi
   fallback sang heuristic token-F1. API key hỏng vẫn cho ra `judge_accuracy` trông bình thường.

### Cách triển khai

Tôi không sửa `src/` (đó là contract surface dùng chung) mà viết tooling vận hành trong `script/`:

- `check_llm.py` chạy **trước mọi thứ**: kiểm tra credential, dựng client, gọi thật một câu, và
  quan trọng nhất là thử `with_structured_output(JudgeVerdict)` — chính API mà judge dùng.
- `check_retrieval.py` xác thực Clean Dataset Schema, đo mức truncation, build/load collection,
  **assert tên collection khớp state và số vector khớp số dòng**, rồi chạy self-retrieval và lookup
  (kèm một case âm: key vô nghĩa phải trả `None`). Exit code 1 khi có lỗi để dùng làm gate.
- `run_agent_demo.py` ghi lại tool call, chia câu hỏi thành hai nhóm in-corpus / out-of-corpus.
- `run_evaluation.py` xác thực Evaluation Set contract, chạy `evaluate_pipeline` với đúng output
  path cho từng state, **đếm số verdict mang marker `"Fallback heuristic judge"`**, và tách metric
  theo `question_type` để thấy nhánh nào suy giảm trước.

### Input, output và contract

| Thành phần                | Mô tả                                                                                                                             |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Input                     | `data/clean/papers_clean.json` (10 cột theo Clean Dataset Schema), `data/eval/test_set.json` (5 trường), `.env`                    |
| Output                    | `data/embeddings/papers_embeddings*.json`, collection trong `data/chroma/`, `agent_demo_answers.json`, `*_metrics.json`, `*_answers.json` |
| Module phụ thuộc          | `src/ingestion/cleaning.py` (TV2), `src/evaluation/testset.py` (TV2), `src/retrieval/*`, `src/evaluation/metrics.py`               |
| Module sử dụng output     | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` (Trưởng nhóm), `src/observability/reporting.py` (TV4)                |
| Điều kiện lỗi cần xử lý   | Thiếu cột bắt buộc; NaN trong metadata; collection name sai state; thiếu index khi `load()`; provider không hỗ trợ structured output; state chưa có dữ liệu (bỏ qua, không fail) |

### Cách xác minh

```bash
uv run python script/check_llm.py
uv run python script/check_retrieval.py
uv run python script/run_agent_demo.py
uv run python script/run_evaluation.py
```

- **Kết quả mong đợi:** provider PASS; 24 vector 384 chiều trong đúng collection `papers-baseline`;
  mọi paper tự truy hồi được; agent từ chối câu hỏi ngoài corpus; baseline metrics được ghi ra file
  và judge là LLM thật.
- **Kết quả thực tế:** đúng như mong đợi. `check_llm.py` PASS cả 5 stage. `check_retrieval.py` PASS
  (5/5 self-retrieval rank 1, 5/5 lookup, 24/24 vector). `run_agent_demo.py`: 4/4 grounded, 3/3
  refused. `run_evaluation.py`: 16 sample, `retrieval_hit_rate` = 1.0, `mean_token_f1` = 1.0,
  `judge_accuracy` = 1.0, `mean_judge_score` = 5.0, 16/16 verdict từ LLM.
- **Artifact/log:** `data/embeddings/papers_embeddings.json`, `data/results/agent_demo_answers.json`,
  `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`. Không chứa secret;
  `.env` nằm trong `.gitignore`.

**Lưu ý trung thực về baseline:** cả bốn metric bằng đúng 1.0 là **hiệu ứng trần**, không phải bằng
chứng rằng agent "hiểu" ngôn ngữ. `qa.py::_extract_answer` là bộ trích xuất theo luật, còn
`ground_truth` được TV2 sinh ra từ chính những cột mà bộ trích xuất đó trả về, nên chuỗi khớp tuyệt
đối. Thêm nữa, corpus chỉ có 24 document với `top_k=4`. Điều này **không làm hỏng thí nghiệm** — trái
lại, một trần sạch giúp mọi thay đổi sau corruption đều quy được về chất lượng dữ liệu chứ không
phải nhiễu của model. Nhưng con số 1.0 phải được đọc đúng như vậy trong báo cáo nhóm.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `papers_clean.csv` có 15/24 dòng `pdf_url` rỗng. `pd.read_csv` mặc định chuyển ô
  rỗng thành `NaN`, mà `pdf_url` là một trong 8 trường được đẩy thẳng vào ChromaDB metadata — nơi
  chỉ nhận giá trị scalar.
- **Các phương án đã cân nhắc:**
  1. Yêu cầu TV2 sửa `cleaning.py`. Nhưng file JSON của TV2 **đã đúng** (lưu chuỗi rỗng) — lỗi nằm ở
     cách đọc, không phải cách ghi.
  2. Đọc CSV rồi `fillna("")` ngay trong hàm load.
  3. Ưu tiên đọc JSON, fallback sang CSV với `keep_default_na=False`, và tách riêng bước sửa dữ liệu.
- **Phương án đã chọn:** phương án 3.
- **Lý do:** phương án 2 nhìn có vẻ gọn nhưng **sai về mặt báo cáo**. Bản nháp đầu tiên của tôi làm
  đúng như vậy: `load_clean_frame()` tự động `fillna("")` khi load. Hậu quả là `validate_contract()`
  chạy sau đó **luôn báo PASS**, kể cả trên dữ liệu thật sự hỏng — vì chính hàm load đã lặng lẽ vá
  dữ liệu trước khi kiểm tra. Đó đúng là kiểu "report không khớp artifact" mà Rubric trừ điểm. Tôi
  tách thành hai bước: `load_clean_frame()` **không sửa gì**, còn `coerce_metadata()` là lời gọi
  tường minh và **in ra từng thay đổi** kèm dòng `COERCED ... <-- raise this with the artifact's
  owner`.
- **Bằng chứng quyết định phù hợp:** chạy `validate_contract()` trên frame đã cố tình chèn NaN cho
  ra đúng danh sách lỗi (`summary has 1 null value(s)`, `pdf_url has 1 null value(s)`); sau khi gọi
  `coerce_metadata()` thì PASS và trả về đúng 2 note mô tả thay đổi. Dữ liệu gốc không bị sửa
  (copy-on-write).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `run_agent_demo.py` báo `out-of-corpus refusals 0/3` kèm nhãn `[HALLUCINATED?]`
  cho cả ba câu — tức là agent bị nghi ngờ bịa câu trả lời về những bài báo không tồn tại.
- **Lệnh tái hiện:** `uv run python script/run_agent_demo.py`
- **Nguyên nhân gốc:** **lỗi nằm ở code của tôi, không phải ở agent.** Đọc câu trả lời đã lưu trong
  `agent_demo_answers.json` thì thấy agent trả lời hoàn toàn đúng: *"I couldn't find a paper titled
  … in the indexed corpus."* Danh sách `REFUSAL_MARKERS` của tôi có `"not find"`, `"cannot"`,
  `"can't"` nhưng **thiếu dạng rút gọn `"couldn't find"`** — đúng cách diễn đạt mà `gpt-4o-mini`
  dùng. Chuỗi `"couldn't find"` không chứa substring `"not find"`, nên cả ba đều trượt. Đây là false
  negative của heuristic, không phải hallucination.
- **Cách xử lý:** bổ sung các biến thể rút gọn và đầy đủ của cùng một động từ vào
  `REFUSAL_MARKERS` (`couldn't find`, `could not find`, `didn't find`, `did not find`, `isn't`,
  `is not`, `no specific`), kèm comment giải thích lý do để người sau không lặp lại.
- **Cách xác minh sau khi sửa:** chạy lại bộ marker mới trên **chính file
  `agent_demo_answers.json` đã lưu** (không cần gọi lại LLM): 3/3 câu được nhận diện là refusal,
  marker khớp là `"couldn't find"` ở cả ba.
- **Điều học được:** một heuristic keyword không được coi là bằng chứng. Nếu tôi chỉ đọc con số
  `0/3` và ghi vào báo cáo, tôi đã kết luận sai về hành vi của agent theo hướng bất lợi. Bài học
  rộng hơn: **luôn đọc artifact thô trước khi tin vào chỉ số tổng hợp** — đúng tinh thần của cả bài
  lab này. Vì vậy script vẫn in ra `WARN ... read the answers before reporting`.

### Blocker thứ hai: ChromaDB store hỏng sau khi merge

- **Triệu chứng nguyên văn:** `chromadb.errors.NotFoundError: Collection [papers-baseline] does not
  exist` — trong khi `data/embeddings/papers_embeddings.json` vẫn khai báo đúng tên collection đó.
- **Lệnh tái hiện:** `uv run python script/check_retrieval.py --all` ngay sau `git pull origin main`.
- **Nguyên nhân gốc:** `data/chroma/` là **binary**. Git không merge được `chroma.sqlite3` theo dòng
  nên đã lấy một phía, trong khi thư mục segment `8fd0a215-…/` đến từ phía còn lại. Kết quả là một
  store không nhất quán: truy vấn trực tiếp bảng `collections` trong sqlite vẫn thấy dòng
  `papers-baseline`, nhưng `get_collection()` của ChromaDB không mở được. Cả ba manifest đều trỏ tới
  collection không dùng được, nên **không state nào evaluate được**.
- **Cách xử lý:** thêm cờ `--reset-store` cho `check_retrieval.py` — xóa sạch `data/chroma/` (giữ
  `.gitkeep`) rồi build lại cả ba collection từ dataset. Đây là cách đúng vì vector là dữ liệu
  **dẫn xuất**: chúng luôn sinh lại được từ `data/clean/`, nên không mất gì.
- **Cách xác minh sau khi sửa:** `uv run python script/check_retrieval.py --all --reset-store` cho
  ba collection với đúng 24 / 22 / 24 vector, sau đó `run_evaluation.py --all` chạy trọn vẹn.
- **Điều học được:** không nên commit artifact nhị phân sinh ra được. Trước đó tôi chọn commit
  `data/chroma/` với lý do `LocalEmbeddingIndex.load()` sẽ lỗi nếu thiếu — lý do đó đúng, nhưng cái
  giá phải trả là một xung đột merge không thể giải quyết thủ công. Lựa chọn tốt hơn: đưa thư mục
  này vào `.gitignore` và ghi rõ trong README rằng sau khi clone phải chạy
  `check_retrieval.py --all --rebuild`. Tôi đã sửa lại quyết định này.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
TV1 gọi Crossref REST API với query *"agentic retrieval augmented generation large language model"*
và filter `from-pub-date:<hôm nay − 180 ngày>,has-abstract:true`, lưu **raw response nguyên vẹn**
vào `data/raw/crossref_response.json` (phục vụ lineage) và bản đã parse thành `PaperRecord` vào
`crossref_records.json`, với `paper_id` là DOI. TV2 làm sạch thành 24 dòng với 10 cột chuẩn, trong
đó `text_for_embedding` gộp title + authors + categories + summary. Tôi đọc file JSON này, sinh
embedding 384 chiều bằng `all-MiniLM-L6-v2` (normalize sẵn) và nạp vào collection ChromaDB dùng
cosine space, id mỗi document là `f"{paper_id}::{index}"` để dòng trùng lặp sau corruption không
đụng id.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
Mỗi sample có `ground_truth` (chuỗi đáp án) và `ground_truth_doc_ids` (danh sách `paper_id`). Hai
thứ này đo hai tầng khác nhau: `retrieval_hit_rate` kiểm tra có `paper_id` nào trong top-k trùng
`ground_truth_doc_ids` không — tức **tìm đúng tài liệu chưa**; còn `mean_token_f1` và LLM judge so
nội dung câu trả lời với `ground_truth` — tức **trả lời đúng chưa**. Tách hai tầng như vậy cho phép
phân biệt "retrieval hỏng" với "sinh câu trả lời hỏng", vì corruption có thể gây ra cái này mà không
gây ra cái kia.

**3. Quality checks khác freshness monitoring ở điểm nào?**
Quality checks trả lời *"dữ liệu có hợp lệ không"* — cấu trúc và tính toàn vẹn: `paper_id` unique và
non-null, `title` không rỗng, summary đủ dài, không trùng lặp. Freshness trả lời *"dữ liệu có còn
mới không"* — một chiều thời gian dựa trên `age_days` so với ngưỡng 180 ngày. Điểm mấu chốt: một
dataset có thể **pass toàn bộ quality checks mà vẫn stale**. Đó chính là kiểu hỏng nguy hiểm nhất
trong thực tế, vì không có gì báo lỗi — pipeline chạy xanh, agent vẫn trả lời trôi chảy, chỉ là trả
lời bằng thông tin cũ.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Vì đây là thí nghiệm có đối chứng. Ta chỉ được phép thay đổi **một biến duy nhất**: chất lượng dữ
liệu. Nếu đổi câu hỏi giữa các lần đo thì chênh lệch metric không còn quy được về corruption — nó có
thể chỉ là do bộ câu hỏi mới khó hơn. Vì vậy `REFRESH_TEST_SET` phải giữ tắt sau khi test set đã
đóng băng, và `run_evaluation.py` luôn trỏ tới cùng một `settings.paths.eval_testset`.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Khi `repaired_metrics.json` quay về xấp xỉ `baseline_metrics.json` trên cả bốn chỉ số, **đồng thời**
data quality checks chuyển từ FAIL về PASS và freshness từ stale về fresh. Riêng con đường repair
mới là điểm quan trọng nhất: repair phải đi từ `data/raw/crossref_records.json` chứ không phải từ
file corrupted. Đó là lý do tồn tại của raw artifact — nếu chỉ giữ dữ liệu đã clean thì không có gì
để phục hồi về.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                             |
| -------------------- | -------: | --------: | -------: | -------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |    0.5000 |   1.0000 | Sụt −0.5000 rồi phục hồi hoàn toàn. Nguyên nhân cơ học: 2/4 paper trong test set bị xóa           |
| `mean_token_f1`      |   1.0000 |    0.4375 |   1.0000 | Sụt −0.5625. Đây là chỉ số duy nhất phản ánh **mức độ** hỏng theo từng trường                    |
| `judge_accuracy`     |   1.0000 |    0.4375 |   1.0000 | LLM judge thật (16/16 verdict, 0 fallback). Trùng số với `token_f1` là ngẫu nhiên — xem bên dưới  |
| `mean_judge_score`   |   5.0000 |    3.0625 |   5.0000 | Cao hơn heuristic (2.7500) vì LLM cho điểm bán phần ở câu `summary` rỗng                          |
| Quality checks       | *(TV4)*  | *(TV4)*   | *(TV4)*  | Ngoài phạm vi của tôi                                                                              |
| Freshness status     | *(TV4)*  | *(TV4)*   | *(TV4)*  | Baseline có `age_days` 5–175, dưới ngưỡng 180. Corruption có scenario `stale_published_dates` (4 dòng) |

Chi tiết `token_f1` theo `question_type` — bảng này mới là phần có tín hiệu thật:

| question_type | Baseline | Corrupted | Repaired | Diễn giải                                                                    |
| ------------- | -------: | --------: | -------: | ------------------------------------------------------------------------------ |
| `summary`     |   1.0000 |    0.0000 |   1.0000 | **Sụp hoàn toàn.** `blank_summaries` khiến câu trả lời là chuỗi rỗng          |
| `authors`     |   1.0000 |    0.2500 |   1.0000 | Chỉ đúng ở paper vừa sống sót vừa đứng rank 1                                 |
| `date`        |   1.0000 |    0.5000 |   1.0000 | `stale_published_dates` làm sai ngày trên các dòng còn lại                     |
| `categories`  |   1.0000 |    1.0000 |   1.0000 | **Không đổi dù `hit_rate` chỉ còn 0.50** — chỉ số này vô nghĩa, xem phân tích  |

Ba chỉ số phụ tôi tự đo ở baseline: self-retrieval **5/5 ở rank 1** (score 0.7263–0.8608), agent
**4/4** câu in-corpus có tool call, **3/3** câu out-of-corpus bị từ chối.

Hai tín hiệu ở tầng vector mà chỉ smoke test mới thấy được, không có trong file metrics:

| Tín hiệu (đo bằng `check_retrieval.py`)  | Baseline | Corrupted | Repaired | Ý nghĩa                                                          |
| ---------------------------------------- | -------: | --------: | -------: | ------------------------------------------------------------------ |
| Self-retrieval rank 1 (5 mẫu)            |      5/5 |       4/5 |      5/5 | Corruption làm **1 paper không còn tự truy hồi được từ title** |
| Số từ trung bình `text_for_embedding`    |    255.3 |     189.6 |    255.3 | Giảm 26% do `blank_summaries` — bằng chứng corruption tới vector |
| Document vượt cửa sổ ~200 từ             |    20/24 |     11/22 |    20/24 | Cùng nguyên nhân                                                   |
| `paper_id` duy nhất / tổng dòng          |    24/24 |     19/22 |    24/24 | 3 dòng duplicate đúng như `corruption_log.json`                    |

Mẫu bị MISS ở corrupted là *"Microsoft Azure artificial intelligence / machine learning…"* — trùng
với scenario `truncate_titles`. Đây là bằng chứng trực tiếp rằng corruption làm hỏng **embedding**,
không chỉ làm hỏng câu trả lời: document vẫn nằm trong index nhưng chính title của nó không còn kéo
được nó lên top-4.

### Sự cố tính toàn vẹn đã phát hiện và khắc phục: LLM judge không chạy

Khi audit artifact do pipeline nhóm sinh ra bằng `uv run python script/run_evaluation.py --audit`,
**48/48 verdict ở cả ba trạng thái đều mang marker `"Fallback heuristic judge used because the LLM
evaluator was unavailable."`** `_judge_answer` đã nuốt exception và rơi về heuristic token-F1 trong
toàn bộ lần chạy.

Ba bằng chứng độc lập tại thời điểm đó:

1. `judge_accuracy` = 0.4375 bằng đúng `mean_token_f1` = 0.4375 ở trạng thái corrupted.
2. `repaired_answers.json` **trùng từng byte** với `baseline_answers.json` (MD5 `2ad28ee0…`) — chỉ
   xảy ra khi toàn bộ đường sinh câu trả lời và chấm điểm đều tất định.
3. Mọi `judge.score` khớp chính xác công thức heuristic (`f1 ≥ 0.95 → 5`, `≥ 0.5 → 3`, còn lại `1`).

**Cách khắc phục:** chạy `script/check_llm.py` để xác nhận provider (`openai` / `gpt-4o-mini` PASS
cả 5 stage, gồm cả `with_structured_output`), rồi chạy lại `run_evaluation.py --all`. Sau khi chạy
lại, audit báo **0 fallback ở cả ba state** và `--audit` kết luận `no integrity problems found`.

**Thay đổi sau khi sửa:** `mean_judge_score` của corrupted tăng từ **2.7500 → 3.0625**. Nguyên nhân
cụ thể: với 4 câu `summary` bị rỗng, heuristic chấm cứng 1 điểm, còn LLM chấm 2–3 điểm vì ghi nhận
câu trả lời "không sai về nội dung, chỉ là thiếu". Kiểm tra từng sample cho thấy **4/16 điểm khác
với công thức heuristic**, tức judge hiện tại là phép đo độc lập chứ không phải diễn giải lại
`token_f1`. Việc `judge_accuracy` vẫn bằng 0.4375 chỉ là trùng số ngẫu nhiên (7/16 câu đúng), không
phải dấu hiệu phụ thuộc.

Hai chỉ số `retrieval_hit_rate` và `mean_token_f1` **không đổi trước và sau khi sửa** — chúng được
tính tất định từ index và không đi qua judge. Đây là lý do mọi phân tích bên dưới vẫn đứng vững kể
cả trong bản artifact hỏng.

Đây chính là chế độ hỏng âm thầm mà `script/check_llm.py` được viết ra để chặn: pipeline chạy xanh,
file metrics vẫn đủ bốn con số, không exception nào được ném ra. Nếu không audit thì nhóm đã báo cáo
`mean_judge_score = 2.7500` như một chỉ số LLM.

### Kết luận từ số liệu

1. **[Data corruption]** — `drop_latest_records` xóa 5/24 bản ghi (còn 22 dòng, gồm 3 dòng
   duplicate), `blank_summaries` làm rỗng 5 summary, `stale_published_dates` làm cũ 4 ngày →
   **[quality/freshness signal]** — TV4 ghi nhận quality checks FAIL và freshness stale →
   **[agent metric]** — `retrieval_hit_rate` 1.0000 → 0.5000, `mean_token_f1` 1.0000 → 0.4375.
2. **[Repair action]** — dựng lại dataset từ `data/raw/crossref_records.json` →
   **[quality/freshness phục hồi]** — 24/24 dòng trở lại, mọi cột trùng khít baseline (0 dòng khác
   biệt trên `title`, `summary`, `published`, `text_for_embedding`, `authors_joined`) →
   **[agent metric phục hồi]** — cả bốn chỉ số trở về đúng mức baseline, delta = +0.0000.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Xét theo hai cơ chế tách biệt:

- **`drop_latest_records` chi phối `retrieval_hit_rate`.** Test set chỉ phủ **4 paper**, và 2 trong
  số đó (`10.1007/s10278-026-02086-9`, `10.1111/exsy.70341`) nằm trong 5 bản ghi bị xóa. Vì vậy
  hit_rate rơi đúng 0.50, và **cả bốn question_type đều rơi đúng 0.50** — mức đồng đều này chứng tỏ
  nguyên nhân là *document biến mất khỏi index*, không phải embedding bị suy giảm ngữ nghĩa.
- **`blank_summaries` chi phối chất lượng câu trả lời.** `summary` là nhóm duy nhất về **0.0000**,
  kể cả trên 2 sample mà retrieval vẫn hit (eval-02, eval-04): `first_sentence("")` trả về chuỗi
  rỗng, nên dù tìm đúng tài liệu thì vẫn không có gì để trả lời.

- **`truncate_titles` là scenario duy nhất phá được embedding một cách quan sát được.** Smoke test
  cho thấy 1/5 paper mẫu ở corrupted **không còn tự truy hồi được từ chính title của nó** (mẫu
  *"Microsoft Azure artificial intelligence…"*), trong khi baseline và repaired đều 5/5 rank 1.
  Document vẫn nằm trong index nhưng vector của nó đã lệch đủ để rơi khỏi top-4.

Hai mục đầu đúng như dự đoán tôi đưa cho TV4 trước khi họ viết corruption. Riêng
`inject_summary_noise` vẫn không tách được tác động riêng, phù hợp với giới hạn 256 token: nhiễu
chèn ở cuối `text_for_embedding` rơi vào vùng bị cắt. Tôi đã xác minh corruption **có** tới được
vector — 14/22 dòng sống sót có `text_for_embedding` thay đổi, và số từ trung bình giảm từ 255.3
xuống 189.6 — nên TV4 rebuild đúng; vấn đề chỉ là phần nhiễu nằm ngoài cửa sổ embedding.

**Kết quả nào khác với kỳ vọng ban đầu?**

Hai kết quả.

Thứ nhất, **`categories` giữ nguyên `token_f1` = 1.0000 dù `hit_rate` chỉ còn 0.50.** Tôi nghi có
lỗi tính toán nên kiểm tra trực tiếp: `categories_joined` bằng `'General'` trên **cả 24/24
document**. Crossref thường không trả trường `subject`, nên cleaning gán mặc định cho tất cả. Hệ quả
là câu hỏi `categories` trả lời đúng **bất kể truy hồi ra tài liệu nào** — 4/16 sample của test set
không có khả năng phân biệt và làm `mean_token_f1` bị thổi lên. Đây là khuyết điểm của test set chứ
không phải của pipeline, và cần nêu trong báo cáo nhóm.

Thứ hai, **`retrieval_hit` có thể `True` mà câu trả lời vẫn sai** (eval-04-authors: hit=True,
f1=0.00). Nguyên nhân nằm ở `metrics.py`: `retrieval_hit` được tính trên **toàn bộ top-k**
(`any(doc_id in ground_truth_doc_ids for doc_id in retrieved_doc_ids)`), trong khi `_extract_answer`
chỉ dùng **`retrieved[0]`**. Tài liệu đúng lọt vào top-4 nhưng không đứng đầu thì vẫn tính là hit mà
câu trả lời lấy từ tài liệu khác. Hai chỉ số này đo hai thứ khác nhau và không nên đọc như một.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Raw artifact là điều kiện cần để phục hồi.** Trước bài này tôi coi việc lưu raw response là dư
   thừa vì đã có cleaned data. Nhưng repair chỉ khả thi khi còn nguồn để quay về — nếu chỉ giữ file
   clean thì dữ liệu hỏng là hỏng vĩnh viễn. Lineage không phải thủ tục hành chính, nó là cơ chế
   khôi phục.
2. **Hỏng âm thầm nguy hiểm hơn hỏng ồn ào.** Ba cơ chế trong bài này đều **không ném exception**:
   collection bị ghi đè vẫn cho ra metrics; judge hỏng vẫn cho ra `judge_accuracy`; MiniLM cắt bớt
   text mà không cảnh báo. Observability tồn tại chính vì những trường hợp này — pipeline chạy xanh
   không đồng nghĩa với kết quả đúng.
3. **Chất lượng dữ liệu quyết định chất lượng RAG, nhưng qua đường nào thì phải đo mới biết.** Việc
   phát hiện 20/24 document vượt cửa sổ 256 token cho thấy cùng một hành động corruption có thể tác
   động mạnh hoặc gần như bằng không, tùy vào việc nó rơi vào đâu trong text. Không đọc kỹ tầng
   embedding thì không thể dự đoán được điều đó.

### Nếu có thêm thời gian

**Ưu tiên 1 — bỏ hoặc thay nhóm câu hỏi `categories`.** `categories_joined` bằng `'General'` trên
24/24 document, nên 4/16 sample luôn đúng bất kể truy hồi ra gì. Chúng đang thổi `mean_token_f1`
lên mà không đo được điều gì. Cách đo cải thiện: bỏ 4 sample đó và tính lại — nếu `mean_token_f1`
corrupted giảm xuống dưới 0.4375 thì đó là bằng chứng định lượng rằng test set hiện tại đang che bớt
mức độ hỏng thật.

**Ưu tiên 2 — rút gọn `text_for_embedding` xuống dưới cửa sổ 256 token** (title + 2 câu đầu của
abstract). Hiện 20/24 document bị cắt âm thầm. Cách đo: so `retrieval_hit_rate` và điểm cosine trung
bình của self-retrieval giữa hai cấu hình trên cùng test set. Đây cũng là điều kiện để
`inject_summary_noise` thực sự đo được tác động.

**Ưu tiên 3 — mở rộng test set ra ngoài 4 paper.** Với 4 paper và `top_k=4` trên corpus 24 document,
một scenario corruption xóa 2 paper là đủ ấn định `hit_rate` = 0.50. Độ phân giải của phép đo hiện
quá thô để phân biệt các loại corruption khác nhau.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng — RAGAS được ghi rõ là
      **chưa chạy**; audit artifact hiện tại xác nhận 48/48 verdict đến từ LLM và không còn fallback.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyen Quang Vinh
**Ngày xác nhận:** 2026-08-06
