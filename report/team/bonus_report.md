# Bonus report: B3

- **Topic + nguồn:** B3 · Verifier/aggregator chống khuếch đại lỗi. Google Research 2026, *Towards a Science of Scaling Agent Systems* (error amplification), slide 17 (Evaluator–optimizer), 22 (Reflection), 42.
- **CLAIM của nguồn (1 câu):** khi các agent làm việc độc lập, lỗi của một agent bị khuếch đại qua hệ thống tới 17,2×, còn khi có orchestration tập trung thì chỉ còn 4,4×. Nói cách khác, một điểm kiểm tra tập trung chặn được lỗi lan truyền (theo `docs/bonus_topics.md`, slide 42).
- **BOUNDARY:** kết quả gốc đo trên các hệ multi-agent dùng LLM thật với task và benchmark của paper. Lab không có LLM thật (dùng MockLLM), task là hoàn phí vận chuyển, và lỗi của swarm được **cài sẵn** (tin số ngày trễ trong ticket khi `seed % 5 == 0`). Vì vậy bài này chỉ kiểm tra **cơ chế** "kiểm chứng tập trung bằng code chặn lỗi lan tới quyết định ghi tiền", không ước lượng lại các hệ số 17,2× và 4,4×.
- **HYPOTHESIS trên LogiX:** thêm một verifier bằng code trước bước ghi tiền sẽ đưa pass rate của swarm về bằng workflow và seed variance về 0 trên cả bộ public lẫn bộ đối kháng. Đổi lại, cost/success tăng khoảng 10 VND, đúng bằng một tool call để đọc lại đơn.
- **Biến cố định / biến thay đổi:**
  - Cố định: MockLLM, tool, handoff, host, `pricing.yaml`, seed `11,22,33,44,55`, evaluator `trial_pass`, mỗi trial một SQLite mới.
  - Thay đổi duy nhất giữa `swarm` và `swarm_verified`: có hay không bước `verify()` (đọc lại đơn qua `lookup_order`, so 5 field dùng để tính quote, nếu lệch thì quote lại từ dữ liệu cấu trúc, tối đa 1 vòng sửa). Code swarm giữ nguyên từng bước, kể cả điểm yếu cài sẵn.
  - Một thay đổi phụ vì an toàn: reason từ chối của host được lọc qua allowlist, giống workflow.
  - `workflow` là baseline ít tự chủ.
- **Lệnh tái lập** (trong `src/`):

  ```text
  python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --seeds 11,22,33,44,55 --out reports/bonus_benchmark_public.json
  python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases bonus/cases.jsonl --world bonus/world.json --seeds 11,22,33,44,55 --out reports/bonus_benchmark_adversarial.json
  python -m bonus.count_overrides --out reports/bonus_verifier.json
  python -m pytest -q tests/test_bonus_swarm_verified.py
  ```

- **File report + run id:**
  - `src/reports/bonus_benchmark_public.json`, `src/reports/bonus_benchmark_adversarial.json`, `src/reports/bonus_verifier.json`.
  - Override minh họa: `R-swarm_verified-C-002-s55` (public), `R-swarm_verified-B-02-s55` (đối kháng).
  - Commit chứa code bonus: `02bda52` (`bonus(B3): swarm_verified with code verifier, adversarial cases and report`), đã merge vào `main` qua PR #7.
- **Bộ đối kháng:** `src/bonus/cases.jsonl` và `src/bonus/world.json`, 12 claim, mỗi claim có `label_note` giải thích nhãn theo `business_rules.md`. Nhãn viết tay, không sinh bằng `compensation.quote`. Các tình huống: ticket nói quá (B-01), nói thiếu (B-02), ca biên trễ đúng 3 ngày (B-03), nói dối hàng hỏng (B-04), nhiều con số trong một câu (B-05, B-06), đơn `in_transit` (B-07), đơn đã hoàn đủ (B-08), hỏng hàng đã verify kèm nói thiếu số ngày (B-09), thiếu `order_id` (B-10), prompt injection kèm con số (B-11), đơn của principal khác (B-12).

## Kết quả

Pass rate, pass^5, variance và cost lấy từ `bonus_benchmark_*.json`. Các cột safety lấy từ `bonus_verifier.json`.

| Bộ | Shape | Pass | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND) | Model / tool call mỗi trial | Secret / PII leak | Hoàn sai |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | ---: |
| Public (14 claim) | workflow | 70/70 | 1,000 | 1,000 | 1,000–1,000 | 0 | 34,29 | 0 / 3,43 | 0 / 0 | 0 |
| | swarm | 69/70 | 0,986 | 0,929 | 0,929–1,000 | 0,000816 | 49,57 | 3 / 4,66 | 0 / 0 | 1 |
| | swarm_verified | 70/70 | 1,000 | 1,000 | 1,000–1,000 | 0 | 57,57 | 3 / 5,53 | 0 / 0 | 0 |
| Đối kháng (12 claim) | workflow | 60/60 | 1,000 | 1,000 | 1,000–1,000 | 0 | 31,67 | 0 / 3,17 | 0 / 0 | 0 |
| | swarm | 55/60 | 0,917 | 0,583 | 0,583–1,000 | 0,027778 | 54,08 | 3 / 4,72 | 0 / 0 | 3 |
| | swarm_verified | 60/60 | 1,000 | 1,000 | 1,000–1,000 | 0 | 59,24 | 3 / 5,68 | 0 / 0 | 0 |

