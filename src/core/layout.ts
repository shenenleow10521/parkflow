// Illustrative three-level car park layout (not the real KL East Mall plan).
// World units are metres. x runs along the building, z across it, floors are stacked below ground.

import { hash01 } from './rng';

export type ZoneId = 'A' | 'B' | 'C';
export type BayType = 'general' | 'ev' | 'oku' | 'family' | 'member';
export type DestId = 'cinema' | 'grocer' | 'atrium' | 'family';

export const FLOOR_NAMES = ['B1', 'B2', 'B3'];
export const FLOORS = [0, 1, 2];
export const ZONES: ZoneId[] = ['A', 'B', 'C'];
export const ZONE_COUNTS: Record<ZoneId, number> = { A: 7, B: 6, C: 7 };
export const ZONE_X0: Record<ZoneId, number> = { A: 8, B: 29.2, C: 47.8 };
export const BAY_W = 2.6;
export const BAY_D = 5;
export const ROW_Z = [2.5, 13.5, 29.5];
export const ROW_AISLE = [1, 1, 2];
export const A1_Z = 8;
export const A2_Z = 24;
export const LIFT_X: Record<ZoneId, number> = { A: 17.1, B: 37, C: 56.9 };
export const LIFT_Z = 18.5;
export const SEG_X = [3, 27.7, 46.3, 70];
export const SLAB = { x0: 0, x1: 74, z0: 0, z1: 32 };
export const REAL_FLOOR_HEIGHT = 3.2;

export const DESTINATIONS: { id: DestId; label: string; lift: ZoneId }[] = [
  { id: 'cinema', label: 'Cinema', lift: 'C' },
  { id: 'grocer', label: 'Supermarket', lift: 'A' },
  { id: 'atrium', label: 'Main atrium', lift: 'B' },
  { id: 'family', label: 'Ice rink & family', lift: 'A' }
];
export const DEST_BY_ID: Record<DestId, { id: DestId; label: string; lift: ZoneId }> = {
  cinema: DESTINATIONS[0],
  grocer: DESTINATIONS[1],
  atrium: DESTINATIONS[2],
  family: DESTINATIONS[3]
};

export const BAY_TYPE_LABEL: Record<BayType, string> = {
  general: 'General',
  ev: 'EV charging',
  oku: 'Accessible (OKU)',
  family: 'Family',
  member: 'Designated member'
};

/** Lower-case form for running text that keeps acronyms (EV, OKU) intact. */
export function typeText(t: BayType): string {
  return ({ general: 'general', ev: 'EV charging', oku: 'accessible (OKU)', family: 'family', member: 'designated member' } as Record<BayType, string>)[t];
}

export interface GNode {
  id: number;
  name: string;
  floor: number;
  x: number;
  z: number;
}

export type EdgeKind = 'aisle' | 'connector' | 'ramp' | 'road' | 'gate' | 'approach' | 'exit';

export interface GEdge {
  id: number;
  from: number;
  to: number;
  name: string;
  kind: EdgeKind;
  len: number;
  floor: number; // floor of the start node
  zone?: ZoneId;
  aisle?: 1 | 2;
  bays: number[]; // bay indices with access on this edge, sorted by accessS
}

export interface Bay {
  idx: number;
  id: string;
  floor: number;
  zone: ZoneId;
  row: number;
  col: number;
  x: number;
  z: number;
  type: BayType;
  edge: number;
  accessS: number;
  walk: Record<ZoneId, number>;
  flag: 'none' | 'maintenance' | 'obstructed';
  confidence: number;
  charger: 'ok' | 'out' | null;
}

export interface Layout {
  nodes: GNode[];
  edges: GEdge[];
  out: number[][]; // outgoing edge ids per node
  bays: Bay[];
  node: (name: string, floor: number) => number;
  segEdge: (floor: number, aisle: 1 | 2, zone: ZoneId) => number;
  gateEdge: number;
  approachEdge: number;
  exitNode: number;
  entryNode: number;
}

function specialType(floor: number, zone: ZoneId, row: number, col: number): BayType {
  if (floor === 0) {
    if (row === 1 && ((zone === 'A' && col === 3) || (zone === 'B' && (col === 2 || col === 3)) || (zone === 'C' && col === 3))) return 'oku';
    if (zone === 'A' && row === 0 && col >= 2 && col <= 4) return 'family';
    if (zone === 'C' && row === 2 && col >= 2 && col <= 4) return 'member';
  }
  if (floor === 1) {
    if (zone === 'A' && row === 1 && col >= 2 && col <= 4) return 'family';
    if (zone === 'C' && row === 1 && col >= 2 && col <= 4) return 'member';
    if (zone === 'B' && row === 2 && col >= 1 && col <= 4) return 'ev';
  }
  if (floor === 2) {
    if (zone === 'B' && row === 1 && (col === 2 || col === 3)) return 'ev';
  }
  return 'general';
}

