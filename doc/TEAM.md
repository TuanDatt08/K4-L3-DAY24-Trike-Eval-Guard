# Nhóm thực hiện K4 Track 3A

Tên nhóm: Trike

Repo chung: https://github.com/TuanDatt08/K4-L3-DAY24-Trike-Eval-Guard

Trưởng nhóm/người nộp: Lê Tuấn Đạt — 2A202602623

Ngày lab/deadline áp dụng: 2026-10-12, deadline 23:59 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: cập nhật SHA của commit cuối sau khi push (lệnh `git rev-parse HEAD`).

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Lê Tuấn Đạt | 2A202602623 | Tích hợp m1–m5 từ Day 18; Phase A/B/C (`src/phase_*.py`); chạy batch; viết 3 báo cáo | Commit trên repo; `artifacts/*.json`; `doc/reports/*.md` |

Người tích hợp/chạy batch/nộp link: Lê Tuấn Đạt — sửa môi trường, chép và chỉnh adapter m1–m5,
chạy `setup_answers.py --live` và runner A/B/C, chạy `check_lab.py`, push và nộp link.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 Home 10.0.26300; Python 3.11.9 trong `.venv`.
Virtualenv/dependencies/imports: cài `requirements/requirements.txt` với
`constraints-core.txt`; `pip check` không lỗi. Lỗi gặp và cách sửa:
`import ragas` báo `pyarrow requires NumPy 2.0` (pyarrow 26) → cài `pyarrow>=15,<18` (17.0.0);
sau đó `OSError WinError 1114 ... torch\lib\c10.dll` khi import pandas/pyarrow trước torch 2.14.1
(hai gói này mang `msvcp140.dll` cũ) → hạ `torch==2.5.1+cpu` và `transformers==4.46.3`.
Sau khi sửa: `python -c "import ragas, nemoguardrails, presidio_analyzer, spacy"` in `imports OK`.
Models/Qdrant/50 answers đã chuẩn bị: spaCy `en_core_web_lg`; bge-m3 và bge-reranker-v2-m3
trong cache HuggingFace; Qdrant `qdrant/qdrant:v1.9.7` qua Docker Compose. `setup_answers.py --live`
sinh 50 answers (20/20/10), cả 50 có `generation_mode = llm`, model `gpt-4o-mini-2024-07-18`.
Hai PDF scan trong `data/` bị m1 bỏ qua vì không có text layer.

Chỉnh sửa để module Day 18 khớp lab: thêm `LLM_API_KEY`/`LLM_MODEL`/`llm_client` vào `config.py`
(Day 18 dùng Gemini, lab này dùng OpenAI); m2 dùng `client.search` vì lab pin `qdrant-client<1.10`;
m4 bỏ `try/except` nuốt lỗi, chấm lại câu ra NaN, kẹp sai số float `1.0000000000000002` về 1.0 và
trả `metadata.evaluator_models`.

## INDIVIDUAL

### LeTuanDat-2A202602623

- Phần được giao và phần thực tế đã làm: toàn bộ lab — tích hợp m1–m5; Tasks 1–4
  (`group_by_distribution`, `run_ragas_50q`, `bottom_10`, `cluster_analysis`); Tasks 5–8
  (`pairwise_judge`, `swap_and_average`, `cohen_kappa`, `bias_report`); Tasks 9a–12 (`pii_scan`,
  `check_input_rail`, `run_adversarial_suite`, `check_output_rail`, `measure_p95_latency`); chỉnh
  prompt `self_check_input` trong `guardrails/config.yml`; viết `failure_clusters.md`,
  `bias_report.md`, `blueprint.md`.
- Bằng chứng: commit trên repo; `artifacts/answers_50q.json`, `ragas_50q.json`,
  `judge_results.json`, `guard_results.json`.
- Cách kiểm tra: `python -m pytest tests/ -q` (86 passed offline); chạy live
  `run_experiments.py --phase a/b/c` (Phase C với `--latency-samples 20`); `python scripts/check_lab.py`.
  Kết quả: avg_score 0.785, nhóm yếu nhất multi_hop 0.729; κ = 1.0; attacks 20/20, clean 8/8,
  output 4/4; input guard P95 792.8ms.
- Điều đã học: faithfulness cao chưa chắc answer đúng (ID 5 trả lời trung thành với chunk sai); cây
  chẩn đoán theo worst_metric có thể gán sai nguyên nhân — 8 câu "Không tìm thấy." là over-refusal
  chứ không phải hallucination; pairwise A/B khác nhãn 0/1; swap-and-average phát hiện case judge
  không chắc chắn; bộ clean controls cần thiết vì guard luôn-chặn cũng đạt 20/20 attacks.
- Giới hạn/cách xử lý: Presidio với spaCy `en` chặn nhầm 7/8 câu sạch tiếng Việt → chỉ giữ 3 entity
  của bài; prompt input rail ban đầu chặn nhầm câu mật khẩu và lọt 2 câu off-topic → làm rõ prompt
  theo loại, nhưng vì tune trên chính bộ test nên ghi rõ cần bộ held-out; latency vượt 500ms được
  ghi đúng số đo.
- Nguồn/AI hỗ trợ nếu có: dùng Claude Code (AI) để đọc đề, sửa lỗi môi trường, viết code các Task,
  chạy thực nghiệm và soạn nháp báo cáo. Kiểm chứng: chạy unit tests, chạy live runner, `check_lab.py`,
  và đối chiếu từng số liệu trong báo cáo với `artifacts/*.json`. Module m1–m5 lấy từ bài Day 18 của
  chính mình.

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp.
