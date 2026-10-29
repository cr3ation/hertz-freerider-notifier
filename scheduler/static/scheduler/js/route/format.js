/* Formatting for the route window's panels: escaping, icons, dates and links. */

const SPRITE = document.getElementById('routeModal')?.dataset.icons || '';

export const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// An outline icon from the sprite (static/scheduler/icons.svg), like {% icon %} in the templates
export const icon = (name, size, width) =>
  `<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${width || 2}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="${SPRITE}#${name}"></use></svg>`;

export const place = (loc, size) => esc(loc.short) + (loc.airport ? `<span class="ico-plane" title="Airport">${icon('plane', size)}</span>` : '');

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
export const DAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export const iso = s => s.replace('T', ' ');
export const weekday = s => DAYS[new Date(s).getDay()];
// 137 -> "2h 17m", as format_duration in presentation.py
export const duration = minutes => {
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return h ? (m ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
};

export const placeUrl = l => `https://www.google.com/maps/search/?api=1&query=${l.lat},${l.lon}`;
export const directionsUrl = (a, b) => `https://www.google.com/maps/dir/?api=1&origin=${a.lat},${a.lon}&destination=${b.lat},${b.lon}&travelmode=driving`;
export const BOOK_URL = 'https://www.hertzfreerider.se/sv-se/';
