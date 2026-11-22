"""Kiểm tra nhất quán dữ liệu web đã xuất (không cần raster gốc).

Kiểm tra cho từng điểm, từng bán kính trong data/catalog.json:
  - tệp chi tiết tồn tại, ID/tên/tọa độ khớp danh mục;
  - đủ 7 lớp đúng mã, tên, màu theo bảng mã; không còn tên "Rừng bổ sung";
  - sum(class_area_ha) == valid_ha; valid_ha + missing_ha == area_ha;
  - percent == area_ha / buffer_area_ha * 100 (mẫu số toàn vùng đệm);
  - diện tích hình học vùng đệm (chiếu về CRS tính toán) khớp area_ha;
  - tâm vùng đệm cách điểm < 1 m; bán kính đúng radius_m;
  - ảnh tồn tại, image_bounds hợp lệ;
  - CSV người dùng: đúng số dòng, khớp số gốc, không có dòng diện tích thiếu.

    python gis/kiem_tra_nhat_quan.py [--data data] [--json bao_cao.json]
Thoát mã 1 nếu có lỗi.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from pyproj import Transformer
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ["rừng bổ sung", "thiếu dữ liệu", "diện tích thiếu", "missing"]
TOL_HA = 1e-6        # dung sai cộng dồn số thực
TOL_PCT = 1e-6
TOL_GEOM_HA = 0.01   # sai khác do làm tròn tọa độ GeoJSON WGS84


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--json", help="ghi báo cáo JSON")
    a = ap.parse_args(argv)
    data = Path(a.data)
    cat = json.loads((data / "catalog.json").read_text(encoding="utf-8"))
    code_table = {c["code"]: c for c in cat["classes"]}
    to_m = Transformer.from_crs("EPSG:4326", cat["crs"], always_xy=True).transform
    errors, rows = [], []
    fields = cat["fields"]
    for p in cat["points"]:
        pt = dict(zip(fields, p))
        pid = pt["id"]
        def err(msg, pid=pid):
            errors.append(f"{pid}: {msg}")
        f = data / "details" / f"{pid}.json"
        if not f.exists():
            err("thiếu tệp chi tiết"); continue
        d = json.loads(f.read_text(encoding="utf-8"))
        for k in ("id", "name", "kind", "lon", "lat"):
            if d[k] != pt[k]:
                err(f"{k} chi tiết {d[k]!r} khác danh mục {pt[k]!r}")
        want = cat["radii_depot"] if d.get("depot") else cat["radii_default"]
        if sorted(map(int, d["results"])) != sorted(want):
            err(f"bán kính {list(d['results'])} ≠ {want}")
        if bool(d.get("depot")) != bool(pt["depot"]):
            err("cờ kho không khớp danh mục")
        c = None
        for rad, r in d["results"].items():
            rad = int(rad)
            if [c["code"] for c in r["classes"]] != list(code_table):
                err(f"{rad}: mã lớp không đúng bảng mã")
            for c in r["classes"]:
                ref = code_table[c["code"]]
                if c["name"] != ref["name"] or c["color"].lower() != ref["color"].lower():
                    err(f"{rad}: lớp {c['code']} tên/màu khác bảng mã")
                if c["area_ha"] < 0:
                    err(f"{rad}: lớp {c['code']} âm")
                if abs(c["area_ha"] / r["area_ha"] * 100 - c["percent"]) > TOL_PCT:
                    err(f"{rad}: percent lớp {c['code']} sai")
            s_ = sum(c["area_ha"] for c in r["classes"])
            if abs(s_ - r["valid_ha"]) > TOL_HA:
                err(f"{rad}: tổng lớp {s_} ≠ valid_ha {r['valid_ha']}")
            if abs(r["valid_ha"] + r["qc"]["missing_ha"] - r["area_ha"]) > TOL_HA * 10:
                err(f"{rad}: valid + missing ≠ area")
            if abs(r["qc"]["nodata_ha"] + r["qc"]["outside_ha"] + r["qc"]["unknown_ha"] - r["qc"]["missing_ha"]) > TOL_HA:
                err(f"{rad}: missing ≠ nodata + outside + unknown")
            g = shapely.transform(shape(r["buffer"]), lambda xy: np.column_stack(to_m(xy[:, 0], xy[:, 1])))
            geom_ha = g.area / 1e4
            if abs(geom_ha - r["area_ha"]) > TOL_GEOM_HA * rad / 2000:
                err(f"{rad}: diện tích hình học {geom_ha:.4f} ≠ area_ha {r['area_ha']:.4f}")
            cpt = Point(to_m(d["lon"], d["lat"]))
            rmax = max(cpt.distance(Point(xy)) for xy in g.exterior.coords)
            if abs(rmax - rad) > 0.5:
                err(f"{rad}: bán kính đỉnh {rmax:.2f} m")
            if g.centroid.distance(cpt) > 1.0:
                err(f"{rad}: tâm vùng đệm lệch")
            if r["image"]:
                if not (data.parent / r["image"]).exists():
                    err(f"{rad}: thiếu ảnh {r['image']}")
                (s0, w0), (n0, e0) = r["image_bounds"]
                if not (s0 < d["lat"] < n0 and w0 < d["lon"] < e0):
                    err(f"{rad}: image_bounds không chứa điểm")
            elif r["valid_ha"] > 0:
                err(f"{rad}: có diện tích nhưng không có ảnh")
            rows.append({"id": pid, "radius": rad, "area_ha": r["area_ha"], "geom_ha": geom_ha, "valid_ha": r["valid_ha"],
                         "coverage_percent": r["coverage_percent"], "outside_ha": r["qc"]["outside_ha"],
                         "classes_present": sum(c["area_ha"] > 0 for c in r["classes"])})
        if "rừng bổ sung" in json.dumps(d, ensure_ascii=False).lower():
            err("còn tên 'Rừng bổ sung'")

    # CSV người dùng
    csv_path = data / "dien_tich.csv"
    with open(csv_path, encoding="utf-8-sig") as fh:
        lines = list(csv.DictReader(fh))
    raw = csv_path.read_text(encoding="utf-8-sig").lower()
    for word in FORBIDDEN:
        if word in raw:
            errors.append(f"CSV chứa '{word}'")
    idx = {}
    for ln in lines:
        idx.setdefault((ln["Ma_vi_tri"], int(ln["Ban_kinh_m"])), []).append(ln)
    for p in cat["points"]:
        d = json.loads((data / "details" / f"{p[0]}.json").read_text(encoding="utf-8"))
        for rad, r in d["results"].items():
            got = idx.get((p[0], int(rad)), [])
            if r["valid_ha"] == 0:
                if len(got) != 1 or got[0]["Ma_lop"]:
                    errors.append(f"{p[0]} {rad}: CSV điểm ngoài raster phải có 1 dòng ghi chú")
                continue
            if len(got) != len(code_table):
                errors.append(f"{p[0]} {rad}: CSV có {len(got)} dòng lớp"); continue
            for c, ln in zip(r["classes"], got):
                if int(ln["Ma_lop"]) != c["code"] or ln["Loai_dat"] != c["name"] \
                   or abs(float(ln["Dien_tich_ha"]) - c["area_ha"]) > 5e-7 \
                   or abs(float(ln["Ty_le_phan_tram_toan_vung_dem"]) - c["percent"]) > 5e-7:
                    errors.append(f"{p[0]} {rad}: CSV lớp {c['code']} khác JSON")

    report = {"points": len(cat["points"]), "errors": errors, "rows": rows}
    if a.json:
        Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("Bán kính (m) × số vùng đệm:", dict(Counter(r["radius"] for r in rows)))
    print("Sai lệch lớn nhất diện tích hình học − area_ha (ha):", max(abs(r["geom_ha"] - r["area_ha"]) for r in rows))
    print("Vùng đệm có phần ngoài raster:", sum(1 for r in rows if r["outside_ha"] > 1e-6), "; không có dữ liệu:", sum(1 for r in rows if r["valid_ha"] == 0))
    print("Vùng đệm có đủ 7 lớp > 0:", sum(1 for r in rows if r["classes_present"] == 7))
    print(f"{len(cat['points'])} điểm, {len(errors)} lỗi")
    for e in errors:
        print("  LỖI", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
