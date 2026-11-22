"""Đo thời gian tải với bộ dữ liệu đầy đủ (Chrome headless). Chạy máy chủ tĩnh trước.
    python kiem_thu/do_toc_do.py [URL]"""
import asyncio, json, sys
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000/'
PROFILES = {'không giới hạn': None, '4G chậm (9 Mbps, 170 ms)': (9e6 / 8, 170)}

async def run(p, name, prof):
    b = await p.chromium.launch(args=['--no-sandbox'], **({'executable_path': sys.argv[2]} if len(sys.argv) > 2 else {}))
    pg = await b.new_page(viewport={'width': 1366, 'height': 820})
    await pg.route('**/tile.openstreetmap.org/**', lambda r: r.abort())   # bỏ nền OSM để đo phần dữ liệu riêng
    cdp = await pg.context.new_cdp_session(pg)
    if prof:
        await cdp.send('Network.enable')
        await cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': prof[1], 'downloadThroughput': prof[0], 'uploadThroughput': prof[0]})
    t0 = await pg.evaluate('performance.now()') if False else None
    await pg.goto(URL)
    await pg.wait_for_selector('html[data-app-ready]')
    ready = await pg.evaluate("performance.now()")
    res = {}
    for pid in ('TXD0001', 'BC21'):
        t = await pg.evaluate("performance.now()")
        await pg.evaluate(f"location.hash='#{pid}'")
        await pg.wait_for_selector(f'#map[data-detail-station={pid}]')
        tbl = await pg.evaluate("performance.now()")
        await pg.wait_for_function("document.getElementById('layerStatus').textContent === ''")
        img = await pg.evaluate("performance.now()")
        res[pid] = (round(tbl - t), round(img - t))
    t = await pg.evaluate("performance.now()")
    await pg.click("[data-radius='10000']"); await pg.wait_for_function("document.getElementById('layerStatus').textContent === ''")
    r10 = round(await pg.evaluate("performance.now()") - t)
    nodes = await pg.evaluate("document.getElementsByTagName('*').length")
    xfer = await pg.evaluate("Math.round(performance.getEntriesByType('resource').reduce((s, e) => s + (e.transferSize || 0), 0) / 1024)")
    await b.close()
    return {'cấu hình mạng': name, 'mở trang → sẵn sàng (ms)': round(ready), 'chọn TXD0001: bảng / ảnh (ms)': res['TXD0001'],
            'chọn BC21: bảng / ảnh (ms)': res['BC21'], 'BC21 đổi sang 10 km: ảnh (ms)': r10, 'số phần tử DOM': nodes, 'đã tải (KB)': xfer}

async def main():
    async with async_playwright() as p:
        for n, pr in PROFILES.items():
            print(json.dumps(await run(p, n, pr), ensure_ascii=False))
asyncio.run(main())
