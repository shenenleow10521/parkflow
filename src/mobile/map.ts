// Live top-down map of one car-park level for the driver app (SVG, metres as user units).
// Static geometry is built once per floor; bays, cars, the driver's own car and the route update in place.

import { Sim, Vehicle, VState, MANEUVER_S } from '../core/sim';
import { Layout, BAY_W, A1_Z, A2_Z, SEG_X, LIFT_X, LIFT_Z, ZONE_X0, ZONE_COUNTS, ZONES, ZoneId, SLAB } from '../core/layout';
import { animate, reducedMotion } from './motion';

const NS = 'http://www.w3.org/2000/svg';
const VIEW = { x: -9, z: -3.4, w: 92, h: 40 };

function el<K extends keyof SVGElementTagNameMap>(tag: K, attrs: Record<string, string | number> = {}, parent?: Element): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, tag);
  for (const k of Object.keys(attrs)) e.setAttribute(k, String(attrs[k]));
  if (parent) parent.appendChild(e);
  return e;
}

export interface Pose {
  x: number;
  z: number;
  a: number;
  floor: number;
}

export function edgePose(L: Layout, edgeId: number, s: number): Pose {
  const e = L.edges[edgeId];
  const a = L.nodes[e.from];
  const b = L.nodes[e.to];
  const k = Math.max(0, Math.min(1, s / e.len));
  return { x: a.x + (b.x - a.x) * k, z: a.z + (b.z - a.z) * k, a: Math.atan2(b.z - a.z, b.x - a.x), floor: k < 0.5 ? a.floor : b.floor };
}

function placeAt(sim: Sim, v: Vehicle, state: VState, edge: number, s: number, man: number): Pose | null {
  const L = sim.L;
  if (state === 'parked' && v.bay >= 0) {
    const b = L.bays[v.bay];
    return { x: b.x, z: b.z, a: b.row === 0 ? -Math.PI / 2 : Math.PI / 2, floor: b.floor };
  }
  if ((state === 'parking' || state === 'unparking') && v.bay >= 0) {
    const b = L.bays[v.bay];
    const az = b.row < 2 ? A1_Z : A2_Z;
    let k = Math.min(1, man / MANEUVER_S);
    if (state === 'unparking') k = 1 - k;
    const into = b.row === 0 ? -Math.PI / 2 : Math.PI / 2;
    const along = b.row < 2 ? 0 : Math.PI;
    return { x: b.x, z: az + (b.z - az) * k, a: along + (into - along) * Math.min(1, k * 2), floor: b.floor };
  }
  if (state === 'queued') {
    const e = L.edges[L.approachEdge];
    return edgePose(L, L.approachEdge, e.len - 1 - Math.max(0, sim.gateQueue.indexOf(v.i)) * 7);
  }
  if (edge < 0) return null;
  return edgePose(L, edge, s);
}

/** Interpolated pose between the previous and current simulation tick. */
export function vehiclePose(sim: Sim, v: Vehicle, alpha: number): Pose | null {
  const cur = placeAt(sim, v, v.state, v.edge, v.s, v.man);
  if (!cur || alpha >= 1 || v.pState === 'pending') return cur;
  const prev = placeAt(sim, v, v.pState, v.pEdge, v.pS, v.pMan);
  if (!prev || prev.floor !== cur.floor || Math.hypot(prev.x - cur.x, prev.z - cur.z) > 9) return cur;
  let da = cur.a - prev.a;
  while (da > Math.PI) da -= 2 * Math.PI;
  while (da < -Math.PI) da += 2 * Math.PI;
  return { x: prev.x + (cur.x - prev.x) * alpha, z: prev.z + (cur.z - prev.z) * alpha, a: prev.a + da * Math.min(1, alpha * 1.6), floor: cur.floor };
}

/** Walking path from a bay to its nearest lift lobby, along the walkway beside the bay row. */
export function walkPath(L: Layout, bayIdx: number, lift: ZoneId): number[][] {
  const b = L.bays[bayIdx];
  const wz = b.row === 0 ? 5.4 : b.row === 1 ? 16.6 : 26.6;
  return [
    [b.x, b.z],
    [b.x, wz],
    [LIFT_X[lift], wz],
    [LIFT_X[lift], LIFT_Z]
  ];
}

