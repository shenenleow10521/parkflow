// About 90 seconds of guided walkthrough. Each caption is computed from the live state when shown.

import { store, emit, resetSim, runMatchedComparison, Section } from './store';
import { $, esc, icon, fmtSecs, fmtDist, fmtPct, prefersReducedMotion } from './dom';
import { SceneView } from '../render/gl3d';
import { clockLabel } from '../core/scenarios';
import { FLOOR_NAMES, DEST_BY_ID, BAY_TYPE_LABEL, typeText } from '../core/layout';

interface Step {
  title: string;
  setup: () => void;
  caption: () => string;
}

export const pres = { active: false, step: 0, paused: false, stepStart: 0, stepMs: 15000 };
let presScene: SceneView;
let presGo: (s: Section) => void;

export function initPresentation(s: SceneView, go: (s: Section) => void) {
  presScene = s;
  presGo = go;
}

function spotlight(id: string | null) {
  for (const el of Array.from(document.querySelectorAll('.spot'))) el.classList.remove('spot');
  if (id) document.getElementById(id)?.classList.add('spot');
}

const STEPS: Step[] = [
  {
    title: 'Weekend congestion',
    setup: () => {
      if (store.scenarioId !== 'surge') store.scenarioId = 'surge';
      resetSim(0);
      store.sim.runTo(22 * 60);
      store.speed = 5;
      store.playing = true;
      presGo('overview');
      store.floorView = 0;
      store.planView = false;
      emit('floor');
      presScene.fit(true);
      spotlight(null);
    },
    caption: () => {
      const sim = store.sim;
      const c = sim.counts();
      const s = sim.searchingVehicles().length;
      return `Weekend surge at ${sim.clock(false)} MYT. ${fmtPct(c.occupied / c.usable)} of usable bays are taken and ${s} vehicle${s === 1 ? ' is' : 's are'} searching. B1, nearest the entrance and Lifts A and B, has ${c.perFloor[0].generalFree} general bays left.`;
    }
  },
  {
    title: 'The arrival wave ahead',
    setup: () => {
      presGo('overview');
      store.floorView = 'all';
      emit('floor');
      presScene.fit(true);
      spotlight('card-chart');
    },
    caption: () => {
      const sim = store.sim;
      const f = sim.forecast;
      if (!f) return 'Forecast unavailable.';
      const fill = f.fillMin.intent !== null ? `reaching 95% around ${clockLabel(sim.scn, sim.t + f.fillMin.intent * 60, false)}` : 'staying below 95% for the next hour';
      return `With the ice show, the active offer and 'I'm coming' drivers, the forecast expects ${Math.round(f.arr30.intent)} arrivals in the next 30 minutes, ${fill}. Occupancy history alone expects ${Math.round(f.arr30.hist)}.`;
    }
  },
  {
    title: 'One allocation decision',
    setup: () => {
      presGo('overview');
      spotlight(null);
      const sim = store.sim;
      let dec = null;
      for (let i = sim.decisions.length - 1; i >= 0; i--) {
        const d = sim.decisions[i];
        const v = sim.vehicles[d.vehicle];
        if (v && v.state === 'driving' && d.chosen) { dec = d; break; }
      }
      dec = dec || sim.decisions[sim.decisions.length - 1];
      if (!dec) return;
      store.selected = { kind: 'vehicle', id: dec.vehicle };
      store.rightTab = 'reasoning';
      emit('select');
      presScene.focusVehicle(sim.vehicles[dec.vehicle]);
    },
    caption: () => {
      const sim = store.sim;
      const sel = store.selected;
      const v = sel && sel.kind === 'vehicle' ? sim.vehicles[sel.id] : null;
      if (!v || !v.alloc) return 'Select a guided vehicle to see its decision.';
      return `${v.code}, heading for ${DEST_BY_ID[v.dest].label}: ${v.alloc.explanation}`;
    }
  },
  {
    title: 'Simultaneous arrivals',
    setup: () => {
      presGo('overview');
      spotlight(null);
      const sim = store.sim;
      const burst = sim.injectArrivals(4, 'atrium');
      store.demoBurst = burst.map((v) => v.i);
      sim.runTo(sim.t + 40);
      store.selected = { kind: 'vehicle', id: burst[burst.length - 1].i };
      store.rightTab = 'reasoning';
      store.floorView = 'all';
      emit('floor');
      emit('select');
      presScene.fit(true);
    },
    caption: () => {
      const sim = store.sim;
      const vs = store.demoBurst.map((i) => sim.vehicles[i]).filter(Boolean);
      const guided = vs.filter((v) => v.alloc && v.alloc.chosen);
      if (!guided.length) return 'Four drivers are waiting at the entrance.';
      const t0 = Math.min(...guided.map((v) => v.gateT));
      const t1 = Math.max(...guided.map((v) => v.gateT));
      const zones = new Set(guided.map((v) => v.alloc!.chosen!.label));
      const list = guided.map((v) => `${v.code} → ${v.alloc!.chosen!.label}`).join(', ');
      const waiting = vs.length - guided.length;
      return `Four drivers for the Main atrium passed the gate within ${t1 - t0} s. Instead of sending all of them to the same apparent vacancy, ParkFlow used ${zones.size} zone${zones.size === 1 ? '' : 's'}: ${list}.${waiting ? ` ${waiting} still at the entrance.` : ''}`;
    }
  },
  {
    title: 'Reservation and no-show release',
    setup: () => {
      presGo('overview');
      spotlight(null);
      const sim = store.sim;
      const r = sim.reservations.find((x) => !x.userCreated && sim.scn.reservations.find((d) => d.id === x.id && d.noShow));
      if (r && r.status === 'confirmed') sim.runTo(r.windowEnd + r.grace + 2);
      if (r) {
        store.selected = { kind: 'bay', id: r.bay };
        store.rightTab = 'vehicle';
        emit('select');
        presScene.focusBay(sim.L.bays[r.bay]);
      }
    },
    caption: () => {
      const sim = store.sim;
      const r = sim.reservations.find((x) => !x.userCreated && sim.scn.reservations.find((d) => d.id === x.id && d.noShow));
      const ok = sim.reservations.find((x) => x.status === 'parked' || x.status === 'checked-in');
      let txt = '';
      if (ok) txt += `${ok.id} (${typeText(ok.type)}) checked in at ${clockLabel(sim.scn, ok.checkInT, false)} and was routed straight to its held bay. `;
      if (r && r.status === 'expired') txt += `${r.id} (${typeText(r.type)}) never arrived: its hold expired at ${clockLabel(sim.scn, r.closedT, false)} after the 10-minute grace period, and bay ${sim.L.bays[r.bay].id} went back to ${typeText(r.type)} inventory, not general parking.`;
      else if (r) txt += `${r.id} is still within its window; it will be released at ${clockLabel(sim.scn, r.windowEnd + r.grace, false)} if nobody arrives.`;
      return txt || 'No reservation in this scenario.';
    }
  },
  {
    title: 'Matched-run comparison',
    setup: () => {
      spotlight(null);
      if (!store.comparison || store.comparison.scenarioId !== store.scenarioId || store.comparisonStale) {
        runMatchedComparison();
        store.comparisonStale = false;
      }
      store.playing = false;
      presGo('impact');
    },
    caption: () => {
      const c = store.comparison;
      if (!c) return 'Run the comparison to see results.';
      const B = c.baseline, G = c.guided;
      const unres = (r: typeof B) => r.stillSearching + r.gaveUp + r.diverted + r.notAdmitted;
      return `Same ${B.scheduled} arrivals, same seed. Mean gate-to-park ${fmtSecs(B.meanG2P)} → ${fmtSecs(G.meanG2P)}; P90 ${fmtSecs(B.p90G2P)} → ${fmtSecs(G.p90G2P)}; mean search distance ${fmtDist(B.meanSearchDist)} → ${fmtDist(G.meanSearchDist)}. Unresolved vehicles: ${unres(B)} without guidance, ${unres(G)} with it.`;
    }
  }
];

