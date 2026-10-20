// Overview UI: header, KPI strip, right-hand panel, lower cards, event feed and driver preview.

import { store, emit, toast, persist } from './store';
import { $, esc, setHTML, fmtPct, fmtSecs, fmtDist, icon, tag, signed, dotMatrix } from './dom';

function fmtShort(secs: number): string {
  if (!isFinite(secs)) return '–';
  const s = Math.round(secs);
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`;
}
import { Sim, Vehicle, SimEvent } from '../core/sim';
import { Allocation, Candidate, WEIGHT_LABELS, AllocWeights, DEFAULT_WEIGHTS } from '../core/allocation';
import { DESTINATIONS, DEST_BY_ID, BAY_TYPE_LABEL, typeText, FLOOR_NAMES, ZONES, DestId, BayType } from '../core/layout';
import { clockLabel, SCENARIOS } from '../core/scenarios';
import { occupancyChart, legendItems } from './charts';
import { pctChange } from '../core/metrics';

export const STATE_LABEL: Record<string, string> = {
  pending: 'Not yet arrived',
  queued: 'Waiting at entrance',
  driving: 'Searching',
  parking: 'Parking',
  parked: 'Parked',
  unparking: 'Leaving bay',
  leaving: 'Driving to exit',
  exited: 'Left the car park',
  cancelled: 'Trip cancelled',
  diverted: 'Diverted to overflow'
};

const FACTOR_COLORS: Record<keyof AllocWeights, string> = { drive: 'var(--f-drive)', walk: 'var(--f-walk)', congestion: 'var(--f-cong)', load: 'var(--f-load)', forecast: 'var(--f-fc)' };
const FACTOR_SHORT: Record<keyof AllocWeights, string> = { drive: 'Drive', walk: 'Walk', congestion: 'Congestion', load: 'Guided load', forecast: 'Forecast' };

function focusedWithin(el: HTMLElement): boolean {
  const a = document.activeElement as HTMLElement | null;
  return !!a && el.contains(a) && (a.tagName === 'INPUT' || a.tagName === 'SELECT' || a.tagName === 'TEXTAREA');
}

export function vehicleStateLabel(sim: Sim, v: Vehicle): string {
  if (v.state === 'driving' && v.bay >= 0 && v.resId) return 'To reserved bay';
  if (v.state === 'leaving' && v.gaveUp) return 'Gave up, leaving';
  if (v.state === 'driving' && v.gateT >= 0 && sim.t - v.gateT > 300) return 'Searching > 5 min';
  return STATE_LABEL[v.state] || v.state;
}

// ---------------- header ----------------
export function initHeader() {
  const sel = $('#scenario') as HTMLSelectElement;
  sel.innerHTML = SCENARIOS.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join('');
  setHTML($('#speed'), [1, 5, 15, 30].map((s) => `<button type="button" data-speed="${s}" aria-pressed="false">${s}×</button>`).join(''));
}

export function renderHeader() {
  const sim = store.sim;
  $('#clock').textContent = sim.clock(true);
  ($('#scenario') as HTMLSelectElement).value = store.scenarioId;
  const play = $('#play');
  const done = sim.t >= sim.tEnd;
  setHTML(play, store.playing ? `${icon('pause', 16)}<span>Pause</span>` : `${icon('play', 16)}<span>${done ? 'Ended' : 'Play'}</span>`);
  play.setAttribute('aria-label', store.playing ? 'Pause simulation' : done ? 'Run complete' : 'Play simulation');
  play.title = store.playing ? 'Pause' : done ? 'Run complete. Reset to replay.' : 'Play';
  (play as HTMLButtonElement).disabled = done;
  for (const b of Array.from($('#speed').children) as HTMLElement[]) b.setAttribute('aria-pressed', String(Number(b.dataset.speed) === store.speed));
  const badge = $('#simbadge');
  badge.classList.toggle('running', store.playing);
  const phase = sim.t >= sim.tWindowEnd ? (done ? 'Run complete' : 'Drain period') : 'Arrivals open';
  $('#phase').textContent = phase;
}

// ---------------- KPI strip ----------------
// Available general bays live on the level board, so the strip carries the five numbers that answer
// "how is it going": fullness, time to park, who is still searching, what is coming, and the measured effect.
export function renderKPIs() {
  const sim = store.sim;
  const c = sim.counts();
  const recent = sim.vehicles.filter((v) => v.parkT >= 0 && v.gateT >= 0 && sim.t - v.parkT <= 900);
  const g2p = recent.map((v) => v.parkT - v.gateT);
  const meanG2P = g2p.length ? g2p.reduce((a, b) => a + b, 0) / g2p.length : NaN;
  const searching = sim.searchingVehicles();
  const slow = searching.filter((v) => sim.t - v.gateT > 300).length;
  const f = sim.forecast;
  const occ = c.occupied / c.usable;
  const cmp = store.comparison;
  const occTone = occ >= 0.95 ? 'crit' : occ >= 0.88 ? 'warn' : '';
  let k5: string;
  if (cmp) {
    const red = -pctChange(cmp.baseline.meanSearchDist, cmp.guided.meanSearchDist);
    k5 = `<div class="kpi kpi-cmp" data-go="impact" role="button" tabindex="0" title="Matched run on ${esc(cmp.scenarioName)}: identical arrivals with and without guidance. Open Impact for the full table.">
      <div class="kpi-l">Search distance vs no guidance</div>
      <div class="kpi-row"><div class="kpi-v">${isFinite(red) ? `${red >= 0 ? '−' : '+'}${Math.abs(red).toFixed(0)}<small>%</small>` : '–'}</div>${tag('sim', 'Matched run')}</div>
      <div class="kpi-s">${fmtDist(cmp.baseline.meanSearchDist)} down to ${fmtDist(cmp.guided.meanSearchDist)} per parked car</div></div>`;
  } else {
    k5 = `<div class="kpi kpi-empty">
      <div class="kpi-l">Search distance vs no guidance</div>
      <div class="kpi-row"><div class="kpi-v kpi-muted">Not measured yet</div></div>
      <div class="kpi-s"><button type="button" class="linkbtn" data-act="run-compare">Run the matched comparison</button></div></div>`;
  }
  const html = `
    <div class="kpi ${occTone}" tabindex="0" title="Share of usable bays that are occupied. Bays with an uncertain camera view count as occupied. Leaving soon means payment is recorded but the car has not left yet.">
      <div class="kpi-l">Occupancy</div>
      <div class="kpi-row"><div class="kpi-v">${Math.round(occ * 100)}<small>%</small></div>${tag('now')}</div>
      <div class="kpi-s">${c.occupied} of ${c.usable} usable bays, ${c.departing} leaving soon</div></div>
    <div class="kpi" tabindex="0" title="Average time from crossing the entrance gate to finishing parking, for cars that parked in the last 15 simulated minutes. Queueing before the gate is not included.">
      <div class="kpi-l">Gate to parked</div>
      <div class="kpi-row"><div class="kpi-v">${g2p.length ? fmtShort(meanG2P) : '–'}</div>${tag('sim', 'Simulated')}</div>
      <div class="kpi-s">Average of ${g2p.length} car${g2p.length === 1 ? '' : 's'} in the last 15 min</div></div>
    <div class="kpi ${slow > 2 ? 'warn' : ''}" tabindex="0" title="Cars inside the car park that have not found a bay yet.">
      <div class="kpi-l">Still searching</div>
      <div class="kpi-row"><div class="kpi-v">${searching.length}<small> car${searching.length === 1 ? '' : 's'}</small></div>${tag('now')}</div>
      <div class="kpi-s">${slow ? `${slow} for over 5 min` : 'None over 5 min'}, ${sim.gateQueue.length} at the entrance</div></div>
    <div class="kpi kpi-fc" tabindex="0" title="Cars expected to arrive in the next 30 minutes, combining typical-day history with event, cinema, dining, offer and 'I'm coming' signals. History-only figure shown for comparison.">
      <div class="kpi-l">Arriving in 30 min</div>
      <div class="kpi-row"><div class="kpi-v">${f ? Math.round(f.arr30.intent) : '–'}<small> cars</small></div>${tag('fc')}</div>
      <div class="kpi-s">History alone says ${f ? Math.round(f.arr30.hist) : '–'}${f && f.fillMin.intent !== null ? `, 95% full by ${clockLabel(sim.scn, sim.t + f.fillMin.intent * 60, false)}` : ''}</div></div>
    ${k5}`;
  setHTML($('#kpis'), html);
}

// ---------------- situation line under the level board ----------------
export function renderBanner() {
  const sim = store.sim;
  const c = sim.counts();
  const occ = c.occupied / c.usable;
  const f = sim.forecast;
  const searching = sim.searchingVehicles();
  const slow = searching.filter((v) => sim.t - v.gateT > 300).length;
  const tone = occ >= 0.95 || c.generalFree <= 6 ? 'crit' : occ >= 0.85 || c.perFloor[0].generalFree <= 6 ? 'warn' : 'ok';
  const state = tone === 'crit' ? 'Nearly full' : tone === 'warn' ? 'Busy' : 'Running smoothly';
  const parts: string[] = [];
  parts.push(searching.length ? `${searching.length} driver${searching.length === 1 ? ' is' : 's are'} searching${slow ? `, ${slow} for over 5 minutes` : ''}.` : 'No one is searching right now.');
  if (f) parts.push(f.fillMin.intent !== null ? `Forecast: about 95% full by <b>${clockLabel(sim.scn, sim.t + f.fillMin.intent * 60, false)}</b>.` : 'Forecast: no fill expected in the next hour.');
  if (sim.t >= sim.tEnd) parts.push('This run has ended. Press reset to replay it.');
  const recs = operatorActions().filter((a) => a.recommended).length;
  let btn: string;
  if (recs) btn = `<button type="button" class="btn btn-sm btn-primary" data-act="open-actions">${icon('alert', 14)} Review ${recs} suggested action${recs === 1 ? '' : 's'}</button>`;
  else if (!store.comparison) btn = `<button type="button" class="btn btn-sm" data-act="run-compare">${icon('compare', 14)} Measure the impact</button>`;
  else btn = `<button type="button" class="btn btn-sm" data-go="impact">${icon('impact', 14)} See the impact</button>`;
  const el = $('#banner');
  el.className = `status tone-${tone}`;
  setHTML(el, `<div class="st-top"><span class="bn-state"><i class="bn-dot"></i>${state}</span>${btn}</div><p class="bn-text">${parts.join(' ')}</p>`);
}

// ---------------- right-hand panel ----------------
export function renderSide(force = false) {
  const side = $('#side');
  if (!force && focusedWithin(side)) return;
  for (const b of Array.from($('#side-tabs').children) as HTMLElement[]) {
    const on = b.dataset.tab === store.rightTab;
    b.setAttribute('aria-selected', String(on));
    b.tabIndex = on ? 0 : -1;
  }
  const sel = store.selected;
  const tab1 = $('#side-tabs').children[0] as HTMLElement;
  tab1.textContent = sel && sel.kind === 'bay' ? 'Selected bay' : 'Selected vehicle';
  let html = '';
  if (store.rightTab === 'vehicle') html = sel && sel.kind === 'bay' ? bayDetail(sel.id) : sel ? vehicleDetail(store.sim.vehicles[sel.id]) : emptySelection();
  else if (store.rightTab === 'reasoning') html = reasoningPanel();
  else html = operatorPanel();
  setHTML($('#side-body'), html);
}

function emptySelection(): string {
  const sim = store.sim;
  const searching = sim.searchingVehicles().length;
  return `<div class="empty">
    <div class="empty-ic">${icon('car', 22)}</div>
    <p><strong>Select a vehicle or bay in the model</strong></p>
    <p class="muted">Hover over the model to identify things. Click a car to see where ParkFlow sent it and why, or click a bay to see its type and status.</p>
    <div class="btn-row">
      <button type="button" class="btn btn-sm" data-act="pick-searching" ${searching ? '' : 'disabled'}>${icon('focus', 14)} Select a searching vehicle</button>
      <button type="button" class="btn btn-sm" data-act="pick-latest">${icon('car', 14)} Latest arrival</button>
    </div>
  </div>`;
}

function chips(elig: BayType[]): string {
  return elig.map((t) => `<span class="chip chip-${t}">${esc(BAY_TYPE_LABEL[t])}</span>`).join('');
}

function routeSummary(sim: Sim, v: Vehicle): string {
  if (v.edge < 0 || !(v.state === 'driving' || v.state === 'leaving')) return '';
  const names: string[] = [];
  const edges = [v.edge, ...v.route];
  for (const id of edges) {
    const e = sim.L.edges[id];
    let n = e.name;
    if (e.kind === 'road' || e.kind === 'connector') continue;
    if (e.kind === 'aisle') n = `${FLOOR_NAMES[sim.L.nodes[e.from].floor]} aisle ${e.aisle} · Zone ${e.zone}`;
    if (names[names.length - 1] !== n) names.push(n);
  }
  if (v.bay >= 0 && v.state === 'driving') names.push(`Bay ${sim.L.bays[v.bay].id}`);
  if (v.state === 'leaving') names.push('Exit gate');
  return `<ol class="route">${names.slice(0, 7).map((n, i) => `<li class="${i === 0 ? 'cur' : ''}">${esc(n)}</li>`).join('')}${names.length > 7 ? `<li class="more">+${names.length - 7} more</li>` : ''}</ol>`;
}

export function driveEstimate(sim: Sim, v: Vehicle): { m: number; s: number } {
  const m = sim.routeLength(v);
  return { m, s: m / 2.8 };
}

function vehicleDetail(v: Vehicle | undefined): string {
  const sim = store.sim;
  if (!v) return emptySelection();
  const lift = DEST_BY_ID[v.dest].lift;
  const elapsed = v.gateT >= 0 ? (v.parkT >= 0 ? v.parkT - v.gateT : sim.t - v.gateT) : NaN;
  const searching = v.state === 'driving' || v.state === 'parking';
  const est = driveEstimate(sim, v);
  const walk = v.bay >= 0 ? sim.L.bays[v.bay].walk[lift] : v.alloc && v.alloc.chosen ? Math.round(v.alloc.chosen.walk) : NaN;
  const guidance = v.resId && v.bay >= 0 ? `Reserved bay ${sim.L.bays[v.bay].id}` : v.target ? `${FLOOR_NAMES[v.target.floor]} Zone ${v.target.zone}${v.target.inv !== 'general' ? ` (${BAY_TYPE_LABEL[v.target.inv]})` : ''}` : v.initial ? 'Parked before the scenario started' : '–';
  const res = v.resId ? sim.reservations.find((r) => r.id === v.resId) : null;
  const stTone = v.state === 'driving' && sim.t - v.gateT > 300 ? 'warn' : searching ? 'teal' : v.state === 'parked' ? 'muted' : 'slate';
  const destSelect = searching && !v.resId
    ? `<label class="inline-field"><span>Change destination</span><select data-act="vehicle-dest" id="vehicle-dest-select">${DESTINATIONS.map((d) => `<option value="${d.id}" ${d.id === v.dest ? 'selected' : ''}>${esc(d.label)}</option>`).join('')}</select></label>`
    : '';
  return `<div class="sel-head">
      <span class="code">${esc(v.code)}</span>
      <span class="pill pill-${stTone}">${esc(vehicleStateLabel(sim, v))}</span>
      ${tag('sim', 'Simulated')}
    </div>
    <dl class="facts">
      <div><dt>Destination</dt><dd>${esc(DEST_BY_ID[v.dest].label)} · Lift ${lift}</dd></div>
      <div><dt>Guidance</dt><dd>${esc(guidance)}</dd></div>
      <div><dt>${v.parkT >= 0 ? 'Gate-to-park time' : 'Elapsed since gate'}</dt><dd>${v.gateT >= 0 ? fmtSecs(elapsed) : '–'}</dd></div>
      <div><dt>Driven since gate</dt><dd>${v.gateT >= 0 ? fmtDist(v.searchDist) : '–'}</dd></div>
      <div><dt>Remaining drive</dt><dd>${searching || v.state === 'leaving' ? `${fmtDist(est.m)} · ≈ ${fmtSecs(est.s)}` : '–'}</dd></div>
      <div><dt>Walk to Lift ${lift}</dt><dd>${isFinite(walk) ? `≈ ${walk} m · ${fmtSecs(walk / 1.2)}` : '–'}</dd></div>
      <div class="wide"><dt>Eligible bay types</dt><dd class="chips">${chips(v.elig)}</dd></div>
      ${res ? `<div class="wide"><dt>Reservation</dt><dd>${esc(res.id)} · ${esc(res.status)} · bay ${esc(sim.L.bays[res.bay].id)}</dd></div>` : ''}
      ${v.reroutes ? `<div class="wide"><dt>Route updates</dt><dd>${v.reroutes}</dd></div>` : ''}
    </dl>
    ${v.notice ? `<p class="notice">${icon('info', 14)} ${esc(v.notice)}</p>` : ''}
    ${routeSummary(sim, v)}
    <div class="btn-row">
      <button type="button" class="btn btn-sm" data-act="focus-selected">${icon('focus', 14)} Focus in 3D</button>
      ${v.alloc ? `<button type="button" class="btn btn-sm" data-act="tab-reasoning">${icon('allocation', 14)} Why this zone?</button>` : ''}
    </div>
    ${destSelect}
    <p class="fine">Position and timings are derived from the simulation. Indoor phone positioning is not implemented.</p>`;
}

function bayDetail(idx: number): string {
  const sim = store.sim;
  const b = sim.L.bays[idx];
  const st = sim.bayStatus(idx);
  const stLabel: Record<string, string> = { available: 'Available', occupied: 'Occupied', reserved: 'Reserved (held)', departing: 'Occupied · payment recorded, likely departing', uncertain: 'Uncertain', unavailable: 'Unavailable (maintenance)' };
  const o = sim.occ[idx] >= 0 ? sim.vehicles[sim.occ[idx]] : sim.claim[idx] >= 0 ? sim.vehicles[sim.claim[idx]] : null;
  const res = sim.reservations.filter((r) => r.bay === idx).slice(-1)[0];
  let resTxt = 'None';
  if (res) {
    const window = `${clockLabel(sim.scn, res.windowStart, false)}–${clockLabel(sim.scn, res.windowEnd, false)}`;
    resTxt = `${res.id} · ${res.status}${res.status === 'confirmed' ? ` · window ${window}, held until ${clockLabel(sim.scn, res.windowEnd + res.grace, false)}` : res.status === 'expired' ? ` at ${clockLabel(sim.scn, res.closedT, false)} · released to ${typeText(res.type)} inventory` : ''}`;
  }
  const conf = b.flag === 'obstructed' ? `${Math.round(b.confidence * 100)}% · camera view obstructed, status uncertain` : b.flag === 'maintenance' ? 'Manually flagged out of use' : `${Math.round(b.confidence * 100)}% · clear view (simulated)`;
  let charger = '';
  if (b.type === 'ev') {
    let cs = 'Charger available';
    if (b.charger === 'out') cs = 'Charger out of service: parking possible, charging not available';
    else if (o && sim.occ[idx] >= 0) {
      const end = Math.min(o.departT, o.parkT + 3600);
      cs = end > sim.t ? `Charging session in use · expected end ${clockLabel(sim.scn, end, false)}` : 'Session complete · vehicle still parked (charger idle but blocked)';
    } else if (st === 'reserved') cs = 'Held for an EV reservation';
    charger = `<div class="wide"><dt>EV charger</dt><dd>${esc(cs)}</dd></div>`;
  }
  const walks = ZONES.map((z) => `Lift ${z}: ${b.walk[z]} m`).join(' · ');
  return `<div class="sel-head"><span class="code">${esc(b.id)}</span><span class="pill pill-${st}">${esc(stLabel[st])}</span>${tag('now')}</div>
    <dl class="facts">
      <div><dt>Type</dt><dd>${esc(BAY_TYPE_LABEL[b.type])}</dd></div>
      <div><dt>Floor · zone</dt><dd>${FLOOR_NAMES[b.floor]} · Zone ${b.zone}</dd></div>
      <div><dt>Occupancy</dt><dd>${o ? `${esc(o.code)}${o.initial ? ' (parked before scenario start)' : ''}` : 'Empty'}</dd></div>
      <div><dt>Observation confidence</dt><dd>${esc(conf)}</dd></div>
      <div class="wide"><dt>Reservation</dt><dd>${esc(resTxt)}</dd></div>
      ${charger}
      <div class="wide"><dt>Walking distance</dt><dd>${walks}</dd></div>
    </dl>
    ${st === 'departing' ? `<p class="notice">${icon('clock', 14)} A payment signals a likely departure. The bay stays occupied until the vehicle has actually left.</p>` : ''}
    ${b.type === 'oku' ? `<p class="notice">${icon('oku', 14)} Protected accessible bay: never released to general traffic.</p>` : ''}
    <div class="btn-row">
      <button type="button" class="btn btn-sm" data-act="focus-bay">${icon('focus', 14)} Focus in 3D</button>
      ${o ? `<button type="button" class="btn btn-sm" data-act="select-vehicle" data-id="${o.i}">${icon('car', 14)} Select ${esc(o.code)}</button>` : ''}
    </div>`;
}

export function currentDecision(): Allocation | null {
  const sim = store.sim;
  const sel = store.selected;
  if (sel && sel.kind === 'vehicle') {
    const v = sim.vehicles[sel.id];
    if (v && v.alloc) return v.alloc;
  }
  return sim.decisions[sim.decisions.length - 1] || null;
}

export function candidateRows(a: Allocation): string {
  return a.ranked
    .map((c, i) => {
      const segs = (Object.keys(c.parts) as (keyof AllocWeights)[]).map((k) => `<i style="width:${(c.parts[k] / 1.12) * 100}%;background:${FACTOR_COLORS[k]}" title="${FACTOR_SHORT[k]} ${c.parts[k].toFixed(2)}"></i>`).join('');
      const bonus = c.bonus > 0 ? `<i style="width:${(c.bonus / 1.12) * 100}%" class="bonus" title="Eligible special inventory or operator preference +${c.bonus.toFixed(2)}"></i>` : '';
      return `<div class="cand ${i === 0 ? 'win' : ''}">
        <div class="cand-h"><span class="rank">${i + 1}</span><span class="cand-n">${esc(c.label)}</span><span class="score">${c.total.toFixed(2)}</span></div>
        <div class="bar">${segs}${bonus}</div>
        <div class="cand-s">${c.effective >= 1 ? `${c.free} free − ${c.heading} heading = ${c.effective}` : `${c.free} free · ${c.heading} heading`} · walk ${Math.round(c.walk)} m · drive ${Math.round(c.drive)} m · ${Math.round(c.congestion)} on approach</div>
      </div>`;
    })
    .join('');
}

export function weightsDrawer(idPrefix: string): string {
  const w = store.weights;
  const sum = Object.values(w).reduce((a, b) => a + b, 0);
  return `<details class="drawer" id="${idPrefix}-drawer">
    <summary>${icon('sliders', 14)} Scoring method and weights</summary>
    <p class="fine">1. Hard constraints: bay type must match the driver's eligibility; accessible bays need a permit; reserved and out-of-service bays are excluded; a zone needs at least one free suitable bay after counting drivers already heading there.</p>
    <p class="fine">2. Each input is min–max normalised across feasible zones (0 = best, 1 = worst). Score = Σ weight × (1 − normalised value), plus 0.10 for eligible special inventory and any operator floor preference.</p>
    <div class="weights">
      ${(Object.keys(w) as (keyof AllocWeights)[])
        .map((k) => `<label class="wt"><span class="wt-l"><i class="dot" style="background:${FACTOR_COLORS[k]}"></i>${esc(WEIGHT_LABELS[k])}</span>
          <input type="range" min="0" max="0.6" step="0.05" value="${w[k]}" data-weight="${k}" id="${idPrefix}-w-${k}" aria-label="${esc(WEIGHT_LABELS[k])} weight">
          <output>${w[k].toFixed(2)}</output></label>`)
        .join('')}
    </div>
    <div class="btn-row"><span class="fine">Sum of weights: ${sum.toFixed(2)}</span><button type="button" class="btn btn-sm" data-act="reset-weights">Reset weights</button></div>
  </details>`;
}

function reasoningPanel(): string {
  const a = currentDecision();
  if (!a) return `<div class="empty"><p><strong>No allocation yet</strong></p><p class="muted">Decisions appear as vehicles pass the entrance gate.</p></div>`;
  const sim = store.sim;
  const selV = store.selected && store.selected.kind === 'vehicle' ? sim.vehicles[store.selected.id] : null;
  const isSel = !!selV && selV.alloc === a;
  const why = !selV ? 'Showing the latest decision. Select a vehicle to see its own.' : selV.resId ? `${selV.code} holds a reservation, so it went straight to its held bay without zone allocation. Showing the latest decision instead.` : selV.initial ? `${selV.code} parked before the scenario started. Showing the latest decision instead.` : selV.gateT < 0 ? `${selV.code} has not reached the gate yet. Showing the latest decision instead.` : 'Showing the latest decision.';
  const modeNote: Record<string, string> = {
    normal: '',
    shared: 'Every suitable zone already has drivers heading to its remaining bays, so this zone is shared.',
    'expected-departure': 'No suitable bay was free; the driver was sent where departures are expected.',
    none: 'No suitable bay was free or expected soon. An alternative should be offered.'
  };
  return `<div class="sel-head"><span class="code">${esc(a.vehicleCode)}</span><span class="muted">${esc(DEST_BY_ID[a.dest].label)} · decided at ${clockLabel(sim.scn, a.t, false)} from ${esc(a.fromLabel)}</span></div>
    ${isSel ? '' : `<p class="fine">${esc(why)}</p>`}
    <p class="explain">${esc(a.explanation)}</p>
    ${modeNote[a.mode] ? `<p class="notice warn">${icon('alert', 14)} ${esc(modeNote[a.mode])}</p>` : ''}
    <div class="cands-h"><span>Top candidate zones</span><span class="fine">${a.feasibleCount} feasible after constraints</span></div>
    ${candidateRows(a)}
    ${legendFactors()}
    <p class="msg-preview">${icon('phone', 14)} Driver sees: “${esc(a.message)}”</p>
    ${weightsDrawer('side')}`;
}

export function legendFactors(): string {
  return `<div class="factor-legend">${(Object.keys(FACTOR_SHORT) as (keyof AllocWeights)[]).map((k) => `<span><i style="background:${FACTOR_COLORS[k]}"></i>${FACTOR_SHORT[k]}</span>`).join('')}<span><i class="bonus"></i>Eligible inventory</span></div>`;
}

// ---------------- operator actions ----------------
export interface ActionDef {
  id: 'offer' | 'later' | 'floor' | 'overflow';
  title: string;
  why: string;
  what: string;
  recommended: boolean;
  applied: boolean;
  available: boolean;
  response?: number;
  responseLabel?: string;
}

export function operatorActions(): ActionDef[] {
  const sim = store.sim;
  const f = sim.forecast;
  const c = sim.counts();
  const occ = c.occupied / c.usable;
  const fill = f && f.fillMin.intent !== null ? clockLabel(sim.scn, sim.t + f.fillMin.intent * 60, false) : null;
  const pressure = occ >= 0.9 || (f && f.fillMin.intent !== null && f.fillMin.intent <= 60);
  const bestFloor = [1, 2].sort((a, b) => c.perFloor[b].generalFree - c.perFloor[a].generalFree)[0];
  const out: ActionDef[] = [];
  if (sim.scn.offer) {
    out.push({
      id: 'offer',
      title: `Pause the “${sim.scn.offer.name}” promotion`,
      why: sim.op.offerActive ? (pressure ? `Forecast reaches 95% ${fill ? `around ${fill}` : 'soon'}; the offer keeps attracting cars into a nearly full car park.` : 'Occupancy is manageable; keep the offer running for now.') : `Paused at ${clockLabel(sim.scn, sim.op.offerPausedT, false)}: ${sim.op.offerCancelled} offer-driven trips not yet under way were assumed not to come.`,
      what: 'Stops new offer redemptions for this period. Trips already under way are unaffected.',
      recommended: !!pressure && sim.op.offerActive,
      applied: !sim.op.offerActive,
      available: sim.op.offerActive,
      response: sim.op.offerResponse,
      responseLabel: 'Share of offer-driven trips (not yet under way) that will not come'
    });
  }
  out.push({
    id: 'later',
    title: "Suggest a later arrival to 'I'm coming' drivers",
    why: sim.op.laterApplied ? `Sent: ${sim.op.laterShifted} trips assumed to shift by 30 minutes.` : pressure ? `Peak demand is forecast ${fill ? `around ${fill}` : 'within the hour'}; moving some arrivals by 30 minutes flattens the peak.` : 'No peak is forecast within the next hour.',
    what: 'Sends a message (simulated) to drivers who tapped “I’m coming” and are due within 45 minutes.',
    recommended: !!pressure && !sim.op.laterApplied,
    applied: sim.op.laterApplied,
    available: !sim.op.laterApplied,
    response: sim.op.laterResponse,
    responseLabel: 'Share of notified drivers who arrive 30 minutes later'
  });
  out.push({
    id: 'floor',
    title: sim.op.floorBiasApplied >= 0 ? `Remove the ${FLOOR_NAMES[sim.op.floorBiasApplied]} guidance preference` : `Guide new arrivals towards ${FLOOR_NAMES[bestFloor]}`,
    why: sim.op.floorBiasApplied >= 0 ? `Active: new allocations add +0.12 to ${FLOOR_NAMES[sim.op.floorBiasApplied]} zones.` : `${FLOOR_NAMES[bestFloor]} has ${c.perFloor[bestFloor].generalFree} general bays free while B1 has ${c.perFloor[0].generalFree}.`,
    what: 'Adds a visible preference to the allocation score. Eligibility, capacity limits and accessible-bay protection are unchanged.',
    recommended: sim.op.floorBiasApplied < 0 && c.perFloor[0].generalFree < 6 && c.perFloor[bestFloor].generalFree > 10,
    applied: sim.op.floorBiasApplied >= 0,
    available: true
  });
  out.push({
    id: 'overflow',
    title: 'Offer an overflow option (illustrative)',
    why: sim.op.overflowApplied ? `Active: ${sim.op.overflowDiverted} drivers chose the overflow option so far.` : occ >= 0.93 ? `Occupancy is ${fmtPct(occ)}. Drivers still on the way can be offered an alternative before they queue.` : 'Occupancy is below 93%; not needed yet.',
    what: 'Shows “I’m coming” drivers an illustrative overflow car park (about 650 m walk, shuttle every 10 minutes) while occupancy is 97% or higher. No real site or partnership is implied.',
    recommended: !sim.op.overflowApplied && (occ >= 0.93 || (!!f && f.fillMin.intent !== null && f.fillMin.intent <= 30)),
    applied: sim.op.overflowApplied,
    available: !sim.op.overflowApplied,
    response: sim.op.overflowResponse,
    responseLabel: 'Share of eligible drivers who accept the overflow option'
  });
  return out;
}

function operatorPanel(): string {
  const sim = store.sim;
  const acts = operatorActions();
  const pend = store.pendingAction;
  const items = acts
    .map((a) => {
      const reviewing = pend === a.id;
      const status = a.applied ? `<span class="pill pill-muted">Applied</span>` : a.recommended ? `<span class="pill pill-warn">Recommended</span>` : `<span class="pill pill-slate">Available</span>`;
      const resp = a.response !== undefined
        ? `<label class="resp"><span>${esc(a.responseLabel || 'Response rate')} ${tag('assume')}</span>
            <input type="range" min="0.05" max="0.9" step="0.05" value="${a.response}" data-resp="${a.id}" id="resp-${a.id}" aria-label="${esc(a.responseLabel || '')}"><output>${Math.round(a.response * 100)}%</output></label>`
        : '';
      const canApply = a.id === 'floor' || a.available;
      return `<div class="action ${a.recommended ? 'rec' : ''} ${a.applied && a.id !== 'floor' ? 'done' : ''}">
        <div class="action-h"><span class="action-t">${esc(a.title)}</span>${status}</div>
        <p class="action-why">${esc(a.why)}</p>
        ${reviewing ? `<div class="review"><p>${esc(a.what)}</p>${resp}
          <div class="btn-row"><button type="button" class="btn btn-primary btn-sm" data-act="confirm-action" data-id="${a.id}">${icon('check', 14)} Confirm and apply</button>
          <button type="button" class="btn btn-sm" data-act="cancel-action">Cancel</button></div></div>`
          : canApply ? `<button type="button" class="btn btn-sm" data-act="review-action" data-id="${a.id}">Review</button>` : ''}
      </div>`;
    })
    .join('');
  const ar = sim.assistance
    .map((r) => `<li><span>${esc(r.id)} · arrival in about ${r.etaMin} min · requested ${clockLabel(sim.scn, r.t, false)}</span>${r.status === 'logged' ? `<button type="button" class="btn btn-sm" data-act="ack-assist" data-id="${r.id}">Acknowledge</button>` : '<span class="pill pill-muted">Acknowledged</span>'}</li>`)
    .join('');
  return `<p class="fine">Recommendations come from the forecast and current occupancy. Nothing is applied until you confirm it. Simulated responses use the visible assumptions.</p>
    <div class="actions">${items}</div>
    <h4 class="sub-h">Accessible-bay assistance requests</h4>
    ${ar ? `<ul class="assist">${ar}</ul>` : `<p class="fine">None yet. Drivers can request assistance from the Reservations page.</p>`}`;
}

export function applyAction(id: string) {
  const sim = store.sim;
  const a = operatorActions().find((x) => x.id === id);
  if (!a) return;
  if (id === 'offer') sim.pauseOffer(a.response ?? 0.5);
  else if (id === 'later') sim.recommendLaterArrival(a.response ?? 0.25);
  else if (id === 'floor') {
    if (sim.op.floorBiasApplied >= 0) sim.clearFloorBias();
    else {
      const c = sim.counts();
      const best = [1, 2].sort((x, y) => c.perFloor[y].generalFree - c.perFloor[x].generalFree)[0];
      sim.guideToFloor(best);
    }
  } else if (id === 'overflow') sim.enableOverflow(a.response ?? 0.3);
  store.pendingAction = null;
  toast('Operator action applied');
  emit('action');
}

export function setResponse(id: string, v: number) {
  const op = store.sim.op;
  if (id === 'offer') op.offerResponse = v;
  if (id === 'later') op.laterResponse = v;
  if (id === 'overflow') op.overflowResponse = v;
}

export function setWeight(k: keyof AllocWeights, v: number) {
  store.weights[k] = v;
  persist();
}

export function resetWeights() {
  Object.assign(store.weights, DEFAULT_WEIGHTS);
  persist();
}

// ---------------- lower cards ----------------
export function renderLower() {
  const sim = store.sim;
  const chartEl = $('#chart-occ');
  const w = Math.max(280, chartEl.clientWidth || 420);
  setHTML(chartEl, occupancyChart(sim, sim.forecast, { w, h: Math.max(150, chartEl.clientHeight || 170) }));
  renderFloors();
  renderEvents();
}

function renderFloors() {
  const sim = store.sim;
  const c = sim.counts();
  const generalTotal = sim.L.bays.filter((b) => b.type === 'general' && b.flag === 'none').length;
  const drivingByFloor = [0, 0, 0];
  for (const v of sim.searchingVehicles()) drivingByFloor[sim.vehicleFloor(v)]++;
  const rows = [0, 1, 2]
    .map((f) => {
      const p = c.perFloor[f];
      const n = p.generalFree;
      const tone = n === 0 ? 'full' : n <= 8 ? 'low' : 'ok';
      const seg = (k: number, cls: string, label: string) => (k > 0 ? `<i class="${cls}" style="flex:${k}" title="${label}: ${k}"></i>` : '');
      const occNoDep = p.occupied - p.departing - p.uncertain;
      const zones = ZONES.map((z) => {
        const k = sim.L.bays.filter((b) => b.floor === f && b.zone === z && b.type === 'general' && sim.isFree(b.idx)).length;
        return `<span class="zc zc-${z.toLowerCase()} ${k === 0 ? 'z0' : k <= 2 ? 'z1' : ''}" title="Zone ${z}: ${k} general bays free"><i></i>${z}<b>${k}</b></span>`;
      }).join('');
      const s = drivingByFloor[f];
      return `<button type="button" class="lvl lvl-${tone}" data-act="floor" data-floor="${f}" aria-pressed="${store.floorView === f}" title="Show ${FLOOR_NAMES[f]} in the model">
        <span class="plate">${FLOOR_NAMES[f]}</span>
        <span class="led">${dotMatrix(n === 0 ? 'FULL' : String(n), 4, 4.4, n === 0 ? 'Full' : String(n))}</span>
        <span class="sr">${n} general free on ${FLOOR_NAMES[f]}.</span>
        <span class="lvl-meta"><span class="zones">${zones}</span><span class="lvl-s">${s ? `${s} car${s === 1 ? '' : 's'} searching` : 'No one searching'}</span></span>
        <span class="stack" aria-hidden="true">${seg(occNoDep, 's-occ', 'Taken')}${seg(p.departing, 's-dep', 'Leaving soon')}${seg(p.uncertain, 's-unc', 'Camera unsure')}${seg(p.reserved, 's-res', 'Held')}${seg(p.specialFree, 's-spf', 'Special free')}${seg(p.generalFree, 's-gen', 'General free')}</span>
      </button>`;
    })
    .join('');
  setHTML($('#floors-body'), rows);
  const tot = $('#board-total');
  tot.title = `General bays only. Also ${c.specialFree} special bays free, ${c.reserved} held for bookings, ${c.uncertain} with an uncertain camera view.`;
  setHTML(tot, `<b>${c.generalFree}</b> of ${generalTotal} free`);
}

const EVENT_GROUPS: Record<string, string[]> = {
  all: [],
  guidance: ['guide', 'reroute'],
  bays: ['park', 'depart', 'payment'],
  reservations: ['reservation'],
  operator: ['operator', 'forecast', 'alert']
};

function renderEvents() {
  const sim = store.sim;
  const g = EVENT_GROUPS[store.eventFilter] || [];
  const list: SimEvent[] = [];
  for (let i = sim.events.length - 1; i >= 0 && list.length < 60; i--) {
    const e = sim.events[i];
    if (!g.length || g.includes(e.kind)) list.push(e);
  }
  const html = list.length
    ? list
        .map((e) => {
          const ts = clockLabel(sim.scn, e.t, false) + ':' + String(Math.floor(e.t % 60)).padStart(2, '0');
          const target = e.vehicle !== undefined ? `data-act="select-vehicle" data-id="${e.vehicle}"` : e.bay !== undefined ? `data-act="select-bay" data-id="${e.bay}"` : '';
          return `<li class="ev ev-${e.tone}" ${target} ${target ? 'role="button" tabindex="0"' : ''}><time>${ts}</time><span class="ev-t"><b class="ev-k">${esc(KIND_LABEL[e.kind] || e.kind)}</b> ${esc(e.text)}</span></li>`;
        })
        .join('')
    : `<li class="ev-empty">No events in this category yet.</li>`;
  setHTML($('#events-list'), html);
  for (const b of Array.from($('#event-filters').children) as HTMLElement[]) b.setAttribute('aria-pressed', String(b.dataset.filter === store.eventFilter));
}

const KIND_LABEL: Record<string, string> = { guide: 'Guidance', reroute: 'Route update', park: 'Parked', depart: 'Departure', payment: 'Payment', reservation: 'Reservation', operator: 'Operator', forecast: 'Forecast', alert: 'Alert' };

export function initLowerStatic() {
  setHTML($('#event-filters'), Object.keys(EVENT_GROUPS).map((k) => `<button type="button" data-filter="${k}" aria-pressed="false">${k[0].toUpperCase() + k.slice(1)}</button>`).join(''));
  setHTML($('#chart-legend'), legendItems([
    { color: 'var(--ink)', label: 'Measured' },
    { color: 'var(--ink-3)', label: 'History forecast', dash: true },
    { color: 'var(--teal)', label: 'History + intent', dash: true },
    { color: 'var(--teal)', label: 'Assumed range', band: true }
  ]));
}

// ---------------- driver preview ----------------
export function renderPhone(force = false) {
  const el = $('#phone');
  el.classList.toggle('collapsed', store.driver.collapsed);
  $('#phone-toggle').setAttribute('aria-expanded', String(!store.driver.collapsed));
  if (store.driver.collapsed) return;
  if (!force && focusedWithin(el)) return;
  const sim = store.sim;
  const sel = store.selected;
  const v = sel && sel.kind === 'vehicle' ? sim.vehicles[sel.id] : null;
  setHTML($('#phone-screen'), v && v.gateT >= 0 ? phoneForVehicle(sim, v) : phonePlan(sim));
}

function alternativesHTML(sim: Sim, dest: DestId): string {
  const f = sim.forecast;
  const later = f ? clockLabel(sim.scn, sim.t + 45 * 60, false) : '';
  return `<div class="ph-alt"><div class="ph-kicker">${icon('alert', 13)} Alternatives</div>
    <ul>
      <li><b>Wait nearby</b> · departures are expected; you will be guided when a bay frees up.</li>
      <li><b>Overflow car park</b> <span class="muted">(illustrative)</span> · about 650 m walk, shuttle every 10 min.</li>
      <li><b>Arrive later</b> · forecast is easier after about ${later}.</li>
      <li><b>Public transport</b> · drop-off point at the ${esc(DEST_BY_ID[dest].label)} entrance.</li>
    </ul></div>`;
}

function phoneForVehicle(sim: Sim, v: Vehicle): string {
  const lift = DEST_BY_ID[v.dest].lift;
  if (v.state === 'parked' || v.state === 'unparking' || v.state === 'leaving' || v.state === 'exited') {
    const b = v.bay >= 0 ? sim.L.bays[v.bay] : null;
    return `<div class="ph-who">${esc(v.code)} · ${esc(DEST_BY_ID[v.dest].label)}</div>
      ${b && v.parkT >= 0 ? `<div class="ph-card ok"><div class="ph-kicker">Parked</div><div class="ph-instr">${esc(b.id)} · ${FLOOR_NAMES[b.floor]} Zone ${b.zone}</div><div class="ph-sub">Walk ≈ ${b.walk[lift]} m to Lift ${lift}. “Find my car” will point back here.</div></div>` : `<div class="ph-card"><div class="ph-kicker">${esc(vehicleStateLabel(sim, v))}</div><div class="ph-sub">This trip ended without parking.</div></div>`}
      ${v.gateT >= 0 && v.parkT >= 0 ? `<div class="ph-stats"><div><b>${fmtSecs(v.parkT - v.gateT)}</b><span>Gate to bay</span></div><div><b>${fmtDist(v.searchDist)}</b><span>Driven</span></div></div>` : ''}
      <p class="ph-fine">Simulation-derived location. Indoor phone positioning is not implemented.</p>`;
  }
  const est = driveEstimate(sim, v);
  const a = v.alloc;
  let instr: string;
  if (v.resId && v.bay >= 0) {
    const b = sim.L.bays[v.bay];
    instr = `Proceed to ${FLOOR_NAMES[b.floor]} · Zone ${b.zone} · Reserved bay ${b.id}.`;
  } else instr = a ? a.message : 'Follow the signs; guidance appears once you pass the gate.';
  const walk = v.bay >= 0 ? sim.L.bays[v.bay].walk[lift] : a && a.chosen ? Math.round(a.chosen.walk) : NaN;
  const needAlt = a && (a.mode === 'none' || a.mode === 'expected-departure');
  return `<div class="ph-who">${esc(v.code)} · ${esc(DEST_BY_ID[v.dest].label)}</div>
    ${v.state === 'queued' ? `<div class="ph-card"><div class="ph-kicker">At the entrance</div><div class="ph-sub">Waiting for the barrier. Guidance appears at the gate.</div></div>` : `<div class="ph-card ph-guide"><div class="ph-kicker">Your parking guidance</div><div class="ph-instr">${esc(instr)}</div></div>`}
    ${v.notice && v.notice.startsWith('Updated route') ? `<div class="ph-update">${icon('reset', 13)} ${esc(v.notice)}</div>` : ''}
    <div class="ph-stats">
      <div><b>≈ ${fmtShort(est.s)}</b><span>Driving · ${fmtDist(est.m)}</span></div>
      <div><b>${isFinite(walk) ? `≈ ${fmtShort(walk / 1.2)}` : '–'}</b><span>Walking · ${isFinite(walk) ? walk + ' m' : '–'}</span></div>
    </div>
    ${needAlt ? alternativesHTML(sim, v.dest) : ''}
    <p class="ph-fine">Location shown is simulation-derived. Indoor phone positioning is not implemented.</p>`;
}

function phonePlan(sim: Sim): string {
  const d = store.driver;
  const elig: BayType[] = ['general'];
  if (d.ev) elig.push('ev');
  if (d.family) elig.push('family');
  if (d.member) elig.push('member');
  const c = sim.counts();
  const a = sim.previewAllocation(d.dest, elig);
  const lift = DEST_BY_ID[d.dest].lift;
  const f = sim.forecast;
  const dist = a.chosen ? a.chosen.drive + 20 : NaN;
  const resOpts = (['ev', 'family', 'member'] as const)
    .filter((t) => (t === 'ev' && d.ev) || (t === 'family' && d.family) || (t === 'member' && d.member))
    .map((t) => {
      const q = sim.bookable(t);
      return `<li>${esc(BAY_TYPE_LABEL[t])}: <b>${q.bookable}</b> bookable now <button type="button" class="linkbtn" data-go="reservations">Reserve</button></li>`;
    })
    .join('');
  const needAlt = a.mode === 'none' || a.mode === 'expected-departure';
  return `<div class="ph-who">Plan a visit</div>
    <label class="ph-field"><span>Going to</span><select data-act="driver-dest" id="driver-dest">${DESTINATIONS.map((x) => `<option value="${x.id}" ${x.id === d.dest ? 'selected' : ''}>${esc(x.label)}</option>`).join('')}</select></label>
    <div class="ph-toggles">
      <label><input type="checkbox" data-act="driver-flag" data-flag="ev" id="drv-ev" ${d.ev ? 'checked' : ''}> EV</label>
      <label><input type="checkbox" data-act="driver-flag" data-flag="family" id="drv-family" ${d.family ? 'checked' : ''}> Family pass</label>
      <label><input type="checkbox" data-act="driver-flag" data-flag="member" id="drv-member" ${d.member ? 'checked' : ''}> Member</label>
    </div>
    <div class="ph-cap"><b>${c.generalFree}</b> general bays free now <span class="muted">(B1 ${c.perFloor[0].generalFree} · B2 ${c.perFloor[1].generalFree} · B3 ${c.perFloor[2].generalFree})</span></div>
    ${f && f.fillMin.intent !== null ? `<div class="ph-fc">${icon('forecast', 13)} Forecast: about 95% full by ${clockLabel(sim.scn, sim.t + f.fillMin.intent * 60, false)}</div>` : ''}
    <div class="ph-card ph-guide"><div class="ph-kicker">If you arrived now</div><div class="ph-instr">${esc(a.message)}</div></div>
    <div class="ph-stats"><div><b>≈ ${fmtShort(dist / 3)}</b><span>Driving from gate</span></div><div><b>${a.chosen ? `≈ ${Math.round(a.chosen.walk)} m` : '–'}</b><span>Walk to Lift ${lift}</span></div></div>
    ${resOpts ? `<ul class="ph-res">${resOpts}</ul>` : ''}
    ${needAlt ? alternativesHTML(sim, d.dest) : ''}
    <p class="ph-fine">Select a vehicle in the model to follow its guidance. Accessible-bay help is requested from the Reservations page.</p>`;
}

export function signedPct(x: number): string {
  return signed(x, 0, '%');
}
