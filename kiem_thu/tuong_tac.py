# Chạy: python -m http.server 8000 (thư mục gốc) rồi python kiem_thu/tuong_tac.py [URL]
# Cần: pip install playwright && python -m playwright install chromium (hoặc sửa executable_path)
"""Kiểm thử tương tác trên trình duyệt thật (Chrome headless) với dữ liệu web hiện có."""
import asyncio, json, sys, csv, io
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000/'
results = []
def check(name, ok, info=''):
    results.append((name, bool(ok), info)); print(('PASS' if ok else 'FAIL'), name, info)

async def state(pg):
    return await pg.evaluate('''() => ({
      sel: document.getElementById('map').dataset.selectedStation || null,
      det: document.getElementById('map').dataset.detailStation || null,
      name: document.getElementById('locationName').textContent,
      tag: document.getElementById('locationTag').textContent,
      buffers: document.querySelectorAll('.leaflet-boundary-pane path:not(.overlap-hatch)').length,
      images: [...document.querySelectorAll('.leaflet-classified-pane img')].map(i => i.src.split('/').pop()),
      rows: [...document.querySelectorAll('#areaRows tr')].map(r => [...r.children].map(td => td.textContent)),
      chartStation: document.getElementById('chart').dataset.station || null,
      chartVals: [...document.querySelectorAll('#chart .val')].map(t => +t.dataset.value),
      chartLabels: [...document.querySelectorAll('#chart .cat')].map(t => t.textContent),
      bars: [...document.querySelectorAll('#chart .bar')].map(b => b.getAttribute('fill')),
      bodyHidden: document.getElementById('detailBody').hidden,
      status: document.getElementById('detailStatusText').textContent,
      text: document.body.innerText,
    })''')

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--no-sandbox'], **({'executable_path': '/usr/bin/google-chrome'} if __import__('os').path.exists('/usr/bin/google-chrome') else {}))
        ctx = await b.new_context(viewport={'width': 1366, 'height': 820}, accept_downloads=True)
        pg = await ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        # Làm chậm chi tiết XD01 để kiểm tra phản hồi cũ
        delays = {'BC11': 1500}
        async def slow(route):
            name = route.request.url.split('/details/')[1].split('.json')[0]
            await asyncio.sleep(delays.get(name, 0) / 1000)
            try: await route.continue_()
            except Exception: pass
        await pg.route('**/data/details/*.json*', slow)
        await pg.goto(URL); await pg.wait_for_selector('html[data-app-ready]')
        cat = json.loads(open('data/catalog.json', encoding='utf-8').read())
        n = len(cat['points'])
        st = await state(pg)
        check('danh mục hiển thị đúng số điểm từ dữ liệu', f'{n} vị trí' in st['text'], f'{n}')
        check('không có vùng đệm/ảnh khi chưa chọn', st['buffers'] == 0 and not st['images'])

        # Danh sách chỉ vẽ 200 dòng đầu: lọc Bến cảng để thao tác trên danh sách
        await pg.select_option('#kindFilter', 'Bến cảng'); await pg.wait_for_timeout(50)
        # A (chậm) → B nhanh: chỉ còn B
        await pg.click('#stationList [data-station=BC11]')
        await pg.wait_for_timeout(100)
        st = await state(pg)
        check('đang tải: ẩn số liệu, hiện trạng thái tải', st['bodyHidden'] and 'Đang tải' in st['status'])
        await pg.evaluate("document.querySelector('[data-station]') || 0")
        await pg.click('#showList'); await pg.click('#stationList [data-station=BC21]')
        await pg.wait_for_selector('#map[data-detail-station=BC21]')
        await pg.wait_for_timeout(1800)  # chờ quá thời gian phản hồi XD01
        st = await state(pg)
        d2full = json.load(open('data/details/BC21.json', encoding='utf-8')); d2 = dict(d2full); d2.update(d2full['results']['2000'])
        check('đổi nhanh A→B: chỉ còn B', st['sel'] == 'BC21' and st['det'] == 'BC21' and st['buffers'] == 1 and len(st['images']) == 1 and st['images'][0].split('?')[0] == d2['image'].split('/')[-1] and st['name'] == d2['name'], json.dumps({k: st[k] for k in ('sel', 'det', 'buffers', 'images')}))

        # Bảng khớp số gốc (làm tròn 2 chữ số, vi-VN)
        fmt = lambda v: f'{v:,.2f}'.replace(',', '§').replace('.', ',').replace('§', '.')
        exp = [[c['name'], fmt(c['area_ha']), fmt(c['percent'])] for c in d2['classes']]
        check('bảng = số gốc làm tròn', st['rows'] == exp)
        # Biểu đồ
        await pg.click('[data-view=chart]'); await pg.wait_for_timeout(150)
        st = await state(pg)
        check('biểu đồ ha = area_ha gốc, đúng tên và thứ tự', st['chartStation'] == 'BC21' and st['chartVals'] == [c['area_ha'] for c in d2['classes']] and st['chartLabels'] == [c['name'] for c in d2['classes']])
        nonzero = [c['color'] for c in d2['classes'] if c['area_ha'] > 0]
        check('màu thanh = màu bảng mã; lớp 0 không có thanh', st['bars'] == nonzero, f"{len(st['bars'])} thanh")
        zero_lbl = await pg.evaluate("[...document.querySelectorAll('#chart .val')].filter(t=>+t.dataset.value===0).map(t=>t.textContent)")
        check('lớp diện tích 0 có nhãn 0', all(z.startswith('0,00') for z in zero_lbl), str(zero_lbl))
        check('tên Rừng, không có Rừng bổ sung/diện tích thiếu trên giao diện', 'Rừng' in st['chartLabels'] and 'bổ sung' not in st['text'].lower() and 'thiếu' not in st['text'].lower())
        await pg.click('[data-unit=percent]'); await pg.wait_for_timeout(100)
        st = await state(pg)
        check('biểu đồ % = percent gốc (mẫu số toàn vùng đệm)', st['chartVals'] == [c['percent'] for c in d2['classes']] and abs(sum(st['chartVals']) - d2['coverage_percent']) < 1e-9, f"tổng {sum(st['chartVals']):.4f}% (không ép 100%)")
        # Đổi điểm khi đang ở biểu đồ → biểu đồ cập nhật
        await pg.evaluate("location.hash='#BC20'")
        await pg.wait_for_selector('#map[data-detail-station=BC20]'); await pg.wait_for_timeout(100)
        st = await state(pg)
        d7full = json.load(open('data/details/BC20.json', encoding='utf-8')); d7 = d7full['results']['2000']
        check('đổi điểm: biểu đồ cập nhật theo điểm mới', st['chartStation'] == 'BC20' and st['chartVals'] == [c['percent'] for c in d7['classes']])
        await pg.click('[data-unit=ha]')
        # CSV
        async with pg.expect_download() as dl:
            await pg.click('#exportSelected')
        path = await (await dl.value).path()
        rows = list(csv.reader(io.StringIO(open(path, encoding='utf-8-sig').read())))
        check('CSV điểm: 7 dòng lớp × mọi bán kính, số gốc 6 chữ số', len(rows) == 1 + 7 * len(d7full['results']) and [float(r[9]) for r in rows[1:8]] == [round(c['area_ha'], 6) for c in d7['classes']] and 'Rừng' in [r[8] for r in rows])
        # Bỏ chọn
        await pg.click('#clearSelection'); await pg.wait_for_timeout(100)
        st = await state(pg)
        check('bỏ chọn: không còn vùng đệm/ảnh', st['buffers'] == 0 and not st['images'] and st['sel'] is None)
        # Lọc + tìm kiếm (không dấu)
        kinds = [k['name'] for k in cat['kinds']]
        await pg.select_option('#kindFilter', kinds[-1]); await pg.wait_for_timeout(50)
        cnt = await pg.locator('#stationList [data-station]').count()
        check('lọc loại', cnt == cat['kinds'][-1]['count'], f"{kinds[-1]}: {cnt}")
        await pg.select_option('#kindFilter', ''); await pg.fill('#searchInput', 'tra noc'); await pg.wait_for_timeout(300)
        names = await pg.locator('#stationList [data-station]').all_inner_texts()
        check('tìm không dấu "tra noc"', len(names) >= 1 and all('Trà Nóc' in x for x in names), str(len(names)))
        await pg.keyboard.press('Enter'); await pg.wait_for_selector('#map[data-detail-station]')
        check('Enter chọn kết quả đầu', True)
        await pg.fill('#searchInput', ''); await pg.wait_for_timeout(300)
        await pg.click('#overviewButton'); await pg.wait_for_timeout(100)
        st = await state(pg)
        check('toàn cảnh: bỏ chọn và hiện danh sách', st['sel'] is None and st['buffers'] == 0)
        # Bàn phím: Tab tới danh sách rồi Enter
        await pg.select_option('#kindFilter', 'Bến cảng'); await pg.wait_for_timeout(50)
        await pg.focus('#stationList [data-station=BC23]'); await pg.keyboard.press('Enter')
        await pg.wait_for_selector('#map[data-detail-station=BC23]')
        foc = await pg.evaluate('document.activeElement.id')
        check('bàn phím: Enter trên danh sách chọn điểm, focus về tiêu đề', foc == 'locationName')
        # Lỗi tải chi tiết + thử lại
        await pg.unroute('**/data/details/*.json*')
        fail = {'on': True}
        async def maybe_fail(route):
            if fail['on'] and 'BC24' in route.request.url: await route.abort()
            else: await route.continue_()
        await pg.route('**/data/details/*.json*', maybe_fail)
        await pg.click('#showList'); await pg.click('#stationList [data-station=BC24]'); await pg.wait_for_timeout(400)
        st = await state(pg)
        check('lỗi tải chi tiết: báo lỗi, không giữ bảng cũ', st['bodyHidden'] and 'Chưa tải được' in st['status'] and st['buffers'] == 0)
        fail['on'] = False
        await pg.click('#retryDetail'); await pg.wait_for_selector('#map[data-detail-station=BC24]')
        check('thử lại thành công', True)
        # Ảnh lỗi: bảng vẫn dùng được
        await pg.route('**/data/anh/*.png*', lambda r: r.abort())
        await pg.click('#showList'); await pg.click('#stationList [data-station=BC25]')
        await pg.wait_for_selector('#map[data-detail-station=BC25]'); await pg.wait_for_timeout(400)
        st = await state(pg)
        img_msg = await pg.text_content('#imageStatus')
        check('ảnh lỗi: báo lỗi ảnh, bảng/biểu đồ vẫn có', 'Ảnh hiện trạng chưa tải được' in img_msg and not st['bodyHidden'])
        # Mở lại trang với hash + nhớ chế độ biểu đồ
        await pg.goto(URL + '#BC18'); await pg.wait_for_selector('#map[data-detail-station=BC18]')
        st = await state(pg)
        check('mở lại trang theo #BC18, nhớ chế độ biểu đồ', st['sel'] == 'BC18' and st['chartStation'] == 'BC18')
        # Chuyển nhanh liên tục 9 điểm (ảnh bình thường trở lại)
        await pg.unroute('**/data/anh/*.png*')
        seq = ['BC11', 'TXD0001', 'BC21', 'TXD0236', 'BC20', 'TXD0500', 'BC24', 'TXD0800', 'BC25']
        for i in seq:
            await pg.evaluate(f"location.hash='#{i}'")
        await pg.wait_for_selector('#map[data-detail-station=BC25]'); await pg.wait_for_timeout(800)
        st = await state(pg)
        last = json.load(open('data/details/BC25.json', encoding='utf-8'))['results']['2000']
        check('chuyển nhanh 9 điểm: chỉ một vùng đệm, một ảnh, đúng điểm cuối', st['buffers'] == 1 and len(st['images']) == 1 and st['images'][0].split('?')[0] == last['image'].split('/')[-1] and st['chartStation'] == 'BC25')
        # Đổi bán kính 2 → 3 → 5 → 10 km nhanh
        await pg.evaluate("location.hash='#BC21'"); await pg.wait_for_selector('#map[data-detail-station=BC21]')
        full = json.load(open('data/details/BC21.json', encoding='utf-8'))
        for rad in ('3000', '5000', '10000'):
            await pg.click(f"[data-radius='{rad}']")
        await pg.wait_for_selector('#map[data-radius="10000"]'); await pg.wait_for_timeout(400)
        st = await state(pg)
        r10 = full['results']['10000']
        check('đổi bán kính 10 km: một vùng đệm, một ảnh, biểu đồ = số 10 km', st['buffers'] == 1 and len(st['images']) == 1 and st['images'][0].split('?')[0] == r10['image'].split('/')[-1] and st['chartVals'] == [c['area_ha'] for c in r10['classes']] and '31.415,83' in st['text'])
        await pg.goto('about:blank'); await pg.goto(URL + '#BC21/5000'); await pg.wait_for_selector('#map[data-radius="5000"][data-detail-station=BC21]')
        check('tải lại trang theo #BC21/5000', True)
        await pg.evaluate("location.hash='#TXD0002'"); await pg.wait_for_selector('#map[data-detail-station=TXD0002]')
        hid = await pg.evaluate("document.getElementById('radiusPicker').hidden")
        rr = await pg.evaluate("document.getElementById('map').dataset.radius")
        check('điểm thường: chỉ 2 km, ẩn chọn bán kính', hid and rr == '2000')
        await pg.evaluate("location.hash='#BC01'"); await pg.wait_for_selector('#map[data-detail-station=BC01]'); await pg.wait_for_timeout(200)
        st = await state(pg)
        note = await pg.text_content('#resultNote')
        vis = await pg.evaluate("[document.getElementById('tableView').hidden, document.getElementById('chartView').hidden, document.getElementById('exportSelected').hidden]")
        check('điểm ngoài raster: không hiện bảng/biểu đồ số 0, có ghi chú', all(vis) and 'ngoài phạm vi raster' in note and not st['images'])
        est_id = next(p[0] for p in cat['points'] if p[6])
        await pg.evaluate(f"location.hash='#{est_id}'"); await pg.wait_for_selector(f'#map[data-detail-station={est_id}]')
        fl = await pg.text_content('#depotInfo')
        check('vị trí ước lượng hiện trong thuộc tính', 'Ước lượng' in fl, est_id)
        await pg.evaluate("location.hash='#BC21'"); await pg.wait_for_selector('#map[data-detail-station=BC21]')
        check('điểm không ước lượng: không có dòng Vị trí', 'Vị trí' not in (await pg.text_content('#depotInfo')))
        await pg.click('#showList'); await pg.wait_for_timeout(50)
        cnt = await pg.locator("#kindFilter option[value='__depot']").count()
        check('bộ lọc không còn mục kho có dung tích', cnt == 0)
        check('không có lỗi JavaScript', not errs, '; '.join(errs))
        await b.close()
    bad = [r for r in results if not r[1]]
    print(f'{len(results) - len(bad)}/{len(results)} đạt')
    sys.exit(1 if bad else 0)
asyncio.run(main())
