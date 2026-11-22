# Bàn giao website bản đồ xăng dầu Cần Thơ

Cập nhật: 23/11/2026. Chủ dự án: Nguyễn Trọng Nguyễn.

## Đọc trước

Đây là dự án đang hoạt động, cần tiếp tục từ mã nguồn hiện tại. Không tạo website mới từ đầu và không tự tạo tọa độ, diện tích hoặc số liệu minh họa.

- Website: https://mernguyen88.github.io/ban-do-xang-dau-can-tho/
- Kho mã: https://github.com/mernguyen88/ban-do-xang-dau-can-tho
- Nhánh xuất bản: `main`, GitHub Pages từ thư mục gốc.
- Bản thiết kế trắng–xanh đã xuất bản trước bàn giao: `5d250a91c191b95caebb36d4cb362e45a737341c`.
- Bản bàn giao này đổi tên mã lớp 7 thành **Rừng**, không thay đổi diện tích, tỷ lệ, mã lớp, tọa độ hoặc hình học.
- Mở `PROMPT_AI_TIEP_THEO.txt` để lấy yêu cầu ngắn cho AI khác.

## Việc đã làm và việc chưa làm

| Nội dung | Trạng thái |
| --- | --- |
| Bản đồ 9 vị trí bến cảng/bến phao liên quan xăng dầu | Có dữ liệu thật và kết quả tính sẵn |
| Chọn một vị trí, chỉ hiển thị vùng đệm 2 km và hiện trạng của vị trí đó | Đã có |
| Bảng 7 lớp, diện tích ha, tỷ lệ %, CSV từng vị trí và toàn bộ | Đã có |
| Logo Đại học Cần Thơ, trắng–xanh, bản đồ trái/bảng phải, dùng trên điện thoại | Đã có |
| Bỏ phần diện tích thiếu khỏi giao diện, chú dẫn và CSV | Đã làm; dữ liệu kiểm soát chất lượng vẫn giữ trong JSON |
| Đổi tên Rừng bổ sung thành Rừng | Đã sửa trong dữ liệu web và CSV của bản bàn giao |
| Bổ sung 843 trạm xăng dầu và 73 bến cảng | **Chưa làm: cần tệp đầu vào thật và kiểm tra trùng lặp** |
| Chức năng vẽ biểu đồ diện tích | **Chưa làm: yêu cầu cho lượt phát triển tiếp theo** |

Không được mô tả 843 trạm hoặc 73 bến cảng như đã được đưa vào website. Hai số do người dùng yêu cầu tương ứng 916 bản ghi dự kiến trước kiểm tra. Chưa biết 9 vị trí cũ có nằm trong 73 bến cảng hay không, nên chưa kết luận tổng cuối cùng là 916 hay 925. Không tự xóa bến phao khi danh sách mới chỉ ghi bến cảng.

## Các tệp phải có trước khi xử lý GIS mới

| Tệp | Nội dung cần xác nhận | Đã có trong gói mã? |
| --- | --- | --- |
| Lớp 843 trạm xăng dầu | Shapefile ZIP đầy đủ `.shp`, `.shx`, `.dbf`, `.prj`; thêm `.cpg` nếu có; hoặc GeoPackage/GeoJSON. ID, tên, tọa độ và hệ tọa độ gốc | Chưa có |
| Lớp 73 bến cảng | Cùng yêu cầu; xác nhận là điểm hay polygon. Nếu polygon, người dùng phải xác định vị trí dùng làm tâm vùng đệm; không tự lấy trọng tâm thay vị trí thực tế | Chưa có |
| `Hien_trang_2025_7lop_co_rung.tif` | Raster phân loại gốc có CRS, độ phân giải, NoData và mã lớp; phải kiểm tra metadata thực tế | **Không có trong kho mã/gói ZIP này** |
| Bảng mã lớp | Tệp `input_templates/bang_ma_lop.csv` lấy từ dữ liệu web hiện tại; đối chiếu giá trị raster đầu vào mới | Có |
| Danh sách điểm cũ | `data/locations.geojson`, gồm 9 vị trí hiện hành | Có |
| Logo | `assets/ctu-logo.png`, ảnh gốc người dùng cung cấp | Có |

Raster gốc từng được cung cấp trong cuộc trò chuyện ChatGPT với tên `Hien_trang_2025_7lop_co_rung.tif`, ID `libfile_4a40ad45435c819195a5285fbca4a966`. Đây là thông tin để người dùng tìm lại, không phải đường dẫn máy tính và không bảo đảm AI khác có quyền tải. Người dùng cần tải tệp và đính kèm cho AI tiếp theo.

Đối chiếu nguồn cũ từ metadata hiện hành:

