// Forecast, Allocation, Reservations and Impact sections. All read the same live Sim and store.

import { store, persist, FieldObs } from './store';
import { $, esc, setHTML, fmtPct, fmtSecs, fmtDist, fmtNum, icon, tag, signed } from './dom';
import { Sim } from '../core/sim';
import { ASSUMPTION_META, DEFAULT_ASSUMPTIONS, ForecastAssumptions } from '../core/forecast';
import { BAY_TYPE_LABEL, FLOOR_NAMES, ZONES, DEST_BY_ID, DESTINATIONS, BOOKABLE_TYPES } from '../core/layout';
import { clockLabel, clockFromMin, SCENARIO_BY_ID } from '../core/scenarios';
import { arrivalsChart, legendItems, COMPONENT_LABELS, g2pHistogram, searchingChart, fieldStrip, flowPanel, memberLivePanel, memberHistoryPanel } from './charts';
import { candidateRows, legendFactors, weightsDrawer, operatorActions } from './panels';
import { pctChange, RunSummary } from '../core/metrics';
import { mean, percentile } from '../core/rng';

function pageFocused(el: HTMLElement): boolean {
  const a = document.activeElement as HTMLElement | null;
  return !!a && el.contains(a) && (a.tagName === 'INPUT' || a.tagName === 'SELECT' || a.tagName === 'TEXTAREA');
}

function draft(key: string, fallback = ''): string {
  return esc(store.drafts[key] ?? fallback);
}

function chartWidth(id: string, fallback: number): number {
  const el = document.getElementById(id);
  return el && el.clientWidth > 50 ? el.clientWidth : fallback;
}

