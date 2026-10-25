/* Route details for the dashboard.
 *
 * Clicking anything with a data-route-id (live table row, mobile card, listed notification) opens a
 * Bootstrap modal that is a full-window Leaflet map (A = pickup, B = return) with floating glass panels:
 * the trip as three steps on the left (pick up, drive, return) and every destination the same car can
 * be returned to on the right. Steps and map are linked: a step zooms the map, A/B scrolls to the step.
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
    route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    split: '<path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22v-8.3a4 4 0 0 0-1.2-2.9L3 3"/><path d="m15 9 6-6"/>',
    maximize: '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
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
    // Tabler Icons "car", "bus" and "plane" (MIT)
    car: '<path d="M7 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M17 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M5 17h-2v-6l2 -5h9l4 5h1a2 2 0 0 1 2 2v4h-2m-4 0h-6m-6 -6h15m-6 0v-5"/>',
    bus: '<path d="M6 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M18 17m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M4 17h-2v-11a1 1 0 0 1 1 -1h14a5 7 0 0 1 5 7v5h-2m-4 0h-8"/><path d="M16 5l1.5 7l4.5 0"/><path d="M2 10l15 0"/><path d="M7 5l0 5"/><path d="M12 5l0 5"/>',
    plane: '<path d="M16 10h4a2 2 0 0 1 0 4h-4l-4 7h-3l2 -7h-4l-2 2h-3l2 -4l-2 -4h3l2 2h4l-2 -7h3z"/>',
  };
  const icon = (name, size, width) =>
    `<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${width || 2}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PATHS[name]}</svg>`;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const place = (loc, size) => esc(loc.short) + (loc.airport ? `<span class="ico-plane" title="Airport">${icon('plane', size)}</span>` : '');

  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const iso = s => s.replace('T', ' ');
  const weekday = s => DAYS[new Date(s).getDay()];
  const minutesOf = duration => {
    const h = /(\d+)h/.exec(duration || ''), m = /(\d+)m/.exec(duration || '');
    return (h ? +h[1] * 60 : 0) + (m ? +m[1] : 0);
  };
  const placeUrl = l => `https://www.google.com/maps/search/?api=1&query=${l.lat},${l.lon}`;
  const directionsUrl = (a, b) => `https://www.google.com/maps/dir/?api=1&origin=${a.lat},${a.lon}&destination=${b.lat},${b.lon}&travelmode=driving`;
  const BOOK_URL = 'https://www.hertzfreerider.se/sv-se/';
  const hasCoords = r => [r.from.lat, r.from.lon, r.to.lat, r.to.lon].every(v => typeof v === 'number');
  const ll = loc => [loc.lat, loc.lon];
  const wide = () => window.matchMedia('(min-width: 861px)').matches;

  // "Mon–Fri 07:00–15:00 · Sat–Sun closed"
  function hoursHtml(loc) {
    const groups = [];
    loc.hours.forEach((h, i) => {
      const value = h ? `${h[0]}–${h[1]}` : 'closed';
      const last = groups[groups.length - 1];
      if (last && last.value === value) last.to = i; else groups.push({ from: i, to: i, value });
    });
    return `<div class="hours">${groups.map(g => `<span><b>${g.from === g.to ? DAY_SHORT[g.from] : DAY_SHORT[g.from] + '–' + DAY_SHORT[g.to]}</b> ${g.value}</span>`).join('')}</div>`;
  }

  function accessHtml(loc, when, kind) {
    if (loc.kiosk) {
      return `<span class="access ok">${icon('key', 13)} ${kind === 'return' ? 'Key drop box – return 24/7' : 'Key kiosk – pick up 24/7'}</span>`;
    }
    const d = new Date(when), h = loc.hours[(d.getDay() + 6) % 7];
    return `<span class="access no">${icon('clock', 13)} No kiosk – ${kind === 'return' ? 'return' : 'pick up'} during opening hours (${DAY_SHORT[(d.getDay() + 6) % 7]} ${h ? h[0] + '–' + h[1] : 'closed'})</span>`;
  }

  // Hertz instructions, folded to three lines until clicked
  function infoHtml(loc, kind) {
    const lines = [];
    if (kind === 'pickup') {
      if (loc.info.location) lines.push(['key', 'Key', loc.info.location]);
      if (loc.info.parking) lines.push(['parking', 'Car is parked', loc.info.parking]);
    } else if (loc.info.return) {
      lines.push(['door', 'Return', loc.info.return]);
    }
    if (loc.info.misc) lines.push(['info', 'Good to know', loc.info.misc]);
    return lines.map(([ic, title, text]) => `<div class="info-line">${icon(ic, 14)}<div><b>${title}</b><div class="rm-clamp" title="Click to show all">${esc(text)}</div></div></div>`).join('');
  }

  function stationHtml(loc, kind, when) {
    const links = `<div class="loc-links"><a href="${placeUrl(loc)}" target="_blank" rel="noopener">${icon('pin', 13)} Map</a>${loc.phone ? `<a href="tel:${esc(loc.phone.replace(/[^+\d]/g, ''))}">${icon('phone', 13)} ${esc(loc.phone)}</a>` : ''}</div>`;
    return `<div class="rm-place">${place(loc, 14)} <small>${esc(loc.sub)}</small></div>
      <div class="rm-addr">${esc(loc.address)}${loc.city ? ', ' + esc(loc.city) : ''}</div>
      <div class="rm-card">${accessHtml(loc, when, kind)}${hoursHtml(loc)}${infoHtml(loc, kind)}${links}</div>`;
  }

  // Time window bar: waiting (striped) → available (green), the drive in yellow at the start
  function windowHtml(r) {
    const now = Date.now(), a = new Date(r.availableAt).getTime(), z = new Date(r.latestReturn).getTime();
    const s0 = Math.min(now, a), total = Math.max(1, z - s0), start = Math.max(now, a);
    const pct = t => ((t - s0) / total * 100).toFixed(2) + '%';
    const drive = minutesOf(r.duration) * 60000 / total * 100;
    return `<div class="rm-win">
      <div class="top"><span>Time window</span><b>${r.hoursAvailable} h</b></div>
      <div class="bar">${a > now ? `<i class="wait" style="left:0;width:${pct(a)}"></i>` : ''}<i class="ok" style="left:${pct(start)};right:0"></i><i class="drv" style="left:${pct(start)};width:max(4px, ${drive.toFixed(2)}%)"></i></div>
      <div class="ends"><span>${a > now ? 'Now' : 'Now · ready'}</span>${a > now ? `<span>Ready ${iso(r.availableAt)}</span>` : ''}<span>Return by ${iso(r.latestReturn)}</span></div>
    </div>`;
  }

  function carHtml(r) {
    const badge = r.car.tags.includes('Electric') ? 'bolt' : r.car.tags.includes('Plug-in hybrid') ? 'plug' : '';
    const tags = r.car.tags.map(t => `<span class="mini-badge ${t === 'Electric' || t === 'Plug-in hybrid' ? 'ev' : ''}">${esc(t)}</span>`).join('');
    return `<div class="rm-car"><div class="car-tile">${icon(r.car.van ? 'bus' : 'car', 22, 1.6)}${badge ? `<span class="ct-badge">${icon(badge, 10)}</span>` : ''}</div>
      <div><div class="name">${esc(r.car.name || 'Car (model announced at pickup)')} ${tags}</div><div class="raw">${esc(r.car.raw)}</div></div></div>
      ${r.warnings.map(w => `<div class="warnbox">${icon('alert', 14)} ${esc(w)}</div>`).join('')}`;
  }

  // The car's current destination plus the alternatives (same transportOfferId), nearest first
  function destinations(r) {
    return [{ id: r.id, km: r.km, duration: r.duration, route: r }]
      .concat(r.alternatives.filter(x => ROUTES[x.id]).map(x => ({ ...x, route: ROUTES[x.id] })))
      .sort((a, b) => a.km - b.km);
  }

  function render(r) {
    const showOnMap = target => `<button type="button" data-focus="${target}">${icon('pin', 11, 2.4)} Show on map</button>`;
    const others = destinations(r).filter(o => o.id !== r.id);
    $('routeHead').innerHTML = `
      <div class="rm-kick">${icon('route', 12)} Your trip</div>
      <div class="rm-title" id="routeModalTitle">${place(r.from, 17)} ${icon('arrow', 17)} ${place(r.to, 17)}</div>
      <div class="rm-chips">${r.availableNow ? '<span class="status-chip open">Available now</span>' : `<span class="status-chip upcoming">From ${iso(r.availableAt)} · ${esc(r.pickupIn)}</span>`}${r.count > 1 ? `<span class="mini-badge twin">×${r.count} identical</span>` : ''}</div>`;
    $('routeSteps').innerHTML = `
      <section class="rm-step" data-step="a">
        <button type="button" class="rm-mk ring" data-focus="a" title="Show pickup on the map"><span></span></button>
        <div class="rm-k">Step 1 · Pick up ${showOnMap('a')}</div>
        <div class="rm-when">From ${iso(r.availableAt)} <small>${weekday(r.availableAt)}</small>${r.availableNow ? '<span class="now">● Available now</span>' : ''}</div>
        ${stationHtml(r.from, 'pickup', r.availableNow ? new Date() : r.availableAt)}
      </section>
      <section class="rm-step" data-step="ab">
        <button type="button" class="rm-mk car" data-focus="ab" title="Show the route on the map">${icon(r.car.van ? 'bus' : 'car', 16)}</button>
        <div class="rm-k">Step 2 · Drive ${showOnMap('ab')}</div>
        <div class="rm-drive"><div><b>${r.km} km</b><span>distance</span></div><div><b>≈ ${esc(r.duration)}</b><span>drive time</span></div><div><b>${r.maxKm} km</b><span>max allowed</span></div></div>
        <div class="rm-card">${carHtml(r)}${windowHtml(r)}</div>
      </section>
      <section class="rm-step" data-step="b">
        <button type="button" class="rm-mk pin" data-focus="b" title="Show return on the map"><svg width="24" height="27" viewBox="0 0 24 26" aria-hidden="true"><path d="M12 25s-8-7.4-8-14a8 8 0 0 1 16 0c0 6.6-8 14-8 14z" fill="currentColor"/><circle cx="12" cy="11" r="3.2"/></svg></button>
        <div class="rm-k">Step 3 · Return ${showOnMap('b')}</div>
        <div class="rm-when">By ${iso(r.latestReturn)} <small>${weekday(r.latestReturn)}</small></div>
        ${stationHtml(r.to, 'return', r.latestReturn)}
      </section>
      ${others.length ? `<div class="rm-others"><div class="rm-k">Same car, other destinations</div>${others.map(o => destinationHtml(o, r)).join('')}</div>` : ''}`;
    $('routeSteps').scrollTop = 0;
    $('routeFooter').innerHTML = `
      <a class="btn btn-outline-light btn-sm" href="${directionsUrl(r.from, r.to)}" target="_blank" rel="noopener">${icon('nav', 13)} Directions</a>
      <a class="btn btn-primary btn-sm fw-bold" href="${BOOK_URL}" target="_blank" rel="noopener">Book on Hertz ${icon('external', 13)}</a>`;
    const options = destinations(r);
    $('routeDestinations').innerHTML = `
      <div class="rm-kick">${icon('split', 12)} Where this car can go</div>
      <h4>${options.length > 1 ? `${options.length} destinations from ${esc(r.from.short)}` : `Only ${esc(r.to.short)}`}</h4>
      ${options.map(o => destinationHtml(o, r)).join('')}
      <div class="hint">${options.length > 1 ? 'Hover to preview on the map, click to switch.' : 'The car is only offered to this destination.'}</div>`;
    $('routeTools').querySelector('[data-zoom="all"]').hidden = options.length < 2;
  }

  function destinationHtml(o, r) {
    return `<a class="rm-dest-item ${o.id === r.id ? 'on' : ''}" href="#route-${esc(o.id)}" data-route-id="${esc(o.id)}" data-line="${esc(o.id)}">
      <span class="dot"></span>
      <span><span class="name">${place(o.route.to, 13)}</span><span class="meta">by ${iso(o.route.latestReturn)}</span></span>
      <span class="km">${o.km} km<span class="meta">${esc(o.duration)}</span></span></a>`;
  }

  // Map
  let map = null, layer = null, current = null, bounds = null, lines = {};
  function drawMap() {
    const r = current;
    if (!map) {
      map = L.map('routeMap', { zoomControl: false });
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
    lines = {};
    bounds = null;
    $('routeTools').hidden = !hasCoords(r);
    if (!hasCoords(r)) {
      map.setView([62, 15], 5);
      return;
    }
    const a = ll(r.from), b = ll(r.to), points = [a, b];
    const pin = (letter, cls) => L.divIcon({ className: '', html: `<div class="pin-ab ${cls}"><span>${letter}</span></div>`, iconSize: [30, 30], iconAnchor: [15, 30] });
    const label = (text, cls) => L.divIcon({ className: '', html: `<span class="map-lbl ${cls || ''}">${esc(text)}</span>`, iconSize: null, iconAnchor: [-20, 26] });
    r.alternatives.forEach(x => {
      const alt = ROUTES[x.id];
      if (!alt || !hasCoords(alt)) return;
      const p = ll(alt.to);
      points.push(p);
      lines[x.id] = L.polyline([a, p], { color: '#6c757d', weight: 2, dashArray: '4 6' }).addTo(layer).on('click', () => open(x.id));
      L.circleMarker(p, { radius: 6, color: '#fff', weight: 2, fillColor: '#6c757d', fillOpacity: 1 }).addTo(layer).on('click', () => open(x.id))
        .on('mouseover', () => highlight(x.id, true)).on('mouseout', () => highlight(x.id, false));
      L.marker(p, { icon: label(`${alt.to.short} · ${x.km} km`, 'alt'), interactive: false }).addTo(layer);
    });
    L.polyline([a, b], { color: '#ffb347', weight: 9, opacity: .5 }).addTo(layer);
    L.polyline([a, b], { color: '#212529', weight: 3, dashArray: '8 6' }).addTo(layer);
    L.marker(a, { icon: pin('A', 'a'), zIndexOffset: 900 }).addTo(layer).on('click', () => focus('a', true));
    L.marker(b, { icon: pin('B', 'b'), zIndexOffset: 900 }).addTo(layer).on('click', () => focus('b', true));
    L.marker(a, { icon: label(r.from.short), interactive: false }).addTo(layer);
    L.marker(b, { icon: label(`${r.to.short} · ${r.km} km`), interactive: false }).addTo(layer);
    bounds = { ab: L.latLngBounds([a, b]), all: L.latLngBounds(points) };
  }

  function highlight(id, on) {
    const line = lines[id];
    if (!line) return;
    line.setStyle(on ? { color: '#ffb347', weight: 5, dashArray: null } : { color: '#6c757d', weight: 2, dashArray: '4 6' });
    if (on) line.bringToFront();
  }

  // Keep A and B clear of the floating panels (side by side on wide screens, panel at the bottom on phones)
  const padding = () => wide()
    ? { paddingTopLeft: [470, 70], paddingBottomRight: [330, 50] }
    : { paddingTopLeft: [40, 70], paddingBottomRight: [150, window.innerHeight * .62] };

  // Step 1 → A, step 2 → the route, step 3 → B; clicking A or B on the map scrolls to that step
  function focus(target, scrollPanel, animate = true) {
    $('routeTools').querySelectorAll('[data-zoom]').forEach(btn => btn.classList.toggle('on', btn.dataset.zoom === target));
    $('routeSteps').querySelectorAll('.rm-step').forEach(s => s.classList.toggle('on', s.dataset.step === target));
    if (scrollPanel) {
      const step = $('routeSteps').querySelector(`[data-step="${target}"]`);
      if (step) $('routeSteps').scrollTo({ top: step.offsetTop - 12, behavior: 'smooth' });
    }
    if (!bounds) return;
    if (target === 'a' || target === 'b') {
      map.flyTo(ll(target === 'a' ? current.from : current.to), 15, { duration: .7 });
      map.once('moveend', () => map.panBy(wide() ? [-160, 0] : [0, window.innerHeight * .28]));
    } else {
      const options = Object.assign({ maxZoom: 11 }, padding());
      const box = target === 'all' ? bounds.all : bounds.ab;
      if (animate) map.flyToBounds(box, Object.assign({ duration: .7 }, options)); else map.fitBounds(box, options);
    }
  }

  function show(animate) {
    drawMap();
    focus(current.alternatives.length ? 'all' : 'ab', false, animate);
  }

  function open(id) {
    const r = ROUTES[id];
    if (!r) return;
    current = r;
    render(r);
    if (modalEl.classList.contains('show')) show(true); else modal.show();
  }

  $('routeTools').innerHTML = `
    <button type="button" data-zoom="ab">${icon('route', 13)}<span>Route</span></button>
    <button type="button" data-zoom="a">A<span> · Pickup</span></button>
    <button type="button" data-zoom="b">B<span> · Return</span></button>
    <button type="button" data-zoom="all">${icon('maximize', 13)}<span>All destinations</span></button>`;
  modalEl.addEventListener('shown.bs.modal', () => show(false));
  $('routeTools').addEventListener('click', e => {
    const b = e.target.closest('[data-zoom]');
    if (b) focus(b.dataset.zoom, b.dataset.zoom !== 'all');
  });
  $('routeSteps').addEventListener('click', e => {
    const f = e.target.closest('[data-focus]');
    if (f) return focus(f.dataset.focus, false);
    const clamp = e.target.closest('.rm-clamp');
    if (clamp) clamp.classList.add('open');
  });
  $('routeDestinations').addEventListener('mouseover', e => {
    const item = e.target.closest('[data-line]');
    if (item) highlight(item.dataset.line, true);
  });
  $('routeDestinations').addEventListener('mouseout', e => {
    const item = e.target.closest('[data-line]');
    if (item && !item.contains(e.relatedTarget)) highlight(item.dataset.line, false);
  });
  document.addEventListener('click', e => {
    const target = e.target.closest('[data-route-id]');
    if (!target) return;
    e.preventDefault();
    open(target.dataset.routeId);
  });
  // Deep link, e.g. /#route-67729 opens that route directly
  const deepLink = location.hash.match(/^#route-(\d+)$/);
  if (deepLink) open(deepLink[1]);
})();
