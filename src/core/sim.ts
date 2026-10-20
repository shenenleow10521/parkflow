// Discrete-time (1 s) simulation engine. Single source of truth for vehicles, bays, reservations,
// allocation decisions, events and the per-minute history that feeds every chart and metric.

import { Layout, Bay, BayType, DestId, ZoneId, FLOOR_NAMES, DEST_BY_ID, BAY_TYPE_LABEL, typeText, shortestPath } from './layout';
import { ScenarioDef, Demand, generateDemand, Source, clockLabel, stableUnit } from './scenarios';
import { allocate, Allocation, AllocContext, AllocWeights, zoneLabel } from './allocation';
import { computeForecast, Forecast, ForecastAssumptions, forecastByLift } from './forecast';
import { hash01 } from './rng';

export type Policy = 'guided' | 'unguided';
export type VState = 'pending' | 'queued' | 'driving' | 'parking' | 'parked' | 'unparking' | 'leaving' | 'exited' | 'cancelled' | 'diverted';

export interface Vehicle {
  i: number;
  code: string;
  key: string;
  arrivalT: number;
  durationS: number;
  dest: DestId;
  cls: 'ice' | 'ev';
  elig: BayType[];
  member: boolean;
  source: Source | 'demo';
  threshold: number;
  coming: boolean;
  etaNoiseS: number;
  resId: string | null;
  initial: boolean;
  injected: boolean;
  state: VState;
  edge: number;
  s: number;
  route: number[];
  queueT: number;
  gateT: number;
  parkT: number;
  paidT: number;
  departT: number;
  exitT: number;
  searchDist: number;
  bay: number;
  man: number;
  target: { floor: number; zone: ZoneId; inv: BayType } | null;
  alloc: Allocation | null;
  reroutes: number;
  relaxed: boolean;
  gaveUp: boolean;
  seenA1: boolean[];
  seenA2: boolean[];
  deepest: number;
  notice: string;
  // previous tick snapshot for render interpolation
  pEdge: number;
  pS: number;
  pMan: number;
  pState: VState;
  mt: number;
}

export interface Reservation {
  id: string;
  type: 'ev' | 'family' | 'member';
  bay: number;
  windowStart: number;
  windowEnd: number;
  grace: number;
  durationS: number;
  status: 'confirmed' | 'checked-in' | 'parked' | 'cancelled' | 'expired';
  createdT: number;
  vehicle: number;
  checkInT: number;
  closedT: number;
  userCreated: boolean;
}

export type EventKind = 'guide' | 'park' | 'depart' | 'payment' | 'reroute' | 'reservation' | 'operator' | 'forecast' | 'alert';

export interface SimEvent {
  t: number;
  kind: EventKind;
  text: string;
  tone: 'info' | 'ok' | 'warn' | 'crit';
  vehicle?: number;
  bay?: number;
}

export interface MinuteRecord {
  t: number;
  occupied: number;
  usable: number;
  generalFree: number;
  searching: number;
  queue: number;
  entries: number;
}

export interface ForecastSnapshot {
  madeT: number;
  forT: number;
  hist: number;
  intent: number;
  histLo: number;
  histHi: number;
  intentLo: number;
  intentHi: number;
}

export interface AssistanceRequest {
  id: string;
  t: number;
  etaMin: number;
  status: 'logged' | 'acknowledged';
}

export interface OperatorState {
  offerActive: boolean;
  offerPausedT: number;
  offerResponse: number;
  offerCancelled: number;
  laterApplied: boolean;
  laterResponse: number;
  laterShifted: number;
  floorBiasApplied: number; // -1 none, else floor index
  overflowApplied: boolean;
  overflowResponse: number;
  overflowDiverted: number;
}

export interface SimOptions {
  policy: Policy;
  live: boolean;
  weights: AllocWeights;
  assumptions: ForecastAssumptions;
}

export const GAP = 7;
export const MANEUVER_S = 7;
export const GIVE_UP_S = 20 * 60;
const SPEED: Record<string, number> = { cruise: 3.2, search: 2.2, connector: 3.4, road: 3.4, ramp: 2.6, gate: 2.0, approach: 2.4, exit: 3.0 };
const GUIDE_EXPIRY_S = 6 * 60;

export class Sim {
  readonly L: Layout;
  readonly scn: ScenarioDef;
  readonly opts: SimOptions;
  t = 0;
  readonly tWindowEnd: number;
  readonly tEnd: number;
  vehicles: Vehicle[] = [];
  occ: Int32Array;
  claim: Int32Array;
  hold: (string | null)[];
  reservations: Reservation[] = [];
  events: SimEvent[] = [];
  history: MinuteRecord[] = [];
  decisions: Allocation[] = [];
  snapshots: ForecastSnapshot[] = [];
  assistance: AssistanceRequest[] = [];
  forecast: Forecast | null = null;
  /** One entry per forecast refresh (each simulated minute): the intent occupancy curve and headline numbers. */
  forecastLog: { t: number; occ: number[]; arr30: number; fill: number | null; peak: number }[] = [];
  gateQueue: number[] = [];
  nextGateT = 0;
  peakQueue = 0;
  entriesThisMinute = 0;
  edgeCount: Float32Array;
  heading = new Map<string, { v: number; exp: number }[]>();
  op: OperatorState;
  floorBias = [0, 0, 0];
  private pending: number[] = [];
  private buckets: number[][];
  usable: number;
  private pressureAlerted = false;

  constructor(L: Layout, scn: ScenarioDef, opts: SimOptions, demand?: Demand) {
    this.L = L;
    this.scn = scn;
    this.opts = opts;
    this.tWindowEnd = scn.windowMin * 60;
    this.tEnd = (scn.windowMin + scn.drainMin) * 60;
    this.occ = new Int32Array(L.bays.length).fill(-1);
    this.claim = new Int32Array(L.bays.length).fill(-1);
    this.hold = L.bays.map(() => null);
    this.edgeCount = new Float32Array(L.edges.length);
    this.buckets = L.edges.map(() => []);
    this.usable = L.bays.filter((b) => b.flag !== 'maintenance').length;
    this.op = {
      offerActive: !!scn.offer,
      offerPausedT: -1,
      offerResponse: 0.5,
      offerCancelled: 0,
      laterApplied: false,
      laterResponse: 0.25,
      laterShifted: 0,
      floorBiasApplied: -1,
      overflowApplied: false,
      overflowResponse: 0.3,
      overflowDiverted: 0
    };
    const d = demand || generateDemand(scn, L);
    this.init(d);
  }

