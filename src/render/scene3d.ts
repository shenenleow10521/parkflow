// Procedural 3D view of the car park, drawn with an orthographic camera and painter's ordering on
// a 2D canvas (no WebGL needed). Picking uses the projected polygons from the last frame.

import { store, emit } from '../ui/store';
import { Layout, Bay, GEdge, FLOOR_NAMES, ZONES, LIFT_X, LIFT_Z, SLAB, ZONE_X0, ZONE_COUNTS, BAY_W, ROW_Z, A1_Z, A2_Z, DEST_BY_ID } from '../core/layout';
import { Sim, Vehicle, VState, MANEUVER_S, GAP } from '../core/sim';
import { prefersReducedMotion } from '../ui/dom';

type V3 = [number, number, number];
interface Cam { yaw: number; pitch: number; zoom: number; tx: number; ty: number; tz: number }
interface Pick { kind: 'vehicle' | 'bay'; id: number; pts: number[] }

export const FLOOR_SPACING = 23;
const DEG = Math.PI / 180;

const C = {
  bg0: '#0c1729',
  bg1: '#132440',
  slabTop: '#1b2c47',
  slabSide: '#101d33',
  lane: '#24385a',
  laneLine: 'rgba(214, 226, 240, 0.28)',
  walk: '#1f3150',
  zebra: 'rgba(235, 240, 246, 0.55)',
  wall: '#2d4268',
  lift: '#d9e3e0',
  liftSide: '#9fb2ae',
  available: '#2fb37f',
  occupied: '#3a4963',
  reserved: '#8f6fe0',
  departing: '#e2a63a',
  hatchBase: '#454f60',
  hatchLine: '#8a93a3',
  ramp: '#2a3f62',
  road: '#22365a',
  carSearch: '#3ccfbb',
  carSlow: '#f0b04b',
  carLeave: '#a9b6cc',
  carParked: '#62728e',
  carRes: '#b49cf5',
  route: '#5eead4',
  label: '#e8eef6',
  labelDim: 'rgba(214, 226, 240, 0.65)',
  typeOku: '#6aa8ff',
  typeLadies: '#f19bbb',
  typeMember: '#e9d27c',
  zoneHi: 'rgba(94, 234, 212, 0.16)',
  zoneHiLine: 'rgba(94, 234, 212, 0.75)'
};

const TYPE_COLOR: Record<string, string> = { oku: C.typeOku, ladies: C.typeLadies, member: C.typeMember };

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
const shadeCache = new Map<string, string>();
function shade(hex: string, f: number): string {
  const key = hex + f.toFixed(2);
  let s = shadeCache.get(key);
  if (!s) {
    const [r, g, b] = hexToRgb(hex);
    s = `rgb(${Math.round(Math.min(255, r * f))},${Math.round(Math.min(255, g * f))},${Math.round(Math.min(255, b * f))})`;
    shadeCache.set(key, s);
  }
  return s;
}