export interface MapState {
  floor: number;
  me: Vehicle | null;
  route: boolean;
  zone: { floor: number; zone: ZoneId } | null;
  walk: { bay: number; lift: ZoneId } | null;
  alpha: number;
  /** World points the camera should keep in view; null shows the whole level. */
  focus: number[][] | null;
}

const DEG = 180 / Math.PI;

export class FloorMap {
  readonly svg: SVGSVGElement;
  private floor = -1;
  private gStatic: SVGGElement;
  private gZone: SVGGElement;
  private gBays: SVGGElement;
  private gRoute: SVGGElement;
  private gCars: SVGGElement;
  private gMe: SVGGElement;
  private bayRects = new Map<number, SVGRectElement>();
  private bayCars = new Map<number, SVGRectElement>();
  private bayState = new Map<number, string>();
  private carPool: SVGRectElement[] = [];
  private routePath: SVGPathElement;
  private routeGlow: SVGPathElement;
  private walkLine: SVGPolylineElement;
  private zoneRects: SVGRectElement[] = [];
  private routeKey = '';
  private zoneKey = '';
  private cam = { x: VIEW.x, z: VIEW.z, w: VIEW.w, h: VIEW.h };
  private camT = 0;
  private camSnap = true;

  constructor(host: HTMLElement, label: string) {
    this.svg = el('svg', { viewBox: `${VIEW.x} ${VIEW.z} ${VIEW.w} ${VIEW.h}`, class: 'fmap', role: 'img', 'aria-label': label });
    this.gStatic = el('g', {}, this.svg);
    this.gZone = el('g', { class: 'm-zone' }, this.svg);
    this.gBays = el('g', {}, this.svg);
    this.gRoute = el('g', {}, this.svg);
    this.gCars = el('g', {}, this.svg);
    this.gMe = el('g', { class: 'm-me', visibility: 'hidden' }, this.svg);
    el('circle', { r: 4.2, class: 'm-me-halo' }, this.gMe);
    el('circle', { r: 2.1, class: 'm-me-dot' }, this.gMe);
    el('path', { d: 'M 2.9 0 L -0.9 -1.5 L -0.2 0 L -0.9 1.5 Z', class: 'm-me-arrow' }, this.gMe);
    this.routeGlow = el('path', { class: 'm-route-glow', d: '' }, this.gRoute);
    this.routePath = el('path', { class: 'm-route', d: '' }, this.gRoute);
    this.walkLine = el('polyline', { class: 'm-walk', points: '' }, this.gRoute);
    for (let i = 0; i < 2; i++) this.zoneRects.push(el('rect', { class: 'm-zone-r', rx: 0.8, visibility: 'hidden' }, this.gZone));
    host.appendChild(this.svg);
  }

