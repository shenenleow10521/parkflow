// Scenario definitions and deterministic demand generation.
// All inputs here are synthetic and illustrative. "Truth" parameters drive the simulated arrivals;
// the forecast never reads them directly and relies on its own editable assumptions instead.

import { Rng, hash01 } from './rng';
import { Layout, BayType, DestId, DESTINATIONS } from './layout';

export type Source = 'routine' | 'cinema' | 'dining' | 'event' | 'offer';
export type ScenarioId = 'normal' | 'surge' | 'cinema' | 'noshow' | 'pressure';

export interface ReservationDef {
  id: string;
  type: 'ev' | 'family' | 'member';
  windowStartMin: number; // minutes after scenario start
  windowLenMin: number;
  durationMin: number;
  noShow: boolean;
  arriveOffsetMin: number; // arrival relative to window start (if not a no-show)
}

export interface ScenarioDef {
  id: ScenarioId;
  name: string;
  summary: string;
  day: string;
  startMin: number; // clock minutes since midnight (MYT)
  windowMin: number;
  drainMin: number;
  seed: number;
  initialOcc: number;
  routinePerMin: number;
  routineSlope: number; // change in rate per hour
  historyFactor: number; // how the typical-day history compares with today's routine demand
  memberIndexTrue: number; // today's opted-in member visits vs typical (truth)
  memberIndexSignal: number; // what the aggregated member pattern reports
  destMix: Record<DestId, number>;
  cinema?: { showtimeMin: number; tickets: number; trueCarShare: number; trueParty: number };
  dining?: { slots: { min: number; covers: number }[]; trueCarShare: number; trueParty: number };
  event?: { name: string; startMin: number; expectedVisitors: number; trueCarShare: number; trueParty: number; lift: DestId };
  offer?: { name: string; outstanding: number; redeemPerHour: number; trueCarShare: number };
  reservations: ReservationDef[];
  comingShare: number; // share of arrivals who tapped "I'm coming"
}

