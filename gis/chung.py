"""Hàm dùng chung cho quy trình GIS: đọc cấu hình, đọc lớp điểm, raster,
tính diện tích giao chính xác và xuất ảnh hiển thị."""
from __future__ import annotations

import csv
import hashlib
import math
import re
import tomllib
import unicodedata
from pathlib import Path

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
OUTSIDE = -2_000_000_001   # giá trị đánh dấu ô nằm ngoài phạm vi raster (nội bộ)


# ---------------------------------------------------------------- cấu hình
def load_config(path: str | Path) -> dict:
    path = Path(path)
    cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    base = path.resolve().parent
    cfg["_base"] = base

    def resolve(p):
        if not p:
            return p
        q = Path(p)
        return q if q.is_absolute() else (ROOT / q)
    cfg["raster"]["path"] = resolve(cfg["raster"]["path"])
    cfg["raster"]["class_table"] = resolve(cfg["raster"].get("class_table", "gis/bang_ma_lop.csv"))
    for s in cfg.get("sources", []):
        s["path"] = resolve(s["path"])
    if cfg.get("depots", {}).get("table"):
        cfg["depots"]["table"] = resolve(cfg["depots"]["table"])
    out = cfg.setdefault("output", {})
    out["work_dir"] = resolve(out.get("work_dir", "gis/ket_qua"))
    out["web_dir"] = resolve(out.get("web_dir", "data"))
    d = cfg.setdefault("dedupe", {})
    if d.get("decisions"):
        d["decisions"] = resolve(d["decisions"])
    return cfg


