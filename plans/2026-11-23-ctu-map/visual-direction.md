# Hướng giao diện

- Vibe: minimal + academic cartography.
- Macrostructure: Workbench. Không có lịch sử Perfect UI trong kho; giữ chức năng bản đồ và đổi vị trí bảng kết quả.
- Màu: trắng #FFFFFF; primary #1C57A5; cyan #00AFEF làm chi tiết nhỏ; chữ #172D49; đường viền #D7E2EF.
- Font: Be Vietnam Pro cho tiêu đề, Noto Sans cho nội dung và bảng, có bộ ký tự tiếng Việt; tự lưu font để không phụ thuộc tải CDN khi xem.
- Không dùng gradient, thẻ KPI lặp lại, huy hiệu trang trí hay lời giới thiệu tiếp thị.
- Biểu tượng SVG tự vẽ, nét 1.6–1.8, dùng currentColor. Logo CTU giữ nguyên.
- Motion 1/3: hover/focus 120–180 ms, cubic-bezier(.2,.8,.2,1). Không animation xuất hiện đoạn văn; native scroll; reduced-motion tắt transition.
- Hiệu ứng nền được coi là tùy chọn, không áp dụng vào bản đồ tra cứu này. Người dùng đã được thông báo có thể bổ sung sau.
- Màu bản đồ phân loại giữ độc lập với màu giao diện. Pixel chưa phân loại chỉ đổi độ trong suốt khi hiển thị; số liệu nguồn giữ nguyên.
