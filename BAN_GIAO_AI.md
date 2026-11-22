# Bàn giao website bản đồ xăng dầu Cần Thơ

Cập nhật: 23/11/2026 (lượt 2). Chủ dự án: Nguyễn Trọng Nguyễn.

- Website: https://mernguyen88.github.io/ban-do-xang-dau-can-tho/ — Kho mã: https://github.com/mernguyen88/ban-do-xang-dau-can-tho — xuất bản `main` /(root).
- HTML/CSS/JS thuần + Leaflet 1.9.4; không build, không máy chủ GIS. Kết quả GIS tính trước bằng Python, web chỉ đọc.
- Không tạo website mới, không tự tạo tọa độ/diện tích/số liệu minh họa.

## Trạng thái

| Nội dung | Trạng thái |
| --- | --- |
| 9 vị trí cũ (XD01–XD09) | **Đã xóa** theo yêu cầu; còn trong lịch sử git (commit `706cf05`) |
| 843 cơ sở xăng dầu | Đã đưa vào: 840 điểm (gộp 3 bản ghi trùng hoàn toàn) |
| 73 bản ghi `bencang` | Chỉ lấy **28 bến cảng** theo yêu cầu; 45 bến phao/phao/rùa neo ghi "loai" trong `gis/ket_qua/anh_xa_id.csv` |
| Vùng đệm 2 km, bảng ha/%, CSV | Đã có cho 868 điểm, tính từ raster gốc |
| Bảng / Biểu đồ (thanh ngang, ha / %) | Đã có |
| 3, 5, 10 km cho kho có dung tích (Phụ lục 2) | Đã có cho 7 điểm ghép được; **11 kho chưa có vị trí** (không tự gán) |
| Tìm kiếm, lọc, tải chi tiết theo điểm, chống phản hồi cũ | Đã có |
| Quy trình GIS tái lập + kiểm tra | `gis/` (xem README) |

## Tệp đầu vào

| Tệp | Ghi chú |
| --- | --- |
| `dau_vao/Co_so_xang_dau_Can_Tho.*` | 843 điểm, EPSG:4326, trường TEN_DIEM, VI_TRI, TOA_DO, GHI_CHU. Không có trường ID → ID = `TXD` + thứ tự bản ghi (0001–0843). TOA_DO khớp hình học cả 843 bản ghi. 354 bản ghi "Vị trí ước lượng" (353 sau gộp). |
| `dau_vao/bencang.*` | 73 điểm, EPSG:4326. ID = `BC` + thứ tự (01–73). Bến cảng = tên bắt đầu "Bến cảng". |
| `dau_vao/Hien_trang_2025_7lop_co_rung.tif` | **Không commit** (.gitignore). EPSG:32648, 10 m, uint8, NoData 0, 11723×11953; SHA-256 `f92f71a627e16d15ce874818878b9c260ca4deec30ca3ac2acac0245b31d9303`. Mã 1–7 đều có, không có mã lạ. |
| `dau_vao/thongtinbosung.docx` | **Không commit** (có tên, điện thoại người đại diện). Bảng Phụ lục 2 đã trích (bỏ cột liên hệ) vào `gis/kho_phu_luc_2_trich.csv`; tổng 449.814 m³ khớp dòng tổng cộng. |

Thứ tự bản ghi là cơ sở của ID: nếu chủ dự án gửi shapefile mới có thứ tự khác, ID sẽ đổi — đối chiếu bằng SHA-256 nguồn trong `gis/ket_qua/bao_cao_hop_nhat.md`.

## Đối chiếu trùng

- Gộp tự động chỉ khi cùng tên + cùng địa chỉ (chuẩn hóa) + cách ≤ 1 m: TXD0055←0056, TXD0195←0196, TXD0413←0414.
- 59 nhóm (182 điểm) dùng chung một tọa độ (thường là tâm phường/xã của vị trí ước lượng) nhưng khác tên → **giữ riêng**; vùng đệm và kết quả trùng nhau, giao diện ghi chú "vị trí ước lượng".
- Danh sách cặp gần nhau/cùng tên: `gis/ket_qua/doi_chieu_trung.csv`. Muốn gộp/tách: ghi `gop`/`rieng` vào `gis/quyet_dinh_trung.csv`, chạy lại.

## Ghép kho Phụ lục 2 (`gis/kho_phu_luc_2.csv`) — cần chủ dự án xác nhận

