# Đăng nhập và phiên

Trang /login hỗ trợ đăng nhập, tạo tài khoản ATTENDEE và chọn tài khoản demo. /register chuyển tới chế độ đăng ký. Access token ở bộ nhớ; refresh token ở cookie HttpOnly. User lưu cục bộ để hiển thị, không dùng làm căn cứ phân quyền backend.

AuthProvider phục hồi phiên trước khi route quyết định chuyển trang. apiClient refresh khi request bảo vệ nhận 401; các request đồng thời dùng chung một promise. Lỗi sai mật khẩu không kích hoạt refresh. Refresh thất bại xóa phiên và đưa người dùng về login. Logout gọi API thu hồi refresh cookie rồi xóa trạng thái client.

| Role | Trang chủ |
| --- | --- |
| ATTENDEE | /events |
| STAFF | /staff |
| ORGANIZER | /organizer |

RoleGuard đưa người chưa login về /login, người sai role tới thông báo thiếu quyền. URL được nhớ sau login phải thuộc role của tài khoản vừa đăng nhập.

Demo các tài khoản độc lập bằng browser profile hoặc cửa sổ riêng; các tab cùng origin/profile dùng chung cookie và localStorage.
