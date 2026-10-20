// Explainable zone allocation. Hard eligibility and capacity constraints first, then a transparent
// weighted score over min-max normalised inputs. Guidance is zone-level, never an exclusive general bay.

import { Layout, BayType, DestId, ZoneId, FLOORS, ZONES, FLOOR_NAMES, DEST_BY_ID, BAY_TYPE_LABEL, GEdge } from './layout';

export interface AllocWeights {
  drive: number;
  walk: number;
  congestion: number;
  load: number;
  forecast: number;
}

export const DEFAULT_WEIGHTS: AllocWeights = { drive: 0.15, walk: 0.3, congestion: 0.2, load: 0.2, forecast: 0.15 };

export const WEIGHT_LABELS: Record<keyof AllocWeights, string> = {
  drive: 'Driving distance from current position',
  walk: 'Walking distance to destination lift',
  congestion: 'Vehicles on the approach and in the zone',
  load: 'Vehicles already guided to the zone vs free bays',
  forecast: 'Forecast arrivals (next 30 min) vs free bays'
};

export interface Candidate {
  floor: number;
  zone: ZoneId;
  inv: BayType;
  label: string;
  free: number;
  heading: number;
  effective: number;
  drive: number;
  walk: number;
  congestion: number;
  forecast: number;
  parts: AllocWeights; // weighted contribution of each factor (0..weight)
  bonus: number;
  total: number;
  entryEdge: number;
  path: number[];
}

export interface Allocation {
  t: number;
  vehicleCode: string;
  vehicle: number;
  dest: DestId;
  fromLabel: string;
  chosen: Candidate | null;
  ranked: Candidate[];
  feasibleCount: number;
  mode: 'normal' | 'shared' | 'expected-departure' | 'none';
  explanation: string;
  message: string;
  /** The zone that would have won with the forecast term removed, when that differs from the choice. */
  withoutForecast: Candidate | null;
}

export interface AllocContext {
  L: Layout;
  t: number;
  isFree: (bay: number) => boolean;
  heading: (floor: number, zone: ZoneId, inv: BayType) => number;
  edgeLoad: (edge: number) => number;
  expectedDepartures: (floor: number, zone: ZoneId, inv: BayType) => number;
  forecastByLift: (lift: ZoneId) => number;
  floorBias: number[];
  weights: AllocWeights;
}

export function zoneLabel(floor: number, zone: ZoneId, inv?: BayType): string {
  const base = `${FLOOR_NAMES[floor]} Zone ${zone}`;
  if (!inv || inv === 'general') return base;
  return `${base} ${BAY_TYPE_LABEL[inv].replace(' charging', '').replace('Designated ', '')} bays`;
}

function dijkstraFrom(L: Layout, from: number, weight: (e: GEdge) => number) {
  const n = L.nodes.length;
  const dist = new Float64Array(n).fill(Infinity);
  const prev = new Int32Array(n).fill(-1);
  const done = new Uint8Array(n);
  dist[from] = 0;
  for (;;) {
    let u = -1;
    let best = Infinity;
    for (let i = 0; i < n; i++) if (!done[i] && dist[i] < best) { best = dist[i]; u = i; }
    if (u < 0) break;
    done[u] = 1;
    for (const eid of L.out[u]) {
      const e = L.edges[eid];
      const nd = dist[u] + weight(e);
      if (nd < dist[e.to]) { dist[e.to] = nd; prev[e.to] = eid; }
    }
  }
  const pathTo = (to: number): number[] => {
    const p: number[] = [];
    let cur = to;
    let guard = 0;
    while (cur !== from && prev[cur] >= 0 && guard++ < 200) { p.push(prev[cur]); cur = L.edges[prev[cur]].from; }
    return p.reverse();
  };
  return { dist, pathTo };
}

function norm(values: number[]): (v: number) => number {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return (v: number) => (max - min < 1e-9 ? 0 : (v - min) / (max - min));
}

