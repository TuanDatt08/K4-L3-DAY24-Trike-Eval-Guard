# Blueprint CI/CD cho RAG và guardrails

Nhóm: Trike

Người phụ trách: Lê Tuấn Đạt — 2A202602623

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: Phase C 2026-10-12T16:23:00Z (Phase A 16:19:37Z, Phase B 16:20:16Z); guard models: `gpt-4o-mini` (NeMo self-check input/output) + Presidio/spaCy `en_core_web_lg` local.
Models generation/evaluator/judge từ A/B: generation `gpt-4o-mini-2024-07-18` (answers_50q.json);
evaluator `gpt-4o-mini` + `BAAI/bge-m3` (m4, ragas_50q.json); judge `gpt-4o-mini` (judge_results.json).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

| Tầng | Chặn gì | Failure action | Log |
|---|---|---|---|
| Presidio (local) | CCCD/CMND (9/12 số), SĐT VN `0[3-9]xxxxxxxx`, email | Chặn request, trả câu từ chối chuẩn; không gửi text sang LLM | Chỉ log entity type + vị trí và bản `anonymized`, không log giá trị PII |
| NeMo input (self check input) | off-topic, jailbreak, giả danh, prompt injection, hỏi dữ liệu cá nhân/credential | Trả câu từ chối từ `rails.co`; quyết định đọc từ `activated_rails[].stop`, không dò từ khóa | Log id request, rail đã kích hoạt, không log prompt đầy đủ |
| RAG (m1–m5) | — | Lỗi generation → extractive fallback, ghi `generation_mode` | Log contexts ids, model id |
| NeMo output (self check output) | CCCD, SĐT/email riêng, lương cá nhân, credential trong answer | Thay answer bằng câu từ chối; answer an toàn giữ nguyên | Log rail kích hoạt + answer đã redact |

Secrets (`OPENAI_API_KEY`) chỉ nằm trong `.env`/secret store của CI, không vào repo hay log.
Nếu NeMo/OpenAI lỗi hoặc timeout: **fail-closed** cho input rail (chặn kèm thông báo thử lại) vì
đây là ranh giới bảo mật; Presidio vẫn chạy local nên tầng PII không phụ thuộc mạng.

Kết quả thực nghiệm: Presidio chặn 4/20 attacks (nhóm `pii_injection` có PII thật), NeMo input
chặn 16/20 còn lại; 8/8 câu sạch được cho qua; 4/4 output cases đúng (2 sạch giữ nguyên, 2 nhạy cảm
bị thay). Hai điều chỉnh đã làm để xử lý chặn nhầm (ghi rõ vì đã tune trên chính bộ test):
1. Presidio chỉ giữ 3 entity của bài. Lần chạy local đầu tiên, spaCy `en` gắn nhãn PERSON cho cụm
   tiếng Việt ("Xin lỗi", "bao nhiêu") và US_DRIVER_LICENSE cho "v2024" → 7/8 câu sạch sẽ bị chặn.
2. Prompt `self_check_input` ban đầu chặn nhầm câu sạch 107 ("mật khẩu tối thiểu bao nhiêu ký tự",
   kết quả 7/8) và bỏ lọt 2 câu off-topic (bài thơ, phim Marvel; 18/20). Prompt được làm rõ theo
   *loại* (câu hỏi về quy định mật khẩu được phép, hỏi mật khẩu thật thì chặn; liệt kê các dạng
   off-topic) → 20/20 và 8/8. Vì tune trên cùng bộ 28 câu, kết quả này có thể lạc quan; cần bộ
   held-out để xác nhận.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 15.1 | 18.7 | 19.5 | Đã đo; nhỏ (~2% tổng) |
| NeMo input | 668.9 | 777.4 | 845.8 | Đã đo; bottleneck (1 lời gọi gpt-4o-mini/request) |
| Input guard sequential | 682.9 | 792.8 | 861.3 | Đã đo; vượt target 500ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 792.8ms, `latency_budget_ok = False`.
Bottleneck là NeMo input (~98% thời gian): mỗi request là một lời gọi API OpenAI qua mạng từ máy cá
nhân (min 602ms, max 863ms trên 20 mẫu). Hướng giảm: cache quyết định cho input lặp lại, chạy
Presidio và NeMo song song (Presidio rẻ nên có thể bỏ qua NeMo khi Presidio đã chặn trong request
thật), dùng classifier local nhỏ cho off-topic/jailbreak và chỉ gọi LLM khi không chắc chắn, hoặc
đặt server gần region API. Kế hoạch đo phần chưa đo: thêm timestamp `perf_counter` quanh
`run_query` (RAG) và `check_output_rail` (output) trên 8 câu sạch × ≥ 3 vòng sau 2 warm-up, lưu raw
samples, và đo full request end-to-end có short-circuit tách riêng với phép đo input layers.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

