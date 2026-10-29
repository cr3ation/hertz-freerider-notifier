/* The dashboard's lists: tabs on phones, tooltips, the filters for live availability and the history,
 * the "Top" buttons and confirming a delete. A module, so it runs once the page is parsed (after Bootstrap). */

// Phones show one section at a time; the view marks the first one active
document.querySelectorAll('.mobile-tabs .nav-link').forEach((button, _, buttons) => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.dashboard-section').forEach(s => s.classList.toggle('active', s.id === button.dataset.target));
    buttons.forEach(b => {
      b.classList.toggle('active', b === button);
      b.setAttribute('aria-selected', b === button ? 'true' : 'false');
    });
  });
});

// Hover tooltips on desktop. On touch screens a tap would leave them open, so they are left out there.
const touch = 'ontouchstart' in window || window.matchMedia('(pointer: coarse)').matches;
document.querySelectorAll('[data-bs-title]').forEach(el => {
  if (touch) el.removeAttribute('data-bs-toggle');
  else new bootstrap.Tooltip(el, { delay: { show: 1500, hide: 100 }, trigger: 'hover' });
});

/**
 * Filters a list's rows with a search box. A row matches when its text or data-search (which has the full
 * station names, e.g. "Stockholm Centralstation") contains the term, and keep(row) agrees.
 * Returns apply(), for when what keep() looks at changes.
 */
function createListFilter({ rows, search, keep = () => true, onApply }) {
  const apply = () => {
    const term = search.value.trim().replace(/\s+/g, ' ').toLowerCase();
    let visible = 0;
    rows.forEach(row => {
      const text = `${row.dataset.search || ''} | ${row.innerText}`.toLowerCase();
      const show = (!term || text.includes(term)) && keep(row);
      row.style.display = show ? '' : 'none';
      if (show) visible += 1;
    });
    onApply(visible, rows.length);
  };
  search.addEventListener('input', apply);
  apply();
  return apply;
}

const live = document.getElementById('liveSearch');
if (live) {
  const matchesButton = document.getElementById('toggleShowMatches');
  let onlyMatches = false;
  const applyLive = createListFilter({
    rows: [...document.querySelectorAll('.live-availability-table tbody tr.route-row')],
    search: live,
    keep: row => !onlyMatches || row.classList.contains('has-match'),
    onApply: (visible, total) => {
      document.getElementById('liveVisibleCount').textContent = `${visible} / ${total}`;
      matchesButton.classList.toggle('filter-active', onlyMatches);
    },
  });
  matchesButton.addEventListener('click', () => {
    onlyMatches = !onlyMatches;
    applyLive();
  });
  document.getElementById('resetFilters').addEventListener('click', () => {
    onlyMatches = false;
    live.value = '';
    applyLive();
  });
}

const historySearch = document.getElementById('histSearch');
if (historySearch) {
  const range = document.getElementById('histTime');
  const MAX_AGE = { '24h': 24 * 3600 * 1000, '7d': 7 * 24 * 3600 * 1000 };
  const applyHistory = createListFilter({
    rows: [...document.querySelectorAll('#histBody tr[data-notified]')],
    search: historySearch,
    keep: row => !MAX_AGE[range.value] || Date.now() - new Date(row.dataset.notified) <= MAX_AGE[range.value],
    onApply: visible => {
      document.getElementById('histCount').textContent = visible;
    },
  });
  range.addEventListener('change', applyHistory);
  document.getElementById('histReset').addEventListener('click', () => {
    historySearch.value = '';
    range.value = 'all';
    applyHistory();
  });
}

// "Top" scrolls a list back up: inside its box on desktop, the page to the list's card on phones
[['scrollTopLive', '.live-table-wrapper'], ['histScrollTop', '.history-wrapper']].forEach(([id, selector]) => {
  const button = document.getElementById(id), box = document.querySelector(selector);
  if (!button || !box) return;
  button.addEventListener('click', () => {
    if (box.scrollHeight > box.clientHeight) box.scrollTo({ top: 0, behavior: 'smooth' });
    else box.closest('.glass-card').scrollIntoView({ behavior: 'smooth' });
  });
});

// Forms with data-confirm (deleting a search) ask first
document.addEventListener('submit', e => {
  const question = e.target.dataset.confirm;
  if (question && !window.confirm(question)) e.preventDefault();
});
