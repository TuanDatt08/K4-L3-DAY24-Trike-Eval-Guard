# Đánh giá LLM Judge Phase B

Nhóm: Trike

Người phụ trách: Lê Tuấn Đạt — 2A202602623

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T16:20:16Z.
Models generation/judge: generation `gpt-4o-mini-2024-07-18` (answer A); judge `gpt-4o-mini`
(`config.JUDGE_MODEL`, temperature 0, `response_format = json_object`).

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Pass 1 gửi (A, B); pass 2 gửi (B, A) với cùng question/reference, rồi winner và scores của pass 2
được quy về A/B gốc. Lưu ý: `reasoning_pass2` giữ nguyên văn của lượt swap nên chữ "Answer A" trong
đó chỉ answer B gốc.

| ID | Answer A (pipeline) | Answer B (model_answer) | winner_pass1 | winner_pass2 (quy về gốc) | final | consistent | scores pass1 A/B | scores pass2 A/B |
|---|---|---|---|---|---|---|---|---|
| 1 | Nghỉ 3 ngày làm việc khi kết hôn. | Nghỉ 3 ngày làm việc có lương khi kết hôn. | B | B | B | True | 0.8 / 1.0 | 0.8 / 1.0 |
| 5 | Cần Trưởng phòng và Kế toán trưởng. | Cần Giám đốc phòng ban phê duyệt. | tie | tie | tie | True | 0.0 / 0.0 | 0.0 / 0.0 |
| 12 | Thưởng Tết tối thiểu 1 tháng lương cho NV chính thức từ 6 tháng. | Thưởng Tết tối thiểu 1 tháng lương. | A | tie | tie | False | 1.0 / 0.5 | 1.0 / 1.0 |
| 21 | 18 ngày phép (15 + 3); lương "theo quy định công ty". | 18 ngày phép; lương Senior 20–35 triệu. | B | B | B | True | 0.8 / 1.0 | 0.8 / 1.0 |
| 41 | 15 ngày phép năm. | 12 ngày phép năm. | A | A | A | True | 1.0 / 0.0 | 1.0 / 0.0 |

Reasoning tóm tắt: ID 1 — B nêu "có lương" như reference. ID 5 — cả hai sai so với reference (đơn
> 50 triệu cần Tổng Giám đốc), judge cho 0/0 và tie, đúng hành vi mong muốn. ID 12 — pass 1 coi A
đầy đủ hơn vì nêu điều kiện "từ 6 tháng", pass 2 coi hai answer tương đương. ID 21 — B có khoảng
lương 20–35 triệu, A né phần lương. ID 41 — A đúng v2024 (15 ngày), B dùng chính sách v2023 đã bị
thay thế (12 ngày); cả hai lượt đều nhận ra bẫy phiên bản.

Position bias count/rate: 1/5 = 0.2.
Verbosity win rate: 0.333 (1/3); decisive cases: 3 (ID 1, 21, 41).

Case không nhất quán duy nhất (ID 12) là cặp mà hai answer cùng đúng mức thưởng, chỉ khác việc lặp lại
điều kiện "từ 6 tháng" của câu hỏi. Đây là case sát ranh giới tie, nên việc đổi winner khi đổi thứ tự
là dấu hiệu judge không chắc chắn hơn là bằng chứng thiên vị vị trí có hệ thống; swap-and-average đã
xử lý đúng bằng cách cho tie. Với verbosity: trong 3 case decisive, answer dài hơn chỉ thắng 1 lần
(ID 21) và ở case đó B thắng vì có khoảng lương — một ý thiết yếu của câu hỏi — chứ không phải vì dài.
ID 1 B dài hơn A một cụm "có lương" và đó cũng là nội dung có trong reference. Với 5 cặp, các tỷ lệ
trên chỉ là tín hiệu, không đủ để kết luận về bias.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| question_id | model_answer gốc | judge label | reasoning (rút gọn) | human_label | agree |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Đúng số ngày, đúng reference | 1 | yes |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Sai: > 50 triệu cần Tổng Giám đốc | 0 | yes |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Đúng mức thưởng | 1 | yes |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Đúng ngày phép và khoảng lương | 1 | yes |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Đúng: hoàn 100% khi chưa đủ 1 năm | 1 | yes |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu Kế toán trưởng; sai cách tính phạt | 0 | yes |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Đúng cả ngày phép và phụ cấp | 1 | yes |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Dùng chính sách cũ v2023 thay vì v2024 | 0 | yes |
| 46 | Thử việc không được nghỉ phép năm, phải xin nghỉ không lương. | 1 | Đúng phủ định theo reference | 1 | yes |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Sai: VPN cá nhân bị cấm | 0 | yes |

Cohen’s κ: 1.0.
Observed/chance agreement và diễn giải: p_o = 10/10 = 1.0; judge và human cùng có 6 nhãn 1 và 4 nhãn 0,
nên p_e = 0.6 × 0.6 + 0.4 × 0.4 = 0.52; κ = (1.0 − 0.52) / (1 − 0.52) = 1.0 — "almost perfect"
theo thang Landis–Koch, vượt ngưỡng bonus 0.6.

## Giới hạn và cách dùng judge

κ = 1.0 trên 10 nhãn không có nghĩa judge luôn đúng: mẫu nhỏ và phần lớn case có lỗi rõ ràng (sai
số, sai phiên bản, đảo phủ định) — loại lỗi dễ nhận ra khi có reference. Judge chưa được thử trên
case mơ hồ (answer đúng một phần, diễn đạt khác nhiều). Judge và generation cùng họ gpt-4o-mini nên
có rủi ro self-preference trong pairwise (A là output của gpt-4o-mini); ở 5 cặp này A thắng 1, B thắng
2, tie 2 nên chưa thấy dấu hiệu đó. Cách dùng đề xuất: luôn chạy swap-and-average cho pairwise,
coi tie do không nhất quán là "cần người xem", định kỳ lấy mẫu thêm nhãn người để đo lại κ, và không
dùng judge làm đáp án tuyệt đối khi thiếu reference.