Đối chiếu với kết quả hiện tại: faithfulness trung bình 50 câu = (20×0.842 + 20×0.487 + 10×0.800)/50
= 0.691 → **không đạt** gate 0.75 (do 8 câu over-refusal và multi_hop); avg_score trung bình = 0.785
→ đạt 0.65; attacks 20/20, clean 8/8, output 4/4 → đạt.

Job đề xuất (chưa triển khai — repo chưa có workflow CI):

1. `python -m pytest tests/ -q` — offline, mỗi PR.
2. `python scripts/run_experiments.py --phase c --live --latency-samples 20` — khi đổi
   `guardrails/` hoặc `phase_c_guard.py` (có chi phí API, chạy với secret của CI).
3. `python scripts/run_experiments.py --phase a --live` — nightly hoặc khi đổi m1–m5/prompt.
4. `python scripts/check_lab.py` — validate schema/counts/percentile.

`check_lab.py` hiện chỉ kiểm tra mốc lab (≥15/20, clean 8/8), **không** kiểm tra các ngưỡng
MIN_FAITHFULNESS/MIN_AVG/MIN_ATTACKS ở trên. Để thành gate thật cần thêm một script nhỏ đọc
`ragas_50q.json`/`guard_results.json`, so với ngưỡng và `sys.exit(1)` khi không đạt.

## Monitoring và cải tiến

| Metric | Ngưỡng cảnh báo | Cách lấy mẫu | Người xử lý |
|---|---|---|---|
| Tỷ lệ request bị input rail chặn | tăng > 2× so với tuần trước | log quyết định rail mỗi request | Owner guardrails |
| False positive (user báo bị chặn nhầm) | > 0 case/tuần cần review | nút báo lỗi + review mẫu chặn ngẫu nhiên 20/tuần | Owner guardrails |
| Tỷ lệ answer "Không tìm thấy." | > 10% | đếm trên log answer | Owner RAG |
| Faithfulness RAGAS trên mẫu production | < 0.75 | chấm 50 câu mẫu/tuần (có reference do người viết) | Owner RAG |
| Input guard P95 | > 500ms | raw latency mỗi request | Owner hạ tầng |
| PII trong log | > 0 | quét log bằng Presidio hằng ngày | Owner bảo mật |

Drift: khi thêm phiên bản chính sách mới (như v2023→v2024), chạy lại Phase A và bổ sung câu
adversarial về phiên bản vào test set. Privacy: log chỉ giữ bản anonymized; dữ liệu test là dữ liệu
mẫu. Giới hạn: bộ 50/20/8/4 nhỏ, prompt guard đã tune trên chính bộ 28 input.

RAGAS mean/worst distribution: avg_score 0.785 trên 50 câu; nhóm yếu nhất multi_hop (0.729).
Cohen’s κ: 1.0 (10/10 nhãn khớp human).
Attacks passed: 20/20; clean false_positive_rate: 0.0.

Cải tiến có thể kiểm tra:
1. Sửa prompt generation cho phép trả lời từng phần → kỳ vọng số câu "Không tìm thấy." giảm từ 8/50
   và faithfulness multi_hop tăng từ 0.487; đo bằng chạy lại setup + Phase A.
2. `RERANK_TOP_K` 3 → 5 → kiểm tra context_recall adversarial (0.717) và multi_hop (0.804) tăng.
3. Lọc/ưu tiên metadata phiên bản mới nhất khi retrieval → kiểm tra ID 33, 39 và bẫy v2023/v2024.
4. Viết thêm 10–20 attack và câu sạch held-out (chưa dùng để tune prompt) → đo lại pass rate và
   false-positive rate để biết 20/20, 8/8 có tổng quát hóa không.
5. Thử classifier local cho input rail → so P95 input guard với 792.8ms hiện tại, giữ ≥ 18/20 và 8/8.
