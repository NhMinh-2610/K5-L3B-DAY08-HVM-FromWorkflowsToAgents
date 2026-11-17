# Phân công Lab 8 LogiX-VN cho nhóm 3 người

Mỗi người phụ trách một shape và có thể bắt đầu song song. Swarm có sẵn để đối chứng. Cả nhóm dùng Python 3.11–3.13 theo hướng dẫn và chạy các lệnh của lab trong `src/`.

## Phần việc của từng người

| Người | Code và test | Báo cáo và bàn giao |
| --- | --- | --- |
| **1 — Workflow và tích hợp** | Viết [`workflow.py`](src/lab8/shapes/workflow.py). Tính quote từ dữ liệu đơn bằng `compute_compensation`, rồi truyền quote đầy đủ cho host. Thêm test approval của claim khác bị từ chối và có audit `policy_denied`. | Merge ba nhánh, chạy benchmark và crash suite, cập nhật [`TEAM.md`](TEAM.md), chốt commit và push bài. |
| **2 — Single Agent và báo cáo** | Viết [`single.py`](src/lab8/shapes/single.py) bằng `run_react`, tối đa 8 bước. Agent chỉ dùng tool đọc. Ghi model call vào `Budget`. Thêm test ticket khai sai số ngày trễ, kiểm tra kết quả theo dữ liệu đơn. | Tổng hợp [báo cáo nhóm](report/team/group_report.md). Điền [research card](report/team/research_card.md) theo R2. So sánh Swarm khi bật và tắt khả năng dùng số ngày trễ từ ticket, giữ nguyên model, tool có sẵn, corpus, seed, giá và bộ chấm. Ghi lệnh đã chạy, run ID và số liệu đo được. |
| **3 — Orchestrator và bảo mật** | Viết [`orchestrator.py`](src/lab8/shapes/orchestrator.py) bằng `make_handoff` và `run_readonly_investigators`. Investigator chỉ đọc, orchestrator gọi host để hoàn tiền. Thêm test handoff và trace sạch khi claim chứa `CANARY_SECRET_*`. | Rà approval và trace của cả ba shape. Tự kiểm khi có `student_drop`, rồi điền [ADR](report/team/decision_adr.md) từ benchmark và kết quả kiểm tra. |

Cả ba giữ chữ ký `run_claim`, dùng `common.finish()` để tạo kết quả và trace cả khi trả sớm, truyền `crash_at` cho `durability.issue_refund` và để `InjectedCrash` lan ra. Mỗi người có ít nhất một commit kỹ thuật, một test đã thêm hoặc sửa và một [báo cáo cá nhân](report/team/MSSV_HoTen.md) mang MSSV và họ tên của mình. [Contract](docs/contracts.md) · [Luật nghiệp vụ](docs/business_rules.md)

## Checklist bàn giao

1. **CP1–CP3:** Cả nhóm chạy smoke và cổng host. Mỗi người chạy `python -m pytest -q -m student -o addopts= -k <shape>`, thay `<shape>` bằng `workflow`, `single` hoặc `orchestrator`. Bàn giao khi 62 test có sẵn cho shape và test riêng đều xanh, gồm T11 gọi lại và T12 crash rồi chạy lại.
2. **CP4:** Người 1 chạy `python -m lab8.crash_test --count 20 --out reports/crash.json` và kiểm tra `20/20`. Người 3 rà việc hoàn tiền khi thiếu approval hợp lệ, rò secret và ghi trùng khi crash. Dùng T11/T12 để kiểm tra từng shape vì crash suite chủ yếu kiểm host.
3. **CP5:** Người 1 chạy benchmark cả bốn shape trên bộ public với seed `11,22,33,44,55` và commit hai JSON do công cụ sinh. Người 2 lấy số liệu cho báo cáo. Người 3 ưu tiên shape ít tự chủ nhất đáp ứng yêu cầu và điền số liệu, commit hash, run ID vào ADR. Ngưỡng hidden chính thức là **pass rate ≥ 0,75**. [Lệnh tạo báo cáo](src/reports/README.md)
4. **Trước khi nộp:** Cả nhóm kiểm tra bảng đóng góp có đủ ba dòng và ba báo cáo cá nhân. Người 1 chạy `python -m pytest -q` và `python -m lab8.check_submission`, xác nhận `0 FAIL` rồi push. Cả ba tự nộp cùng link repo trên LMS. [Checkpoints](CHECKPOINTS.md) · [Hướng dẫn nộp](SUBMISSION.md)

Ưu tiên phần bắt buộc. Tên repo hiện có `L3B`, mẫu nộp ghi `L3A`. Người 1 đối chiếu quy ước của lớp với coach trước khi chốt tên nộp.