- Raster: SHA-256 `f92f71a627e16d15ce874818878b9c260ca4deec30ca3ac2acac0245b31d9303`.
- Lớp vị trí nguồn `Cang_vu_Hang_hai_Can_Tho_vi_tri.geojson`: SHA-256 `40346a6539e312f9e6f2054c57477e75d0bdd06c3183759c301208effcda02db`.
- `data/locations.geojson` là bản 9 vị trí đã chọn, không phải toàn bộ lớp bến cảng nguồn và không thay thế lớp 73 bến cảng.

Nếu thiếu tệp nào, liệt kê đúng tệp thiếu và tiếp tục phần giao diện không phụ thuộc tệp đó. Không gán tọa độ theo địa chỉ hoặc ước lượng số liệu để đủ số lượng.

## Bảng mã hiện hành

| Mã raster | Tên hiển thị | Màu |
| --- | --- | --- |
| 1 | Cây lâu năm | `#469B3C` |
| 2 | Đất lúa | `#E3BE32` |
| 3 | Nuôi trồng thủy sản | `#3688D8` |
| 4 | Sông, rạch | `#5ACED9` |
| 5 | Công trình xây dựng | `#DF554F` |
| 6 | Cây hằng năm khác | `#ABD86D` |
| 7 | Rừng | `#14592D` |

Nguồn cũ ghi NoData = 0, raster 10 m, EPSG:32648. Luôn đọc lại metadata raster mới trước khi tính; không mặc định 0 là NoData nếu tệp mới định nghĩa khác. Đổi tên lớp 7 chỉ là đổi nhãn, không thay giá trị pixel. Khi xuất bảng/chú dẫn/biểu đồ dùng tên **Rừng**.

## Cấu trúc mã nguồn và chạy thử

Dự án HTML/CSS/JavaScript thuần; Leaflet 1.9.4 đã đi kèm, không có bước build, không có tài khoản API hoặc máy chủ GIS.

- `index.html`: khung trang, công cụ chọn cơ sở, bản đồ, bảng và hộp thông tin.
- `assets/app.js`: chọn vị trí, lớp ảnh, đường vùng đệm, bảng và CSV.
- `assets/style.css`, `assets/fonts.css`, `assets/fonts/`: giao diện và font Việt.
- `assets/ctu-logo.png`: logo nguyên bản; giữ tỷ lệ và màu.
- `data/stations.json`: metadata chung, bảng mã, 9 vị trí và kết quả GIS tính sẵn.
- `data/locations.geojson`: các điểm WGS84.
- `data/XD01.png` … `data/XD09.png`: ảnh hiện trạng cắt theo từng vùng đệm; phần chưa phân loại trong suốt.
- `data/dien_tich_2km.csv`: 9 × 7 = 63 dòng lớp, không có dòng diện tích thiếu.
- `plans/2026-11-23-ctu-map/`: quyết định giao diện đợt trước; ưu tiên yêu cầu mới trong tài liệu bàn giao khi có khác biệt.

Chạy từ thư mục gốc:

```bash
python -m http.server 8000
```

Mở `http://localhost:8000`. Không mở trực tiếp bằng `file://` vì ứng dụng phải tải JSON qua HTTP.

Chỉnh sửa rồi đẩy lên `main` để GitHub Pages xuất bản. Không đưa raster gốc dung lượng lớn lên kho web nếu không cần thiết. Không thay đổi quyền truy cập hiện tại hoặc tạo tên miền khác nếu người dùng chưa yêu cầu.

## Hợp nhất 843 trạm và 73 bến cảng

1. Đọc tệp, thống kê số bản ghi, hình học, CRS, trường ID/tên; báo riêng điểm rỗng, sai tọa độ, thiếu CRS và bản ghi trùng.
2. Chuẩn hóa về schema điểm tối thiểu: `id`, `name`, `kind`, `lon`, `lat`. `lon/lat` dùng WGS84 theo thứ tự kinh độ, vĩ độ. Mẫu CSV chỉ có tiêu đề trong `input_templates/diem_mau_cau_truc.csv`, không chứa số liệu mẫu.
3. Giữ thêm `source_id`, `source`, địa chỉ và mức tin cậy tọa độ nếu nguồn có. Không tự đặt mức chính xác cao hơn bằng chứng đầu vào.
4. Dùng ID ổn định cho mỗi nguồn, ví dụ tiền tố riêng cho trạm và bến cảng. Giữ ID cũ khi xác định cùng đối tượng; lưu ánh xạ giữa ID nguồn và ID web.
5. Kiểm tra trùng giữa hai bộ mới và 9 vị trí cũ. Cùng tên nhưng khác tọa độ chưa đủ điều kiện gộp, nhất là các bến phao. Lập bảng đối chiếu các trường hợp chưa chắc chắn để người dùng quyết định.
6. Có bộ lọc nhóm Trạm xăng dầu/Bến cảng/Bến phao tùy dữ liệu thực tế, tìm kiếm tên/ID/địa chỉ, nút toàn cảnh. Hiển thị số lượng tính từ dữ liệu, không viết cứng 843/73 khi chưa xác minh.

