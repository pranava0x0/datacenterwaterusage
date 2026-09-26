
// ===== Lazily loaded tabs =====
// Only the default tab ships inside index.html. Every other tab is its own
// small page (tab-NAME.html?v=HASH) fetched the first time it is opened — or
// as soon as a reader hovers, focuses or touches its button, so the fetch is
// usually done before the click lands. The page used to parse ~1.5 MB and
// ~15,000 elements up front for tabs most visits never open.
const TAB_ANCHORS = (() => {
  const el = document.getElementById('tab-anchors');
  try { return el ? JSON.parse(el.textContent) : {}; } catch (e) { return {}; }
})();
// Which lazy tab owns an element id — so a link, a shared URL or the Back
// button can reach a card whose tab has not been fetched yet.
const ANCHOR_TAB = {};
Object.keys(TAB_ANCHORS).forEach(tab => TAB_ANCHORS[tab].forEach(id => { ANCHOR_TAB[id] = tab; }));

const panelFetches = {};
function fetchPanel(name){
  const panel = document.getElementById('panel-' + name);
  const src = panel && panel.dataset.src;
  if (!src) return Promise.resolve(null);
  if (!panelFetches[name]){
    panelFetches[name] = fetch(src)
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); })
      .then(text => new DOMParser().parseFromString(text, 'text/html'))
      .catch(err => { delete panelFetches[name]; throw err; });
  }
  return panelFetches[name];
}