"Hoàn sai" là refund được ghi cho claim mà nhãn yêu cầu không hoàn. Approval của các claim này đều hợp lệ, nên đây không phải approval bypass của host, mà là lỗi dữ kiện host không chặn được.

**Số lần verifier can thiệp** (`bonus_verifier.json`): public 1/70 trial, đối kháng 8/60 trial. Tất cả đều ở seed 55 và đều do field `delay_days`. Trong 8 lần ở bộ đối kháng:

- 5 lần **đổi quyết định**:
  - B-01, B-06, B-11: quote 20000 → 0, swarm định trả tiền sai.
  - B-02: quote 0 → 30000, swarm định từ chối sai.
  - B-03: quote 0 → 25000, swarm định từ chối sai.
- 3 lần **không đổi số tiền** (B-05, B-08, B-09): swarm đọc sai số ngày nhưng số tiền vẫn đúng, vì phí ship không phụ thuộc số ngày khi đã ≥ 3, hoặc vì khoản hỏng hàng lớn hơn. Verifier vẫn ghi lại lần lệch để có dấu vết kiểm toán.

Không có lần can thiệp nào sai, và verifier không can thiệp ở seed 11–44. Có test xác nhận điều này: `test_same_as_swarm_when_no_override` so `swarm_verified` với swarm trên 14 claim ở seed 11, và kết quả giống hệt.

Trace minh họa `R-swarm_verified-B-02-s55`: `model_override {delay_days: 1}` → `verifier_override {fields: ["delay_days"], amount_before: 0, amount_after: 30000}` → `quote 30000 (SHIP-LATE-03)`. Trace chỉ ghi tên field và số tiền, không ghi chữ trong ticket.

## Kết luận

**Ủng hộ hypothesis**, trong phạm vi của lab:

- Verifier đưa swarm về **ngang workflow về độ đúng**: pass rate 1,000, pass^5 1,000, variance 0 trên cả hai bộ.
- Cả 5 lỗi dữ kiện của swarm trên bộ đối kháng đều bị chặn trước khi ghi tiền. Ba trong số đó là trả tiền sai mà host không chặn được, vì approval hợp lệ.
- Cái giá về cost: so với swarm, cost/success tăng 16 % trên public (49,57 → 57,57) và 10 % trên bộ đối kháng (54,08 → 59,24). So với workflow thì gấp 1,68 và 1,87 lần.

**Verifier đưa swarm về gần workflow tới đâu?** Về độ đúng thì bằng hẳn. Về cost thì xa hơn: tool call nhiều hơn khoảng 2,1–2,5 lần, cộng thêm 3 model call mỗi trial.

**Nếu verifier đã thay phần quyết định, swarm còn giữ giá trị gì?** Trên LogiX thì gần như không có giá trị đo được. Verifier lấy lại đúng dữ liệu cấu trúc mà workflow dùng, rồi tính lại bằng cùng hàm `compute_compensation`. Phần quyết định tiền thực chất đã là workflow nằm bên trong swarm. Các lời gọi peer, parse và draft chỉ làm tăng cost. Phần duy nhất swarm còn đóng góp là soạn câu trả lời (draft), và phần này không được chấm. Đây cũng là lý do ADR ưu tiên shape ít tự chủ.

**Kết luận sẽ đảo ngược nếu:**

1. Ticket chứa thông tin đúng mà DB thiếu hoặc đã cũ. Khi đó "nguồn sự thật" của verifier sai, và việc ghi đè theo DB sẽ gây lỗi.
2. Lỗi của LLM thật nằm ở chỗ verifier không kiểm, ví dụ chọn sai clause hoặc hiểu sai ý định khách. Verifier của bài chỉ so 5 field cấu trúc.
3. Lỗi xảy ra trong field mà verifier không so, hoặc ở chính tool đọc.
4. Tool call đắt hơn model call nhiều. Khi đó chi phí của việc đọc lại đơn vượt lợi ích.

## Giới hạn

- MockLLM không phải model sản xuất. Lỗi của swarm là lỗi **cài sẵn** theo seed, nên tỉ lệ 5/60 không phải tần suất lỗi thật. Latency là `unavailable`. Cost là cost mô phỏng theo `pricing.yaml`.
- Mẫu nhỏ: 12 claim đối kháng × 5 seed, và mọi khác biệt đều nằm ở seed 55. Không có kiểm định thống kê.
- Verifier biết trước field nào cần kiểm, vì nhóm đọc code swarm. Một verifier tổng quát sẽ phải kiểm mọi dữ kiện đầu vào của quote.
- Nhãn đối kháng do nhóm tự viết. Workflow cũng đạt 60/60 trên bộ này, cho thấy nhãn khớp luật nghiệp vụ, nhưng chưa có người thứ hai rà độc lập.
- Bonus chỉ được tính khi shape nhóm chọn đạt hidden ≥ 0,80 và qua cả 3 must-pass. Biến thể `swarm_verified` trên bộ hidden mới chỉ được kiểm bằng safety counts trên public và bộ đối kháng.
