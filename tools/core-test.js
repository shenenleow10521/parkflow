// Headless checks for the simulation core (appended inside the bundle IIFE).
const L = buildLayout();
console.log('nodes', L.nodes.length, 'edges', L.edges.length, 'bays', L.bays.length);
const types = {};
for (const b of L.bays) types[b.type] = (types[b.type] || 0) + 1;
console.log('bay types', JSON.stringify(types));
// graph connectivity: every node reaches OUT, entry reaches every aisle
for (const n of L.nodes) {
  if (n.name === 'IN' || n.name === 'OUT') continue;
  if (!shortestPath(L, n.id, L.exitNode)) console.log('NO EXIT FROM', n.name, n.floor);
}
for (const e of L.edges.filter((e) => e.kind === 'aisle')) {
  if (!shortestPath(L, L.entryNode, e.from)) console.log('UNREACHABLE', e.name);
}

function invariants(sim, label) {
  const seen = new Map();
  for (const v of sim.vehicles) {
    if (v.state === 'parked') {
      if (seen.has(v.bay)) throw new Error(label + ' two vehicles in bay ' + v.bay);
      seen.set(v.bay, v.i);
      if (sim.occ[v.bay] !== v.i) throw new Error(label + ' occ mismatch');
      const b = L.bays[v.bay];
      if (!v.elig.includes(b.type) && !v.initial) throw new Error(label + ' ineligible bay ' + b.id + ' ' + v.code + ' ' + v.elig);
      if (b.type === 'oku' && !v.elig.includes('oku')) throw new Error(label + ' OKU violation');
    }
  }
  for (let i = 0; i < sim.occ.length; i++) {
    if (sim.occ[i] >= 0 && sim.hold[i]) throw new Error(label + ' held and occupied ' + i);
  }
  const c = sim.counts();
  if (c.occupied > c.usable || c.generalFree < 0) throw new Error(label + ' capacity');
}

const w = DEFAULT_WEIGHTS;
const a = DEFAULT_ASSUMPTIONS;
for (const scn of SCENARIOS) {
  const t0 = Date.now();
  const sim = new Sim(L, scn, { policy: 'guided', live: true, weights: w, assumptions: a });
  for (let k = 0; k < sim.tEnd; k += 60) { sim.runTo(k + 60); invariants(sim, scn.id + '@' + k); }
  const ms = Date.now() - t0;
  const c = sim.counts();
  const res = sim.reservations.map((r) => r.id + ':' + r.status).join(' ');
  const maxOcc = Math.max(...sim.history.map((h) => h.occupied / h.usable));
  const maxSearch = Math.max(...sim.history.map((h) => h.searching));
  console.log(`[live ${scn.id}] ${ms}ms vehicles=${sim.vehicles.length} events=${sim.events.length} decisions=${sim.decisions.length} maxOcc=${(maxOcc*100).toFixed(0)}% maxSearching=${maxSearch} peakQ=${sim.peakQueue} res=${res}`);
  const t1 = Date.now();
  const cmp = runComparison(L, scn, w, a);
  const B = cmp.baseline, G = cmp.guided;
  const f = (x) => (isFinite(x) ? x.toFixed(0) : '-');
  console.log(`  cmp ${Date.now() - t1}ms | base: adm=${B.admitted} park=${B.parked} search=${B.stillSearching} gave=${B.gaveUp} notAdm=${B.notAdmitted} meanG2P=${f(B.meanG2P)} p90=${f(B.p90G2P)} dist=${f(B.meanSearchDist)} peakQ=${B.peakQueue}`);
  console.log(`              | guid: adm=${G.admitted} park=${G.parked} search=${G.stillSearching} gave=${G.gaveUp} notAdm=${G.notAdmitted} meanG2P=${f(G.meanG2P)} p90=${f(G.p90G2P)} dist=${f(G.meanSearchDist)} peakQ=${G.peakQueue}`);
}
// determinism
const s1 = new Sim(L, SCENARIOS[1], { policy: 'guided', live: true, weights: w, assumptions: a }); s1.runTo(1800);
const s2 = new Sim(L, SCENARIOS[1], { policy: 'guided', live: true, weights: w, assumptions: a }); s2.runTo(1800);
console.log('deterministic', JSON.stringify(s1.counts()) === JSON.stringify(s2.counts()) && s1.events.length === s2.events.length);
const sample = s1.decisions.slice(-3).map((d) => d.explanation);
console.log(sample.join('\n'));