export function startPresentation() {
  pres.active = true;
  pres.paused = false;
  pres.step = 0;
  $('#pres').hidden = false;
  document.body.classList.add('pres-open');
  enter(0);
}

function enter(i: number) {
  pres.step = i;
  pres.stepStart = performance.now();
  STEPS[i].setup();
  renderPres(true);
  emit('pres');
}

export function presNext() {
  if (pres.step < STEPS.length - 1) enter(pres.step + 1);
}

export function presBack() {
  if (pres.step > 0) enter(pres.step - 1);
}

export function presToggle() {
  pres.paused = !pres.paused;
  pres.stepStart = performance.now();
  renderPres(true);
}

export function presExit() {
  pres.active = false;
  $('#pres').hidden = true;
  document.body.classList.remove('pres-open');
  for (const el of Array.from(document.querySelectorAll('.spot'))) el.classList.remove('spot');
  emit('pres');
}

export function presTick() {
  if (!pres.active) return;
  if (!pres.paused && pres.step < STEPS.length - 1 && performance.now() - pres.stepStart > pres.stepMs) presNext();
  renderPres(false);
}

export function renderPres(force: boolean) {
  if (!pres.active) return;
  const s = STEPS[pres.step];
  const dots = STEPS.map((x, i) => `<span class="pd ${i === pres.step ? 'on' : i < pres.step ? 'done' : ''}" title="${esc(x.title)}"></span>`).join('');
  const progress = pres.paused || pres.step === STEPS.length - 1 ? 0 : Math.min(1, (performance.now() - pres.stepStart) / pres.stepMs);
  const html = `<div class="pres-top"><div class="pdots">${dots}</div><span class="pstep">Step ${pres.step + 1} of ${STEPS.length}</span></div>
    <h3>${esc(s.title)}</h3>
    <p class="pcap">${esc(s.caption())}</p>
    <div class="pbar"><i style="width:${(progress * 100).toFixed(1)}%"></i></div>
    <div class="pctl">
      <button type="button" class="btn btn-sm btn-dark" data-pres="back" ${pres.step === 0 ? 'disabled' : ''}>${icon('left', 14)} Back</button>
      <button type="button" class="btn btn-sm btn-dark" data-pres="pause">${pres.paused ? `${icon('play', 14)} Resume` : `${icon('pause', 14)} Pause`}</button>
      <button type="button" class="btn btn-sm btn-light" data-pres="next" ${pres.step === STEPS.length - 1 ? 'disabled' : ''}>Next ${icon('right', 14)}</button>
      <button type="button" class="btn btn-sm btn-dark" data-pres="exit">${icon('x', 14)} Exit</button>
    </div>`;
  // Rebuild the controls only when the step or pause state changes, so buttons stay put under the
  // pointer; the live caption and the progress bar update in place.
  const el = $('#pres-body');
  const key = `${pres.step}|${pres.paused}`;
  if (force || el.dataset.key !== key) {
    el.innerHTML = html;
    el.dataset.key = key;
  } else {
    const cap = el.querySelector('.pcap') as HTMLElement | null;
    const text = s.caption();
    if (cap && cap.textContent !== text) cap.textContent = text;
    const bar = el.querySelector('.pbar i') as HTMLElement | null;
    if (bar) bar.style.width = `${(progress * 100).toFixed(1)}%`;
  }
  void prefersReducedMotion;
  void FLOOR_NAMES;
}
