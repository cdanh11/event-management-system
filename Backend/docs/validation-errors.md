# Validation & mã lỗi

## Nguyên tắc phân biệt 400 / 422

| Mã | Ý nghĩa | Ví dụ |
| --- | --- | --- |
| `422 VALIDATION_ERROR` | Payload **sai hình dạng/kiểu hoặc quan hệ ngay trong payload** — Pydantic chặn ở tầng bind body, endpoint chưa chạy | Email sai, `capacity` âm, `end_time <= start_time` trong cùng payload |
| `400` | Quy tắc **nghiệp vụ cần trạng thái hiện tại/DB** — endpoint kiểm tra sau khi bind | `INVALID_EVENT_TIME` (start trong quá khứ), `REGISTRATION_CLOSED`, `EVENT_STARTED`, `INVALID_TRANSITION`, `EVENT_NOT_DELETABLE`, `CURSOR_OFFSET_CONFLICT` |

Body lỗi thống nhất do exception handler tập trung trong `app/main.py`:

```json
{ "status": 422, "code": "VALIDATION_ERROR", "message": "Request payload is invalid", "details": [...] }
```

## Pydantic trong `app/schemas.py`

- `Field(min_length=…)`, `Field(gt=0)`, `EmailStr` cho ràng buộc từng field.
- `model_validator(mode="after")` cho quan hệ giữa các field (`EventIn`,
  `EventUpdateIn` kiểm tra `end_time > start_time` khi cả hai mốc đều có trong payload).
- `EventStatus`, `NotifyMode` là `str, Enum` nên Swagger hiển thị đúng giá trị hợp lệ.
- `ValidationErrorOut` được gắn ở mức router cho response 422, khớp body lỗi custom.

## Trường hợp PATCH gửi 1 mốc thời gian

Pydantic không nhìn thấy DB nên validator chỉ chạy khi cả hai mốc cùng có trong payload.
Khi client gửi lẻ một mốc, endpoint merge với giá trị DB rồi kiểm tra qua
`_validate_event_time()` và trả `400`. Đây là thiết kế có chủ đích (422 = lỗi shape,
400 = lỗi nghiệp vụ), không phải lọt lưới.

## Lưu ý kỹ thuật: sanitize `ctx.error`

`model_validator` đưa `ValueError` vào `ctx.error` của `exc.errors()`, mà `json.dumps`
không serialize được exception object (từng làm handler 422 crash thành 500).
Handler hiện tại sanitize bằng `jsonable_encoder(..., custom_encoder={ValueError: str})`.

## Thử nhanh trên Swagger (`/docs`)

1. `POST /events` với `end_time` trước `start_time` → `422`.
2. `POST /events` với `start_time` trong quá khứ → `400 INVALID_EVENT_TIME`.
3. Gọi endpoint cần auth không kèm token → `401`; sai role → `403`.
4. Đăng ký trùng → `409 ALREADY_REGISTERED`; event đầy → `409 EVENT_FULL`.
