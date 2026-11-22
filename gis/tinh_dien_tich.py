"""Bước 3 — Tính diện tích hiện trạng trong vùng đệm từ raster gốc, xuất dữ liệu web.

    python gis/tinh_dien_tich.py [--cau-hinh gis/cau_hinh.toml] [--so-tien-trinh 4]

Đầu vào: gis/ket_qua/diem_hop_nhat.geojson (bước 2), raster gốc, bảng mã lớp,
gis/kho_phu_luc_2.csv (kho có dung tích → bán kính 2/3/5/10 km).

Phương pháp (mỗi điểm, mỗi bán kính):
  1. Vùng đệm = đường tròn bán kính r quanh điểm trong CRS raster (EPSG:32648),
     xấp xỉ bằng 1.440 cạnh (quad_segs = 360).
  2. Diện tích mỗi lớp = tổng diện tích giao thực tế giữa các ô 10 m thuộc lớp đó và
     vùng đệm (ô biên tính theo phần giao, không đếm nguyên ô).
  3. area_ha = diện tích hình học vùng đệm / 10.000; percent = lớp / area_ha × 100
     (mẫu số toàn vùng đệm, không chuẩn hóa về 100 %).
  4. NoData, ngoài phạm vi raster, mã lạ được theo dõi trong qc; kiểm tra cân bằng
     tổng lớp + qc = diện tích vùng đệm.
  5. Ảnh PNG chỉ để hiển thị: chiếu sang EPSG:3857 bằng láng giềng gần nhất.
Kết quả dùng lại (bộ đệm) khi raster, tọa độ và tham số không đổi; các điểm dùng
chung tọa độ dùng chung một phép tính và một ảnh.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chung  # noqa: E402
import webdata  # noqa: E402

_SRC = None
_CTX = {}


def _init(raster_path, ctx):
    import rasterio
    global _SRC, _CTX
    _SRC = rasterio.open(raster_path)
    _CTX = ctx


def task_key(x, y, r, ctx):
    raw = f"{ctx['raster_sha']}|{x:.3f}|{y:.3f}|{r}|{ctx['quad_segs']}|{ctx['png_px'](r)}|{ctx['classes_sig']}|v3"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def compute(task):
    x, y, r, key = task
    ctx = _CTX
    cache = Path(ctx["cache_dir"]) / f"{key}.json"
    png = Path(ctx["image_dir"]) / f"{key}.png"
    if cache.exists() and (png.exists() or json.loads(cache.read_text())["image"] is None):
        return key, json.loads(cache.read_text())
    geom = chung.make_buffer(x, y, r, ctx["quad_segs"])
    codes = [c["code"] for c in ctx["classes"]]
    a = chung.class_areas(_SRC, geom, codes, _SRC.nodata)
    g_m2 = geom.area
    qc_m2 = a["nodata"] + a["outside"] + a["unknown"]
    cls_m2 = sum(a["classes"].values())
    if abs(a["cells_total_m2"] - g_m2) > 1e-6 * g_m2 or abs(cls_m2 + qc_m2 - g_m2) > 1e-6 * g_m2:
        raise RuntimeError(f"Mất cân bằng diện tích tại ({x}, {y}, r={r}): ô {a['cells_total_m2']}, hình {g_m2}")
    area_ha = g_m2 / 1e4
    classes = [{"code": c["code"], "name": c["name"], "color": c["color"],
                "area_ha": a["classes"][c["code"]] / 1e4, "percent": a["classes"][c["code"]] / 1e4 / area_ha * 100}
               for c in ctx["classes"]]
    valid_ha = cls_m2 / 1e4
    res = {
        "radius_m": r, "area_ha": area_ha, "valid_ha": valid_ha, "coverage_percent": valid_ha / area_ha * 100,
        "classes": classes,
        "qc": {"missing_ha": qc_m2 / 1e4, "nodata_ha": a["nodata"] / 1e4, "outside_ha": a["outside"] / 1e4,
               "unknown_ha": a["unknown"] / 1e4, "unknown_codes": {str(k): v / 1e4 for k, v in a["unknown_codes"].items()},
               "vertices": len(geom.exterior.coords) - 1},
        "buffer": chung.geom_to_wgs84_geojson(geom, _SRC.crs),
        "image": None, "image_bounds": None,
    }
    if valid_ha > 0:
        res["image_bounds"] = chung.render_png(_SRC, geom, ctx["classes"], png, size=ctx["png_px"](r))
        res["image"] = f"{ctx['image_url']}/{key}.png"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return key, res


def load_depots(path, ids):
    depots = {}
    if not path or not Path(path).exists():
        return depots, []
    unmatched = []
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            mid = (r.get("ma_diem") or "").strip()
            info = {"stt": int(r["stt"]), "ten_kho": r["ten_kho"], "loai_kho": r["loai_kho"], "dia_chi": r["dia_chi"],
                    "dung_tich_m3": int(r["dung_tich_m3"]) if r["dung_tich_m3"] else None,
                    "tinh_trang": r["tinh_trang"], "muc_khop": r["muc_khop"], "can_cu": r["can_cu"]}
            if not mid:
                unmatched.append(info); continue
            if mid not in ids:
                raise SystemExit(f"Kho {r['stt']}: mã điểm {mid} không có trong diem_hop_nhat.geojson")
            if mid in depots:
                raise SystemExit(f"Mã điểm {mid} được ghép với hơn một kho; cần chủ dự án xác nhận.")
            depots[mid] = info
    return depots, unmatched


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="gis/cau_hinh.toml")
    ap.add_argument("--so-tien-trinh", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--chi-ma", nargs="*", help="chỉ tính các mã này (kiểm thử)")
    a = ap.parse_args(argv)
    cfg = chung.load_config(a.cau_hinh)
    work = Path(cfg["output"]["work_dir"]); web = Path(cfg["output"]["web_dir"])
    raster = cfg["raster"]["path"]
    if not raster.exists():
        raise SystemExit(f"THIẾU raster gốc: {raster}")
    rsha = chung.sha256(raster)
    exp = cfg["raster"].get("expected_sha256")
    if exp and rsha != exp:
        raise SystemExit(f"SHA-256 raster {rsha} khác giá trị mong đợi {exp}. Kiểm tra tệp hoặc cập nhật cấu hình có chủ đích.")
    import rasterio
    with rasterio.open(raster) as src:
        info = chung.raster_info(src)
    problems = chung.check_raster(info, cfg["buffer"]["calc_crs"])
    if problems:
        raise SystemExit("Raster không đạt: " + "; ".join(problems))
    if info["nodata"] is None:
        raise SystemExit("Raster không khai báo NoData; cần chủ dự án xác nhận trước khi tính.")
    classes = chung.read_class_table(cfg["raster"]["class_table"])

    fc = json.loads((work / "diem_hop_nhat.geojson").read_text(encoding="utf-8"))
    feats = fc["features"]
    if a.chi_ma:
        feats = [f for f in feats if f["properties"]["id"] in set(a.chi_ma)]
    ids = {f["properties"]["id"] for f in fc["features"]}
    depots, unmatched = load_depots(cfg.get("depots", {}).get("table"), ids)

    b = cfg["buffer"]
    res_m = info["res"][0]
    png_px = lambda r: int(min(b["max_png_px"], max(b["min_png_px"], math.ceil(2 * r / res_m))))  # noqa: E731
    ctx = {"raster_sha": rsha, "quad_segs": b["quad_segs"], "classes": classes, "png_px": png_px,
           "classes_sig": json.dumps(classes, ensure_ascii=False), "cache_dir": str(work / "cache"),
           "image_dir": str(web / "anh"), "image_url": "data/anh"}
    tasks, plan = {}, []
    for f in feats:
        p = f["properties"]
        radii = b["depot_radii_m"] if p["id"] in depots else b["radii_m"]
        for r in radii:
            k = task_key(p["x_m"], p["y_m"], r, ctx)
            tasks[k] = (p["x_m"], p["y_m"], r, k)
            plan.append((p["id"], r, k))
    print(f"{len(feats)} điểm, {len(plan)} vùng đệm, {len(tasks)} phép tính duy nhất; {a.so_tien_trinh} tiến trình")
    t0 = time.time()
    ctx_pickle = dict(ctx); ctx_pickle["png_px"] = None
    results = {}
    if a.so_tien_trinh > 1:
        with ProcessPoolExecutor(a.so_tien_trinh, initializer=_init_wrapper, initargs=(str(raster), ctx_pickle, b, res_m)) as ex:
            for i, (k, res) in enumerate(ex.map(compute, tasks.values(), chunksize=4)):
                results[k] = res
                if (i + 1) % 100 == 0:
                    print(f"  {i + 1}/{len(tasks)} ({time.time() - t0:.0f} s)")
    else:
        _init_wrapper(str(raster), ctx_pickle, b, res_m)
        for k, t in tasks.items():
            results[k] = compute(t)[1]
    print(f"Tính xong sau {time.time() - t0:.1f} s")

    points = []
    by_point = {}
    for pid, r, k in plan:
        by_point.setdefault(pid, {})[str(r)] = results[k]
    for f in feats:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        item = {"id": p["id"], "name": p["name"], "kind": p["kind"], "lon": lon, "lat": lat,
                "address": p.get("address", ""), "position_quality": p.get("position_quality", ""),
                "source": p["source"], "source_fid": p["fid"], "merged_from": p.get("merged_from", []),
                "depot": depots.get(p["id"]), "results": by_point[p["id"]]}
        if p.get("description"):
            item["description"] = p["description"]
        points.append(item)

    src_labels = {s["key"]: s["label"] for s in cfg["sources"]}
    kinds_count = {}
    for pt in points:
        kinds_count[pt["kind"]] = kinds_count.get(pt["kind"], 0) + 1
    merge_report = (work / "bao_cao_hop_nhat.md").read_text(encoding="utf-8")
    auto = merge_report.count("— gop (tự động)")
    meta = {
        "title": "Hiện trạng quanh cơ sở xăng dầu", "year": cfg["raster"]["year"], "radius_m": b["radii_m"][0],
        "radii_default": b["radii_m"], "radii_depot": b["depot_radii_m"],
        "crs": b["calc_crs"], "crs_label": b["calc_crs_label"], "resolution_m": info["res"], "classes": classes,
        "sources": [{"label": f"Vị trí — {s['label']}", "name": s["name"], "sha256": s["sha256"]} for s in fc["sources"]]
                   + [{"label": f"Hiện trạng năm {cfg['raster']['year']}", "name": raster.name, "sha256": rsha},
                      {"label": "Kho có dung tích", "name": cfg.get("depots", {}).get("source_label", ""), "sha256": ""}],
        "method": ("Vùng đệm tròn trong WGS 84 / UTM 48N, xấp xỉ bằng 1.440 cạnh. Diện tích ô biên được tính theo phần giao "
                   "với vùng đệm, sử dụng raster gốc 10 m. Tỷ lệ từng lớp tính trên toàn diện tích vùng đệm. "
                   "Ảnh hiển thị dùng lấy mẫu láng giềng gần nhất, không dùng để tính diện tích."),
        "selection": (f"{len(points)} vị trí: " + ", ".join(f"{v} {k.lower()}" for k, v in kinds_count.items())
                      + f". Gộp {auto} bản ghi trùng hoàn toàn (cùng tên, địa chỉ và tọa độ). Từ tệp bencang chỉ lấy bến cảng."
                      + f" {len(depots)}/{len(depots) + len(unmatched)} kho trong Phụ lục 2 được ghép với điểm trên bản đồ và có thêm bán kính 3, 5, 10 km."),
        "scope_note": cfg["output"]["scope_note"],
        "depots_unmatched": [{"stt": u["stt"], "ten_kho": u["ten_kho"], "dung_tich_m3": u["dung_tich_m3"]} for u in unmatched],
    }
    stats = webdata.write_web_data(web, meta, points)
    used = {Path(r["image"]).name for pt in points for r in pt["results"].values() if r["image"]}
    removed = 0
    for img in (web / "anh").glob("*.png"):
        if img.name not in used:
            img.unlink(); removed += 1
    img_bytes = sum((web / "anh" / n).stat().st_size for n in used)
    stats.update({"images": len(used), "image_bytes_total": img_bytes, "images_removed": removed})
    (work / "thong_ke_xuat.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


def _init_wrapper(raster_path, ctx, b, res_m):
    ctx = dict(ctx)
    ctx["png_px"] = lambda r: int(min(b["max_png_px"], max(b["min_png_px"], math.ceil(2 * r / res_m))))
    _init(raster_path, ctx)


if __name__ == "__main__":
    main()
