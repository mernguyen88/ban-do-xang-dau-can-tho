# Kiểm kê tệp đầu vào

## Raster

- sha256: `f92f71a627e16d15ce874818878b9c260ca4deec30ca3ac2acac0245b31d9303`
- sha256_matches_expected: `True`
- crs: `EPSG:32648`
- res: `[10.0, 10.0]`
- nodata: `0.0`
- dtype: `uint8`
- width: `11723`
- height: `11953`
- bounds: `[524740.0, 1021890.0, 641970.0, 1141420.0]`
- bounds_wgs84: `[105.22523780828128, 9.242231561879231, 106.29659686598538, 10.325590290352617]`
- problems: `[]`
- codes_missing_in_raster: `[]`
- values_not_in_class_table: `{}`

## Nguồn `tram`

- records: `843`
- layers: `['Co_so_xang_dau_Can_Tho']`
- crs: `EPSG:4326`
- geom_types: `{'Point': 843}`
- empty_geometry: `0`
- outside_vietnam: `0`
- outside_raster_extent: `0`
- duplicate_geometry_records: `187`
- wgs84_extent: `[105.277998, 9.273492, 106.250091, 10.311896]`

| Trường | Kiểu | Có giá trị | Duy nhất | Ứng viên ID |
| --- | --- | --- | --- | --- |
| TEN_DIEM | str | 843 | 828 |  |
| VI_TRI | str | 843 | 639 |  |
| TOA_DO | str | 843 | 717 |  |
| GHI_CHU | str | 354 | 1 |  |

## Nguồn `ben_cang`

- records: `73`
- layers: `['bencang']`
- crs: `EPSG:4326`
- geom_types: `{'Point': 73}`
- empty_geometry: `0`
- outside_vietnam: `0`
- outside_raster_extent: `7`
- duplicate_geometry_records: `0`
- wgs84_extent: `[105.496944, 9.520712, 106.54166, 10.321944]`

| Trường | Kiểu | Có giá trị | Duy nhất | Ứng viên ID |
| --- | --- | --- | --- | --- |
| layer | str | 73 | 1 |  |
| name | str | 73 | 61 |  |
| descriptio | str | 41 | 41 |  |
| Toa do X | float64 | 73 | 22 |  |
| Toa do Y | float64 | 73 | 21 |  |