export class Scene3D {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  w = 800;
  h = 500;
  dpr = 1;
  cam: Cam = { yaw: -6 * DEG, pitch: 25 * DEG, zoom: 6, tx: 28, ty: -23, tz: 16 };
  private tween: { from: Cam; to: Cam; t0: number; dur: number } | null = null;
  private picks: Pick[] = [];
  private hover: Pick | null = null;
  private hatch: CanvasPattern | null = null;
  private drag: { x: number; y: number; moved: number; mode: 'orbit' | 'pan'; id: number } | null = null;
  private pointers = new Map<number, { x: number; y: number }>();
  private pinch: { d: number; cx: number; cy: number } | null = null;
  dirty = true;
  ok = true;
  followId: number | null = null;
  stopFollow() {
    this.followId = null;
  }
  // basis
  private rx = 1; private rz = 0; private ux = 0; private uy = 1; private uz = 0; private dx = 0; private dy = 0; private dz = 1;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) { this.ok = false; this.ctx = null as unknown as CanvasRenderingContext2D; return; }
    this.ctx = ctx;
    this.makeHatch();
    this.bindInput();
    this.resize();
    this.fit(false);
  }

  private makeHatch() {
    const c = document.createElement('canvas');
    c.width = 8; c.height = 8;
    const g = c.getContext('2d');
    if (!g) return;
    g.fillStyle = C.hatchBase; g.fillRect(0, 0, 8, 8);
    g.strokeStyle = C.hatchLine; g.lineWidth = 1.4;
    g.beginPath(); g.moveTo(-2, 10); g.lineTo(10, -2); g.moveTo(-2, 2); g.lineTo(2, -2); g.moveTo(6, 10); g.lineTo(10, 6); g.stroke();
    this.hatch = this.ctx.createPattern(c, 'repeat');
  }

  resize() {
    const r = this.canvas.getBoundingClientRect();
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.w = Math.max(200, r.width);
    this.h = Math.max(200, r.height);
    this.canvas.width = Math.round(this.w * this.dpr);
    this.canvas.height = Math.round(this.h * this.dpr);
    this.dirty = true;
  }

  // ---------- camera ----------
  private basis(c: Cam) {
    const cp = Math.cos(c.pitch), sp = Math.sin(c.pitch), cy = Math.cos(c.yaw), sy = Math.sin(c.yaw);
    this.rx = cy; this.rz = -sy;
    this.ux = -sy * sp; this.uy = cp; this.uz = -cy * sp;
    this.dx = cp * sy; this.dy = sp; this.dz = cp * cy;
  }

  private P(x: number, y: number, z: number): [number, number, number] {
    const c = this.cam;
    const px = x - c.tx, py = y - c.ty, pz = z - c.tz;
    return [
      this.w / 2 + (px * this.rx + pz * this.rz) * c.zoom,
      this.h / 2 - (px * this.ux + py * this.uy + pz * this.uz) * c.zoom,
      px * this.dx + py * this.dy + pz * this.dz
    ];
  }

  floorY(f: number): number {
    if (store.floorView === 'all') return -f * FLOOR_SPACING;
    return -(f - (store.floorView as number)) * FLOOR_SPACING;
  }

  floorVisible(f: number): boolean {
    return store.floorView === 'all' || store.floorView === f;
  }

  defaultCam(): Cam {
    if (store.planView) return { yaw: 0, pitch: 89.5 * DEG, zoom: 6, tx: 28, ty: 0, tz: 16 };
    return store.floorView === 'all' ? { yaw: -6 * DEG, pitch: 25 * DEG, zoom: 6, tx: 28, ty: 0, tz: 16 } : { yaw: -14 * DEG, pitch: 38 * DEG, zoom: 6, tx: 28, ty: 0, tz: 16 };
  }

  /** Frame the visible floors in the viewport. */
  fit(animate = true) {
    const target = this.defaultCam();
    const floors = [0, 1, 2].filter((f) => this.floorVisible(f));
    const saved = this.cam;
    this.cam = { ...target, zoom: 1, tx: 0, ty: 0, tz: 0 };
    this.basis(this.cam);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const zs = [SLAB.z0 - 1, SLAB.z1 + 3];
    for (const f of floors) {
      const y0 = this.floorY(f);
      const xs = f === 0 ? [-40, 82] : [-24, 82];
      for (const x of xs) for (const z of zs) for (const y of [y0 - 1, y0 + 3]) {
        const p = this.P(x, y, z);
        minX = Math.min(minX, p[0] - this.w / 2); maxX = Math.max(maxX, p[0] - this.w / 2);
        minY = Math.min(minY, p[1] - this.h / 2); maxY = Math.max(maxY, p[1] - this.h / 2);
      }
    }
    const padL = 24, padR = store.driver.collapsed || this.w < 640 ? 24 : Math.min(282, this.w * 0.34), padTop = 52, padBot = 40;
    const zoom = Math.min((this.w - padL - padR) / (maxX - minX), (this.h - padTop - padBot) / (maxY - minY));
    const cxs = (minX + maxX) / 2 + (padR - padL) / 2 / zoom, cys = (minY + maxY) / 2 - (padTop - padBot) / 2 / zoom;
    // shift target so the projected bounds are centred
    const tx = cxs * this.rx - cys * this.ux;
    const ty = -cys * this.uy;
    const tz = cxs * this.rz - cys * this.uz;
    target.tx = tx; target.ty = ty; target.tz = tz;
    target.zoom = zoom;
    this.cam = saved;
    this.setCam(target, animate);
  }

  setCam(to: Cam, animate = true) {
    if (!animate || prefersReducedMotion()) {
      this.cam = to;
      this.tween = null;
    } else {
      this.tween = { from: { ...this.cam }, to, t0: performance.now(), dur: 750 };
    }
    this.dirty = true;
  }

  focusOn(x: number, y: number, z: number, zoom = 13) {
    const z1 = Math.max(this.cam.zoom, zoom);
    // keep the focused point clear of the driver preview panel on the right
    const padR = store.driver.collapsed || this.w < 640 ? 0 : Math.min(282, this.w * 0.34);
    this.basis(this.cam);
    const k = padR / 2 / z1;
    const to = { ...this.cam, tx: x + this.rx * k, ty: y, tz: z + this.rz * k, zoom: z1 };
    this.setCam(to, true);
  }

  focusVehicle(v: Vehicle) {
    const sim = store.sim;
    const f = sim.vehicleFloor(v);
    if (store.floorView !== 'all' && store.floorView !== f) {
      store.floorView = f;
      emit('floor');
    }
    const p = this.vehiclePos(sim, v, 1);
    if (p) this.focusOn(p.x, p.y, p.z, 13);
  }

  focusBay(b: Bay) {
    if (store.floorView !== 'all' && store.floorView !== b.floor) { store.floorView = b.floor; emit('floor'); }
    this.focusOn(b.x, this.floorY(b.floor), b.z, 14);
  }

  private stepTween() {
    if (!this.tween) return;
    const k = Math.min(1, (performance.now() - this.tween.t0) / this.tween.dur);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    const a = this.tween.from, b = this.tween.to;
    let dyaw = b.yaw - a.yaw;
    while (dyaw > Math.PI) dyaw -= 2 * Math.PI;
    while (dyaw < -Math.PI) dyaw += 2 * Math.PI;
    this.cam = {
      yaw: a.yaw + dyaw * e,
      pitch: a.pitch + (b.pitch - a.pitch) * e,
      zoom: a.zoom * Math.pow(b.zoom / a.zoom, e),
      tx: a.tx + (b.tx - a.tx) * e,
      ty: a.ty + (b.ty - a.ty) * e,
      tz: a.tz + (b.tz - a.tz) * e
    };
    if (k >= 1) this.tween = null;
    this.dirty = true;
  }

  get animating(): boolean {
    return !!this.tween;
  }

  // ---------- input ----------
  private bindInput() {
    const cv = this.canvas;
    cv.addEventListener('contextmenu', (e) => e.preventDefault());
    cv.addEventListener('pointerdown', (e) => {
      cv.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (this.pointers.size === 2) {
        const [p1, p2] = Array.from(this.pointers.values());
        this.pinch = { d: Math.hypot(p1.x - p2.x, p1.y - p2.y), cx: (p1.x + p2.x) / 2, cy: (p1.y + p2.y) / 2 };
        this.drag = null;
        return;
      }
      const pan = e.button === 2 || e.button === 1 || e.shiftKey || store.planView;
      this.drag = { x: e.clientX, y: e.clientY, moved: 0, mode: pan ? 'pan' : 'orbit', id: e.pointerId };
      this.tween = null;
    });
    cv.addEventListener('pointermove', (e) => {
      if (this.pointers.has(e.pointerId)) this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (this.pinch && this.pointers.size === 2) {
        const [p1, p2] = Array.from(this.pointers.values());
        const d = Math.hypot(p1.x - p2.x, p1.y - p2.y);
        const cx = (p1.x + p2.x) / 2, cy = (p1.y + p2.y) / 2;
        this.cam.zoom = Math.min(60, Math.max(2, this.cam.zoom * (d / this.pinch.d)));
        this.panBy(cx - this.pinch.cx, cy - this.pinch.cy);
        this.pinch = { d, cx, cy };
        this.dirty = true;
        return;
      }
      if (!this.drag || this.drag.id !== e.pointerId) {
        this.updateHover(e);
        return;
      }
      const dx = e.clientX - this.drag.x, dy = e.clientY - this.drag.y;
      this.drag.x = e.clientX; this.drag.y = e.clientY;
      this.drag.moved += Math.abs(dx) + Math.abs(dy);
      if (this.drag.moved < 4) return;
      if (this.drag.mode === 'orbit') {
        this.cam.yaw -= dx * 0.006;
        this.cam.pitch = Math.min(89.5 * DEG, Math.max(14 * DEG, this.cam.pitch + dy * 0.005));
      } else this.panBy(dx, dy);
      this.dirty = true;
    });
    const end = (e: PointerEvent) => {
      this.pointers.delete(e.pointerId);
      if (this.pointers.size < 2) this.pinch = null;
      if (this.drag && this.drag.id === e.pointerId) {
        if (this.drag.moved < 5) this.click(e);
        this.drag = null;
      }
    };
    cv.addEventListener('pointerup', end);
    cv.addEventListener('pointercancel', end);
    cv.addEventListener('pointerleave', () => { if (this.hover) { this.hover = null; this.dirty = true; } });
    cv.addEventListener('wheel', (e) => {
      e.preventDefault();
      const r = cv.getBoundingClientRect();
      const mx = e.clientX - r.left - this.w / 2, my = e.clientY - r.top - this.h / 2;
      const z0 = this.cam.zoom;
      const z1 = Math.min(60, Math.max(2, z0 * Math.exp(-e.deltaY * 0.0015)));
      this.basis(this.cam);
      const k = 1 / z0 - 1 / z1;
      this.cam.tx += this.rx * mx * k - this.ux * my * k;
      this.cam.ty += -this.uy * my * k;
      this.cam.tz += this.rz * mx * k - this.uz * my * k;
      this.cam.zoom = z1;
      this.tween = null;
      this.dirty = true;
    }, { passive: false });
    window.addEventListener('resize', () => {
      const w0 = this.w, h0 = this.h;
      this.resize();
      if (Math.abs(this.w - w0) > 40 || Math.abs(this.h - h0) > 40) this.fit(false);
    });
  }

  private panBy(dx: number, dy: number) {
    this.basis(this.cam);
    const z = this.cam.zoom;
    this.cam.tx -= (this.rx * dx - this.ux * dy) / z;
    this.cam.ty -= (-this.uy * dy) / z;
    this.cam.tz -= (this.rz * dx - this.uz * dy) / z;
  }

  private pickAt(x: number, y: number): Pick | null {
    for (let i = this.picks.length - 1; i >= 0; i--) {
      const p = this.picks[i];
      if (pointInPoly(x, y, p.pts)) return p;
    }
    return null;
  }

  private updateHover(e: PointerEvent) {
    const r = this.canvas.getBoundingClientRect();
    const p = this.pickAt(e.clientX - r.left, e.clientY - r.top);
    const changed = (p && (!this.hover || p.kind !== this.hover.kind || p.id !== this.hover.id)) || (!p && this.hover);
    this.hover = p;
    this.canvas.style.cursor = p ? 'pointer' : 'grab';
    if (changed) this.dirty = true;
  }

  private click(e: PointerEvent) {
    const r = this.canvas.getBoundingClientRect();
    const p = this.pickAt(e.clientX - r.left, e.clientY - r.top);
    if (!p) { store.selected = null; emit('select'); return; }
    store.selected = { kind: p.kind, id: p.id };
    if (p.kind === 'vehicle') store.rightTab = store.rightTab === 'actions' ? 'vehicle' : store.rightTab;
    else store.rightTab = 'vehicle';
    emit('select');
  }

  // ---------- geometry helpers ----------
  private poly(pts: V3[], fill: string | CanvasPattern, stroke?: string, lw = 1, pick?: { kind: 'vehicle' | 'bay'; id: number }, alpha = 1) {
    const ctx = this.ctx;
    const sp: number[] = [];
    ctx.beginPath();
    for (let i = 0; i < pts.length; i++) {
      const p = this.P(pts[i][0], pts[i][1], pts[i][2]);
      sp.push(p[0], p[1]);
      if (i === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]);
    }
    ctx.closePath();
    if (alpha !== 1) ctx.globalAlpha = alpha;
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
    if (alpha !== 1) ctx.globalAlpha = 1;
    if (pick) this.picks.push({ kind: pick.kind, id: pick.id, pts: sp });
    return sp;
  }

  private rect(x0: number, x1: number, z0: number, z1: number, y: number, fill: string | CanvasPattern, stroke?: string, lw = 1, alpha = 1) {
    return this.poly([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]], fill, stroke, lw, undefined, alpha);
  }

  /** Oriented box: centre (cx, cz), base y, length along heading angle a, width, height. */
  private box(cx: number, y: number, cz: number, len: number, wid: number, h: number, a: number, color: string, opts: { pick?: { kind: 'vehicle' | 'bay'; id: number }; outline?: string; topColor?: string } = {}) {
    const ca = Math.cos(a), sa = Math.sin(a);
    const lx = (ca * len) / 2, lz = (sa * len) / 2, wx = (-sa * wid) / 2, wz = (ca * wid) / 2;
    const b: V3[] = [
      [cx - lx - wx, y, cz - lz - wz], [cx + lx - wx, y, cz + lz - wz], [cx + lx + wx, y, cz + lz + wz], [cx - lx + wx, y, cz - lz + wz]
    ];
    const t: V3[] = b.map((p) => [p[0], y + h, p[2]] as V3);
    const faces: { pts: V3[]; nx: number; nz: number }[] = [
      { pts: [b[0], b[1], t[1], t[0]], nx: -wx, nz: -wz },
      { pts: [b[1], b[2], t[2], t[1]], nx: lx, nz: lz },
      { pts: [b[2], b[3], t[3], t[2]], nx: wx, nz: wz },
      { pts: [b[3], b[0], t[0], t[3]], nx: -lx, nz: -lz }
    ];
    const all: number[] = [];
    for (const f of faces) {
      if (f.nx * this.dx + f.nz * this.dz <= 0) continue;
      const n = Math.hypot(f.nx, f.nz) || 1;
      const light = 0.62 + 0.22 * ((f.nx / n) * -0.45 + (f.nz / n) * 0.75);
      const sp = this.poly(f.pts, shade(color, light));
      all.push(...sp);
    }
    const top = this.poly(t, opts.topColor || shade(color, 1.08), opts.outline, opts.outline ? 2 : 1);
    all.push(...top);
    if (opts.pick) this.picks.push({ kind: opts.pick.kind, id: opts.pick.id, pts: hull(all) });
  }

  private text(x: number, y: number, z: number, s: string, opts: { size?: number; color?: string; bg?: string; weight?: number; align?: CanvasTextAlign; dy?: number } = {}) {
    const p = this.P(x, y, z);
    const ctx = this.ctx;
    const size = opts.size || 11;
    ctx.font = `${opts.weight || 600} ${size}px "Instrument Sans", "Segoe UI", system-ui, sans-serif`;
    ctx.textAlign = opts.align || 'center';
    ctx.textBaseline = 'middle';
    const tx = p[0], ty = p[1] + (opts.dy || 0);
    if (opts.bg) {
      const w = ctx.measureText(s).width + 10;
      const x0 = opts.align === 'left' ? tx - 5 : opts.align === 'right' ? tx - w + 5 : tx - w / 2;
      ctx.fillStyle = opts.bg;
      roundRect(ctx, x0, ty - size / 2 - 4, w, size + 8, 5);
      ctx.fill();
    }
    ctx.fillStyle = opts.color || C.label;
    ctx.fillText(s, tx, ty);
  }

  // ---------- vehicle placement ----------
  private edgePoint(L: Layout, eid: number, s: number): { x: number; y: number; z: number; a: number } {
    const e = L.edges[eid];
    const a = L.nodes[e.from], b = L.nodes[e.to];
    const k = Math.max(0, Math.min(1, s / e.len));
    const ya = this.floorY(a.floor), yb = this.floorY(b.floor);
    return { x: a.x + (b.x - a.x) * k, y: ya + (yb - ya) * k, z: a.z + (b.z - a.z) * k, a: Math.atan2(b.z - a.z, b.x - a.x) };
  }

  private placeAt(sim: Sim, v: Vehicle, state: VState, edge: number, s: number, man: number): { x: number; y: number; z: number; a: number } | null {
    const L = sim.L;
    if (state === 'parked') {
      const b = L.bays[v.bay];
      return { x: b.x, y: this.floorY(b.floor), z: b.z, a: Math.PI / 2 };
    }
    if (state === 'parking' || state === 'unparking') {
      const b = L.bays[v.bay];
      const az = b.row < 2 ? A1_Z : A2_Z;
      let k = Math.min(1, man / MANEUVER_S);
      if (state === 'unparking') k = 1 - k;
      return { x: b.x, y: this.floorY(b.floor), z: az + (b.z - az) * k, a: Math.PI / 2 };
    }
    if (state === 'queued') {
      const idx = sim.gateQueue.indexOf(v.i);
      if (idx < 0 || idx > 1) return null;
      return this.edgePoint(L, L.approachEdge, L.edges[L.approachEdge].len - 1 - idx * GAP);
    }
    if (edge < 0) return null;
    return this.edgePoint(L, edge, s);
  }

  vehiclePos(sim: Sim, v: Vehicle, alpha: number): { x: number; y: number; z: number; a: number } | null {
    const cur = this.placeAt(sim, v, v.state, v.edge, v.s, v.man);
    if (!cur) return null;
    if (alpha >= 1 || v.pState === 'pending') return cur;
    const prev = this.placeAt(sim, v, v.pState, v.pEdge, v.pS, v.pMan);
    if (!prev) return cur;
    if (Math.hypot(prev.x - cur.x, prev.z - cur.z) > 9 || Math.abs(prev.y - cur.y) > 6) return cur;
    let da = cur.a - prev.a;
    while (da > Math.PI) da -= 2 * Math.PI;
    while (da < -Math.PI) da += 2 * Math.PI;
    return { x: prev.x + (cur.x - prev.x) * alpha, y: prev.y + (cur.y - prev.y) * alpha, z: prev.z + (cur.z - prev.z) * alpha, a: prev.a + da * Math.min(1, alpha * 1.6) };
  }

  private vehicleGroup(sim: Sim, v: Vehicle): { floor: number; ramp: boolean } | null {
    if (v.state === 'parked' || v.state === 'parking' || v.state === 'unparking') return { floor: sim.L.bays[v.bay].floor, ramp: false };
    if (v.state === 'queued') return { floor: 0, ramp: false };
    if (v.edge < 0) return null;
    const e = sim.L.edges[v.edge];
    if (e.kind === 'ramp') return { floor: sim.L.nodes[e.to].floor > sim.L.nodes[e.from].floor ? sim.L.nodes[e.to].floor : sim.L.nodes[e.from].floor, ramp: true };
    return { floor: sim.L.nodes[e.from].floor, ramp: false };
  }

  // ---------- draw ----------
  render(alpha: number) {
    if (!this.ok) return;
    this.stepTween();
    const ctx = this.ctx;
    const sim = store.sim;
    const L = sim.L;
    this.basis(this.cam);
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    const g = ctx.createLinearGradient(0, 0, 0, this.h);
    g.addColorStop(0, C.bg1);
    g.addColorStop(1, C.bg0);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, this.w, this.h);
    this.picks = [];

    const sel = store.selected;
    const selV = sel && sel.kind === 'vehicle' ? sim.vehicles[sel.id] : null;
    const counts = sim.counts();

    // group vehicles
    const byFloor: Vehicle[][] = [[], [], []];
    const byRamp: Vehicle[][] = [[], [], []];
    for (const v of sim.vehicles) {
      if (v.state === 'pending' || v.state === 'exited' || v.state === 'cancelled' || v.state === 'diverted') continue;
      const gp = this.vehicleGroup(sim, v);
      if (!gp) continue;
      (gp.ramp ? byRamp : byFloor)[gp.floor].push(v);
    }

    const floors = store.floorView === 'all' ? [2, 1, 0] : [store.floorView as number];
    for (const f of floors) {
      // ramps arriving from the floor below are drawn before this floor's slab
      if (store.floorView === 'all' && f < 2) this.drawRamps(sim, f + 1, byRamp[f + 1], alpha, selV);
      this.drawFloor(sim, f, byFloor[f], alpha, selV, counts.perFloor[f].generalFree);
    }
    if (store.floorView !== 'all') {
      const f = store.floorView as number;
      this.drawRampStubs(sim, f, byRamp, alpha, selV);
    }

    // labels last so they stay readable
    this.drawLabels(sim, counts);
    if (selV) this.drawSelectedOverlay(sim, selV, alpha);
    this.dirty = false;
  }

  private drawFloor(sim: Sim, f: number, cars: Vehicle[], alpha: number, selV: Vehicle | null, generalFree: number) {
    void generalFree;
    const L = sim.L;
    const y = this.floorY(f);
    const ctx = this.ctx;
    // slab with thickness
    this.box((SLAB.x0 + SLAB.x1) / 2, y - 0.9, (SLAB.z0 + SLAB.z1) / 2, SLAB.x1 - SLAB.x0, SLAB.z1 - SLAB.z0, 0.9, 0, C.slabSide, { topColor: C.slabTop });
    // roads beyond the slab on this floor
    for (const e of L.edges) {
      if (e.kind === 'aisle' || e.kind === 'connector' || e.kind === 'ramp') continue;
      const a = L.nodes[e.from], b = L.nodes[e.to];
      if (a.floor !== f || b.floor !== f) continue;
      this.roadQuad(a.x, a.z, b.x, b.z, y + 0.01, e.kind === 'gate' || e.kind === 'approach' || e.kind === 'exit' ? C.road : C.ramp);
    }
    // lanes
    this.rect(0.4, 73.6, A1_Z - 3, A1_Z + 3, y + 0.02, C.lane);
    this.rect(0.4, 73.6, A2_Z - 3, A2_Z + 3, y + 0.02, C.lane);
    this.rect(0.4, 6.4, A1_Z - 3, A2_Z + 3, y + 0.02, C.lane);
    this.rect(66.6, 73.6, A1_Z - 3, A2_Z + 3, y + 0.02, C.lane);
    // walkway strip
    this.rect(6.6, 66.4, 16.2, 20.8, y + 0.02, C.walk);
    // lane arrows (one-way loop)
    ctx.lineWidth = 1.2;
    for (let x = 10; x < 68; x += 9) this.chevron(x, y + 0.04, A1_Z, 1, 0);
    for (let x = 64; x > 6; x -= 9) this.chevron(x, y + 0.04, A2_Z, -1, 0);
    this.chevron(70, y + 0.04, 16, 0, 1);
    this.chevron(3.4, y + 0.04, 16, 0, -1);
    // zebra crossings to each lift
    for (const z of ZONES) {
      const lx = LIFT_X[z];
      for (let k = -1.25; k <= 1.25; k += 0.75) {
        this.rect(lx + k - 0.22, lx + k + 0.22, A1_Z - 2.8, A1_Z + 2.8, y + 0.03, C.zebra);
        this.rect(lx + k - 0.22, lx + k + 0.22, A2_Z - 2.8, A2_Z + 2.8, y + 0.03, C.zebra);
      }
    }
    // bays
    const showGlyph = this.cam.zoom >= 7.5;
    for (const b of L.bays) {
      if (b.floor !== f) continue;
      const st = sim.bayStatus(b.idx);
      const fill = st === 'available' ? C.available : st === 'reserved' ? C.reserved : st === 'departing' ? C.departing : st === 'occupied' ? C.occupied : this.hatch || C.hatchBase;
      const hx = BAY_W / 2 - 0.12, hz = 2.38;
      const isHover = this.hover && this.hover.kind === 'bay' && this.hover.id === b.idx;
      const isSel = store.selected && store.selected.kind === 'bay' && store.selected.id === b.idx;
      this.poly([[b.x - hx, y + 0.05, b.z - hz], [b.x + hx, y + 0.05, b.z - hz], [b.x + hx, y + 0.05, b.z + hz], [b.x - hx, y + 0.05, b.z + hz]], fill, isSel ? '#ffffff' : isHover ? 'rgba(255,255,255,0.7)' : undefined, isSel ? 2.2 : 1.4, { kind: 'bay', id: b.idx });
      // bay type marker: a coloured band at the aisle end
      if (b.type !== 'general') {
        const towardAisle = b.row === 0 ? 1 : b.row === 1 ? -1 : -1;
        const zEdge = b.z + towardAisle * hz;
        this.rect(b.x - hx, b.x + hx, Math.min(zEdge, zEdge - towardAisle * 0.7), Math.max(zEdge, zEdge - towardAisle * 0.7), y + 0.06, TYPE_COLOR[b.type]);
      }
      if (showGlyph) this.bayGlyph(b, st, y);
    }
    // target zone highlight for the selected guided vehicle
    if (selV && selV.target && selV.target.floor === f && selV.parkT < 0 && (selV.state === 'driving' || selV.state === 'parking')) this.zoneHighlight(selV.target.zone, y);
    // 3D objects, painter-sorted
    const objs: { d: number; draw: () => void }[] = [];
    const depth = (x: number, yy: number, z: number) => this.P(x, yy, z)[2];
    // perimeter parapets with openings for lanes
    const wallH = 0.9;
    const walls: [number, number, number, number][] = [
      [SLAB.x0, SLAB.x1, SLAB.z0, SLAB.z0 + 0.3], [SLAB.x0, SLAB.x1, SLAB.z1 - 0.3, SLAB.z1],
      [SLAB.x0, SLAB.x0 + 0.3, SLAB.z0, A1_Z - 3], [SLAB.x0, SLAB.x0 + 0.3, A1_Z + 3, A2_Z - 3], [SLAB.x0, SLAB.x0 + 0.3, A2_Z + 3, SLAB.z1],
      [SLAB.x1 - 0.3, SLAB.x1, SLAB.z0, A1_Z - 3], [SLAB.x1 - 0.3, SLAB.x1, A1_Z + 3, A2_Z - 3], [SLAB.x1 - 0.3, SLAB.x1, A2_Z + 3, SLAB.z1]
    ];
    for (const w of walls) {
      const cx = (w[0] + w[1]) / 2, cz = (w[2] + w[3]) / 2;
      objs.push({ d: depth(cx, y, cz), draw: () => this.box(cx, y, cz, w[1] - w[0], w[3] - w[2], wallH, 0, C.wall) });
    }
    for (const z of ZONES) {
      const lx = LIFT_X[z];
      objs.push({ d: depth(lx, y, LIFT_Z), draw: () => this.box(lx, y, LIFT_Z, 4.6, 4.2, 2.8, 0, C.liftSide, { topColor: C.lift }) });
    }
    if (f === 0) {
      // gate booths and barrier arms
      objs.push({ d: depth(-12, y, 4), draw: () => this.box(-12, y, 4.2, 1.6, 1.6, 2.2, 0, '#8796ad', { topColor: '#c8d2df' }) });
      objs.push({ d: depth(-12, y, 28), draw: () => this.box(-12, y, 27.8, 1.6, 1.6, 2.2, 0, '#8796ad', { topColor: '#c8d2df' }) });
      const open = sim.nextGateT - sim.t > 2;
      objs.push({ d: depth(-12, y, 8), draw: () => this.box(-12, y + 1, open ? 6.2 : 8, 0.25, open ? 1.6 : 5.6, 0.25, 0, '#f2c14e') });
      objs.push({ d: depth(-12, y, 24), draw: () => this.box(-12, y + 1, 24, 0.25, 5.6, 0.25, 0, '#f2c14e') });
    }
    for (const v of cars) {
      const p = this.vehiclePos(sim, v, alpha);
      if (!p) continue;
      objs.push({ d: depth(p.x, p.y, p.z), draw: () => this.drawCar(v, p, selV) });
    }
    objs.sort((a, b) => a.d - b.d);
    for (const o of objs) o.draw();
  }

  private drawCar(v: Vehicle, p: { x: number; y: number; z: number; a: number }, selV: Vehicle | null) {
    const sim = store.sim;
    let color = C.carParked;
    if (v.state === 'leaving' || v.state === 'unparking') color = C.carLeave;
    else if (v.state === 'driving' || v.state === 'parking' || v.state === 'queued') {
      color = v.resId ? C.carRes : v.gateT >= 0 && sim.t - v.gateT > 300 ? C.carSlow : C.carSearch;
    }
    const isSel = selV === v;
    const isHover = this.hover && this.hover.kind === 'vehicle' && this.hover.id === v.i;
    this.box(p.x, p.y + 0.06, p.z, 4.3, 1.9, 1.35, p.a, color, { pick: { kind: 'vehicle', id: v.i }, outline: isSel ? '#ffffff' : isHover ? 'rgba(255,255,255,0.75)' : undefined });
  }

  private roadQuad(x0: number, z0: number, x1: number, z1: number, y: number, fill: string) {
    const a = Math.atan2(z1 - z0, x1 - x0);
    const wx = -Math.sin(a) * 3, wz = Math.cos(a) * 3;
    const ex = Math.cos(a) * 3, ez = Math.sin(a) * 3;
    this.poly([[x0 - ex + wx, y, z0 - ez + wz], [x1 + ex + wx, y, z1 + ez + wz], [x1 + ex - wx, y, z1 + ez - wz], [x0 - ex - wx, y, z0 - ez - wz]], fill);
  }

  private chevron(x: number, y: number, z: number, dx: number, dz: number) {
    const ctx = this.ctx;
    const s = 1.1;
    const px = -dz, pz = dx;
    const a = this.P(x - dx * s + px * s, y, z - dz * s + pz * s);
    const b = this.P(x + dx * s * 0.6, y, z + dz * s * 0.6);
    const c = this.P(x - dx * s - px * s, y, z - dz * s - pz * s);
    ctx.strokeStyle = C.laneLine;
    ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.lineTo(c[0], c[1]); ctx.stroke();
  }

  private bayGlyph(b: Bay, st: string, y: number) {
    const p = this.P(b.x, y + 0.08, b.z);
    const ctx = this.ctx;
    const s = Math.min(9, this.cam.zoom * 0.7);
    ctx.save();
    ctx.translate(p[0], p[1]);
    ctx.lineWidth = 1.3;
    ctx.strokeStyle = 'rgba(255,255,255,0.9)';
    ctx.fillStyle = 'rgba(255,255,255,0.92)';
    if (st === 'reserved') {
      ctx.font = `700 ${s * 1.2}px "IBM Plex Mono", ui-monospace, monospace`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('R', 0, 0);
    } else if (st === 'departing') {
      ctx.beginPath(); ctx.arc(0, 0, s * 0.55, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, -s * 0.38); ctx.moveTo(0, 0); ctx.lineTo(s * 0.3, 0); ctx.stroke();
    } else if (st === 'uncertain') {
      ctx.font = `700 ${s * 1.2}px "IBM Plex Mono", ui-monospace, monospace`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('?', 0, 0);
    } else if (st === 'unavailable') {
      ctx.beginPath(); ctx.moveTo(-s * 0.4, -s * 0.4); ctx.lineTo(s * 0.4, s * 0.4); ctx.moveTo(s * 0.4, -s * 0.4); ctx.lineTo(-s * 0.4, s * 0.4); ctx.stroke();
    } else if (st === 'available' && b.type !== 'general') {
      drawTypeGlyph(ctx, b.type, s);
    }
    ctx.restore();
  }

  private zoneHighlight(zone: string, y: number) {
    const x0 = ZONE_X0[zone as 'A'] - 0.3;
    const x1 = ZONE_X0[zone as 'A'] + ZONE_COUNTS[zone as 'A'] * BAY_W + 0.3;
    for (const [z0, z1] of [[ROW_Z[0] - 2.7, ROW_Z[1] + 2.7], [ROW_Z[2] - 2.7, ROW_Z[2] + 2.7]]) {
      this.rect(x0, x1, z0, z1, y + 0.09, C.zoneHi, C.zoneHiLine, 1.5);
    }
  }

  private drawRamps(sim: Sim, lowerFloor: number, cars: Vehicle[], alpha: number, selV: Vehicle | null) {
    const L = sim.L;
    for (const e of L.edges) {
      if (e.kind !== 'ramp') continue;
      const a = L.nodes[e.from], b = L.nodes[e.to];
      const lo = Math.max(a.floor, b.floor);
      if (lo !== lowerFloor) continue;
      this.rampQuad(e, 0, 1);
    }
    const objs = cars
      .map((v) => ({ v, p: this.vehiclePos(sim, v, alpha) }))
      .filter((o) => o.p)
      .map((o) => ({ ...o, d: this.P(o.p!.x, o.p!.y, o.p!.z)[2] }))
      .sort((x, y) => x.d - y.d);
    for (const o of objs) this.drawCar(o.v, o.p!, selV);
  }

  private rampQuad(e: GEdge, k0: number, k1: number, alpha = 0.92) {
    const L = store.sim.L;
    const a = L.nodes[e.from], b = L.nodes[e.to];
    const ya = this.floorY(a.floor), yb = this.floorY(b.floor);
    const p0: V3 = [a.x + (b.x - a.x) * k0, ya + (yb - ya) * k0, a.z + (b.z - a.z) * k0];
    const p1: V3 = [a.x + (b.x - a.x) * k1, ya + (yb - ya) * k1, a.z + (b.z - a.z) * k1];
    const w = 3;
    this.poly([[p0[0] - w, p0[1], p0[2]], [p0[0] + w, p0[1], p0[2]], [p1[0] + w, p1[1], p1[2]], [p1[0] - w, p1[1], p1[2]]], C.ramp, 'rgba(160,180,210,0.35)', 1, undefined, alpha);
    // direction chevrons along the ramp
    for (let k = k0 + 0.15; k < k1 - 0.05; k += 0.25) {
      const cx = a.x + (b.x - a.x) * k, cy = ya + (yb - ya) * k + 0.05, cz = a.z + (b.z - a.z) * k;
      const dz = Math.sign(b.z - a.z);
      this.chevron(cx, cy, cz, 0, dz);
    }
  }

  private drawRampStubs(sim: Sim, f: number, byRamp: Vehicle[][], alpha: number, selV: Vehicle | null) {
    const L = sim.L;
    for (const e of L.edges) {
      if (e.kind !== 'ramp') continue;
      const a = L.nodes[e.from], b = L.nodes[e.to];
      if (a.floor === f) this.rampQuad(e, 0, 0.4, 0.75);
      else if (b.floor === f) this.rampQuad(e, 0.6, 1, 0.75);
    }
    const cars = [...byRamp[0], ...byRamp[1], ...byRamp[2]].filter((v) => sim.vehicleFloor(v) === f);
    for (const v of cars) {
      const p = this.vehiclePos(sim, v, alpha);
      if (p) this.drawCar(v, p, selV);
    }
  }

  private drawLabels(sim: Sim, counts: ReturnType<Sim['counts']>) {
    const L = sim.L;
    const zoom = this.cam.zoom;
    for (const f of [0, 1, 2]) {
      if (!this.floorVisible(f)) continue;
      const y = this.floorY(f);
      const pf = counts.perFloor[f];
      this.text(f === 0 ? -26 : -8, y + 0.2, SLAB.z1 + 2.5, `${FLOOR_NAMES[f]}  ·  ${pf.generalFree} general free`, { size: 12, bg: 'rgba(8,16,30,0.82)', align: 'right', weight: 650 });
      if (zoom >= 4.5) {
        for (const z of ZONES) {
          const lx = LIFT_X[z];
          this.text(lx, y + 3.4, LIFT_Z, `Lift ${z}`, { size: 10, bg: 'rgba(233,239,236,0.92)', color: '#13213a', weight: 700 });
        }
      }
      if (zoom >= 3.5) {
        for (const z of ZONES) {
          const x = ZONE_X0[z] + (ZONE_COUNTS[z] * BAY_W) / 2;
          this.text(x, y, SLAB.z1 + 2.2, `Zone ${z}`, { size: 10, color: C.labelDim, weight: 700 });
        }
      }
    }
    if (this.floorVisible(0)) {
      const y = this.floorY(0);
      this.text(-19, y + 0.2, A1_Z - 4.8, 'Entrance', { size: 10.5, bg: 'rgba(8,16,30,0.8)' });
      this.text(-19, y + 0.2, A2_Z + 4.8, 'Exit', { size: 10.5, bg: 'rgba(8,16,30,0.8)' });
      const q = sim.gateQueue.length;
      if (q > 0) this.text(-31, y + 0.5, A1_Z, `Queue ${q}`, { size: 10.5, bg: q > 3 ? 'rgba(180,56,47,0.95)' : 'rgba(201,138,18,0.95)', color: '#fff', weight: 700 });
    }
    if (zoom >= 4) {
      for (const e of L.edges) {
        if (e.kind !== 'ramp') continue;
        const a = L.nodes[e.from], b = L.nodes[e.to];
        if (!this.floorVisible(a.floor)) continue;
        const down = b.floor > a.floor;
        const y = this.floorY(a.floor);
        this.text(a.x, y + 0.3, a.z + (down ? -4.6 : 4.6), `${down ? '↓' : '↑'} ${FLOOR_NAMES[b.floor]}`, { size: 10, bg: 'rgba(8,16,30,0.75)', color: C.labelDim });
      }
    }
  }

  private drawSelectedOverlay(sim: Sim, v: Vehicle, alpha: number) {
    const L = sim.L;
    const ctx = this.ctx;
    const pos = this.vehiclePos(sim, v, alpha);
    if (!pos) return;
    // remaining driving route
    if ((v.state === 'driving' || v.state === 'leaving') && v.edge >= 0) {
      const pts: [number, number][] = [];
      const push = (x: number, y: number, z: number) => { const p = this.P(x, y + 0.35, z); pts.push([p[0], p[1]]); };
      push(pos.x, pos.y, pos.z);
      const edges = [v.edge, ...v.route];
      for (let i = 0; i < edges.length; i++) {
        const e = L.edges[edges[i]];
        const isLast = i === edges.length - 1;
        if (isLast && v.bay >= 0 && e.id === L.bays[v.bay].edge) {
          const b = L.bays[v.bay];
          const ep = this.edgePoint(L, e.id, b.accessS);
          push(ep.x, ep.y, ep.z);
          push(b.x, ep.y, b.z);
          break;
        }
        const n = L.nodes[e.to];
        if (!this.floorVisible(n.floor) && store.floorView !== 'all') {
          // fade out at the edge of the visible floor
          const ep = this.edgePoint(L, e.id, e.len * 0.4);
          push(ep.x, ep.y, ep.z);
          break;
        }
        push(n.x, this.floorY(n.floor), n.z);
      }
      ctx.save();
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.strokeStyle = 'rgba(94,234,212,0.25)';
      ctx.lineWidth = 9;
      ctx.beginPath();
      pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.stroke();
      ctx.strokeStyle = C.route;
      ctx.lineWidth = 3;
      ctx.stroke();
      ctx.restore();
    }
    // walking line to the destination lift (separate measure)
    const lift = DEST_BY_ID[v.dest].lift;
    let from: { x: number; y: number; z: number; f: number } | null = null;
    if (v.bay >= 0) {
      const b = L.bays[v.bay];
      from = { x: b.x, y: this.floorY(b.floor), z: b.z, f: b.floor };
    } else if (v.target) {
      from = { x: ZONE_X0[v.target.zone] + (ZONE_COUNTS[v.target.zone] * BAY_W) / 2, y: this.floorY(v.target.floor), z: ROW_Z[1], f: v.target.floor };
    }
    if (from && this.floorVisible(from.f)) {
      const a = this.P(from.x, from.y + 0.4, from.z);
      const m = this.P(LIFT_X[lift], from.y + 0.4, from.z);
      const b = this.P(LIFT_X[lift], from.y + 0.4, LIFT_Z);
      ctx.save();
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = 'rgba(255,255,255,0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(m[0], m[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      ctx.restore();
      const walk = v.bay >= 0 ? L.bays[v.bay].walk[lift] : v.alloc && v.alloc.chosen ? Math.round(v.alloc.chosen.walk) : 0;
      this.text(LIFT_X[lift], from.y + 3.6, LIFT_Z, `Walk ≈ ${walk} m`, { size: 10.5, bg: 'rgba(255,255,255,0.95)', color: '#13213a', dy: -16, weight: 700 });
    }
    // code tag above the car
    this.text(pos.x, pos.y + 2.4, pos.z, v.code, { size: 10.5, bg: 'rgba(94,234,212,0.95)', color: '#06201c', weight: 700, dy: -6 });
  }
}