const panelReady = {};
function loadPanel(name){
  const panel = document.getElementById('panel-' + name);
  if (!panel) return Promise.reject(new Error('no such tab: ' + name));
  if (!panel.dataset.src) return Promise.resolve(panel);
  if (panelReady[name]) return panelReady[name];
  panel.setAttribute('aria-busy', 'true');
  panelReady[name] = fetchPanel(name).then(doc => {
    const body = doc && doc.getElementById('panel-' + name);
    if (!body) throw new Error('tab page is missing its panel');
    // The standalone page points cross-tab links at sibling files
    // (tab-cwa.html#x) so they work with JavaScript off. In here every tab
    // is one document again, so they go back to plain fragments.
    body.querySelectorAll('a[href]').forEach(a => {
      const m = /^(?:tab-[a-z]+|index)[.]html(#.+)$/.exec(a.getAttribute('href'));
      if (m) a.setAttribute('href', m[1]);
    });
    panel.replaceChildren(...[...body.childNodes].map(n => document.importNode(n, true)));
    delete panel.dataset.src;
    // The parsed page has been copied in; keeping it would hold a second
    // full DOM of the tab for the life of the page. panelReady remembers.
    delete panelFetches[name];
    panel.removeAttribute('aria-busy');
    // Parsed-then-moved scripts never run. Re-create each one so the tab's
    // own inline scripts (its totals, the Explore client) execute in order.
    panel.querySelectorAll('script').forEach(old => {
      if (old.type && old.type !== 'text/javascript') return;
      const fresh = document.createElement('script');
      fresh.textContent = old.textContent;
      old.replaceWith(fresh);
    });
    initPanel(panel);
    return panel;
  }).catch(err => {
    delete panelReady[name];
    panel.removeAttribute('aria-busy');
    const note = document.createElement('p');
    note.className = 'tab-loading tab-failed';
    note.append('This section could not be loaded. ');
    const a = document.createElement('a');
    a.href = 'tab-' + name + '.html';
    a.textContent = 'Open it as its own page';
    note.append(a, ', or reload to try again.');
    panel.replaceChildren(note);
    throw err;
  });
  return panelReady[name];
}

// --- Tabs ---
const tabsBar = document.querySelector('.tabs-bar');
const tabsRow = document.querySelector('.tabs');
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tabpanel');
// The tab that ships inline; Back to the hashless first entry returns here.
const DEFAULT_TAB = ([...tabs].find(t => t.getAttribute('aria-selected') === 'true') || tabs[0] || {dataset: {}}).dataset.tab;
function activateTab(name, fromLink){
  tabs.forEach(x => x.setAttribute('aria-selected', x.dataset.tab === name ? 'true' : 'false'));
  panels.forEach(p => p.hidden = (p.id !== 'panel-' + name));
  scrollTabIntoView(name);
  // A tab is shareable: the address bar names it. Tab-to-tab switches
  // replace the entry, so they do not bury the page under Back-button
  // entries; but leaving a card a link pushed must not overwrite it, or Back
  // would skip the card the reader just visited.
  if (!fromLink){
    const onPanel = !location.hash || location.hash.startsWith('#panel-');
    history[onPanel ? 'replaceState' : 'pushState'](null, '', '#panel-' + name);
  }
  return loadPanel(name).then(panel => {
    // The graph blob is a separate file fetched on first activation.
    if (name === 'explore' && window.exploreInit) window.exploreInit();
    return panel;
  });
}
tabs.forEach(t => {
  t.addEventListener('click', () => { activateTab(t.dataset.tab).catch(() => {}); });
  const warm = () => { fetchPanel(t.dataset.tab).catch(() => {}); };
  t.addEventListener('pointerenter', warm, {once: true});
  t.addEventListener('focus', warm, {once: true});
  t.addEventListener('touchstart', warm, {once: true, passive: true});
});

// The row is one non-wrapping scroller, so the selected chip can be off-screen
// after a cross-tab link. Nudge the scroller itself rather than calling
// scrollIntoView, which would also scroll the page vertically.
function scrollTabIntoView(name){
  if (!tabsRow) return;
  const el = [...tabs].find(t => t.dataset.tab === name);
  if (!el) return;
  const left = el.offsetLeft - tabsRow.offsetLeft;
  const pad = 24;
  if (left < tabsRow.scrollLeft + pad) tabsRow.scrollLeft = Math.max(0, left - pad);
  else if (left + el.offsetWidth > tabsRow.scrollLeft + tabsRow.clientWidth - pad)
    tabsRow.scrollLeft = left + el.offsetWidth - tabsRow.clientWidth + pad;
}

// Edge fade, only while there is something past the edge to fade toward.
function syncTabOverflow(){
  if (!tabsBar || !tabsRow) return;
  const over = tabsRow.scrollWidth > tabsRow.clientWidth + 4;
  tabsBar.classList.toggle('is-scrollable', over);
  tabsBar.classList.toggle('at-end',
    tabsRow.scrollLeft + tabsRow.clientWidth >= tabsRow.scrollWidth - 4);
}
if (tabsRow){
  tabsRow.addEventListener('scroll', syncTabOverflow, {passive: true});
  window.addEventListener('resize', syncTabOverflow);
  syncTabOverflow();
}

// --- Back to top ---
// Two viewport heights: far enough that the sticky bar alone has stopped
// being the answer, close enough to catch a reader mid-card-list.
const toTop = document.getElementById('to-top');
if (toTop){
  const smooth = !(window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  let ticking = false;
  const syncToTop = () => {
    ticking = false;
    toTop.classList.toggle('is-visible', window.scrollY > window.innerHeight * 2);
  };
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(syncToTop);
  }, {passive: true});
  toTop.addEventListener('click', () =>
    window.scrollTo({top: 0, behavior: smooth ? 'smooth' : 'auto'}));
  syncToTop();
}

// --- Card groups ---
// A group is a <details> wrapping part of a filtered card list. After a filter
// runs, each group reports how many of its cards survived, an emptied group
// gets out of the way entirely, and a filter narrow enough to fit on a screen
// or two opens whatever is left — otherwise narrowing to one status could
// leave every match sitting behind a closed summary.
const GROUP_AUTO_OPEN_MAX = 15;
function syncCardGroups(scopeSel, cardSel){
  const groups = [...document.querySelectorAll(scopeSel)];
  if (!groups.length) return;
  const live = groups.map(g => ({
    el: g,
    n: [...g.querySelectorAll(cardSel)].filter(c => !c.hidden).length,
  }));
  const total = live.reduce((sum, g) => sum + g.n, 0);
  live.forEach(g => {
    const badge = g.el.querySelector('.cg-count');
    if (badge) badge.textContent = g.n === 1 ? '1 entry' : g.n + ' entries';
    g.el.hidden = g.n === 0;
    if (g.n && total <= GROUP_AUTO_OPEN_MAX) g.el.open = true;
  });
}

