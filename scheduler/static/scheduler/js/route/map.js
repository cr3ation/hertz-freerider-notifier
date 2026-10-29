/* The Leaflet map behind the panels: one route with the car's other destinations, or every route with its
 * stations. main.js decides what to draw; the click handlers it passes in (on.open etc.) lead back there. */

import { ROUTES, hasCoords, ll } from './data.js';
import { esc } from './format.js';

let map = null, layer = null, lines = {}, arrows = {}, bounds = null;
// The overview's stations, keyed by Hertz tracCode: { loc, from: [route ids], to: [route ids], marker }
export const stations = new Map();

// Side panels from Bootstrap's lg breakpoint, as in route-modal.css; below it the steps are a bottom sheet
export const wide = () => window.matchMedia('(min-width: 992px)').matches;

function ensureMap() {
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
}

// A → B with labels, and a thin line to every other destination of the same car. False without coordinates.
export function drawRoute(r, on) {
  ensureMap();
  lines = {};
  bounds = null;
  if (!hasCoords(r)) {
    map.setView([62, 15], 5);
    return false;
  }
  const a = ll(r.from), b = ll(r.to), points = [a, b];
  const pin = (letter, cls) => L.divIcon({ className: '', html: `<div class="pin-ab ${cls}"><span>${letter}</span></div>`, iconSize: [30, 30], iconAnchor: [15, 30] });
  const label = (text, cls) => L.divIcon({ className: '', html: `<span class="map-lbl ${cls || ''}">${esc(text)}</span>`, iconSize: null, iconAnchor: [-20, 26] });
  r.alternatives.forEach(x => {
    const alt = ROUTES[x.id];
    if (!alt || !hasCoords(alt)) return;
    const p = ll(alt.to);
    points.push(p);
    lines[x.id] = L.polyline([a, p], { color: '#6c757d', weight: 2, dashArray: '4 6' }).addTo(layer).on('click', () => on.open(x.id));
    L.circleMarker(p, { radius: 6, color: '#fff', weight: 2, fillColor: '#6c757d', fillOpacity: 1 }).addTo(layer).on('click', () => on.open(x.id))
      .on('mouseover', () => on.highlight(x.id, true)).on('mouseout', () => on.highlight(x.id, false));
    L.marker(p, { icon: label(`${alt.to.short} · ${x.km} km`, 'alt'), interactive: false }).addTo(layer);
  });
  L.polyline([a, b], { color: '#ffb347', weight: 9, opacity: .5 }).addTo(layer);
  L.polyline([a, b], { color: '#212529', weight: 3, dashArray: '8 6' }).addTo(layer);
  L.marker(a, { icon: pin('A', 'a'), zIndexOffset: 900 }).addTo(layer).on('click', () => on.focus('a', true));
  L.marker(b, { icon: pin('B', 'b'), zIndexOffset: 900 }).addTo(layer).on('click', () => on.focus('b', true));
  L.marker(a, { icon: label(r.from.short), interactive: false }).addTo(layer);
  L.marker(b, { icon: label(`${r.to.short} · ${r.km} km`), interactive: false }).addTo(layer);
  bounds = { ab: L.latLngBounds([a, b]), all: L.latLngBounds(points) };
  return true;
}

// A chevron 60 % of the way to the destination, so a return trip's arrow lands elsewhere on the same line.
// The angle is taken in projected (Mercator) pixels, which keep their direction at every zoom level.
function arrowMarker(r) {
  const a = map.project(ll(r.from), 0), b = map.project(ll(r.to), 0);
  const deg = Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI;
  const at = map.unproject(a.add(b.subtract(a).multiplyBy(.6)), 0);
  return L.marker(at, { interactive: false, icon: L.divIcon({ className: '', iconSize: [16, 16], iconAnchor: [8, 8],
    html: `<div class="rm-arrow" style="transform:rotate(${deg}deg)"><svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 1.5 13 7 2 12.5 5 7z"/></svg></div>` }) });
}

