'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const num = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const tickNum = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 2 });
  const fmt = n => num.format(n);
  const LIST_PAGE = 200;         // số dòng danh sách hiển thị mỗi lần
  const els = { details: $('detailsPanel'), empty: $('emptyPanel'), search: $('searchInput'), kind: $('kindFilter') };
  const store = (() => { try { return window.localStorage; } catch { return null; } })();
  const remember = (k, v) => { try { store?.setItem(k, v); } catch { /* bỏ qua */ } };
  const recall = k => { try { return store?.getItem(k); } catch { return null; } };

  let catalog, points = [], byId = new Map(), map, markerLayer, lastSel = null;
  let filtered = [], listShown = 0;
  let selected = null;           // điểm (danh mục) đang chọn
  let detail = null;             // chi tiết đã tải của điểm đang chọn
  let image = null, buffer = null, controller = null, requestSeq = 0;
  let radius = 2000;             // bán kính đang xem (m)
  let view = recall('ctu-map-view') === 'chart' ? 'chart' : 'table';
  let unit = recall('ctu-map-unit') === 'percent' ? 'percent' : 'ha';
  const cache = new Map();       // id → Promise<chi tiết>
  const markers = new Map();
  const dialog = $('methodDialog');

  $('mobileResults').addEventListener('click', () => document.querySelector('.results-panel').scrollIntoView({ behavior: 'auto', block: 'start' }));
  $('methodButton').addEventListener('click', () => dialog.showModal());
  $('closeDialog').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) { const r = dialog.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close(); } });

  const escapeHTML = text => String(text ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fold = text => String(text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'd').toLowerCase();
  const km = r => `${tickNum.format(r / 1000)} km`;
  const cap = n => `${new Intl.NumberFormat('vi-VN').format(n)} m³`;
  const result = () => detail?.results?.[String(radius)] || null;
  const pad = i => String(i).padStart(String(points.length).length < 2 ? 2 : String(points.length).length, '0');

  /* ---------- Danh sách, tìm kiếm, lọc ---------- */
  function applyFilter() {
    const q = fold(els.search.value.trim());
    const kind = els.kind.value;
    filtered = points.filter(p => (!kind || (kind === '__depot' ? p.depot > 0 : kind === '__estimated' ? p.estimated : p.kind === kind)) && (!q || p.search.includes(q)));
    listShown = 0;
    $('stationList').innerHTML = '';
    renderMore();
    const total = points.length;
    $('stationCount').textContent = filtered.length === total ? `${total} vị trí` : `${filtered.length} / ${total} vị trí`;
    $('listNote').textContent = filtered.length ? 'Chọn cơ sở trên bản đồ hoặc trong danh sách.' : 'Không có cơ sở phù hợp với từ khóa hoặc loại đã chọn.';
    updateMarkers();
  }
  function renderMore() {
    const slice = filtered.slice(listShown, listShown + LIST_PAGE);
    $('stationList').insertAdjacentHTML('beforeend', slice.map(p => {
      const extra = [p.id, p.kind, p.address].filter(Boolean).map(escapeHTML).join(' · ');
      const current = selected?.id === p.id ? ' aria-current="true"' : '';
      const tags = (p.depot ? `<em class="tag tag-depot">Kho ${cap(p.depot)}</em>` : '')
        + (p.status === 'outside' ? '<em class="tag tag-warn">Ngoài phạm vi raster</em>' : '');
      return `<button type="button" data-station="${escapeHTML(p.id)}"${current}><span>${pad(p.n)}</span><span>${escapeHTML(p.name)}<small>${extra}</small>${tags ? `<span class="tags">${tags}</span>` : ''}</span></button>`;
    }).join(''));
    listShown += slice.length;
    const rest = filtered.length - listShown;
    $('moreStations').hidden = rest <= 0;
    $('moreStations').textContent = `Hiện thêm ${Math.min(rest, LIST_PAGE)} vị trí (còn ${rest})`;
  }
  function showList() {
    els.details.hidden = true; els.empty.hidden = false;
    const back = $('backToSelected');
    back.hidden = !selected;
    if (selected) back.textContent = `← Quay lại ${selected.name}`;
  }
  function showDetailsPanel() { els.empty.hidden = true; els.details.hidden = false; $('backToSelected').hidden = true; }

  /* ---------- Điểm trên bản đồ ---------- */
  function updateMarkers() {
    const visible = new Set(filtered.map(p => p.id));
    for (const [id, m] of markers) {
      const on = visible.has(id) || selected?.id === id;
      if (on && !markerLayer.hasLayer(m)) markerLayer.addLayer(m);
      if (!on && markerLayer.hasLayer(m)) markerLayer.removeLayer(m);
    }
  }
  const ICON_TRAM = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect x="1" y="1" width="22" height="22" rx="5" fill="#1c57a5" stroke="#fff" stroke-width="1.6"/><rect x="5.5" y="5" width="8" height="14" rx="1.3" fill="#fff"/><rect x="7.2" y="7" width="4.6" height="3.6" fill="#1c57a5"/><path d="M13.5 9.5h1.6c.7 0 1.2.5 1.2 1.2v5c0 .7.5 1.2 1.2 1.2s1.2-.5 1.2-1.2V9.2L16.8 7" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>');
  const ICON_PORT = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#0a86b8" stroke="#fff" stroke-width="1.6"/><circle cx="12" cy="6.6" r="1.8" fill="none" stroke="#fff" stroke-width="1.6"/><path d="M12 8.4v10M8.6 11.2h6.8M6.2 13.2a5.8 5.8 0 0 0 11.6 0" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></svg>');
  const iconFor = p => p.kind === 'Bến cảng'
    ? L.divIcon({ className: 'pt pt-port', iconSize: [24, 24], iconAnchor: [12, 12], html: '' })
    : L.divIcon({ className: 'pt pt-tram', iconSize: [19, 19], iconAnchor: [9.5, 9.5], html: '' });
  function buildMarkers() {
    document.documentElement.style.setProperty('--icon-tram', `url("${ICON_TRAM}")`);
    document.documentElement.style.setProperty('--icon-port', `url("${ICON_PORT}")`);
    markerLayer = L.layerGroup().addTo(map);
    for (const p of points) {
      const m = L.marker([p.lat, p.lon], { icon: iconFor(p), keyboard: false, title: '', riseOnHover: true, zIndexOffset: p.kind === 'Bến cảng' ? 200 : 0 });
      m.bindTooltip(`${escapeHTML(p.id)} · ${escapeHTML(p.name)}`, { direction: 'top', offset: [0, -11] });
      m.on('click', () => choose(p.id));
      markers.set(p.id, m); markerLayer.addLayer(m);
    }
    map.getContainer().dataset.markerMode = 'icons';
    $('kindLegend').innerHTML = catalog.kinds.map(k => `<div><span class="pt-legend ${k.name === 'Bến cảng' ? 'pt-port' : 'pt-tram'}"></span>${escapeHTML(k.name)}</div>`).join('')
      + '<div><span class="hatch-legend"></span>Chồng lấn với vùng đệm 2 km lân cận</div>';
    $('kindLegend').hidden = false;
  }
  function highlightMarker() {
    const id = selected?.id;
    if (lastSel && lastSel !== id) { const m = markers.get(lastSel); m?.getElement()?.classList.remove('is-selected'); m?.setZIndexOffset(byId.get(lastSel)?.kind === 'Bến cảng' ? 200 : 0); }
    if (id) { const m = markers.get(id); m?.setZIndexOffset(1000); m?.getElement()?.classList.add('is-selected'); }
    lastSel = id || null;
  }

  /* ---------- Vùng chồng lấn với vùng đệm 2 km lân cận (chỉ hiển thị) ---------- */
  let overlapLayer = null;
  const NEIGHBOR_R = 2000, SEG = 128;
  function circlePoly(cx, cy, r) { const out = []; for (let i = 0; i < SEG; i++) { const t = 2 * Math.PI * i / SEG; out.push([cx + r * Math.cos(t), cy + r * Math.sin(t)]); } return out; }
  function clip(subject, clipPoly) {          // Sutherland–Hodgman, đa giác lồi ngược chiều kim đồng hồ
    let out = subject;
    for (let i = 0; i < clipPoly.length && out.length; i++) {
      const [ax, ay] = clipPoly[i], [bx, by] = clipPoly[(i + 1) % clipPoly.length];
      const inside = ([px, py]) => (bx - ax) * (py - ay) - (by - ay) * (px - ax) >= 0;
      const inter = ([px, py], [qx, qy]) => { const d1 = (bx - ax) * (py - ay) - (by - ay) * (px - ax), d2 = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax); const t = d1 / (d1 - d2); return [px + t * (qx - px), py + t * (qy - py)]; };
      const input = out; out = [];
      for (let j = 0; j < input.length; j++) {
        const P = input[j], Q = input[(j + 1) % input.length];
        if (inside(Q)) { if (!inside(P)) out.push(inter(P, Q)); out.push(Q); } else if (inside(P)) out.push(inter(P, Q));
      }
    }
    return out;
  }
  function drawOverlaps(p, r) {
    if (overlapLayer) { overlapLayer.remove(); overlapLayer = null; }
    const kx = 111320 * Math.cos(p.lat * Math.PI / 180), ky = 110574;
    const toXY = q => [(q.lon - p.lon) * kx, (q.lat - p.lat) * ky];
    const toLL = ([x, y]) => [p.lat + y / ky, p.lon + x / kx];
    const self = circlePoly(0, 0, r);
    const lenses = []; let n = 0;
    for (const q of points) {
      if (q.id === p.id) continue;
      const [x, y] = toXY(q);
      if (Math.hypot(x, y) >= r + NEIGHBOR_R) continue;
      const lens = clip(circlePoly(x, y, NEIGHBOR_R), self);
      if (lens.length > 2) { lenses.push(lens.map(toLL)); n++; }
    }
    if (lenses.length) overlapLayer = L.polygon(lenses, { pane: 'boundary', interactive: false, className: 'overlap-hatch', weight: 0.7, color: '#1c57a5', opacity: 0.35, fillOpacity: 1 }).addTo(map);
    return n;
  }

  /* ---------- Chọn điểm ---------- */
  function clearLayers() {
    if (image) { image.remove(); image = null; }
    if (buffer) { buffer.remove(); buffer = null; }
    if (overlapLayer) { overlapLayer.remove(); overlapLayer = null; }
  }
  function setHash(id) {
    const h = id ? `#${encodeURIComponent(id)}${radius !== 2000 ? '/' + radius : ''}` : location.pathname + location.search;
    try { history.replaceState(null, '', h); } catch { /* bỏ qua */ }
  }
  function parseHash() {
    const [id, r] = decodeURIComponent(location.hash.slice(1)).split('/');
    return { id, r: Number(r) || 0 };
  }
  function clearSelection() {
    controller?.abort(); requestSeq++;
    clearLayers(); selected = null; detail = null;
    $('radiusLabel').textContent = '2.000 m';
    $('mobileResults').hidden = true; $('layerControls').hidden = true; $('mapHint').hidden = false;
    $('stationList').querySelectorAll('[aria-current]').forEach(b => b.removeAttribute('aria-current'));
    highlightMarker(); updateMarkers(); showList(); setHash('');
    map.getContainer().removeAttribute('data-selected-station');
    map.getContainer().removeAttribute('data-detail-station');
  }
  function overview() {
    clearSelection();
    const list = filtered.length ? filtered : points;
    if (list.length === 1) map.setView([list[0].lat, list[0].lon], 14, { animate: false });
    else map.fitBounds(L.latLngBounds(list.map(p => [p.lat, p.lon])).pad(.18), { animate: false, maxZoom: 13 });
  }
  function detailUrl(id) { return `data/details/${encodeURIComponent(id)}.json?v=${catalog.version}`; }
  function loadDetail(id, signal) {
    if (cache.has(id)) return cache.get(id);
    const job = fetch(detailUrl(id), { signal }).then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    }).then(d => {
      if (d.id !== id) throw new Error('Tệp chi tiết không khớp mã vị trí.');
      return d;
    });
    cache.set(id, job);
    job.catch(() => cache.delete(id));   // lỗi hoặc hủy: lần sau tải lại
    return job;
  }
  function setStatus(text, retry = false) {
    $('detailStatus').hidden = !text; $('detailStatusText').textContent = text || '';
    $('retryDetail').hidden = !retry;
  }
  async function choose(id, { fit = true, focus = false, r = 0 } = {}) {
    const p = byId.get(id);
    if (!p) return;
    if (r) radius = r;
    controller?.abort();
    controller = new AbortController();
    const seq = ++requestSeq;
    clearLayers(); selected = p; detail = null;
    // Hiển thị ngay thông tin danh mục; số liệu cũ bị ẩn cho tới khi chi tiết mới về.
    showDetailsPanel();
    $('detailBody').hidden = true; setStatus('Đang tải số liệu…');
    $('mobileResults').hidden = false; $('mapHint').hidden = true; $('layerControls').hidden = true;
    $('locationTag').textContent = `${p.id} · ${p.kind}`;
    $('locationName').textContent = p.name;
    $('coordinates').textContent = `${p.lat.toFixed(6)}° N · ${p.lon.toFixed(6)}° E${p.address ? ' · ' + p.address : ''}`;
    $('flagNotes').innerHTML = ''; $('depotInfo').hidden = true; $('radiusPicker').hidden = true;
    $('stationList').querySelectorAll('[data-station]').forEach(b => b.dataset.station === id ? b.setAttribute('aria-current', 'true') : b.removeAttribute('aria-current'));
    const mapEl = map.getContainer();
    mapEl.setAttribute('data-selected-station', id); mapEl.removeAttribute('data-detail-station');
    highlightMarker(); updateMarkers(); setHash(id);
    if (focus) $('locationName').focus({ preventScroll: true });
    if (fit) map.setView([p.lat, p.lon], Math.max(map.getZoom(), 13), { animate: false });
    let d;
    try {
      d = await loadDetail(id, controller.signal);
    } catch (error) {
      if (seq !== requestSeq) return;               // đã đổi sang điểm khác
      setStatus('Chưa tải được số liệu của vị trí này. Kiểm tra kết nối rồi thử lại.', true);
      console.error(error);
      return;
    }
    if (seq !== requestSeq || selected?.id !== id) return;   // phản hồi cũ: bỏ qua
    detail = d; setStatus('');
    if (!d.results[String(radius)]) radius = Math.min(...Object.keys(d.results).map(Number));
    renderPointInfo(d);
    showResult(fit);
    mapEl.setAttribute('data-detail-station', id);
  }
  function showResult(fit = true) {
    const d = detail, r = result();
    if (!d || !r) return;
    clearLayers();
    $('radiusLabel').textContent = `${new Intl.NumberFormat('vi-VN').format(radius)} m`;
    document.querySelectorAll('[data-radius]').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.radius) === radius)));
    buffer = L.geoJSON(r.buffer, { pane: 'boundary', interactive: false, style: { color: '#1c57a5', weight: 2, opacity: 1, fillOpacity: 0 } }).addTo(map);
    if (r.image) addImage(d, r); else { $('imageStatus').textContent = ''; $('layerStatus').textContent = ''; }
    const nOver = drawOverlaps(selected, radius);
    $('overlapRow').innerHTML = `<dt>Chồng lấn</dt><dd>${nOver ? `${nOver} vùng đệm 2 km lân cận (tô sọc trên bản đồ)` : 'Không có'}</dd>`;
    $('layerControls').hidden = !r.image;
    renderDetail(d, r);
    map.getContainer().setAttribute('data-radius', String(radius));
    setHash(d.id);
    if (fit) map.fitBounds(buffer.getBounds(), { padding: [30, 30], animate: false, maxZoom: 16 });
  }
  function renderPointInfo(d) {
    $('flagNotes').innerHTML = '';
    const k = d.depot, rows = [];
    if (k) {
      rows.push(`<div><dt>Kho (Phụ lục 2)</dt><dd>${escapeHTML(k.ten_kho)}</dd></div>`,
        `<div><dt>Dung tích</dt><dd>${k.dung_tich_m3 != null ? cap(k.dung_tich_m3) : '—'}</dd></div>`,
        `<div><dt>Loại kho</dt><dd>${escapeHTML(k.loai_kho)}</dd></div>`,
        `<div><dt>Tình trạng</dt><dd>${escapeHTML(k.tinh_trang)}</dd></div>`);
    }
    const est = (d.position_quality || '').toLowerCase().includes('ước lượng');
    if (est) rows.push('<div><dt>Vị trí</dt><dd>Ước lượng</dd></div>');
    rows.push('<div id="overlapRow"></div>');
    $('depotInfo').innerHTML = rows.join('');
    $('depotInfo').hidden = false;
    const radii = Object.keys(d.results).map(Number).sort((a, b) => a - b);
    $('radiusPicker').hidden = radii.length < 2;
    $('radiusButtons').innerHTML = radii.map(r => `<button type="button" data-radius="${r}" aria-pressed="${r === radius}">${km(r)}</button>`).join('');
  }
  function addImage(d, r) {
    const current = L.imageOverlay(`${r.image}?v=${catalog.version}`, r.image_bounds, { pane: 'classified', opacity: Number($('opacity').value) / 100, interactive: false, alt: `Hiện trạng sử dụng đất trong bán kính ${km(radius)} quanh ${d.name}` });
    image = current;
    $('imageStatus').textContent = ''; $('layerStatus').textContent = 'Đang tải lớp hiện trạng…';
    current.on('load', () => { if (image === current) $('layerStatus').textContent = ''; });
    current.on('error', () => {
      if (image !== current) return;
      $('layerStatus').textContent = 'Chưa tải được ảnh hiện trạng.';
      $('imageStatus').textContent = 'Ảnh hiện trạng chưa tải được; bảng và biểu đồ vẫn dùng số liệu tính từ raster gốc.';
    });
    current.addTo(map);
    if (!$('showLanduse').checked) current.remove();
  }
  function renderDetail(d, r) {
    $('detailBody').hidden = false;
    const outside = r.valid_ha === 0 && r.qc?.outside_ha > 0;
    const partial = !outside && r.qc?.outside_ha > 1e-6;
    $('bufferLabel').textContent = `Diện tích vùng đệm ${km(radius)}`;
    $('totalArea').textContent = fmt(r.area_ha);
    $('tableCaption').textContent = `Diện tích và tỷ lệ từng loại đất trong vùng đệm ${km(radius)}`;
    document.querySelector('.table-heading').hidden = outside;
    $('tableView').hidden = outside || view !== 'table'; $('chartView').hidden = outside || view !== 'chart';
    $('exportSelected').hidden = outside;
    $('resultNote').textContent = outside
      ? 'Vùng đệm nằm ngoài phạm vi raster hiện trạng 2025 nên không tính được diện tích các loại đất.'
      : `Tỷ lệ tính trên diện tích toàn vùng đệm ${km(radius)}. Số liệu làm tròn đến 2 chữ số thập phân.${partial ? ' Một phần vùng đệm nằm ngoài phạm vi raster hiện trạng.' : ''}`;
    $('resultNote').classList.toggle('note-strong', outside || partial);
    if (outside) return;
    $('validArea').textContent = fmt(r.valid_ha);
    $('coveragePercent').textContent = fmt(r.coverage_percent);
    $('areaRows').innerHTML = r.classes.map(c => `<tr data-class="${c.code}"><td><span class="class-name"><span class="swatch" style="background:${c.color}"></span>${escapeHTML(c.name)}</span></td><td>${fmt(c.area_ha)}</td><td>${fmt(c.percent)}</td></tr>`).join('');
    renderView();
  }

  /* ---------- Bảng / Biểu đồ ---------- */
  function renderView() {
    document.querySelectorAll('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
    document.querySelectorAll('[data-unit]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.unit === unit)));
    const r = result();
    const outside = r && r.valid_ha === 0 && r.qc?.outside_ha > 0;
    $('tableView').hidden = outside || view !== 'table';
    $('chartView').hidden = outside || view !== 'chart';
    if (view === 'chart' && r && !outside) renderChart();
  }
  function niceStep(max, count) {
    const raw = max / Math.max(count, 1);
    const mag = 10 ** Math.floor(Math.log10(raw));
    const r = raw / mag;
    return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 2.5 ? 2.5 : r <= 5 ? 5 : 10) * mag;
  }
  let measureCtx;
  function textWidth(text, font) {
    measureCtx ??= document.createElement('canvas').getContext('2d');
    measureCtx.font = font; return measureCtx.measureText(text).width;
  }
  function renderChart() {
    const d = detail, res = result(), box = $('chart');
    const isPct = unit === 'percent';
    const values = res.classes.map(c => isPct ? c.percent : c.area_ha);
    const label = v => isPct ? `${fmt(v)} %` : `${fmt(v)} ha`;
    $('chartTitle').textContent = d.name;
    $('chartSub').textContent = `Bán kính ${km(radius)} · Hiện trạng ${catalog.year} · Đơn vị: ${isPct ? '% diện tích toàn vùng đệm' : 'ha'}`;
    const W = Math.max(250, Math.floor(box.clientWidth || 300));
    const valueFont = '500 12.5px "Noto Sans", system-ui, sans-serif';
    const reserve = Math.ceil(Math.max(...values.map(v => textWidth(label(v), valueFont)))) + 10;
    const plotW = Math.max(80, W - reserve - 2);
    const rawMax = Math.max(...values);
    const step = niceStep(rawMax > 0 ? rawMax : 1, W < 330 ? 3 : 4);
    const axisMax = Math.max(step, Math.ceil((rawMax > 0 ? rawMax : 1) / step - 1e-9) * step);
    const x = v => 1 + v / axisMax * plotW;
    const rowH = 46, top = 2, barH = 14, labelY = 14, barY = 21;
    const plotH = top + rowH * values.length;
    const H = plotH + 26;
    const ticks = [];
    for (let t = 0; t <= axisMax + step * 1e-6; t += step) ticks.push(+t.toFixed(10));
    const desc = res.classes.map((c, i) => `${c.name}: ${label(values[i])}`).join('; ');
    let svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="chartTitle chartSub" aria-describedby="chartDesc" xmlns="http://www.w3.org/2000/svg"><desc id="chartDesc">${escapeHTML(desc)}</desc>`;
    svg += ticks.map(t => `<line class="grid${t === 0 ? ' baseline' : ''}" x1="${x(t)}" x2="${x(t)}" y1="${top}" y2="${plotH}"/>`).join('');
    svg += ticks.map((t, i) => `<text class="tick" x="${x(t)}" y="${plotH + 17}" text-anchor="${i === 0 ? 'start' : i === ticks.length - 1 && x(t) > W - 24 ? 'end' : 'middle'}">${tickNum.format(t)}</text>`).join('');
    res.classes.forEach((c, i) => {
      const v = values[i], y0 = top + i * rowH, w = x(v) - x(0);
      const r = Math.min(4, w / 2, barH / 2);
      const bx = x(0), by = y0 + barY;
      const bar = w > 0 ? `<path class="bar" fill="${c.color}" d="M${bx} ${by}h${w - r}a${r} ${r} 0 0 1 ${r} ${r}v${barH - 2 * r}a${r} ${r} 0 0 1 ${-r} ${r}h${-(w - r)}z"/>` : '';
      svg += `<g class="bar-row" data-index="${i}" data-class="${c.code}"><rect class="hit" x="0" y="${y0}" width="${W}" height="${rowH}"/>`
        + `<text class="cat" x="1" y="${y0 + labelY}">${escapeHTML(c.name)}</text>${bar}`
        + `<text class="val" x="${bx + Math.max(w, 0) + 6}" y="${by + barH / 2 + 4.5}" data-value="${v}">${label(v)}</text></g>`;
    });
    svg += '</svg>';
    box.innerHTML = svg;
    box.dataset.unit = unit; box.dataset.station = d.id; box.dataset.radius = String(radius);
  }
  function chartTip(e) {
    const row = e.target.closest?.('.bar-row');
    const tip = $('chartTip');
    if (!row || !detail) { tip.hidden = true; $('chart').querySelectorAll('.is-hover').forEach(n => n.classList.remove('is-hover')); return; }
    const c = result().classes[Number(row.dataset.index)];
    $('chart').querySelectorAll('.bar-row').forEach(n => n.classList.toggle('is-hover', n === row));
    tip.innerHTML = `<span class="swatch" style="background:${c.color}"></span><strong>${escapeHTML(c.name)}</strong><span>${fmt(c.area_ha)} ha · ${fmt(c.percent)} %</span>`;
    tip.hidden = false;
    const fig = $('chartView').getBoundingClientRect(), rr = row.getBoundingClientRect();
    tip.style.top = `${rr.top - fig.top - tip.offsetHeight + 4}px`;
  }

  function exportSelected() {
    if (!detail) return;
    const s = detail;
    const quote = text => `"${String(text).replaceAll('"', '""')}"`;
    const est = (s.position_quality || '').toLowerCase().includes('ước lượng') ? 'Có' : '';
    const rows = [['Mã vị trí', 'Tên vị trí', 'Loại cơ sở', 'Kinh độ', 'Vĩ độ', 'Vị trí ước lượng', 'Bán kính m', 'Mã lớp', 'Loại đất', 'Diện tích ha', 'Tỷ lệ % toàn vùng đệm']];
    for (const rad of Object.keys(s.results).map(Number).sort((a, b) => a - b)) {
      const r = s.results[String(rad)];
      if (r.valid_ha === 0) continue;
      for (const c of r.classes) rows.push([s.id, s.name, s.kind, s.lon, s.lat, est, rad, c.code, c.name, c.area_ha.toFixed(6), c.percent.toFixed(6)]);
    }
    const url = URL.createObjectURL(new Blob(['﻿' + rows.map(r => r.map(quote).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = `${s.id}_dien_tich.csv`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function fillInfo() {
    $('legendRows').innerHTML = catalog.classes.map(c => `<div><span class="swatch" style="background:${c.color}"></span>${escapeHTML(c.name)}</div>`).join('');
    const info = catalog.info || {};
    $('estimatedNote').textContent = info.estimated_note || '';
    const res = catalog.resolution_m ? `${catalog.resolution_m[0]} × ${catalog.resolution_m[1]} m` : '';
    $('sourceList').innerHTML = (info.sources || []).map(s => `<div><dt>${escapeHTML(s.label)}</dt><dd>${escapeHTML(s.text)}</dd></div>`).join('')
      + (res ? `<div><dt>Độ phân giải</dt><dd>${escapeHTML(res)}</dd></div>` : '')
      + `<div><dt>Hệ tọa độ</dt><dd>${escapeHTML(catalog.crs_label || catalog.crs)}</dd></div>`;
  }

  async function init() {
    if (!window.L) throw new Error('Chưa tải được thư viện bản đồ. Hãy tải lại trang.');
    const response = await fetch('data/catalog.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Chưa tải được danh mục vị trí. Hãy tải lại trang.');
    catalog = await response.json();
    const F = catalog.fields;
    const kinds = catalog.kinds.map(k => k.name);
    points = catalog.points.map((row, i) => {
      const p = Object.fromEntries(F.map((f, j) => [f, row[j]]));
      p.n = i + 1; p.kindIndex = kinds.indexOf(p.kind); p.estimated = !!p.estimated; p.depot = p.depot || 0;
      p.search = fold(`${p.id} ${p.name} ${p.address || ''}`);
      return p;
    });
    if (!points.length) throw new Error('Chưa có vị trí trong bộ dữ liệu.');
    byId = new Map(points.map(p => [p.id, p]));
    fillInfo();
    els.kind.innerHTML = '<option value="">Tất cả loại</option>' + catalog.kinds.map(k => `<option value="${escapeHTML(k.name)}">${escapeHTML(k.name)} (${k.count})</option>`).join('');
    els.kind.disabled = false; els.search.disabled = false;

    map = L.map('map', { zoomControl: false, minZoom: 7, maxZoom: 20, scrollWheelZoom: true, attributionControl: true, preferCanvas: false });
    map.createPane('classified').style.zIndex = 350;
    map.createPane('boundary').style.zIndex = 410;
    L.control.zoom({ position: 'topright' }).addTo(map);
    L.control.scale({ imperial: false, position: 'bottomright', maxWidth: 120 }).addTo(map);
    let tileErrors = 0, tileLoads = 0;
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>', maxZoom: 19, maxNativeZoom: 19 }).addTo(map);
    tiles.on('tileerror', () => { tileErrors++; if (tileErrors > 3 && !tileLoads) { $('mapError').hidden = false; $('mapError').textContent = 'Bản đồ nền chưa tải được. Các vị trí, vùng đệm và hiện trạng vẫn sử dụng được.'; } });
    tiles.on('tileload', () => { tileLoads++; $('mapError').hidden = true; });
    buildMarkers();

    $('stationList').addEventListener('click', e => { const t = e.target.closest('[data-station]'); if (t) choose(t.dataset.station, { focus: true }); });
    $('moreStations').addEventListener('click', renderMore);
    $('backToSelected').addEventListener('click', () => { if (selected) { showDetailsPanel(); $('locationName').focus({ preventScroll: true }); } });
    $('showList').addEventListener('click', () => { showList(); els.search.focus(); });
    let t;
    els.search.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { applyFilter(); if (selected) showList(); }, 120); });
    els.search.addEventListener('keydown', e => { if (e.key === 'Enter' && filtered.length) { e.preventDefault(); choose(filtered[0].id, { focus: true }); } });
    els.kind.addEventListener('change', () => { applyFilter(); if (selected) showList(); });
    $('overviewButton').addEventListener('click', overview);
    $('clearSelection').addEventListener('click', clearSelection);
    $('retryDetail').addEventListener('click', () => selected && choose(selected.id));
    $('exportSelected').addEventListener('click', exportSelected);
    $('radiusButtons').addEventListener('click', e => { const b = e.target.closest('[data-radius]'); if (b && detail) { radius = Number(b.dataset.radius); showResult(true); } });
    document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => { view = b.dataset.view; remember('ctu-map-view', view); renderView(); }));
    document.querySelectorAll('[data-unit]').forEach(b => b.addEventListener('click', () => { unit = b.dataset.unit; remember('ctu-map-unit', unit); renderView(); }));
    $('chart').addEventListener('pointermove', chartTip);
    $('chart').addEventListener('pointerdown', chartTip);
    $('chart').addEventListener('pointerleave', () => { $('chartTip').hidden = true; $('chart').querySelectorAll('.is-hover').forEach(n => n.classList.remove('is-hover')); });
    let lastW = 0;
    new ResizeObserver(entries => { const w = Math.round(entries[0].contentRect.width); if (w && w !== lastW) { lastW = w; if (view === 'chart' && detail && !$('chartView').hidden) renderChart(); } }).observe($('chart'));
    $('showLanduse').addEventListener('change', () => { if (image) { if ($('showLanduse').checked) image.addTo(map); else image.remove(); } });
    $('opacity').addEventListener('input', () => { $('opacityValue').textContent = `${$('opacity').value}%`; if (image) image.setOpacity(Number($('opacity').value) / 100); });

    const fromHash = parseHash();   // đọc trước khi overview() xóa hash
    applyFilter(); overview();
    new ResizeObserver(() => map.invalidateSize({ animate: false })).observe($('map'));
    if (window.matchMedia('(max-width:800px)').matches) document.querySelector('.map-legend').open = false;
    if (byId.has(fromHash.id)) choose(fromHash.id, { r: fromHash.r });
    window.addEventListener('hashchange', () => { const h = parseHash(); if (!byId.has(h.id)) return; if (h.id !== selected?.id) choose(h.id, { r: h.r }); else if (h.r && h.r !== radius && detail?.results[String(h.r)]) { radius = h.r; showResult(true); } });
    document.documentElement.dataset.appReady = 'true';
  }
  init().catch(error => {
    $('mapError').hidden = false; $('mapError').textContent = error.message;
    $('stationCount').textContent = 'Chưa tải được';
    document.querySelector('.empty-panel h2').textContent = 'Chưa thể mở bản đồ';
    $('listNote').textContent = error.message; $('listNote').classList.add('error-empty');
    console.error(error);
  });
})();
