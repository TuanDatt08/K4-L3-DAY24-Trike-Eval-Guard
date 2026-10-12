# Phân tích lỗi Phase A

Nhóm: Trike

Người phụ trách: Lê Tuấn Đạt — 2A202602623

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T16:19:37Z.
Generation mode/fallback và điều kiện chạy: 50/50 answers có `generation_mode = llm`, không có
extractive fallback. Pipeline: m1 hierarchical chunking (26 tài liệu, 114 child chunks; 2 PDF scan
`BCTC.pdf` và Nghị định 13/2023 bị bỏ qua vì không có text layer) → m5 enrichment (1 lời gọi
LLM/chunk) → m2 hybrid BM25 + dense bge-m3 trên Qdrant 1.9.7 → m3 rerank bge-reranker-v2-m3 top 3
→ generation với system prompt "Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'".
Models generation/evaluator: generation `gpt-4o-mini-2024-07-18`; evaluator từ m4
`gpt-4o-mini` (LLM judge của RAGAS 0.1.22) + `BAAI/bge-m3` (embedding cho answer_relevancy).
`answer_relevancy.strictness = 1` để giảm chi phí.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.842 | 0.487 | 0.800 |
| answer_relevancy | 0.734 | 0.626 | 0.673 |
| context_precision | 0.937 | 1.000 | 0.958 |
| context_recall | 0.850 | 0.804 | 0.717 |
| avg_score | 0.841 | 0.729 | 0.787 |

Retrieval nhìn chung tốt (precision ≥ 0.93, recall ≥ 0.71 ở cả ba nhóm). Chênh lệch lớn nhất
nằm ở faithfulness của multi_hop (0.487), tức phía generation.

## Bottom 10 và nguyên nhân

| Rank | ID | Distribution | Question | avg_score | worst_metric | diagnosis | suggested_fix |
|---|---|---|---|---|---|---|---|
| 1 | 8 | factual | Nhân viên được nghỉ bao nhiêu ngày khi cha hoặc mẹ mất? | 0.1250 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 2 | 33 | multi_hop | Manager thâm niên 12 năm: tổng phụ cấp tháng và số ngày phép năm theo v2024? | 0.3750 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 3 | 22 | multi_hop | Mua laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT? | 0.4167 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 4 | 48 | adversarial | Nhân viên thử việc có được hưởng bảo hiểm sức khỏe PVI không? | 0.4167 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 5 | 50 | adversarial | Manager có thể dùng VPN cá nhân (NordVPN) khi WFH để tăng bảo mật không? | 0.4167 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 6 | 39 | multi_hop | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 (độ dài, thời hạn đổi, MFA). | 0.5000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 7 | 9 | factual | Nam nhân viên được nghỉ bao nhiêu ngày khi vợ sinh con? | 0.5000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 8 | 5 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | 0.5616 | context_recall | Missing relevant chunks | Improve chunking or add BM25 |
| 9 | 27 | multi_hop | Thâm niên 7 năm theo v2024 được bao nhiêu ngày phép? Trừ 4 ngày ốm không giấy y tế còn bao nhiêu? | 0.6390 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 10 | 30 | multi_hop | So sánh quyền lợi bảo hiểm giữa nhân viên thử việc và nhân viên chính thức. | 0.6556 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |

Diagnosis/suggested_fix ở bảng trên là output Task 3 (map từ `DIAGNOSTIC_TREE` theo worst_metric),
giữ nguyên như trong JSON. Đọc answer/contexts/reference cho thấy **nhãn tự động "LLM hallucinating"
sai về nguyên nhân** với phần lớn các câu này:

- **Over-refusal, không phải hallucination (8/50 câu trả "Không tìm thấy.":** ids 8, 9, 22, 25, 33,
  39, 48, 50). Answer từ chối không có claim nào nên RAGAS chấm faithfulness = 0 và answer_relevancy
  = 0. Trong 7/8 câu này context_recall ≥ 0.5, tức context đã chứa phần lớn thông tin cần:
  - ID 39: context_recall = **1.0** — đủ chunk mật khẩu v2 (12 ký tự, MFA bắt buộc) và đoạn
    "v1.0 đã được thay thế bởi v2.0 từ 01/07/2024" — nhưng model vẫn trả "Không tìm thấy." vì
    câu hỏi so sánh hai phiên bản mà context không có đủ số liệu v1.0, nên chọn từ chối toàn bộ.
  - ID 33: context có "15 ngày phép năm v2024" và "cộng 1 ngày cho mỗi 3 năm" nhưng thiếu chunk phụ
    cấp; model từ chối thay vì trả lời phần ngày phép (15 + 4 = 19) và nói rõ phần thiếu.
  - ID 50: context chứa nguyên văn "Không sử dụng VPN cá nhân (NordVPN, ExpressVPN) trong mạng công ty"
    nhưng model vẫn từ chối — đây là câu có đáp án trực tiếp.
  - ID 48: context có "PVI ... cho tất cả nhân viên chính thức" và "thử việc KHÔNG được nghỉ phép năm";
    câu trả lời đúng ("không") cần suy luận phủ định từ phạm vi "nhân viên chính thức", model không
    dám suy luận.
