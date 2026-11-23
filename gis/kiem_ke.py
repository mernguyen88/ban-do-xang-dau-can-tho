"""Bước 1 — Kiểm kê tệp đầu vào (không sửa dữ liệu).

    python gis/kiem_ke.py [--cau-hinh gis/cau_hinh.toml]

Báo cáo: gis/ket_qua/kiem_ke.md và kiem_ke.json
  - từng lớp điểm: tồn tại?, thành phần ZIP (.shp/.shx/.dbf/.prj/.cpg), số bản ghi,
    kiểu hình học, CRS, hình học rỗng, tọa độ ngoài Việt Nam/ngoài raster,
    trùng hình học, trùng tên, danh sách trường + mức duy nhất (để chọn id_field);
  - raster: SHA-256, CRS, độ phân giải, NoData, kiểu dữ liệu, phạm vi, giá trị pixel
    (đếm theo khối) đối chiếu bảng mã.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chung  # noqa: E402

VN_BBOX = (102.0, 8.0, 110.5, 23.5)


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(chung.ROOT))
    except ValueError:
        return str(path)


def inventory_vector(path: Path, layer=None, source_crs=None, raster_bounds_wgs=None):
    rep = {"path": rel(path), "exists": path.exists()}
    if not path.exists():
        return rep
    rep["sha256"] = chung.sha256(path)
    members = chung.zip_members(path)
    if members:
        exts = {Path(m).suffix.lower() for m in members}
        rep["zip_members"] = members
        rep["zip_missing"] = [e for e in (".shp", ".shx", ".dbf", ".prj") if e not in exts]
        rep["has_cpg"] = ".cpg" in exts
    try:
        gdf, layers = chung.read_vector(path, layer or None)
    except Exception as e:  # báo lỗi rõ, không dừng các nguồn khác
        rep["error"] = str(e)
        return rep
    rep["layers"] = layers
    rep["records"] = len(gdf)
    rep["crs"] = gdf.crs.to_string() if gdf.crs else None
    rep["epsg"] = gdf.crs.to_epsg() if gdf.crs else None
    rep["geom_types"] = gdf.geometry.geom_type.fillna("NULL").value_counts().to_dict()
    empty = gdf.geometry.isna() | gdf.geometry.is_empty
    rep["empty_geometry"] = int(empty.sum())
    crs = gdf.crs or (source_crs or None)
    rep["crs_used_for_check"] = str(crs) if crs else None
    if crs is None:
        rep["coordinate_check"] = "KHÔNG kiểm tra được: thiếu CRS (.prj). Không tự gán CRS."
    else:
        g = gdf.loc[~empty].geometry
        pts = g.representative_point() if not all(g.geom_type == "Point") else g
        tr = chung.transformer(crs, "EPSG:4326")
        lon, lat = tr.transform(pts.x.values, pts.y.values)
        import numpy as np
        lon, lat = np.asarray(lon), np.asarray(lat)
        bad = ~np.isfinite(lon) | ~np.isfinite(lat) | (lon < VN_BBOX[0]) | (lon > VN_BBOX[2]) | (lat < VN_BBOX[1]) | (lat > VN_BBOX[3])
        rep["outside_vietnam"] = int(bad.sum())
        rep["wgs84_extent"] = [float(np.nanmin(lon)), float(np.nanmin(lat)), float(np.nanmax(lon)), float(np.nanmax(lat))] if len(lon) else None
        if raster_bounds_wgs:
            w, s, e, n = raster_bounds_wgs
            rep["outside_raster_extent"] = int((~bad & ((lon < w) | (lon > e) | (lat < s) | (lat > n))).sum())
        wkb = g.to_wkb()
        rep["duplicate_geometry_records"] = int(wkb.duplicated(keep=False).sum())
    fields = []
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        s = gdf[col]
        nn = s.dropna().astype(str).str.strip()
        nn = nn[nn != ""]
        fields.append({"name": col, "dtype": str(s.dtype), "non_empty": int(len(nn)), "unique": int(nn.nunique()),
                       "is_unique_id_candidate": bool(len(nn) == len(gdf) and nn.nunique() == len(gdf))})
    rep["fields"] = fields
    return rep


def inventory_raster(path: Path, class_table, expected_sha, calc_crs, full_scan=True):
    rep = {"path": rel(path), "exists": path.exists()}
    if not path.exists():
        return rep
    import rasterio
    rep["sha256"] = chung.sha256(path)
    rep["sha256_matches_expected"] = (rep["sha256"] == expected_sha) if expected_sha else None
    with rasterio.open(path) as src:
        info = chung.raster_info(src)
        rep.update(info)
        rep["problems"] = chung.check_raster(info, calc_crs)
        if src.crs:
            tr = chung.transformer(src.crs, "EPSG:4326")
            b = src.bounds
            xs, ys = tr.transform([b.left, b.right, b.left, b.right], [b.bottom, b.bottom, b.top, b.top])
            rep["bounds_wgs84"] = [min(xs), min(ys), max(xs), max(ys)]
        if full_scan:
            counts = chung.raster_value_counts(src)
            px = abs(src.transform.a * src.transform.e)
            rep["value_counts"] = {str(k): v for k, v in counts.items()}
            codes = {c["code"] for c in class_table}
            rep["codes_missing_in_raster"] = sorted(codes - set(counts))
            others = [k for k in counts if k not in codes and k != src.nodata]
            rep["values_not_in_class_table"] = {str(k): {"pixels": counts[k], "area_ha": counts[k] * px / 1e4} for k in others}
    return rep


def md_report(r):
    L = ["# Kiểm kê tệp đầu vào", ""]
    ras = r["raster"]
    L += ["## Raster", ""]
    if not ras["exists"]:
        L.append(f"- **THIẾU** `{ras['path']}`")
    else:
        for k in ("sha256", "sha256_matches_expected", "crs", "res", "nodata", "dtype", "width", "height", "bounds", "bounds_wgs84", "problems",
                  "codes_missing_in_raster", "values_not_in_class_table"):
            L.append(f"- {k}: `{ras.get(k)}`")
    for key, s in r["sources"].items():
        L += ["", f"## Nguồn `{key}`", ""]
        if not s["exists"]:
            L.append(f"- **THIẾU** `{s['path']}`"); continue
        if s.get("error"):
            L.append(f"- **LỖI ĐỌC**: {s['error']}"); continue
        for k in ("records", "layers", "crs", "geom_types", "empty_geometry", "outside_vietnam", "outside_raster_extent",
                  "duplicate_geometry_records", "zip_missing", "has_cpg", "coordinate_check", "wgs84_extent"):
            if k in s:
                L.append(f"- {k}: `{s[k]}`")
        L += ["", "| Trường | Kiểu | Có giá trị | Duy nhất | Ứng viên ID |", "| --- | --- | --- | --- | --- |"]
        for f in s["fields"]:
            L.append(f"| {f['name']} | {f['dtype']} | {f['non_empty']} | {f['unique']} | {'có' if f['is_unique_id_candidate'] else ''} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="gis/cau_hinh.toml")
    ap.add_argument("--khong-quet-raster", action="store_true", help="bỏ qua đếm giá trị pixel toàn raster")
    a = ap.parse_args(argv)
    cfg = chung.load_config(a.cau_hinh)
    classes = chung.read_class_table(cfg["raster"]["class_table"])
    ras = inventory_raster(cfg["raster"]["path"], classes, cfg["raster"].get("expected_sha256"), cfg["buffer"].get("calc_crs"),
                           full_scan=not a.khong_quet_raster)
    rb = ras.get("bounds_wgs84")
    sources = {}
    for s in cfg.get("sources", []):
        sources[s["key"]] = inventory_vector(s["path"], s.get("layer"), s.get("source_crs") or None, rb)
    report = {"raster": ras, "sources": sources}
    out = Path(cfg["output"]["work_dir"]); out.mkdir(parents=True, exist_ok=True)
    (out / "kiem_ke.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (out / "kiem_ke.md").write_text(md_report(report), encoding="utf-8")
    print(md_report(report))
    missing = [k for k, s in sources.items() if not s["exists"]] + ([] if ras["exists"] else ["raster"])
    if missing:
        print("THIẾU:", ", ".join(missing))
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
