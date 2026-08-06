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
| Evaluation corrupted/repaired     | `script/run_evaluation.py --all`                    | Corrupted/repaired dataset từ flow tích hợp | `corrupted_metrics.json`, `repaired_metrics.json`                    | Hoàn thành, đã đối chiếu artifact |
| RAGAS metrics                     | `RUN_RAGAS=1`                                       | Answers + LLM                               | Trường `ragas` trong metrics JSON                                    | **Chưa chạy**                 |
| Tài liệu vận hành                 | `docs/` (gitignored)                                | —                                           | Runbook, data contract, ghi chú kỹ thuật                             | Hoàn thành                    |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                              | Thành viên/module được hỗ trợ | Kết quả                                                                                                                                |
| ------------------------------------------------------ | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Kiểm chứng Clean Dataset Schema và Evaluation Set       | TV1, TV2                      | Xác nhận 10/10 cột bắt buộc, 16/16 sample đúng contract và đúng nhánh keyword của `qa.py`                                               |
| Cảnh báo NaN trong `pdf_url` khi đọc CSV                | TV2 / mọi người đọc CSV        | 15/24 dòng `pdf_url` rỗng bị `pd.read_csv` chuyển thành NaN; ChromaDB metadata không nhận NaN. JSON đúng, chỉ CSV cần `keep_default_na=False` |
| Cảnh báo giới hạn 256 token của MiniLM                  | TV4 (corruption)              | 20/24 document vượt ngưỡng ~200 từ; corruption thêm nhiễu vào **cuối** summary sẽ nằm trong vùng bị cắt và không tới được vector         |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                            | File/hàm/artifact liên quan                  | Kết quả bàn giao                                                    | Cách xác minh                              |
| ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------ |
| Build collection `papers-baseline`               | `data/embeddings/papers_embeddings.json`     | 24 vector, 384 chiều, cosine space                                   | `uv run python script/check_retrieval.py`  |
| Kiểm chứng semantic search                       | Log của `check_retrieval.py`                 | 5/5 paper tự truy hồi chính nó ở **rank 1**, score 0.7263–0.8608     | `uv run python script/check_retrieval.py`  |
| Kiểm chứng exact lookup                          | Log của `check_retrieval.py`                 | 5/5 paper resolve bằng cả `paper_id` và title; key sai trả về `None` | `uv run python script/check_retrieval.py`  |
| Kiểm chứng LLM provider + structured output      | Log của `check_llm.py`                       | `openai` / `gpt-4o-mini` PASS cả 5 stage                             | `uv run python script/check_llm.py`        |
| Agent demo + hallucination test                  | `data/results/agent_demo_answers.json`       | 4/4 câu in-corpus có tool call; 3/3 câu out-of-corpus bị từ chối     | `uv run python script/run_agent_demo.py`   |
| Chạy evaluation ba trạng thái                    | `data/results/*_metrics.json`                | Đủ 16 sample cho baseline, corrupted và repaired                     | Đối chiếu ba metrics artifact              |
| Kiểm chứng nguồn judge                           | `data/results/*_answers.json`                | Cả ba trạng thái dùng fallback heuristic do LLM evaluator không khả dụng | Kiểm tra trường `judge.reasoning`        |

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

- **Kết quả mong đợi:** 24 vector 384 chiều trong đúng collection `papers-baseline`; mọi paper tự
  truy hồi được; agent từ chối câu hỏi ngoài corpus; đủ metrics cho cả ba trạng thái.