  // ---------- setup ----------
  private newVehicle(partial: Partial<Vehicle> & { key: string }): Vehicle {
    const i = this.vehicles.length;
    const v: Vehicle = {
      i,
      code: `V-${String(101 + i).padStart(4, '0')}`,
      arrivalT: 0,
      durationS: 3600,
      dest: 'atrium',
      cls: 'ice',
      elig: ['general'],
      member: false,
      source: 'routine',
      threshold: 35,
      coming: false,
      etaNoiseS: 0,
      resId: null,
      initial: false,
      injected: false,
      state: 'pending',
      edge: -1,
      s: 0,
      route: [],
      queueT: -1,
      gateT: -1,
      parkT: -1,
      paidT: Infinity,
      departT: Infinity,
      exitT: -1,
      searchDist: 0,
      bay: -1,
      man: 0,
      target: null,
      alloc: null,
      reroutes: 0,
      relaxed: false,
      gaveUp: false,
      seenA1: [false, false, false],
      seenA2: [false, false, false],
      deepest: 0,
      notice: '',
      pEdge: -1,
      pS: 0,
      pMan: 0,
      pState: 'pending',
      mt: -1,
      ...partial
    };
    v.pState = v.state;
    this.vehicles.push(v);
    return v;
  }

  private init(d: Demand) {
    const L = this.L;
    // Reservation bays first, chosen deterministically from bays left free by the initial fill.
    const initialByBay = new Map<number, (typeof d.initial)[number]>();
    for (const s of d.initial) initialByBay.set(s.bay, s);
    for (const r of this.scn.reservations) {
      const candidates = L.bays
        .filter((b) => b.type === r.type && b.flag === 'none' && (b.type !== 'ev' || b.charger === 'ok') && !this.hold[b.idx])
        .sort((a, b) => (initialByBay.has(a.idx) ? 1 : 0) - (initialByBay.has(b.idx) ? 1 : 0) || hash01(r.id + a.id) - hash01(r.id + b.id));
      const bay = candidates[0];
      if (!bay) continue;
      initialByBay.delete(bay.idx);
      this.hold[bay.idx] = r.id;
      this.reservations.push({
        id: r.id,
        type: r.type,
        bay: bay.idx,
        windowStart: r.windowStartMin * 60,
        windowEnd: (r.windowStartMin + r.windowLenMin) * 60,
        grace: 600,
        durationS: r.durationMin * 60,
        status: 'confirmed',
        createdT: -3600,
        vehicle: -1,
        checkInT: -1,
        closedT: -1,
        userCreated: false
      });
    }
    // Initial parked vehicles
    for (const spec of initialByBay.values()) {
      const elapsed = hash01(`el${spec.bay}`) * 3600;
      const v = this.newVehicle({
        key: `init-${spec.bay}`,
        initial: true,
        state: 'parked',
        cls: spec.cls,
        elig: spec.elig,
        member: spec.member,
        dest: spec.dest,
        bay: spec.bay,
        parkT: -elapsed,
        departT: spec.remainingS,
        durationS: spec.remainingS + elapsed
      });
      v.paidT = v.departT - (180 + hash01(`pd${spec.bay}`) * 300);
      this.occ[spec.bay] = v.i;
    }
    // Arrivals
    for (const a of d.arrivals) {
      const v = this.newVehicle({
        key: a.key,
        arrivalT: a.arrivalT,
        durationS: a.durationS,
        dest: a.dest,
        cls: a.cls,
        elig: a.elig,
        member: a.member,
        source: a.source,
        threshold: a.threshold,
        coming: a.coming,
        etaNoiseS: a.etaNoiseS,
        resId: a.resId
      });
      if (a.resId) {
        const r = this.reservations.find((x) => x.id === a.resId);
        if (r) r.vehicle = v.i;
      }
      this.pending.push(v.i);
    }
    this.sortPending();
    this.recordMinute();
    this.updateForecast();
  }

  private sortPending() {
    this.pending.sort((a, b) => this.vehicles[a].arrivalT - this.vehicles[b].arrivalT || a - b);
  }

  // ---------- queries ----------
  clock(withDay = true): string {
    return clockLabel(this.scn, this.t, withDay);
  }

  isFree(bay: number): boolean {
    return this.occ[bay] < 0 && this.claim[bay] < 0 && !this.hold[bay] && this.L.bays[bay].flag === 'none';
  }

  bayStatus(bay: number): 'unavailable' | 'uncertain' | 'reserved' | 'departing' | 'occupied' | 'available' {
    const b = this.L.bays[bay];
    if (b.flag === 'maintenance') return 'unavailable';
    if (b.flag === 'obstructed') return 'uncertain';
    const o = this.occ[bay];
    if (o >= 0) return this.vehicles[o].paidT <= this.t ? 'departing' : 'occupied';
    if (this.claim[bay] >= 0) return 'occupied';
    if (this.hold[bay]) return 'reserved';
    return 'available';
  }

  counts() {
    let occupied = 0;
    let generalFree = 0;
    let specialFree = 0;
    let reserved = 0;
    let departing = 0;
    let uncertain = 0;
    let unavailable = 0;
    const perFloor = [0, 1, 2].map(() => ({ total: 0, usable: 0, occupied: 0, generalFree: 0, specialFree: 0, reserved: 0, departing: 0, uncertain: 0 }));
    for (const b of this.L.bays) {
      const st = this.bayStatus(b.idx);
      const pf = perFloor[b.floor];
      pf.total++;
      if (st === 'unavailable') { unavailable++; continue; }
      pf.usable++;
      if (st === 'uncertain') { uncertain++; pf.uncertain++; occupied++; pf.occupied++; continue; }
      if (st === 'occupied' || st === 'departing') { occupied++; pf.occupied++; if (st === 'departing') { departing++; pf.departing++; } continue; }
      if (st === 'reserved') { reserved++; pf.reserved++; continue; }
      if (b.type === 'general') { generalFree++; pf.generalFree++; } else { specialFree++; pf.specialFree++; }
    }
    return { occupied, generalFree, specialFree, reserved, departing, uncertain, unavailable, usable: this.usable, perFloor };
  }