// --- Sub-tabs (Water Cases) ---
// Delegated, so sub-tabs inside a tab that arrives later work without being
// wired up one by one.
function activateSubtab(name){
  const panel = document.getElementById('panel-' + name);
  if (!panel || !panel.parentElement) return;
  const group = panel.parentElement;
  group.querySelectorAll('.subtab').forEach(x =>
    x.setAttribute('aria-selected', x.dataset.subtab === name ? 'true' : 'false'));
  group.querySelectorAll(':scope > .subtabpanel').forEach(p => p.hidden = (p.id !== 'panel-' + name));
}
document.addEventListener('click', e => {
  const t = e.target.closest('.subtab');
  if (t) activateSubtab(t.dataset.subtab);
});

// ===== Per-tab behaviour, run when a tab's content arrives =====
// Each function wires up the controls inside one tab. The default tab runs at
// load; the rest run the moment their page has been fetched and inserted.
// Their state lives out here because the link handler below resets a filter
// that is hiding a link's target.
let legChecks = [], applyLegFilter = () => {};
let issueChecks = [], applyIssueFilter = () => {};
let cwaCatChecks = [], cwaTypeChecks = [], cwaStatuteChecks = [], applyCwaFilter = () => {};

function initLegislation(){
  // Node lists are cached once: the cards are static, and re-querying the DOM
  // on every checkbox change costs needless reflow work on low-end mobile.
  const legCount = document.getElementById('leg-count');
  const legBills = [...document.querySelectorAll('.leg-bill')];
  legChecks = [...document.querySelectorAll('.leg-status, .leg-level, .leg-scope, .leg-principle, .leg-instrument')];
  applyLegFilter = function(){
    const statuses = new Set(), levels = new Set(), scopes = new Set(),
          prins = new Set(), instruments = new Set();
    legChecks.forEach(c => {
      if (!c.checked) return;
      if (c.classList.contains('leg-status')) statuses.add(c.value);
      else if (c.classList.contains('leg-level')) levels.add(c.value);
      else if (c.classList.contains('leg-scope')) scopes.add(c.value);
      else if (c.classList.contains('leg-instrument')) instruments.add(c.value);
      else prins.add(c.value);
    });
    const counts = {};
    let shown = 0;
    legBills.forEach(el => {
      const sc = (el.dataset.scope || '').split(' ').filter(Boolean);
      const pr = (el.dataset.principles || '').split(' ').filter(Boolean);
      const ok = statuses.has(el.dataset.status) && levels.has(el.dataset.level) &&
        sc.some(s => scopes.has(s)) && pr.some(p => prins.has(p)) &&
        instruments.has(el.dataset.instrument || 'bill');
      el.hidden = !ok;
      if (ok){ shown++; counts[el.dataset.status] = (counts[el.dataset.status]||0)+1; }
    });
    const lOrder = window.LEG_STATUS_ORDER || {}, lLabels = window.LEG_STATUS_LABELS || {};
    const lSummary = Object.keys(counts).sort((a,b)=>(lOrder[a]??9)-(lOrder[b]??9))
      .map(k => counts[k] + ' ' + (lLabels[k]||k)).join(' · ');
    // "instruments", not "bills": many are executive orders, agency rules,
    // commission dockets and local ordinances.
    const legStrong = document.createElement('strong');
    legStrong.textContent = 'Showing ' + shown + ' of ' + window.LEG_TOTAL + ' instruments';
    legCount.replaceChildren(legStrong);
    if (lSummary) legCount.append(' — ' + lSummary);
    syncCardGroups('#leg-bills .card-group', '.leg-bill');
  };
  legChecks.forEach(c => c.addEventListener('change', applyLegFilter));
  if (legCount) applyLegFilter();
}

