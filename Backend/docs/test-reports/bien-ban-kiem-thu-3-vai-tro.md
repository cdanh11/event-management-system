Người thực hiện: Nguyễn Tuấn Đạt (3123410070)
Ngày thực hiện: 6/11/2026
Commit được kiểm thử: cb8145b6784d09c4ab566b7f3bd5bb877c65acc6
Môi trường: Windows 11, Version 25H2, OS Build 26200.9711/ Git git version 2.49.0.windows.1/ Python: Python 3.13.2 /Node: v22.20.0/ Docker: Docker Compose version v5.6.0
 
| Mã | Kịch bản | Kết quả mong đợi | Kết quả thực tế | Ảnh |
|------|----------|------------------|-----------------| -----------------|
| TC01 | Đăng nhập user1 / 123456 | 200, có access_token | 200, có access_token | img/TC01.png |
| TC02 | Đăng nhập sai mật khẩu | 401 INVALID_CREDENTIALS | 401 Unauthorized | img/TC02.png |
| TC03 | user1 gọi POST /events | 403 FORBIDDEN | 403 Forbidden | img/TC03.png |
| TC04 | organizer1 tạo sự kiện capacity = -5 | 422 VALIDATION_ERROR | 422 VALIDATION_ERROR | img/TC04.png |
| TC05 | organizer1 tạo sự kiện hợp lệ | 201, trạng thái DRAFT | 201 Created, sự kiện được tạo với trạng thái DRAFT | img/TC05.png |
| TC06 | user1 đăng ký sự kiện DRAFT | 400 | 400 Bad Request, không thể đăng ký sự kiện DRAFT | img/TC06.png |
| TC07 | Công bố sự kiện rồi user1 đăng ký | 201, vé mã EV-… | 201 Created, đăng ký thành công, có mã vé EV-6CFBEB955F04466FB91CBF25 | img/TC07.png |
| TC08 | user1 đăng ký lại cùng sự kiện | 409 ALREADY_REGISTERED | 409 Conflict, ALREADY_REGISTERED | img/TC08.png |
| TC09 | Check-in vé VALID của sự kiện STARTED | 201 | 201 Created, check-in thành công, vé đã được sử dụng | img/TC09.png |
| TC10 | Check-in lại cùng vé | 409 TICKET_ALREADY_USED | 409 Conflict, TICKET_ALREADY_USED | img/TC10.png |
| TC11 | Check-in khi sự kiện chưa STARTED | 400 CHECKIN_CLOSED | 400 Bad Request, CHECKIN_CLOSED | img/TC11.png |
| TC12 | STAFF không được phân công check-in | 403 FORBIDDEN | 403 Forbidden, FORBIDDEN | img/TC12.png |
| TC13 | Hủy đăng ký vé chưa dùng ở sự kiện PUBLISHED | 200, số đăng ký giảm 1 | 200 OK, hủy đăng ký thành công, registered_count giảm 1 | img/TC13.png |
| TC14 | Mở chi tiết sự kiện ở 2 tab, đăng ký ở tab 1 | Tab 2 cập nhật số chỗ không cần tải lại | Tab 2 tự động cập nhật số chỗ còn lại không cần tải lại | img/TC14a.png,img/TC14b.png |