"""Bước 2 — Chuẩn hóa, gán ID ổn định, đối chiếu trùng và hợp nhất các lớp điểm.

    python gis/hop_nhat_diem.py [--cau-hinh gis/cau_hinh.toml]

Kết quả trong gis/ket_qua/:
  diem_hop_nhat.geojson  điểm cuối cùng (WGS84) + x_m, y_m trong CRS tính toán
  anh_xa_id.csv          mọi bản ghi nguồn → ID web, trạng thái (giu / gop_vao / loai)
  doi_chieu_trung.csv    các cặp gần nhau/cùng tên: khoảng cách, phân loại, quyết định
  bao_cao_hop_nhat.md    số bản ghi đọc, loại, gộp, chờ xác minh, tổng cuối cùng

Quy tắc:
  - ID: tiền tố nguồn + ID nguồn; nếu nguồn không có trường ID thì dùng thứ tự
    bản ghi (FID + 1). Thứ tự này chỉ ổn định khi tệp nguồn không đổi — SHA-256
    của tệp nguồn được ghi vào báo cáo để đối chiếu.
  - Gộp tự động chỉ khi cùng tên + cùng địa chỉ (đã chuẩn hóa) + cách ≤ auto_merge_m.
  - Các cặp khác chỉ được liệt kê; gộp khi người dùng ghi `gop` trong
    gis/quyet_dinh_trung.csv. Ghi `rieng` để tách một cặp gộp tự động.
  - Không tự sửa tọa độ, không gán tọa độ theo địa chỉ.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chung  # noqa: E402

VN_BBOX = (102.0, 8.0, 110.5, 23.5)


def clean(v):
    if v is None:
        return ""
    if isinstance(v, float) and np.isnan(v):
        return ""
    return " ".join(str(v).split())


def load_source(s: dict, calc_crs: str):
    gdf, _ = chung.read_vector(s["path"], s.get("layer") or None)
    if gdf.crs is None:
        if not s.get("source_crs"):
            raise SystemExit(f"{s['path'].name}: thiếu CRS (.prj). Cần chủ dự án xác nhận CRS gốc rồi điền source_crs.")
        gdf = gdf.set_crs(s["source_crs"])
    to_wgs = chung.transformer(gdf.crs, "EPSG:4326")
    to_m = chung.transformer(gdf.crs, calc_crs)
    recs, dropped = [], []
    rules = [(re.compile(p, re.I), k) for p, k in s.get("kind_rules", [])]
    include = re.compile(s["include_name_regex"], re.I) if s.get("include_name_regex") else None
    ids_seen = {}
    for fid, row in enumerate(gdf.itertuples(index=False)):
        g = getattr(row, gdf.geometry.name)
        src_id = clean(getattr(row, s["id_field"])) if s.get("id_field") else str(fid + 1)
        base = {"source": s["key"], "fid": fid, "source_id": src_id}
        if g is None or g.is_empty:
            dropped.append({**base, "ly_do": "hình học rỗng"}); continue
        if g.geom_type == "MultiPoint" and len(g.geoms) == 1:
            g = g.geoms[0]
        if g.geom_type != "Point":
            if s.get("center") == "fields":
                lon = float(getattr(row, s["center_lon_field"])); lat = float(getattr(row, s["center_lat_field"]))
                g = shapely.Point(*chung.transformer("EPSG:4326", gdf.crs).transform(lon, lat))
            else:
                dropped.append({**base, "ly_do": f"hình học {g.geom_type}: cần chủ dự án chỉ định điểm làm tâm"}); continue
        lon, lat = to_wgs.transform(g.x, g.y)
        if not (np.isfinite(lon) and np.isfinite(lat)) or not (VN_BBOX[0] <= lon <= VN_BBOX[2] and VN_BBOX[1] <= lat <= VN_BBOX[3]):
            dropped.append({**base, "ly_do": f"tọa độ ngoài Việt Nam ({lon}, {lat})"}); continue
        if not src_id:
            dropped.append({**base, "ly_do": "thiếu ID nguồn"}); continue
        if src_id in ids_seen:
            raise SystemExit(f"{s['path'].name}: ID nguồn {src_id!r} trùng (bản ghi {ids_seen[src_id]} và {fid}); chọn id_field khác.")
        ids_seen[src_id] = fid
        name = clean(getattr(row, s["name_field"]))
        if include and not include.search(name):
            dropped.append({**base, "ly_do": s.get("exclude_reason", "không khớp điều kiện chọn")}); continue
        kind = s["kind"]
        if s.get("kind_field"):
            kind = clean(getattr(row, s["kind_field"])) or kind
        for pat, k in rules:
            if pat.search(name):
                kind = k; break
        x, y = to_m.transform(g.x, g.y)
        sid = src_id.zfill(s.get("id_width", 0)) if src_id.isdigit() else src_id
        recs.append({
            "id": chung.web_id(s["id_prefix"], sid) if not src_id.isdigit() else f"{s['id_prefix']}{sid}",
            **base, "name": name or f"{s['label']} {src_id}", "kind": kind,
            "address": clean(getattr(row, s["address_field"])) if s.get("address_field") else "",
            "description": clean(getattr(row, s["description_field"])) if s.get("description_field") else "",
            "position_quality": clean(getattr(row, s["quality_field"])) if s.get("quality_field") else "",
            "lon": round(float(lon), 7), "lat": round(float(lat), 7), "x_m": float(x), "y_m": float(y),
        })
    return gdf, recs, dropped


def read_decisions(path):
    dec = {}
    if path and Path(path).exists():
        with open(path, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if not r.get("id_a"):
                    continue
                key = tuple(sorted((r["id_a"].strip(), r["id_b"].strip())))
                dec[key] = {"quyet_dinh": (r.get("quyet_dinh") or "").strip().lower(), "giu_id": (r.get("giu_id") or "").strip(),
                            "ghi_chu": r.get("ghi_chu", "")}
    return dec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="gis/cau_hinh.toml")
    a = ap.parse_args(argv)
    cfg = chung.load_config(a.cau_hinh)
    calc = cfg["buffer"]["calc_crs"]
    dd = cfg["dedupe"]
    out = Path(cfg["output"]["work_dir"]); out.mkdir(parents=True, exist_ok=True)

    all_recs, all_dropped, read_counts, src_meta = [], [], {}, []
    for s in cfg["sources"]:
        gdf, recs, dropped = load_source(s, calc)
        read_counts[s["key"]] = len(gdf)
        src_meta.append({"key": s["key"], "label": s["label"], "name": Path(s["path"]).name,
                         "sha256": chung.sha256(s["path"]), "crs": gdf.crs.to_string(), "records": len(gdf)})
        all_recs += recs; all_dropped += dropped
    ids = [r["id"] for r in all_recs]
    if len(ids) != len(set(ids)):
        raise SystemExit("ID web trùng giữa các nguồn; đổi id_prefix.")
    by_id = {r["id"]: r for r in all_recs}
    order = {r["id"]: i for i, r in enumerate(all_recs)}

    # ---- tìm cặp gần nhau
    xy = np.array([[r["x_m"], r["y_m"]] for r in all_recs])
    pts = shapely.points(xy)
    tree = shapely.STRtree(pts)
    reach = max(dd["review_m"], dd["review_same_name_m"], dd["auto_merge_m"])
    left, right = tree.query(pts, predicate="dwithin", distance=reach)
    pairs = []
    for i, j in zip(left.tolist(), right.tolist()):
        if i >= j:
            continue
        a_, b_ = all_recs[i], all_recs[j]
        d = float(np.hypot(*(xy[i] - xy[j])))
        same_name = chung.fold(a_["name"]) == chung.fold(b_["name"])
        same_addr = chung.fold(a_["address"]) == chung.fold(b_["address"])
        if same_name and same_addr and d <= dd["auto_merge_m"] and dd["auto_merge_m"] > 0:
            cat = "tu_dong_gop"
        elif same_name and d <= dd["review_same_name_m"]:
            cat = "cung_ten_khac_vi_tri"
        elif d <= dd["review_m"]:
            cat = "gan_nhau_khac_ten"
        else:
            continue
        pairs.append({"id_a": a_["id"], "id_b": b_["id"], "khoang_cach_m": round(d, 3), "phan_loai": cat,
                      "cung_ten": same_name, "cung_dia_chi": same_addr,
                      "ten_a": a_["name"], "ten_b": b_["name"], "dia_chi_a": a_["address"], "dia_chi_b": b_["address"],
                      "vi_tri_a": a_["position_quality"], "vi_tri_b": b_["position_quality"]})

    # Trùng hoàn toàn + duplicate_action = "offset": giữ riêng, dịch bản ghi sau về phía đông
    offset_notes = []
    if dd.get("duplicate_action") == "offset":
        step = float(dd.get("duplicate_offset_m", 10.0))
        shift_count = defaultdict(int)
        to_wgs = chung.transformer(calc, "EPSG:4326")
        for p in pairs:
            if p["phan_loai"] != "tu_dong_gop":
                continue
            later = by_id[p["id_b"]] if order[p["id_b"]] > order[p["id_a"]] else by_id[p["id_a"]]
            shift_count[p["id_a"]] += 1
            k = shift_count[p["id_a"]]
            later["x_m"] += step * k
            lon, lat = to_wgs.transform(later["x_m"], later["y_m"])
            later["lon"], later["lat"] = round(float(lon), 7), round(float(lat), 7)
            later["coord_note"] = f"dịch {step * k:g} m về phía đông (trùng hoàn toàn {p['id_a']})"
            p["phan_loai"] = "trung_hoan_toan_dich_toa_do"
            p["quyet_dinh"] = f"giữ riêng, dịch {later['id']} {step * k:g} m"
            offset_notes.append(f"- {later['id']} dịch {step * k:g} m đông (trùng {p['id_a']}): {later['name']} · {later['address']}")

    decisions = read_decisions(dd.get("decisions"))
    parent = {i: i for i in ids}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    keep_pref = {}
    for p in pairs:
        key = tuple(sorted((p["id_a"], p["id_b"])))
        dec = decisions.get(key, {})
        q = dec.get("quyet_dinh", "")
        merge = (p["phan_loai"] == "tu_dong_gop" and q != "rieng") or q == "gop"
        if p["phan_loai"] == "trung_hoan_toan_dich_toa_do":
            continue
        p["quyet_dinh"] = q or ("gop (tự động)" if p["phan_loai"] == "tu_dong_gop" else "giữ riêng (chưa có quyết định)")
        if merge:
            ra, rb = find(p["id_a"]), find(p["id_b"])
            if ra != rb:
                parent[rb] = ra
            if dec.get("giu_id"):
                keep_pref[find(p["id_a"])] = dec["giu_id"]
    groups = defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    final, id_map = [], []
    for root, members in groups.items():
        members.sort(key=lambda m: order[m])
        rep = keep_pref.get(root) if keep_pref.get(root) in members else members[0]
        r = dict(by_id[rep]); r["merged_from"] = [m for m in members if m != rep]
        final.append(r)
        for m in members:
            id_map.append({"source": by_id[m]["source"], "fid": by_id[m]["fid"], "source_id": by_id[m]["source_id"],
                           "web_id": rep, "trang_thai": "giu" if m == rep else "gop_vao", "ten": by_id[m]["name"]})
    for d in all_dropped:
        id_map.append({"source": d["source"], "fid": d["fid"], "source_id": d["source_id"], "web_id": "", "trang_thai": "loai: " + d["ly_do"], "ten": ""})
    final.sort(key=lambda r: order[r["id"]])
    id_map.sort(key=lambda r: (r["source"], r["fid"]))

    # ---- ghi kết quả
    fc = {"type": "FeatureCollection", "crs_calc": calc, "sources": src_meta, "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
         "properties": {k: v for k, v in r.items() if k not in ("lon", "lat")}} for r in final]}
    (out / "diem_hop_nhat.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    with open(out / "anh_xa_id.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, ["source", "fid", "source_id", "web_id", "trang_thai", "ten"]); w.writeheader(); w.writerows(id_map)
    cols = ["id_a", "id_b", "khoang_cach_m", "phan_loai", "quyet_dinh", "cung_ten", "cung_dia_chi", "ten_a", "ten_b", "dia_chi_a", "dia_chi_b", "vi_tri_a", "vi_tri_b"]
    with open(out / "doi_chieu_trung.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(pairs)

    # nhóm trùng tọa độ (vị trí ước lượng dùng chung tâm phường/xã)
    coord_groups = defaultdict(list)
    for r in final:
        coord_groups[(round(r["x_m"], 2), round(r["y_m"], 2))].append(r["id"])
    shared = [g for g in coord_groups.values() if len(g) > 1]
    cnt = defaultdict(int)
    for p in pairs:
        cnt[p["phan_loai"]] += 1
    kinds = defaultdict(int)
    for r in final:
        kinds[r["kind"]] += 1
    L = ["# Báo cáo hợp nhất điểm", ""]
    L += ["| Nguồn | Tệp | SHA-256 | CRS | Bản ghi đọc | Loại bỏ | Gộp vào bản ghi khác | Còn lại |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m in src_meta:
        dropped = sum(1 for d in all_dropped if d["source"] == m["key"])
        merged = sum(1 for x in id_map if x["source"] == m["key"] and x["trang_thai"] == "gop_vao")
        kept = sum(1 for x in id_map if x["source"] == m["key"] and x["trang_thai"] == "giu")
        L.append(f"| {m['label']} | {m['name']} | `{m['sha256'][:12]}…` | {m['crs']} | {m['records']} | {dropped} | {merged} | {kept} |")
    L += ["", f"**Tổng điểm cuối cùng: {len(final)}** (" + ", ".join(f"{k}: {v}" for k, v in kinds.items()) + ")", ""]
    L += [f"- Cặp trùng hoàn toàn (cùng tên + cùng địa chỉ + ≤ {dd['auto_merge_m']} m): {cnt['tu_dong_gop'] + cnt['trung_hoan_toan_dich_toa_do']} "
          f"({'giữ riêng, dịch tọa độ' if offset_notes else 'gộp'})",
          f"- Cặp cùng tên nhưng khác vị trí (≤ {dd['review_same_name_m']} m), giữ riêng: {cnt['cung_ten_khac_vi_tri']}",
          f"- Cặp khác tên cách ≤ {dd['review_m']} m, giữ riêng: {cnt['gan_nhau_khac_ten']}",
          f"- Quyết định người dùng đã áp dụng: {sum(1 for p in pairs if tuple(sorted((p['id_a'], p['id_b']))) in decisions)}",
          f"- Nhóm điểm dùng chung một tọa độ sau hợp nhất: {len(shared)} nhóm, {sum(len(g) for g in shared)} điểm (lớn nhất {max((len(g) for g in shared), default=0)})",
          f"- Điểm ghi 'Vị trí ước lượng': {sum(1 for r in final if 'ước lượng' in r['position_quality'].lower())}",
          f"- Bản ghi bị loại: {len(all_dropped)}"]
    reasons = defaultdict(int)
    for d in all_dropped:
        reasons[(d["source"], d["ly_do"])] += 1
    for (src, why), n in reasons.items():
        L.append(f"  - {src}: {n} bản ghi — {why}")
    if offset_notes:
        L += ["", "## Bản ghi trùng hoàn toàn: giữ riêng, dịch tọa độ (theo yêu cầu chủ dự án)", ""] + offset_notes
    L += ["", "## Cặp gộp tự động", ""]
    for p in pairs:
        if p["phan_loai"] == "tu_dong_gop":
            L.append(f"- {p['id_a']} ← {p['id_b']}: {p['ten_a']} · {p['dia_chi_a']} ({p['khoang_cach_m']} m) — {p['quyet_dinh']}")
    (out / "bao_cao_hop_nhat.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
