// Hand-built SVG charts. Every number comes from the live Sim, the forecast, or a matched comparison.

import { Sim } from '../core/sim';
import { Forecast } from '../core/forecast';
import { clockLabel, ScenarioDef } from '../core/scenarios';
import { RunSummary } from '../core/metrics';
import { FLOOR_NAMES } from '../core/layout';
import { esc } from './dom';

const INK = 'var(--ink-3)';
const GRID = 'var(--grid)';

function niceTicks(min: number, max: number, count: number): number[] {
  const span = max - min || 1;
  const step0 = span / count;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= count) || step0;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

function path(pts: [number, number][]): string {
  return pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('');
}

export interface OccChartOpts {
  w: number;
  h: number;
  showHistBand?: boolean;
  snapshots?: boolean;
  /** An earlier intent forecast, drawn faintly so viewers can see how the forecast moved. */
  ghost?: { t: number; occ: number[]; usable: number } | null;
  /** Measured, one forecast and the 95% line only: for the occupancy panel. */
  simple?: boolean;
}

/** Occupancy (share of usable bays): measured so far, then both forecasts with the intent range. */
export function occupancyChart(sim: Sim, f: Forecast | null, o: OccChartOpts): string {
  const s = sim.scn;
  const W = o.w, H = o.h;
  const m = { l: 38, r: 14, t: 12, b: 24 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const tMax = sim.tEnd;
  const hist = sim.history;
  const occ = hist.map((r) => r.occupied / r.usable);
  const fcVals: number[] = [];
  if (f) for (const arr of [f.hist.occ, f.intent.occ, f.intent.hi, f.intent.lo, f.hist.lo]) for (const v of arr) fcVals.push(v / f.usable);
  const lo = Math.max(0, Math.floor((Math.min(...occ, ...fcVals, 0.9) - 0.04) * 10) / 10);
  const hi = 1;
  const x = (t: number) => m.l + (t / tMax) * iw;
  const y = (v: number) => m.t + (1 - (v - lo) / (hi - lo)) * ih;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="Occupancy and forecast chart" preserveAspectRatio="none" class="chart">`;
  // grid
  for (const v of niceTicks(lo, hi, H < 120 ? 2 : 4)) {
    svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/>`;
    svg += `<text x="${m.l - 6}" y="${y(v) + 3.5}" text-anchor="end" class="ax">${Math.round(v * 100)}%</text>`;
  }
  for (let t = 0; t <= tMax; t += 1800) {
    svg += `<text x="${x(t)}" y="${H - 6}" text-anchor="middle" class="ax">${clockLabel(s, t, false)}</text>`;
  }
  // window end marker
  svg += `<line x1="${x(sim.tWindowEnd)}" x2="${x(sim.tWindowEnd)}" y1="${m.t}" y2="${m.t + ih}" stroke="${GRID}" stroke-dasharray="2 3"/>`;
  if (!o.simple) svg += `<text x="${x(sim.tWindowEnd) - 4}" y="${m.t + 10}" text-anchor="end" class="ax">arrivals end</text>`;
  // 95% threshold
  if (0.95 > lo) {
    svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(0.95)}" y2="${y(0.95)}" stroke="var(--amber)" stroke-dasharray="4 4" opacity=".7"/>`;
    svg += `<text x="${W - m.r - 2}" y="${y(0.95) - 4}" text-anchor="end" class="ax" fill="var(--amber)">95%</text>`;
  }
  if (f) {
    const t0 = f.t;
    const pts = (arr: number[]) => arr.map((v, k) => [x(Math.min(tMax, t0 + (k + 1) * 60)), y(v / f.usable)] as [number, number]).filter((p, k) => t0 + (k + 1) * 60 <= tMax);
    const start: [number, number] = [x(t0), y(occ[occ.length - 1] ?? 0)];
    const hiP = [start, ...pts(f.intent.hi)];
    const loP = [start, ...pts(f.intent.lo)].reverse();
    if (hiP.length > 1) svg += `<path d="${path([...hiP, ...loP])}Z" fill="var(--teal)" opacity=".14"/>`;
    if (o.showHistBand) {
      const hh = [start, ...pts(f.hist.hi)];
      const hl = [start, ...pts(f.hist.lo)].reverse();
      if (hh.length > 1) svg += `<path d="${path([...hh, ...hl])}Z" fill="var(--ink-3)" opacity=".08"/>`;
    }
    if (!o.simple) svg += `<path d="${path([start, ...pts(f.hist.occ)])}" fill="none" stroke="var(--ink-3)" stroke-width="2" stroke-dasharray="5 4"/>`;
    svg += `<path d="${path([start, ...pts(f.intent.occ)])}" fill="none" stroke="var(--teal)" stroke-width="2.4" stroke-dasharray="7 4"/>`;
  }
  // an earlier forecast, for comparison
  if (o.ghost && o.ghost.t < sim.t) {
    const g = o.ghost;
    const gp = g.occ.map((v, k) => [x(g.t + (k + 1) * 60), y(v / g.usable)] as [number, number]).filter((_, k) => g.t + (k + 1) * 60 <= tMax);
    if (gp.length > 1) {
      svg += `<path d="${path(gp)}" fill="none" stroke="var(--teal)" stroke-width="1.4" stroke-dasharray="1.5 3.5" opacity=".75"/>`;
      const lp = gp[Math.min(gp.length - 1, 44)];
      svg += `<text x="${lp[0]}" y="${lp[1] + 14}" text-anchor="middle" class="ax" fill="var(--teal)">forecast at ${clockLabel(s, g.t, false)}</text>`;
    }
  }
  // matured forecast checks: each pair of rings is a forecast made 30 minutes earlier; the whisker runs to what happened
  if (o.snapshots) {
    for (const sn of sim.snapshots) {
      if (sn.forT > sim.t || sn.forT > tMax) continue;
      const rec = sim.history.find((h) => h.t >= sn.forT);
      const cx = x(sn.forT);
      if (rec) {
        const ay = y(rec.occupied / rec.usable);
        svg += `<line x1="${cx}" x2="${cx}" y1="${y(sn.hist / sim.usable)}" y2="${ay}" stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="2 2" opacity=".7"/>`;
        svg += `<line x1="${cx}" x2="${cx}" y1="${y(sn.intent / sim.usable)}" y2="${ay}" stroke="var(--teal)" stroke-width="1.6" opacity=".8"/>`;
      }
      svg += `<circle cx="${cx}" cy="${y(sn.hist / sim.usable)}" r="3" fill="var(--surface)" stroke="var(--ink-3)" stroke-width="1.5"><title>History-only forecast made at ${clockLabel(s, sn.madeT, false)}</title></circle>`;
      svg += `<circle cx="${cx}" cy="${y(sn.intent / sim.usable)}" r="3" fill="var(--surface)" stroke="var(--teal)" stroke-width="1.8"><title>History + intent forecast made at ${clockLabel(s, sn.madeT, false)}</title></circle>`;
    }
  }
  // measured
  const mp = hist.map((r, i) => [x(r.t), y(occ[i])] as [number, number]);
  if (mp.length > 1) svg += `<path d="${path(mp)}" fill="none" stroke="var(--ink)" stroke-width="2.4"/>`;
  const last = mp[mp.length - 1];
  if (last) svg += `<circle cx="${last[0]}" cy="${last[1]}" r="3.5" fill="var(--ink)"/>`;
  // now line
  const nx = x(sim.t);
  svg += `<line x1="${nx}" x2="${nx}" y1="${m.t}" y2="${m.t + ih}" stroke="var(--ink)" stroke-width="1" opacity=".5"/>`;
  svg += `<text x="${nx + 4}" y="${m.t + ih - 4}" class="ax" fill="var(--ink)">Now ${clockLabel(s, sim.t, false)}</text>`;
  svg += '</svg>';
  return svg;
}

