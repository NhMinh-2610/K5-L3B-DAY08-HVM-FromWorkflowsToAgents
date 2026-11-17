# Decision record

Quyết định dựa trên benchmark public của commit triển khai dưới đây. Các số
liệu không phải điểm hidden chính thức.

- Shape chọn: workflow
- Commit hash: 44d149e
- Run id dẫn chứng: R-workflow-C-001-s11; R-workflow-C-014-s55; R-orchestrator-C-001-s11; R-swarm-C-002-s55 (src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: public 1.0 / 1.0 / 1.0–1.0 / 0.0; 14 claim × 5 seed, 70/70 trial
- Cost per success (mô phỏng, VND): 34.285714285714285
- Crash safety: 20/20 (src/reports/crash.json, suite host + swarm); T11/T12 của cả bốn shape qua ma trận student; orchestrator qua thêm cả 3 cửa sổ crash trong test nhóm
- Secret leak / approval bypass: public 0 / 0; PII leak 0, trace contract failures 0 (src/reports/orchestrator_security.json); hidden chưa được chấm

## Vì sao shape này

Workflow, single và orchestrator đều đạt 70/70 trial public, pass^5 bằng 1
và variance bằng 0. Nhóm chọn workflow vì các bước được xác định bằng code,
không cần gọi model, phù hợp nguyên tắc chọn kiến trúc ít tự chủ nhất vẫn làm
được việc. Audit public không ghi nhận leak hoặc bypass ở shape này. Quyết định
dựa trên bằng chứng public; điều kiện hidden chính thức vẫn cần giảng viên chấm.

Số liệu lấy từ `src/reports/benchmark.json`, mỗi trial có SQLite mới, cùng
MockLLM, ngày policy 2026-11-15, seed 11/22/33/44/55, corpus và bảng giá.

| Shape | Trial pass | Pass rate | Pass^5 | Seed min–max | Variance | VND/success | Mean / p95 events |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| workflow | 70/70 | 1 | 1 | 1–1 | 0 | 34.285714 | 4.428571 / 5 |
| single | 70/70 | 1 | 1 | 1–1 | 0 | 32.255714 | 4.642857 / 5 |
| orchestrator | 70/70 | 1 | 1 | 1–1 | 0 | 57.23 | 6 / 7 |
| swarm | 69/70 | 0.985714 | 0.928571 | 0.928571–1 | 0.000816327 | 49.566957 | 2.8 / 3 |

## Có đáng đổi lấy multi-agent không

Trên tập public, orchestrator không tăng pass rate so với workflow. Orchestrator
có ranh giới investigator đọc rõ ràng nhưng thêm lượt đọc claim, policy và lịch
sử refund. Swarm fail
`C-002`, seed 55, do lấy số ngày trong ticket thay cho order. Đổi sang multi-agent
khi tập đánh giá rộng hơn chứng minh lợi ích đủ lớn về chất lượng hoặc yêu cầu
tách trust/deploy, trong khi vẫn qua approval, leak và crash gates. Không kết
luận multi-agent luôn kém từ 14 claim và MockLLM.

## Trace và bằng chứng

Trace orchestrator ghi `claim`, `handoff`, `investigator`, `quote`,
`refund_request`, `refund_outcome`, `decision` theo nhánh. Handoff đi qua
`make_handoff`, `facts={}`, chỉ giao tool đọc. Trace không ghi ticket, parent
context, header, phone, address, internal note hoặc item name. `common.finish`
lấy effect/audit từ ledger, ghi JSON mới với run ID đúng ở mọi nhánh return.
Trace được flush trước side effect; crash truyền ra ngoài và connection luôn đóng.
Reason từ host và hàm quote được lọc qua danh sách mã cố định trước khi ghi trace
hoặc trả kết quả. Reason bất thường được đổi thành `policy_denied` hoặc
`no_entitlement`, tránh đưa giá trị status trong DB ra ngoài.

Audit public quét kết quả, trace, mọi file cùng thư mục có tiền tố run ID và
stdout/stderr trên 280 trial. Cả bốn shape có leak/bypass/trace errors bằng 0
trong phạm vi public. Bốn ca bổ sung cài secret hoặc PII vào approval status và
order status đã tái hiện rò dữ liệu trước bản vá, rồi pass sau bản vá.
Không sinh debug file ngoài phạm vi scanner. Chi tiết allowlist và phạm vi
kiểm chứng nằm trong `orchestrator_security.md`.

Kiểm thử trên commit `44d149e`: cổng mặc định 84 passed, 248 deselected;
ma trận student đầy đủ 248 passed, 84 deselected.

Các lệnh tái lập, chạy trong `src/` sau khi kích hoạt môi trường ảo:

```text
python -m pytest -q --basetemp=.pytest_cache/tmp
python -m pytest -q -m student -o addopts= --basetemp=.pytest_cache/tmp-student
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
python -m lab8.crash_test --count 20 --out reports/crash.json
python -m tests.audit_team_security --out reports/orchestrator_security.json
```

## Giới hạn

MockLLM không phải model sản xuất; cost là mô phỏng, latency là `unavailable`.
Steps đếm event do từng tracer ghi, không đồng nghĩa với số lượt model/tool;
cần đọc thêm `mean_model_calls` và `mean_tool_calls` khi so topology.
Workflow tính `issue_refund` vào tool call, còn single và orchestrator không.
Vì vậy chi phí hiện tại chịu ảnh hưởng của cách đếm, không chỉ topology. Các số
trong bảng được giữ nguyên từ benchmark; lựa chọn workflow dựa vào mức tự chủ
và kết quả xử lý, không dựa vào kết luận rằng workflow rẻ nhất.
Public benchmark không xác nhận ngưỡng hidden ≥ 0.75 trên 40 × 5 trial.
Chưa có `student_drop/` tại thời điểm tự kiểm. Khi có pack không nhãn, dùng lệnh
dưới để kiểm status/trace/leak; không suy ra pass rate từ pack không nhãn:

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator --cases student_drop/hidden_claims.jsonl --world student_drop/hidden_world_state.json --seeds 11,22,33,44,55 --out reports/hidden_selfcheck.json
```

Shape chọn chỉ đạt cổng chính thức sau khi giảng viên chấm hidden và xác nhận
approval bypass/secret leak bằng 0 cùng crash safety. JSON bằng chứng được sinh
bằng công cụ, không sửa tay.
