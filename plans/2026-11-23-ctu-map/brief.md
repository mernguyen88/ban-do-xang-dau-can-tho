# Thiết kế lại bản đồ cơ sở xăng dầu Cần Thơ

- Người dùng yêu cầu giao diện bớt cảm giác do AI tạo, tham chiếu Perfect UI, logo CTU đã cung cấp, nền trắng và xanh.
- Mục đích: chọn một trong 9 vị trí, xem vùng đệm 2 km và diện tích hiện trạng sử dụng đất năm 2025.
- Loại trang: GIS dashboard, generic tier, không có nội dung tiếp thị. Áp dụng nguyên tắc giao diện dữ liệu, không mô phỏng landing page.
- Giữ HTML/CSS/JavaScript, Leaflet, GitHub Pages, dữ liệu và phép tính đã kiểm tra.
- Loại bỏ toàn bộ số liệu, hàng bảng, chú dẫn và ô thống kê diện tích thiếu khỏi giao diện và CSV. Không gán chúng thành một loại đất.
- Giữ nguyên diện tích từng lớp và tỷ lệ trên toàn vùng đệm; ghi rõ mẫu số trong chú thích bảng.
- Logo PNG RGBA 1816 × 482 được sao chép nguyên byte, không cắt, đổi màu hoặc vẽ lại.
- Không thêm nội dung chứng nhận, tên đơn vị phụ trách hoặc tuyên bố chính thức chưa được cung cấp.

## Bố cục

Header trắng: logo nguyên bản, tiêu đề dự án, nút dữ liệu. Thanh công cụ đơn giản. Bản đồ bên trái, danh sách/kết quả bên phải. Trên điện thoại, bản đồ nằm trên bảng kết quả. Chú dẫn chỉ gồm 7 lớp hiện trạng.