/** Arrivals per 5 minutes: realised gate entries so far, forecast components ahead. */
export function arrivalsChart(sim: Sim, f: Forecast | null, W: number, H: number): string {
  const m = { l: 34, r: 12, t: 12, b: 24 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const tMax = sim.tEnd;
  const bins: { t: number; v: number }[] = [];
  for (let t = 0; t < sim.t; t += 300) {
    let v = 0;
    for (const r of sim.history) if (r.t > t && r.t <= t + 300) v += r.entries;
    bins.push({ t, v });
  }
  const comps = ['history', 'member', 'cinema', 'dining', 'event', 'offer', 'coming'] as const;
  const colors: Record<string, string> = { history: 'var(--c-hist)', member: 'var(--c-member)', cinema: 'var(--c-cinema)', dining: 'var(--c-dining)', event: 'var(--c-event)', offer: 'var(--c-offer)', coming: 'var(--c-coming)' };
  const fBins: { t: number; parts: Record<string, number>; hist: number }[] = [];
  if (f) {
    for (let k = 0; k < f.horizon; k += 5) {
      const t = f.t + k * 60;
      if (t >= tMax) break;
      const parts: Record<string, number> = {};
      for (const c of comps) parts[c] = f.components[c].slice(k, k + 5).reduce((a, b) => a + b, 0);
      fBins.push({ t, parts, hist: f.hist.arrivals.slice(k, k + 5).reduce((a, b) => a + b, 0) });
    }
  }
  const maxV = Math.max(4, ...bins.map((b) => b.v), ...fBins.map((b) => Object.values(b.parts).reduce((a, c) => a + c, 0)), ...fBins.map((b) => b.hist));
  const x = (t: number) => m.l + (t / tMax) * iw;
  const y = (v: number) => m.t + (1 - v / maxV) * ih;
  const bw = (300 / tMax) * iw - 2;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="chart" role="img" aria-label="Arrivals per five minutes">`;
  for (const v of niceTicks(0, maxV, 4)) {
    svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${m.l - 6}" y="${y(v) + 3.5}" text-anchor="end" class="ax">${v}</text>`;
  }
  for (let t = 0; t <= tMax; t += 1800) svg += `<text x="${x(t)}" y="${H - 6}" text-anchor="middle" class="ax">${clockLabel(sim.scn, t, false)}</text>`;
  for (const b of bins) svg += `<rect x="${x(b.t) + 1}" y="${y(b.v)}" width="${Math.max(1, bw)}" height="${m.t + ih - y(b.v)}" fill="var(--ink)" opacity=".78" rx="1.5"/>`;
  for (const b of fBins) {
    let acc = 0;
    for (const c of comps) {
      const v = b.parts[c];
      if (v <= 0.001) continue;
      svg += `<rect x="${x(b.t) + 1}" y="${y(acc + v)}" width="${Math.max(1, bw)}" height="${y(acc) - y(acc + v)}" fill="${colors[c]}" opacity=".9"/>`;
      acc += v;
    }
  }
  if (fBins.length) {
    const hp = fBins.map((b) => [x(b.t) + bw / 2 + 1, y(b.hist)] as [number, number]);
    svg += `<path d="${path(hp)}" fill="none" stroke="var(--ink-2)" stroke-width="2" stroke-dasharray="4 3"/>`;
  }
  const nx = x(sim.t);
  svg += `<line x1="${nx}" x2="${nx}" y1="${m.t}" y2="${m.t + ih}" stroke="var(--ink)" opacity=".5"/>`;
  svg += '</svg>';
  return svg;
}

