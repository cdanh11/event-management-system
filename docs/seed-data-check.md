# Đối chiếu bộ dữ liệu mẫu (seed)

Người thực hiện: Mai Thanh Duy — ngày 05/11/2026.
Mã nguồn kiểm tra: nhánh `main` tại commit `58c9e56` (bản niêm phong trước khi bổ sung thư mục `lab/` và file này).

Mục đích: kiểm tra lại các số liệu dữ liệu mẫu được dùng trong báo cáo (37 tài khoản, 20 sự kiện,
181 đăng ký/vé, 62 check-in, 40 phân công) bằng cách chạy chính `Backend/app/seed.py`.

## Cách chạy

Tại thư mục `Backend`, dùng database SQLite trong bộ nhớ để không chạm database trình diễn:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_seed.py -q
```

Đếm số bản ghi sau khi gọi hàm `_seed` hai lần liên tiếp trên cùng một database rỗng
(script đếm dùng `select(func.count())` trên từng bảng).

## Kết quả

`tests/test_seed.py`: 3 passed.

| Hạng mục | Kết quả | Khớp báo cáo |
| --- | --- | --- |
| Tài khoản | 37 (ATTENDEE 30, STAFF 5, ORGANIZER 2) | Có |
| Sự kiện | 20 (PUBLISHED 10, COMPLETED 5, DRAFT 2, ONGOING 1, STARTED 1, CANCELLED 1) | Có |
| Đăng ký | 181 (REGISTERED 164, CANCELLED 17) | Có |
| Vé | 181 (VALID 102, USED 62, CANCELLED 17) | Có |
| Check-in | 62 (bằng số vé USED) | Có |
| Phân công nhân viên | 40 | Có |
| Chạy seed lần 2 | `{'accounts': 37, 'events_added': 0}`: không thêm sự kiện trùng | Có |

Tài khoản mẫu dùng email dạng `user1@demo.com`, `staff1@demo.com`, `organizer1@demo.com`
(đăng nhập được bằng tên rút gọn `user1`, `staff1`, `organizer1`), mật khẩu chung `123456`.

Môi trường chạy: Windows, Python 3.13.9, SQLite trong bộ nhớ. Số liệu benchmark 100.000 sự kiện
ở Chương 10 của báo cáo là phép đo riêng trên PostgreSQL ngày 20/10/2026, không thuộc file này.
