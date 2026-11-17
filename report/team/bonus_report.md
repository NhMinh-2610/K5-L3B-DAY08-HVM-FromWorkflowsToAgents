# Bonus report: B3

**Topic và nguồn** · Verifier chống khuếch đại lỗi. Google Research 2026, *Towards a Science of Scaling Agent Systems*, slide 17, 22 và 42.

**Claim và phạm vi** · Nghiên cứu ghi nhận mức khuếch đại lỗi 17,2× với agent độc lập và 4,4× với orchestration tập trung. LogiX dùng MockLLM và lỗi cài sẵn theo seed để kiểm tra cơ chế verifier chặn lỗi trước khi ghi tiền. Hai hệ số trên thuộc thiết lập LLM thật của nghiên cứu.

**Giả thuyết** · Verifier đưa pass rate của swarm về bằng workflow và seed variance về 0 trên cả hai tập. Chi phí mỗi trial thành công dự kiến tăng khoảng 10 VND so với swarm.

**Thiết lập** · Ba shape chạy cùng claim, seed, MockLLM, host, bảng giá và evaluator, với một SQLite mới mỗi trial. Bản `swarm_verified` giữ cơ chế swarm và thêm một lượt đọc đơn để đối chiếu 5 trường dùng tính quote. Nếu lệch, verifier tính lại quote một lần và ghi `verifier_override`. Bản này cũng lọc mã từ chối của host qua allowlist. Bộ đối kháng có 12 claim viết tay theo luật nghiệp vụ, với giải thích nhãn trong [cases.jsonl](../../src/bonus/cases.jsonl) và dữ liệu đơn trong [world.json](../../src/bonus/world.json).

## Lệnh tái lập

Chạy trong `src/`. Code B3 ở commit `02bda52` (PR #7).

```text
python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --seeds 11,22,33,44,55 --out reports/bonus_benchmark_public.json
python -m lab8.benchmark --shapes workflow,swarm,swarm_verified --extra-shape swarm_verified=bonus.swarm_verified:run_claim --cases bonus/cases.jsonl --world bonus/world.json --seeds 11,22,33,44,55 --out reports/bonus_benchmark_adversarial.json
python -m bonus.count_overrides --out reports/bonus_verifier.json
python -m pytest -q tests/test_bonus_swarm_verified.py
```

## Kết quả

| Bộ | Shape | Pass rate | Pass^5 | Variance | VND/success | Model / tool mỗi trial | Hoàn sai |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Public | workflow | 1,000 (70/70) | 1,000 | 0 | 34,29 | 0 / 3,43 | 0 |
| Public | swarm | 0,986 (69/70) | 0,929 | 0,000816 | 49,57 | 3 / 4,66 | 1 |
| Public | swarm_verified | 1,000 (70/70) | 1,000 | 0 | 57,57 | 3 / 5,53 | 0 |
| Đối kháng | workflow | 1,000 (60/60) | 1,000 | 0 | 31,67 | 0 / 3,17 | 0 |
| Đối kháng | swarm | 0,917 (55/60) | 0,583 | 0,027778 | 54,08 | 3 / 4,72 | 3 |
| Đối kháng | swarm_verified | 1,000 (60/60) | 1,000 | 0 | 59,24 | 3 / 5,68 | 0 |

Cả ba shape có **0 secret leak và 0 PII leak** trên hai tập. “Hoàn sai” đếm các claim có refund dù nhãn yêu cầu 0 refund. Các ca này có approval hợp lệ. [Benchmark public](../../src/reports/bonus_benchmark_public.json), [benchmark đối kháng](../../src/reports/bonus_benchmark_adversarial.json), [thống kê verifier](../../src/reports/bonus_verifier.json)

Verifier can thiệp **1/70** trial public và **8/60** trial đối kháng, đều do sai `delay_days` ở seed 55. Trên tập đối kháng, 5 lần đổi quyết định gồm 3 ca chặn hoàn sai và 2 ca khôi phục khoản hoàn hợp lệ. Ba lần còn lại giữ nguyên số tiền.

**Trace minh họa** · Trong `R-swarm_verified-B-02-s55`, model đọc trễ 1 ngày từ ticket. Sự kiện `verifier_override` ghi trường `delay_days` và số tiền đổi từ 0 lên 30.000 VND, rồi quote áp dụng điều khoản `SHIP-LATE-03`. Run public tương ứng là `R-swarm_verified-C-002-s55`.

## Kết luận và giới hạn

Verifier đạt độ đúng và variance như giả thuyết. Chi phí mỗi trial thành công tăng **8,01 VND** trên public và **5,16 VND** trên tập đối kháng so với swarm. So với workflow, số tool call mỗi trial gấp **1,61×** và **1,79×**, cộng thêm 3 model call. Quyết định tiền dựa trên dữ liệu đơn và cùng hàm tính quote như workflow. Swarm còn soạn câu trả lời, phần nằm ngoài tiêu chí chấm của benchmark.

Khi ticket đúng và dữ liệu đơn đã cũ, verifier có thể ghi đè dữ kiện đúng. Lượt đọc lại cũng có thể bỏ sót lỗi ở ngoài các trường được đối chiếu, ví dụ model chọn sai điều khoản. MockLLM, lỗi cài sẵn theo seed và tập mẫu nhỏ giới hạn khả năng suy rộng. Chi phí được mô phỏng, latency không được đo và nhãn đối kháng chưa được rà độc lập.

Điểm bonus phụ thuộc vào kết quả hidden của workflow (≥ 0,80 và qua ba must-pass) cùng kết quả safety của `swarm_verified` do giảng viên chấm.
