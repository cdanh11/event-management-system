# Validation và hợp đồng lỗi

FastAPI bind request vào Pydantic trước khi chạy endpoint. Field kiểm tra email, độ dài, capacity dương; field_validator trim text và chuẩn hóa thời gian; model_validator kiểm tra end sau start. PATCH cho phép bỏ field nhưng không chấp nhận null cho cột NOT NULL.

| HTTP | Ý nghĩa và ví dụ |
| --- | --- |
| 422 VALIDATION_ERROR | Payload sai kiểu/thiếu field, text rỗng, capacity âm, end trước start, PATCH null |
| 400 | Quy tắc nghiệp vụ: thời gian đã qua, registration/cancellation đóng, transition sai, check-in đóng hoặc WRONG_EVENT |
| 401 | Thiếu/sai/hết hạn token hoặc refresh cookie |
| 403 | Sai role hoặc không có quyền trên tài nguyên |
| 404 | Event, registration, ticket hoặc cursor không tồn tại |
| 409 | Đăng ký trùng/đầy, email trùng, staff đã gán, vé đã dùng hoặc capacity dưới số đăng ký |
| 502 NOTIFICATION_FAILED | Notify thủ công không gọi webhook thành công |

Body lỗi HTTP: `{status, code, message}`. Body 422 thêm `details`, gồm vị trí và nguyên nhân field lỗi. Handler giữ headers của HTTPException và dùng jsonable_encoder để ValueError trong ctx.error không gây lỗi JSON serialization.

PATCH chỉ gửi một mốc giờ: endpoint ghép giá trị DB rồi kiểm tra, trả 400 khi lịch không hợp lệ. Pydantic không đọc DB. Lịch STARTED/COMPLETED/CANCELLED không cho sửa qua API, kể cả client bỏ qua frontend.

Thử Swagger: end trước start → 422; start quá khứ → 400; thiếu Bearer → 401; attendee tạo event → 403; đăng ký trùng → 409. Schema lỗi 422 được gắn ở router tổng; auth/error responses được khai báo cho các route chính, không khẳng định mọi mã lỗi của mọi route đã được liệt kê trong OpenAPI.