  searchingVehicles(): Vehicle[] {
    return this.vehicles.filter((v) => (v.state === 'driving' || v.state === 'parking') && v.gateT >= 0 && v.parkT < 0);
  }

  activeVehicles(): Vehicle[] {
    return this.vehicles.filter((v) => v.state === 'driving' || v.state === 'leaving' || v.state === 'parking' || v.state === 'unparking' || v.state === 'parked');
  }

  paidPending(): number {
    let n = 0;
    for (const v of this.vehicles) if (v.state === 'parked' && v.paidT <= this.t) n++;
    return n;
  }

  comingETAs(): number[] {
    const out: number[] = [];
    for (const id of this.pending) {
      const v = this.vehicles[id];
      if (v.state !== 'pending' || !v.coming) continue;
      if (v.arrivalT - this.t <= 45 * 60) out.push(v.arrivalT + v.etaNoiseS);
    }
    return out;
  }

  headingCount(floor: number, zone: ZoneId, inv: BayType): number {
    const list = this.heading.get(`${floor}-${zone}-${inv}`);
    if (!list) return 0;
    return list.filter((h) => h.exp > this.t).length;
  }

  expectedDepartures(floor: number, zone: ZoneId, inv: BayType, within = 300): number {
    let n = 0;
    for (const b of this.L.bays) {
      if (b.floor !== floor || b.zone !== zone || b.type !== inv) continue;
      const o = this.occ[b.idx];
      if (o < 0) continue;
      const v = this.vehicles[o];
      if (v.paidT <= this.t || v.departT - this.t < within) n++;
    }
    return n;
  }

  allocContext(): AllocContext {
    const byLift = forecastByLift(this.forecast, this.scn.destMix);
    return {
      L: this.L,
      t: this.t,
      isFree: (b) => this.isFree(b),
      heading: (f, z, inv) => this.headingCount(f, z, inv),
      edgeLoad: (e) => this.edgeCount[e],
      expectedDepartures: (f, z, inv) => this.expectedDepartures(f, z, inv),
      forecastByLift: (lift) => byLift[lift],
      floorBias: this.floorBias,
      weights: this.opts.weights
    };
  }

  /** What-if allocation for a driver who has not arrived yet (driver preview). Does not change state. */
  previewAllocation(dest: DestId, elig: BayType[]): Allocation {
    return allocate(this.allocContext(), { code: 'Preview', index: -1, elig, dest }, this.L.entryNode, 'Entrance gate');
  }

  routeLength(v: Vehicle): number {
    if (v.edge < 0) return 0;
    let d = this.L.edges[v.edge].len - v.s;
    for (const e of v.route) d += this.L.edges[e].len;
    if (v.bay >= 0 && v.state === 'driving') {
      // route ends at the bay's aisle edge; subtract the part beyond the bay
      const b = this.L.bays[v.bay];
      const last = v.route.length ? v.route[v.route.length - 1] : v.edge;
      if (last === b.edge) d -= this.L.edges[b.edge].len - b.accessS;
    }
    return Math.max(0, d);
  }

  vehicleFloor(v: Vehicle): number {
    if (v.state === 'parked') return this.L.bays[v.bay].floor;
    if (v.edge < 0) return 0;
    const e = this.L.edges[v.edge];
    if (e.kind === 'ramp') return v.s < e.len / 2 ? this.L.nodes[e.from].floor : this.L.nodes[e.to].floor;
    return this.L.nodes[e.from].floor;
  }

  // ---------- events ----------
  log(kind: EventKind, text: string, tone: SimEvent['tone'] = 'info', vehicle?: number, bay?: number) {
    if (!this.opts.live) return;
    this.events.push({ t: this.t, kind, text, tone, vehicle, bay });
    if (this.events.length > 600) this.events.splice(0, this.events.length - 600);
  }