// ================= Forecast =================
export function renderForecast(force = false) {
  const root = $('#view-forecast');
  if (!force && pageFocused(root)) return;
  const sim = store.sim;
  const s = sim.scn;
  const f = sim.forecast;
  const a = store.assumptions;
  const wHalf = chartWidth('fc-occ', 1200);
  const wArr = chartWidth('fc-arr', 520);
  const wMem = chartWidth('fc-mem', 560);
  const signals: [string, string][] = [];
  signals.push(['Cinema attendance', s.cinema ? `${clockFromMin(s.cinema.showtimeMin)} screening · ${s.cinema.tickets} tickets sold` : 'No major screening in this window']);
  signals.push(['Restaurant bookings', s.dining ? s.dining.slots.map((x) => `${clockFromMin(x.min)} · ${x.covers} covers`).join('; ') : 'No large bookings in this window']);
  signals.push(['Mall event schedule', s.event ? `${s.event.name} · ${s.event.expectedVisitors} expected visitors` : 'No event scheduled']);
  signals.push(['Parking offers', s.offer ? `${s.offer.name} · ${s.offer.outstanding} vouchers outstanding · ~${s.offer.redeemPerHour}/h · ${sim.op.offerActive ? 'active' : 'paused'}` : 'No active offer']);
  const etas = sim.comingETAs();
  signals.push(["'I'm coming' drivers", etas.length ? `${etas.length} with ETAs in the next 45 min (earliest ${clockLabel(s, Math.min(...etas), false)})` : 'None in the next 45 minutes']);
  signals.push(['Opted-in member visit pattern', `Index ${s.memberIndexSignal.toFixed(2)} vs a typical ${s.day === 'Sat' ? 'Saturday' : 'weekday'} (aggregated)`]);

  const comps = ['history', 'member', 'cinema', 'dining', 'event', 'offer', 'coming'] as const;
  const basis: Record<string, string> = {
    history: `Typical ${s.day === 'Sat' ? 'Saturday' : 'weekday'} arrival profile at this time`,
    member: `History × (member index − 1)`,
    cinema: s.cinema ? `${s.cinema.tickets} × ${fmtPct(a.cinemaCarShare)} by car ÷ ${a.cinemaParty} per car × (1 − ${fmtPct(s.dining ? a.overlapCinemaDining : 0)} overlap), peaking ${a.cinemaLeadMin} min before showtime` : 'No screening',
    dining: s.dining ? `Covers × ${fmtPct(a.diningCarShare)} by car ÷ ${a.diningParty} per car, around booking times` : 'No bookings',
    event: s.event ? `${s.event.expectedVisitors} × ${fmtPct(a.eventCarShare)} by car ÷ ${a.eventParty} per car, peaking 30 min before start` : 'No event',
    offer: s.offer ? `${s.offer.redeemPerHour}/h × ${fmtPct(a.offerCarShare)} by car while active` : 'No offer',
    coming: `Known ETAs × (1 − ${fmtPct(a.comingOverlap)} already in history)`
  };
  const sum = (arr: number[], n: number) => arr.slice(0, n).reduce((x, y) => x + y, 0);
  const convRows = f
    ? comps.map((c) => `<tr><td><i class="dot" style="background:var(--c-${c === 'history' ? 'hist' : c})"></i>${esc(COMPONENT_LABELS[c])}</td><td class="num">${fmtNum(sum(f.components[c], 30), 1)}</td><td class="num">${fmtNum(sum(f.components[c], 60), 1)}</td><td class="fine">${esc(basis[c])}</td></tr>`).join('')
    : '';
  const matured = sim.snapshots.filter((sn) => sn.forT <= sim.t).slice(-6).reverse();
  const actualAt = (t: number) => {
    const r = sim.history.find((h) => h.t >= t);
    return r ? r.occupied : NaN;
  };
  const errRows = matured
    .map((sn) => {
      const act = actualAt(sn.forT);
      const u = sim.usable;
      return `<tr><td>${clockLabel(s, sn.madeT, false)} → ${clockLabel(s, sn.forT, false)}</td><td class="num">${fmtPct(sn.hist / u)}</td><td class="num">${fmtPct(sn.intent / u)}</td><td class="num"><b>${fmtPct(act / u)}</b></td><td class="num">${signed(((sn.hist - act) / u) * 100, 0, ' pts')}</td><td class="num">${signed(((sn.intent - act) / u) * 100, 0, ' pts')}</td></tr>`;
    })
    .join('');
  const nextCheck = sim.snapshots.find((sn) => sn.forT > sim.t);
  const mae = (key: 'hist' | 'intent') => {
    const all = sim.snapshots.filter((sn) => sn.forT <= sim.t);
    if (!all.length) return NaN;
    return mean(all.map((sn) => Math.abs(sn[key] - actualAt(sn.forT)) / sim.usable)) * 100;
  };
  const acts = operatorActions().filter((x) => x.recommended);

  // ----- live refresh state: the forecast is recomputed every simulated minute -----
  const log = sim.forecastLog;
  const cur = log[log.length - 1];
  const before = (secs: number) => {
    for (let i = log.length - 1; i >= 0; i--) if (log[i].t <= sim.t - secs) return log[i];
    return null;
  };
  const prev5 = before(300);
  if (cur && cur.t !== fcSeen.t) {
    fcSeen.flashUntil = fcSeen.t >= 0 ? performance.now() + 1300 : 0;
    fcSeen.t = cur.t;
  }
  const flash = performance.now() < fcSeen.flashUntil;
  const nextIn = 60 - (sim.t % 60);
  const liveTxt = sim.t >= sim.tEnd ? 'Run complete' : store.playing ? `Updated ${clockLabel(s, cur ? cur.t : sim.t, false)}, next in ${Math.max(1, Math.ceil(nextIn / Math.max(1, store.speed)))} s` : `Updated ${clockLabel(s, cur ? cur.t : sim.t, false)}, paused`;
  const delta = (now: number, then: number | undefined, unit = '') => {
    if (then === undefined || !isFinite(now) || !isFinite(then)) return '';
    const d = Math.round(now - then);
    if (d === 0) return `<span class="delta">no change in 5 min</span>`;
    return `<span class="delta ${d > 0 ? 'up' : 'down'}">${d > 0 ? '+' : '−'}${Math.abs(d)}${unit} in 5 min</span>`;
  };

  // ----- 1. guidance: zone pressure and decisions the forecast changed -----
  const ctx = sim.allocContext();
  const outlook: { f: number; z: typeof ZONES[number]; free: number; heading: number; expected: number; minutes: number }[] = [];
  for (const fl of [0, 1, 2])
    for (const z of ZONES) {
      const free = sim.L.bays.filter((b) => b.floor === fl && b.zone === z && b.type === 'general' && sim.isFree(b.idx)).length;
      const heading = sim.headingCount(fl, z, 'general');
      const expected = ctx.forecastByLift(z) / 3;
      const eff = free - heading;
      const minutes = eff <= 0 ? 0 : expected > 0.05 ? eff / (expected / 30) : Infinity;
      outlook.push({ f: fl, z, free, heading, expected, minutes });
    }
  const pressured = outlook.filter((o) => o.free > 0 && o.minutes < 30).sort((a, b) => a.minutes - b.minutes);
  const recent = sim.decisions.filter((d) => d.t >= sim.t - 900 && d.chosen);
  const flips = recent.filter((d) => d.withoutForecast);
  const lastFlip = flips[flips.length - 1];
  let gHead: string, gBody: string;
  if (flips.length) {
    gHead = `Changed ${flips.length} of ${recent.length} picks in 15 min`;
    gBody = `Latest: ${lastFlip.vehicleCode} went to ${lastFlip.chosen!.label} instead of ${lastFlip.withoutForecast!.label}, which is expected to fill first.`;
  } else if (pressured.length) {
    const p0 = pressured[0];
    gHead = `Watching ${FLOOR_NAMES[p0.f]} Zone ${p0.z}`;
    gBody = `It could fill in about ${Math.max(1, Math.round(p0.minutes))} min. No pick has needed to change yet${recent.length ? ` (${recent.length} in the last 15 min)` : ''}: zones nearer the lifts still have room.`;
  } else {
    gHead = 'No zone under pressure';
    gBody = 'Expected arrivals fit every zone for the next 30 minutes, so guidance is choosing on walking distance and traffic.';
  }

  // ----- 2. driver app: what shoppers are told before they leave home -----
  const peak = cur ? cur.peak : NaN;
  let dHead: string, dBody: string;
  if (f && f.fillMin.intent !== null) {
    const fillAt = sim.t + f.fillMin.intent * 60;
    dHead = `“Nearly full by ${clockLabel(s, fillAt, false)}”`;
    dBody = f.fillMin.intent > 20 ? `Drivers are told to come before ${clockLabel(s, fillAt - 15 * 60, false)} or book a Ladies' parking or designated member bay.` : 'Drivers are told to expect a short wait; guidance sends them to the next free zone.';
  } else if (peak >= 0.85) {
    dHead = '“Getting busy”';
    dBody = `The app shows about ${Math.round(peak * 100)}% full at the busiest point in the next hour.`;
  } else {
    dHead = '“Plenty of space”';
    dBody = 'The app shows no queue expected in the next hour.';
  }
  dBody += ` ${etas.length} driver${etas.length === 1 ? ' has' : 's have'} shared an ETA; ${etas.length === 1 ? 'that trip is' : 'those trips are'} already in this forecast.`;

  // ----- 3. operator -----
  const oHead = acts.length ? `${acts.length} action${acts.length === 1 ? '' : 's'} suggested` : 'No action needed';
  const oBody = acts.length ? acts.map((x) => esc(x.title)).join('. ') + '.' : `Peak forecast is ${isFinite(peak) ? Math.round(peak * 100) : '–'}% in the next hour. The team is alerted when it reaches 95%.`;

  const maeH = mae('hist');
  const maeI = mae('intent');
  const maxMae = Math.max(maeH || 0, maeI || 0, 1);
  const accHead = isFinite(maeH) && isFinite(maeI) && maeI > 0.05 ? (maeH / maeI >= 1.2 ? `Intent signals made it ${fmtNum(maeH / maeI, 1)}× more accurate` : maeI > maeH * 1.2 ? 'History alone has been closer so far' : 'Both forecasts are performing similarly') : '';

  const zoneHead = ZONES.map((z) => `<div class="zg-h"><i class="zsw zsw-${z.toLowerCase()}"></i><b>Zone ${z}</b><span>Lift ${z}, about ${fmtNum(ctx.forecastByLift(z), 0)} cars in 30 min</span></div>`).join('');
  const zoneRows = [0, 1, 2]
    .map((fl) => `<div class="zg-f"><span class="plate-sm">${FLOOR_NAMES[fl]}</span></div>${ZONES.map((z) => {
      const o = outlook.find((x) => x.f === fl && x.z === z)!;
      const tone = o.free === 0 || o.minutes <= 0 ? 'full' : o.minutes <= 10 ? 'crit' : o.minutes < 30 ? 'warn' : 'ok';
      const head = o.free === 0 ? 'Full now' : o.minutes <= 0 ? 'Taken by cars on the way' : o.minutes < 30 ? `Full in ~${Math.max(1, Math.round(o.minutes))} min` : 'Room for 30+ min';
      return `<div class="zg zg-${tone}"><b>${head}</b><span>${o.free} free, ${o.heading} on the way, ~${fmtNum(o.expected, 1)} expected</span></div>`;
    }).join('')}`)
    .join('');

  const html = `
  <div class="page-head">
    <div><h2>Demand forecast</h2><p class="lede">Expected arrivals for the next hour, refreshed every simulated minute from what is known at that moment. It steers guidance, what the driver app tells shoppers, and when the team is alerted.</p></div>
    <div class="fc-head-r"><span class="live-chip ${flash ? 'flash' : ''}" aria-live="off"><i></i>${esc(liveTxt)}</span><div class="tags">${tag('now', 'Measured')} ${tag('fc')} ${tag('synthetic')}</div></div>
  </div>
  <section class="fc-impact ${flash ? 'flash' : ''}" aria-label="What the forecast is steering now">
    <article class="fi">
      <div class="fi-h">${icon('allocation', 16)}<span>Guidance</span></div>
      <b class="fi-big">${esc(gHead)}</b>
      <p>${esc(gBody)}</p>
      <button type="button" class="linkbtn" data-go="allocation">See the decisions</button>
    </article>
    <article class="fi">
      <div class="fi-h">${icon('phone', 16)}<span>Driver app</span></div>
      <b class="fi-big">${esc(dHead)}</b>
      <p>${esc(dBody)}</p>
    </article>
    <article class="fi">
      <div class="fi-h">${icon('alert', 16)}<span>Operator</span></div>
      <b class="fi-big">${esc(oHead)}</b>
      <p>${oBody}</p>
      ${acts.length ? `<button type="button" class="linkbtn" data-act="open-actions">Review and confirm</button>` : ''}
    </article>
  </section>
  <div class="grid">
    <section class="card span2">
      <div class="card-h"><h3>Where it fills first, next 30 minutes</h3>${tag('fc')}</div>
      <div class="zone-grid"><div></div>${zoneHead}${zoneRows}</div>
      <p class="fine">Expected cars for each lift are split evenly across the three levels, the same rule the guidance score uses. Cars already guided to a zone are taken off its free bays.</p>
    </section>
    <section class="card span2 flow-card">
      <div class="card-h"><h3>Parking occupancy</h3><span class="fine">Vehicle movement in 5-minute windows, next 30 minutes</span></div>
      <div id="fc-occ" class="flow">${flowPanel(sim, f, { w: wHalf, h: 230, id: 'fc' })}</div>
    </section>
    <section class="card mem-card" aria-labelledby="mem-live-h">
      <div class="card-h"><h3 id="mem-live-h">Members parked now</h3>${tag('now', 'Live')}</div>
      <div class="flow">${memberLivePanel(sim)}</div>
    </section>
    <section class="card mem-card" aria-labelledby="mem-past-h">
      <div class="card-h"><h3 id="mem-past-h">Members vs non-members since ${clockLabel(s, 0, false)}</h3><span class="fine">Cars parked, every 10 minutes</span></div>
      <div id="fc-mem" class="flow">${memberHistoryPanel(sim, { w: wMem, h: 230 })}</div>
    </section>
    <section class="card">
      <div class="card-h"><h3>Is it right?</h3>${tag('sim', 'After outcome')}</div>
      ${errRows
        ? `${accHead ? `<p class="acc-head">${esc(accHead)}</p>` : ''}
           <div class="acc"><div class="acc-row"><span>History only</span><span class="acc-bar"><i style="width:${((maeH || 0) / maxMae) * 100}%"></i></span><b>${fmtNum(maeH, 1)} pts</b></div><div class="acc-row acc-int"><span>History + intent</span><span class="acc-bar"><i style="width:${((maeI || 0) / maxMae) * 100}%"></i></span><b>${fmtNum(maeI, 1)} pts</b></div></div>
           <p class="fine">Average miss, 30 minutes ahead, in percentage points of usable bays. A forecast is stored every 5 minutes and checked when its time comes.</p>
           <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Made → for</th><th class="num">History</th><th class="num">+ Intent</th><th class="num">Actual</th><th class="num">Miss, hist.</th><th class="num">Miss, intent</th></tr></thead><tbody>${errRows}</tbody></table></div>`
        : `<div class="empty small"><p><strong>No outcome to compare yet</strong></p><p class="muted">A forecast is stored every 5 minutes and checked once its 30-minute horizon has been simulated.${nextCheck ? ` First check at ${clockLabel(s, nextCheck.forT, false)}.` : ''}</p></div>`}
    </section>
    <section class="card">
      <div class="card-h"><h3>Arrivals per 5 minutes</h3>${tag('fc')}</div>
      <div id="fc-arr" class="chart-box">${arrivalsChart(sim, f, wArr, 210)}</div>
      ${legendItems([{ color: 'var(--ink)', label: 'Realised entries' }, ...comps.map((c) => ({ color: `var(--c-${c === 'history' ? 'hist' : c})`, label: COMPONENT_LABELS[c], band: true })), { color: 'var(--ink-2)', label: 'History only', dash: true }])}
    </section>
    <section class="card">
      <div class="card-h"><h3>Intent signals</h3>${tag('synthetic')}</div>
      <table class="tbl"><tbody>${signals.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</tbody></table>
      <p class="fine">No live connection to cinema, restaurant, messaging or member systems exists in this prototype. These values are illustrative inputs.</p>
    </section>
    <section class="card">
      <div class="card-h"><h3>Forecast assumptions</h3>${tag('assume')}</div>
      <div class="assume">${ASSUMPTION_META.map((m) => {
        const v = a[m.key];
        const shown = m.pct ? fmtPct(v) : `${v}${m.unit ? ' ' + m.unit : ''}`;
        return `<label class="as"><span>${esc(m.label)}</span><input type="range" id="as-${m.key}" min="${m.min}" max="${m.max}" step="${m.step}" value="${v}" data-assume="${m.key}"><output>${esc(shown)}</output></label>`;
      }).join('')}</div>
      <div class="btn-row"><span class="fine">Move a slider and the forecast, zone outlook and guidance update at once. Saved in this browser only.</span><button type="button" class="btn btn-sm" data-act="reset-assumptions">Reset assumptions</button></div>
    </section>
    <section class="card span2">
      <div class="card-h"><h3>From signals to expected cars</h3>${tag('fc')}</div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Component</th><th class="num">Next 30 min</th><th class="num">Next 60 min</th><th>Basis</th></tr></thead><tbody>${convRows}</tbody></table></div>
      <p class="fine">Tickets and covers are converted to cars with the assumptions above, never one-to-one. Overlap terms avoid counting the same trip twice.</p>
    </section>
  </div>`;
  setHTML(root, html);
}