  private buildFloor(sim: Sim, f: number) {
    const L = sim.L;
    this.floor = f;
    this.gStatic.textContent = '';
    this.gBays.textContent = '';
    this.bayRects.clear();
    this.bayCars.clear();
    this.bayState.clear();
    const g = this.gStatic;
    // side roads: entrance and exit on B1, ramps elsewhere
    if (f === 0) {
      el('rect', { x: -9, y: A1_Z - 2.8, width: 12, height: 5.6, class: 'm-road' }, g);
      el('rect', { x: -9, y: A2_Z - 2.8, width: 12, height: 5.6, class: 'm-road' }, g);
      el('text', { x: -8.2, y: A1_Z - 3.6, class: 'm-t m-t-l' }, g).textContent = 'Entrance';
      el('text', { x: -8.2, y: A2_Z + 5.4, class: 'm-t m-t-l' }, g).textContent = 'Exit';
      this.chev(g, -5, A1_Z, 0);
      this.chev(g, -3, A2_Z, Math.PI);
    } else {
      el('rect', { x: -7.5, y: A1_Z - 2.8, width: 7.5, height: A2_Z - A1_Z + 5.6, rx: 1, class: 'm-ramp' }, g);
      el('text', { x: -3.75, y: (A1_Z + A2_Z) / 2 + 0.8, class: 'm-t m-t-c m-t-ramp' }, g).textContent = 'Up';
    }
    el('rect', { x: 74, y: A1_Z - 2.8, width: 7.5, height: A2_Z - A1_Z + 5.6, rx: 1, class: 'm-ramp' }, g);
    el('text', { x: 77.75, y: (A1_Z + A2_Z) / 2 + 0.8, class: 'm-t m-t-c m-t-ramp' }, g).textContent = f < 2 ? 'Down' : 'Ramp';
    // deck and the one-way lane loop
    el('rect', { x: SLAB.x0, y: SLAB.z0, width: SLAB.x1 - SLAB.x0, height: SLAB.z1 - SLAB.z0, rx: 1.2, class: 'm-slab' }, g);
    const loop = `M ${SEG_X[0]} ${A1_Z} H ${SEG_X[3]} V ${A2_Z} H ${SEG_X[0]} Z`;
    el('path', { d: loop, class: 'm-lane' }, g);
    el('path', { d: loop, class: 'm-lane-mark' }, g);
    if (f < 2) el('rect', { x: 70, y: A1_Z - 2.8, width: 6, height: 5.6, class: 'm-lane-fill' }, g);
    if (f > 0) el('rect', { x: 70, y: A2_Z - 2.8, width: 6, height: 5.6, class: 'm-lane-fill' }, g);
    el('rect', { x: -2, y: A1_Z - 2.8, width: 6, height: 5.6, class: 'm-lane-fill' }, g);
    el('rect', { x: -2, y: A2_Z - 2.8, width: 6, height: 5.6, class: 'm-lane-fill' }, g);
    for (const x of [14, 36, 58]) this.chev(g, x, A1_Z, 0);
    for (const x of [24, 46, 64]) this.chev(g, x, A2_Z, Math.PI);
    this.chev(g, SEG_X[3], 16, Math.PI / 2);
    this.chev(g, SEG_X[0], 16, -Math.PI / 2);
    // zone colour bands (the painted pillar bands in the building)
    for (const z of ZONES) {
      const x0 = ZONE_X0[z] - 0.2;
      const w = ZONE_COUNTS[z] * BAY_W + 0.4;
      el('rect', { x: x0, y: -2.4, width: w, height: 1, rx: 0.5, class: `m-band m-band-${z.toLowerCase()}` }, g);
      el('text', { x: x0 + w / 2, y: 34.6, class: 'm-t m-t-c m-t-zone' }, g).textContent = `Zone ${z}`;
    }
    // lift lobbies
    for (const z of ZONES) {
      el('rect', { x: LIFT_X[z] - 2.3, y: LIFT_Z - 1.7, width: 4.6, height: 3.4, rx: 0.7, class: 'm-lift' }, g);
      el('text', { x: LIFT_X[z], y: LIFT_Z + 0.85, class: 'm-t m-t-c m-t-lift' }, g).textContent = z;
    }
    // bays with a parked-car silhouette layer
    for (const b of L.bays) {
      if (b.floor !== f) continue;
      const r = el('rect', { x: b.x - BAY_W / 2 + 0.12, y: b.z - 2.42, width: BAY_W - 0.24, height: 4.84, rx: 0.25, class: 'm-bay' }, this.gBays);
      this.bayRects.set(b.idx, r);
      if (b.type !== 'general') {
        const ze = b.row === 0 ? b.z + 1.95 : b.z - 2.37;
        el('rect', { x: b.x - BAY_W / 2 + 0.3, y: ze, width: BAY_W - 0.6, height: 0.42, class: `m-type m-type-${b.type}` }, this.gBays);
      }
      const c = el('rect', { x: b.x - 0.95, y: b.z - 2.05, width: 1.9, height: 4.1, rx: 0.55, class: 'm-pcar', visibility: 'hidden' }, this.gBays);
      this.bayCars.set(b.idx, c);
    }
    this.routeKey = '';
    this.camSnap = true;
  }