  // ---------- step ----------
  step() {
    const L = this.L;
    this.t += 1;
    const t = this.t;
    for (const v of this.vehicles) {
      v.pEdge = v.edge;
      v.pS = v.s;
      v.pMan = v.man;
      v.pState = v.state;
    }

    // 1. arrivals join the entrance queue (before the gate)
    while (this.pending.length && this.vehicles[this.pending[0]].arrivalT <= t) {
      const v = this.vehicles[this.pending.shift() as number];
      if (v.state !== 'pending') continue;
      if (this.op.overflowApplied && v.coming && !v.resId && this.occupancyShare() >= 0.97 && stableUnit(`ovf${v.key}`) < this.op.overflowResponse) {
        v.state = 'diverted';
        this.op.overflowDiverted++;
        this.log('operator', `${v.code} chose the illustrative overflow car park before reaching the gate (response-rate assumption ${Math.round(this.op.overflowResponse * 100)}%).`, 'info', v.i);
        continue;
      }
      v.state = 'queued';
      v.queueT = t;
      this.gateQueue.push(v.i);
    }
    this.peakQueue = Math.max(this.peakQueue, this.gateQueue.length);

    // 2. reservations: expiry after the grace period
    for (const r of this.reservations) {
      if (r.status === 'confirmed' && t > r.windowEnd + r.grace) {
        r.status = 'expired';
        r.closedT = t;
        if (this.hold[r.bay] === r.id) this.hold[r.bay] = null;
        const b = L.bays[r.bay];
        this.log('reservation', `${r.id} expired as a no-show after the ${r.grace / 60}-minute grace period. ${BAY_TYPE_LABEL[r.type]} bay ${b.id} released to ${typeText(r.type)} inventory.`, 'warn', undefined, r.bay);
      }
    }

    // 3. edge occupancy buckets
    for (const b of this.buckets) b.length = 0;
    for (const v of this.vehicles) {
      if (v.edge >= 0 && (v.state === 'driving' || v.state === 'leaving' || v.state === 'parking' || v.state === 'unparking')) this.buckets[v.edge].push(v.i);
    }
    const minS = new Float64Array(L.edges.length).fill(Infinity);
    for (let e = 0; e < this.buckets.length; e++) {
      const bk = this.buckets[e];
      bk.sort((a, b) => this.vehicles[b].s - this.vehicles[a].s);
      if (bk.length) minS[e] = this.vehicles[bk[bk.length - 1]].s;
    }

    // 4. gate admission (entrance barrier cycle 5 s)
    if (this.gateQueue.length && t >= this.nextGateT && minS[L.gateEdge] >= GAP) {
      const v = this.vehicles[this.gateQueue.shift() as number];
      v.state = 'driving';
      v.edge = L.gateEdge;
      v.s = 0;
      v.gateT = t;
      v.pEdge = L.approachEdge;
      v.pS = L.edges[L.approachEdge].len;
      this.entriesThisMinute++;
      minS[L.gateEdge] = 0;
      this.buckets[L.gateEdge].push(v.i);
      this.nextGateT = t + 5;
      this.onGate(v);
    }

    // 5. departures: unpark when due and the aisle is clear
    for (const v of this.vehicles) {
      if (v.state !== 'parked') continue;
      if (v.paidT <= t && v.paidT > t - 1) {
        this.log('payment', `Payment recorded for the vehicle in ${L.bays[v.bay].id}. Likely departure; bay stays occupied until the vehicle leaves.`, 'info', v.i, v.bay);
      }
      if (v.departT > t) continue;
      const b = L.bays[v.bay];
      const bk = this.buckets[b.edge];
      let clear = true;
      for (const id of bk) if (Math.abs(this.vehicles[id].s - b.accessS) < GAP) { clear = false; break; }
      if (!clear) continue;
      v.state = 'unparking';
      v.edge = b.edge;
      v.s = b.accessS;
      v.man = 0;
      v.pEdge = v.edge;
      v.pS = v.s;
      bk.push(v.i);
      bk.sort((a, c) => this.vehicles[c].s - this.vehicles[a].s);
      minS[b.edge] = Math.min(minS[b.edge], v.s);
    }

    // 6. movement
    this.edgeCount.fill(0);
    for (let e = 0; e < this.buckets.length; e++) {
      const bk = this.buckets[e];
      if (!bk.length) continue;
      let leaderS = Infinity;
      for (const id of bk.slice()) {
        const v = this.vehicles[id];
        if (v.edge !== e || v.mt === t) continue;
        if (v.state === 'parking' || v.state === 'unparking') {
          leaderS = v.s;
          continue;
        }
        v.mt = t;
        this.moveVehicle(v, leaderS, minS);
        leaderS = v.edge === e ? v.s : leaderS;
      }
    }

    // 7. maneuvers
    for (const v of this.vehicles) {
      if (v.state === 'parking') {
        v.man += 1;
        if (v.man >= MANEUVER_S) this.completePark(v);
      } else if (v.state === 'unparking') {
        v.man += 1;
        if (v.man >= MANEUVER_S) this.completeUnpark(v);
      }
    }

    // 8. edge load for congestion scoring
    for (const v of this.vehicles) {
      if (v.edge >= 0 && (v.state === 'driving' || v.state === 'leaving' || v.state === 'parking' || v.state === 'unparking')) {
        const stopped = v.s === v.pS && v.edge === v.pEdge;
        this.edgeCount[v.edge] += stopped ? 1.5 : 1;
      }
    }

    // 9. give up after a long search
    for (const v of this.vehicles) {
      if (v.state === 'driving' && v.gateT >= 0 && v.parkT < 0 && !v.resId && t - v.gateT > GIVE_UP_S) {
        v.gaveUp = true;
        this.toLeaving(v);
        this.log('alert', `${v.code} gave up after ${Math.round(GIVE_UP_S / 60)} minutes of searching and is leaving without parking.`, 'crit', v.i);
      }
    }

    if (t % 60 === 0) {
      this.recordMinute();
      this.updateForecast();
      if (this.opts.live && t % 300 === 0) this.snapshotForecast();
    }
  }

  runTo(tTarget: number) {
    while (this.t < tTarget && this.t < this.tEnd) this.step();
  }

  occupancyShare(): number {
    let n = 0;
    for (let i = 0; i < this.occ.length; i++) {
      const b = this.L.bays[i];
      if (b.flag === 'maintenance') continue;
      if (this.occ[i] >= 0 || this.claim[i] >= 0 || this.hold[i] || b.flag === 'obstructed') n++;
    }
    return n / this.usable;
  }

  private recordMinute() {
    const c = this.counts();
    this.history.push({
      t: this.t,
      occupied: c.occupied,
      usable: c.usable,
      generalFree: c.generalFree,
      searching: this.searchingVehicles().length,
      queue: this.gateQueue.length,
      entries: this.entriesThisMinute
    });
    this.entriesThisMinute = 0;
  }

  updateForecast() {
    const c = this.counts();
    this.forecast = computeForecast(
      {
        scn: this.scn,
        t: this.t,
        occupied: c.occupied + c.reserved,
        usable: c.usable,
        paidPending: this.paidPending(),
        comingETAs: this.comingETAs(),
        offerActive: this.op.offerActive
      },
      this.opts.assumptions
    );
    const fc = this.forecast;
    const entry = { t: this.t, occ: fc.intent.occ.slice(), arr30: fc.arr30.intent, fill: fc.fillMin.intent, peak: Math.max(...fc.intent.occ) / Math.max(1, fc.usable) };
    if (this.forecastLog.length && this.forecastLog[this.forecastLog.length - 1].t === this.t) this.forecastLog[this.forecastLog.length - 1] = entry;
    else this.forecastLog.push(entry);
    if (this.forecastLog.length > 180) this.forecastLog.shift();
    if (this.opts.live && this.forecast.fillMin.intent !== null && !this.pressureAlerted && this.t < this.tWindowEnd) {
      this.pressureAlerted = true;
      const hm = clockLabel(this.scn, this.t + this.forecast.fillMin.intent * 60, false);
      this.log('forecast', `Forecast: occupancy reaches 95% around ${hm} (history + intent). History alone ${this.forecast.fillMin.hist === null ? 'does not expect this within 60 minutes' : 'expects it around ' + clockLabel(this.scn, this.t + this.forecast.fillMin.hist * 60, false)}.`, 'warn');
    }
  }

  private snapshotForecast() {
    const f = this.forecast;
    if (!f) return;
    const k = 29;
    this.snapshots.push({
      madeT: this.t,
      forT: this.t + 1800,
      hist: f.hist.occ[k],
      intent: f.intent.occ[k],
      histLo: f.hist.lo[k],
      histHi: f.hist.hi[k],
      intentLo: f.intent.lo[k],
      intentHi: f.intent.hi[k]
    });
  }