export function allocate(ctx: AllocContext, v: { code: string; index: number; elig: BayType[]; dest: DestId }, fromNode: number, fromLabel: string): Allocation {
  const { L, weights } = ctx;
  const lift = DEST_BY_ID[v.dest].lift;
  const dj = dijkstraFrom(L, fromNode, (e) => (e.kind === 'exit' ? 1e6 : e.len));
  const raw: Candidate[] = [];
  const invs = Array.from(new Set(v.elig));
  for (const f of FLOORS) {
    for (const z of ZONES) {
      for (const inv of invs) {
        const bays = L.bays.filter((b) => b.floor === f && b.zone === z && b.type === inv && b.flag !== 'maintenance');
        if (!bays.length) continue;
        const freeBays = bays.filter((b) => ctx.isFree(b.idx));
        const heading = ctx.heading(f, z, inv);
        const free = freeBays.length;
        const walkSet = freeBays.length ? freeBays : bays;
        const walk = walkSet.reduce((a, b) => a + b.walk[lift], 0) / walkSet.length;
        const a1Free = freeBays.some((b) => b.row < 2);
        const entryEdge = L.segEdge(f, a1Free || !freeBays.length ? 1 : 2, z);
        const entryNode = L.edges[entryEdge].from;
        const drive = dj.dist[entryNode];
        if (!isFinite(drive)) continue;
        const path = dj.pathTo(entryNode);
        let congestion = 0;
        for (const eid of path) congestion += ctx.edgeLoad(eid);
        congestion += ctx.edgeLoad(L.segEdge(f, 1, z)) + ctx.edgeLoad(L.segEdge(f, 2, z));
        const effective = free - heading;
        const forecast = ctx.forecastByLift(z) / FLOORS.length / Math.max(1, effective);
        raw.push({
          floor: f,
          zone: z,
          inv,
          label: zoneLabel(f, z, inv),
          free,
          heading,
          effective,
          drive,
          walk,
          congestion,
          forecast,
          parts: { drive: 0, walk: 0, congestion: 0, load: 0, forecast: 0 },
          bonus: 0,
          total: 0,
          entryEdge,
          path
        });
      }
    }
  }

  let mode: Allocation['mode'] = 'normal';
  let pool = raw.filter((c) => c.effective >= 1);
  if (!pool.length) {
    pool = raw.filter((c) => c.free >= 1);
    mode = 'shared';
  }
  if (!pool.length) {
    const withDep = raw.map((c) => ({ c, d: ctx.expectedDepartures(c.floor, c.zone, c.inv) })).filter((x) => x.d > 0);
    if (withDep.length) {
      withDep.sort((a, b) => b.d - a.d || a.c.walk - b.c.walk);
      const top = withDep.slice(0, 3).map((x) => x.c);
      pool = top;
      mode = 'expected-departure';
    } else {
      pool = raw.slice();
      mode = 'none';
    }
  }

  const nDrive = norm(pool.map((c) => c.drive));
  const nWalk = norm(pool.map((c) => c.walk));
  const nCong = norm(pool.map((c) => c.congestion));
  const loadVal = (c: Candidate) => c.heading / Math.max(1, c.free);
  const nLoad = norm(pool.map(loadVal));
  const nFc = norm(pool.map((c) => c.forecast));
  for (const c of pool) {
    c.parts = {
      drive: weights.drive * (1 - nDrive(c.drive)),
      walk: weights.walk * (1 - nWalk(c.walk)),
      congestion: weights.congestion * (1 - nCong(c.congestion)),
      load: weights.load * (1 - nLoad(loadVal(c))),
      forecast: weights.forecast * (1 - nFc(c.forecast))
    };
    c.bonus = (c.inv !== 'general' ? 0.1 : 0) + (ctx.floorBias[c.floor] || 0);
    c.total = c.parts.drive + c.parts.walk + c.parts.congestion + c.parts.load + c.parts.forecast + c.bonus;
  }
  pool.sort((a, b) => b.total - a.total || a.walk - b.walk);
  const chosen = pool[0] || null;
  let noFc: Candidate | null = null;
  for (const c of pool) {
    const sc = c.total - c.parts.forecast;
    if (!noFc || sc > noFc.total - noFc.parts.forecast + 1e-9 || (Math.abs(sc - (noFc.total - noFc.parts.forecast)) < 1e-9 && c.walk < noFc.walk)) noFc = c;
  }
  const withoutForecast = chosen && noFc && noFc !== chosen && weights.forecast > 0 ? noFc : null;
  const ranked = pool.slice(0, 3);
  const explanation = chosen ? explain(chosen, pool, lift, mode, ctx) : 'No candidate zone could be reached.';
  const message = chosen ? driverMessage(chosen, lift, mode) : 'No suitable bay is available right now.';
  return {
    t: ctx.t,
    vehicleCode: v.code,
    vehicle: v.index,
    dest: v.dest,
    fromLabel,
    chosen,
    ranked,
    feasibleCount: raw.filter((c) => c.effective >= 1).length,
    mode,
    explanation,
    message,
    withoutForecast
  };
}