- **Lỗi retrieval thật (ID 5):** context_recall = 0. Reranker đưa lên chunk *tạm ứng* (≥ 5 triệu cần
  Kế toán trưởng) thay vì chunk ngưỡng phê duyệt mua sắm (> 50 triệu cần CEO). Model trả lời trung
  thành với context sai ("Trưởng phòng và Kế toán trưởng") nên faithfulness = 1.0 nhưng answer sai —
  ví dụ điển hình faithfulness cao không đồng nghĩa với đúng.
- **ID 8:** context_recall = 0 — chunk nghỉ phép đặc biệt được lấy là đoạn "giấy tờ chứng minh",
  không phải đoạn quy định số ngày tang lễ; hai chunk còn lại là nghỉ ốm và phép năm v2023. Đây là
  lỗi retrieval dẫn tới từ chối (giả thuyết: child chunk 256 ký tự tách đoạn số ngày khỏi đoạn giấy
  tờ cùng mục — chưa kiểm chứng).

Vì vậy gợi ý "Tighten system prompt" của cây chẩn đoán đi **ngược** với lỗi thật: prompt hiện tại đã
quá chặt. Sửa đúng là cho phép trả lời từng phần có căn cứ.

## Matrix và nhóm yếu nhất

Matrix đếm **mọi câu** theo metric thấp nhất của câu đó (tổng cột = kích thước nhóm 20/20/10, không phải số failure):

| worst_metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 5 | 14 | 2 |
| answer_relevancy | 12 | 4 | 1 |
| context_precision | 1 | 0 | 1 |
| context_recall | 2 | 2 | 6 |

Nhóm yếu theo mean thấp nhất: multi_hop; mean: 0.729 (factual 0.841, adversarial 0.787).
Worst metric xuất hiện nhiều nhất: faithfulness; số câu: 21.

Multi_hop yếu vì câu hỏi cần ghép 2–3 chính sách (phép năm + phụ cấp, mua sắm + CNTT, tạm ứng +
phạt). Với top-3 rerank, thường chỉ một phần thông tin có mặt; prompt "chỉ dựa trên context, nếu
không có → Không tìm thấy" khiến model từ chối cả câu (4/8 câu từ chối là multi_hop) hoặc ghép phép
tính không có trong context (ID 27, 30 có faithfulness thấp nhưng không từ chối). Factual có nhiều
worst_metric = answer_relevancy (12) chủ yếu vì answer ngắn đúng nhưng câu hỏi sinh ngược với
`strictness = 1` không khớp hoàn toàn câu gốc — đó là nhiễu của metric hơn là lỗi nghiêm trọng
(factual vẫn có avg cao nhất).

Đề xuất sửa và cách kiểm chứng:
1. Đổi system prompt generation: "Trả lời phần có trong context, nêu rõ phần không tìm thấy; ưu tiên
   phiên bản chính sách mới nhất". Chạy lại `setup_answers.py --live` rồi Phase A; kỳ vọng số câu
   "Không tìm thấy." giảm từ 8 và faithfulness multi_hop tăng từ 0.487.
2. Tăng `RERANK_TOP_K` từ 3 lên 5 cho câu multi-hop; so sánh context_recall multi_hop (0.804) trước/sau.
3. Chunk theo cấu trúc bảng/ngưỡng (structure-aware) cho `mua_sam.md` và `nghi_phep_dac_biet.md`
   để ID 5 và ID 8 lấy đúng đoạn ngưỡng; kiểm tra context_recall của hai câu này > 0.

## Bẫy adversarial và giới hạn

Adversarial mean 0.787 **thấp hơn** factual 0.841 (cao hơn multi_hop 0.729). Worst_metric của
adversarial chủ yếu là context_recall (6/10, recall trung bình 0.717 — thấp nhất ba nhóm): bẫy phiên
bản (`nghi_phep_nam_v2023` vs `v2024`, `mat_khau_v1` vs `v2`) làm retriever kéo cả chunk của phiên
bản cũ vào top 3, chiếm chỗ của chunk cần thiết. Trong bottom 10 có hai bẫy adversarial:
ID 48 (negation trap — PVI chỉ dành cho nhân viên chính thức, tài liệu không nêu exclusion) và ID 50
(policy contradiction — câu hỏi nghe hợp lý nhưng VPN cá nhân bị cấm). Ở cả hai, pipeline **không**
rơi vào bẫy theo hướng trả lời sai ("có"), mà từ chối — an toàn hơn nhưng vẫn không trả lời được.
Điểm adversarial thấp hơn chỉ cho thấy nhóm này khó hơn, không tự chứng minh pipeline nhận ra
version conflict; chỉ đọc answer từng câu mới kết luận được như trên.

Giới hạn: 50 câu (10 adversarial) là mẫu nhỏ; RAGAS chấm bằng cùng họ model với generation
(gpt-4o-mini) nên có thể thiên vị; `strictness = 1` làm answer_relevancy nhiễu hơn; hai PDF scan
không có trong corpus nên câu nào cần chúng sẽ thiếu context. Không có fallback trong lượt chạy này.
