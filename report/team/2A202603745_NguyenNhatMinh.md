# Báo cáo cá nhân — 2A202603745_NguyenNhatMinh

## 1. Thông tin thành viên

- Họ tên: Nguyễn Nhật Minh
- MSSV: 2A202603745
- Email: nnhatminh2610@gmail.com
- GitHub: NhMinh-2610

## 2. Phần việc phụ trách

Shape C `orchestrator`; handoff chỉ đọc; trace và kiểm tra rò secret/PII;
kiểm crash/idempotency; quyết định kiến trúc trong `decision_adr.md`.

## 3. Đóng góp cụ thể

- Commit triển khai ban đầu: `a06249f`; bản vá bảo mật và test hồi quy: `44d149e`.
- Hoàn thiện `src/lab8/shapes/orchestrator.py`: đọc claim an toàn, giao tool đọc
  cho investigator, quote từ order view, gọi host với quote đầy đủ và trả qua
  `common.finish()`. Không dùng ticket làm nguồn quyết số tiền.
- Truyền `crash_at`, để crash truyền ra ngoài, đóng connection trong `finally`.
- Bổ sung 19 trường hợp test trong `src/tests/test_team_orchestrator.py`, bao
  gồm secret/PII nằm cả trong ticket, approval thiếu/sai claim, ba điểm crash,
  replay, quote thay đổi gây conflict, trần theo đơn và trace ở nhánh sớm.
- Kiểm tra hai đường rò dữ liệu qua approval status và order status. Bốn ca cài
  secret hoặc PII đều fail trước bản vá. Sau khi lọc reason bằng danh sách mã
  được phép, cả bốn ca đều pass và không phát sinh refund.
- Viết `src/tests/audit_team_security.py` để tái lập audit public cho cả bốn shape.
  Tài liệu allowlist và field cấm: `orchestrator_security.md`.
- Tổng hợp benchmark, crash và audit sau tích hợp vào ADR; chọn workflow vì
  không cần model mà vẫn đạt cùng kết quả public với hai shape còn lại.

## 4. Bằng chứng

Các lệnh chạy trong `src/`, sau khi kích hoạt môi trường ảo:

| Lệnh | Kết quả |
| --- | --- |
| `python -m pytest -q --basetemp=.pytest_cache/tmp` | 84 passed, 248 deselected; gồm 19 ca test riêng của orchestrator |
| `python -m pytest -q -m student -o addopts= --basetemp=.pytest_cache/tmp-student` | 248 passed, 84 deselected; đủ bốn shape, mỗi shape 62 ca |
| `python -m lab8.crash_test --count 20 --out reports/crash.json` | 20/20; suite host + swarm |
| `python -m tests.audit_team_security --out reports/orchestrator_security.json` | 280 trial; secret/PII/approval bypass/trace errors đều 0 |
| `python -m lab8.check_submission` | 0 FAIL |

`src/reports/benchmark.json`: orchestrator 70/70 public, pass rate/pass^5 = 1/1,
seed variance = 0, cost/success = 57.23 VND mô phỏng. Run ID minh họa:
`R-orchestrator-C-001-s11`, `R-orchestrator-C-002-s55`.
Kết quả benchmark và audit được sinh bằng công cụ; không sửa JSON bằng tay.

Trên máy Windows, pytest mặc định gặp lỗi quyền truy cập thư mục temp dùng
chung. `--basetemp=.pytest_cache/tmp` chuyển dữ liệu tạm vào thư mục riêng của
dự án; không sửa host, metric, policy hoặc fixture để vượt test.

## 5. Công cụ AI đã dùng

Codex được dùng để hỗ trợ viết code, test, đọc trace và tổng hợp báo cáo.
Kết quả được kiểm tra bằng pytest, crash suite và audit trên DB tạm. Số liệu
lấy từ report do công cụ sinh. Phần chạy lab dùng MockLLM offline theo đề bài.

## 6. Tự đánh giá

Phần orchestrator đã qua ma trận public và kiểm tra bổ sung về ranh giới bảo mật,
retry và ba cửa sổ crash. Audit chỉ chứng minh phạm vi dữ liệu và output đã quét.
Chưa có bộ hidden hoặc `student_drop/` để kết luận điểm hidden. Workflow đã
được tích hợp và được chọn trong ADR dựa trên bằng chứng public.
Khả năng giải thích trực tiếp kiến trúc và ranh giới code/model phải được kiểm
tra độc lập với các test tự động.

Kiểm thử bổ sung cho thấy dữ liệu nhạy cảm còn có thể đi qua lý do do host tạo,
ngay cả khi handoff đã sạch. Vì vậy việc lọc dữ liệu cần được thực hiện ở cả
ranh giới giao việc và đầu ra. Kết quả hiện tại chỉ bao phủ các ca đã chạy;
ngưỡng hidden và việc giải thích trực tiếp kiến trúc vẫn phải kiểm tra riêng.
