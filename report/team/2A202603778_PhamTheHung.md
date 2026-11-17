# Báo cáo cá nhân — Phạm Thế Hùng

## 1. Thông tin thành viên

- Họ tên: Phạm Thế Hùng
- MSSV: 2A202603778
- Email: 26ai.hungpt5@vinuni.edu.vn	
- GitHub: `thehung1406`

## 2. Phần việc phụ trách

Shape A `workflow`, tích hợp ba shape, chạy crash suite và benchmark công khai, cập nhật thông tin nhóm.

## 3. Đóng góp cụ thể

- Commit `3b87b6e` triển khai workflow Python cố định. Quote lấy từ dữ liệu đơn và được truyền đầy đủ vào `issue_refund` để host kiểm tra approval, trừ tiền đã hoàn theo đơn và chống ghi trùng.
- Trace ghi tên bước, trạng thái và mã lý do đã lọc. Trace không chứa ticket, số điện thoại, địa chỉ, tên hàng, ghi chú nội bộ hoặc secret.
- Thêm `test_workflow_rejects_approval_for_another_claim` và `test_workflow_retry_keeps_one_refund_and_audit`.

## 4. Bằng chứng

- Kiểm tra commit tích hợp `f1f5ede` trên Windows với Python 3.13.17. Bộ pytest mặc định có 84 test pass, ma trận public có 248 test pass. Trong đó `workflow` đạt 62/62, gồm T11 (chạy lại) và T12 (chạy lại sau crash).
- Chạy lại crash suite đạt `20/20`. [Kết quả crash suite](../../src/reports/crash.json)
- Benchmark public cho `workflow` đạt 70/70 trial trên 14 claim và 5 seed, `pass^5 = 1.0`, seed variance `0.0`, chi phí mô phỏng `34,29 VND` mỗi trial thành công. Run ID dẫn chứng `R-workflow-C-001-s11`. [Kết quả benchmark](../../src/reports/benchmark.json)

## 5. Công cụ AI đã dùng

Codex hỗ trợ lập kế hoạch, viết workflow và test, chạy bộ kiểm thử và chuẩn bị báo cáo. Đối chiếu kết quả bằng lệnh pytest và crash suite của repo, số liệu từ JSON do benchmark sinh.

## 6. Tự đánh giá

Hùng bổ sung sau khi tự kiểm bài.
