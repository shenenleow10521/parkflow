// Entry point: wires the DOM, the shared store, the 3D scene and the simulation clock.

import { store, on, emit, resetSim, setScenario, runMatchedComparison, persist, toast, Section } from './ui/store';
import { $, $$, esc, icon, prefersReducedMotion, loadJSON, saveJSON } from './ui/dom';
import { Scene3D } from './render/scene3d';
import { GLScene, SceneView } from './render/gl3d';
import { initHeader, renderHeader, renderKPIs, renderSide, renderLower, renderPhone, initLowerStatic, applyAction, setResponse, setWeight, resetWeights, renderBanner } from './ui/panels';
import { renderForecast, renderAllocation, renderReservations, renderImpact, setAssumption, resetAssumptions, validateObs, importCSV } from './ui/pages';
import { initPresentation, startPresentation, presNext, presBack, presToggle, presExit, presTick, pres } from './ui/presentation';
import { ScenarioId, clockLabel } from './core/scenarios';
import { AllocWeights } from './core/allocation';
import { ForecastAssumptions } from './core/forecast';
import { DestId, FLOOR_NAMES } from './core/layout';
import { FieldObs, EmissionSettings } from './ui/store';

const NAV: { id: Section; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: 'overview' },
  { id: 'forecast', label: 'Forecast', icon: 'forecast' },
  { id: 'allocation', label: 'Allocation', icon: 'allocation' },
  { id: 'reservations', label: 'Reservations', icon: 'reservations' },
  { id: 'impact', label: 'Impact', icon: 'impact' }
];

let scene: SceneView;
let uiDirty = true;
let pageDirty = true;

function goSection(s: Section) {
  store.section = s;
  for (const n of NAV) {
    const v = document.getElementById(`view-${n.id}`) as HTMLElement;
    v.hidden = n.id !== s;
  }
  for (const b of $$('#rail [data-section]')) {
    const on = b.dataset.section === s;
    b.setAttribute('aria-current', on ? 'page' : 'false');
  }
  if (s === 'overview') {
    requestAnimationFrame(() => { scene.resize(); scene.dirty = true; uiDirty = true; });
  }
  pageDirty = true;
  uiDirty = true;
  $('#main').scrollTop = 0;
}

function renderRail() {
  $('#rail').innerHTML = NAV.map((n) => `<button type="button" data-section="${n.id}" aria-current="${n.id === store.section ? 'page' : 'false'}">${icon(n.icon, 20)}<span>${n.label}</span></button>`).join('') +
    `<button type="button" class="rail-help" id="help-btn" title="How to use ParkFlow and keyboard shortcuts"><span class="help-ic" aria-hidden="true">?</span><span>Help</span></button>`;
}

function renderViewportControls() {
  const fv = store.floorView;
  for (const b of $$('#floor-seg button')) {
    const v = b.dataset.floorview as string;
    b.setAttribute('aria-pressed', String(v === String(fv)));
    (b as HTMLButtonElement).disabled = store.planView && v === 'all';
  }
  $('#plan-toggle').setAttribute('aria-pressed', String(store.planView));
  const sel = store.selected;
  ($('#focus-btn') as HTMLButtonElement).disabled = !sel;
  const following = scene && scene.followId !== null;
  const label = following ? 'Stop following' : sel && sel.kind === 'bay' ? 'Show selected bay' : 'Follow selected';
  const fl = $('#focus-label');
  if (fl.textContent !== label) fl.textContent = label;
  $('#focus-btn').setAttribute('aria-pressed', String(!!following));
  $('#focus-btn').title = sel ? (following ? 'Stop moving the camera with this car' : 'Move the camera to the selection') : 'Select a car or bay first';
}

function renderToast() {
  const el = $('#toast');
  const age = performance.now() - store.toastT;
  if (store.toast && age < 2600) {
    el.textContent = store.toast;
    el.classList.add('show');
  } else el.classList.remove('show');
}

function renderAll() {
  renderHeader();
  renderKPIs();
  renderViewportControls();
  if (store.section === 'overview') {
    renderBanner();
    renderSide();
    renderLower();
    renderPhone();
  }
  renderToast();
}

function renderPage() {
  if (store.section === 'forecast') renderForecast();
  else if (store.section === 'allocation') renderAllocation();
  else if (store.section === 'reservations') renderReservations();
  else if (store.section === 'impact') renderImpact();
}