export const SCENARIOS: ScenarioDef[] = [
  {
    id: 'normal',
    name: 'Normal afternoon',
    summary: 'Moderate weekday demand with spare capacity on every level.',
    day: 'Tue',
    startMin: 14 * 60,
    windowMin: 90,
    drainMin: 30,
    seed: 1101,
    initialOcc: 0.52,
    routinePerMin: 1.0,
    routineSlope: 0.1,
    historyFactor: 1.0,
    memberIndexTrue: 1.0,
    memberIndexSignal: 1.0,
    destMix: { cinema: 0.15, grocer: 0.35, atrium: 0.35, family: 0.15 },
    offer: { name: 'Weekday 2 free hours after 2 pm', outstanding: 180, redeemPerHour: 14, trueCarShare: 0.9 },
    reservations: [
      { id: 'R-11', type: 'ev', windowStartMin: 15, windowLenMin: 15, durationMin: 90, noShow: false, arriveOffsetMin: 4 },
      { id: 'R-12', type: 'family', windowStartMin: 30, windowLenMin: 15, durationMin: 120, noShow: false, arriveOffsetMin: 6 }
    ],
    comingShare: 0.2
  },
  {
    id: 'surge',
    name: 'Weekend surge',
    summary: 'A Saturday arrival wave for an ice show crowds the levels nearest Lifts A and B.',
    day: 'Sat',
    startMin: 14 * 60,
    windowMin: 90,
    drainMin: 30,
    seed: 2207,
    initialOcc: 0.6,
    routinePerMin: 0.68,
    routineSlope: 0.15,
    historyFactor: 1.0,
    memberIndexTrue: 1.08,
    memberIndexSignal: 1.07,
    destMix: { cinema: 0.12, grocer: 0.18, atrium: 0.38, family: 0.32 },
    event: { name: 'Ice show (15:00)', startMin: 15 * 60, expectedVisitors: 280, trueCarShare: 0.52, trueParty: 3.1, lift: 'family' },
    offer: { name: 'Weekend dining: 2 hours free parking', outstanding: 240, redeemPerHour: 12, trueCarShare: 0.9 },
    reservations: [
      { id: 'R-01', type: 'member', windowStartMin: 5, windowLenMin: 15, durationMin: 120, noShow: false, arriveOffsetMin: 3 },
      { id: 'R-02', type: 'ev', windowStartMin: 15, windowLenMin: 15, durationMin: 90, noShow: true, arriveOffsetMin: 0 },
      { id: 'R-03', type: 'family', windowStartMin: 20, windowLenMin: 15, durationMin: 150, noShow: false, arriveOffsetMin: 7 },
      { id: 'R-04', type: 'ev', windowStartMin: 30, windowLenMin: 15, durationMin: 75, noShow: false, arriveOffsetMin: 2 }
    ],
    comingShare: 0.24
  },
  {
    id: 'cinema',
    name: 'Cinema arrival wave',
    summary: 'A sold-out 19:45 screening and dinner bookings build demand that history alone misses.',
    day: 'Sat',
    startMin: 18 * 60 + 30,
    windowMin: 90,
    drainMin: 30,
    seed: 3313,
    initialOcc: 0.55,
    routinePerMin: 0.55,
    routineSlope: -0.1,
    historyFactor: 1.02,
    memberIndexTrue: 1.03,
    memberIndexSignal: 1.04,
    destMix: { cinema: 0.2, grocer: 0.1, atrium: 0.45, family: 0.25 },
    cinema: { showtimeMin: 19 * 60 + 45, tickets: 300, trueCarShare: 0.5, trueParty: 2.3 },
    dining: { slots: [{ min: 19 * 60, covers: 70 }, { min: 19 * 60 + 30, covers: 60 }], trueCarShare: 0.55, trueParty: 2.7 },
    reservations: [
      { id: 'R-21', type: 'member', windowStartMin: 25, windowLenMin: 15, durationMin: 180, noShow: false, arriveOffsetMin: 5 },
      { id: 'R-22', type: 'ev', windowStartMin: 40, windowLenMin: 15, durationMin: 120, noShow: false, arriveOffsetMin: 4 }
    ],
    comingShare: 0.24
  },
  {
    id: 'noshow',
    name: 'Reservation no-show',
    summary: 'Two special-bay reservations expire after their grace period and return to their own inventory.',
    day: 'Tue',
    startMin: 11 * 60,
    windowMin: 90,
    drainMin: 30,
    seed: 4421,
    initialOcc: 0.58,
    routinePerMin: 1.0,
    routineSlope: 0.25,
    historyFactor: 1.0,
    memberIndexTrue: 1.0,
    memberIndexSignal: 1.0,
    destMix: { cinema: 0.08, grocer: 0.4, atrium: 0.37, family: 0.15 },
    reservations: [
      { id: 'R-31', type: 'ev', windowStartMin: 5, windowLenMin: 15, durationMin: 60, noShow: true, arriveOffsetMin: 0 },
      { id: 'R-32', type: 'family', windowStartMin: 10, windowLenMin: 15, durationMin: 90, noShow: false, arriveOffsetMin: 5 },
      { id: 'R-33', type: 'member', windowStartMin: 20, windowLenMin: 15, durationMin: 120, noShow: true, arriveOffsetMin: 0 },
      { id: 'R-34', type: 'ev', windowStartMin: 35, windowLenMin: 15, durationMin: 90, noShow: false, arriveOffsetMin: 3 }
    ],
    comingShare: 0.2
  },
  {
    id: 'pressure',
    name: 'Capacity pressure',
    summary: 'A busy Saturday with few suitable bays left; the system recommends alternatives.',
    day: 'Sat',
    startMin: 15 * 60,
    windowMin: 90,
    drainMin: 30,
    seed: 5531,
    initialOcc: 0.89,
    routinePerMin: 0.65,
    routineSlope: 0.0,
    historyFactor: 0.97,
    memberIndexTrue: 1.06,
    memberIndexSignal: 1.05,
    destMix: { cinema: 0.15, grocer: 0.2, atrium: 0.4, family: 0.25 },
    event: { name: 'Weekend market (15:30)', startMin: 15 * 60 + 30, expectedVisitors: 240, trueCarShare: 0.5, trueParty: 2.8, lift: 'atrium' },
    offer: { name: 'Weekend dining: 2 hours free parking', outstanding: 260, redeemPerHour: 20, trueCarShare: 0.9 },
    reservations: [
      { id: 'R-41', type: 'member', windowStartMin: 10, windowLenMin: 15, durationMin: 120, noShow: false, arriveOffsetMin: 4 },
      { id: 'R-42', type: 'ev', windowStartMin: 25, windowLenMin: 15, durationMin: 90, noShow: true, arriveOffsetMin: 0 }
    ],
    comingShare: 0.26
  }
];