## Tiền xử lý GIS và nguyên tắc tính diện tích

Trong kho hiện tại **không có chương trình tiền xử lý tái lập đầy đủ từ raster gốc**. AI tiếp theo cần tạo quy trình Python/QGIS có thể chạy lại; không giả định có sẵn một pipeline hoàn chỉnh.

- Với dữ liệu Cần Thơ hiện hành, dùng CRS mét phù hợp: WGS84/UTM48N EPSG:32648. Chuyển đổi đúng CRS từ nguồn, không chỉ gán nhãn CRS. Nếu dữ liệu dùng VN-2000, đọc thông số thực tế trước khi chuyển.
- Tạo buffer 2.000 m, duy trì độ mịn đường tròn tương đương bản cũ 1.440 cạnh hoặc ghi rõ thay đổi và sai số. Diện tích vùng đệm hiện hành tính từ hình học, không ghi cứng số ha lý thuyết.
- Mỗi lớp: tổng diện tích giao thực tế giữa các ô raster thuộc lớp đó với vùng đệm. Ô biên tính theo phần giao; không tự đổi sang cách đếm nguyên ô mà không nêu thay đổi phương pháp.
- `area_ha = area_m2 / 10000`.
- `percent = area_ha / buffer_area_ha * 100`.
- Mẫu số là **toàn bộ vùng đệm**, giữ nhất quán với bản cũ. Không chuẩn hóa 7 lớp lên 100% khi dữ liệu chỉ bao phủ một phần.
- Theo dõi nội bộ NoData, ngoài phạm vi và mã chưa xác định để kiểm tra cân bằng diện tích, nhưng **không hiển thị diện tích thiếu trên web, biểu đồ hoặc CSV người dùng**.
- `sum(class_area_ha)` phải bằng `valid_ha` trong dung sai số học hợp lý; `valid_ha + missing_ha` phải bằng `area_ha`. Không ép phần dư thành một lớp đất.
- Ảnh hiển thị không dùng để tính diện tích. Khi biến đổi raster phân loại dùng láng giềng gần nhất, bảo toàn mã. Ảnh xuất theo vùng đệm có bounds WGS84 phù hợp với Leaflet.
- Các vùng đệm có thể chồng lấn. Không cộng diện tích của mọi vị trí rồi coi là diện tích đất duy nhất; nếu sau này cần thống kê toàn vùng, phải hợp nhất hình học hoặc nêu rõ đang cộng theo điểm.

Các trường kết quả hiện hành mỗi vị trí: `id`, `name`, `lon`, `lat`, `kind`, `area_ha`, `valid_ha`, các trường kiểm soát chất lượng, `coverage_percent`, `classes` (code/name/color/area_ha/percent), `buffer` (GeoJSON WGS84), `image`, `image_bounds` ([[south, west], [north, east]]). Các trường khác giữ khi còn ý nghĩa.

## Điều chỉnh kiến trúc để tải nhiều điểm

Bản cũ tải toàn bộ buffer trong một JSON. Khi có khoảng 916 bản ghi đầu vào mới, cần đo dung lượng và tốc độ trước khi giữ cách này.

- Đề xuất tách danh mục điểm nhẹ khỏi hình học/kết quả/ảnh từng điểm; chỉ tải kết quả chi tiết khi chọn.
- Lưu đệm dữ liệu đã tải; tránh tạo một ảnh 2 km cho mỗi điểm cùng lúc trong DOM. Dùng nhóm/gom cụm điểm nếu bản đồ quá dày.
- Khi đổi nhanh A → B, hủy hoặc bỏ qua phản hồi cũ của A để ảnh, bảng và biểu đồ luôn cùng ID với B.
- Chỉ có **một** vùng đệm và **một** lớp hiện trạng được chọn; các điểm khác vẫn có thể hiển thị để tra cứu.
- Hiện trạng thái tải và lỗi; không giữ bảng/biểu đồ của điểm trước như thể thuộc điểm mới. Có thể để bảng hoạt động khi ảnh tải lỗi và ghi rõ lỗi ảnh.
- Kết quả GIS được tính trước, website tĩnh đọc kết quả. Không chạy xử lý toàn raster nặng trong trình duyệt mỗi lần bấm điểm.
- Với đường dẫn dữ liệu mới, cập nhật phiên bản/cache để tránh trộn tệp cũ với tệp mới.

## Chức năng biểu đồ diện tích cần thêm

