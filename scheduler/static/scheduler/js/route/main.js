/* Route details for the dashboard.
 *
 * Clicking anything with a data-route-id (a live table row, a listed notification) opens a Bootstrap modal
 * that is a full-window Leaflet map (A = pickup, B = return) with floating glass panels: the trip as three
 * steps on the left and every destination the same car can be returned to on the right. Steps and map are
 * linked: a step zooms the map, A/B scrolls to the step. The "Map" button opens the same window as an
 * overview of every route visible in the table; picking one shows its steps while the list of all routes
 * stays on the right. Clicking a station shows a station card with the routes from and to it.
 *
 * Modules: data.js (the routes from the view), format.js, panels.js (the panels' HTML), map.js (Leaflet).
 */

import { ROUTES, destinations, findRoute, hasCoords } from './data.js';
import { icon } from './format.js';
import * as maps from './map.js';
import { overviewListHtml, routePanels, stationPanels } from './panels.js';

const modalEl = document.getElementById('routeModal');
if (modalEl && window.bootstrap && window.L) init();

function init() {
  const modal = new bootstrap.Modal(modalEl);
  const $ = id => document.getElementById(id);

  // What the window shows. mode: 'route' (a trip's steps), 'overview' (every route) or 'station' (a station
  // card). overview holds the overview's route lists while the window was opened with the Map button, so a
  // route or station opened from there can go back to it.
  const state = { mode: null, current: null, station: null, overview: null };
  const handlers = { open, focus, highlight, showStation };

  // Keep A and B clear of the floating panels (side by side on wide screens, panel at the bottom on phones)
  // (the overview has no labels, so it needs no room for them on the right)
  const padding = () => {
    const listOnly = state.mode === 'overview';
    return maps.wide()
      ? { paddingTopLeft: [listOnly ? 40 : 470, 70], paddingBottomRight: [state.overview ? 380 : 330, 50] }
      : { paddingTopLeft: [40, 70], paddingBottomRight: [listOnly ? 40 : 150, window.innerHeight * .62] };
  };

  const setPanels = ({ head, steps, footer }) => {
    $('routeHead').innerHTML = head;
    $('routeSteps').innerHTML = steps;
    $('routeSteps').scrollTop = 0;
    $('routeFooter').innerHTML = footer;
  };

  // Route / A / B / All destinations belong to a route; "All routes" only exists with the overview
  function updateTools() {
    const hasAlternatives = state.mode === 'route' && destinations(state.current).length > 1;
    $('routeTools').querySelectorAll('[data-zoom]').forEach(btn => {
      const zoom = btn.dataset.zoom;
      btn.hidden = zoom === 'overview' ? !state.overview : state.mode !== 'route' || (zoom === 'all' && !hasAlternatives);
    });
  }

  // Put the panels for the current state in place, then draw the map (once the window is shown)
  function render(animate) {
    modalEl.classList.toggle('is-overview', state.mode === 'overview');
    modalEl.classList.toggle('has-overview', !!state.overview);
    if (state.mode === 'route') {
      const panels = routePanels(state.current, !!state.overview);
      setPanels(panels);
      $('routeDestinations').innerHTML = state.overview ? overviewListHtml(state.overview, state.current.id) : panels.destinations;
    } else if (state.mode === 'station') {
      setPanels(stationPanels(maps.stations.get(state.station)));
    } else {
      $('routeDestinations').innerHTML = overviewListHtml(state.overview, null);
      $('routeDestinations').scrollTop = 0;
    }
    updateTools();
    if (modalEl.classList.contains('show')) drawMap(animate); else modal.show();
  }

  function drawMap(animate) {
    if (state.mode === 'route') {
      $('routeTools').hidden = !maps.drawRoute(state.current, handlers);
      focus(state.current.alternatives.length ? 'all' : 'ab', false, animate);
    } else if (state.mode === 'station') {
      maps.showStation(state.station, padding());
    } else {
      $('routeTools').hidden = false;
      maps.drawOverview(state.overview.showAll ? state.overview.all : state.overview.visible, handlers, padding(), animate);
    }
  }

  function open(id) {
    const r = findRoute(id);
    if (!r) return;
    Object.assign(state, { mode: 'route', current: r, station: null });
    render(true);
  }

  // The overview lists the routes the table shows (its filters apply) and can show all of them
  function openOverview() {
    const known = Array.from(document.querySelectorAll('.live-availability-table tbody tr.route-row')).filter(row => ROUTES[row.dataset.routeId]);
    state.overview = {
      all: known.map(row => row.dataset.routeId),
      visible: known.filter(row => row.style.display !== 'none').map(row => row.dataset.routeId),
      showAll: false,
    };
    showOverview(false);
  }

  function showOverview(animate) {
    Object.assign(state, { mode: 'overview', current: null, station: null });
    render(animate);
  }

  // The station card replaces the steps; the map keeps the overview and marks the station's routes
  function showStation(code) {
    if (!maps.stations.has(code)) return;
    Object.assign(state, { mode: 'station', station: code });
    render(true);
  }

  function highlight(id, on) {
    maps.highlight(id, on, state.mode === 'station' ? state.station : null);
  }

  // Step 1 → A, step 2 → the route, step 3 → B; clicking A or B on the map scrolls to that step
  function focus(target, scrollPanel, animate = true) {
    if (target === 'overview') return state.mode === 'overview' ? drawMap(true) : showOverview(true);
    $('routeTools').querySelectorAll('[data-zoom]').forEach(btn => btn.classList.toggle('on', btn.dataset.zoom === target));
    $('routeSteps').querySelectorAll('.rm-step').forEach(s => s.classList.toggle('on', s.dataset.step === target));
    if (scrollPanel) {
      const step = $('routeSteps').querySelector(`[data-step="${target}"]`);
      if (step) $('routeSteps').scrollTo({ top: step.offsetTop - 12, behavior: 'smooth' });
    }
    if (state.mode === 'route' && hasCoords(state.current)) maps.zoomTo(target, state.current, padding(), animate);
  }

  $('routeTools').innerHTML = `
    <button type="button" data-zoom="ab">${icon('route', 13)}<span>Route</span></button>
    <button type="button" data-zoom="a">A<span> · Pickup</span></button>
    <button type="button" data-zoom="b">B<span> · Return</span></button>
    <button type="button" data-zoom="all">${icon('maximize', 13)}<span>All destinations</span></button>
    <button type="button" data-zoom="overview">${icon('map', 13)}<span>All routes</span></button>`;
  modalEl.addEventListener('shown.bs.modal', () => drawMap(false));
  // Next time a table row is clicked the window opens as plain route details again
  modalEl.addEventListener('hidden.bs.modal', () => {
    state.overview = null;
    state.station = null;
    modalEl.classList.remove('is-overview', 'has-overview');
  });
  $('routeHead').addEventListener('click', e => {
    if (e.target.closest('[data-zoom="overview"]')) showOverview(true);
  });
  // "Show all" / "Only the filtered": a route keeps its map, the overview (and a station card) draws again
  $('routeDestinations').addEventListener('click', e => {
    if (!e.target.closest('[data-show-all]')) return;
    state.overview.showAll = !state.overview.showAll;
    if (state.mode === 'route') $('routeDestinations').innerHTML = overviewListHtml(state.overview, state.current.id);
    else showOverview(true);
  });
  const mapButton = document.getElementById('openRouteMap');
  if (mapButton) mapButton.addEventListener('click', openOverview);
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
  // Hovering a route in a list (right panel or station card) previews its line
  [$('routeDestinations'), $('routeSteps')].forEach(list => {
    list.addEventListener('mouseover', e => {
      const item = e.target.closest('[data-line]');
      if (item) highlight(item.dataset.line, true);
    });
    list.addEventListener('mouseout', e => {
      const item = e.target.closest('[data-line]');
      if (item && !item.contains(e.relatedTarget)) highlight(item.dataset.line, false);
    });
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
  else if (location.hash === '#map') openOverview();
}
