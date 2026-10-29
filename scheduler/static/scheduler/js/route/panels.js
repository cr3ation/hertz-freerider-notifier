/* The HTML of the route window's panels. Every function returns markup; main.js puts it in place. */

import { ROUTES, destinations } from './data.js';
import { BOOK_URL, DAY_SHORT, directionsUrl, duration, esc, icon, iso, place, placeUrl, weekday } from './format.js';

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
  if (kind !== 'return') {
    if (loc.info.location) lines.push(['key', 'Key', loc.info.location]);
    if (loc.info.parking) lines.push(['parking', 'Car is parked', loc.info.parking]);
  }
  if (kind !== 'pickup' && loc.info.return) lines.push(['door', 'Return', loc.info.return]);
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
  const drive = r.minutes * 60000 / total * 100;
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

function destinationHtml(o, r) {
  return `<a class="rm-dest-item ${o.id === r.id ? 'on' : ''}" href="#route-${esc(o.id)}" data-route-id="${esc(o.id)}" data-line="${esc(o.id)}">
    <span class="dot"></span>
    <span><span class="name">${place(o.route.to, 13)}</span><span class="meta">by ${iso(o.route.latestReturn)}</span></span>
    <span class="km">${o.km} km<span class="meta">${duration(o.minutes)}</span></span></a>`;
}

export function routeItemHtml(id, selectedId) {
  const r = ROUTES[id];
  return `<a class="rm-dest-item ${id === selectedId ? 'on' : ''}" href="#route-${esc(id)}" data-route-id="${esc(id)}" data-line="${esc(id)}">
    <span class="dot"></span>
    <span><span class="name">${place(r.from, 12)}<span class="to">→</span>${place(r.to, 12)}</span><span class="meta">by ${iso(r.latestReturn)} · ${esc(r.car.name || 'Model TBA')}</span></span>
    <span class="km">${r.km} km<span class="meta">${duration(r.minutes)}</span></span></a>`;
}

// The overview's list: the routes visible in the table (or all of them), in table order
export function overviewListHtml(overview, selectedId) {
  const ids = overview.showAll ? overview.all : overview.visible, filtered = overview.visible.length < overview.all.length;
  const toggle = filtered
    ? `<button type="button" class="rm-link" data-show-all>${overview.showAll ? `Only the ${overview.visible.length} filtered` : `Show all ${overview.all.length}`}</button>` : '';
  return `
    <div class="rm-kick">${icon('map', 12)} All available routes</div>
    <h4>${ids.length < overview.all.length ? `${ids.length} of ${overview.all.length} routes` : `${ids.length} routes`} ${toggle}</h4>
    ${ids.map(id => routeItemHtml(id, selectedId)).join('')}
    <div class="hint">Hover to preview on the map, click a route or a station.</div>`;
}