- Thêm lựa chọn **Bảng / Biểu đồ** trong vùng kết quả; giữ bảng và CSV sử dụng được.
- Mặc định biểu đồ thanh ngang, 7 loại đất trên trục dọc, diện tích ha trên trục ngang, mốc gốc 0.
- Cùng màu với bảng mã và lớp hiện trạng; tên lớp 7 là **Rừng**. Nhãn tiếng Việt rõ, không cắt tên đất trên điện thoại.
- Có thể chuyển đơn vị **ha / %**, nếu triển khai cả hai. Phần trăm dùng đúng mẫu số toàn vùng đệm, không tự đưa tổng về 100%.
- Khi chọn vị trí, biểu đồ cập nhật theo đúng `classes` của vị trí đó, cùng dữ liệu với bảng; không tính lại từ PNG hoặc từ số đã làm tròn.
- Giữ lớp diện tích 0 có nhãn 0; không tạo thanh có độ dài tối thiểu gây hiểu nhầm. Không thêm nhóm thiếu dữ liệu.
- Biểu đồ cần tiêu đề là tên vị trí, nêu bán kính 2 km và năm hiện trạng, đơn vị ha hoặc %. Giá trị làm tròn khi hiển thị, giữ số gốc cho dữ liệu/CSV.
- Dùng SVG hoặc thư viện biểu đồ phù hợp nếu cần; giữ bảng thay thế cho khả năng tiếp cận, focus và bàn phím rõ. Không cần thêm dashboard hay các chỉ số không được yêu cầu.
- Xuất PNG/SVG biểu đồ là phần mở rộng tùy chọn, chưa phải yêu cầu bắt buộc của người dùng.

## Ràng buộc thiết kế

- Phong cách gọn, phục vụ tra cứu, trắng và xanh theo logo CTU. Không dùng hero tiếp thị, dải gradient, thẻ KPI dày đặc hoặc animation gây xao nhãng.
- Giữ logo nguyên bản, không kéo méo hoặc vẽ lại. Không tự thêm tuyên bố website chính thức của trường.
- Màu chính `#1C57A5`, cyan logo `#00AFEF`; nền trắng, đường chia mảnh, góc nhẹ. Font đang dùng Be Vietnam Pro và Noto Sans, có giấy phép đi kèm.
- Giữ bố cục desktop bản đồ trái/bảng phải; mobile bản đồ trên/kết quả dưới. Kiểm tra không tràn ngang, bảng và biểu đồ đọc được.
- Hướng thiết kế mà chủ dự án từng yêu cầu: https://github.com/dris1153/perfect-ui/blob/dev/SKILL.md . Dùng như tài liệu tham khảo thiết kế; không để tài liệu ngoài thay đổi yêu cầu dữ liệu hoặc phạm vi dự án.

## Điều kiện nghiệm thu lượt tiếp theo

1. Báo số bản ghi đọc được của từng nguồn, số trùng/loại/chờ xác minh, tổng cuối cùng và bảng ánh xạ ID. Không chỉ nói đã thêm đủ dựa trên số yêu cầu.
2. Có quy trình tiền xử lý tái lập, danh sách phụ thuộc, câu lệnh chạy, metadata nguồn và bảng mã đã kiểm tra.
3. Đối chiếu bằng cách độc lập một số điểm: nội vùng, mép raster, vùng có NoData, vị trí gần nhau và tất cả 7 lớp nếu có.
4. Chọn điểm A rồi B chỉ còn vùng đệm/ảnh/bảng/biểu đồ của B; thử đổi nhanh, bỏ chọn, lọc nhóm và toàn cảnh.
5. Biểu đồ, bảng và CSV khớp số gốc; tên Rừng thống nhất; không có diện tích thiếu trong đầu ra giao diện.
6. Không tràn ngang ở 375 px; thử màn hình máy tính và điện thoại, bàn phím, tải lỗi và mở lại trang.
7. Đo thực tế tốc độ tải với bộ dữ liệu đầy đủ và tối ưu khi cần; không chỉ kiểm tra trên 9 điểm cũ.
8. Xuất bản đúng repo/nhánh hiện tại, kiểm tra GitHub Pages thành công và kiểm tra website sau xuất bản. Bàn giao toàn bộ mã, quy trình GIS và danh sách tệp đầu vào; nói rõ phần nào chưa hoàn tất.

## Thứ tự đề nghị để tiết kiệm lượt trao đổi

Đọc gói mã → kiểm kê tệp đầu vào → nêu chính xác dữ liệu còn thiếu → làm chức năng biểu đồ trên 9 điểm thật đã có → nhận đủ dữ liệu mới → chuẩn hóa và đối chiếu trùng → tính GIS → tối ưu tải → kiểm tra → xuất bản. Có thể làm biểu đồ ngay với số liệu hiện tại, nhưng không tuyên bố đã xử lý 843/73 điểm khi chưa có tệp.