function runComparisonUI() {
  const btn = $('#run-compare') as HTMLButtonElement;
  btn.disabled = true;
  btn.innerHTML = `${icon('compare', 16)}<span>Running…</span>`;
  setTimeout(() => {
    try {
      runMatchedComparison();
      store.comparisonStale = false;
      toast('Matched comparison complete');
      goSection('impact');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `${icon('compare', 16)}<span>Run comparison</span>`;
    }
  }, 30);
}

function selectVehicle(id: number, focus = false) {
  store.selected = { kind: 'vehicle', id };
  if (store.section !== 'overview' && store.section !== 'allocation') goSection('overview');
  emit('select');
  if (focus && store.section === 'overview') scene.focusVehicle(store.sim.vehicles[id]);
}

function selectBay(id: number) {
  store.selected = { kind: 'bay', id };
  store.rightTab = 'vehicle';
  if (store.section !== 'overview') goSection('overview');
  emit('select');
  scene.focusBay(store.sim.L.bays[id]);
}

function handleAct(el: HTMLElement) {
  const act = el.dataset.act as string;
  const sim = store.sim;
  const id = el.dataset.id;
  switch (act) {
    case 'run-compare': runComparisonUI(); break;
    case 'pick-searching': {
      const list = sim.searchingVehicles().filter((v) => v.state === 'driving');
      const v = list.sort((a, b) => a.gateT - b.gateT)[0];
      if (v) selectVehicle(v.i, true);
      break;
    }
    case 'pick-latest': {
      const v = sim.vehicles.filter((x) => x.gateT >= 0).sort((a, b) => b.gateT - a.gateT)[0];
      if (v) selectVehicle(v.i, true);
      break;
    }
    case 'focus-selected':
    case 'focus-bay': focusSelected(); break;
    case 'tab-reasoning': store.rightTab = 'reasoning'; emit('select'); break;
    case 'select-vehicle': if (id) selectVehicle(Number(id), store.section === 'overview'); break;
    case 'select-bay': if (id) selectBay(Number(id)); break;
    case 'review-action': store.pendingAction = id || null; emit('action'); break;
    case 'cancel-action': store.pendingAction = null; emit('action'); break;
    case 'confirm-action': if (id) applyAction(id); break;
    case 'ack-assist': {
      const r = sim.assistance.find((x) => x.id === id);
      if (r) { r.status = 'acknowledged'; sim.log('operator', `${r.id} acknowledged by the operator.`, 'ok'); }
      emit('action');
      break;
    }
    case 'reset-weights': resetWeights(); markStale(); emit('weights'); break;
    case 'floor': { const f = Number(el.dataset.floor); store.floorView = store.floorView === f && !store.planView ? 'all' : f; store.planView = false; emit('floor'); scene.fit(true); break; }
    case 'reset-assumptions': resetAssumptions(); markStale(); pageDirty = true; break;
    case 'open-actions': store.rightTab = 'actions'; goSection('overview'); break;
    case 'burst': {
      const dest = (store.drafts.burstDest || 'atrium') as DestId;
      const vs = sim.injectArrivals(4, dest);
      store.demoBurst = vs.map((v) => v.i);
      toast('Four arrivals added at the entrance');
      pageDirty = true;
      break;
    }
    case 'res-checkin': if (id) { store.resMsg = sim.checkInNow(id); pageDirty = true; } break;
    case 'res-cancel': if (id) { store.resMsg = sim.cancelReservation(id); pageDirty = true; } break;
    case 'field-del': store.field = store.field.filter((o) => o.id !== id); persist(); store.fieldMsg = `Observation ${id} deleted.`; pageDirty = true; break;
    case 'field-import': {
      const r = importCSV(store.drafts.fCsv || '');
      store.fieldMsg = `${r.added} row${r.added === 1 ? '' : 's'} imported${r.rejected.length ? `, ${r.rejected.length} rejected: ${r.rejected.slice(0, 3).join(' ')}${r.rejected.length > 3 ? ' …' : ''}` : '.'}`;
      if (r.added && !r.rejected.length) store.drafts.fCsv = '';
      pageDirty = true;
      break;
    }
    case 'field-clear': store.drafts.fieldClear = '1'; pageDirty = true; break;
    case 'field-clear-no': store.drafts.fieldClear = ''; pageDirty = true; break;
    case 'field-clear-yes': store.field = []; persist(); store.drafts.fieldClear = ''; store.fieldMsg = 'All observations deleted.'; pageDirty = true; break;
  }
  uiDirty = true;
}

