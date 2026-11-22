# Bản đồ cơ sở xăng dầu Cần Thơ

Website tương tác từ 9 vị trí bến cảng/bến phao liên quan xăng dầu và raster hiện trạng năm 2025 do chủ dự án cung cấp.

Bấm một vị trí để xem vùng đệm 2 km, hiện trạng bên trong, bảng diện tích ha và tỷ lệ từng loại đất. Bảng chỉ hiển thị bảy loại đất được phân loại; tỷ lệ vẫn tính trên toàn vùng đệm. Có thể tải bảng CSV của từng vị trí hoặc cả 9 vị trí.

## Dữ liệu và cách tính

- Raster gốc: Hien_trang_2025_7lop_co_rung.tif, 10 m, EPSG:32648, NoData = 0.
- Gộp các bản ghi trùng tên và tọa độ. Bến phao cùng tên nhưng khác tọa độ được giữ riêng.
- Vùng đệm 2.000 m trong UTM 48N; 1.440 cạnh. Diện tích ô biên tính theo phần giao với vùng đệm.
- Tỷ lệ tính trên toàn vùng đệm, bao gồm phần thiếu dữ liệu.
- Mã 7 là rừng bổ sung theo raster nguồn.
- Các vùng đệm chồng lấn; không cộng trực tiếp để suy ra diện tích duy nhất.
- Các kết quả đã được kiểm tra độc lập bằng cách chuyển raster sang polygon và giao với từng vùng đệm.

## Xuất bản

Tệp index.html nằm ở thư mục gốc. Trong GitHub Settings → Pages, chọn Deploy from a branch, nhánh main, thư mục /(root). Tệp .nojekyll giữ website ở dạng tĩnh.

Website dùng đường dẫn tương đối, phù hợp GitHub Pages dạng tài khoản hoặc dự án. Không cần build, API key hoặc máy chủ xử lý GIS. Khi đổi raster hoặc thêm vị trí, cần tính lại dữ liệu đầu vào.

Leaflet 1.9.4 đi kèm giấy phép trong assets/LEAFLET-LICENSE.txt. Bản đồ nền OpenStreetMap được ghi công trên giao diện.

## Giao diện

Logo Đại học Cần Thơ do chủ dự án cung cấp, giữ nguyên tỷ lệ và màu. Giao diện nền trắng, màu xanh theo logo; font Be Vietnam Pro và Noto Sans hỗ trợ tiếng Việt, lưu cùng website. Không khẳng định đây là trang xuất bản chính thức của trường.