  // ---------- vehicle logic ----------
  private onGate(v: Vehicle) {
    const L = this.L;
    if (v.resId) {
      const r = this.reservations.find((x) => x.id === v.resId);
      if (r && r.status === 'confirmed') {
        r.status = 'checked-in';
        r.checkInT = this.t;
        v.bay = r.bay;
        this.claimRoute(v, L.edges[L.gateEdge].to);
        v.notice = `Reserved ${typeText(r.type)} bay ${L.bays[r.bay].id} is held for you.`;
        this.log('reservation', `${r.id} checked in at the entrance (simulated). ${v.code} is routed to held bay ${L.bays[r.bay].id}.`, 'ok', v.i, r.bay);
        return;
      }
      v.resId = null; // expired or cancelled: treated as an ordinary arrival
    }
    if (this.opts.policy === 'guided') this.guide(v, L.edges[L.gateEdge].to, 'Entrance gate', true);
    else v.route = [];
  }

  private claimRoute(v: Vehicle, fromNode: number) {
    const b = this.L.bays[v.bay];
    const p = shortestPath(this.L, fromNode, this.L.edges[b.edge].from, (e) => (e.kind === 'exit' ? 1e6 : e.len));
    v.route = p ? [...p.edges, b.edge] : [b.edge];
  }

  private guide(v: Vehicle, fromNode: number, fromLabel: string, atGate: boolean) {
    this.dropHeading(v);
    const a = allocate(this.allocContext(), { code: v.code, index: v.i, elig: v.elig, dest: v.dest }, fromNode, fromLabel);
    const prev = v.target;
    v.alloc = a;
    if (this.opts.live) {
      this.decisions.push(a);
      if (this.decisions.length > 300) this.decisions.splice(0, this.decisions.length - 300);
    }
    const c = a.chosen;
    if (!c) {
      v.target = null;
      v.route = [];
      return;
    }
    v.target = { floor: c.floor, zone: c.zone, inv: c.inv };
    const key = `${c.floor}-${c.zone}-${c.inv}`;
    if (!this.heading.has(key)) this.heading.set(key, []);
    (this.heading.get(key) as { v: number; exp: number }[]).push({ v: v.i, exp: this.t + GUIDE_EXPIRY_S });
    v.route = this.zoneRoute(fromNode, c.floor, c.zone);
    if (atGate) {
      v.notice = a.message;
      this.log('guide', `${v.code} entered (${DEST_BY_ID[v.dest].label}) and was guided to ${zoneLabel(c.floor, c.zone, c.inv)}.`, a.mode === 'normal' ? 'info' : 'warn', v.i);
    } else if (fromLabel === 'destination change') {
      v.notice = `Updated route: ${a.message}`;
    } else {
      v.reroutes++;
      if (a.mode !== 'normal') v.relaxed = true;
      v.notice = `Updated route: ${a.message}`;
      const from = prev ? zoneLabel(prev.floor, prev.zone) : 'its zone';
      this.log('reroute', fromLabel === 'capacity change' ? `${v.code} updated route to ${zoneLabel(c.floor, c.zone, c.inv)}: a suitable bay became free there (was ${from}).` : `${v.code} rerouted from ${from} to ${zoneLabel(c.floor, c.zone, c.inv)} because suitable bays there were taken.`, 'warn', v.i);
    }
  }

  private zoneRoute(fromNode: number, floor: number, zone: ZoneId): number[] {
    const L = this.L;
    const w = (e: { kind: string; len: number }) => (e.kind === 'exit' ? 1e6 : e.len);
    const s1 = L.segEdge(floor, 1, zone);
    const s2 = L.segEdge(floor, 2, zone);
    const p1 = shortestPath(L, fromNode, L.edges[s1].from, w);
    const p2 = shortestPath(L, L.edges[s1].to, L.edges[s2].from, w);
    if (!p1 || !p2) return [];
    return [...p1.edges, s1, ...p2.edges, s2];
  }

  private dropHeading(v: Vehicle) {
    if (!v.target) return;
    const key = `${v.target.floor}-${v.target.zone}-${v.target.inv}`;
    const list = this.heading.get(key);
    if (list) {
      const idx = list.findIndex((h) => h.v === v.i);
      if (idx >= 0) list.splice(idx, 1);
    }
  }

  private wants(v: Vehicle, b: Bay): boolean {
    if (!this.isFree(b.idx) && !(v.bay === b.idx && this.hold[b.idx] === v.resId && this.occ[b.idx] < 0 && this.claim[b.idx] < 0)) return false;
    if (v.resId && v.bay >= 0) return v.bay === b.idx;
    if (!v.elig.includes(b.type)) return false;
    if (v.state === 'leaving') return false;
    const searchT = this.t - v.gateT;
    if (this.opts.policy === 'guided') {
      if (v.relaxed || !v.target) return true;
      if (b.floor === v.target.floor && b.zone === v.target.zone) return true;
      // A driver passing a free eligible bay that is at least as convenient as the guided zone takes it.
      const targetWalk = v.alloc && v.alloc.chosen ? v.alloc.chosen.walk : Infinity;
      return b.walk[DEST_BY_ID[v.dest].lift] <= targetWalk + 5;
    }
    const walk = b.walk[DEST_BY_ID[v.dest].lift];
    return walk <= v.threshold || searchT > 180;
  }

