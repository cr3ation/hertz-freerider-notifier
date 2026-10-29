/* The routes from the view (json_script "route-details-data"): each station once, keyed by its Hertz
 * tracCode, routes keyed by id and pointing at their stations, and aliases for identical cars' other ride ids.
 * Here each route gets its station objects back, so the rest can use r.from and r.to directly. */

const el = document.getElementById('route-details-data');
const DATA = el ? JSON.parse(el.textContent) : { stations: {}, routes: {}, aliases: {} };

export const ROUTES = {};
Object.entries(DATA.routes).forEach(([id, r]) => { ROUTES[id] = { ...r, from: DATA.stations[r.from], to: DATA.stations[r.to] }; });

// A notification links to its first ride, which may be an identical car listed under another row
export const findRoute = id => ROUTES[id] || ROUTES[DATA.aliases[id]];

export const hasCoords = r => [r.from.lat, r.from.lon, r.to.lat, r.to.lon].every(v => typeof v === 'number');
export const ll = loc => [loc.lat, loc.lon];

// The car's current destination plus the alternatives (same transportOfferId), nearest first
export function destinations(r) {
  return [{ id: r.id, km: r.km, minutes: r.minutes, route: r }]
    .concat(r.alternatives.filter(x => ROUTES[x.id]).map(x => ({ ...x, route: ROUTES[x.id] })))
    .sort((a, b) => a.km - b.km);
}