function initIssues(){
  // Part 4 conflict-site filtering by issue type.
  const conflictCount = document.getElementById('conflict-count');
  const dcSites = [...document.querySelectorAll('.dc-site')];
  issueChecks = [...document.querySelectorAll('.dc-issue')];
  applyIssueFilter = function(){
    const picked = new Set(issueChecks.filter(c => c.checked).map(c => c.value));
    // Matches can sit behind the "remaining sites" fold; a filter that appears
    // to match nothing is worse than a long list. Only once the reader has
    // actually narrowed something — this also runs on load, with everything on.
    const sitesFold = document.getElementById('sites-fold');
    if (sitesFold && picked.size < issueChecks.length) sitesFold.open = true;
    let shown = 0;
    dcSites.forEach(el => {
      // A site carries 1-3 tags and matches if ANY is picked — the tags are
      // facets of one conflict, not alternatives.
      const tags = (el.dataset.issues || '').split(' ').filter(Boolean);
      const ok = tags.some(t => picked.has(t));
      el.hidden = !ok;
      if (ok) shown++;
    });
    if (conflictCount){
      const strong = document.createElement('strong');
      strong.textContent = 'Showing ' + shown + ' of ' + dcSites.length + ' sites';
      conflictCount.replaceChildren(strong);
    }
  };
  issueChecks.forEach(c => c.addEventListener('change', applyIssueFilter));
  if (conflictCount) applyIssueFilter();
}

function initCwa(){
  const cwaCount = document.getElementById('cwa-count');
  const cwaCases = [...document.querySelectorAll('.cwa-case')];
  const recent = document.getElementById('cwa-recent');
  cwaCatChecks = [...document.querySelectorAll('.cwa-cat')];
  cwaTypeChecks = [...document.querySelectorAll('.cwa-type')];
  cwaStatuteChecks = [...document.querySelectorAll('.cwa-statute')];
  applyCwaFilter = function(){
    const cats = new Set(cwaCatChecks.filter(c => c.checked).map(c => c.value));
    const types = new Set(cwaTypeChecks.filter(c => c.checked).map(c => c.value));
    const statutes = new Set(cwaStatuteChecks.filter(c => c.checked).map(c => c.value));
    const onlyRecent = recent && recent.checked;
    const counts = {};
    let shown = 0;
    cwaCases.forEach(el => {
      const cat = el.dataset.category;
      const ye = parseInt(el.dataset.yearend, 10) || 0;
      const caseStatutes = (el.dataset.statutes || '').split(' ');
      const ok = cats.has(cat) && types.has(el.dataset.casetype)
        && caseStatutes.some(s => statutes.has(s))
        && (!onlyRecent || ye >= 2020);
      el.hidden = !ok;
      if (ok){ shown++; counts[cat] = (counts[cat]||0)+1; }
    });
    const order = window.CWA_CAT_ORDER || {};
    const labels = window.CWA_CAT_LABELS || {};
    const summary = Object.keys(counts)
      .sort((a,b)=>(order[a]??9)-(order[b]??9))
      .map(k => counts[k] + ' ' + (labels[k]||k)).join(' · ');
    cwaCount.innerHTML = '<strong>Showing ' + shown + ' of ' + window.CWA_TOTAL +
      ' cases</strong>' + (summary ? ' — ' + summary : '');
    syncCardGroups('#cwa-cases .card-group', '.cwa-case');
  };
  [...cwaCatChecks, ...cwaTypeChecks, ...cwaStatuteChecks, recent].forEach(c =>
    c && c.addEventListener('change', applyCwaFilter));
  if (cwaCount) applyCwaFilter();
}