  private moveVehicle(v: Vehicle, leaderS: number, minS: Float64Array) {
    const L = this.L;
    let e = L.edges[v.edge];
    const searching = v.state === 'driving' && v.parkT < 0;
    const inTargetZone = !!v.target && e.kind === 'aisle' && e.zone === v.target.zone && L.nodes[e.from].floor === v.target.floor;
    let speed: number;
    if (e.kind === 'aisle') speed = searching && (this.opts.policy === 'unguided' || inTargetZone || v.relaxed || v.resId) ? SPEED.search : SPEED.cruise;
    else speed = SPEED[e.kind] ?? SPEED.road;
    let budget = speed;
    let cap = leaderS - GAP;
    let moved = 0;
    for (let guard = 0; guard < 4 && budget > 1e-6; guard++) {
      const sOld = v.s;
      let sNew = Math.min(v.s + budget, cap, Number.POSITIVE_INFINITY);
      if (sNew < sOld) sNew = sOld;
      // scan for bays passed this tick
      if (searching && e.kind === 'aisle') {
        for (const bi of e.bays) {
          const b = L.bays[bi];
          if (b.accessS < sOld - 1e-6 || b.accessS > sNew) continue;
          if (this.wants(v, b)) {
            moved += b.accessS - sOld;
            v.s = b.accessS;
            this.startPark(v, b);
            if (searching) v.searchDist += moved;
            return;
          }
        }
      }
      if (sNew < e.len) {
        moved += sNew - sOld;
        v.s = sNew;
        break;
      }
      // reached end of edge
      moved += e.len - sOld;
      budget -= e.len - sOld;
      v.s = e.len;
      if (e.kind === 'exit') {
        v.state = 'exited';
        v.exitT = this.t;
        v.edge = -1;
        break;
      }
      this.arriveAtNode(v, e.to);
      if (v.route.length === 0) this.decideAtNode(v, e.to);
      const next = v.route[0];
      if (next === undefined) break;
      const room = minS[next] - GAP;
      if (room <= 0) break; // blocked at the junction
      v.route.shift();
      v.edge = next;
      v.s = 0;
      e = L.edges[next];
      cap = room;
      minS[next] = Math.min(minS[next], 0);
      const fresh = this.buckets[next];
      fresh.push(v.i);
    }
    if (searching) v.searchDist += moved;
  }

  private arriveAtNode(v: Vehicle, node: number) {
    const n = this.L.nodes[node];
    const f = n.floor;
    if (n.name === 'A1d') v.seenA1[f] = true;
    if (n.name === 'A2a') v.seenA2[f] = true;
    if (n.name === 'A2d' || n.name === 'A1a') {
      // entering a floor from a ramp resets what this driver has seen there
      const prevEdge = this.L.edges[v.edge];
      if (prevEdge.kind === 'road' && (this.L.nodes[prevEdge.from].name === 'RDb' || this.L.nodes[prevEdge.from].name === 'RUt')) {
        v.seenA1[f] = false;
        v.seenA2[f] = false;
      }
    }
    v.deepest = Math.max(v.deepest, f);
    if (v.target && v.relaxed === false && this.t - v.gateT > 4 * 60) v.relaxed = true;
  }

  private decideAtNode(v: Vehicle, node: number) {
    const L = this.L;
    const n = L.nodes[node];
    if (n.name === 'OUT') return;
    if (v.state === 'leaving') {
      const p = shortestPath(L, node, L.exitNode);
      v.route = p ? p.edges : [];
      return;
    }
    if (v.resId && v.bay >= 0) {
      this.claimRoute(v, node);
      return;
    }
    if (this.opts.policy === 'guided') {
      const tg = v.target;
      if (tg && v.alloc && (v.alloc.mode === 'expected-departure' || v.alloc.mode === 'none') && this.expectedDepartures(tg.floor, tg.zone, tg.inv) > 0) {
        // Waiting for a known departure: keep circling the same zone instead of crossing floors.
        v.route = this.zoneRoute(node, tg.floor, tg.zone);
        if (v.route.length) return;
      }
      if (v.reroutes >= 1) v.relaxed = true;
      this.guide(v, node, `${FLOOR_NAMES[n.floor]} ${n.name}`, false);
      if (v.route.length) return;
    }
    // Documented unguided search policy (also the guided fallback when no zone is reachable)
    const f = n.floor;
    const edgeTo = (name: string, floor: number) => L.out[node].find((eid) => L.nodes[L.edges[eid].to].name === name && L.nodes[L.edges[eid].to].floor === floor);
    let next: number | undefined;
    if (n.name === 'A1d') {
      if (f < 2 && v.seenA1[f] && v.seenA2[f]) next = edgeTo('RDt', f);
      else next = edgeTo('A2d', f);
    } else if (n.name === 'A2a') {
      if (f > 0 && v.seenA1[f] && v.seenA2[f] && v.deepest === 2) next = edgeTo('RUb', f);
      else next = edgeTo('A1a', f);
    } else {
      const outs = L.out[node].filter((eid) => L.edges[eid].kind !== 'exit' && L.nodes[L.edges[eid].to].name !== 'GOUT');
      next = outs[0];
    }
    v.route = next === undefined ? [] : [next];
  }

  private startPark(v: Vehicle, b: Bay) {
    this.claim[b.idx] = v.i;
    v.bay = b.idx;
    v.state = 'parking';
    v.man = 0;
    v.route = [];
  }

  private completePark(v: Vehicle) {
    const b = this.L.bays[v.bay];
    this.claim[b.idx] = -1;
    this.occ[b.idx] = v.i;
    if (this.hold[b.idx] && this.hold[b.idx] === v.resId) {
      this.hold[b.idx] = null;
      const r = this.reservations.find((x) => x.id === v.resId);
      if (r) { r.status = 'parked'; r.closedT = this.t; }
    }
    v.state = 'parked';
    v.parkT = this.t;
    v.departT = this.t + v.durationS;
    v.paidT = v.departT - (180 + stableUnit(`pay${v.key}`) * 300);
    this.dropHeading(v);
    const secs = this.t - v.gateT;
    v.notice = `Parked in ${b.id}. Walk to Lift ${DEST_BY_ID[v.dest].lift} about ${b.walk[DEST_BY_ID[v.dest].lift]} m.`;
    this.log('park', `${v.code} parked in ${b.id} · ${fmtDur(secs)} gate-to-park · ${Math.round(v.searchDist)} m driven.`, secs > 300 ? 'warn' : 'ok', v.i, b.idx);
  }

  private completeUnpark(v: Vehicle) {
    const b = this.L.bays[v.bay];
    this.occ[b.idx] = -1;
    this.log('depart', `Departure confirmed from ${b.id}. Bay now available.`, 'info', v.i, b.idx);
    v.state = 'leaving';
    v.man = 0;
    const p = shortestPath(this.L, this.L.edges[v.edge].to, this.L.exitNode);
    v.route = p ? p.edges : [];
    if (this.opts.policy === 'guided') this.dispatchFreedBay(b);
  }

