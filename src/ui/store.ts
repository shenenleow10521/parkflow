// Shared application state. Every view reads from this one store and the one live Sim instance.

import { buildLayout, Layout, DestId } from '../core/layout';
import { SCENARIO_BY_ID, ScenarioId } from '../core/scenarios';
import { Sim } from '../core/sim';
import { AllocWeights, DEFAULT_WEIGHTS } from '../core/allocation';
import { ForecastAssumptions, DEFAULT_ASSUMPTIONS } from '../core/forecast';
import { Comparison, runComparison } from '../core/metrics';
import { loadJSON, loadArray, saveJSON } from './dom';

export type Section = 'overview' | 'forecast' | 'allocation' | 'reservations' | 'impact';
export type Selection = { kind: 'vehicle'; id: number } | { kind: 'bay'; id: number } | null;

export interface EmissionSettings {
  factorKgPerKm: number;
  peakPeriodsPerYear: number;
  offPeakPeriodsPerYear: number;
}

export interface FieldObs {
  id: string;
  date: string; // YYYY-MM-DD
  gateEntry: string; // HH:MM:SS
  parked: string; // HH:MM:SS
  zone: string;
  note: string;
}

export interface Layers {
  lights: boolean;
  cctv: boolean;
  route: boolean;
  autoRotate: boolean;
}

export interface DriverPrefs {
  collapsed: boolean;
  autoOpen: boolean;
  dest: DestId;
  ev: boolean;
  family: boolean;
  member: boolean;
}

export const store = {
  L: buildLayout() as Layout,
  scenarioId: 'surge' as ScenarioId,
  sim: null as unknown as Sim,
  playing: true,
  speed: 10,
  section: 'overview' as Section,
  selected: null as Selection,
  rightTab: 'vehicle' as 'vehicle' | 'reasoning' | 'actions',
  floorView: 'all' as 'all' | number,
  planView: false,
  comparison: null as Comparison | null,
  offpeak: null as Comparison | null,
  weights: loadJSON<AllocWeights>('parkflow.weights', { ...DEFAULT_WEIGHTS }),
  assumptions: loadJSON<ForecastAssumptions>('parkflow.assumptions', { ...DEFAULT_ASSUMPTIONS }),
  emission: loadJSON<EmissionSettings>('parkflow.emission', { factorKgPerKm: 0.18, peakPeriodsPerYear: 104, offPeakPeriodsPerYear: 520 }),
  noShowRate: loadJSON<{ v: number }>('parkflow.noshow', { v: 0.15 }).v,
  field: loadArray<FieldObs>('parkflow.field'),
  driver: { collapsed: true, autoOpen: true, dest: 'atrium', ev: false, family: false, member: false } as DriverPrefs,
  eventFilter: 'all' as string,
  layers: loadJSON<Layers>('parkflow.layers', { lights: true, cctv: false, route: true, autoRotate: false }),
  pendingAction: null as string | null,
  demoBurst: [] as number[],
  drafts: {} as Record<string, string>,
  fieldMsg: '' as string,
  resMsg: '' as string,
  comparisonStale: false,
  toast: '' as string,
  toastT: 0
};

type Listener = (topic: string) => void;
const listeners: Listener[] = [];

export function on(fn: Listener) {
  listeners.push(fn);
}

export function emit(topic: string) {
  for (const fn of listeners) fn(topic);
}

export function newSim(): Sim {
  const scn = SCENARIO_BY_ID[store.scenarioId];
  const sim = new Sim(store.L, scn, { policy: 'guided', live: true, weights: store.weights, assumptions: store.assumptions });
  return sim;
}

/** Rebuild the live simulation from the scenario seed. Warm-up gives the opening frame some traffic. */
export function resetSim(warmupS = 480) {
  store.sim = newSim();
  store.sim.runTo(warmupS);
  store.selected = null;
  store.demoBurst = [];
  store.pendingAction = null;
  emit('reset');
}

export function setScenario(id: ScenarioId) {
  store.scenarioId = id;
  if (store.comparison && store.comparison.scenarioId !== id) store.comparison = null;
  resetSim();
}

export function persist() {
  saveJSON('parkflow.weights', store.weights);
  saveJSON('parkflow.assumptions', store.assumptions);
  saveJSON('parkflow.emission', store.emission);
  saveJSON('parkflow.noshow', { v: store.noShowRate });
  saveJSON('parkflow.field', store.field);
  saveJSON('parkflow.layers', store.layers);
}

export function runMatchedComparison(): Comparison {
  const scn = SCENARIO_BY_ID[store.scenarioId];
  store.comparison = runComparison(store.L, scn, store.weights, store.assumptions);
  if (!store.offpeak || store.offpeak.scenarioId !== 'normal') {
    store.offpeak = store.scenarioId === 'normal' ? store.comparison : runComparison(store.L, SCENARIO_BY_ID.normal, store.weights, store.assumptions);
  }
  emit('comparison');
  return store.comparison;
}

export function toast(msg: string) {
  store.toast = msg;
  store.toastT = performance.now();
  emit('toast');
}
