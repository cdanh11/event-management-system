# Realtime trong web MVP

Dashboard hiển thị Registered, Left, Fill và Last changes trong phiên. Registered là registered_count từ backend, không phải check-in count.

1. SocketManager lấy ticket qua POST /ws/ticket bằng Bearer rồi mở WS /ws/events/{id}?ticket=.... Mỗi reconnect lấy ticket mới.
2. Snapshot đầu thiết lập số; occupancy sau cập nhật đăng ký/hủy và trạng thái. Không tạo delta giả từ snapshot đầu.
3. Mất kết nối: backoff 1/2/4/8 giây rồi tối đa 15 giây, có jitter. Hết retry hiện Paused và Try again. REST dự phòng 5 giây khi tab đang hiện; response cũ không ghi đè WS mới.
4. Room dùng chung, đóng khi subscriber cuối rời đi. Backend nhận heartbeat nhưng không trả pong; phòng yên lặng không tự bị coi là mất kết nối.
5. Event terminal đóng WS. Updated dùng clock chung; Last changes chỉ giữ tối đa 20 thay đổi trong phiên, không phải lịch sử audit.

Overview, danh sách event và lịch sử Check-in dùng polling; lịch sử check-in 5 giây. Event detail nhận WS/trạng thái và làm mới REST. Không có notification push hoặc biểu đồ trong MVP.

Demo: organizer chọn event Published trên Dashboard, attendee ở profile khác Register rồi Cancel registration; kiểm tra +1/-1 không reload. Mỗi attendee chỉ được đăng ký một lần trên một event, kể cả sau hủy.