/** Last forecast refresh the page has shown, so a new one can be highlighted briefly. */
const fcSeen = { t: -1, flashUntil: 0 };

export function setAssumption(key: keyof ForecastAssumptions, v: number) {
  store.assumptions[key] = v;
  persist();
  store.sim.updateForecast();
}

export function resetAssumptions() {
  Object.assign(store.assumptions, DEFAULT_ASSUMPTIONS);
  persist();
  store.sim.updateForecast();
}

// ================= Allocation =================
export function renderAllocation(force = false) {
  const root = $('#view-allocation');
  if (!force && pageFocused(root)) return;
  const sim = store.sim;
  const decs = sim.decisions.slice(-14).reverse();
  const sel = store.selected && store.selected.kind === 'vehicle' ? sim.vehicles[store.selected.id] : null;
  const cur = sel && sel.alloc ? sel.alloc : decs[0] || null;
  const rows = decs
    .map((d) => {
      const v = sim.vehicles[d.vehicle];
      const run = d.ranked[1];
      const on = cur === d;
      return `<tr class="${on ? 'on' : ''}" data-act="select-vehicle" data-id="${d.vehicle}" role="button" tabindex="0"><td>${clockLabel(sim.scn, d.t, false)}</td><td>${esc(d.vehicleCode)}</td><td>${esc(DEST_BY_ID[d.dest].label)}</td><td><b>${esc(d.chosen ? d.chosen.label : '–')}</b></td><td class="num">${d.chosen ? d.chosen.total.toFixed(2) : '–'}</td><td>${run ? `${esc(run.label)} (${run.total.toFixed(2)})` : '–'}</td><td>${modeChip(d.mode)}${d.withoutForecast ? `<span class="pill pill-teal" title="Without the forecast term this car would have gone to ${esc(d.withoutForecast.label)}">Forecast steered</span>` : ''}</td><td>${esc(v ? shortState(v.state, v.parkT) : '')}</td></tr>`;
    })
    .join('');
  // simultaneous arrivals demo
  const burst = store.demoBurst.map((i) => sim.vehicles[i]).filter(Boolean);
  const burstRows = burst
    .map((v) => `<tr data-act="select-vehicle" data-id="${v.i}" role="button" tabindex="0"><td>${esc(v.code)}</td><td>${v.gateT >= 0 ? clockLabel(sim.scn, v.gateT, false) + ':' + String(v.gateT % 60).padStart(2, '0') : 'waiting'}</td><td><b>${v.alloc && v.alloc.chosen ? esc(v.alloc.chosen.label) : v.gateT >= 0 ? '–' : 'at entrance'}</b></td><td>${v.parkT >= 0 ? `parked ${esc(sim.L.bays[v.bay].id)} · ${fmtSecs(v.parkT - v.gateT)}` : esc(shortState(v.state, v.parkT))}</td></tr>`)
    .join('');
  const zonesUsed = new Set(burst.filter((v) => v.alloc && v.alloc.chosen).map((v) => v.alloc!.chosen!.label));
  const html = `
  <div class="page-head">
    <div><h2>Allocation</h2><p class="lede">Every guided car gets a zone, never an exclusive general bay. Select a decision to see why that zone won. Weights can be tuned under Why this bay on the overview.</p></div>
    <div class="tags">${tag('sim', 'Simulated decisions')}</div>
  </div>
  <div class="grid">
    <section class="card span2">
      <div class="card-h"><h3>Recent decisions</h3><span class="fine">Select a row to inspect it and follow the vehicle</span></div>
      ${rows ? `<div class="tbl-wrap"><table class="tbl tbl-click"><thead><tr><th>Time</th><th>Vehicle</th><th>Destination</th><th>Recommended</th><th class="num">Score</th><th>Runner-up</th><th>Note</th><th>Now</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="muted">Decisions appear as guided vehicles pass the entrance gate.</p>'}
    </section>
    <section class="card">
      <div class="card-h"><h3>Decision detail</h3>${cur ? `<span class="fine">${esc(cur.vehicleCode)} · ${clockLabel(sim.scn, cur.t, false)}</span>` : ''}</div>
      ${cur ? `<p class="explain">${esc(cur.explanation)}</p>${candidateRows(cur)}${legendFactors()}<p class="msg-preview">${icon('phone', 14)} “${esc(cur.message)}”</p>` : '<p class="muted">No decision yet.</p>'}
    </section>
    <section class="card">
      <div class="card-h"><h3>Simultaneous arrivals</h3>${tag('sim', 'Live demo')}</div>
      <p class="fine">Adds four drivers for the same destination at the entrance at once. An expiring count of drivers heading to each zone stops them all being sent to the same apparent vacancy.</p>
      <div class="btn-row"><label class="inline-field"><span>Destination</span><select id="burst-dest" data-draft="burstDest">${DESTINATIONS.map((d) => `<option value="${d.id}" ${(store.drafts.burstDest || 'atrium') === d.id ? 'selected' : ''}>${esc(d.label)}</option>`).join('')}</select></label>
      <button type="button" class="btn btn-primary btn-sm" data-act="burst">${icon('plus', 14)} Add 4 simultaneous arrivals</button></div>
      ${burst.length ? `<div class="tbl-wrap"><table class="tbl tbl-click"><thead><tr><th>Vehicle</th><th>Gate</th><th>Guided to</th><th>Outcome</th></tr></thead><tbody>${burstRows}</tbody></table></div><p class="fine">${zonesUsed.size} different zone${zonesUsed.size === 1 ? '' : 's'} used for ${burst.filter((v) => v.alloc).length} guided arrivals.</p>` : ''}
    </section>
  </div>`;
  setHTML(root, html);
}

function modeChip(m: string): string {
  if (m === 'normal') return '';
  const map: Record<string, [string, string]> = { shared: ['Shared zone', 'pill-warn'], 'expected-departure': ['Waiting for a departure', 'pill-warn'], none: ['No space', 'pill-crit'] };
  const [l, c] = map[m] || [m, 'pill-slate'];
  return `<span class="pill ${c}">${l}</span>`;
}

function shortState(s: string, parkT: number): string {
  if (parkT >= 0 && (s === 'parked' || s === 'unparking' || s === 'leaving' || s === 'exited')) return 'Parked';
  return ({ queued: 'At entrance', driving: 'Searching', parking: 'Parking', leaving: 'Leaving', exited: 'Left', pending: 'Not arrived', cancelled: 'Cancelled', diverted: 'Diverted' } as Record<string, string>)[s] || s;
}

// ================= Reservations =================
export function renderReservations(force = false) {
  const root = $('#view-reservations');
  if (!force && pageFocused(root)) return;
  const sim = store.sim;
  const s = sim.scn;
  const types = BOOKABLE_TYPES;
  const who: Record<string, string> = { ladies: 'For women drivers, next to the lift.', member: 'For opted-in rewards members.' };
  const inv = types
    .map((t) => {
      const q = sim.bookable(t);
      return `<div class="inv inv-${t}"><div class="inv-h">${icon(t === 'ladies' ? 'ladies' : 'star', 16)} ${esc(BAY_TYPE_LABEL[t])}</div>
        <div class="inv-n"><b>${q.bookable}</b><span>bookable now</span></div>
        <div class="inv-s">${q.total} bays, ${q.occupied} occupied, ${q.held} held, ${q.free} free. ${who[t]}</div></div>`;
    })
    .join('');
  const oku = sim.L.bays.filter((b) => b.type === 'oku');
  const okuFree = oku.filter((b) => sim.isFree(b.idx)).length;
  const invOku = `<div class="inv inv-oku"><div class="inv-h">${icon('oku', 16)} Accessible (OKU)</div><div class="inv-n"><b>${okuFree}</b><span>of ${oku.length} free</span></div><div class="inv-s">Protected for permit holders. Not bookable, never released to general traffic.</div></div>`;
  const statusChip = (st: string) => `<span class="pill ${({ confirmed: 'pill-res', 'checked-in': 'pill-teal', parked: 'pill-muted', cancelled: 'pill-slate', expired: 'pill-warn' } as Record<string, string>)[st] || ''}">${esc(st === 'checked-in' ? 'Checked in' : st[0].toUpperCase() + st.slice(1))}</span>`;
  const rows = sim.reservations
    .slice()
    .sort((a, b) => a.windowStart - b.windowStart)
    .map((r) => {
      const b = sim.L.bays[r.bay];
      const deadline = r.windowEnd + r.grace;
      const left = deadline - sim.t;
      const graceTxt = r.status === 'confirmed' ? (sim.t > r.windowEnd ? `<span class="warn-t">In grace period · ${Math.ceil(left / 60)} min left</span>` : `Held until ${clockLabel(s, deadline, false)}`) : r.status === 'expired' ? `Released ${clockLabel(s, r.closedT, false)}` : r.status === 'checked-in' ? `Checked in ${clockLabel(s, r.checkInT, false)}` : r.status === 'parked' ? `Parked ${clockLabel(s, r.closedT, false)}` : `Cancelled ${clockLabel(s, r.closedT, false)}`;
      const btns = r.status === 'confirmed' ? `<button type="button" class="btn btn-sm" data-act="res-checkin" data-id="${r.id}">Check in now</button><button type="button" class="btn btn-sm btn-ghost" data-act="res-cancel" data-id="${r.id}">Cancel</button>` : '';
      return `<tr><td><b>${esc(r.id)}</b>${r.userCreated ? ' <span class="fine">(you)</span>' : ''}</td><td>${esc(BAY_TYPE_LABEL[r.type])}</td><td><button type="button" class="linkbtn" data-act="select-bay" data-id="${r.bay}">${esc(b.id)}</button></td><td>${clockLabel(s, r.windowStart, false)}–${clockLabel(s, r.windowEnd, false)}</td><td>${Math.round(r.durationS / 60)} min</td><td>${graceTxt}</td><td>${statusChip(r.status)}</td><td class="btns">${btns}</td></tr>`;
    })
    .join('');
  const ladiesBays = sim.L.bays.filter((b) => b.type === 'ladies');
  const ladiesRows = ladiesBays
    .map((b) => {
      const st = sim.bayStatus(b.idx);
      const ch =
        st === 'available' ? '<span class="pill pill-teal">Free</span>'
        : st === 'reserved' ? `<span class="pill pill-res">Held for ${esc(sim.hold[b.idx] as string)}</span>`
        : st === 'departing' ? '<span class="pill pill-warn">Paid, leaving soon</span>'
        : st === 'unavailable' ? '<span class="pill pill-crit">Closed</span>'
        : '<span class="pill pill-slate">Taken</span>';
      return `<tr><td><button type="button" class="linkbtn" data-act="select-bay" data-id="${b.idx}">${esc(b.id)}</button></td><td>${FLOOR_NAMES[b.floor]}, Zone ${b.zone}</td><td>${ch}</td><td class="num">${b.walk[b.zone]} m</td></tr>`;
    })
    .join('');
  const confirmed = sim.reservations.filter((r) => r.status === 'confirmed').length;
  const ns = store.noShowRate;
  const html = `
  <div class="page-head">
    <div><h2>Special-bay reservations</h2><p class="lede">General parking stays guidance-only. Ladies' parking and designated member bays can be reserved within capacity. Accessible (OKU) bays are protected, not sold.</p></div>
    <div class="tags">${tag('now')} ${tag('sim', 'Simulated bookings')}</div>
  </div>
  <div class="inv-row">${inv}${invOku}</div>
  <div class="grid">
    <section class="card span2">
      <div class="card-h"><h3>Reservations</h3><span class="fine">Grace period 10 minutes after the arrival window, then the hold expires and the bay returns to its own inventory.</span></div>
      ${rows ? `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>ID</th><th>Type</th><th>Bay</th><th>Arrival window</th><th>Duration</th><th>Hold</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="muted">No reservations in this scenario.</p>'}
      ${store.resMsg ? `<p class="notice">${icon('info', 14)} ${esc(store.resMsg)}</p>` : ''}
    </section>
    <section class="card">
      <div class="card-h"><h3>New reservation</h3>${tag('sim', 'Simulated')}</div>
      <form class="form" id="res-form" novalidate>
        <label><span>Bay type</span><select id="res-type" data-draft="resType">${types.map((t) => `<option value="${t}" ${(store.drafts.resType || 'ladies') === t ? 'selected' : ''}>${esc(BAY_TYPE_LABEL[t])}</option>`).join('')}</select></label>
        <label><span>Arrival window starts in</span><select id="res-start" data-draft="resStart">${[10, 20, 30, 45].map((m) => `<option value="${m}" ${(store.drafts.resStart || '20') === String(m) ? 'selected' : ''}>${m} min (${clockLabel(s, sim.t + m * 60, false)})</option>`).join('')}</select></label>
        <label><span>Expected duration</span><select id="res-dur" data-draft="resDur">${[60, 90, 120, 180].map((m) => `<option value="${m}" ${(store.drafts.resDur || '90') === String(m) ? 'selected' : ''}>${m} min</option>`).join('')}</select></label>
        <label class="check"><input type="checkbox" id="res-elig" data-draft="resElig" ${store.drafts.resElig === '1' ? 'checked' : ''}> <span>The driver is eligible for this bay type (a woman driver for Ladies' parking, an opted-in member for designated member bays)</span></label>
        <p class="fine">Window length 15 minutes · grace period 10 minutes · overbooking disabled.</p>
        <button type="submit" class="btn btn-primary btn-sm">${icon('check', 14)} Reserve</button>
      </form>
    </section>
    <section class="card">
      <div class="card-h"><h3>Booking quota and no-shows</h3>${tag('assume')}</div>
      <label class="as"><span>No-show rate (demo assumption)</span><input type="range" id="noshow" min="0" max="0.5" step="0.05" value="${ns}" data-act="noshow"><output>${fmtPct(ns)}</output></label>
      <ul class="plain">
        <li>Guaranteed reservations never exceed free bays of the type, and one bay per type is kept for eligible walk-in drivers.</li>
        <li>The no-show rate is not used to overbook. It sets expectations: of ${confirmed} open holds, about ${fmtNum(confirmed * (1 - ns), 1)} are expected to check in and ${fmtNum(confirmed * ns, 1)} to be released at expiry.</li>
        <li>Expired holds return to their own inventory (Ladies' parking to Ladies' parking, member to member), never to general parking.</li>
      </ul>
    </section>
    <section class="card">
      <div class="card-h"><h3>Ladies' parking</h3>${tag('now')}</div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Bay</th><th>Where</th><th>Status</th><th class="num">Walk to lift</th></tr></thead><tbody>${ladiesRows}</tbody></table></div>
      <p class="fine">For women drivers. The bays sit beside the lift so the walk is short and in view. Eligibility is self-declared in the app; staff may check at the bay.</p>
    </section>
    <section class="card">
      <div class="card-h"><h3>Accessible-bay assistance</h3></div>
      <form class="form" id="assist-form" novalidate>
        <label><span>Arriving in about</span><select id="assist-eta" data-draft="assistEta">${[5, 10, 15, 30].map((m) => `<option value="${m}" ${(store.drafts.assistEta || '10') === String(m) ? 'selected' : ''}>${m} min</option>`).join('')}</select></label>
        <label class="check"><input type="checkbox" id="assist-permit" data-draft="assistPermit" ${store.drafts.assistPermit === '1' ? 'checked' : ''}> <span>The driver or a passenger holds an OKU permit (staff verify on arrival)</span></label>
        <button type="submit" class="btn btn-sm">${icon('oku', 14)} Request assistance</button>
      </form>
      <p class="fine">Currently ${okuFree} of ${oku.length} accessible bays are free. A request alerts the operator; it is not a guarantee, because access depends on on-site enforcement.</p>
    </section>
  </div>`;
  setHTML(root, html);
}

// ================= Impact =================
function row(label: string, b: string, g: string, change: string, cls = ''): string {
  return `<tr class="${cls}"><th>${esc(label)}</th><td class="num">${b}</td><td class="num">${g}</td><td class="num">${change}</td></tr>`;
}

function pctTxt(before: number, after: number, lowerIsBetter = true): string {
  const p = pctChange(before, after);
  if (!isFinite(p)) return '–';
  const good = lowerIsBetter ? p < 0 : p > 0;
  return `<span class="${Math.abs(p) < 0.5 ? '' : good ? 'good' : 'bad'}">${signed(p, 0, '%')}</span>`;
}

export function annualProjection(): { peakKg: number; offKg: number; total: number; peakKm: number; offKm: number } | null {
  const c = store.comparison;
  const o = store.offpeak;
  if (!c || !o) return null;
  const f = store.emission.factorKgPerKm;
  const peakKm = Math.max(0, (c.baseline.iceSearchDist - c.guided.iceSearchDist) / 1000);
  const offKm = Math.max(0, (o.baseline.iceSearchDist - o.guided.iceSearchDist) / 1000);
  const peakKg = peakKm * f * store.emission.peakPeriodsPerYear;
  const offKg = offKm * f * store.emission.offPeakPeriodsPerYear;
  return { peakKg, offKg, total: peakKg + offKg, peakKm, offKm };
}

export function renderImpact(force = false) {
  const root = $('#view-impact');
  if (!force && pageFocused(root)) return;
  const c = store.comparison;
  let body: string;
  if (!c) {
    body = `<section class="card span2 empty-card">
      <div class="empty"><div class="empty-ic">${icon('compare', 22)}</div>
      <p><strong>No matched comparison yet</strong></p>
      <p class="muted">Runs the “${esc(store.sim.scn.name)}” scenario twice with identical arrivals, durations, eligibility mix, initial occupancy and random seed: once with a documented unguided search policy and once with ParkFlow guidance. Marketing actions stay off in both.</p>
      <button type="button" class="btn btn-primary" data-act="run-compare">${icon('compare', 16)} Run matched comparison</button></div>
    </section>`;
  } else {
    const B = c.baseline, G = c.guided;
    const unresolved = (r: RunSummary) => r.stillSearching + r.gaveUp + r.diverted + r.notAdmitted;
    const wH = chartWidth('imp-hist', 480);
    const wS = chartWidth('imp-search', 480);
    const scn = SCENARIO_BY_ID[c.scenarioId as keyof typeof SCENARIO_BY_ID];
    const iceKm = (B.iceSearchDist - G.iceSearchDist) / 1000;
    const kg = Math.max(0, iceKm) * store.emission.factorKgPerKm;
    const proj = annualProjection();
    body = `
    ${store.comparisonStale ? `<p class="notice warn span2">${icon('alert', 14)} Weights or assumptions changed after this comparison. Run it again to refresh.</p>` : ''}
    <div class="big-cmp span2">
      <div><span>Mean gate-to-park</span><b>${fmtSecs(B.meanG2P)} → <em>${fmtSecs(G.meanG2P)}</em></b>${pctTxt(B.meanG2P, G.meanG2P)}</div>
      <div><span>P90 gate-to-park</span><b>${fmtSecs(B.p90G2P)} → <em>${fmtSecs(G.p90G2P)}</em></b>${pctTxt(B.p90G2P, G.p90G2P)}</div>
      <div><span>Mean search distance</span><b>${fmtDist(B.meanSearchDist)} → <em>${fmtDist(G.meanSearchDist)}</em></b>${pctTxt(B.meanSearchDist, G.meanSearchDist)}</div>
      <div><span>Unresolved vehicles</span><b>${unresolved(B)} → <em>${unresolved(G)}</em></b><span class="fine">of ${B.admitted} admitted</span></div>
    </div>
    <section class="card span2">
      <div class="card-h"><h3>Matched-run results · ${esc(c.scenarioName)}</h3>${tag('sim')}</div>
      <div class="tbl-wrap"><table class="tbl cmp">
        <thead><tr><th>Metric</th><th class="num">Unguided baseline</th><th class="num">ParkFlow guidance</th><th class="num">Change</th></tr></thead>
        <tbody>
          ${row('Scheduled arrivals (identical demand)', String(B.scheduled), String(G.scheduled), '–')}
          ${row('Admitted through the gate', String(B.admitted), String(G.admitted), '–')}
          ${row('Parked successfully', String(B.parked), String(G.parked), signed(G.parked - B.parked))}
          ${row('Mean gate-to-park (parked vehicles)', fmtSecs(B.meanG2P), fmtSecs(G.meanG2P), pctTxt(B.meanG2P, G.meanG2P))}
          ${row('Median gate-to-park', fmtSecs(B.medianG2P), fmtSecs(G.medianG2P), pctTxt(B.medianG2P, G.medianG2P))}
          ${row('P90 gate-to-park (all admitted, unresolved at time searched)', fmtSecs(B.p90G2P), fmtSecs(G.p90G2P), pctTxt(B.p90G2P, G.p90G2P))}
          ${row('Mean search distance (parked vehicles)', fmtDist(B.meanSearchDist), fmtDist(G.meanSearchDist), pctTxt(B.meanSearchDist, G.meanSearchDist))}
          ${row('Total search distance (all admitted)', fmtDist(B.totalSearchDist), fmtDist(G.totalSearchDist), pctTxt(B.totalSearchDist, G.totalSearchDist))}
          ${row('Peak entrance queue (vehicles before the gate)', String(B.peakQueue), String(G.peakQueue), signed(G.peakQueue - B.peakQueue))}
          ${row('Mean wait before the gate (not in gate-to-park)', fmtSecs(B.meanGateWait), fmtSecs(G.meanGateWait), '–')}
          ${row('Still searching at end of drain', String(B.stillSearching), String(G.stillSearching), signed(G.stillSearching - B.stillSearching), 'sep')}
          ${row('Gave up after 20 minutes (unable to park)', String(B.gaveUp), String(G.gaveUp), signed(G.gaveUp - B.gaveUp))}
          ${row('Diverted before the gate', String(B.diverted), String(G.diverted), signed(G.diverted - B.diverted))}
          ${row('Not admitted by end of drain', String(B.notAdmitted), String(G.notAdmitted), signed(G.notAdmitted - B.notAdmitted))}
        </tbody></table></div>
      <p class="fine">Seed ${c.seed} · ${scn.windowMin}-minute arrival window plus ${scn.drainMin}-minute drain · computed in this browser from both simulation runs. No figure here is hard-coded.</p>
    </section>
    <section class="card">
      <div class="card-h"><h3>Gate-to-park distribution</h3>${legendItems([{ color: 'var(--c-base)', label: 'Unguided', band: true }, { color: 'var(--teal)', label: 'ParkFlow', band: true }])}</div>
      <div id="imp-hist" class="chart-box">${g2pHistogram(B, G, wH, 220)}</div>
    </section>
    <section class="card">
      <div class="card-h"><h3>Vehicles searching over time</h3>${legendItems([{ color: 'var(--c-base)', label: 'Unguided' }, { color: 'var(--teal)', label: 'ParkFlow' }])}</div>
      <div id="imp-search" class="chart-box">${searchingChart(scn, B, G, wS, 220)}</div>
    </section>
    <section class="card">
      <div class="card-h"><h3>Method</h3></div>
      <ul class="plain">
        <li><b>Unguided policy:</b> drivers enter at B1 and loop each level in turn. They take the first free eligible bay within their own acceptable walk to their lift (22–46 m, drawn per driver), or any eligible bay after 3 minutes. After the lowest level they work back up.</li>
        <li><b>ParkFlow policy:</b> zone allocation at the gate using the score shown on the Allocation page, expiring guidance counts, re-evaluation when bays free up, and acceptance of an equally convenient free bay passed on the way.</li>
        <li><b>Same in both:</b> arrivals, durations, eligibility, initial occupancy, reservations, gate throughput (one vehicle per 5 s) and the 20-minute give-up rule.</li>
        <li><b>Gate-to-park time</b> runs from crossing the entrance gate to completing the parking manoeuvre. Queueing before the gate is reported separately.</li>
      </ul>
    </section>
    <section class="card">
      <div class="card-h"><h3>Avoided tailpipe CO₂ (estimate)</h3>${tag('sim', 'Estimate')}</div>
      <div class="co2">
        <div><span>Avoided combustion-vehicle search distance</span><b>${fmtNum(iceKm, 2)} km</b></div>
        <div><span>Emissions factor ${tag('assume')}</span><b><label class="sr" for="co2-factor">Emissions factor</label><input id="co2-factor" type="number" min="0.05" max="0.5" step="0.01" value="${store.emission.factorKgPerKm}" data-emission="factorKgPerKm"> kg CO₂/km</b></div>
        <div><span>Combustion-vehicle share (simulated demand)</span><b>${fmtPct(G.iceShare)}</b></div>
        <div class="hl"><span>Estimated avoided tailpipe CO₂, this run</span><b>${fmtNum(kg, 2)} kg</b></div>
      </div>
      <p class="fine">Avoided CO₂ = reduced combustion-vehicle search distance × assumed factor. EVs are excluded. The factor is a demo assumption: replace with a sourced local factor. No separate idling term is added, to avoid double counting. This is not a verified carbon saving.</p>
      <details class="drawer"><summary>${icon('sliders', 14)} Scenario projection (annual)</summary>
        <div class="proj">
          <label><span>Comparable peak periods per year (like this run)</span><input type="number" id="proj-peak" min="0" max="1000" step="1" value="${store.emission.peakPeriodsPerYear}" data-emission="peakPeriodsPerYear"></label>
          <label><span>Off-peak periods per year (like “Normal afternoon”)</span><input type="number" id="proj-off" min="0" max="2000" step="1" value="${store.emission.offPeakPeriodsPerYear}" data-emission="offPeakPeriodsPerYear"></label>
        </div>
        ${proj ? `<table class="tbl"><tbody>
          <tr><th>Peak: ${fmtNum(proj.peakKm, 2)} km avoided per period × ${store.emission.peakPeriodsPerYear}</th><td class="num">${fmtNum(proj.peakKg, 0)} kg</td></tr>
          <tr><th>Off-peak: ${fmtNum(proj.offKm, 2)} km avoided per period × ${store.emission.offPeakPeriodsPerYear}</th><td class="num">${fmtNum(proj.offKg, 0)} kg</td></tr>
          <tr class="sep"><th>Scenario projection, per year</th><td class="num"><b>${fmtNum(proj.total / 1000, 2)} t CO₂</b></td></tr></tbody></table>
          <p class="fine">Scenario projection only. Each 2-hour period is simulated, not extrapolated from one busy hour. Off-peak savings come from a separate matched run of the Normal afternoon scenario.</p>` : '<p class="muted">Run the comparison to compute the projection.</p>'}
      </details>
    </section>`;
  }
  const html = `
  <div class="page-head">
    <div><h2>Impact</h2><p class="lede">Baseline versus guided, from matched simulation runs. Field observations are kept separate below.</p></div>
    <div class="tags">${tag('sim')} ${tag('field')}</div>
  </div>
  <div class="grid">${body}${fieldPanel()}</div>`;
  setHTML(root, html);
}

// ---------------- field validation ----------------
function parseTime(s: string): number | null {
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(s.trim());
  if (!m) return null;
  const h = +m[1], mi = +m[2], se = m[3] ? +m[3] : 0;
  if (h > 23 || mi > 59 || se > 59) return null;
  return h * 3600 + mi * 60 + se;
}

function validDate(s: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s.trim());
  if (!m) return false;
  const y = +m[1], mo = +m[2], d = +m[3];
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === mo - 1 && dt.getUTCDate() === d;
}