export function driverMessage(c: Candidate, lift: ZoneId, mode: Allocation['mode']): string {
  const where = c.inv === 'general' ? `Zone ${c.zone}` : `Zone ${c.zone} ${BAY_TYPE_LABEL[c.inv].replace(' charging', '').replace('Designated ', '').toLowerCase()} bays`;
  const base = `Proceed to ${FLOOR_NAMES[c.floor]} · ${where} · Follow signs to Lift ${lift}.`;
  if (mode === 'expected-departure') return `${base} No bay is free yet; departures are expected there.`;
  if (mode === 'none') return `No suitable bay is free. ${base}`;
  return base;
}

function explain(c: Candidate, pool: Candidate[], lift: ZoneId, mode: Allocation['mode'], ctx: AllocContext): string {
  const parts: string[] = [];
  if (mode === 'expected-departure') {
    const d = ctx.expectedDepartures(c.floor, c.zone, c.inv);
    return `${c.label} recommended: no suitable bay is free right now, and ${d} departure${d === 1 ? ' is' : 's are'} expected there shortly (payment recorded, bay still occupied).`;
  }
  if (mode === 'none') return `${c.label} suggested as a holding area: no suitable bay is free or expected to free up soon. An alternative such as overflow parking should be offered.`;
  const cap =
    mode === 'shared'
      ? `${c.free} suitable bay${c.free === 1 ? ' is' : 's are'} free but other drivers are already heading there`
      : c.heading > 0
        ? `${c.effective} suitable bay${c.effective === 1 ? ' remains' : 's remain'} after allowing for ${c.heading} driver${c.heading === 1 ? '' : 's'} already heading there`
        : `${c.effective} suitable bay${c.effective === 1 ? ' is' : 's are'} free`;
  parts.push(cap);
  const walkM = Math.round(c.walk);
  parts.push(walkM <= 25 ? `Lift ${lift} is nearby (about ${walkM} m on foot)` : `Lift ${lift} is about ${walkM} m on foot`);
  const alt = pool
    .filter((p) => p !== c)
    .sort((a, b) => a.walk - b.walk)[0];
  if (alt) {
    if (alt.walk < c.walk - 3) {
      if (alt.congestion >= c.congestion + 2) parts.push(`${alt.label} is closer to Lift ${lift} but ${Math.round(alt.congestion)} vehicles are on its approach`);
      else if (alt.heading >= 1 && alt.effective <= 2) parts.push(`${alt.label} is closer but ${alt.heading} driver${alt.heading === 1 ? ' is' : 's are'} already heading to its last ${alt.free} bay${alt.free === 1 ? '' : 's'}`);
      else if (alt.forecast > c.forecast * 1.5) parts.push(`${alt.label} is closer but is forecast to fill within 30 minutes`);
      else if (alt.drive > c.drive + 30) parts.push(`${alt.label} is closer on foot but needs about ${Math.round(alt.drive - c.drive)} m more driving`);
      else parts.push(`${alt.label} scores slightly lower overall (${alt.total.toFixed(2)} vs ${c.total.toFixed(2)})`);
    } else if (c.inv !== 'general') {
      parts.push(`it uses the ${BAY_TYPE_LABEL[c.inv].toLowerCase()} inventory this driver is eligible for`);
    } else if (alt.congestion > c.congestion + 1) {
      parts.push(`its approach is clearer than ${alt.label} (${Math.round(c.congestion)} vs ${Math.round(alt.congestion)} vehicles)`);
    }
  }
  const last = parts.pop();
  return `${c.label} recommended: ${parts.join(', ')}${parts.length ? ', and ' : ''}${last}.`;
}