export const SCENARIO_BY_ID: Record<ScenarioId, ScenarioDef> = Object.fromEntries(SCENARIOS.map((s) => [s.id, s])) as Record<ScenarioId, ScenarioDef>;

export interface ArrivalSpec {
  key: string;
  arrivalT: number; // seconds after scenario start
  dest: DestId;
  cls: 'ice' | 'ev';
  elig: BayType[];
  member: boolean;
  source: Source;
  durationS: number;
  threshold: number; // walking distance an unguided driver accepts (m)
  coming: boolean;
  etaNoiseS: number;
  resId: string | null;
}

export interface InitialSpec {
  bay: number;
  remainingS: number;
  cls: 'ice' | 'ev';
  elig: BayType[];
  member: boolean;
  dest: DestId;
}

export interface Demand {
  arrivals: ArrivalSpec[];
  initial: InitialSpec[];
}

/** Triangular weight helper: share of a wave arriving in minute m. */
function tri(m: number, peak: number, half: number): number {
  const d = Math.abs(m - peak);
  return d >= half ? 0 : (half - d) / (half * half);
}

/** True (hidden) arrival rate per minute by source, at clock minute cm. Used only to generate demand. */
export function trueRates(s: ScenarioDef, cm: number): Record<Source, number> {
  const rel = cm - s.startMin;
  const routine = Math.max(0.2, s.routinePerMin + (s.routineSlope * rel) / 60) * s.memberIndexTrue;
  let cinema = 0;
  if (s.cinema) cinema = ((s.cinema.tickets * s.cinema.trueCarShare) / s.cinema.trueParty) * tri(cm, s.cinema.showtimeMin - 28, 24);
  let dining = 0;
  if (s.dining) for (const slot of s.dining.slots) dining += ((slot.covers * s.dining.trueCarShare) / s.dining.trueParty) * tri(cm, slot.min - 8, 16);
  let event = 0;
  if (s.event) event = ((s.event.expectedVisitors * s.event.trueCarShare) / s.event.trueParty) * tri(cm, s.event.startMin - 30, 26);
  let offer = 0;
  if (s.offer) offer = (s.offer.redeemPerHour / 60) * s.offer.trueCarShare;
  return { routine, cinema, dining, event, offer };
}

const DEST_IDS = DESTINATIONS.map((d) => d.id);

function durationFor(rng: Rng, dest: DestId): number {
  const base = { cinema: 165, grocer: 45, atrium: 95, family: 125 }[dest];
  const sd = { cinema: 20, grocer: 15, atrium: 35, family: 30 }[dest];
  return Math.max(15, rng.normal(base, sd)) * 60;
}

function eligibility(rng: Rng, dest: DestId): { cls: 'ice' | 'ev'; elig: BayType[]; member: boolean } {
  const cls: 'ice' | 'ev' = rng.chance(0.12) ? 'ev' : 'ice';
  const elig: BayType[] = ['general'];
  if (cls === 'ev') elig.push('ev');
  if (rng.chance(0.03)) elig.push('oku');
  if (rng.chance(dest === 'family' ? 0.14 : 0.04)) elig.push('family');
  const member = rng.chance(0.16);
  if (member) elig.push('member');
  return { cls, elig, member };
}

