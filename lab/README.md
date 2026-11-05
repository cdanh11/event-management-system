# Hands-on lab: FastAPI với API sự kiện

Bộ file đi kèm tài liệu `Hands_on_lab_FastAPI_Nhom15.docx` (bài thực hành 30–45 phút cho nhóm khác).
Lab là một API độc lập, không cần Docker, database hay mã nguồn Evently.

| File | Vai trò |
| --- | --- |
| `requirements.txt` | Các phiên bản cố định dùng trong lab |
| `lab_app.py` | Mã khung, người học hoàn thiện TODO A, B, C |
| `test_lab.py` | Sáu test kiểm chứng (TestClient, `dependency_overrides`) |
| `probe_async.py` | Bài mở rộng: gọi `/health` trong lúc `/wait` đang chờ |
| `solution/lab_app.py` | Đáp án tham khảo (đã gồm endpoint `/wait` của bài mở rộng) |

## Chạy nhanh (Windows PowerShell, tại thư mục `lab`)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn lab_app:app --host 127.0.0.1 --port 8010 --reload
```

Trong terminal thứ hai:

```powershell
.\.venv\Scripts\python.exe -m pytest test_lab.py -vv -ra
```

## Kết quả mong đợi

- Mã khung chưa làm bài: `3 failed, 3 passed` (test phát hiện đúng ba TODO chưa làm).
- Sau khi hoàn thiện TODO A, B, C (hoặc chép `solution/lab_app.py` đè lên `lab_app.py`): `6 passed`.
- Bài mở rộng: chạy server bằng bản đã có `/wait`, rồi chạy `python probe_async.py`;
  kết quả thường là `health: 200`, `wait finished before health: False`, `wait: 200`.

Lần chạy kiểm chứng ngày 05/11/2026 (Windows, Python 3.13.9, các phiên bản trong `requirements.txt`)
cho đúng ba kết quả trên.
