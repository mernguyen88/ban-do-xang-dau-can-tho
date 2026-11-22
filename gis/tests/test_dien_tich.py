"""Kiểm thử thuật toán diện tích bằng raster TỔNG HỢP tạo tạm (không phải dữ liệu dự án).

    python -m pytest gis/tests -q      (hoặc: python gis/tests/test_dien_tich.py)
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import rasterio
import shapely
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chung  # noqa: E402

X0, Y0, RES = 500000.0, 1100000.0, 10.0


def make_raster(arr, nodata=0):
    tmp = Path(tempfile.mkdtemp()) / "t.tif"
    with rasterio.open(tmp, "w", driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1, dtype="uint8",
                       crs="EPSG:32648", transform=from_origin(X0, Y0, RES, RES), nodata=nodata) as dst:
        dst.write(arr.astype("uint8"), 1)
    return rasterio.open(tmp)


def brute(src, geom):
    arr, r0, c0 = chung.read_cells(src, geom)
    t = src.transform
    xs = t.c + (c0 + np.arange(arr.shape[1])) * t.a
    ys = t.f + (r0 + np.arange(arr.shape[0])) * t.e
    X, Y = np.meshgrid(xs, ys)
    return shapely.area(shapely.intersection(shapely.box(X, Y + t.e, X + t.a, Y), geom))


def test_uniform_full_area():
    src = make_raster(np.full((600, 600), 1))
    g = chung.make_buffer(X0 + 3000.3, Y0 - 3000.7, 2000, 360)
    a = chung.class_areas(src, g, list(range(1, 8)), 0)
    assert abs(a["classes"][1] - g.area) < 1e-6
    assert a["nodata"] == a["outside"] == a["unknown"] == 0


def test_fast_equals_brute_random():
    rng = np.random.default_rng(1)
    src = make_raster(rng.integers(0, 9, (700, 700)))   # gồm NoData 0 và mã lạ 8
    for r in (2000, 3000):
        g = chung.make_buffer(X0 + 3500.37, Y0 - 3499.81, r, 360)
        arr, r0, c0 = chung.read_cells(src, g)
        fast = chung.cell_fractions(src.transform, r0, c0, arr.shape, g)
        assert np.abs(fast - brute(src, g)).max() < 1e-6
        a = chung.class_areas(src, g, list(range(1, 8)), 0)
        total = sum(a["classes"].values()) + a["nodata"] + a["outside"] + a["unknown"]
        assert abs(total - g.area) < 1e-6 * g.area
        assert a["unknown"] > 0 and a["nodata"] > 0


def test_half_split():
    arr = np.full((600, 600), 2); arr[:, 300:] = 3
    src = make_raster(arr)
    g = chung.make_buffer(X0 + 3000, Y0 - 3000, 2000, 360)   # tâm nằm đúng ranh giới cột
    a = chung.class_areas(src, g, list(range(1, 8)), 0)
    assert abs(a["classes"][2] - a["classes"][3]) < 1e-6
    assert abs(a["classes"][2] + a["classes"][3] - g.area) < 1e-6


def test_outside_raster_edge():
    src = make_raster(np.full((300, 300), 5))
    g = chung.make_buffer(X0 + 100, Y0 - 1500, 2000, 360)   # một phần nằm ngoài mép trái
    a = chung.class_areas(src, g, list(range(1, 8)), 0)
    assert a["outside"] > 0
    assert abs(a["classes"][5] + a["outside"] - g.area) < 1e-6 * g.area


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