function drawTypeGlyph(ctx: CanvasRenderingContext2D, type: string, s: number) {
  ctx.fillStyle = 'rgba(255,255,255,0.95)';
  ctx.strokeStyle = 'rgba(255,255,255,0.95)';
  if (type === 'oku') {
    ctx.beginPath(); ctx.arc(s * 0.05, -s * 0.5, s * 0.14, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(-s * 0.05, s * 0.18, s * 0.36, 0.3, Math.PI * 1.6); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s * 0.05, -s * 0.32); ctx.lineTo(s * 0.05, 0.02 * s); ctx.lineTo(s * 0.4, 0.02 * s); ctx.lineTo(s * 0.5, s * 0.45); ctx.stroke();
  } else if (type === 'ladies') {
    // female sign: ring with a cross below
    ctx.lineWidth = Math.max(1.5, s * 0.12);
    ctx.beginPath(); ctx.arc(0, -s * 0.18, s * 0.3, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, s * 0.12); ctx.lineTo(0, s * 0.62); ctx.moveTo(-s * 0.2, s * 0.4); ctx.lineTo(s * 0.2, s * 0.4); ctx.stroke();
  } else if (type === 'member') {
    ctx.beginPath();
    for (let i = 0; i < 10; i++) {
      const r = i % 2 === 0 ? s * 0.55 : s * 0.24;
      const a = -Math.PI / 2 + (i * Math.PI) / 5;
      if (i === 0) ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r); else ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    ctx.closePath(); ctx.fill();
  }
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function pointInPoly(x: number, y: number, pts: number[]): boolean {
  let inside = false;
  for (let i = 0, j = pts.length - 2; i < pts.length; j = i, i += 2) {
    const xi = pts[i], yi = pts[i + 1], xj = pts[j], yj = pts[j + 1];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi + 1e-12) + xi) inside = !inside;
  }
  return inside;
}

function hull(pts: number[]): number[] {
  const p: [number, number][] = [];
  for (let i = 0; i < pts.length; i += 2) p.push([pts[i], pts[i + 1]]);
  p.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o: number[], a: number[], b: number[]) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower: [number, number][] = [];
  for (const q of p) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop(); lower.push(q); }
  const upper: [number, number][] = [];
  for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop(); upper.push(q); }
  const h = lower.slice(0, -1).concat(upper.slice(0, -1));
  const out: number[] = [];
  for (const q of h) out.push(q[0], q[1]);
  return out;
}

export const SCENE_COLORS = C;