export function validateObs(o: FieldObs, existing: FieldObs[]): string | null {
  if (!o.id.trim()) return 'Observation ID is required.';
  if (!/^[A-Za-z0-9-_]{1,16}$/.test(o.id.trim())) return 'Use a short anonymous ID (letters, digits, - or _), not a plate number or name.';
  if (existing.some((x) => x.id === o.id.trim())) return `ID ${o.id} already exists.`;
  if (!validDate(o.date)) return 'Date must be a real date in YYYY-MM-DD format.';
  const a = parseTime(o.gateEntry);
  const b = parseTime(o.parked);
  if (a === null) return 'Gate-entry time must be HH:MM or HH:MM:SS.';
  if (b === null) return 'Parking-complete time must be HH:MM or HH:MM:SS.';
  if (b <= a) return 'Parking-complete time must be after gate entry on the same day.';
  if (b - a > 2 * 3600) return 'Gate-to-park longer than 2 hours looks like an entry error.';
  if (!o.zone.trim()) return 'Observed floor or zone is required.';
  if (o.note.length > 120) return 'Keep the note under 120 characters.';
  return null;
}

export function obsSeconds(o: FieldObs): number {
  return (parseTime(o.parked) as number) - (parseTime(o.gateEntry) as number);
}

export function importCSV(text: string): { added: number; rejected: string[] } {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const rejected: string[] = [];
  let added = 0;
  for (let i = 0; i < lines.length; i++) {
    const cols = lines[i].split(',').map((c) => c.trim().replace(/^"|"$/g, ''));
    if (i === 0 && /observation/i.test(cols[0])) continue;
    if (cols.length < 5) { rejected.push(`Line ${i + 1}: expected at least 5 columns.`); continue; }
    const o: FieldObs = { id: cols[0], date: cols[1], gateEntry: cols[2], parked: cols[3], zone: cols[4], note: cols.slice(5).join(', ') };
    const err = validateObs(o, store.field);
    if (err) { rejected.push(`Line ${i + 1}: ${err}`); continue; }
    o.id = o.id.trim();
    store.field.push(o);
    added++;
  }
  persist();
  return { added, rejected };
}

