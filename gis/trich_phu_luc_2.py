"""Trích bảng Phụ lục 2 (danh sách kho xăng dầu có dung tích) từ tệp Word.

    python gis/trich_phu_luc_2.py dau_vao/thongtinbosung.docx gis/kho_phu_luc_2_trich.csv

Chỉ giữ các cột kỹ thuật (không lấy người đại diện, điện thoại). Dung tích ghi
nguyên số trong tài liệu (dấu chấm phân tách hàng nghìn → số nguyên m³).
Tệp này KHÔNG có tọa độ; việc ghép kho với điểm bản đồ nằm ở
gis/kho_phu_luc_2.csv (cột ma_diem, do người dùng xác nhận).
"""
import csv
import sys

import docx

COLS = ["stt", "loai_kho", "ten_kho", "dia_chi", "dia_ban_cu", "dung_tich_m3", "cau_cang_tan", "trong_ngoai_kcn", "don_vi_so_huu", "tinh_trang"]
SRC_IDX = [0, 1, 2, 3, 4, 5, 6, 7, 8, 11]


def to_int(s):
    s = s.strip().replace(".", "").replace(",", "")
    return int(s) if s.isdigit() else ""


def main(src, out):
    d = docx.Document(src)
    body = list(d.element.body.iterchildren())
    title_seen = False
    table = None
    for el in body:
        tag = el.tag.split("}")[1]
        if tag == "p":
            text = "".join(t.text or "" for t in el.iter() if t.tag.endswith("}t")).strip().upper()
            if text.startswith("PHỤ LỤC 2"):
                title_seen = True
        elif tag == "tbl" and title_seen:
            table = docx.table.Table(el, d)
            break
    if table is None:
        sys.exit("Không tìm thấy bảng sau tiêu đề PHỤ LỤC 2")
    rows = []
    for r in table.rows[1:]:
        cells, prev = [], None
        for c in r.cells:
            if c._tc is prev:
                continue
            prev = c._tc
            cells.append(c.text.strip())
        if not cells[0].strip().isdigit():
            continue  # dòng tổng cộng
        rec = dict(zip(COLS, [cells[i] for i in SRC_IDX]))
        rec["stt"] = int(rec["stt"])
        rec["dung_tich_m3"] = to_int(rec["dung_tich_m3"])
        rec["cau_cang_tan"] = to_int(rec["cau_cang_tan"])
        rows.append(rec)
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, COLS)
        w.writeheader()
        w.writerows(rows)
    total = sum(r["dung_tich_m3"] for r in rows if r["dung_tich_m3"] != "")
    print(f"{len(rows)} kho; tổng dung tích {total} m³")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