  /** Re-evaluate guidance when capacity changes: offer the freed bay's zone to the nearest driver whose zone has filled. */
  private dispatchFreedBay(b: Bay) {
    if (!this.isFree(b.idx)) return;
    const freeInZone = this.L.bays.filter((x) => x.floor === b.floor && x.zone === b.zone && x.type === b.type && this.isFree(x.idx)).length;
    if (this.headingCount(b.floor, b.zone, b.type) >= freeInZone) return;
    let best: Vehicle | null = null;
    let bestD = Infinity;
    for (const v of this.vehicles) {
      if (v.state !== 'driving' || v.gateT < 0 || v.parkT >= 0 || v.resId || !v.elig.includes(b.type) || !v.target) continue;
      const tg = v.target;
      const stillFree = this.L.bays.some((x) => x.floor === tg.floor && x.zone === tg.zone && v.elig.includes(x.type) && this.isFree(x.idx));
      if (stillFree && !(tg.floor === b.floor && tg.zone === b.zone)) continue;
      if (tg.floor === b.floor && tg.zone === b.zone) continue; // already heading there
      const e = this.L.edges[v.edge];
      const p = shortestPath(this.L, e.to, this.L.edges[b.edge].from, (x) => (x.kind === 'exit' ? 1e6 : x.len));
      if (!p) continue;
      const d = e.len - v.s + p.cost + b.accessS;
      if (d < bestD) { bestD = d; best = v; }
    }
    if (best) this.guide(best, this.L.edges[best.edge].to, 'capacity change', false);
  }

  private toLeaving(v: Vehicle) {
    this.dropHeading(v);
    v.state = 'leaving';
    v.target = null;
    const p = shortestPath(this.L, this.L.edges[v.edge].to, this.L.exitNode);
    v.route = p ? p.edges : [];
  }

  // ---------- live interactions ----------
  injectArrivals(n: number, dest: DestId): Vehicle[] {
    const out: Vehicle[] = [];
    for (let k = 0; k < n; k++) {
      const v = this.newVehicle({
        key: `demo-${this.t}-${k}`,
        arrivalT: this.t + 1,
        dest,
        durationS: 90 * 60,
        source: 'demo',
        injected: true,
        threshold: 35
      });
      out.push(v);
      this.pending.push(v.i);
    }
    this.sortPending();
    this.log('operator', `${n} simultaneous demo arrivals added at the entrance, all heading for ${DEST_BY_ID[dest].label}.`, 'info');
    return out;
  }

  // ---------- driver app: the shopper's own car ----------
  /** "I'm on my way" in the driver app: one car with a known destination and ETA joins the pending arrivals
   *  and counts as an intent signal in the forecast. Duration is long; the driver ends the stay by paying. */
  addDriver(p: { dest: DestId; etaS: number; elig: BayType[]; cls: 'ice' | 'ev'; member: boolean }): Vehicle {
    const v = this.newVehicle({
      key: `driver-${this.t}-${this.vehicles.length}`,
      arrivalT: this.t + Math.max(1, Math.round(p.etaS)),
      dest: p.dest,
      elig: p.elig,
      cls: p.cls,
      member: p.member,
      durationS: 6 * 3600,
      coming: true,
      source: 'demo',
      injected: true,
      threshold: 35
    });
    this.pending.push(v.i);
    this.sortPending();
    this.log('guide', `${v.code} pressed "I'm coming" in the driver app: about ${Math.max(1, Math.round(p.etaS / 60))} min away, heading for ${DEST_BY_ID[p.dest].label}.`, 'info', v.i);
    return v;
  }

  /** Move a pending driver's arrival (ETA changed, or "I'm at the entrance"). */
  setDriverArrival(vid: number, etaS: number) {
    const v = this.vehicles[vid];
    if (!v || v.state !== 'pending') return;
    v.arrivalT = this.t + Math.max(1, Math.round(etaS));
    if (!this.pending.includes(v.i)) this.pending.push(v.i);
    this.sortPending();
  }

  /** Pay in the app: the bay shows as leaving soon and the car departs after the walk back. */
  driverPay(vid: number, walkBackS = 150): boolean {
    const v = this.vehicles[vid];
    if (!v || v.state !== 'parked') return false;
    v.paidT = this.t + 1;
    v.departT = this.t + 1 + walkBackS;
    v.durationS = 0;
    return true;
  }

  /** Cancel a trip that has not reached the entrance. */
  cancelDriver(vid: number): boolean {
    const v = this.vehicles[vid];
    if (!v || v.state !== 'pending') return false;
    v.state = 'cancelled';
    this.pending = this.pending.filter((id) => id !== vid);
    this.log('guide', `${v.code} cancelled the trip in the driver app.`, 'info', v.i);
    return true;
  }

  bookable(type: 'ev' | 'family' | 'member'): { total: number; outOfService: number; occupied: number; held: number; free: number; buffer: number; bookable: number } {
    const bays = this.L.bays.filter((b) => b.type === type && b.flag !== 'maintenance');
    const outOfService = bays.filter((b) => b.charger === 'out').length;
    let occupied = 0;
    let held = 0;
    let free = 0;
    for (const b of bays) {
      if (this.occ[b.idx] >= 0 || this.claim[b.idx] >= 0) occupied++;
      else if (this.hold[b.idx]) held++;
      else if (b.charger !== 'out') free++;
    }
    const buffer = 1; // protected walk-in buffer: never book the last free bay of a type
    return { total: bays.length, outOfService, occupied, held, free, buffer, bookable: Math.max(0, free - buffer) };
  }

  createReservation(type: 'ev' | 'family' | 'member', startInMin: number, durationMin: number): { ok: true; r: Reservation } | { ok: false; error: string } {
    const q = this.bookable(type);
    if (q.bookable < 1) return { ok: false, error: `No ${typeText(type)} bay can be guaranteed: ${q.free} free, ${q.buffer} kept for walk-in eligible drivers. Overbooking is disabled.` };
    const bay = this.L.bays.find((b) => b.type === type && this.isFree(b.idx) && b.charger !== 'out');
    if (!bay) return { ok: false, error: 'No suitable bay is free.' };
    const n = this.reservations.filter((r) => r.userCreated).length + 1;
    const r: Reservation = {
      id: `R-9${n}`,
      type,
      bay: bay.idx,
      windowStart: this.t + startInMin * 60,
      windowEnd: this.t + (startInMin + 15) * 60,
      grace: 600,
      durationS: durationMin * 60,
      status: 'confirmed',
      createdT: this.t,
      vehicle: -1,
      checkInT: -1,
      closedT: -1,
      userCreated: true
    };
    this.hold[bay.idx] = r.id;
    this.reservations.push(r);
    const v = this.newVehicle({
      key: `user-${r.id}`,
      arrivalT: r.windowStart + 180,
      dest: type === 'family' ? 'family' : 'atrium',
      cls: type === 'ev' ? 'ev' : 'ice',
      elig: ['general', type],
      member: type === 'member',
      durationS: r.durationS,
      resId: r.id,
      coming: true,
      source: 'demo',
      injected: true
    });
    r.vehicle = v.i;
    this.pending.push(v.i);
    this.sortPending();
    this.log('reservation', `${r.id} booked: ${typeText(type)} bay ${bay.id} held, arrival window ${clockLabel(this.scn, r.windowStart, false)}–${clockLabel(this.scn, r.windowEnd, false)}, grace 10 min.`, 'ok', undefined, bay.idx);
    return { ok: true, r };
  }

