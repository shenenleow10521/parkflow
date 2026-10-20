// Matched comparison runs and outcome metrics. Both runs replay identical demand, durations,
// eligibility mix, initial occupancy and seed. Marketing interventions are off in both.

import { Layout } from './layout';
import { ScenarioDef, generateDemand } from './scenarios';
import { Sim, Policy } from './sim';
import { AllocWeights } from './allocation';
import { ForecastAssumptions } from './forecast';
import { mean, percentile } from './rng';

export interface RunSummary {
  policy: Policy;
  scheduled: number;
  admitted: number;
  parked: number;
  stillSearching: number;
  gaveUp: number;
  diverted: number;
  notAdmitted: number;
  meanG2P: number;
  medianG2P: number;
  p90G2P: number; // all admitted vehicles; unresolved counted at their elapsed search time (lower bound)
  meanSearchDist: number; // parked vehicles
  totalSearchDist: number; // all admitted vehicles, metres
  iceSearchDist: number; // combustion vehicles only, metres
  iceShare: number;
  peakQueue: number;
  meanGateWait: number;
  g2p: number[];
  occupancy: number[]; // per minute occupancy share
  searchingSeries: number[];
}

export interface Comparison {
  scenarioId: string;
  scenarioName: string;
  baseline: RunSummary;
  guided: RunSummary;
  computedAt: number;
  seed: number;
}

function summarise(sim: Sim, policy: Policy): RunSummary {
  const sched = sim.vehicles.filter((v) => !v.initial && !v.injected);
  const admitted = sched.filter((v) => v.gateT >= 0);
  const parked = admitted.filter((v) => v.parkT >= 0);
  const stillSearching = admitted.filter((v) => v.parkT < 0 && !v.gaveUp && (v.state === 'driving' || v.state === 'parking')).length;
  const gaveUp = admitted.filter((v) => v.gaveUp).length;
  const notAdmitted = sched.filter((v) => v.state === 'queued').length;
  const diverted = sched.filter((v) => v.state === 'diverted').length;
  const g2p = parked.map((v) => v.parkT - v.gateT);
  const censored = admitted.map((v) => (v.parkT >= 0 ? v.parkT - v.gateT : (v.gaveUp ? 1200 : sim.t - v.gateT)));
  const ice = admitted.filter((v) => v.cls === 'ice');
  const waits = admitted.map((v) => v.gateT - v.queueT);
  return {
    policy,
    scheduled: sched.filter((v) => v.state !== 'cancelled').length,
    admitted: admitted.length,
    parked: parked.length,
    stillSearching,
    gaveUp,
    diverted,
    notAdmitted,
    meanG2P: mean(g2p),
    medianG2P: percentile(g2p, 0.5),
    p90G2P: percentile(censored, 0.9),
    meanSearchDist: mean(parked.map((v) => v.searchDist)),
    totalSearchDist: admitted.reduce((a, v) => a + v.searchDist, 0),
    iceSearchDist: ice.reduce((a, v) => a + v.searchDist, 0),
    iceShare: admitted.length ? ice.length / admitted.length : 0,
    peakQueue: sim.peakQueue,
    meanGateWait: mean(waits),
    g2p,
    occupancy: sim.history.map((h) => h.occupied / h.usable),
    searchingSeries: sim.history.map((h) => h.searching)
  };
}

export function runComparison(L: Layout, scn: ScenarioDef, weights: AllocWeights, assumptions: ForecastAssumptions): Comparison {
  const demand = generateDemand(scn, L);
  const clone = () => JSON.parse(JSON.stringify(demand));
  const base = new Sim(L, scn, { policy: 'unguided', live: false, weights, assumptions }, clone());
  base.runTo(base.tEnd);
  const guided = new Sim(L, scn, { policy: 'guided', live: false, weights, assumptions }, clone());
  guided.runTo(guided.tEnd);
  return {
    scenarioId: scn.id,
    scenarioName: scn.name,
    baseline: summarise(base, 'unguided'),
    guided: summarise(guided, 'guided'),
    computedAt: Date.now(),
    seed: scn.seed
  };
}

export function pctChange(before: number, after: number): number {
  if (!isFinite(before) || !isFinite(after) || before === 0) return NaN;
  return ((after - before) / before) * 100;
}