- **Kết quả thực tế:** `check_retrieval.py` PASS (5/5 self-retrieval rank 1, 5/5 lookup,
  24/24 vector). `run_agent_demo.py`: 4/4 grounded, 3/3 refused. Ba evaluation artifact đều có
  16 sample. Baseline và repaired đạt `retrieval_hit_rate` = 1.0, `mean_token_f1` = 1.0,
  `judge_accuracy` = 1.0, `mean_judge_score` = 5.0; corrupted lần lượt còn 0.5, 0.4375,
  0.4375 và 2.75. Trường `judge.reasoning` cho biết evaluator đã dùng fallback heuristic ở cả ba
  trạng thái; vì vậy không diễn giải các judge metrics này là kết quả của LLM judge thật.
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

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| -------------------- | -------: | --------: | -------: | -------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | Corruption làm mất một nửa retrieval hit; repair phục hồi hoàn toàn |
| `mean_token_f1`      | 1.0000 | 0.4375 | 1.0000 | Nội dung trả lời suy giảm rõ rệt rồi trở lại mức baseline |
| `judge_accuracy`     | 1.0000 | 0.4375 | 1.0000 | Chỉ số dùng fallback heuristic trong cả ba artifact, không phải LLM judge thật |
| `mean_judge_score`   | 5.0000 | 2.7500 | 5.0000 | Điểm heuristic giảm 2.25 rồi phục hồi về 5.0 |
| Quality checks       | 6/6 PASS | 3/6 PASS | 6/6 PASS | Corrupted fail uniqueness, summary length và freshness |
| Freshness status     | Fresh | Stale | Fresh | Corrupted có 6 dòng stale; repaired không còn dòng stale |

Ba chỉ số phụ tôi tự đo được ở baseline: self-retrieval **5/5 ở rank 1** (score 0.7263–0.8608),
agent **4/4** câu in-corpus có tool call, **3/3** câu out-of-corpus bị từ chối.

### Kết luận từ số liệu

Hai chuỗi nhân quả đã được xác nhận bằng artifact:

1. `[Data corruption]` → quality giảm từ 6/6 xuống 3/6, freshness chuyển sang stale →
   `retrieval_hit_rate` giảm 50% và `mean_token_f1` giảm 56.25%.
2. `[Repair từ raw records]` → quality trở lại 6/6, freshness trở lại fresh → toàn bộ metrics
   phục hồi về đúng mức baseline.

Các corruption ảnh hưởng trực tiếp nhất là **xóa bản ghi**, **làm rỗng summary** và **cắt title**:
xóa bản ghi loại tài liệu đúng khỏi index; summary rỗng phá nội dung embedding/câu trả lời; title
bị cắt làm exact-title lookup không còn khớp. Nhiễu chèn cuối summary có thể tác động yếu hơn do
giới hạn 256 token của MiniLM: 20/24
document hiện đã dài quá ngưỡng, nên nhiễu chèn vào **cuối** `text_for_embedding` rơi vào vùng bị
cắt và **không bao giờ tới được vector**. Ngược lại, xóa bản ghi làm `retrieval_hit_rate` sụt trực
tiếp vì document đúng biến mất khỏi index, còn làm rỗng summary phá luôn cả embedding lẫn câu trả
lời cho nhóm câu hỏi `summary`.

Kết quả nào khác với kỳ vọng ban đầu? — cả bốn metric baseline đạt đúng 1.0, cao hơn tôi dự đoán.
Giả thuyết ban đầu là có lỗi trong cách tính. Tôi đã kiểm tra bằng cách đọc trực tiếp
`baseline_answers.json` và đối chiếu với `papers_clean.json`: `_extract_answer` trả về đúng cột
`authors_joined` / `published` / `categories_joined` / `first_sentence(summary)`, và `ground_truth`
của TV2 được sinh từ **chính những cột đó**, nên khớp tuyệt đối là hành vi đúng chứ không phải bug.

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

Rút gọn `text_for_embedding` xuống dưới cửa sổ 256 token (chỉ giữ title + categories + 2 câu đầu của
abstract) rồi chạy lại evaluation để so sánh. Hiện 20/24 document đang bị cắt âm thầm, nghĩa là một
phần abstract chưa từng được đánh chỉ mục. Cách đo cải thiện: so `retrieval_hit_rate` và điểm cosine
trung bình của self-retrieval giữa hai cấu hình, trên cùng test set. Nếu điểm tăng, đó là bằng chứng
định lượng rằng truncation đang làm giảm chất lượng retrieval — và cũng là dữ liệu để TV4 thiết kế
corruption có ý nghĩa hơn.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Corrupted và repaired được đối chiếu từ artifact thực tế; RAGAS vẫn được ghi rõ là chưa chạy.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quang Vinh
**Ngày xác nhận:** 2026-08-06