export const COMPONENT_LABELS: Record<string, string> = {
  history: 'Typical-day history',
  member: 'Opted-in member pattern (adjustment)',
  cinema: 'Cinema tickets',
  dining: 'Restaurant bookings',
  event: 'Mall event',
  offer: 'Active parking offer',
  coming: "'I'm coming' drivers (net of overlap)"
};

export function legendItems(items: { color: string; label: string; dash?: boolean; band?: boolean; dot?: boolean }[]): string {
  return `<div class="legend-row">${items
    .map((i) => `<span class="lg">${i.band ? `<i class="sw band" style="background:${i.color}"></i>` : i.dot ? `<i class="sw dot" style="border-color:${i.color}"></i>` : `<i class="sw ${i.dash ? 'dash' : 'line'}" style="--c:${i.color}"></i>`}${esc(i.label)}</span>`)
    .join('')}</div>`;
}

/** Grouped histogram of gate-to-park times, baseline vs guided. Unresolved vehicles get their own bin. */
export function g2pHistogram(b: RunSummary, g: RunSummary, W: number, H: number): string {
  const edges = [0, 60, 120, 180, 300, 600, Infinity];
  const labels = ['< 1 min', '1–2', '2–3', '3–5', '5–10', '> 10', 'Unresolved'];
  const count = (r: RunSummary) => {
    const c = new Array(7).fill(0);
    for (const v of r.g2p) for (let i = 0; i < 6; i++) if (v >= edges[i] && v < edges[i + 1]) { c[i]++; break; }
    c[6] = r.admitted - r.parked;
    return c;
  };
  const cb = count(b), cg = count(g);
  const maxV = Math.max(1, ...cb, ...cg);
  const m = { l: 30, r: 8, t: 10, b: 30 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const gw = iw / 7;
  const y = (v: number) => m.t + (1 - v / maxV) * ih;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="chart" role="img" aria-label="Gate-to-park time distribution">`;
  for (const v of niceTicks(0, maxV, 4)) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${m.l - 5}" y="${y(v) + 3.5}" text-anchor="end" class="ax">${v}</text>`;
  for (let i = 0; i < 7; i++) {
    const x0 = m.l + i * gw + gw * 0.14;
    const bw = gw * 0.34;
    svg += `<rect x="${x0}" y="${y(cb[i])}" width="${bw}" height="${m.t + ih - y(cb[i])}" fill="var(--c-base)" rx="2"><title>Baseline: ${cb[i]}</title></rect>`;
    svg += `<rect x="${x0 + bw + 2}" y="${y(cg[i])}" width="${bw}" height="${m.t + ih - y(cg[i])}" fill="var(--teal)" rx="2"><title>ParkFlow: ${cg[i]}</title></rect>`;
    svg += `<text x="${m.l + i * gw + gw / 2}" y="${H - 14}" text-anchor="middle" class="ax">${labels[i]}</text>`;
  }
  svg += `<text x="${m.l + iw / 2}" y="${H - 2}" text-anchor="middle" class="ax">gate-to-park time (minutes)</text>`;
  svg += '</svg>';
  return svg;
}

/** Vehicles searching per minute in both runs. */
export function searchingChart(scn: ScenarioDef, b: RunSummary, g: RunSummary, W: number, H: number): string {
  const n = Math.max(b.searchingSeries.length, g.searchingSeries.length);
  const maxV = Math.max(3, ...b.searchingSeries, ...g.searchingSeries);
  const m = { l: 30, r: 10, t: 10, b: 22 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const x = (i: number) => m.l + (i / Math.max(1, n - 1)) * iw;
  const y = (v: number) => m.t + (1 - v / maxV) * ih;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="chart" role="img" aria-label="Vehicles searching over time">`;
  for (const v of niceTicks(0, maxV, 4)) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${m.l - 5}" y="${y(v) + 3.5}" text-anchor="end" class="ax">${v}</text>`;
  for (let i = 0; i < n; i += 30) svg += `<text x="${x(i)}" y="${H - 6}" text-anchor="middle" class="ax">${clockLabel(scn, i * 60, false)}</text>`;
  svg += `<path d="${path(b.searchingSeries.map((v, i) => [x(i), y(v)]))}" fill="none" stroke="var(--c-base)" stroke-width="2.2"/>`;
  svg += `<path d="${path(g.searchingSeries.map((v, i) => [x(i), y(v)]))}" fill="none" stroke="var(--teal)" stroke-width="2.4"/>`;
  svg += '</svg>';
  return svg;
}

/** Field validation distribution (strip plot of gate-to-park seconds). */
export function fieldStrip(values: number[], W: number, H: number): string {
  if (!values.length) return '';
  const maxV = Math.max(60, ...values);
  const m = { l: 10, r: 10, t: 10, b: 22 };
  const iw = W - m.l - m.r;
  const x = (v: number) => m.l + (v / maxV) * iw;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="chart" role="img" aria-label="Observed gate-to-park times">`;
  svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}" stroke="${GRID}"/>`;
  for (const v of niceTicks(0, maxV / 60, 5)) svg += `<text x="${x(v * 60)}" y="${H - 6}" text-anchor="middle" class="ax">${v} min</text>`;
  values.forEach((v, i) => {
    svg += `<circle cx="${x(v)}" cy="${m.t + 6 + (i % 4) * 6}" r="4" fill="var(--field)" opacity=".85"/>`;
  });
  svg += '</svg>';
  return svg;
}

export const CHART_INK = INK;

// ---------------- arrivals and departures, 5-minute windows ----------------
export interface FlowSummary {
  arriving: number;
  arrivingHist: number;
  leaving: number;
  net: number;
  endShare: number;
  paidPending: number;
  fillAt: number | null;
}

export function flowSummary(sim: Sim, f: Forecast | null): FlowSummary | null {
  if (!f) return null;
  const sum = (a: number[], n: number) => a.slice(0, n).reduce((x, y) => x + y, 0);
  const arriving = sum(f.intent.arrivals, 30);
  const leaving = sum(f.intent.departures, 30);
  return {
    arriving,
    arrivingHist: sum(f.hist.arrivals, 30),
    leaving,
    net: arriving - leaving,
    endShare: f.intent.occ[29] / Math.max(1, f.usable),
    paidPending: sim.paidPending(),
    fillAt: f.fillMin.intent !== null ? sim.t + f.fillMin.intent * 60 : null
  };
}

const I_CAR = '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>';
const I_ARROWS = '<path d="M8 3 4 7l4 4M4 7h16M16 21l4-4-4-4M20 17H4"/>';
const I_ALERT = '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>';
const svgIc = (p: string, s = 20) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;

/** Parking occupancy, shown as vehicle movement: who arrives and who leaves in each of the next six 5-minute windows. */
export function flowPanel(sim: Sim, f: Forecast | null, o: { w: number; h: number; id: string; compact?: boolean }): string {
  const fs = flowSummary(sim, f);
  if (!f || !fs) return '<p class="muted">The forecast starts after the first simulated minute.</p>';
  const s = sim.scn;
  const labels = ['Now', '5–10', '10–15', '15–20', '20–25', '25–30'];
  const wins = labels.map((label, k) => ({
    label,
    arr: Math.round(f.intent.arrivals.slice(k * 5, k * 5 + 5).reduce((x, y) => x + y, 0)),
    dep: Math.round(f.intent.departures.slice(k * 5, k * 5 + 5).reduce((x, y) => x + y, 0))
  }));
  const arriving = wins.reduce((a, w) => a + w.arr, 0);
  const leaving = wins.reduce((a, w) => a + w.dep, 0);
  const net = arriving - leaving;
  const c = sim.counts();
  const nowPct = Math.round((c.occupied / c.usable) * 100);
  const endPct = Math.round(fs.endShare * 100);

  // chart
  const W = o.w, H = o.h;
  const m = { l: 26, r: 4, t: 16, b: o.compact ? 18 : 32 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const vmax = Math.max(5, ...wins.map((w) => Math.max(w.arr, w.dep)));
  const ticks = niceTicks(0, vmax, o.compact ? 2 : 4);
  const ymax = Math.max(o.compact ? vmax * 1.3 : vmax, ticks[ticks.length - 1]);
  const y = (v: number) => m.t + ih - (v / ymax) * ih;
  const gw = iw / wins.length;
  const bw = Math.min(o.compact ? 16 : 30, gw * 0.3);
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" class="chart flow-chart" role="img" aria-label="Vehicles arriving and leaving in each 5-minute window for the next 30 minutes">`;
  for (const v of ticks) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${m.l - 6}" y="${y(v) + 3.5}" text-anchor="end" class="ax">${v}</text>`;
  wins.forEach((w, i) => {
    const cx = m.l + i * gw + gw / 2;
    ([[w.arr, 'var(--flow-in)'], [w.dep, 'var(--flow-out)']] as [number, string][]).forEach(([v, col], j) => {
      const x = cx - bw - 2 + j * (bw + 4);
      const h = Math.max(v > 0 ? 2 : 0, m.t + ih - y(v));
      svg += `<rect x="${x.toFixed(1)}" y="${(m.t + ih - h).toFixed(1)}" width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="${col}"><title>${j ? 'Departing' : 'Arriving'}, ${w.label === 'Now' ? 'next 5 minutes' : `${w.label} minutes from now`}: ${v}</title></rect>`;
      svg += `<text x="${(x + bw / 2).toFixed(1)}" y="${(m.t + ih - h - 4).toFixed(1)}" text-anchor="middle" class="ax flow-v">${v}</text>`;
    });
    svg += `<text x="${cx}" y="${m.t + ih + 14}" text-anchor="middle" class="ax${i === 0 ? ' flow-now' : ''}">${w.label}</text>`;
  });
  if (!o.compact) svg += `<text x="${m.l + iw / 2}" y="${H - 3}" text-anchor="middle" class="ax">Minutes from now</text>`;
  svg += '</svg>';

  // call to action
  let tone = 'ok', title: string, text: string;
  if (fs.fillAt !== null && fs.fillAt - sim.t <= 30 * 60) {
    tone = 'crit'; title = 'Prepare overflow access';
    text = `Occupancy forecast to reach 95% by ${clockLabel(s, fs.fillAt, false)}.`;
  } else if (net >= 3) {
    tone = 'warn'; title = 'Watch entry queue';
    text = `More vehicles arriving than leaving (+${net} net).`;
  } else if (net <= -3) {
    title = 'Space opening up';
    text = `More vehicles leaving than arriving (${net} net).`;
  } else {
    title = 'Flow is balanced';
    text = 'Arrivals and departures are roughly even.';
  }
  const tiles = `<div class="flow-tiles${o.compact ? ' compact' : ''}">
      <div class="ft ft-in"><span class="ft-ic">${svgIc(I_CAR, o.compact ? 17 : 24)}</span><div><b>${arriving}</b><span>arriving</span><small>in the next 30 minutes</small></div></div>
      <div class="ft ft-out"><span class="ft-ic">${svgIc(I_CAR, o.compact ? 17 : 24)}</span><div><b>${leaving}</b><span>leaving</span><small>in the next 30 minutes</small></div></div>
      <div class="ft ft-net ft-${net > 0 ? 'up' : 'down'}"><span class="ft-ic">${svgIc(I_ARROWS, o.compact ? 17 : 24)}</span><div><b>${net > 0 ? '+' : net < 0 ? '−' : ''}${Math.abs(net)}</b><span>net vehicles</span><small>${nowPct}% full now, ${endPct}% in 30 min</small></div></div>
    </div>`;
  const legend = `<div class="flow-legend"><span><i class="fl-dot fl-in"></i>Arriving (entry)</span><span><i class="fl-dot fl-out"></i>Departing (exit)</span></div>`;
  return `${tiles}<div class="flow-chart-head">${legend}</div><div class="flow-chart-box">${svg}</div>
    <div class="flow-call flow-${tone}"><span class="fc-ic">${svgIc(tone === 'ok' ? I_CAR : I_ALERT, 18)}</span><b>${esc(title)}</b><i class="fc-sep" aria-hidden="true"></i><span>${esc(text)}</span></div>`;
}

// ---------------- members vs non-members ----------------
const I_STAR = '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>';
const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

/** Live: cars parked right now, rewards members vs everyone else, overall and by level. */
export function memberLivePanel(sim: Sim): string {
  const ms = sim.memberSplit();
  const total = ms.member + ms.other;
  const pM = total ? Math.round((ms.member / total) * 100) : 0;
  const pO = total ? 100 - pM : 0;
  let eAll = sim.entriesThisMinute;
  let eMem = sim.entriesMemberThisMinute;
  for (const h of sim.history) if (h.t > sim.t - 900) { eAll += h.entries; eMem += h.entriesMember; }
  const sAll = ms.searchingMember + ms.searchingOther;
  const pf = sim.counts().perFloor;

  const tiles = `<div class="flow-tiles two">
      <div class="ft ft-mem"><span class="ft-ic">${svgIc(I_STAR, 24)}</span><div><b>${ms.member}</b><span>${plural(ms.member, 'member', 'members')} parked</span><small>${pM}% of parked cars</small></div></div>
      <div class="ft ft-non"><span class="ft-ic">${svgIc(I_CAR, 24)}</span><div><b>${ms.other}</b><span>${plural(ms.other, 'non-member', 'non-members')} parked</span><small>${pO}% of parked cars</small></div></div>
    </div>`;
  const seg = (cls: string, p: number, label: string) => `<i class="${cls}" style="width:${p}%">${p >= 9 ? `<span>${label}</span>` : ''}</i>`;
  const split = `<div class="mem-split" role="img" aria-label="${ms.member} members and ${ms.other} non-members parked">${seg('ms-m', pM, `${pM}% members`)}${seg('ms-o', pO, `${pO}% non-members`)}</div>`;

  const levels = [0, 1, 2]
    .map((f) => {
      const x = ms.byFloor[f];
      const u = Math.max(1, pf[f].usable);
      const wm = (x.member / u) * 100;
      const wo = (x.other / u) * 100;
      return `<div class="ml"><span class="plate-sm">${FLOOR_NAMES[f]}</span>
        <div class="ml-bar" role="img" aria-label="${FLOOR_NAMES[f]}: ${x.member} members, ${x.other} non-members, ${pf[f].usable} usable bays"><i class="ms-m" style="width:${wm.toFixed(1)}%"></i><i class="ms-o" style="width:${wo.toFixed(1)}%"></i></div>
        <span class="ml-n"><b class="ml-m">${x.member}</b> + <b>${x.other}</b><small> of ${pf[f].usable} bays</small></span></div>`;
    })
    .join('');

  const facts = `<div class="mem-facts">
      <div><span>Came in, last 15 min</span><b>${eMem} <small>of ${eAll}</small></b><small>${plural(eMem, 'was a member', 'were members')}</small></div>
      <div><span>Looking for a bay</span><b>${ms.searchingMember} <small>of ${sAll}</small></b><small>${plural(ms.searchingMember, 'is a member', 'are members')}</small></div>
    </div>`;

  const q = sim.bookable('member');
  const elsewhere = ms.member - ms.inMemberBays;
  const full = q.free === 0;
  const call = `<div class="flow-call flow-${full ? 'warn' : 'ok'}"><span class="fc-ic">${svgIc(I_STAR, 18)}</span><b>${full ? 'Member bays full' : 'Member bays available'}</b><i class="fc-sep" aria-hidden="true"></i><span>${full ? `All ${q.total} are taken or held. ` : `${q.free} of ${q.total} free. `}${elsewhere} ${plural(elsewhere, 'member is', 'members are')} parked in general bays.</span></div>`;

  return `${tiles}${split}<div class="mem-levels" aria-label="Parked cars by level">${levels}</div>${facts}${call}`;
}

/** Past: cars parked every 10 minutes since the window opened, members stacked under non-members. */
export function memberHistoryPanel(sim: Sim, o: { w: number; h: number }): string {
  const s = sim.scn;
  const H = sim.history;
  if (!H.length) return '<p class="muted">History starts after the first simulated minute.</p>';
  const live = sim.memberSplit();
  const STEP = 600;
  const n = Math.floor(sim.tEnd / STEP) + 1;
  type Col = { t: number; m: number; o: number; kind: 'past' | 'now' | 'future' };
  const cols: Col[] = [];
  let nowPlaced = false;
  for (let k = 0; k < n; k++) {
    const tk = k * STEP;
    const rec = tk <= sim.t ? H.find((h) => h.t >= tk) : undefined;
    if (rec) cols.push({ t: tk, m: rec.parkedMember, o: rec.parkedOther, kind: 'past' });
    else if (!nowPlaced && sim.t < sim.tEnd) { cols.push({ t: sim.t, m: live.member, o: live.other, kind: 'now' }); nowPlaced = true; }
    else cols.push({ t: tk, m: 0, o: 0, kind: 'future' });
  }

  // headline numbers, minute by minute
  let peak = H[0], shareSum = 0, shareN = 0, eAll = sim.entriesThisMinute, eMem = sim.entriesMemberThisMinute;
  for (const h of H) {
    if (h.parkedMember > peak.parkedMember) peak = h;
    const tot = h.parkedMember + h.parkedOther;
    if (tot) { shareSum += h.parkedMember / tot; shareN++; }
    eAll += h.entries;
    eMem += h.entriesMember;
  }
  const peakNow = live.member > peak.parkedMember;
  const peakN = peakNow ? live.member : peak.parkedMember;
  const peakT = peakNow ? sim.t : peak.t;
  const start = clockLabel(s, 0, false);
  const avgShare = shareN ? Math.round((shareSum / shareN) * 100) : 0;
  const stats = `<div class="mem-stats">
      <div><span>Most members parked</span><b>${peakN}</b><small>${peakNow ? 'right now' : `at ${clockLabel(s, peakT, false)}`}</small></div>
      <div><span>Average member share</span><b>${avgShare}%</b><small>of parked cars since ${start}</small></div>
      <div><span>Members who came in</span><b>${eMem} <small>of ${eAll}</small></b><small>${eAll ? Math.round((eMem / eAll) * 100) : 0}% of entries since ${start}</small></div>
    </div>`;

  // chart
  const W = o.w, Ht = o.h;
  const mg = { l: 30, r: 6, t: 16, b: 26 };
  const iw = W - mg.l - mg.r, ih = Ht - mg.t - mg.b;
  const cap = sim.usable;
  const ticks = niceTicks(0, cap, 4).filter((v) => v < cap - 8);
  const y = (v: number) => mg.t + ih - (v / cap) * ih;
  const base = mg.t + ih;
  const gw = iw / n;
  const bw = Math.min(36, gw * 0.62);
  const every = gw < 30 ? 3 : 2;
  let svg = `<svg viewBox="0 0 ${W} ${Ht}" width="100%" height="${Ht}" class="chart mem-chart" role="img" aria-label="Members and non-members parked every 10 minutes since ${start}">`;
  for (const v of ticks) svg += `<line x1="${mg.l}" x2="${W - mg.r}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${mg.l - 6}" y="${y(v) + 3.5}" text-anchor="end" class="ax">${v}</text>`;
  svg += `<line x1="${mg.l}" x2="${W - mg.r}" y1="${y(cap)}" y2="${y(cap)}" class="mem-cap"/><text x="${W - mg.r}" y="${y(cap) - 4}" text-anchor="end" class="ax">${cap} bays</text>`;
  cols.forEach((c, i) => {
    const cx = mg.l + i * gw + gw / 2;
    const x = cx - bw / 2;
    const clock = clockLabel(s, c.t, false);
    if (c.kind !== 'future') {
      const hm = (c.m / cap) * ih;
      const ho = (c.o / cap) * ih;
      const tot = c.m + c.o;
      const share = tot ? Math.round((c.m / tot) * 100) : 0;
      svg += `<g class="mem-col${c.kind === 'now' ? ' mem-now' : ''}"><title>${c.kind === 'now' ? `Now (${clock})` : clock}: ${c.m} members, ${c.o} non-members (${share}% members)</title>`;
      svg += `<rect x="${x.toFixed(1)}" y="${(base - hm - ho).toFixed(1)}" width="${bw.toFixed(1)}" height="${ho.toFixed(1)}" rx="3" class="mb-o"/>`;
      svg += `<rect x="${x.toFixed(1)}" y="${(base - hm).toFixed(1)}" width="${bw.toFixed(1)}" height="${hm.toFixed(1)}" rx="2" class="mb-m"/>`;
      if (ho >= 15) svg += `<text x="${cx.toFixed(1)}" y="${(base - hm - ho / 2 + 4).toFixed(1)}" text-anchor="middle" class="mv-o">${c.o}</text>`;
      if (hm >= 15) svg += `<text x="${cx.toFixed(1)}" y="${(base - hm / 2 + 4).toFixed(1)}" text-anchor="middle" class="mv-m">${c.m}</text>`;
      else svg += `<text x="${cx.toFixed(1)}" y="${(base - hm - ho - 5).toFixed(1)}" text-anchor="middle" class="mv-m-out">${c.m}</text>`;
      svg += '</g>';
    } else {
      svg += `<line x1="${x.toFixed(1)}" x2="${(x + bw).toFixed(1)}" y1="${base - 0.5}" y2="${base - 0.5}" class="mem-future"/>`;
    }
    const showLabel = c.kind === 'now' || i % every === 0;
    if (showLabel) svg += `<text x="${cx.toFixed(1)}" y="${base + 16}" text-anchor="middle" class="ax${c.kind === 'now' ? ' flow-now' : c.kind === 'future' ? ' mem-fut-l' : ''}">${c.kind === 'now' ? 'Now' : clock}</text>`;
  });
  svg += '</svg>';

  const legend = `<div class="flow-legend"><span><i class="fl-dot fl-mem"></i>Members</span><span><i class="fl-dot fl-non"></i>Non-members</span></div>`;

  // what changed since the window opened
  const first = H[0];
  const share0 = first.parkedMember + first.parkedOther ? Math.round((first.parkedMember / (first.parkedMember + first.parkedOther)) * 100) : 0;
  const liveTot = live.member + live.other;
  const shareNow = liveTot ? Math.round((live.member / liveTot) * 100) : 0;
  const d = shareNow - share0;
  const dm = live.member - first.parkedMember;
  let title: string, text: string;
  if (sim.t < 300) {
    title = 'Just started';
    text = `Members are ${shareNow}% of parked cars. The picture builds every simulated minute.`;
  } else if (Math.abs(d) < 3) {
    title = 'Member share steady';
    text = `About ${shareNow}% of parked cars since ${start} (${dm >= 0 ? '+' : '−'}${Math.abs(dm)} ${plural(Math.abs(dm), 'member', 'members')}).`;
  } else {
    title = d > 0 ? 'Member share rising' : 'Member share falling';
    text = `${shareNow}% of parked cars now, ${d > 0 ? 'up' : 'down'} from ${share0}% at ${start}.`;
  }
  const call = `<div class="flow-call flow-ok"><span class="fc-ic">${svgIc(I_STAR, 18)}</span><b>${esc(title)}</b><i class="fc-sep" aria-hidden="true"></i><span>${esc(text)}</span></div>`;

  return `${stats}<div class="flow-chart-head">${legend}</div><div class="flow-chart-box">${svg}</div>${call}`;
}