function initStates(){
  // County & city action filters. One <select> for 35 states rather than 35
  // chips; status and action type stay checkboxes to match every other row.
  const laCount = document.getElementById('la-count');
  const laRows = [...document.querySelectorAll('#local-actions-table tbody tr')];
  const laStatusChecks = [...document.querySelectorAll('.la-status')];
  const laTypeChecks = [...document.querySelectorAll('.la-type')];
  const laState = document.getElementById('la-state');
  const laWater = document.getElementById('la-water');
  function applyLocalActionFilter(){
    const statuses = new Set(laStatusChecks.filter(c => c.checked).map(c => c.value));
    const types = new Set(laTypeChecks.filter(c => c.checked).map(c => c.value));
    const state = laState ? laState.value : '';
    const waterOnly = laWater ? laWater.checked : false;
    let shown = 0;
    laRows.forEach(tr => {
      const ok = statuses.has(tr.dataset.status) && types.has(tr.dataset.type)
        && (!state || tr.dataset.state === state)
        && (!waterOnly || tr.dataset.water === '1');
      tr.hidden = !ok;
      if (ok) shown++;
    });
    if (laCount){
      const strong = document.createElement('strong');
      strong.textContent = 'Showing ' + shown + ' of ' + (window.LA_TOTAL || laRows.length) + ' actions';
      laCount.replaceChildren(strong);
    }
  }
  [...laStatusChecks, ...laTypeChecks, laState, laWater].forEach(c =>
    c && c.addEventListener('change', applyLocalActionFilter));
  if (laCount) applyLocalActionFilter();
}

function initNews(){
  const newsCount = document.getElementById('news-count');
  const newsBoxes = [...document.querySelectorAll('.news-tag-filter')];
  function applyNewsFilter(){
    const active = new Set(newsBoxes.filter(c => c.checked).map(c => c.value));
    let shown = 0;
    document.querySelectorAll('#news-cards .news-card').forEach(el => {
      const tags = el.dataset.tags ? el.dataset.tags.split(',') : [];
      const ok = active.size === 0 || tags.some(t => active.has(t));
      el.hidden = !ok;
      if (ok) shown++;
    });
    if (newsCount){
      const strong = document.createElement('strong');
      strong.textContent = shown + ' items';
      newsCount.replaceChildren(strong);
    }
    // A topic filter that matches nothing in the first twelve headlines would
    // otherwise look like it matched nothing at all.
    const newsFold = document.getElementById('news-fold');
    if (newsFold && active.size < newsBoxes.length) newsFold.open = true;
  }
  newsBoxes.forEach(c => c.addEventListener('change', applyNewsFilter));
}

const PANEL_INIT = {
  legislation: initLegislation,
  issues: initIssues,
  cwa: initCwa,
  states: initStates,
  news: initNews,
};
function initPanel(panel){
  // Collapsed-by-default groups and folds are in the markup as
  // <details open data-collapsed="1"> so a reader with no JavaScript gets every
  // card; the CSS hides their bodies from first paint (html.js is stamped in
  // <head>), and this closes them for real.
  panel.querySelectorAll('details[data-collapsed]').forEach(d => {
    d.open = false;
    d.removeAttribute('data-collapsed');
  });
  const init = PANEL_INIT[panel.id.replace('panel-', '')];
  if (init) init(panel);
}
document.querySelectorAll('.tabpanel:not([data-src])').forEach(initPanel);