function fieldPanel(): string {
  const obs = store.field;
  const secs = obs.map(obsSeconds);
  const n = obs.length;
  const title = n ? `Field validation · ${n} observation${n === 1 ? '' : 's'}` : 'Field validation — pending';
  const sample = n === 0 ? '' : n < 30 ? `<p class="notice field-note">${icon('info', 14)} Exploratory sample (n = ${n}). It describes the observed period only and is not representative of every operating period.</p>` : '';
  const rows = obs
    .map((o, i) => `<tr><td>${esc(o.id)}</td><td>${esc(o.date)}</td><td>${esc(o.gateEntry)}</td><td>${esc(o.parked)}</td><td class="num">${fmtSecs(secs[i])}</td><td>${esc(o.zone)}</td><td>${esc(o.note)}</td><td><button type="button" class="icon-btn sm" data-act="field-del" data-id="${esc(o.id)}" aria-label="Delete observation ${esc(o.id)}">${icon('trash', 14)}</button></td></tr>`)
    .join('');
  const wF = chartWidth('field-strip', 420);
  return `<section class="card span2 field-card">
    <div class="card-h"><h3>${esc(title)}</h3>${tag('field')}</div>
    <p class="fine">Record real observations from a site visit: the entrance-gate crossing and the moment the car is parked. Use anonymous IDs only. Field data is never mixed with simulated results.</p>
    <div class="field-grid">
      <form class="form" id="field-form" novalidate>
        <div class="form-row">
          <label><span>Observation ID</span><input id="f-id" data-draft="fId" value="${draft('fId')}" placeholder="e.g. OBS-01" autocomplete="off"></label>
          <label><span>Date</span><input id="f-date" type="date" data-draft="fDate" value="${draft('fDate')}"></label>
        </div>
        <div class="form-row">
          <label><span>Gate entry</span><input id="f-in" data-draft="fIn" value="${draft('fIn')}" placeholder="e.g. 14:05:20" inputmode="numeric"></label>
          <label><span>Parking complete</span><input id="f-out" data-draft="fOut" value="${draft('fOut')}" placeholder="e.g. 14:09:02" inputmode="numeric"></label>
        </div>
        <div class="form-row">
          <label><span>Floor or zone</span><input id="f-zone" data-draft="fZone" value="${draft('fZone')}" placeholder="e.g. B2 Zone C"></label>
          <label><span>Pain point (optional)</span><input id="f-note" data-draft="fNote" value="${draft('fNote')}" maxlength="120" placeholder="e.g. queued at B1 ramp"></label>
        </div>
        <button type="submit" class="btn btn-sm">${icon('plus', 14)} Add observation</button>
      </form>
      <div class="form">
        <label><span>Import CSV</span><textarea id="f-csv" rows="4" data-draft="fCsv" placeholder="observation_id,date,gate_entry,parking_complete,floor_zone,note">${draft('fCsv')}</textarea></label>
        <div class="btn-row"><label class="btn btn-sm file-btn">${icon('upload', 14)} Choose file<input type="file" id="f-file" accept=".csv,text/csv"></label><button type="button" class="btn btn-sm" data-act="field-import">Import pasted rows</button></div>
      </div>
    </div>
    ${store.fieldMsg ? `<p class="notice ${/reject|must|required|Use|looks|exists|Keep/.test(store.fieldMsg) ? 'warn' : ''}">${esc(store.fieldMsg)}</p>` : ''}
    ${n ? `<div class="field-stats">
        <div><span>Sample size</span><b>${n}</b></div>
        <div><span>Mean</span><b>${fmtSecs(mean(secs))}</b></div>
        <div><span>Median</span><b>${fmtSecs(percentile(secs, 0.5))}</b></div>
        <div><span>P90</span><b>${fmtSecs(percentile(secs, 0.9))}</b></div>
      </div>
      ${sample}
      <div id="field-strip" class="chart-box">${fieldStrip(secs, wF, 64)}</div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>ID</th><th>Date</th><th>Gate entry</th><th>Parked</th><th class="num">Gate-to-park</th><th>Floor/zone</th><th>Note</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="btn-row">${store.drafts.fieldClear === '1' ? `<span class="fine">Delete all ${n} observations?</span><button type="button" class="btn btn-sm btn-danger" data-act="field-clear-yes">Delete all</button><button type="button" class="btn btn-sm" data-act="field-clear-no">Keep</button>` : `<button type="button" class="btn btn-sm btn-ghost" data-act="field-clear">Clear observations</button>`}</div>`
      : `<div class="empty small field-empty"><p><strong>No observations yet</strong></p><p class="muted">Nothing is pre-filled. Results appear here once you add real measurements.</p></div>`}
  </section>`;
}