// A trip in three steps (pick up, drive, return), plus where else the same car can go
export function routePanels(r, fromOverview) {
  const showOnMap = target => `<button type="button" data-focus="${target}">${icon('pin', 11, 2.4)} Show on map</button>`;
  const options = destinations(r), others = options.filter(o => o.id !== r.id);
  return {
    head: `
      ${fromOverview ? `<button type="button" class="rm-back" data-zoom="overview">← All routes</button>` : ''}
      <div class="rm-kick">${icon('route', 12)} Your trip</div>
      <div class="rm-title" id="routeModalTitle">${place(r.from, 17)} ${icon('arrow', 17)} ${place(r.to, 17)}</div>
      <div class="rm-chips">${r.availableNow ? '<span class="status-chip open">Available now</span>' : `<span class="status-chip upcoming">From ${iso(r.availableAt)} · ${esc(r.pickupIn)}</span>`}${r.count > 1 ? `<span class="mini-badge twin">×${r.count} identical</span>` : ''}</div>`,
    steps: `
      <section class="rm-step" data-step="a">
        <button type="button" class="rm-mk ring" data-focus="a" title="Show pickup on the map"><span></span></button>
        <div class="rm-k">Step 1 · Pick up ${showOnMap('a')}</div>
        <div class="rm-when">From ${iso(r.availableAt)} <small>${weekday(r.availableAt)}</small>${r.availableNow ? '<span class="now">● Available now</span>' : ''}</div>
        ${stationHtml(r.from, 'pickup', r.availableNow ? new Date() : r.availableAt)}
      </section>
      <section class="rm-step" data-step="ab">
        <button type="button" class="rm-mk car" data-focus="ab" title="Show the route on the map">${icon(r.car.van ? 'bus' : 'car', 16)}</button>
        <div class="rm-k">Step 2 · Drive ${showOnMap('ab')}</div>
        <div class="rm-drive"><div><b>${r.km} km</b><span>distance</span></div><div><b>≈ ${duration(r.minutes)}</b><span>drive time</span></div><div><b>${r.maxKm} km</b><span>max allowed</span></div></div>
        <div class="rm-card">${carHtml(r)}${windowHtml(r)}</div>
      </section>
      <section class="rm-step" data-step="b">
        <button type="button" class="rm-mk pin" data-focus="b" title="Show return on the map"><svg width="24" height="27" viewBox="0 0 24 26" aria-hidden="true"><path d="M12 25s-8-7.4-8-14a8 8 0 0 1 16 0c0 6.6-8 14-8 14z" fill="currentColor"/><circle cx="12" cy="11" r="3.2"/></svg></button>
        <div class="rm-k">Step 3 · Return ${showOnMap('b')}</div>
        <div class="rm-when">By ${iso(r.latestReturn)} <small>${weekday(r.latestReturn)}</small></div>
        ${stationHtml(r.to, 'return', r.latestReturn)}
      </section>
      ${others.length ? `<div class="rm-others"><div class="rm-k">Same car, other destinations</div>${others.map(o => destinationHtml(o, r)).join('')}</div>` : ''}`,
    footer: `
      <a class="btn btn-outline-light btn-sm" href="${directionsUrl(r.from, r.to)}" target="_blank" rel="noopener">${icon('nav', 13)} Directions</a>
      <a class="btn btn-primary btn-sm fw-bold" href="${BOOK_URL}" target="_blank" rel="noopener">Book on Hertz ${icon('external', 13)}</a>`,
    destinations: `
      <div class="rm-kick">${icon('split', 12)} Where this car can go</div>
      <h4>${options.length > 1 ? `${options.length} destinations from ${esc(r.from.short)}` : `Only ${esc(r.to.short)}`}</h4>
      ${options.map(o => destinationHtml(o, r)).join('')}
      <div class="hint">${options.length > 1 ? 'Hover to preview on the map, click to switch.' : 'The car is only offered to this destination.'}</div>`,
  };
}

// Station card: what the station offers and every listed route from and to it
export function stationPanels(st) {
  const loc = st.loc;
  const access = loc.kiosk
    ? `<span class="access ok">${icon('key', 13)} Key kiosk – pick up and return 24/7</span>`
    : `<span class="access no">${icon('clock', 13)} No kiosk – staffed hours only</span>`;
  const section = (title, ids) => `<div class="rm-k rm-station-k">${title} · ${ids.length}</div>`
    + (ids.length ? ids.map(id => routeItemHtml(id, null)).join('') : '<div class="rm-none">None right now</div>');
  return {
    head: `
      <button type="button" class="rm-back" data-zoom="overview">← All routes</button>
      <div class="rm-kick">${icon('pin', 12)} Station</div>
      <div class="rm-title" id="routeModalTitle">${place(loc, 17)}</div>
      <div class="rm-addr">${esc(loc.sub)}${loc.sub && loc.address ? ' · ' : ''}${esc(loc.address)}${loc.city ? ', ' + esc(loc.city) : ''}</div>`,
    steps: `
      <div class="rm-card mt-0">${access}${hoursHtml(loc)}${infoHtml(loc, 'station')}</div>
      ${section('Routes from here', st.from)}
      ${section('Routes to here', st.to)}`,
    footer: `
      <a class="btn btn-outline-light btn-sm" href="${placeUrl(loc)}" target="_blank" rel="noopener">${icon('pin', 13)} Google Maps</a>
      ${loc.phone ? `<a class="btn btn-outline-light btn-sm" href="tel:${esc(loc.phone.replace(/[^+\d]/g, ''))}" title="${esc(loc.phone)}">${icon('phone', 13)} Call</a>` : ''}`,
  };
}