| STT | Kho | Dung tích m³ | Điểm | Mức ghép |
| --- | --- | --- | --- | --- |
| 1 | Tổng kho xăng dầu Miền Tây | 103.500 | BC21 | chắc chắn (tên bến cảng) |
| 2 | Tổng kho xăng dầu Cần Thơ (Petro Mekong) | 72.200 | BC11 | khá chắc (đơn vị sở hữu) |
| 3 | Tổng kho xăng dầu, khí đốt (LPG) Cần Thơ | 32.920 | BC24 | khá chắc (Saigon Petro) |
| 4 | Tổng kho xăng dầu Trà Nóc (Nam Sông Hậu) | 50.520 | BC20 | **cần xác nhận** (ứng viên khác BC23) |
| 7 | Kho Phúc Thành | 18.900 | BC25 | chắc chắn |
| 13 | Kho xăng dầu K34 – CTCP An Hiền | 4.800 | BC18 | khá chắc |
| 16 | Kho XD Tân Thạnh | 580 | TXD0236 | chắc chắn (cùng địa chỉ) |

Điểm của các kho 1–4, 7, 13 là **bến cảng của kho**, không phải tâm khu bồn chứa. 11 kho còn lại (STT 5, 6, 8–12, 14, 15, 17, 18) không có điểm tương ứng; cần tọa độ từ chủ dự án.

## Phương pháp & kiểm tra (đã chạy 23/11/2026)

- Vùng đệm tròn 1.440 cạnh trong EPSG:32648; diện tích lớp = giao thực tế ô–vùng đệm; % trên toàn vùng đệm. `qc` (nodata/outside/unknown/missing) chỉ trong JSON.
- Tái lập 5 bến cảng trùng tọa độ với XD01–XD05 cũ: khác biệt ≤ 6·10⁻¹³ ha mọi lớp.
- `kiem_tra_nhat_quan.py`: 868 điểm, 889 vùng đệm (868×2 km + 7×3/5/10 km), 0 lỗi.
- `doi_chieu_doc_lap.py` (polygon hóa raster): nội vùng, mép raster, nhiều NoData, cặp gần nhau 7,8 m, đủ 7 lớp, kho 2–10 km — lệch tối đa 4,5·10⁻⁸ m².
- `kiem_thu/tuong_tac.py` (Chrome headless): 30/30 đạt — đổi nhanh A→B, đổi bán kính, lỗi tải/ảnh, bỏ chọn, lọc, tìm không dấu, bàn phím, mở lại theo liên kết, điểm ngoài raster, 375 px không tràn ngang.
- `kiem_thu/do_toc_do.py` (máy chủ cục bộ, không nén): sẵn sàng 0,38 s; 4G chậm mô phỏng 1,16 s; chọn điểm 0,1–0,8 s. Danh mục 148 KB (≈28 KB gzip); chi tiết 1 điểm 12–47 KB gzip; tổng dữ liệu tĩnh ≈ 72 MB (33 MB JSON + 39 MB PNG) nhưng chỉ tải theo điểm được chọn.

## Kiến trúc web

- `data/catalog.json`: danh mục nhẹ (mảng điểm `id,name,kind,lon,lat,address,estimated,depot,status`) + metadata.
- `data/details/<id>.json`: `results` theo bán kính (`classes`, `buffer`, `image`, `image_bounds`, `qc`), `depot`, `position_quality`.
- `data/anh/<khóa>.png`: ảnh theo vùng đệm, điểm cùng tọa độ dùng chung ảnh.
- `assets/app.js`: >60 điểm vẽ bằng canvas; tải chi tiết khi chọn (AbortController + mã lượt, lưu đệm); chỉ một vùng đệm/ảnh; danh sách hiển thị 200 dòng/lần.

## Ràng buộc thiết kế (giữ nguyên)

Logo CTU nguyên bản; trắng–xanh `#1C57A5`/`#00AFEF`; bản đồ trái/kết quả phải (điện thoại: trên/dưới); không hero, gradient, thẻ KPI. Tên lớp 7 là **Rừng**. Không hiển thị diện tích thiếu.

## Việc còn mở

1. Chủ dự án xác nhận bảng ghép kho (đặc biệt STT 4) và cung cấp tọa độ 11 kho chưa ghép.
2. 353 vị trí ước lượng: nếu có tọa độ chính xác hơn, thay trong shapefile và chạy lại.
3. Nếu dung lượng repo trở thành vấn đề, có thể giảm PNG (ví dụ `max_png_px`) hoặc lưu vùng đệm dạng tham số.