// Every listed route as a thin line between its stations; each station is one dot
export function drawOverview(ids, on, padding, animate) {
  ensureMap();
  lines = {};
  arrows = {};
  bounds = null;
  const points = [];
  stations.clear();
  ids.forEach(id => {
    const r = ROUTES[id];
    if (!hasCoords(r)) return;
    const a = ll(r.from), b = ll(r.to);
    points.push(a, b);
    lines[id] = L.polyline([a, b], { color: '#6c757d', weight: 2, dashArray: '4 6' }).addTo(layer)
      .bindTooltip(`${esc(r.from.short)} → ${esc(r.to.short)} · ${r.km} km`, { sticky: true })
      .on('click', () => on.open(id)).on('mouseover', () => on.highlight(id, true)).on('mouseout', () => on.highlight(id, false));
    arrows[id] = arrowMarker(r).addTo(layer);
    [[r.from, 'from'], [r.to, 'to']].forEach(([loc, side]) => {
      if (!stations.has(loc.code)) stations.set(loc.code, { loc, from: [], to: [] });
      stations.get(loc.code)[side].push(id);
    });
  });
  stations.forEach((st, code) => {
    st.marker = L.circleMarker(ll(st.loc), { radius: 5, color: '#fff', weight: 2, fillColor: '#343a40', fillOpacity: 1 }).addTo(layer)
      .bindTooltip(`${esc(st.loc.short)} · ${st.from.length} leaving · ${st.to.length} arriving · click for details`)
      .on('click', () => on.showStation(code));
  });
  if (!points.length) {
    map.setView([62, 15], 5);
    return;
  }
  bounds = { overview: L.latLngBounds(points) };
  const options = Object.assign({ maxZoom: 11 }, padding);
  if (animate) map.flyToBounds(bounds.overview, Object.assign({ duration: .7 }, options)); else map.fitBounds(bounds.overview, options);
}

// Hover lights a line up; the routes of the open station card stay marked
export function highlight(id, on, stationCode) {
  const line = lines[id];
  if (!line) return;
  const st = stationCode && stations.get(stationCode);
  const marked = st && (st.from.includes(id) || st.to.includes(id));
  line.setStyle(on ? { color: '#ffb347', weight: 5, dashArray: null }
    : marked ? { color: '#e69a2e', weight: 3, dashArray: null } : { color: '#6c757d', weight: 2, dashArray: '4 6' });
  if (on) line.bringToFront();
  const arrow = arrows[id] && arrows[id].getElement();
  if (arrow) arrow.firstChild.classList.toggle('on', !!(on || marked));
}

// Mark a station and its routes, and zoom to them
export function showStation(code, padding) {
  const st = stations.get(code);
  Object.keys(lines).forEach(id => highlight(id, false, code));
  stations.forEach(other => other.marker.setStyle(other === st ? { radius: 8, fillColor: '#ffb347' } : { radius: 5, fillColor: '#343a40' }));
  st.marker.bringToFront();
  const points = [ll(st.loc)];
  st.from.concat(st.to).forEach(id => { points.push(ll(ROUTES[id].from), ll(ROUTES[id].to)); });
  map.flyToBounds(L.latLngBounds(points), Object.assign({ maxZoom: 9, duration: .7 }, padding));
}

// Zoom to the pickup (a), the return (b), the route (ab) or every destination of the car (all)
export function zoomTo(target, r, padding, animate = true) {
  if (!bounds) return;
  if (target === 'a' || target === 'b') {
    map.flyTo(ll(target === 'a' ? r.from : r.to), 15, { duration: .7 });
    map.once('moveend', () => map.panBy(wide() ? [-160, 0] : [0, window.innerHeight * .28]));
  } else {
    const options = Object.assign({ maxZoom: 11 }, padding);
    const box = target === 'all' ? bounds.all : bounds.ab;
    if (animate) map.flyToBounds(box, Object.assign({ duration: .7 }, options)); else map.fitBounds(box, options);
  }
}
