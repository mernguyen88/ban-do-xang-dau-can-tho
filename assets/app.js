'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const num = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmt = n => num.format(n);
  const els = { select: $('stationSelect'), details: $('detailsPanel'), empty: $('emptyPanel') };
  let data, map, selected = null, image = null, buffer = null;
  const markers = new Map();
  const dialog = $('methodDialog');
  $('methodButton').addEventListener('click', () => dialog.showModal());
  $('closeDialog').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) { const r = dialog.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close(); } });

  function escapeHTML(text) { return String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function addLegend() {
    $('legendRows').innerHTML = data.classes.map(c => `<div><span class="swatch" style="background:${c.color}"></span>${escapeHTML(c.name)}</div>`).join('') + '<div><span class="swatch" style="background:#aab0b8"></span>Thiếu dữ liệu</div>';
  }
  function clearLayers() {
    if (image) { image.remove(); image = null; }
    if (buffer) { buffer.remove(); buffer = null; }
  }
  function clearSelection() {
    clearLayers(); selected = null; els.select.value = '';
    els.details.hidden = true; els.empty.hidden = false;
    $('layerControls').hidden = true; $('mapHint').hidden = false;
    for (const marker of markers.values()) marker.getElement()?.classList.remove('is-selected');
    map.getContainer().removeAttribute('data-selected-station');
  }
  function overview() {
    clearSelection();
    map.fitBounds(L.latLngBounds(data.stations.map(s => [s.lat,s.lon])).pad(.18), { animate: false, maxZoom: 13 });
  }
  function choose(id, fit = true) {
    const station = data.stations.find(s => s.id === id);
    if (!station) return;
    clearLayers(); selected = station; els.select.value = id;
    els.empty.hidden = true; els.details.hidden = false;
    $('mapHint').hidden = true; $('layerControls').hidden = false;
    $('locationTag').textContent = `${station.id} · ${station.kind}`;
    $('locationName').textContent = station.name;
    $('coordinates').textContent = `${station.lat.toFixed(6)}° N · ${station.lon.toFixed(6)}° E`;
    $('totalArea').textContent = fmt(station.area_ha);
    $('validArea').textContent = fmt(station.valid_ha);
    $('missingArea').textContent = fmt(station.missing_ha);
    $('coveragePercent').textContent = `${fmt(station.coverage_percent)}%`;
    $('coverageFill').style.width = `${station.coverage_percent}%`;
    for (const [element, field] of [['nodataArea','nodata_ha'],['outsideArea','outside_ha'],['unknownArea','unknown_ha']]) $(element).textContent = `${fmt(station[field])} ha`;
    $('areaRows').innerHTML = station.classes.map(c => `<tr data-class="${c.code}"><td><span class="class-name"><span class="swatch" style="background:${c.color}"></span>${escapeHTML(c.name)}</span></td><td>${fmt(c.area_ha)}</td><td>${fmt(c.percent)}</td></tr>`).join('') + `<tr class="missing-row"><td><span class="class-name"><span class="swatch" style="background:#aab0b8"></span>Thiếu dữ liệu</span></td><td>${fmt(station.missing_ha)}</td><td>${fmt(station.missing_ha/station.area_ha*100)}</td></tr>`;
    $('compositionBar').innerHTML = station.classes.map(c => `<span style="width:${c.percent}%;background:${c.color}"></span>`).join('') + `<span style="width:${100-station.coverage_percent}%;background:#aab0b8"></span>`;

    const currentImage = L.imageOverlay(station.image, station.image_bounds, { pane: 'classified', opacity: Number($('opacity').value)/100, interactive: false, alt: `Hiện trạng sử dụng đất trong bán kính 2 km quanh ${station.name}` });
    image = currentImage;
    $('layerStatus').textContent = 'Đang tải lớp hiện trạng…';
    currentImage.on('load', () => { if (image === currentImage) $('layerStatus').textContent = ''; });
    currentImage.on('error', () => { if (image === currentImage) $('layerStatus').textContent = 'Chưa tải được ảnh hiện trạng. Bảng diện tích vẫn có sẵn.'; });
    // Load while detached as well, so visibility toggling does not lose state.
    currentImage.addTo(map);
    if (!$('showLanduse').checked) currentImage.remove();
    buffer = L.geoJSON(station.buffer, { pane: 'boundary', interactive: false, style: { color: '#0d6159', weight: 2.5, opacity: 1, fillOpacity: 0, dashArray: '7 5' } }).addTo(map);
    for (const [key, marker] of markers) {
      marker.getElement()?.classList.toggle('is-selected', key === id);
      marker.setZIndexOffset(key === id ? 1000 : 0);
    }
    map.getContainer().setAttribute('data-selected-station', station.id);
    if (fit) map.fitBounds(buffer.getBounds(), { padding: [30,30], animate: false, maxZoom: 16 });
  }
  function exportSelected() {
    if (!selected) return;
    const s = selected;
    const quote = text => `"${String(text).replaceAll('"','""')}"`;
    const rows = [['Mã vị trí','Tên vị trí','Kinh độ','Vĩ độ','Mã lớp','Loại đất','Diện tích ha','Tỷ lệ % toàn vùng đệm']];
    for (const c of s.classes) rows.push([s.id,s.name,s.lon,s.lat,c.code,c.name,c.area_ha.toFixed(6),c.percent.toFixed(6)]);
    for (const [key,label] of [['nodata_ha','NoData trong raster'],['outside_ha','Ngoài phạm vi raster'],['unknown_ha','Mã lớp chưa xác định']]) rows.push([s.id,s.name,s.lon,s.lat,'',label,s[key].toFixed(6),(s[key]/s.area_ha*100).toFixed(6)]);
    const url = URL.createObjectURL(new Blob(['\uFEFF'+rows.map(r => r.map(quote).join(',')).join('\r\n')], {type:'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = `${s.id}_dien_tich_2km.csv`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }
  async function init() {
    if (!window.L) throw new Error('Chưa tải được thư viện bản đồ. Hãy tải lại trang.');
    const response = await fetch('data/stations.json');
    if (!response.ok) throw new Error('Chưa tải được dữ liệu vị trí. Hãy tải lại trang.');
    data = await response.json();
    if (!data.stations?.length) throw new Error('Chưa có vị trí trong bộ dữ liệu.');
    $('stationCount').textContent = `${data.stations.length} vị trí`;
    $('selectionMethod').textContent = data.selection;
    $('areaMethod').textContent = data.method;
    els.select.innerHTML = '<option value="">Chọn một vị trí…</option>' + data.stations.map(s => `<option value="${s.id}">${s.id} · ${escapeHTML(s.name)}</option>`).join('');
    els.select.disabled = false;
    $('stationList').innerHTML = data.stations.map((s,i) => `<button type="button" data-station="${s.id}"><span>${String(i+1).padStart(2,'0')}</span><span>${escapeHTML(s.name)}<small>${s.id} · ${s.kind}</small></span></button>`).join('');
    $('stationList').addEventListener('click', e => { const target = e.target.closest('[data-station]'); if (target) choose(target.dataset.station); });
    els.select.addEventListener('change', () => els.select.value ? choose(els.select.value) : clearSelection());
    map = L.map('map', { zoomControl: false, minZoom: 7, maxZoom: 20, scrollWheelZoom: true, attributionControl: true });
    map.createPane('classified').style.zIndex = 350;
    map.createPane('boundary').style.zIndex = 410;
    L.control.zoom({position:'topright'}).addTo(map);
    L.control.scale({imperial:false,position:'bottomleft',maxWidth:120}).addTo(map);
    let tileErrors = 0, tileLoads = 0;
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>', maxZoom:19, maxNativeZoom:19 }).addTo(map);
    tiles.on('tileerror', () => { tileErrors++; if (tileErrors > 3 && !tileLoads) { $('mapError').hidden = false; $('mapError').textContent = 'Bản đồ nền chưa tải được. Các vị trí, vùng đệm và hiện trạng vẫn sử dụng được.'; } });
    tiles.on('tileload', () => { tileLoads++; $('mapError').hidden = true; });
    data.stations.forEach((s,i) => {
      const marker = L.marker([s.lat,s.lon], { title: `${s.id} · ${s.name}`, alt: `${s.id} · ${s.name}`, keyboard: true,
        icon: L.divIcon({ className:'fuel-pin', iconSize:[30,30], iconAnchor:[15,15], html:`<span class="pin-face">${i+1}</span>` }) }).addTo(map);
      marker.bindTooltip(`${escapeHTML(s.id)} · ${escapeHTML(s.name)}`,{direction:'top',offset:[0,-16]});
      marker.on('click', () => choose(s.id)); markers.set(s.id,marker);
    });
    $('overviewButton').addEventListener('click',overview);
    $('clearSelection').addEventListener('click',clearSelection);
    $('exportSelected').addEventListener('click',exportSelected);
    $('showLanduse').addEventListener('change', () => { if (image) { if ($('showLanduse').checked) image.addTo(map); else image.remove(); } });
    $('opacity').addEventListener('input', () => { $('opacityValue').textContent = `${$('opacity').value}%`; if (image) image.setOpacity(Number($('opacity').value)/100); });
    addLegend(); overview();
    new ResizeObserver(() => map.invalidateSize({animate:false})).observe($('map'));
    if (window.matchMedia('(max-width:720px)').matches) document.querySelector('.map-legend').open = false;
    document.documentElement.dataset.appReady = 'true';
  }
  init().catch(error => {
    $('mapError').hidden = false; $('mapError').textContent = error.message;
    $('stationCount').textContent = 'Chưa tải được';
    els.select.innerHTML = '<option value="">Chưa tải được dữ liệu</option>';
    document.querySelector('.empty-panel h2').textContent = 'Chưa thể mở bản đồ';
    document.querySelector('.empty-panel p').textContent = error.message;
    document.querySelector('.empty-panel p').classList.add('error-empty');
    console.error(error);
  });
})();