function markStale() {
  if (store.comparison) store.comparisonStale = true;
}

function focusSelected() {
  const sel = store.selected;
  if (!sel) return;
  if (store.section !== 'overview') goSection('overview');
  if (sel.kind === 'vehicle') scene.focusVehicle(store.sim.vehicles[sel.id]);
  else scene.focusBay(store.sim.L.bays[sel.id]);
}

function bindEvents() {
  document.addEventListener('click', (e) => {
    const t = e.target as HTMLElement;
    const sec = t.closest('[data-section]') as HTMLElement | null;
    if (sec) { goSection(sec.dataset.section as Section); return; }
    const go = t.closest('[data-go]') as HTMLElement | null;
    if (go) { goSection(go.dataset.go as Section); return; }
    const wb = t.closest('[data-welcome]') as HTMLElement | null;
    if (wb) {
      closeWelcome();
      if (wb.dataset.welcome === 'tour') startPresentation();
      return;
    }
    const p = t.closest('[data-pres]') as HTMLElement | null;
    if (p) {
      const a = p.dataset.pres;
      if (a === 'next') presNext(); else if (a === 'back') presBack(); else if (a === 'pause') presToggle(); else presExit();
      uiDirty = true;
      return;
    }
    const tab = t.closest('[data-tab]') as HTMLElement | null;
    if (tab) { store.rightTab = tab.dataset.tab as typeof store.rightTab; renderSide(true); return; }
    const filt = t.closest('[data-filter]') as HTMLElement | null;
    if (filt) { store.eventFilter = filt.dataset.filter as string; uiDirty = true; return; }
    const sp = t.closest('[data-speed]') as HTMLElement | null;
    if (sp) { store.speed = Number(sp.dataset.speed); uiDirty = true; return; }
    const fv = t.closest('[data-floorview]') as HTMLElement | null;
    if (fv) {
      const v = fv.dataset.floorview as string;
      store.floorView = v === 'all' ? 'all' : Number(v);
      emit('floor');
      scene.fit(true);
      return;
    }
    const act = t.closest('[data-act]') as HTMLElement | null;
    if (act && (act.tagName === 'BUTTON' || act.getAttribute('role') === 'button' || act.tagName === 'TR' || act.tagName === 'LI' || act.tagName === 'A')) handleAct(act);
  });
  document.addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement;
    const typing = t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA';
    if (!$('#welcome').hidden) {
      if (e.key === 'Escape') closeWelcome();
      return;
    }
    if (!typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
      if (e.key === ' ' && (t === document.body || t.tagName === 'CANVAS')) { e.preventDefault(); $('#play').click(); return; }
      if (e.key === '?') { openWelcome(); return; }
      if (store.section === 'overview' && /^[0-3]$/.test(e.key)) {
        store.floorView = e.key === '0' ? 'all' : Number(e.key) - 1;
        store.planView = false;
        emit('floor');
        scene.fit(true);
        return;
      }
      if ((e.key === 'f' || e.key === 'F') && store.selected) { $('#focus-btn').click(); return; }
      if (e.key === 'Escape' && store.selected && !pres.active) { store.selected = null; scene.stopFollow(); emit('select'); return; }
    }
    if ((e.key === 'Enter' || e.key === ' ') && t.getAttribute('role') === 'button' && t.tagName !== 'BUTTON') {
      e.preventDefault();
      t.click();
    }
    if (pres.active && t.tagName !== 'INPUT' && t.tagName !== 'SELECT' && t.tagName !== 'TEXTAREA') {
      if (e.key === 'ArrowRight') presNext();
      else if (e.key === 'ArrowLeft') presBack();
      else if (e.key === 'Escape') presExit();
    }
    if (t.getAttribute('role') === 'tab' && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
      const tabs = $$('#side-tabs [role="tab"]');
      const i = tabs.indexOf(t);
      const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      n.click();
      n.focus();
    }
  });
  document.addEventListener('input', (e) => {
    const t = e.target as HTMLInputElement;
    if (t.dataset.draft) store.drafts[t.dataset.draft] = t.type === 'checkbox' ? (t.checked ? '1' : '') : t.value;
    if (t.dataset.weight) {
      setWeight(t.dataset.weight as keyof AllocWeights, Number(t.value));
      const o = t.parentElement?.querySelector('output');
      if (o) o.textContent = Number(t.value).toFixed(2);
      markStale();
    }
    if (t.dataset.resp) {
      setResponse(t.dataset.resp, Number(t.value));
      const o = t.parentElement?.querySelector('output');
      if (o) o.textContent = `${Math.round(Number(t.value) * 100)}%`;
    }
    if (t.dataset.assume) {
      const k = t.dataset.assume as keyof ForecastAssumptions;
      setAssumption(k, Number(t.value));
      markStale();
      const o = t.parentElement?.querySelector('output');
      if (o) o.textContent = t.step && Number(t.max) <= 1 ? `${Math.round(Number(t.value) * 100)}%` : t.value;
    }
    if (t.dataset.act === 'noshow') {
      store.noShowRate = Number(t.value);
      persist();
      const o = t.parentElement?.querySelector('output');
      if (o) o.textContent = `${Math.round(Number(t.value) * 100)}%`;
    }
    if (t.dataset.emission) {
      const k = t.dataset.emission as keyof EmissionSettings;
      const v = Number(t.value);
      if (isFinite(v) && v >= 0) { store.emission[k] = v; persist(); }
    }
  });
  document.addEventListener('change', (e) => {
    const t = e.target as HTMLInputElement;
    if (t.id === 'scenario') { setScenario(t.value as ScenarioId); scene.fit(true); toast(`Scenario: ${(t as unknown as HTMLSelectElement).selectedOptions[0].text}`); return; }
    if (t.dataset.act === 'vehicle-dest' && store.selected && store.selected.kind === 'vehicle') {
      const msg = store.sim.changeDestination(store.selected.id, t.value as DestId);
      toast(msg);
      t.blur();
    }
    if (t.dataset.act === 'driver-dest') { store.driver.dest = t.value as DestId; t.blur(); }
    if (t.dataset.act === 'driver-flag') { const f = t.dataset.flag as 'ev' | 'family' | 'member'; store.driver[f] = t.checked; t.blur(); }
    if (t.dataset.weight || t.dataset.assume || t.dataset.resp || t.dataset.emission || t.dataset.act === 'noshow') { t.blur(); pageDirty = true; }
    if (t.id === 'f-file' && t.files && t.files[0]) {
      const file = t.files[0];
      const reader = new FileReader();
      reader.onload = () => {
        const r = importCSV(String(reader.result || ''));
        store.fieldMsg = `${esc(file.name)}: ${r.added} row${r.added === 1 ? '' : 's'} imported${r.rejected.length ? `, ${r.rejected.length} rejected: ${r.rejected.slice(0, 3).join(' ')}` : '.'}`;
        pageDirty = true;
      };
      reader.onerror = () => { store.fieldMsg = 'The file could not be read. Paste the rows instead.'; pageDirty = true; };
      reader.readAsText(file);
    }
    uiDirty = true;
  });
  document.addEventListener('submit', (e) => {
    const f = e.target as HTMLFormElement;
    e.preventDefault();
    const sim = store.sim;
    if (f.id === 'res-form') {
      if (store.drafts.resElig !== '1') { store.resMsg = 'Confirm the driver is eligible for this bay type before reserving.'; pageDirty = true; return; }
      const type = (store.drafts.resType || 'ev') as 'ev' | 'family' | 'member';
      const r = sim.createReservation(type, Number(store.drafts.resStart || 20), Number(store.drafts.resDur || 90));
      store.resMsg = r.ok ? `${r.r.id} confirmed. Bay ${sim.L.bays[r.r.bay].id} is held until ${clockOf(r.r.windowEnd + r.r.grace)}.` : r.error;
      if (r.ok) store.drafts.resElig = '';
      pageDirty = true;
    }
    if (f.id === 'assist-form') {
      if (store.drafts.assistPermit !== '1') { store.resMsg = 'Accessible-bay assistance needs an OKU permit holder in the vehicle.'; pageDirty = true; return; }
      const req = sim.requestAssistance(Number(store.drafts.assistEta || 10));
      store.resMsg = `${req.id} logged for the operator. Accessible bays stay protected for permit holders; this is not a guaranteed bay.`;
      store.drafts.assistPermit = '';
      pageDirty = true;
    }
    if (f.id === 'field-form') {
      const o: FieldObs = { id: (store.drafts.fId || '').trim(), date: store.drafts.fDate || '', gateEntry: store.drafts.fIn || '', parked: store.drafts.fOut || '', zone: store.drafts.fZone || '', note: store.drafts.fNote || '' };
      const err = validateObs(o, store.field);
      if (err) store.fieldMsg = err;
      else {
        store.field.push(o);
        persist();
        store.fieldMsg = `Observation ${o.id} added.`;
        store.drafts.fId = ''; store.drafts.fIn = ''; store.drafts.fOut = ''; store.drafts.fNote = '';
      }
      pageDirty = true;
    }
    uiDirty = true;
  });

  $('#play').addEventListener('click', () => {
    if (store.sim.t >= store.sim.tEnd) return;
    store.playing = !store.playing;
    uiDirty = true;
  });
  $('#reset').addEventListener('click', () => {
    resetSim();
    toast('Scenario reset to its starting state');
  });
  $('#run-compare').addEventListener('click', runComparisonUI);
  $('#present').addEventListener('click', () => startPresentation());
  $('#plan-toggle').addEventListener('click', () => {
    store.planView = !store.planView;
    if (store.planView && store.floorView === 'all') store.floorView = 0;
    emit('floor');
    scene.fit(true);
  });
  $('#focus-btn').addEventListener('click', () => {
    if (scene.followId !== null) { scene.stopFollow(); uiDirty = true; return; }
    focusSelected();
    uiDirty = true;
  });
  $('#help-btn').addEventListener('click', () => openWelcome());
  $('#welcome').addEventListener('click', (e) => { if (e.target === $('#welcome')) closeWelcome(); });
  $('#reset-cam').addEventListener('click', () => scene.fit(true));
  $('#phone-toggle').addEventListener('click', () => {
    store.driver.collapsed = !store.driver.collapsed;
    if (store.driver.collapsed) store.driver.autoOpen = false;
    renderPhone(true);
    scene.fit(true);
  });
  $('#legend-toggle').addEventListener('click', () => {
    const lg = $('#legend');
    const open = lg.classList.toggle('open');
    $('#legend-toggle').setAttribute('aria-expanded', String(open));
  });
  // Layers popover: what the 3D model draws. Choices persist per viewer.
  const pop = $('#layers-pop');
  const setLayersOpen = (open: boolean) => {
    pop.hidden = !open;
    $('#layers-btn').setAttribute('aria-expanded', String(open));
  };
  for (const inp of $$('#layers-pop input[data-layer]') as HTMLInputElement[]) inp.checked = !!store.layers[inp.dataset.layer as keyof typeof store.layers];
  $('#layers-btn').addEventListener('click', (e) => { e.stopPropagation(); setLayersOpen(!!pop.hidden); });
  document.addEventListener('click', (e) => {
    if (!pop.hidden && !(e.target as HTMLElement).closest('.layers')) setLayersOpen(false);
  });
  pop.addEventListener('keydown', (e) => { if (e.key === 'Escape') { setLayersOpen(false); $('#layers-btn').focus(); } });
  pop.addEventListener('change', (e) => {
    const t = e.target as HTMLInputElement;
    const k = t.dataset.layer as keyof typeof store.layers | undefined;
    if (!k) return;
    store.layers[k] = t.checked;
    persist();
    scene.dirty = true;
    toast(`${t.closest('label')?.querySelector('b')?.textContent || 'Layer'} ${t.checked ? 'on' : 'off'}`);
  });
}