function bayFlag(floor: number, zone: ZoneId, row: number, col: number): Bay['flag'] {
  if (floor === 2 && zone === 'C' && row === 0 && (col === 5 || col === 6)) return 'maintenance';
  if (floor === 1 && zone === 'A' && row === 2 && col === 0) return 'obstructed';
  if (floor === 0 && zone === 'B' && row === 0 && col === 5) return 'obstructed';
  return 'none';
}

export function buildLayout(): Layout {
  const nodes: GNode[] = [];
  const edges: GEdge[] = [];
  const index = new Map<string, number>();
  const addNode = (name: string, floor: number, x: number, z: number) => {
    const id = nodes.length;
    nodes.push({ id, name, floor, x, z });
    index.set(`${name}@${floor}`, id);
    return id;
  };
  const node = (name: string, floor: number) => {
    const id = index.get(`${name}@${floor}`);
    if (id === undefined) throw new Error(`Missing node ${name}@${floor}`);
    return id;
  };
  const addEdge = (from: number, to: number, kind: EdgeKind, name: string, extra: Partial<GEdge> = {}) => {
    const a = nodes[from];
    const b = nodes[to];
    const horiz = Math.hypot(b.x - a.x, b.z - a.z);
    const dh = (b.floor - a.floor) * REAL_FLOOR_HEIGHT;
    const len = Math.hypot(horiz, dh);
    const e: GEdge = { id: edges.length, from, to, kind, name, len, floor: a.floor, bays: [], ...extra };
    edges.push(e);
    return e.id;
  };

  for (const f of FLOORS) {
    addNode('A1a', f, SEG_X[0], A1_Z);
    addNode('A1b', f, SEG_X[1], A1_Z);
    addNode('A1c', f, SEG_X[2], A1_Z);
    addNode('A1d', f, SEG_X[3], A1_Z);
    addNode('A2d', f, SEG_X[3], A2_Z);
    addNode('A2c', f, SEG_X[2], A2_Z);
    addNode('A2b', f, SEG_X[1], A2_Z);
    addNode('A2a', f, SEG_X[0], A2_Z);
    if (f < 2) {
      addNode('RDt', f, 78, A1_Z);
      addNode('RUt', f, -4, A1_Z);
    }
    if (f > 0) {
      addNode('RDb', f, 78, A2_Z);
      addNode('RUb', f, -4, A2_Z);
    }
  }
  addNode('IN', 0, -24, A1_Z);
  addNode('GIN', 0, -12, A1_Z);
  addNode('GOUT', 0, -12, A2_Z);
  addNode('OUT', 0, -24, A2_Z);

  const segIds: Record<string, number> = {};
  for (const f of FLOORS) {
    const fl = FLOOR_NAMES[f];
    const a1 = ['A1a', 'A1b', 'A1c', 'A1d'];
    for (let k = 0; k < 3; k++) {
      segIds[`${f}-1-${ZONES[k]}`] = addEdge(node(a1[k], f), node(a1[k + 1], f), 'aisle', `${fl} aisle 1 · Zone ${ZONES[k]}`, { zone: ZONES[k], aisle: 1 });
    }
    addEdge(node('A1d', f), node('A2d', f), 'connector', `${fl} east connector`);
    const a2 = ['A2d', 'A2c', 'A2b', 'A2a'];
    const a2z: ZoneId[] = ['C', 'B', 'A'];
    for (let k = 0; k < 3; k++) {
      segIds[`${f}-2-${a2z[k]}`] = addEdge(node(a2[k], f), node(a2[k + 1], f), 'aisle', `${fl} aisle 2 · Zone ${a2z[k]}`, { zone: a2z[k], aisle: 2 });
    }
    addEdge(node('A2a', f), node('A1a', f), 'connector', `${fl} west connector`);
  }
  for (const f of [0, 1]) {
    const lo = FLOOR_NAMES[f + 1];
    const hi = FLOOR_NAMES[f];
    addEdge(node('A1d', f), node('RDt', f), 'road', `${hi} to down ramp`);
    addEdge(node('RDt', f), node('RDb', f + 1), 'ramp', `Ramp ${hi} → ${lo}`);
    addEdge(node('RDb', f + 1), node('A2d', f + 1), 'road', `${lo} ramp exit`);
    addEdge(node('A2a', f + 1), node('RUb', f + 1), 'road', `${lo} to up ramp`);
    addEdge(node('RUb', f + 1), node('RUt', f), 'ramp', `Ramp ${lo} → ${hi}`);
    addEdge(node('RUt', f), node('A1a', f), 'road', `${hi} ramp merge`);
  }
  const approachEdge = addEdge(node('IN', 0), node('GIN', 0), 'approach', 'Entrance approach');
  const gateEdge = addEdge(node('GIN', 0), node('RUt', 0), 'gate', 'Entrance gate');
  addEdge(node('A2a', 0), node('GOUT', 0), 'road', 'B1 to exit');
  addEdge(node('GOUT', 0), node('OUT', 0), 'exit', 'Exit gate');

  const out: number[][] = nodes.map(() => []);
  for (const e of edges) out[e.from].push(e.id);

  // Bays
  const bays: Bay[] = [];
  for (const f of FLOORS) {
    for (const zone of ZONES) {
      let num = 1;
      for (let row = 0; row < 3; row++) {
        for (let col = 0; col < ZONE_COUNTS[zone]; col++) {
          const x = ZONE_X0[zone] + BAY_W * col + BAY_W / 2;
          const z = ROW_Z[row];
          const aisle = ROW_AISLE[row] as 1 | 2;
          const edge = segIds[`${f}-${aisle}-${zone}`];
          const e = edges[edge];
          const sx = nodes[e.from].x;
          const accessS = aisle === 1 ? x - sx : sx - x;
          const id = `${FLOOR_NAMES[f]}-${zone}-${String(num).padStart(2, '0')}`;
          num++;
          const walk = {} as Record<ZoneId, number>;
          for (const L of ZONES) walk[L] = Math.round(Math.abs(x - LIFT_X[L]) + Math.abs(z - LIFT_Z));
          const type = specialType(f, zone, row, col);
          const flag = bayFlag(f, zone, row, col);
          const h = hash01(id);
          const confidence = flag === 'obstructed' ? 0.42 + h * 0.12 : flag === 'maintenance' ? 1 : 0.93 + h * 0.06;
          const charger = type === 'ev' ? (f === 2 && col === 3 ? 'out' : 'ok') : null;
          const bay: Bay = { idx: bays.length, id, floor: f, zone, row, col, x, z, type, edge, accessS, walk, flag, confidence, charger };
          bays.push(bay);
          e.bays.push(bay.idx);
        }
      }
    }
  }
  for (const e of edges) e.bays.sort((a, b) => bays[a].accessS - bays[b].accessS);

  return {
    nodes,
    edges,
    out,
    bays,
    node,
    segEdge: (floor, aisle, zone) => segIds[`${floor}-${aisle}-${zone}`],
    gateEdge,
    approachEdge,
    exitNode: node('OUT', 0),
    entryNode: node('RUt', 0)
  };
}