def sha256(path: Path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while b := fh.read(chunk):
            h.update(b)
    return h.hexdigest()


def read_class_table(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as fh:
        rows = [{"code": int(r["code"]), "name": r["name"].strip(), "color": r["color"].strip().upper()} for r in csv.DictReader(fh)]
    for r in rows:
        if "bổ sung" in r["name"].lower():
            raise ValueError(f"Bảng mã còn tên '{r['name']}'; dùng tên 'Rừng' cho mã 7.")
    return rows


# ---------------------------------------------------------------- chuỗi
def fold(text) -> str:
    """Chuẩn hóa tên để so khớp: bỏ dấu, đ→d, chữ thường, gộp khoảng trắng."""
    s = unicodedata.normalize("NFD", str(text or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").replace("đ", "d").replace("Đ", "d").lower()
    s = re.sub(r"[^0-9a-z]+", " ", s)
    return " ".join(s.split())


def web_id(prefix: str, source_id) -> str:
    raw = str(source_id).strip()
    if re.fullmatch(r"\d+(\.0+)?", raw):
        raw = str(int(float(raw))).zfill(4)
    raw = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-")
    if not raw:
        raise ValueError("ID nguồn rỗng")
    return f"{prefix}{raw}"[:64]


# ---------------------------------------------------------------- vector
def read_vector(path: Path, layer: str | None = None):
    import geopandas as gpd
    import pyogrio
    p = str(path)
    if p.lower().endswith(".zip"):
        p = f"zip://{p}"
    layers = [l[0] for l in pyogrio.list_layers(p)]
    if layer:
        if layer not in layers:
            raise ValueError(f"{path.name}: không có lớp {layer!r}; các lớp: {layers}")
    elif len(layers) > 1:
        raise ValueError(f"{path.name}: có nhiều lớp {layers}; ghi rõ `layer` trong cấu hình.")
    gdf = gpd.read_file(p, layer=layer or None, engine="pyogrio")
    return gdf, layers


def zip_members(path: Path) -> list[str]:
    import zipfile
    if not str(path).lower().endswith(".zip"):
        return []
    with zipfile.ZipFile(path) as z:
        return z.namelist()


def transformer(src_crs, dst_crs) -> Transformer:
    return Transformer.from_crs(CRS.from_user_input(src_crs), CRS.from_user_input(dst_crs), always_xy=True)


# ---------------------------------------------------------------- raster
def raster_info(src) -> dict:
    t = src.transform
    crs = src.crs
    info = {
        "crs": crs.to_string() if crs else None,
        "epsg": crs.to_epsg() if crs else None,
        "crs_is_projected": bool(crs and crs.is_projected),
        "linear_units": crs.linear_units if crs else None,
        "width": src.width, "height": src.height, "count": src.count,
        "dtype": src.dtypes[0], "nodata": src.nodata,
        "res": [abs(t.a), abs(t.e)], "rotation": [t.b, t.d],
        "bounds": list(src.bounds),
    }
    return info


def check_raster(info: dict, calc_crs: str):
    problems = []
    if not info["crs"]:
        problems.append("raster không có CRS")
    elif not info["crs_is_projected"] or (info["linear_units"] or "").lower() not in ("metre", "meter", "m"):
        problems.append(f"raster CRS {info['crs']} không phải hệ chiếu đơn vị mét")
    if info["rotation"] != [0.0, 0.0]:
        problems.append("raster có góc xoay; quy trình không hỗ trợ")
    if not np.issubdtype(np.dtype(info["dtype"]), np.integer):
        problems.append(f"raster kiểu {info['dtype']}, không phải số nguyên phân loại")
    if info["count"] != 1:
        problems.append(f"raster có {info['count']} băng; cần 1 băng phân loại")
    if calc_crs and info["crs"] and CRS.from_user_input(calc_crs) != CRS.from_user_input(info["crs"]):
        problems.append(f"CRS tính toán {calc_crs} khác CRS raster {info['crs']}; cấu hình calc_crs = CRS raster")
    return problems


def raster_value_counts(src, max_blocks=None) -> dict:
    """Đếm giá trị pixel theo khối (không nạp toàn raster vào bộ nhớ)."""
    counts: dict[int, int] = {}
    for i, (_, win) in enumerate(src.block_windows(1)):
        if max_blocks and i >= max_blocks:
            break
        a = src.read(1, window=win)
        v, c = np.unique(a, return_counts=True)
        for vv, cc in zip(v.tolist(), c.tolist()):
            counts[int(vv)] = counts.get(int(vv), 0) + int(cc)
    return dict(sorted(counts.items()))


def make_buffer(x: float, y: float, radius: float, quad_segs: int):
    return Point(x, y).buffer(radius, quad_segs=quad_segs)


def read_cells(src, geom):
    """Đọc các ô raster phủ bbox của `geom` (lưới căn theo raster).
    Ô ngoài phạm vi raster mang giá trị OUTSIDE. Trả về (mảng int64, r0, c0)."""
    t = src.transform
    minx, miny, maxx, maxy = geom.bounds
    c0 = math.floor((minx - t.c) / t.a)
    c1 = math.ceil((maxx - t.c) / t.a)
    r0 = math.floor((maxy - t.f) / t.e)
    r1 = math.ceil((miny - t.f) / t.e)
    arr = np.full((r1 - r0, c1 - c0), OUTSIDE, dtype=np.int64)
    rr0, rr1 = max(r0, 0), min(r1, src.height)
    cc0, cc1 = max(c0, 0), min(c1, src.width)
    if rr0 < rr1 and cc0 < cc1:
        from rasterio.windows import Window
        data = src.read(1, window=Window(cc0, rr0, cc1 - cc0, rr1 - rr0))
        arr[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0] = data
    return arr, r0, c0


def cell_fractions(transform, r0, c0, shape, geom):
    """Diện tích giao (m²) giữa từng ô raster và `geom`.

    Ô nằm trọn trong vùng đệm = diện tích ô; ô biên = diện tích phần giao thực
    tế (shapely.intersection). Với đa giác lồi (vùng đệm tròn 1.440 cạnh), một ô
    nằm trọn trong khi cả 4 góc nằm trong; chỉ các ô còn lại gần biên mới cần
    tính giao. Đa giác không lồi dùng cách kiểm tra đầy đủ từng ô."""
    rows, cols = shape
    a, e = transform.a, transform.e
    xs = transform.c + (c0 + np.arange(cols + 1)) * a          # cạnh ô
    ys = transform.f + (r0 + np.arange(rows + 1)) * e
    area = np.zeros(shape, dtype=np.float64)
    cell = abs(a * e)
    shapely.prepare(geom)
    convex = abs(geom.convex_hull.area - geom.area) <= 1e-9 * geom.area
    if convex:
        CX, CY = np.meshgrid(xs, ys)
        corner_in = shapely.contains_xy(geom, CX, CY)
        full = corner_in[:-1, :-1] & corner_in[:-1, 1:] & corner_in[1:, :-1] & corner_in[1:, 1:]
        # ứng viên giao một phần: ô không trọn mà bbox của ô chạm bbox hình (mọi ô trong cửa sổ),
        # lọc bằng khoảng cách tâm ô → hình ≤ nửa đường chéo ô
        mx = (xs[:-1] + xs[1:]) / 2; my = (ys[:-1] + ys[1:]) / 2
        MX, MY = np.meshgrid(mx, my)
        half_diag = 0.5 * np.hypot(a, e)
        cand = ~full
        idx = np.nonzero(cand)
        centers = shapely.points(MX[idx], MY[idx])
        near = shapely.dwithin(geom, centers, half_diag + 1e-6)
        pr, pc = idx[0][near], idx[1][near]
        area[full] = cell
    else:
        X0, Y0 = np.meshgrid(xs[:-1], ys[:-1])
        boxes = shapely.box(np.minimum(X0, X0 + a), np.minimum(Y0, Y0 + e), np.maximum(X0, X0 + a), np.maximum(Y0, Y0 + e))
        full = shapely.contains(geom, boxes)
        area[full] = cell
        pr, pc = np.nonzero(shapely.intersects(geom, boxes) & ~full)
    if len(pr):
        x0 = xs[pc]; x1 = x0 + a; y0 = ys[pr]; y1 = y0 + e
        boxes = shapely.box(np.minimum(x0, x1), np.minimum(y0, y1), np.maximum(x0, x1), np.maximum(y0, y1))
        area[pr, pc] = shapely.area(shapely.intersection(boxes, geom))
    return area


def class_areas(src, geom, codes: list[int], nodata) -> dict:
    """Diện tích m² theo lớp + NoData + ngoài phạm vi + mã chưa xác định."""
    arr, r0, c0 = read_cells(src, geom)
    area = cell_fractions(src.transform, r0, c0, arr.shape, geom)
    if nodata is not None and float(nodata).is_integer() and int(nodata) in codes:
        raise ValueError("NoData trùng một mã lớp; kiểm tra lại metadata raster.")
    out = {"classes": {}, "nodata": 0.0, "outside": 0.0, "unknown": 0.0, "unknown_codes": {}}
    known = np.zeros(arr.shape, bool)
    for c in codes:
        m = arr == c
        known |= m
        out["classes"][c] = float(area[m].sum())
    m_out = arr == OUTSIDE
    out["outside"] = float(area[m_out].sum())
    m_nd = (arr == nodata) if nodata is not None else np.zeros(arr.shape, bool)
    out["nodata"] = float(area[m_nd & ~known].sum())
    m_unk = ~(known | m_out | m_nd) & (area > 0)
    out["unknown"] = float(area[m_unk].sum())
    if m_unk.any():
        v, idx = np.unique(arr[m_unk], return_inverse=True)
        sums = np.bincount(idx, weights=area[m_unk])
        out["unknown_codes"] = {int(k): float(s) for k, s in zip(v, sums)}
    out["cells_total_m2"] = float(area.sum())
    return out


# ---------------------------------------------------------------- ảnh hiển thị
def render_png(src, geom, classes: list[dict], out_png: Path, size: int = 1024):
    """Ảnh RGBA cho Leaflet: chiếu sang EPSG:3857 bằng láng giềng gần nhất,
    pixel ngoài vùng đệm, NoData, ngoài phạm vi và mã lạ trong suốt.
    Trả về image_bounds [[south, west], [north, east]] WGS84."""
    import rasterio
    from rasterio.features import geometry_mask
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject
    from PIL import Image

    arr, r0, c0 = read_cells(src, geom)
    t = src.transform
    src_tr = rasterio.Affine(t.a, 0, t.c + c0 * t.a, 0, t.e, t.f + r0 * t.e)
    to3857 = transformer(src.crs, "EPSG:3857")
    g3857 = shapely.transform(geom, lambda xy: np.column_stack(to3857.transform(xy[:, 0], xy[:, 1])))
    minx, miny, maxx, maxy = g3857.bounds
    side = max(maxx - minx, maxy - miny)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    minx, maxx, miny, maxy = cx - side / 2, cx + side / 2, cy - side / 2, cy + side / 2
    dst_tr = from_bounds(minx, miny, maxx, maxy, size, size)
    dst = np.full((size, size), -1, dtype=np.int32)
    srcv = arr.astype(np.int64)
    srcv[(srcv == OUTSIDE)] = -1
    if src.nodata is not None:
        srcv[srcv == src.nodata] = -1
    reproject(srcv.astype(np.int32), dst, src_transform=src_tr, src_crs=src.crs, src_nodata=-1,
              dst_transform=dst_tr, dst_crs="EPSG:3857", dst_nodata=-1, resampling=Resampling.nearest)
    inside = ~geometry_mask([g3857], out_shape=(size, size), transform=dst_tr, all_touched=False)
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    for c in classes:
        m = (dst == c["code"]) & inside
        h = c["color"].lstrip("#")
        rgba[m] = [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255]
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    tow = transformer("EPSG:3857", "EPSG:4326")
    w, s = tow.transform(minx, miny)
    e, n = tow.transform(maxx, maxy)
    return [[s, w], [n, e]]


def geom_to_wgs84_geojson(geom, src_crs, ndigits=7):
    tr = transformer(src_crs, "EPSG:4326")
    g = shapely.transform(geom, lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1])))
    coords = [[round(x, ndigits), round(y, ndigits)] for x, y in g.exterior.coords]
    return {"type": "Polygon", "coordinates": [coords]}