  /** Frame the focus points (with margin) at the element's aspect ratio, easing toward the target. */
  private updateCamera(focus: number[][] | null) {
    const box = this.svg.getBoundingClientRect();
    const aspect = box.width > 10 && box.height > 10 ? box.width / box.height : VIEW.w / VIEW.h;
    let cx: number, cz: number, w: number, h: number;
    if (focus && focus.length) {
      let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
      for (const p of focus) {
        x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1]);
      }
      w = Math.max(x1 - x0 + 14, 42);
      h = Math.max(z1 - z0 + 12, 24);
      cx = (x0 + x1) / 2;
      cz = (z0 + z1) / 2;
    } else {
      w = VIEW.w;
      h = VIEW.h;
      cx = VIEW.x + VIEW.w / 2;
      cz = VIEW.z + VIEW.h / 2;
    }
    if (w / h < aspect) w = h * aspect;
    else h = w / aspect;
    // keep the frame on the map where it can
    if (w < VIEW.w) cx = Math.min(VIEW.x + VIEW.w - w / 2, Math.max(VIEW.x + w / 2, cx));
    else cx = VIEW.x + VIEW.w / 2;
    if (h < VIEW.h) cz = Math.min(VIEW.z + VIEW.h - h / 2, Math.max(VIEW.z + h / 2, cz));
    else cz = VIEW.z + VIEW.h / 2;
    const tgt = { x: cx - w / 2, z: cz - h / 2, w, h };
    const now = performance.now();
    const dt = this.camT ? Math.min(0.1, (now - this.camT) / 1000) : 1;
    this.camT = now;
    const k = this.camSnap || reducedMotion() ? 1 : 1 - Math.exp(-dt * 4.5);
    this.camSnap = false;
    const c = this.cam;
    c.x += (tgt.x - c.x) * k;
    c.z += (tgt.z - c.z) * k;
    c.w += (tgt.w - c.w) * k;
    c.h += (tgt.h - c.h) * k;
    this.svg.setAttribute('viewBox', `${c.x.toFixed(2)} ${c.z.toFixed(2)} ${c.w.toFixed(2)} ${c.h.toFixed(2)}`);
  }

  private chev(g: Element, x: number, z: number, a: number) {
    el('path', { d: 'M -0.9 -1 L 0.5 0 L -0.9 1', class: 'm-chev', transform: `translate(${x} ${z}) rotate(${a * DEG})` }, g);
  }

  update(sim: Sim, st: MapState) {
    if (st.floor !== this.floor) this.buildFloor(sim, st.floor);
    const L = sim.L;
    const f = this.floor;
    const mineBay = st.me && st.me.bay >= 0 ? st.me.bay : -1;
    // bay status
    for (const [idx, r] of this.bayRects) {
      const s = sim.bayStatus(idx);
      const occupiedBy = sim.occ[idx];
      const key = `${s}|${idx === mineBay ? 1 : 0}|${occupiedBy >= 0 ? 1 : 0}`;
      if (this.bayState.get(idx) === key) continue;
      this.bayState.set(idx, key);
      r.setAttribute('class', `m-bay m-${s}${idx === mineBay ? ' m-mine' : ''}`);
      const c = this.bayCars.get(idx);
      if (c) c.setAttribute('visibility', occupiedBy >= 0 && sim.vehicles[occupiedBy].state === 'parked' && sim.vehicles[occupiedBy] !== st.me ? 'visible' : 'hidden');
    }
    // target zone highlight
    const zk = st.zone && st.zone.floor === f ? `${st.zone.zone}` : '';
    if (zk !== this.zoneKey) {
      this.zoneKey = zk;
      if (zk) {
        const z = zk as ZoneId;
        const x0 = ZONE_X0[z] - 0.5;
        const w = ZONE_COUNTS[z] * BAY_W + 1;
        const boxes = [
          [x0, -0.4, w, 16.8],
          [x0, 26.6, w, 5.8]
        ];
        boxes.forEach((bx, i) => {
          const r = this.zoneRects[i];
          r.setAttribute('x', String(bx[0]));
          r.setAttribute('y', String(bx[1]));
          r.setAttribute('width', String(bx[2]));
          r.setAttribute('height', String(bx[3]));
          r.setAttribute('visibility', 'visible');
          animate(r, { opacity: [0, 1] }, { duration: 0.45 });
        });
      } else for (const r of this.zoneRects) r.setAttribute('visibility', 'hidden');
    }
    // moving cars on this floor (others), pooled
    let n = 0;
    for (const v of sim.vehicles) {
      if (v === st.me) continue;
      if (v.state !== 'driving' && v.state !== 'leaving' && v.state !== 'parking' && v.state !== 'unparking' && v.state !== 'queued') continue;
      const p = vehiclePose(sim, v, st.alpha);
      if (!p || p.floor !== f) continue;
      let r = this.carPool[n];
      if (!r) {
        r = el('rect', { x: -2.1, y: -0.95, width: 4.2, height: 1.9, rx: 0.55, class: 'm-car' }, this.gCars);
        this.carPool.push(r);
      }
      r.setAttribute('transform', `translate(${p.x.toFixed(2)} ${p.z.toFixed(2)}) rotate(${(p.a * DEG).toFixed(1)})`);
      r.setAttribute('visibility', 'visible');
      n++;
    }
    for (let i = n; i < this.carPool.length; i++) this.carPool[i].setAttribute('visibility', 'hidden');
    this.updateCamera(st.focus);
    // the driver's own car
    const me = st.me;
    const mp = me ? vehiclePose(sim, me, st.alpha) : null;
    if (mp && mp.floor === f && me && me.state !== 'exited') {
      this.gMe.setAttribute('visibility', 'visible');
      this.gMe.setAttribute('transform', `translate(${mp.x.toFixed(2)} ${mp.z.toFixed(2)}) rotate(${(mp.a * DEG).toFixed(1)})`);
    } else this.gMe.setAttribute('visibility', 'hidden');
    // route ahead
    let d = '';
    if (st.route && me && mp && (me.state === 'driving' || me.state === 'queued') && me.parkT < 0) {
      const pts: number[][] = [[mp.x, mp.z]];
      const edges = me.state === 'queued' ? [L.approachEdge, L.gateEdge, ...me.route] : me.edge >= 0 ? [me.edge, ...me.route] : [];
      for (let i = 0; i < edges.length; i++) {
        const e = L.edges[edges[i]];
        const last = i === edges.length - 1;
        if (last && me.bay >= 0 && e.id === L.bays[me.bay].edge) {
          const b = L.bays[me.bay];
          const ep = edgePose(L, e.id, b.accessS);
          pts.push([ep.x, ep.z], [b.x, b.z]);
          break;
        }
        const nd = L.nodes[e.to];
        if (nd.floor !== f) {
          const ep = edgePose(L, e.id, e.len * 0.3);
          pts.push([ep.x, ep.z]);
          break;
        }
        pts.push([nd.x, nd.z]);
      }
      if (pts.length > 1) d = 'M ' + pts.map((p) => `${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' L ');
    }
    this.routePath.setAttribute('d', d);
    this.routeGlow.setAttribute('d', d);
    // draw-on when the route's destination changes
    const rk = me && d ? `${me.target ? me.target.floor + me.target.zone : ''}|${me.bay}|${f}` : '';
    if (rk && rk !== this.routeKey) {
      this.routeKey = rk;
      const len = 260;
      this.routePath.style.strokeDasharray = `${len}`;
      animate(this.routePath, { strokeDashoffset: [len, 0] }, { duration: 0.9, ease: [0.3, 0.7, 0.2, 1] }).then(() => {
        if (this.routeKey === rk) {
          this.routePath.style.strokeDasharray = '';
          this.routePath.style.strokeDashoffset = '';
        }
      });
    } else if (!rk) this.routeKey = '';
    // walking path to the lift
    if (st.walk && L.bays[st.walk.bay].floor === f) {
      this.walkLine.setAttribute('points', walkPath(L, st.walk.bay, st.walk.lift).map((p) => p.join(',')).join(' '));
      this.walkLine.setAttribute('visibility', 'visible');
    } else this.walkLine.setAttribute('visibility', 'hidden');
  }
}