function openWelcome() {
  const card = $('#welcome-card');
  card.innerHTML = `
    <div><h2 id="welcome-title">Welcome to ParkFlow</h2>
    <p class="lede">A simulated parking command centre for the KL East Mall pilot concept. Everything here comes from one simulation with synthetic data; nothing is connected to the real mall.</p></div>
    <ol class="steps">
      <li><b>Watch the car park</b>The light above each bay shows its state, like the real indicators: green free, red taken, blinking amber about to leave. The level board counts free bays on each floor.</li>
      <li><b>Click any car</b>See which zone ParkFlow chose for it, the reasons in plain language, and what the driver's phone shows.</li>
      <li><b>Measure the impact</b>“Run comparison” replays the same demand with and without guidance and reports time and distance saved.</li>
    </ol>
    <div class="keys"><span><kbd>Space</kbd> play or pause</span><span><kbd>0</kbd>–<kbd>3</kbd> all floors, B1, B2, B3</span><span><kbd>F</kbd> follow the selected car</span><span><kbd>Esc</kbd> clear selection</span><span><kbd>?</kbd> this help</span></div>
    <div class="modal-actions">
      <button type="button" class="btn" data-welcome="close">Explore on my own</button>
      <button type="button" class="btn btn-primary" data-welcome="tour">${icon('present', 16)} Start the 90-second tour</button>
    </div>`;
  $('#welcome').hidden = false;
  (card.querySelector('[data-welcome="tour"]') as HTMLElement).focus();
}

