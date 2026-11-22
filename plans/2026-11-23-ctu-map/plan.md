# Kế hoạch triển khai

1. Khôi phục bản hiện hành từ GitHub và đọc giao diện, dữ liệu, hướng Perfect UI và hướng logo CTU.
2. Header logo đầy đủ; thanh công cụ gồm chọn cơ sở, bán kính, bật lớp hiện trạng, độ trong suốt và toàn cảnh.
3. Bản đồ lớn bên trái, bảng tra cứu ở bên phải; trạng thái mặc định là danh sách 9 vị trí. Khi chọn chỉ hiện một vùng đệm và một ảnh hiện trạng.
4. Bảng có bảy loại đất, ha và %. Bỏ thẻ KPI, thanh tỷ lệ màu, toàn bộ dòng diện tích thiếu. CSV chỉ có các lớp phân loại. Tỷ lệ giữ mẫu số toàn vùng đệm.
5. Copy logo đúng byte và font có tiếng Việt; làm pixel NoData trong ảnh phân loại trong suốt, giữ nguyên tất cả pixel của lớp hợp lệ.
6. Giữ trạng thái tải, lỗi, bỏ chọn, bàn phím, focus, độ hiển thị, xuất CSV và màn hình nhỏ.
7. Kiểm tra giao diện desktop/mobile, đổi điểm, chỉ một lớp hiện, số liệu nguồn không đổi, logo nguyên bản, CSV 7 dòng mỗi vị trí, không có nhãn diện tích thiếu. Sau đó cập nhật kho và chờ GitHub Pages thành công.

<design_plan>
macrostructure_diversification: PASS — Workbench phù hợp bản đồ; không có log cũ; đổi bản đồ trái / bảng phải theo yêu cầu thiết kế lại.
vibe_validity: PASS — minimal academic, trắng/xanh CTU, logo nguyên bản, SVG đồng nhất.
dial_alignment: PASS — ưu tiên bản đồ và bảng, khoảng cách rõ, góc 2–4 px, không KPI cards hay trang trí tiếp thị.
motion_personality: PASS — CSS hover/focus 120–180 ms, easing (.2,.8,.2,1), native scrolling và reduced-motion.
hero_math: N/A — ứng dụng bản đồ không có hero; header logo giữ đúng tỷ lệ trên desktop và điện thoại.
bento_density: N/A — không dùng bento.
label_sweep: PASS — nhãn mục đích thực tế, năm/ha/%/bán kính rõ; không meta-label hay dòng diện tích thiếu.
button_contrast: PASS — chữ trắng trên #1C57A5, focus rõ; nút phụ chữ xanh trên trắng.
honest_copy: PASS — 9 vị trí và 7 lớp từ dữ liệu nguồn; diện tích/tỷ lệ không thay; không thêm chứng nhận hoặc quan hệ chính thức.
gsap_decision: PASS — không cần GSAP/WebGL/thư viện animation cho bản đồ tra cứu.
</design_plan>

## Kiểm tra trước triển khai

- JavaScript syntax và git diff --check đạt.
- Đã chọn lần lượt 9 vị trí trong trình duyệt: mỗi vị trí có 7 dòng lớp, 1 ảnh và 1 vùng đệm. Bật/tắt hiện trạng hoạt động.
- Kiểm tra chiều rộng 375, 768, 1024 và màn hình desktop; không tràn ngang. Nút xem bảng trên điện thoại cuộn tới đúng bảng.
- Logo giữ nguyên byte; stations.json giữ nguyên byte so với bản hiện hành. CSV có 63 dòng lớp cho 9 vị trí; không có dòng thiếu dữ liệu.
- Pixel phân loại hợp lệ giữ nguyên; chỉ pixel NoData được chuyển sang trong suốt.
- Hộp thông tin, bảng và chú dẫn không có nhãn diện tích thiếu. Phần trăm giữ mẫu số toàn vùng đệm.
