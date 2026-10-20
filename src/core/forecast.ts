// Demand forecasting. Both forecasts share one information cutoff (the current simulated time)
// and never read realised future arrivals. Intent signals are synthetic and labelled as such.

import { ScenarioDef } from './scenarios';
import { ZoneId, DEST_BY_ID, DestId } from './layout';

export interface ForecastAssumptions {
  cinemaCarShare: number;
  cinemaParty: number;
  cinemaLeadMin: number;
  diningCarShare: number;
  diningParty: number;
  eventCarShare: number;
  eventParty: number;
  offerCarShare: number;
  overlapCinemaDining: number;
  comingOverlap: number;
  meanDwellMin: number;
  histBand: number;
  intentBand: number;
}

export const DEFAULT_ASSUMPTIONS: ForecastAssumptions = {
  cinemaCarShare: 0.55,
  cinemaParty: 2.4,
  cinemaLeadMin: 30,
  diningCarShare: 0.6,
  diningParty: 2.6,
  eventCarShare: 0.5,
  eventParty: 3.0,
  offerCarShare: 0.85,
  overlapCinemaDining: 0.15,
  comingOverlap: 0.7,
  meanDwellMin: 150,
  histBand: 0.25,
  intentBand: 0.15
};

export const ASSUMPTION_META: { key: keyof ForecastAssumptions; label: string; min: number; max: number; step: number; unit?: string; pct?: boolean }[] = [
  { key: 'cinemaCarShare', label: 'Cinema ticket holders arriving by car', min: 0.2, max: 0.9, step: 0.05, pct: true },
  { key: 'cinemaParty', label: 'Cinema party size per car', min: 1, max: 4, step: 0.1, unit: 'people' },
  { key: 'cinemaLeadMin', label: 'Cinema arrival peak before showtime', min: 10, max: 60, step: 5, unit: 'min' },
  { key: 'diningCarShare', label: 'Dining guests arriving by car', min: 0.2, max: 0.9, step: 0.05, pct: true },
  { key: 'diningParty', label: 'Dining party size per car', min: 1, max: 5, step: 0.1, unit: 'people' },
  { key: 'eventCarShare', label: 'Event visitors arriving by car', min: 0.2, max: 0.9, step: 0.05, pct: true },
  { key: 'eventParty', label: 'Event party size per car', min: 1, max: 5, step: 0.1, unit: 'people' },
  { key: 'offerCarShare', label: 'Offer redemptions that arrive by car', min: 0.3, max: 1, step: 0.05, pct: true },
  { key: 'overlapCinemaDining', label: 'Overlap: cinema guests also booked for dining', min: 0, max: 0.6, step: 0.05, pct: true },
  { key: 'comingOverlap', label: "Overlap: 'I'm coming' drivers already in the history baseline", min: 0, max: 1, step: 0.05, pct: true },
  { key: 'meanDwellMin', label: 'Mean parking duration (for departures)', min: 45, max: 200, step: 5, unit: 'min' },
  { key: 'histBand', label: 'Assumed range: history forecast', min: 0.05, max: 0.5, step: 0.05, pct: true },
  { key: 'intentBand', label: 'Assumed range: history + intent forecast', min: 0.05, max: 0.5, step: 0.05, pct: true }
];

export interface ForecastInput {
  scn: ScenarioDef;
  t: number;
  occupied: number;
  usable: number;
  paidPending: number;
  comingETAs: number[]; // absolute sim seconds of known "I'm coming" ETAs
  offerActive: boolean;
}

export interface ForecastSeries {
  arrivals: number[];
  /** Expected cars leaving a bay each minute: paid cars first, then the dwell-time hazard. */
  departures: number[];
  occ: number[];
  lo: number[];
  hi: number[];
}

export type IntentComponent = 'history' | 'member' | 'cinema' | 'dining' | 'event' | 'offer' | 'coming';

export interface Forecast {
  t: number;
  horizon: number;
  usable: number;
  hist: ForecastSeries;
  intent: ForecastSeries;
  components: Record<IntentComponent, number[]>;
  arr30: { hist: number; intent: number };
  fillMin: { hist: number | null; intent: number | null };
}

function triF(m: number, peak: number, half: number): number {
  const d = Math.abs(m - peak);
  return d >= half ? 0 : (half - d) / (half * half);
}

export function historyRate(s: ScenarioDef, cm: number): number {
  const rel = cm - s.startMin;
  return Math.max(0.2, s.routinePerMin + (s.routineSlope * rel) / 60) * s.historyFactor;
}