  checkInNow(id: string): string {
    const r = this.reservations.find((x) => x.id === id);
    if (!r || r.status !== 'confirmed') return 'This reservation can no longer be checked in.';
    let v = r.vehicle >= 0 ? this.vehicles[r.vehicle] : null;
    if (!v) {
      v = this.newVehicle({ key: `walkup-${r.id}`, dest: 'atrium', elig: ['general', r.type], cls: r.type === 'ev' ? 'ev' : 'ice', member: r.type === 'member', durationS: r.durationS, resId: r.id, source: 'demo', injected: true });
      r.vehicle = v.i;
    }
    if (v.state !== 'pending') return 'The driver is already on site.';
    v.arrivalT = this.t + 1;
    if (!this.pending.includes(v.i)) this.pending.push(v.i);
    this.sortPending();
    return `${r.id}: driver sent to the entrance; check-in happens at the gate.`;
  }

  cancelReservation(id: string): string {
    const r = this.reservations.find((x) => x.id === id);
    if (!r || r.status !== 'confirmed') return 'Only confirmed reservations can be cancelled.';
    r.status = 'cancelled';
    r.closedT = this.t;
    if (this.hold[r.bay] === r.id) this.hold[r.bay] = null;
    if (r.vehicle >= 0) {
      const v = this.vehicles[r.vehicle];
      if (v.state === 'pending') v.state = 'cancelled';
    }
    this.log('reservation', `${r.id} cancelled. ${this.L.bays[r.bay].id} released to ${typeText(r.type)} inventory.`, 'info', undefined, r.bay);
    return `${r.id} cancelled and its bay released.`;
  }

  /** Driver changes destination in the app: re-run the allocation from the next junction. */
  changeDestination(vid: number, dest: DestId): string {
    const v = this.vehicles[vid];
    if (!v) return 'Vehicle not found.';
    const was = DEST_BY_ID[v.dest].label;
    v.dest = dest;
    if (v.state === 'driving' && v.parkT < 0 && !v.resId && this.opts.policy === 'guided' && v.edge >= 0) {
      this.guide(v, this.L.edges[v.edge].to, 'destination change', false);
      this.log('guide', `${v.code} changed destination from ${was} to ${DEST_BY_ID[dest].label}; guidance re-evaluated.`, 'info', v.i);
      return `Destination updated and guidance re-evaluated.`;
    }
    this.log('guide', `${v.code} changed destination from ${was} to ${DEST_BY_ID[dest].label}.`, 'info', v.i);
    return 'Destination updated. The walking distance now refers to the new lift.';
  }

  requestAssistance(etaMin: number): AssistanceRequest {
    const req: AssistanceRequest = { id: `AR-${this.assistance.length + 1}`, t: this.t, etaMin, status: 'logged' };
    this.assistance.push(req);
    this.log('operator', `${req.id}: accessible-bay assistance requested for arrival in about ${etaMin} min. Staff verification on arrival (simulated).`, 'info');
    return req;
  }

  // Operator actions (live only; always confirmed in the UI first)
  pauseOffer(response: number) {
    if (!this.scn.offer || !this.op.offerActive) return;
    this.op.offerActive = false;
    this.op.offerPausedT = this.t;
    this.op.offerResponse = response;
    let n = 0;
    for (const v of this.vehicles) {
      if (v.state === 'pending' && v.source === 'offer' && v.arrivalT > this.t + 600 && stableUnit(`off${v.key}`) < response) {
        v.state = 'cancelled';
        n++;
      }
    }
    this.op.offerCancelled = n;
    this.log('operator', `Operator paused "${this.scn.offer.name}". Assumed response ${Math.round(response * 100)}%: ${n} offer-driven trips not yet under way will not come during this period.`, 'info');
    this.updateForecast();
  }

  recommendLaterArrival(response: number) {
    if (this.op.laterApplied) return;
    this.op.laterApplied = true;
    this.op.laterResponse = response;
    let n = 0;
    for (const v of this.vehicles) {
      if (v.state === 'pending' && v.coming && !v.resId && v.arrivalT > this.t + 300 && v.arrivalT < this.t + 2700 && stableUnit(`late${v.key}`) < response) {
        v.arrivalT += 1800;
        n++;
      }
    }
    this.op.laterShifted = n;
    this.sortPending();
    this.log('operator', `Operator sent a later-arrival suggestion to "I'm coming" drivers. Assumed response ${Math.round(response * 100)}%: ${n} trips shift by 30 minutes.`, 'info');
    this.updateForecast();
  }

  guideToFloor(floor: number) {
    this.op.floorBiasApplied = floor;
    this.floorBias = [0, 0, 0];
    this.floorBias[floor] = 0.12;
    this.log('operator', `Operator applied a guidance preference for ${FLOOR_NAMES[floor]}. New allocations add +0.12 to ${FLOOR_NAMES[floor]} zones; eligibility and capacity rules are unchanged.`, 'info');
  }

  clearFloorBias() {
    this.op.floorBiasApplied = -1;
    this.floorBias = [0, 0, 0];
    this.log('operator', 'Operator removed the floor guidance preference.', 'info');
  }

  enableOverflow(response: number) {
    this.op.overflowApplied = true;
    this.op.overflowResponse = response;
    this.log('operator', `Operator enabled the illustrative overflow suggestion for "I'm coming" drivers while occupancy is 97% or higher (assumed response ${Math.round(response * 100)}%).`, 'info');
  }
}

export function fmtDur(secs: number): string {
  if (!isFinite(secs)) return '–';
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return m > 0 ? `${m} min ${String(s).padStart(2, '0')} s` : `${s} s`;
}
