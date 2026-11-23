# Bản đồ rủi ro tràn dầu trên địa bàn Thành phố Cần Thơ

Website tra cứu hiện trạng sử dụng đất năm 2025 quanh **871 vị trí**: 843 cơ sở xăng dầu và 28 bến cảng, tính từ raster hiện trạng gốc 10 m. 9 vị trí cũ đã được bỏ theo yêu cầu (lượt 23/11/2026).

- Bấm một điểm: chỉ hiện **một** vùng đệm, ảnh hiện trạng trong vùng đệm và bảng/biểu đồ diện tích (ha, %) của điểm đó.
- Mọi điểm có vùng đệm **2 km**. 7 điểm được ghép với kho có dung tích trong **Phụ lục 2** có thêm **3, 5, 10 km**.
- Chế độ **Bảng / Biểu đồ** (thanh ngang, đơn vị ha hoặc %), cùng màu và cùng số liệu gốc; CSV từng điểm và toàn bộ (`data/dien_tich.csv`).
- Tìm theo tên/mã/địa chỉ (gõ không dấu được), lọc loại cơ sở, kho có dung tích, vị trí ước lượng. Liên kết trực tiếp: `#BC21`, `#BC21/10000`.

## Dữ liệu

| Nguồn | Bản ghi | Dùng |
| --- | --- | --- |
| `dau_vao/Co_so_xang_dau_Can_Tho.shp` (WGS84) | 843 | 843 (3 bản ghi trùng hoàn toàn được giữ, bản sau dịch 10 m về phía đông theo yêu cầu) |
| `dau_vao/bencang.shp` (WGS84) | 73 | 28 bến cảng (bỏ 45 bến phao/phao/rùa neo theo yêu cầu) |
| `Hien_trang_2025_7lop_co_rung.tif` | EPSG:32648, 10 m, NoData 0 | SHA-256 `f92f71a6…9303`; **không đưa lên kho** — đặt vào `dau_vao/` khi chạy lại |
| Phụ lục 2 (`thongtinbosung.docx`) | 18 kho | 7 kho ghép được với điểm bản đồ (`gis/kho_phu_luc_2.csv`); 11 kho không có vị trí |

Lưu ý: 354 điểm ghi "Vị trí ước lượng" trong nguồn, nhiều điểm dùng chung tâm phường/xã; 3 bến cảng Duyên Hải nằm ngoài phạm vi raster (không tính diện tích). Giao diện ghi rõ các trường hợp này.

## Phương pháp

Vùng đệm tròn trong UTM 48N (1.440 cạnh). Diện tích mỗi lớp = tổng diện tích **giao thực tế** giữa ô 10 m và vùng đệm (ô biên tính theo phần giao). Tỷ lệ = diện tích lớp / diện tích toàn vùng đệm × 100, không chuẩn hóa tổng về 100 %. NoData/ngoài phạm vi chỉ theo dõi nội bộ (`qc` trong JSON), không hiển thị. Ảnh PNG chỉ để xem.

## Chạy lại quy trình GIS

```bash
pip install -r gis/requirements.txt
# đặt Hien_trang_2025_7lop_co_rung.tif (và thongtinbosung.docx nếu trích lại Phụ lục 2) vào dau_vao/
python gis/kiem_ke.py                 # 1. kiểm kê CRS, số bản ghi, trùng tọa độ, giá trị raster
python gis/hop_nhat_diem.py           # 2. ID ổn định, đối chiếu trùng, hợp nhất → gis/ket_qua/
python gis/tinh_dien_tich.py          # 3. tính diện tích + ảnh → data/ (có bộ đệm, chạy lại nhanh)
python gis/kiem_tra_nhat_quan.py      # 4. kiểm tra tổng lớp, %, hình học, CSV
python gis/doi_chieu_doc_lap.py       # 5. đối chiếu độc lập bằng polygon hóa raster
python gis/tests/test_dien_tich.py    # kiểm thử thuật toán (raster tổng hợp)
```

Cấu hình: `gis/cau_hinh.toml`. Sửa ghép kho trong `gis/kho_phu_luc_2.csv` (cột `ma_diem`); quyết định gộp/tách cặp nghi trùng trong `gis/quyet_dinh_trung.csv` (`gop` | `rieng`), rồi chạy lại bước 2–5.

## Xem thử và xuất bản

```bash
python -m http.server 8000     # mở http://localhost:8000 (không mở bằng file://)
```

GitHub Pages xuất bản từ nhánh `main`, thư mục gốc. Kiểm thử giao diện: `python kiem_thu/tuong_tac.py`, đo tốc độ: `python kiem_thu/do_toc_do.py`.

Logo Đại học Cần Thơ giữ nguyên bản; không khẳng định đây là trang chính thức của trường. Leaflet 1.9.4 (giấy phép trong `assets/`), nền OpenStreetMap. Tài liệu bàn giao chi tiết: [BAN_GIAO_AI.md](BAN_GIAO_AI.md).
