/* Route details modal for the dashboard.
 *
 * Clicking anything with a data-route-id (live table row, mobile card, listed notification) opens a
 * Bootstrap modal with a Leaflet map (A = pickup, B = return), key times, the car, pickup/return
 * instructions from Hertz and alternative destinations for the same car.
 * Data comes from the view as JSON (json_script "route-details-data"), keyed by route id.
 */
(function () {
  const dataEl = document.getElementById('route-details-data');
  const modalEl = document.getElementById('routeModal');
  if (!dataEl || !modalEl || !window.bootstrap) return;
  const ROUTES = JSON.parse(dataEl.textContent);
  const modal = new bootstrap.Modal(modalEl);
  const $ = id => document.getElementById(id);

  const PATHS = {
    arrow: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
    flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
    route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    split: '<path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 0 0-1.2-2.9L3 3"/><path d="m15 9 6-6"/>',
    pin: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.1-8.7A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    nav: '<path d="M3 11 22 2l-9 19-2-8-8-2z"/>',
    external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    parking: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 17V7h4a3 3 0 0 1 0 6H9"/>',
    door: '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    bolt: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
    plug: '<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
    // Tabler Icons "car" and "bus" (MIT)
    car: '<path d="M7 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M17 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M5 17h-2v-6l2 -5h9l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-6m-6 -6h15m-6 0v-5"/>',
    bus: '<path d="M6 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M18 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M4 17h-2v-11a1 1 0 0 1 1 -1h14a5 7 0 0 1 5 7v5h-2m-4 0h-8"/><path d="M16 5l1.5 7l4.5 0"/><path d="M2 10l15 0"/><path d="M7 5l0 5"/><path d="M12 5l0 5"/>',
  };
  const icon = (name, size, width) =>
    `<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${width || 2}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PATHS[name]}</svg>`;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const iso = s => s.replace('T', ' ');
  const weekday = s => DAYS[new Date(s).getDay()];
  const placeUrl = l => `https://www.google.com/maps/search/?api=1&query=${l.lat},${l.lon}`;
  const directionsUrl = (a, b) => `https://www.google.com/maps/dir/?api=1&origin=${a.lat},${a.lon}&destination=${b.lat},${b.lon}&travelmode=driving`;
  const BOOK_URL = 'https://www.hertzfreerider.se/sv-se/';

  // "Mon–Fri 07:00–15:00 · Sat–Sun closed"
  function hoursHtml(loc) {
    const groups = [];
    loc.hours.forEach((h, i) => {
      const value = h ? `${h[0]}–${h[1]}` : 'closed';
      const last = groups[groups.length - 1];
      if (last && last.value === value) last.to = i; else groups.push({ from: i, to: i, value });
    });
    return groups.map(g => `<span><b>${g.from === g.to ? DAY_SHORT[g.from] : DAY_SHORT[g.from] + '–' + DAY_SHORT[g.to]}</b> ${g.value}</span>`).join('');
  }

  function accessHtml(loc, when, kind) {
    if (loc.kiosk) {
      return `<span class="access ok">${icon('key', 13)} ${kind === 'return' ? 'Key drop box – return 24/7' : 'Key kiosk – pick up 24/7'}</span>`;
    }
    const d = new Date(when), h = loc.hours[(d.getDay() + 6) % 7];
    return `<span class="access no">${icon('clock', 13)} No kiosk – ${kind === 'return' ? 'return' : 'pick up'} during opening hours (${DAY_SHORT[(d.getDay() + 6) % 7]} ${h ? h[0] + '–' + h[1] : 'closed'})</span>`;
  }

  function locationHtml(loc, kind, when) {
    const lines = [];
    if (kind === 'pickup') {
      if (loc.info.location) lines.push(['key', 'Key', loc.info.location]);
      if (loc.info.parking) lines.push(['parking', 'Car is parked', loc.info.parking]);
    } else if (loc.info.return) {
      lines.push(['door', 'Return', loc.info.return]);
    }
    if (loc.info.misc) lines.push(['info', 'Good to know', loc.info.misc]);
    return `<div class="locbox">
      <div class="subhead mt-0">${icon(kind === 'pickup' ? 'key' : 'flag', 13)} ${kind === 'pickup' ? 'Pickup' : 'Return'}</div>
      <div class="ttl">${esc(loc.short)}<small>${esc(loc.sub)}</small></div>
      <div class="addr">${esc(loc.address)}${loc.city ? ', ' + esc(loc.city) : ''}</div>
      ${accessHtml(loc, when, kind)}<div class="hours">${hoursHtml(loc)}</div>
      ${lines.map(([ic, title, text]) => `<div class="info-line">${icon(ic, 14)}<div><b>${title}</b>${esc(text)}</div></div>`).join('')}
      <div class="loc-links"><a href="${placeUrl(loc)}" target="_blank" rel="noopener">${icon('pin', 13)} Map</a>${loc.phone ? `<a href="tel:${esc(loc.phone.replace(/[^+\d]/g, ''))}">${icon('phone', 13)} ${esc(loc.phone)}</a>` : ''}</div>
    </div>`;
  }

  function carHtml(r) {
    const tile = `<div class="car-tile">${icon(r.car.van ? 'bus' : 'car', 32, 1.6)}${r.car.tags.includes('Electric') ? `<span class="ct-badge">${icon('bolt', 11)}</span>` : r.car.tags.includes('Plug-in hybrid') ? `<span class="ct-badge">${icon('plug', 11)}</span>` : ''}</div>`;
    const tags = r.car.tags.map(t => `<span class="mini-badge ${t === 'Electric' || t === 'Plug-in hybrid' ? 'ev' : ''}">${esc(t)}</span>`).join('');
    return `<div class="carbox">${tile}<div>
        <div class="name">${esc(r.car.name || 'Car (model announced at pickup)')}${r.count > 1 ? ` <span class="mini-badge twin">${r.count} identical</span>` : ''}</div>
        <div class="raw">${esc(r.car.raw)}</div><div>${tags}</div></div></div>
      ${r.warnings.map(w => `<div class="warnbox">${icon('alert', 15)} ${esc(w)}</div>`).join('')}`;
  }

  // Map
  let map = null, layer = null, current = null;
  function drawMap() {
    const r = current;
    const hasCoords = [r.from.lat, r.from.lon, r.to.lat, r.to.lon].every(v => typeof v === 'number');
    $('routeMap').style.display = hasCoords ? '' : 'none';
    $('routeMapTools').style.display = hasCoords ? '' : 'none';
    if (!hasCoords) return;
    if (!map) {
      map = L.map('routeMap');
      // OSM's tile policy requires a Referer. Django's default "same-origin" Referrer-Policy strips it for
      // cross-origin requests, so send the origin (never the full URL) for tile images only.
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 18,
        referrerPolicy: 'strict-origin-when-cross-origin',
      }).addTo(map);
      layer = L.layerGroup().addTo(map);
    }
    map.invalidateSize();
    layer.clearLayers();
    const a = [r.from.lat, r.from.lon], b = [r.to.lat, r.to.lon];
    r.alternatives.forEach(x => {
      const alt = ROUTES[x.id];
      if (!alt) return;
      L.polyline([a, [alt.to.lat, alt.to.lon]], { color: '#6c757d', weight: 2, dashArray: '4 6' }).addTo(layer);
      L.circleMarker([alt.to.lat, alt.to.lon], { radius: 5, color: '#fff', weight: 2, fillColor: '#6c757d', fillOpacity: 1 })
        .addTo(layer).bindTooltip('Also possible: ' + alt.to.short);
    });
    L.polyline([a, b], { color: '#ffb347', weight: 8, opacity: .45 }).addTo(layer);
    L.polyline([a, b], { color: '#212529', weight: 3, dashArray: '8 6' }).addTo(layer);
    const pin = (letter, cls) => L.divIcon({ className: '', html: `<div class="pin-ab ${cls}"><span>${letter}</span></div>`, iconSize: [30, 30], iconAnchor: [15, 30] });
    const label = text => L.divIcon({ className: '', html: `<span class="map-lbl">${esc(text)}</span>`, iconSize: null, iconAnchor: [-20, 26] });
    L.marker(a, { icon: pin('A', 'a'), zIndexOffset: 900 }).addTo(layer).bindTooltip(`<b>Pickup:</b> ${esc(r.from.name)}`, { direction: 'top', offset: [0, -28] });
    L.marker(b, { icon: pin('B', 'b'), zIndexOffset: 900 }).addTo(layer).bindTooltip(`<b>Return:</b> ${esc(r.to.name)}`, { direction: 'top', offset: [0, -28] });
    L.marker(a, { icon: label(r.from.short), interactive: false }).addTo(layer);
    L.marker(b, { icon: label(r.to.short), interactive: false }).addTo(layer);
    zoom('ab');
  }
  function zoom(target) {
    const r = current, a = [r.from.lat, r.from.lon], b = [r.to.lat, r.to.lon];
    if (target === 'a') map.flyTo(a, 15, { duration: .6 });
    else if (target === 'b') map.flyTo(b, 15, { duration: .6 });
    else if (target === 'ab') map.fitBounds(L.latLngBounds([a, b]), { padding: [50, 50], maxZoom: 12 });
    else {
      const points = [a, b].concat(r.alternatives.map(x => ROUTES[x.id]).filter(Boolean).map(x => [x.to.lat, x.to.lon]));
      map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 11 });
    }
  }

  function open(id) {
    const r = ROUTES[id];
    if (!r) return;
    current = r;
    const chip = r.availableNow ? '<span class="status-chip open">Available now</span>' : `<span class="status-chip upcoming">Available from ${iso(r.availableAt)}</span>`;
    $('routeModalTitle').innerHTML = `${esc(r.from.short)} ${icon('arrow', 20)} ${esc(r.to.short)} ${chip}${r.matches.length ? '<span class="badge match-badge">Matches your search</span>' : ''}`;
    $('routeModalSub').textContent = `${r.from.name} → ${r.to.name}`;
    $('routeFacts').innerHTML = `
      <div class="fact wide"><div class="l">Pick up from</div><div class="v">${iso(r.availableAt)}</div><div class="s">${weekday(r.availableAt)} · ${r.availableNow ? 'available now' : esc(r.pickupIn)}</div></div>
      <div class="fact wide"><div class="l">Return by</div><div class="v">${iso(r.latestReturn)}</div><div class="s">${weekday(r.latestReturn)} · at ${esc(r.to.short)}</div></div>
      <div class="fact"><div class="l">Distance</div><div class="v">${r.km} km</div><div class="s">max ${r.maxKm} km</div></div>
      <div class="fact"><div class="l">Drive time</div><div class="v">${esc(r.duration)}</div><div class="s">estimated</div></div>
      <div class="fact"><div class="l">Time available</div><div class="v">${r.hoursAvailable} h</div><div class="s">${r.availableNow ? 'from now' : 'from pickup'} to return</div></div>`;
    $('routeCar').innerHTML = carHtml(r);
    $('routeAlternatives').innerHTML = r.alternatives.length
      ? `<div class="subhead">${icon('split', 13)} Same car can also go to</div>` + r.alternatives.map(x => `<button type="button" class="alt-chip" data-route-id="${esc(x.id)}">${esc(x.to)}<small>${x.km} km · ${esc(x.duration)}</small></button>`).join('')
      : '';
    $('routeLocations').innerHTML = `<div class="col-md-6">${locationHtml(r.from, 'pickup', r.availableNow ? new Date() : r.availableAt)}</div><div class="col-md-6">${locationHtml(r.to, 'return', r.latestReturn)}</div>`;
    $('routeMapTools').innerHTML = `<button type="button" data-zoom="ab">${icon('route', 12)} Route A → B</button>`
      + (r.alternatives.length ? `<button type="button" data-zoom="all">${icon('split', 12)} Show ${r.alternatives.length} alternatives</button>` : '')
      + `<button type="button" data-zoom="a">${icon('key', 12)} Zoom to pickup</button><button type="button" data-zoom="b">${icon('flag', 12)} Zoom to return</button>`
      + `<a href="${directionsUrl(r.from, r.to)}" target="_blank" rel="noopener">${icon('nav', 12)} Open in Google Maps</a>`;
    $('routeFooter').innerHTML = `<span class="me-auto small opacity-75">${r.matches.length ? 'Matches: ' + r.matches.map(esc).join(', ') : 'Not matching any of your searches'}</span>
      <a class="btn btn-outline-secondary" href="${directionsUrl(r.from, r.to)}" target="_blank" rel="noopener">Directions</a>
      <a class="btn btn-primary" href="${BOOK_URL}" target="_blank" rel="noopener">Book on Hertz ${icon('external', 14)}</a>`;
    if (modalEl.classList.contains('show')) drawMap(); else modal.show();
  }

  modalEl.addEventListener('shown.bs.modal', drawMap);
  modalEl.addEventListener('click', e => {
    const z = e.target.closest('[data-zoom]');
    if (z) zoom(z.dataset.zoom);
  });
  document.addEventListener('click', e => {
    const target = e.target.closest('[data-route-id]');
    if (target) open(target.dataset.routeId);
  });
  // Deep link, e.g. /#route-67729 opens that route directly
  const deepLink = location.hash.match(/^#route-(\d+)$/);
  if (deepLink) open(deepLink[1]);
})();
