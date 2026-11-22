"""Ghi dữ liệu web tĩnh: danh mục nhẹ, chi tiết từng điểm và CSV người dùng.

Không làm tròn số liệu gốc; chỉ giao diện mới làm tròn khi hiển thị.
Trường kiểm soát chất lượng (qc: nodata/outside/unknown/missing) nằm trong JSON
chi tiết để kiểm tra nội bộ; giao diện, biểu đồ và CSV không hiển thị các diện tích này.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

CATALOG_FIELDS = ["id", "name", "kind", "lon", "lat", "address", "estimated", "depot", "status"]
CSV_HEADER = ["Ma_vi_tri", "Ten_vi_tri", "Loai_co_so", "Kinh_do", "Vi_do", "Vi_tri_uoc_luong", "Ban_kinh_m",
              "Ma_lop", "Loai_dat", "Dien_tich_ha", "Ty_le_phan_tram_toan_vung_dem", "Ghi_chu"]
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
NOTE_OUTSIDE = "Vùng đệm nằm ngoài phạm vi raster hiện trạng; không tính diện tích"
NOTE_PARTIAL = "Một phần vùng đệm nằm ngoài phạm vi raster hiện trạng"


def _dump(obj, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return text


def is_estimated(p) -> bool:
    return "ước lượng" in (p.get("position_quality") or "").lower()


def point_status(results: dict) -> str:
    r = results[min(results, key=int)]
    if r["valid_ha"] == 0 and r["qc"].get("outside_ha", 0) > 0:
        return "outside"
    if r["qc"].get("outside_ha", 0) > 1e-6:
        return "partial"
    return ""


def write_web_data(out_dir: Path, meta: dict, points: list[dict]) -> dict:
    """points: id, name, kind, lon, lat, address, position_quality, depot|None,
    results {"2000": {...}, ...}."""
    out_dir = Path(out_dir)
    details_dir = out_dir / "details"
    details_dir.mkdir(parents=True, exist_ok=True)
    ids = [p["id"] for p in points]
    if len(ids) != len(set(ids)):
        raise ValueError("ID web bị trùng.")
    bad = [i for i in ids if not SAFE_ID.match(i)]
    if bad:
        raise ValueError(f"ID không dùng được làm tên tệp: {bad[:5]}")
    codes = [c["code"] for c in meta["classes"]]
    keep = set(ids)
    for old in details_dir.glob("*.json"):
        if old.stem not in keep:
            old.unlink()
    digest = hashlib.sha256()
    sizes = []
    for p in points:
        for rad, r in p["results"].items():
            if [c["code"] for c in r["classes"]] != codes:
                raise ValueError(f"{p['id']} {rad}: mã lớp sai thứ tự")
        p["status"] = point_status(p["results"])
        text = _dump(p, details_dir / f"{p['id']}.json")
        digest.update(text.encode()); sizes.append(len(text.encode()))

    kinds = []
    for p in points:
        if p["kind"] not in kinds:
            kinds.append(p["kind"])
    catalog = dict(meta)
    catalog["version"] = digest.hexdigest()[:12]
    catalog["kinds"] = [{"name": k, "count": sum(p["kind"] == k for p in points)} for k in kinds]
    catalog["depot_count"] = sum(1 for p in points if p.get("depot"))
    catalog["estimated_count"] = sum(1 for p in points if is_estimated(p))
    catalog["outside_count"] = sum(1 for p in points if p["status"] == "outside")
    catalog["fields"] = CATALOG_FIELDS
    catalog["points"] = [[p["id"], p["name"], p["kind"], p["lon"], p["lat"], p.get("address", ""),
                          1 if is_estimated(p) else 0,
                          p["depot"]["dung_tich_m3"] if p.get("depot") else 0, p["status"]] for p in points]
    cat_text = _dump(catalog, out_dir / "catalog.json")

    with open(out_dir / "dien_tich.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for p in points:
            est = "Có" if is_estimated(p) else ""
            for rad in sorted(p["results"], key=int):
                r = p["results"][rad]
                base = [p["id"], p["name"], p["kind"], p["lon"], p["lat"], est, rad]
                if r["valid_ha"] == 0 and r["qc"].get("outside_ha", 0) > 0:
                    w.writerow(base + ["", "", "", "", NOTE_OUTSIDE]); continue
                note = NOTE_PARTIAL if r["qc"].get("outside_ha", 0) > 1e-6 else ""
                for c in r["classes"]:
                    w.writerow(base + [c["code"], c["name"], f"{c['area_ha']:.6f}", f"{c['percent']:.6f}", note])
    return {"points": len(points), "catalog_bytes": len(cat_text.encode()), "detail_bytes_max": max(sizes),
            "detail_bytes_total": sum(sizes), "version": catalog["version"]}
