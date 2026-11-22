"""Bước 4 — Đối chiếu độc lập: polygon hóa raster (rasterio.features.shapes) rồi
giao từng polygon lớp với vùng đệm, so với kết quả đã xuất.

    python gis/doi_chieu_doc_lap.py [--ma BC21 TXD0001 ...]

Không chỉ định mã thì tự chọn mẫu: điểm nội vùng, sát mép raster, nhiều NoData,
cặp điểm gần nhau nhất (khác tọa độ), điểm có đủ 7 lớp, và mọi bán kính của 1 kho.
Ghi gis/ket_qua/doi_chieu_doc_lap.md. Thoát mã 1 nếu lệch > 1 m² ở bất kỳ lớp nào.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
import shapely
from rasterio.features import shapes
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chung  # noqa: E402

TOL_M2 = 1.0


def polygon_areas(src, geom, codes):
    arr, r0, c0 = chung.read_cells(src, geom)
    t = src.transform
    tr = rasterio.Affine(t.a, 0, t.c + c0 * t.a, 0, t.e, t.f + r0 * t.e)
    out = {c: 0.0 for c in codes}
    other = 0.0
    a32 = np.where(arr == chung.OUTSIDE, -1, arr).astype(np.int32)
    shapely.prepare(geom)
    for g, v in shapes(a32, transform=tr, connectivity=4):
        p = shape(g)
        if not shapely.intersects(geom, p):
            continue
        ar = shapely.intersection(p, geom).area
        if int(v) in out:
            out[int(v)] += ar
        else:
            other += ar
    return out, other


def pick_samples(cat, data):
    pts = {p[0]: p for p in cat["points"]}
    det = {i: json.loads((data / "details" / f"{i}.json").read_text(encoding="utf-8")) for i in pts}
    r2 = {i: d["results"]["2000"] for i, d in det.items()}
    inside = [i for i in r2 if r2[i]["qc"]["outside_ha"] == 0]
    s = {}
    s["Nội vùng, phủ dữ liệu cao nhất"] = max(inside, key=lambda i: r2[i]["coverage_percent"])
    part = [i for i in r2 if r2[i]["qc"]["outside_ha"] > 1e-6 and r2[i]["valid_ha"] > 0]
    if part:
        s["Sát mép raster (một phần ngoài phạm vi)"] = max(part, key=lambda i: r2[i]["qc"]["outside_ha"])
    s["Nhiều NoData nhất"] = max(r2, key=lambda i: r2[i]["qc"]["nodata_ha"])
    full7 = [i for i in r2 if all(c["area_ha"] > 0 for c in r2[i]["classes"])]
    if full7:
        s["Có đủ 7 lớp (gồm Rừng)"] = max(full7, key=lambda i: r2[i]["classes"][6]["area_ha"])
    # cặp gần nhau nhất khác tọa độ
    ids = list(pts)
    xy = np.array([[pts[i][3], pts[i][4]] for i in ids])
    best = (9e9, None, None)
    for k in range(len(ids)):
        d = np.hypot((xy[:, 0] - xy[k, 0]) * 109600, (xy[:, 1] - xy[k, 1]) * 110600)
        d[k] = 9e9; d[d < 0.5] = 9e9
        j = int(d.argmin())
        if d[j] < best[0]:
            best = (d[j], ids[k], ids[j])
    s[f"Cặp gần nhau ({best[0]:.1f} m) — A"] = best[1]
    s[f"Cặp gần nhau ({best[0]:.1f} m) — B"] = best[2]
    s["Kho có dung tích (mọi bán kính)"] = max((i for i in det if det[i].get("depot")), key=lambda i: det[i]["depot"]["dung_tich_m3"] or 0)
    return s, det


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="gis/cau_hinh.toml")
    ap.add_argument("--ma", nargs="*")
    a = ap.parse_args(argv)
    cfg = chung.load_config(a.cau_hinh)
    data = Path(cfg["output"]["web_dir"])
    cat = json.loads((data / "catalog.json").read_text(encoding="utf-8"))
    codes = [c["code"] for c in cat["classes"]]
    if a.ma:
        samples = {f"Chỉ định {m}": m for m in a.ma}
        det = {m: json.loads((data / "details" / f"{m}.json").read_text(encoding="utf-8")) for m in a.ma}
    else:
        samples, det = pick_samples(cat, data)
    to_m = chung.transformer("EPSG:4326", cfg["buffer"]["calc_crs"])
    L = ["# Đối chiếu độc lập (polygon hóa raster)", "", "| Trường hợp | Mã | Bán kính | Lớp lệch lớn nhất (m²) | NoData+ngoài (ha) xuất / kiểm | Phủ % |", "| --- | --- | --- | --- | --- | --- |"]
    worst = 0.0
    with rasterio.open(cfg["raster"]["path"]) as src:
        for label, pid in samples.items():
            d = det[pid]
            x, y = to_m.transform(d["lon"], d["lat"])
            for rad, r in sorted(d["results"].items(), key=lambda kv: int(kv[0])):
                if "mọi bán kính" not in label and rad != "2000":
                    continue
                geom = chung.make_buffer(x, y, int(rad), cfg["buffer"]["quad_segs"])
                got, other = polygon_areas(src, geom, codes)
                diff = max(abs(got[c["code"]] - c["area_ha"] * 1e4) for c in r["classes"])
                worst = max(worst, diff)
                L.append(f"| {label} | {pid} | {int(rad) // 1000} km | {diff:.2e} | {r['qc']['missing_ha']:.4f} / {other / 1e4 + (geom.area - sum(got.values()) - other) / 1e4:.4f} | {r['coverage_percent']:.2f} |")
    L += ["", f"Sai lệch lớn nhất: {worst:.3e} m² (ngưỡng {TOL_M2} m²)."]
    out = Path(cfg["output"]["work_dir"]) / "doi_chieu_doc_lap.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 1 if worst > TOL_M2 else 0


if __name__ == "__main__":
    sys.exit(main())