export function intentRates(s: ScenarioDef, cm: number, a: ForecastAssumptions, offerActive: boolean) {
  const history = historyRate(s, cm);
  const member = history * (s.memberIndexSignal - 1);
  let cinema = 0;
  if (s.cinema) {
    const overlap = s.dining ? a.overlapCinemaDining : 0;
    cinema = ((s.cinema.tickets * a.cinemaCarShare) / a.cinemaParty) * (1 - overlap) * triF(cm, s.cinema.showtimeMin - a.cinemaLeadMin, 24);
  }
  let dining = 0;
  if (s.dining) for (const slot of s.dining.slots) dining += ((slot.covers * a.diningCarShare) / a.diningParty) * triF(cm, slot.min - 8, 16);
  let event = 0;
  if (s.event) event = ((s.event.expectedVisitors * a.eventCarShare) / a.eventParty) * triF(cm, s.event.startMin - 30, 26);
  let offer = 0;
  if (s.offer && offerActive) offer = (s.offer.redeemPerHour / 60) * a.offerCarShare;
  return { history, member, cinema, dining, event, offer };
}

function projectFull(arr: number[], input: ForecastInput, a: ForecastAssumptions): { occ: number[]; dep: number[] } {
  const occ: number[] = [];
  const dep: number[] = [];
  let o = input.occupied;
  let paid = input.paidPending;
  for (let k = 0; k < arr.length; k++) {
    const paidOut = k < 6 ? paid / (6 - k) : 0;
    paid -= paidOut;
    const pool = Math.max(0, o - paid - paidOut);
    const d = paidOut + pool / a.meanDwellMin;
    o = Math.min(input.usable, Math.max(0, o + arr[k] - d));
    occ.push(o);
    dep.push(d);
  }
  return { occ, dep };
}

function project(arr: number[], input: ForecastInput, a: ForecastAssumptions): number[] {
  return projectFull(arr, input, a).occ;
}

export function computeForecast(input: ForecastInput, a: ForecastAssumptions, horizon = 60): Forecast {
  const s = input.scn;
  const startCm = s.startMin + input.t / 60;
  const comp: Record<IntentComponent, number[]> = { history: [], member: [], cinema: [], dining: [], event: [], offer: [], coming: [] };
  const histArr: number[] = [];
  const intArr: number[] = [];
  for (let k = 0; k < horizon; k++) {
    const cm = startCm + k + 0.5;
    const r = intentRates(s, cm, a, input.offerActive);
    const lo = input.t + k * 60;
    const hi = lo + 60;
    const coming = input.comingETAs.filter((e) => e >= lo && e < hi).length * (1 - a.comingOverlap);
    comp.history.push(r.history);
    comp.member.push(r.member);
    comp.cinema.push(r.cinema);
    comp.dining.push(r.dining);
    comp.event.push(r.event);
    comp.offer.push(r.offer);
    comp.coming.push(coming);
    histArr.push(r.history);
    intArr.push(r.history + r.member + r.cinema + r.dining + r.event + r.offer + coming);
  }
  const scale = (arr: number[], f: number) => arr.map((x) => x * f);
  const hp = projectFull(histArr, input, a);
  const ip = projectFull(intArr, input, a);
  const hist: ForecastSeries = {
    arrivals: histArr,
    departures: hp.dep,
    occ: hp.occ,
    lo: project(scale(histArr, 1 - a.histBand), input, a),
    hi: project(scale(histArr, 1 + a.histBand), input, a)
  };
  const intent: ForecastSeries = {
    arrivals: intArr,
    departures: ip.dep,
    occ: ip.occ,
    lo: project(scale(intArr, 1 - a.intentBand), input, a),
    hi: project(scale(intArr, 1 + a.intentBand), input, a)
  };
  const sum30 = (arr: number[]) => arr.slice(0, 30).reduce((x, y) => x + y, 0);
  const fill = (occ: number[]) => {
    const idx = occ.findIndex((o) => o / input.usable >= 0.95);
    return idx < 0 ? null : idx + 1;
  };
  return {
    t: input.t,
    horizon,
    usable: input.usable,
    hist,
    intent,
    components: comp,
    arr30: { hist: sum30(histArr), intent: sum30(intArr) },
    fillMin: { hist: fill(hist.occ), intent: fill(intent.occ) }
  };
}

/** Expected arrivals over the next 30 minutes heading for each lift, from the intent forecast. */
export function forecastByLift(f: Forecast | null, destMix: Record<DestId, number>): Record<ZoneId, number> {
  const out: Record<ZoneId, number> = { A: 0, B: 0, C: 0 };
  if (!f) return out;
  const total = f.arr30.intent;
  const cinemaShare = f.components.cinema.slice(0, 30).reduce((a, b) => a + b, 0) / Math.max(1e-6, total);
  for (const id of Object.keys(destMix) as DestId[]) {
    out[DEST_BY_ID[id].lift] += total * (1 - cinemaShare) * destMix[id];
  }
  out.C += total * cinemaShare;
  return out;
}