export function generateDemand(s: ScenarioDef, L: Layout): Demand {
  const rng = new Rng(s.seed);
  const arrivals: ArrivalSpec[] = [];
  const endMin = s.startMin + s.windowMin;
  const sources: Source[] = ['routine', 'cinema', 'dining', 'event', 'offer'];
  // Arrivals are generated second by second as a Poisson process for each source.
  for (let t = 0; t < s.windowMin * 60; t++) {
    const cm = s.startMin + t / 60;
    if (cm >= endMin) break;
    const r = trueRates(s, cm);
    for (const src of sources) {
      const p = r[src] / 60;
      if (p > 0 && rng.chance(p)) {
        let dest: DestId;
        if (src === 'cinema') dest = 'cinema';
        else if (src === 'dining') dest = rng.chance(0.7) ? 'atrium' : 'cinema';
        else if (src === 'event' && s.event) dest = s.event.lift;
        else dest = rng.pick(DEST_IDS, DEST_IDS.map((d) => s.destMix[d]));
        const e = eligibility(rng, dest);
        arrivals.push({
          key: `a${arrivals.length}`,
          arrivalT: t,
          dest,
          cls: e.cls,
          elig: e.elig,
          member: e.member,
          source: src,
          durationS: durationFor(rng, dest),
          threshold: rng.range(22, 46),
          coming: rng.chance(s.comingShare),
          etaNoiseS: rng.range(-240, 240),
          resId: null
        });
      }
    }
  }
  // Reservation holders who show up
  for (const r of s.reservations) {
    if (r.noShow) continue;
    const elig: BayType[] = ['general', r.type];
    arrivals.push({
      key: `res-${r.id}`,
      arrivalT: (r.windowStartMin + r.arriveOffsetMin) * 60,
      dest: r.type === 'family' ? 'family' : r.type === 'member' ? 'atrium' : 'grocer',
      cls: r.type === 'ev' ? 'ev' : 'ice',
      elig,
      member: r.type === 'member',
      source: 'routine',
      durationS: r.durationMin * 60,
      threshold: 40,
      coming: true,
      etaNoiseS: 60,
      resId: r.id
    });
  }
  arrivals.sort((a, b) => a.arrivalT - b.arrivalT || a.key.localeCompare(b.key));

  // Initial occupancy. Reservation bays are chosen later from the remaining free bays of each type.
  const initial: InitialSpec[] = [];
  const occRng = new Rng(s.seed * 7 + 3);
  for (const bay of L.bays) {
    if (bay.flag === 'maintenance') continue;
    if (bay.flag === 'obstructed') {
      initial.push({ bay: bay.idx, remainingS: 6 * 3600, cls: 'ice', elig: ['general'], member: false, dest: 'atrium' });
      continue;
    }
    let p = s.initialOcc;
    if (bay.type === 'oku') p = Math.min(0.75, s.initialOcc);
    if (bay.type !== 'general' && bay.type !== 'oku') p = s.initialOcc * 0.8;
    // Bays nearest the lifts on B1 fill first in reality
    if (bay.floor === 0) p = Math.min(0.97, p + 0.1);
    if (bay.floor === 2) p = Math.max(0.05, p - 0.12);
    if (!occRng.chance(p)) continue;
    const dest = occRng.pick(DEST_IDS, DEST_IDS.map((d) => s.destMix[d]));
    const elig: BayType[] = ['general'];
    if (bay.type !== 'general') elig.push(bay.type);
    initial.push({
      bay: bay.idx,
      remainingS: occRng.range(4, 170) * 60,
      cls: bay.type === 'ev' || occRng.chance(0.1) ? 'ev' : 'ice',
      elig,
      member: bay.type === 'member',
      dest
    });
  }
  return { arrivals, initial };
}

export function clockLabel(s: ScenarioDef, t: number, withDay = true): string {
  const total = s.startMin * 60 + Math.floor(t);
  const h = Math.floor(total / 3600) % 24;
  const m = Math.floor((total % 3600) / 60);
  const hm = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  return withDay ? `${s.day} ${hm}` : hm;
}

export function clockFromMin(cm: number): string {
  const h = Math.floor(cm / 60) % 24;
  const m = Math.floor(cm % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function stableUnit(key: string): number {
  return hash01(key);
}