function closeWelcome() {
  $('#welcome').hidden = true;
  saveJSON('parkflow.welcome', { seen: true });
}

function clockOf(t: number): string {
  return clockLabel(store.sim.scn, t, false);
}

function loop() {
  let last = performance.now();
  let acc = 0;
  let uiAcc = 0;
  let pageAcc = 0;
  const frame = (now: number) => {
    const dt = Math.min(0.25, (now - last) / 1000);
    last = now;
    const sim = store.sim;
    let ticked = false;
    if (store.playing && sim.t < sim.tEnd) {
      acc += dt * store.speed;
      let n = 0;
      while (acc >= 1 && n < 400 && sim.t < sim.tEnd) { sim.step(); acc -= 1; n++; }
      ticked = n > 0;
      if (sim.t >= sim.tEnd) {
        store.playing = false;
        acc = 0;
        toast('Scenario run complete. Reset to replay it.');
        uiDirty = true;
      }
    }
    const alpha = store.playing ? Math.min(1, acc) : 1;
    if (store.section === 'overview' && (ticked || scene.dirty || scene.animating || (store.playing && store.speed > 0))) scene.render(alpha);
    uiAcc += dt;
    pageAcc += dt;
    if (uiDirty || uiAcc > 0.25) {
      renderAll();
      uiDirty = false;
      uiAcc = 0;
    }
    if (store.section !== 'overview' && (pageDirty || pageAcc > 0.6)) {
      renderPage();
      pageDirty = false;
      pageAcc = 0;
    }
    presTick();
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

function showFallback() {
  const fb = $('#fallback');
  fb.hidden = false;
  const sim = store.sim;
  const c = sim.counts();
  fb.innerHTML = `<p><strong>The model view could not start in this browser.</strong></p><p>All other panels use the same simulation. Current capacity:</p><ul>${[0, 1, 2].map((f) => `<li>${FLOOR_NAMES[f]}: ${c.perFloor[f].generalFree} general bays free, ${c.perFloor[f].occupied} occupied</li>`).join('')}</ul>`;
}

function init() {
  renderRail();
  initHeader();
  initLowerStatic();
  if (prefersReducedMotion()) { store.playing = false; store.speed = 5; }
  else store.speed = 5;
  resetSim(480);
  const gls = new GLScene($('#scene') as HTMLCanvasElement, $('#vp-labels'), $('#vp-tip'));
  if (gls.ok) scene = gls;
  else {
    // WebGL2 unavailable: swap in a fresh canvas for the 2D renderer
    const old = $('#scene') as HTMLCanvasElement;
    const cv = document.createElement('canvas');
    cv.id = 'scene';
    cv.setAttribute('aria-label', old.getAttribute('aria-label') || '');
    old.replaceWith(cv);
    $('#vp-labels').hidden = true;
    scene = new Scene3D(cv);
    if (!scene.ok) showFallback();
  }
  initPresentation(scene, goSection);
  on((topic) => {
    uiDirty = true;
    pageDirty = true;
    if (scene) scene.dirty = true;
    if (topic === 'select' && store.selected && store.selected.kind === 'vehicle' && store.driver.collapsed && store.driver.autoOpen) {
      store.driver.collapsed = false;
      renderPhone(true);
    }
    if (topic === 'reset') {
      store.playing = store.playing && !prefersReducedMotion() ? true : store.playing;
      scene.fit(false);
    }
  });
  bindEvents();
  goSection('overview');
  requestAnimationFrame(() => { scene.resize(); scene.fit(false); scene.dirty = true; });
  if (!loadJSON<{ seen: boolean }>('parkflow.welcome', { seen: false }).seen) openWelcome();
  loop();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