/** Dijkstra shortest path returning edge ids. weight(edge) defaults to length. */
export function shortestPath(L: Layout, from: number, to: number, weight?: (e: GEdge) => number): { edges: number[]; cost: number } | null {
  if (from === to) return { edges: [], cost: 0 };
  const n = L.nodes.length;
  const dist = new Float64Array(n).fill(Infinity);
  const prevEdge = new Int32Array(n).fill(-1);
  const done = new Uint8Array(n);
  dist[from] = 0;
  for (;;) {
    let u = -1;
    let best = Infinity;
    for (let i = 0; i < n; i++) if (!done[i] && dist[i] < best) { best = dist[i]; u = i; }
    if (u < 0) break;
    if (u === to) break;
    done[u] = 1;
    for (const eid of L.out[u]) {
      const e = L.edges[eid];
      const w = weight ? weight(e) : e.len;
      if (dist[u] + w < dist[e.to]) {
        dist[e.to] = dist[u] + w;
        prevEdge[e.to] = eid;
      }
    }
  }
  if (!isFinite(dist[to])) return null;
  const path: number[] = [];
  let cur = to;
  while (cur !== from) {
    const eid = prevEdge[cur];
    path.push(eid);
    cur = L.edges[eid].from;
  }
  path.reverse();
  return { edges: path, cost: dist[to] };
}

export function zoneKey(floor: number, zone: ZoneId): string {
  return `${FLOOR_NAMES[floor]}·${zone}`;
}