// ===== In-page links, deep links and the Back button =====
// Bill / case / reading / site anchors can live on ANOTHER tab — possibly one
// not fetched yet — in another Water Cases sub-tab, inside a collapsed
// <details>, or behind an active filter. navigateTo fetches the owning tab if
// it has to, switches to it and its sub-tab, opens ancestor <details>, resets
// a filter that hides the target, then scrolls to it itself (the browser's own
// fragment jump cannot cross a hidden or not-yet-loaded tab).
function navigateTo(id, push){
  const target = document.getElementById(id);
  if (!target){
    const tab = ANCHOR_TAB[id];
    if (!tab) return false;
    activateTab(tab, true).then(() => navigateTo(id, push)).catch(() => {});
    return true;
  }
  if (target.classList.contains('tabpanel')){
    const name = target.id.replace('panel-', '');
    activateTab(name, true).catch(() => {});
    if (push) history.pushState(null, '', '#' + id);
    (tabsBar || target).scrollIntoView({block: 'start'});
    return true;
  }
  const panel = target.closest('.tabpanel');
  if (panel && panel.hidden) activateTab(panel.id.replace('panel-', ''), true).catch(() => {});
  const subpanel = target.closest('.subtabpanel');
  if (subpanel && subpanel.hidden) activateSubtab(subpanel.id.replace('panel-', ''));
  // Anchors inside a collapsed <details> can't be scrolled to in all
  // browsers — open the ancestors first, or the target itself if it is one.
  if (target.tagName === 'DETAILS') target.open = true;
  let det = target.closest('details');
  while (det) { det.open = true; det = det.parentElement && det.parentElement.closest('details'); }
  const wrap = target.closest('.leg-bill, .cwa-case, .dc-site');
  if (wrap && wrap.hidden) {
    if (wrap.classList.contains('leg-bill')) {
      legChecks.forEach(c => { c.checked = true; });
      applyLegFilter();
    } else if (wrap.classList.contains('dc-site')) {
      // Conflict cards are .bill-card.dc-site, so they fell through to the
      // CWA branch and were never unhidden — every doctrine-matrix row links
      // here, and the matrix sits directly above the filter that hides them.
      issueChecks.forEach(c => { c.checked = true; });
      applyIssueFilter();
    } else {
      [...cwaCatChecks, ...cwaTypeChecks, ...cwaStatuteChecks].forEach(c => { c.checked = true; });
      const recent = document.getElementById('cwa-recent');
      if (recent) recent.checked = false;
      applyCwaFilter();
    }
  }
  // Preserve fragment/history semantics the native jump would have given:
  // the URL is shareable and Back returns here.
  if (push) history.pushState(null, '', '#' + id);
  target.scrollIntoView({behavior: 'smooth', block: 'start'});
  return true;
}

// A shared URL can carry a malformed escape (a truncated %E2 from a chat
// app); decodeURIComponent would throw and abort the script.
function hashId(raw){
  try { return decodeURIComponent(raw); } catch (e) { return raw; }
}

document.addEventListener('click', e => {
  // Respect modifier/middle clicks (new tab, etc.) — let the browser handle them.
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  // Prefix-agnostic: any in-page anchor whose target exists — or will, once
  // its tab loads — gets the cross-tab treatment.
  const a = e.target.closest('a[href^="#"]');
  if (!a || a.getAttribute('href').length < 2) return;
  const id = hashId(a.getAttribute('href').slice(1));
  if (id === 'top' || (!document.getElementById(id) && !ANCHOR_TAB[id])) return;
  e.preventDefault();
  navigateTo(id, true);
});

// Back/Forward between cards visited through links, and a URL someone shared.
window.addEventListener('popstate', () => {
  if (location.hash.length > 1) navigateTo(hashId(location.hash.slice(1)), false);
  // Back to the first, hashless entry: the page opened on the default tab.
  else if (DEFAULT_TAB) activateTab(DEFAULT_TAB, true).catch(() => {});
});
if (location.hash.length > 1) navigateTo(hashId(location.hash.slice(1)), false);

// --- Records table state filter (dormant Data tab; inert while it is off) ---
const recCount = document.getElementById('rec-count');
function applyRecFilter(){
  const states = new Set([...document.querySelectorAll('.rec-state:checked')].map(c => c.value));
  let shown = 0, total = 0;
  document.querySelectorAll('#rec-table tbody tr').forEach(tr => {
    total++;
    const ok = states.has(tr.dataset.state);
    tr.hidden = !ok;
    if (ok) shown++;
  });
  if (recCount) recCount.innerHTML = '<strong>' + shown + ' of ' + total + ' records</strong>';
}
document.querySelectorAll('.rec-state').forEach(c => c.addEventListener('change', applyRecFilter));
if (recCount) applyRecFilter();
