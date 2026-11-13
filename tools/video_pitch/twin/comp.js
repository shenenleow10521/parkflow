// ParkFlow V3 · 60-second film. window.seek(t) draws the frame at time t (seconds). Concept simulation.
import * as THREE from './vendor/three.module.min.js';

const $ = (id) => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, u) => a + (b - a) * u;
const sm = (u) => { u = clamp(u); return u * u * (3 - 2 * u); };
const seg = (t, a, b) => clamp((t - a) / (b - a));
const win = (t, a, b, f = 0.45) => sm(seg(t, a, a + f)) * (1 - sm(seg(t, b - f, b)));
const op = (el, v) => { const s = v.toFixed(3); if (el._o !== s) { el.style.opacity = s; el._o = s; } };
const txt = (el, v) => { if (el._t !== v) { el.textContent = v; el._t = v; } };
const html = (el, v) => { if (el._h !== v) { el.innerHTML = v; el._h = v; } };
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const V = (x, y, z) => new THREE.Vector3(x, y, z);

// ---------------------------------------------------------------- layout (metres), reconstructed from the LG walkthrough
const COLS = ['D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U'];
const SP = 8.1, BW = 2.7, NB = 45;
const STRIPS = [{ z0: 0, z1: 5, face: 1 }, { z0: 11.5, z1: 16.5, face: -1 }, { z0: 16.5, z1: 21.5, face: 1 }, { z0: 28, z1: 33, face: -1 }, { z0: 33, z1: 38, face: 1 }, { z0: 44.5, z1: 49.5, face: -1 }];
const AISLE = [8.25, 24.75, 41.25];
const ROWZ = [5, 11.5, 21.5, 28, 38, 44.5];
const XW = -3.5, GATE_X = -11, LIFT = { x: 128, z: 24.75 };

const bays = [];
STRIPS.forEach((s, si) => {
  for (let i = 0; i < NB; i++) {
    const x = i * BW + BW / 2, z = (s.z0 + s.z1) / 2;
    let type = 'general';
    if (si === 1 && x > 72.9 && x < 81) type = 'oku';
    if (si === 0 && x < 8.1) type = 'closed';
    if (si === 5 && x > 81 && x < 97.2) type = 'moto';
    bays.push({ k: bays.length, si, i, x, z, face: s.face, aisleZ: s.face > 0 ? s.z1 + 3.25 : s.z0 - 3.25, type });
  }
});
const GEN = bays.filter((b) => b.type === 'general');
const NZ = GEN.length; // bays in the Priority Zone (whole LG level, OKU bays excluded: always open)
const dLift = (b) => Math.hypot(b.x - LIFT.x, b.z - LIFT.z);

// ---------------------------------------------------------------- the capacity story (one consistent ledger)
// 9:00  occupied 150 · protected 8  · walk-in 100
// 10:30 occupied 205 · protected 18 · walk-in 35
// 12:00 occupied 232 · protected 26 · walk-in 0   (booked car parks: 233 · 25 · 0)
const NPROT = 26;
const PROT = GEN.slice().sort((a, b) => dLift(a) - dLift(b)).slice(0, NPROT); // amber is drawn on the free bays nearest the lifts
const protSet = new Set(PROT.map((b) => b.k));
const OTHER = GEN.filter((b) => !protSet.has(b.k));
const r1 = rng(20261109);
OTHER.forEach((b) => (b.r = r1()));
OTHER.sort((a, b) => a.r - b.r);
const O9 = OTHER.slice(0, 150), ARR = OTHER.slice(150); // 82 free general bays at 9:00
O9.forEach((b) => (b.o9 = true));
bays.forEach((b) => { b.aT = Infinity; b.aT2 = Infinity; b.lT = Infinity; });
const pick = (list, f) => { const i = list.findIndex(f); return i < 0 ? list.splice(0, 1)[0] : list.splice(i, 1)[0]; };
// visible arrivals and departures on aisle 3, where the camera can see them
const arrPool = ARR.slice();
const A1 = pick(arrPool, (b) => b.aisleZ === 41.25 && b.x > 22 && b.x < 45);
const A2 = pick(arrPool, (b) => b.aisleZ === 41.25 && b.x > 50 && b.x < 70);
const A3 = pick(arrPool, (b) => b.aisleZ === 41.25 && b.x > 30 && b.x < 60);
const OPEN_TAG = pick(arrPool, (b) => b.aisleZ === 41.25 && b.x > 60 && b.x < 90);
const lvPool = O9.slice();
const L1 = pick(lvPool, (b) => b.aisleZ === 41.25 && b.x > 40 && b.x < 75);
const L2 = pick(lvPool, (b) => b.aisleZ === 41.25 && b.x > 15 && b.x < 40);
const LV = [L1, L2, ...lvPool.slice(10, 14)]; // 6 cars leave between 9:00 and 10:30
const ARR1 = [A1, A2, A3, OPEN_TAG, ...arrPool.slice(0, 57)]; // 61 arrive by 10:30
const ARR2 = arrPool.slice(57); // 21 arrive by 12:00
if (ARR1.length + ARR2.length !== 82) console.error('arrival split', ARR1.length, ARR2.length);
const spread = (list, a, b) => list.forEach((x, i) => (x.aT = lerp(a, b, (i + 0.5) / list.length)));
spread(ARR1.slice(4), 31.7, 36.6); spread(ARR2, 39.4, 41.3);
OPEN_TAG.aT = 36.2;
LV.slice(2).forEach((b, i) => (b.lT = 32.0 + i * 1.2));
LV.forEach((b, i) => (b.aT2 = lerp(39.5, 41.2, (i + 0.5) / LV.length))); // their bays refill by 12:00

const T_BOOK = PROT.find((b) => b.aisleZ === 41.25) || PROT[3];
T_BOOK.aT = 52.55;

function occ(b, t) {
  if (b.type !== 'general') return false;
  let o = !!b.o9;
  if (t >= b.lT) o = false;
  if (t >= b.aT || t >= b.aT2) o = true;
  return o;
}
// protected count over time (the rolling plan raises it as bookings build)
const STEP5 = Array.from({ length: 10 }, (_, i) => lerp(32.1, 36.5, i / 9));
const STEP6 = Array.from({ length: 9 }, (_, i) => lerp(39.6, 41.2, i / 8));
const NS0 = 38.9, NSD = 4.0, NS_REL = 2.5; // pitch cut: no-show beat inserted at world time 38.9
let GT = 0, REL = false, CLK15 = 0;
const NS_BAY = PROT[17];
const worldT = (t) => (t < NS0 ? t : t < NS0 + NSD ? NS0 : t - NSD);
const amberStart = PROT.map((_, j) => (j < 8 ? -1 : j < 18 ? STEP5[j - 8] : STEP6[j - 18]));
function protCount(t) {
  let p = 8 + STEP5.filter((x) => t >= x).length + STEP6.filter((x) => t >= x).length;
  if (REL) p -= 1;
  if (t >= T_BOOK.aT) p -= 1;
  return p;
}
function ledger(t) {
  let o = 0; GEN.forEach((b) => { if (occ(b, t)) o++; });
  const p = protCount(t);
  return { o, p, w: NZ - o - p };
}

// ---------------------------------------------------------------- paths
function mkPath(pts) {
  const segs = []; let L = 0;
  for (let i = 0; i < pts.length - 1; i++) { const [ax, az] = pts[i], [bx, bz] = pts[i + 1]; const len = Math.hypot(bx - ax, bz - az); if (len < 1e-3) continue; segs.push({ ax, az, bx, bz, len, L0: L }); L += len; }
  return { segs, L };
}
function rawAt(p, s) {
  s = clamp(s, 0, p.L);
  for (const g of p.segs) if (s <= g.L0 + g.len || g === p.segs[p.segs.length - 1]) { const u = g.len ? (s - g.L0) / g.len : 0; return [lerp(g.ax, g.bx, u), lerp(g.az, g.bz, u)]; }
}
function poseAt(p, s) {
  const r = 2.4, a = rawAt(p, s - r), b = rawAt(p, s + r), c = rawAt(p, s);
  const x = (a[0] + b[0] + c[0]) / 3, z = (a[1] + b[1] + c[1]) / 3;
  let dx = b[0] - a[0], dz = b[1] - a[1];
  if (Math.hypot(dx, dz) < 0.01) { const q = rawAt(p, s - 0.5); dx = c[0] - q[0]; dz = c[1] - q[1]; }
  return { x, z, h: Math.atan2(dx, dz) };
}
const X0 = -48;
const routeIn = (b) => b.aisleZ === 41.25 ? mkPath([[X0, 41.25], [b.x, 41.25], [b.x, b.z]]) : mkPath([[X0, 41.25], [XW, 41.25], [XW, b.aisleZ], [b.x, b.aisleZ], [b.x, b.z]]);
const routeOut = (b) => mkPath([[b.x, b.z], [b.x, b.aisleZ], [XW, b.aisleZ], [XW, 8.25], [X0, 8.25]]);
const P_AWAY = mkPath([[X0, 41.25], [-27, 41.25], [-29.5, 45.5], [-40, 58], [-50, 68]]);
const P_BOOK = routeIn(T_BOOK);
const S_STOP = -16.2 - X0; // booked car waits at the plate camera

const prog = (u) => 0.72 * u + 0.28 * (1 - Math.cos(Math.PI * u)) / 2;
const MOVERS = [
  { id: 'a1', p: routeIn(A1), t0: 31.6, t1: 34.6, bay: A1, col: '#e4e8ee' },
  { id: 'a2', p: routeIn(A2), t0: 33.0, t1: 36.2, bay: A2, col: '#23272e' },
  { id: 'a3', p: routeIn(A3), t0: 34.6, t1: 37.6, bay: A3, col: '#8e2330' },
  { id: 'l1', p: routeOut(L1), t0: 32.2, t1: 35.6, out: L1, col: '#9aa1aa' },
  { id: 'l2', p: routeOut(L2), t0: 35.2, t1: 38.4, out: L2, col: '#2a4f94' },
  { id: 'walk', p: P_AWAY, t0: 42.0, t1: 46.1, col: '#f2f4f7', away: true },
  { id: 'book', p: P_BOOK, t0: 46.2, t1: T_BOOK.aT, bay: T_BOOK, col: '#2f6fe0', booked: true },
];
MOVERS.forEach((m) => { if (m.bay) m.bay.aT = m.t1; if (m.out) m.out.lT = m.t0; });
window.STATS = { NZ, l9: ledger(30), l1030: ledger(38.9), l12: ledger(45), lbook: ledger(53) };
function moverS(m, t) {
  if (m.booked) {
    if (t < 47.7) return prog(seg(t, m.t0, 47.7)) * 0 + (1 - Math.pow(1 - seg(t, m.t0, 47.7), 2)) * S_STOP;
    if (t < 49.0) return S_STOP;
    return S_STOP + sm(seg(t, 49.0, m.t1)) * (m.p.L - S_STOP);
  }
  if (m.away) {
    const s1 = 19.0;
    if (t < 43.5) return (1 - Math.pow(1 - seg(t, m.t0, 43.5), 2)) * s1;
    if (t < 44.0) return s1;
    return s1 + Math.pow(seg(t, 44.0, m.t1), 1.6) * (m.p.L - s1);
  }
  return prog(seg(t, m.t0, m.t1)) * m.p.L;
}

// ---------------------------------------------------------------- three.js scene
const canvas = $('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(1920, 1080, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#06101f');
scene.fog = new THREE.Fog('#06101f', 160, 420);
const camera = new THREE.PerspectiveCamera(38, 16 / 9, 0.3, 900);
const hemi = new THREE.HemisphereLight(0xe6eeff, 0x1a2234, 1.25); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xffffff, 1.25); sun.position.set(50, 120, 70); scene.add(sun);
const sun2 = new THREE.DirectionalLight(0x8fb4ff, 0.45); sun2.position.set(-70, 60, -40); scene.add(sun2);

const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, metalness: 0.05, ...o });
const basic = (c, o = {}) => new THREE.MeshBasicMaterial({ color: c, ...o });
const box = (w, h, d, m, x, y, z) => { const me = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); me.position.set(x, y, z); scene.add(me); return me; };

// floor, ramps, walls
const floor = new THREE.Mesh(new THREE.PlaneGeometry(146, 58), mat('#3a404b', { roughness: 0.92 }));
floor.rotation.x = -Math.PI / 2; floor.position.set(60.5, 0, 24.75); scene.add(floor);
const rampM = mat('#454c58');
[[41.25], [8.25]].forEach(([z]) => { const r = new THREE.Mesh(new THREE.PlaneGeometry(40, 6.5), rampM); r.rotation.x = -Math.PI / 2; r.position.set(-33, 0.01, z); scene.add(r); });
const gr = new THREE.Mesh(new THREE.PlaneGeometry(6.5, 30).rotateX(-Math.PI / 2), rampM); gr.rotation.y = Math.atan2(-16, 18); gr.position.set(-36, 0.012, 54); scene.add(gr);
const wallM = mat('#6d7584', { transparent: true, opacity: 0.8 });
const WH = 1.4;
box(135.5, WH, 0.4, wallM, 60.5, WH / 2, -0.2);
box(135.5, WH, 0.4, wallM, 60.5, WH / 2, 49.7);
[[0, 5], [11.5, 38], [44.5, 49.5]].forEach(([a, b]) => box(0.4, WH, b - a, wallM, -7.2, WH / 2, (a + b) / 2));
[[0, 16.5], [33, 49.5]].forEach(([a, b]) => box(0.4, WH, b - a, wallM, 128.2, WH / 2, (a + b) / 2));
box(8, 2.6, 0.3, mat('#7a818c'), 4, 1.3, 0.3);
box(6, 3, 16.5, mat('#2f7bff', { transparent: true, opacity: 0.6, emissive: '#1d4fb0', emissiveIntensity: 0.7 }), 131.4, 1.5, 24.75);

// ceiling + light strips (only for the ground-level opening shot)
const ceilM = basic('#8f8a80', { transparent: true, opacity: 1, side: THREE.DoubleSide });
const ceil = new THREE.Mesh(new THREE.PlaneGeometry(146, 58), ceilM); ceil.rotation.x = Math.PI / 2; ceil.position.set(60.5, 3.3, 24.75); scene.add(ceil);
const stripM = basic('#ffffff', { transparent: true, opacity: 1 });
const stripGeo = new THREE.BoxGeometry(3.2, 0.06, 0.22);
const lightStrips = new THREE.InstancedMesh(stripGeo, stripM, 66);
const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v3 = new THREE.Vector3(), sc3 = new THREE.Vector3(1, 1, 1), YAX = V(0, 1, 0);
{ let n = 0; AISLE.forEach((z) => { for (let x = -2; x < 126 && n < 66; x += 6) { m4.makeTranslation(x, 3.2, z + 1.2); lightStrips.setMatrixAt(n++, m4); } }); lightStrips.count = n; }
scene.add(lightStrips);
const ceilLight = new THREE.PointLight(0xfff4e0, 0, 60, 1.6); scene.add(ceilLight);

// bay tiles
const tileGeo = new THREE.PlaneGeometry(BW - 0.2, 4.8); tileGeo.rotateX(-Math.PI / 2);
const tiles = new THREE.InstancedMesh(tileGeo, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.92 }), bays.length);
bays.forEach((b, k) => { m4.makeTranslation(b.x, 0.02, b.z); tiles.setMatrixAt(k, m4); tiles.setColorAt(k, new THREE.Color('#3a404b')); });
scene.add(tiles);
const lineGeo = new THREE.BoxGeometry(0.12, 0.03, 5);
const lines = new THREE.InstancedMesh(lineGeo, basic('#e2b42c'), STRIPS.length * (NB + 1));
{ let li = 0; STRIPS.forEach((s) => { for (let i = 0; i <= NB; i++) { m4.makeTranslation(i * BW, 0.03, (s.z0 + s.z1) / 2); lines.setMatrixAt(li++, m4); } }); }
scene.add(lines);
const dashM = basic('#e2b42c', { transparent: true, opacity: 0.55 });
AISLE.forEach((z) => { for (let x = 4; x < 120; x += 9) box(2.2, 0.02, 0.18, dashM, x, 0.03, z); });
// zone outline (cyan glow)
const zoneM = basic('#5fd4ff', { transparent: true, opacity: 0 });
[[-1, 122.5, -0.9], [-1, 122.5, 50.4]].forEach(([a, b, z]) => box(b - a, 0.08, 0.35, zoneM, (a + b) / 2, 0.08, z));
[[-1], [122.5]].forEach(([x]) => box(0.35, 0.08, 51.3, zoneM, x, 0.08, 24.75));

// pillars + labels
const pillars = [];
COLS.forEach((c, ci) => ROWZ.forEach((z, ri) => pillars.push({ ci, x: ci * SP, z, label: c, num: ri + 2, face: ri % 2 === 0 ? 1 : -1 })));
const pLow = new THREE.InstancedMesh(new THREE.BoxGeometry(0.9, 1.2, 0.9).translate(0, 0.6, 0), mat('#f1ede4'), pillars.length);
const pHigh = new THREE.InstancedMesh(new THREE.BoxGeometry(0.9, 2.1, 0.9).translate(0, 2.25, 0), mat('#dccaa9'), pillars.length);
pillars.forEach((p, k) => { m4.makeTranslation(p.x, 0, p.z); pLow.setMatrixAt(k, m4); pHigh.setMatrixAt(k, m4); });
scene.add(pLow, pHigh);
function labelTex(letter, num) {
  const cv = document.createElement('canvas'); cv.width = 96; cv.height = 192; const g = cv.getContext('2d');
  g.fillStyle = '#dccaa9'; g.fillRect(0, 0, 96, 192); g.fillStyle = '#4c5a70'; g.textAlign = 'center';
  g.font = 'bold 74px "Barlow Condensed", sans-serif'; g.fillText(letter, 48, 74);
  g.font = 'bold 58px "Barlow Condensed", sans-serif'; g.fillText(String(num), 48, 140);
  g.font = '600 22px Inter, sans-serif'; g.fillText('LG', 48, 178);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function buildLabels() {
  const geo = new THREE.PlaneGeometry(0.8, 1.6);
  pillars.forEach((p) => { const me = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: labelTex(p.label, p.num) })); me.position.set(p.x, 2.25, p.z + p.face * 0.47); if (p.face < 0) me.rotation.y = Math.PI; scene.add(me); });
}

// parked cars
const CAR_COLS = ['#e9e9ea', '#c8ccd2', '#9aa1aa', '#2b3038', '#1d2026', '#5e636b', '#8e2330', '#2a4f94', '#e9e9ea', '#c8ccd2', '#2b3038', '#6f7f8c', '#f2f2f0', '#3b4048'];
const bodyGeo = new THREE.BoxGeometry(1.8, 0.72, 4.35).translate(0, 0.52, 0);
const cabGeo = new THREE.BoxGeometry(1.5, 0.52, 2.1).translate(0, 1.12, -0.25);
const pBody = new THREE.InstancedMesh(bodyGeo, new THREE.MeshStandardMaterial({ roughness: 0.38, metalness: 0.45 }), bays.length);
const pCab = new THREE.InstancedMesh(cabGeo, new THREE.MeshStandardMaterial({ color: '#1b2230', roughness: 0.15, metalness: 0.7 }), bays.length);
const r3 = rng(5);
bays.forEach((b, k) => { b.col = CAR_COLS[Math.floor(r3() * CAR_COLS.length)]; b.jx = (r3() - 0.5) * 0.3; b.jz = (r3() - 0.5) * 0.35; b.jr = (r3() - 0.5) * 0.05; pBody.setColorAt(k, new THREE.Color(b.col)); });
L1.col && MOVERS[3] && (MOVERS[3].col = L1.col); MOVERS[4].col = L2.col;
scene.add(pBody, pCab);
function setParked(t) {
  bays.forEach((b, k) => {
    let s = 0, y = 0;
    if (occ(b, t)) {
      const at = Math.max(b.aT <= t ? b.aT : -1, b.aT2 <= t ? b.aT2 : -1);
      const moverDriven = MOVERS.some((m) => m.bay === b);
      s = at > 0 && !moverDriven ? sm((t - at) / 0.45) : 1;
      y = (1 - s) * 5;
    } else if (b.lT <= t && !MOVERS.some((m) => m.out === b)) {
      const u = seg(t, b.lT, b.lT + 0.4); s = 1 - sm(u); y = u * 4;
    }
    const h = b.face > 0 ? Math.PI : 0;
    const k2 = Math.max(s, 0.0001);
    m4.compose(v3.set(b.x + b.jx, y, b.z + b.jz), q.setFromAxisAngle(YAX, h + b.jr), sc3.set(k2, k2, k2));
    pBody.setMatrixAt(k, m4); pCab.setMatrixAt(k, m4);
  });
  pBody.instanceMatrix.needsUpdate = pCab.instanceMatrix.needsUpdate = true;
}
const motoM = mat('#4b5563');
for (let x = 82; x < 96.5; x += 1.15) box(0.55, 0.95, 1.9, motoM, x, 0.48, 47);

// gate, plate camera, LED
box(0.5, 1.2, 0.5, mat('#f59e0b'), GATE_X, 0.6, 44.9);
const armPivot = new THREE.Group(); armPivot.position.set(GATE_X, 1.1, 44.7); scene.add(armPivot);
const armM = new THREE.MeshStandardMaterial({ color: '#ffffff', emissive: '#ff4d5e', emissiveIntensity: 0.35 });
const arm = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.16, 6.2), armM); arm.position.set(0, 0, -3.1); armPivot.add(arm);
box(0.18, 3.2, 0.18, mat('#e5e7eb'), GATE_X - 4, 1.6, 37.6);
const lprBox = box(0.7, 0.45, 0.9, mat('#111827'), GATE_X - 4, 3.2, 37.9);
const lprLed = box(0.18, 0.18, 0.05, basic('#5fd4ff'), GATE_X - 4 + 0.36, 3.2, 38.36);
box(0.3, 5.4, 0.3, mat('#9aa3b2'), -21, 2.7, 35.2);
// plate-read beam
const beamGeo = new THREE.BufferGeometry();
beamGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(18), 3));
const beam = new THREE.Mesh(beamGeo, basic('#5fd4ff', { transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
scene.add(beam);
const plateGlow = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.3), basic('#9fe6ff', { transparent: true, opacity: 0, side: THREE.DoubleSide }));
scene.add(plateGlow);

// moving cars
function mkMover(m) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshStandardMaterial({ color: m.col, roughness: 0.32, metalness: 0.45, emissive: m.booked ? '#1d4fb0' : '#000000', emissiveIntensity: m.booked ? 0.45 : 0 }));
  const cab = new THREE.Mesh(cabGeo, new THREE.MeshStandardMaterial({ color: '#131a26', roughness: 0.15, metalness: 0.7 }));
  g.add(body, cab);
  [-0.6, 0.6].forEach((x) => { const hl = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.16, 0.05), basic('#fff8e0')); hl.position.set(x, 0.62, 2.18); g.add(hl); const tl = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.14, 0.05), basic('#ff3344')); tl.position.set(x, 0.66, -2.18); g.add(tl); });
  const beamF = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 9).rotateX(-Math.PI / 2).translate(0, 0.05, 6.6), basic('#fff6d8', { transparent: true, opacity: 0.12, depthWrite: false, blending: THREE.AdditiveBlending }));
  g.add(beamF);
  if (m.booked) {
    const ring = new THREE.Mesh(new THREE.RingGeometry(2.9, 3.5, 48).rotateX(-Math.PI / 2), basic('#5fd4ff', { transparent: true, opacity: 0.75, depthWrite: false }));
    ring.position.y = 0.06; g.add(ring); g.ring = ring;
    const pin = new THREE.Mesh(new THREE.ConeGeometry(0.9, 1.9, 4).rotateX(Math.PI), basic('#5fd4ff')); pin.position.y = 4.6; g.add(pin); g.pin = pin;
  }
  g.visible = false; scene.add(g); return g;
}
MOVERS.forEach((m) => (m.g = mkMover(m)));

// sprites
function mkSign(w, h, scale) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })); sp.scale.set(scale, scale * h / w, 1);
  sp.cv = cv; sp.tex = tex; sp.key = ''; sp.renderOrder = 5; scene.add(sp); return sp;
}
function drawSign(sp, key, fn) { if (sp.key === key) return; sp.key = key; const g = sp.cv.getContext('2d'); g.clearRect(0, 0, sp.cv.width, sp.cv.height); fn(g, sp.cv.width, sp.cv.height); sp.tex.needsUpdate = true; }
function rr(g, x, y, w, h, r, fill, stroke, lw = 6) { g.beginPath(); g.roundRect(x, y, w, h, r); g.fillStyle = fill; g.fill(); if (stroke) { g.lineWidth = lw; g.strokeStyle = stroke; g.stroke(); } }
const led = mkSign(640, 300, 10); led.position.set(-21, 7.6, 35.2);
const genSign = mkSign(520, 130, 10); genSign.position.set(-37, 3.2, 60);
function drawLed(open) {
  const closed = open <= 0;
  drawSign(led, closed ? 'c' : 'o' + open, (g, w, h) => {
    rr(g, 6, 6, w - 12, h - 12, 22, '#04070d', '#2a3446', 8);
    // dot-matrix texture
    g.fillStyle = 'rgba(255,255,255,.035)'; for (let y = 22; y < h - 16; y += 9) for (let x = 22; x < w - 16; x += 9) g.fillRect(x, y, 4, 4);
    const c = closed ? '#ff4d5e' : '#2fdc84';
    g.shadowColor = c; g.shadowBlur = 22; g.fillStyle = c; g.textAlign = 'center';
    g.font = '700 74px "Barlow Condensed"'; g.fillText(closed ? 'WALK-IN CLOSED' : 'WALK-IN OPEN', w / 2, 104);
    g.font = '700 108px "Barlow Condensed"'; g.fillText(closed ? '0' : String(open), w / 2, 206);
    g.shadowColor = '#5fd4ff'; g.shadowBlur = 14; g.fillStyle = '#8fdcff'; g.font = '700 40px "Barlow Condensed"'; g.fillText('BOOKINGS  ▸  ENTER', w / 2, 268);
  });
}
const drawGen = () => drawSign(genSign, 'g', (g, w, h) => { rr(g, 4, 4, w - 8, h - 8, 18, 'rgba(6,16,31,.92)', '#8ab8ff'); g.fillStyle = '#f4f8ff'; g.textAlign = 'center'; g.font = '700 56px "Barlow Condensed"'; g.fillText('GENERAL PARKING  ↘', w / 2, 84); });

// ---------------------------------------------------------------- camera
function orbit(tg, az, el, R) { return V(tg.x + R * Math.cos(el) * Math.sin(az), tg.y + R * Math.sin(el), tg.z + R * Math.cos(el) * Math.cos(az)); }
const KEYS = [ // [t, tx, tz, az, el, R]
  [8.0, 60, 25, -0.62, 0.92, 172], [17.6, 60, 25, -0.26, 0.92, 166],
  [20.6, 98, 26, -0.42, 0.8, 100], [23.9, 100, 26, -0.58, 0.78, 92],
  [25.8, 6, 36, -1.06, 0.6, 86], [31.0, 9, 36, -0.96, 0.62, 82],
  [32.6, 24, 36, -0.8, 0.78, 146], [38.8, 28, 36, -0.68, 0.78, 140],
  [40.3, 46, 28, -0.6, 0.86, 152], [41.9, 46, 28, -0.62, 0.86, 150],
  [43.1, -24, 47, -1.18, 0.52, 60], [45.9, -24, 47, -1.02, 0.52, 58],
  [46.8, -17, 39, -0.98, 0.5, 54], [49.0, -16, 39, -0.86, 0.5, 52],
];
const FOLLOW = [49.0, 52.9];
const tmpA = V(0, 0, 0);
function camFor(t) {
  let fov = 38;
  if (t < 8) {
    const gx = lerp(-1, 9, seg(t, 2.4, 4.4));
    const gPos = V(gx, 1.55, 41.25), gTg = V(gx + 40, 1.25, 40.2);
    const oTg = V(60, 0, 25), oPos = orbit(oTg, -0.62, 0.92, 172);
    const u = sm(seg(t, 4.2, 7.7)), uh = Math.pow(u, 0.75);
    const pos = V(lerp(gPos.x, oPos.x, u), lerp(gPos.y, oPos.y, uh), lerp(gPos.z, oPos.z, u));
    const tg = gTg.clone().lerp(oTg, sm(seg(t, 4.2, 6.6)));
    return [pos, tg, lerp(60, 38, u)];
  }
  if (t >= FOLLOW[0] && t < 54) {
    const m = MOVERS[6], a = poseAt(m.p, moverS(m, t));
    const car = V(a.x, 0, a.z), base = V(-16, 0, 39);
    const u = sm(seg(t, FOLLOW[0], FOLLOW[0] + 1.2));
    const tg = base.clone().lerp(car, u);
    const R = lerp(52, 76, sm(seg(t, 49.4, 52.9))), el = lerp(0.5, 0.78, sm(seg(t, 49.4, 52.9))), az = lerp(-0.86, -0.62, seg(t, 49, 54));
    return [orbit(tg, az, el, R), tg, fov];
  }
  if (t >= 54) {
    const tg0 = V(T_BOOK.x, 0, T_BOOK.z), tg1 = V(58, 0, 25), u = sm(seg(t, 54, 57.6));
    const tg = tg0.clone().lerp(tg1, u);
    return [orbit(tg, lerp(-0.62, -0.28, seg(t, 54, 60)), lerp(0.78, 1.16, u), lerp(74, 220, u)), tg, fov];
  }
  let i = KEYS.length - 1; for (let j = 0; j < KEYS.length - 1; j++) if (t < KEYS[j + 1][0]) { i = j; break; }
  const a = KEYS[i], b = KEYS[Math.min(i + 1, KEYS.length - 1)];
  const u = a === b ? 0 : sm((t - a[0]) / (b[0] - a[0]));
  const tg = V(lerp(a[1], b[1], u), 0, lerp(a[2], b[2], u));
  return [orbit(tg, lerp(a[3], b[3], u), lerp(a[4], b[4], u), lerp(a[5], b[5], u)), tg, fov];
}

// ---------------------------------------------------------------- tags anchored in 3D
const cen = (list) => { const c = V(0, 0, 0); list.forEach((b) => c.add(V(b.x, 0, b.z))); return c.multiplyScalar(1 / list.length); };
const moverPos = (id, t, y) => { const m = MOVERS.find((x) => x.id === id); const a = poseAt(m.p, moverS(m, t)); return V(a.x, y, a.z); };
const TAGS = [
  { t: 'ParkFlow Priority Zone', s: `LG level · ${NZ} bays`, w: () => V(62, 1, 25), on: [6.0, 7.95], c: '#5fd4ff' },
  { t: 'Protected for bookings', s: 'any free bay, not a fixed one', w: () => cen(PROT.slice(0, 8)).setY(1), on: [19.8, 23.9], c: '#ffb21f' },
  { t: 'Open to walk-ins', s: 'everything not protected', w: () => V(OPEN_TAG.x, 1, OPEN_TAG.z), on: [20.3, 23.9], c: '#2fdc84' },
  { t: 'Walk-in → general parking', s: 'zone full for walk-ins', w: (t) => moverPos('walk', t, 3.2), on: [43.3, 45.6], c: '#ff4d5e' },
  { t: 'BOOKING VERIFIED  ✓', s: 'VKL 8821 · plate read at the gate', w: () => V(-15.2, 4.2, 41.25), on: [48.1, 50.2], c: '#2fdc84', big: true },
  { t: 'Parked', s: 'any available bay in the zone', w: () => V(T_BOOK.x, 2.4, T_BOOK.z), on: [52.7, 54.3], c: '#8ab8ff' },
  { t: '', w: () => V(NS_BAY.x, 1.4, NS_BAY.z), on: [NS0 + 0.4, NS0 + NS_REL], c: '#ffb21f', beat: true, big: true,
    dyn: (gt) => { const r = Math.round(900 * (1 - sm(seg(gt, NS0 + 0.3, NS0 + NS_REL)))); return `Booking due 10:30 · not arrived<small>grace period: ${Math.floor(r / 60)}:${String(r % 60).padStart(2, '0')} left</small>`; } },
  { t: 'Released to walk-ins', s: 'no-show after 15 minutes', w: () => V(NS_BAY.x, 1.4, NS_BAY.z), on: [NS0 + NS_REL, NS0 + NSD + 0.2], c: '#2fdc84', beat: true, big: true },
];
const tagLayer = $('tags');
TAGS.forEach((g) => { const el = document.createElement('div'); el.className = g.big ? 'tag big' : 'tag'; el.style.color = g.c; el.innerHTML = `${g.t}${g.s ? `<small>${g.s}</small>` : ''}`; tagLayer.appendChild(el); g.el = el; });
function screenOf(w) { const p = w.clone().project(camera); return [(p.x + 1) / 2 * 1920, (1 - p.y) / 2 * 1080, p.z]; }
function placeTags(t) {
  TAGS.forEach((g) => {
    const tt = g.beat ? GT : t, o = win(tt, g.on[0], g.on[1], 0.35);
    if (o <= 0) { op(g.el, 0); return; }
    if (g.dyn) html(g.el, g.dyn(tt));
    const [x, y] = screenOf(g.w(t));
    g.el.style.left = x.toFixed(1) + 'px'; g.el.style.top = (y - 8).toFixed(1) + 'px'; op(g.el, o);
  });
}

// ---------------------------------------------------------------- per-frame 3D
const COL = { floor: new THREE.Color('#3a404b'), occ: new THREE.Color('#59616e'), free: new THREE.Color('#2fdc84'), prot: new THREE.Color('#ffb21f'), oku: new THREE.Color('#2f6fe0'), closed: new THREE.Color('#2a2f38'), white: new THREE.Color('#ffffff') };
const tc = new THREE.Color();
function update3D(t) {
  let [pos, tg, fov] = camFor(t);
  const bu = win(GT, NS0, NS0 + NSD, 0.9);
  if (bu > 0) { const btg = V(NS_BAY.x, 0, NS_BAY.z), bpos = orbit(btg, -0.5, 0.78, 66); pos = pos.clone().lerp(bpos, bu); tg = tg.clone().lerp(btg, bu); }
  camera.position.copy(pos); camera.lookAt(tg);
  if (camera.fov !== fov) { camera.fov = fov; camera.updateProjectionMatrix(); }
  const ce = 1 - sm(seg(t, 4.3, 5.6));
  ceil.visible = lightStrips.visible = ce > 0.001; ceilM.opacity = ce; stripM.opacity = ce;
  ceilLight.intensity = ce * 40; ceilLight.position.set(pos.x + 8, 3, pos.z);
  setParked(t);
  const SW0 = 18.6, tint = sm(seg(t, SW0, SW0 + 1.6));
  const P = protCount(t);
  const freeProt = PROT.filter((b) => !occ(b, t));
  const amber = new Map(); freeProt.slice(0, P).forEach((b) => amber.set(b.k, amberStart[PROT.indexOf(b)]));
  const sweepX = t >= SW0 && t < SW0 + 1.5 ? (t - SW0) / 1.2 * 125 : t >= 54.4 && t < 56.8 ? lerp(-10, 135, seg(t, 54.4, 56.6)) : -999;
  const pulse = 0.88 + 0.12 * Math.sin(t * 5);
  bays.forEach((b, k) => {
    let c;
    if (b.type === 'oku') c = tc.copy(COL.floor).lerp(COL.oku, 0.85);
    else if (b.type === 'closed' || b.type === 'moto') c = COL.closed;
    else {
      const taken = occ(b, t) || MOVERS.some((m) => m.out === b && t < m.t0);
      let target = COL.free;
      if (taken) target = COL.occ;
      else if (amber.has(b.k)) {
        target = tc.copy(COL.prot).multiplyScalar(pulse);
        const f = 1 - seg(t, amber.get(b.k), amber.get(b.k) + 0.7);
        if (f > 0 && f < 1) target = tc.clone().lerp(COL.white, f * 0.8);
      }
      c = (target === tc ? tc.clone() : target.clone());
      const tb = sm(seg(t, SW0 + b.x / 125 * 1.2, SW0 + b.x / 125 * 1.2 + 0.4));
      c = COL.floor.clone().lerp(c, tb * (taken ? 0.9 : 0.85));
      if (b === NS_BAY && GT >= NS0 + NS_REL - 0.05 && GT < NS0 + NS_REL + 0.9) c = c.clone().lerp(COL.white, (1 - seg(GT, NS0 + NS_REL, NS0 + NS_REL + 0.9)) * 0.85);
    }
    if (sweepX > -900) { const d = Math.abs(b.x - sweepX); if (d < 9) c = c.clone().lerp(COL.white, (1 - d / 9) * 0.55); }
    tiles.setColorAt(k, c);
  });
  tiles.instanceColor.needsUpdate = true;
  zoneM.opacity = Math.max(win(t, 5.6, 8.3, 0.6) * 0.95, win(t, 18.4, 24, 0.5) * 0.6, 0.18 * tint);
  // movers
  let gateAng = 0;
  MOVERS.forEach((m) => {
    const vis = t >= m.t0 - 0.01 && t < m.t1;
    m.g.visible = vis; if (!vis) return;
    const a = poseAt(m.p, moverS(m, t));
    m.g.position.set(a.x, 0, a.z); m.g.rotation.y = a.h;
    if (m.g.pin) { m.g.pin.position.y = 4.6 + Math.sin(t * 4) * 0.35; m.g.pin.rotation.y = t * 2; m.g.ring.material.opacity = 0.5 + 0.3 * Math.sin(t * 6); }
    if (m.bay && !m.booked) gateAng = Math.max(gateAng, sm((a.x + 21) / 3) * (1 - sm((a.x + 4) / 3)));
  });
  gateAng = Math.max(gateAng, sm(seg(t, 48.6, 49.15)) * (1 - sm(seg(t, 50.8, 51.4))));
  armPivot.rotation.x = gateAng * 1.4;
  armM.emissive.set(t >= 48.6 && t < 51.4 ? '#2fdc84' : '#ff4d5e');
  // plate read beam
  const sc = win(t, 47.75, 48.85, 0.2);
  beam.material.opacity = sc * (0.28 + 0.12 * Math.sin(t * 30));
  plateGlow.material.opacity = sc * 0.9;
  if (sc > 0) {
    const car = moverPos('book', t, 0), px = car.x + 2.2, cam = V(GATE_X - 4 + 0.3, 3.15, 38.3);
    const A = [px, 0.95, 40.6], B = [px, 0.35, 40.6], C = [px, 0.95, 41.9], D = [px, 0.35, 41.9];
    beamGeo.attributes.position.array.set([cam.x, cam.y, cam.z, ...A, ...C, cam.x, cam.y, cam.z, ...B, ...D]);
    beamGeo.attributes.position.needsUpdate = true;
    plateGlow.position.set(px + 0.02, 0.62, 41.25); plateGlow.rotation.y = Math.PI / 2;
  }
  lprLed.material.color.set(sc > 0 ? '#2fdc84' : '#5fd4ff');
  const L = ledger(t);
  led.visible = t >= 7 && t < 57.5; genSign.visible = t >= 39 && t < 47;
  drawLed(L.w);
  renderer.render(scene, camera);
  return L;
}

// ---------------------------------------------------------------- HTML: footage, phone, dashboard, forecast, timeline
const fbg = $('footbg'), ffg = $('footfg');
let footPromise = null;
function setFoot(t) {
  const k = clamp(Math.round(t * 30), 0, 119);
  const src = `foot/${String(k).padStart(5, '0')}.jpg`;
  if (ffg._src !== src) { ffg._src = src; ffg.src = src; fbg.src = src; footPromise = Promise.all([ffg.decode(), fbg.decode()]).catch(() => {}); }
}
// QR pass
{
  const r = rng(8821); let s = '';
  const fin = (x, y) => { s += `<rect x="${x}" y="${y}" width="7" height="7" fill="#0d1b33"/><rect x="${x + 1}" y="${y + 1}" width="5" height="5" fill="#fff"/><rect x="${x + 2}" y="${y + 2}" width="3" height="3" fill="#0d1b33"/>`; };
  for (let y = 0; y < 29; y++) for (let x = 0; x < 29; x++) {
    const inF = (x < 8 && y < 8) || (x > 20 && y < 8) || (x < 8 && y > 20);
    if (!inF && r() < 0.48) s += `<rect x="${x}" y="${y}" width="1" height="1" fill="#0d1b33"/>`;
  }
  fin(0, 0); fin(22, 0); fin(0, 22);
  s += `<rect x="11.5" y="11.5" width="6" height="6" rx="1.2" fill="#fff"/><rect x="12.3" y="12.3" width="4.4" height="4.4" rx="1" fill="#2f7bff"/><text x="14.5" y="16" font-size="3.6" font-weight="800" fill="#fff" text-anchor="middle" font-family="Inter">P</text>`;
  if ($('qr')) $('qr').innerHTML = s;
}
const SCR = [['p1', 8.0, 10.35], ['p2', 10.35, 12.55], ['p3', 12.55, 14.85], ['p4', 14.85, 18.3]];
const TAPS = [[9.85, 'b1'], [11.05, 'c12'], [12.0, 'b2'], [14.35, 'b3']];
function updatePhone(t) {
  op($('s-phone'), win(t, 8.0, 18.1, 0.5));
  if (t < 7.9 || t > 18.2) return;
  const e = sm(seg(t, 8.0, 8.9)), x = sm(seg(t, 17.4, 18.1));
  const ry = lerp(-28, -7, e) + lerp(0, 4, seg(t, 9, 17)) - x * 10, ty = lerp(70, 0, e) - x * 40, s = lerp(0.9, 1, e);
  $('phone').style.transform = `rotateY(${ry.toFixed(2)}deg) rotateX(${lerp(8, 2, e).toFixed(2)}deg) translateY(${ty.toFixed(1)}px) scale(${s.toFixed(3)})`;
  SCR.forEach(([id, a, b]) => {
    const o = Math.min(1, win(t, a, b + 0.25, 0.25) + (id === 'p1' && t < 8.3 ? 1 : 0));
    const el = $(id); op(el, o);
    const sl = (1 - sm(seg(t, a, a + 0.35))) * 40; el.style.transform = `translateX(${sl.toFixed(1)}px)`;
  });
  // booking button glow before the tap
  const gl = win(t, 9.0, 10.2, 0.3) * (0.5 + 0.5 * Math.sin(t * 9));
  $('b1').style.boxShadow = `0 10px 24px rgba(47,123,255,.35), 0 0 0 ${(gl * 10).toFixed(1)}px rgba(95,212,255,${(gl * 0.35).toFixed(2)})`;
  const tap = $('tap'), rip = $('ripple'); let to = 0, ro = 0;
  const pr = $('screen').getBoundingClientRect();
  TAPS.forEach(([tt, id]) => {
    const o = win(t, tt - 0.45, tt + 0.25, 0.15);
    const el = $(id);
    el.style.transform = t > tt - 0.08 && t < tt + 0.15 ? 'scale(.96)' : '';
    if (o > to) { to = o; const r = el.getBoundingClientRect(); const cx = r.left - pr.left + r.width / 2, cy = r.top - pr.top + r.height / 2; tap.style.left = cx + 'px'; tap.style.top = cy + 'px'; rip.style.left = cx + 'px'; rip.style.top = cy + 'px'; }
    const ru = seg(t, tt, tt + 0.5); if (ru > 0 && ru < 1) { ro = 1 - ru; rip.style.transform = `scale(${(1 + ru * 1.6).toFixed(2)})`; }
  });
  op(tap, to); op(rip, ro);
  $('c12').className = t >= 11.1 ? 'chip sel' : 'chip';
  op($('vchk'), sm(seg(t, 12.9, 13.3)));
  const k = sm(seg(t, 15.0, 15.45)); $('okc').style.transform = `scale(${(0.4 + 0.6 * k + Math.sin(k * Math.PI) * 0.15).toFixed(3)})`;
  ['f1', 'f2', 'f3'].forEach((id, i) => { const a = 13.0 + i * 0.5; op($(id), win(t, a, 17.6, 0.4)); $(id).style.transform = `translateX(${((1 - sm(seg(t, a, a + 0.5))) * 30).toFixed(1)}px)`; });
}

// clock (virtual minutes after 9:00)
function vmin(t) {
  if (t < 31.5) return 0;
  if (t < NS0) return 90 * sm(seg(t, 31.5, 36.6));
  if (t < 46) return 90 + 15 * CLK15 + 75 * sm(seg(t, 39.3, 41.4));
  return 180 + 3 * seg(t, 46, 54);
}
const hhmm = (m) => { const tot = 9 * 60 + Math.round(m); let h = Math.floor(tot / 60); const mm = tot % 60; const ap = h >= 12 ? 'PM' : 'AM'; if (h > 12) h -= 12; return [`${h}:${String(mm).padStart(2, '0')}`, ap]; };
// timeline 9:00–13:00
const TLW = 740, TLM = 240, tx = (m) => (m / TLM) * TLW;
{
  let s = '';
  for (let m = 0; m <= TLM; m += 15) s += `<i class="tick${m % 60 === 0 ? ' h' : ''}" style="left:${tx(m)}px"></i>`;
  ['9 AM', '10', '11', '12 PM', '1 PM'].forEach((l, i) => (s += `<span class="tlab" style="left:${tx(i * 60)}px">${l}</span>`));
  $('tlmarks').innerHTML = s;
}
const RES = [[105, 3, 25.7], [150, 5, 26.3], [135, 4, 34.4], [180, 8, 34.9], [210, 6, 35.4]];
$('tlres').innerHTML = RES.map(([m, n], i) => `<span class="res" id="rs${i}" style="left:${tx(m)}px;opacity:0">+${n}</span>`).join('');

// forecast chart
const TRUE = [[0, 150], [30, 163], [60, 183], [90, 205], [120, 219], [150, 228], [180, 232], [210, 252], [240, 257], [270, 252]];
const FA = [[0, 150], [30, 158], [60, 168], [90, 180], [120, 192], [150, 202], [180, 210]];
const FB = [[90, 205], [120, 221], [150, 236], [180, 250], [210, 256], [240, 257], [270, 252]];
const BA = { 60: 2, 90: 3, 120: 4, 150: 5 }, BB = { 90: 4, 120: 6, 150: 9, 180: 12, 210: 10, 240: 7 };
const ip = (arr, m) => { for (let i = 0; i < arr.length - 1; i++) if (m <= arr[i + 1][0]) return lerp(arr[i][1], arr[i + 1][1], (m - arr[i][0]) / (arr[i + 1][0] - arr[i][0])); return arr[arr.length - 1][1]; };
const FW = 426, FH = 210, PL = 40, PR = 10, PT = 12, PB = 28;
const fx = (m) => PL + (m / 270) * (FW - PL - PR), fy = (v) => PT + (1 - (v - 100) / 170) * (FH - PT - PB);
function line(arr, m0, m1, stroke, w, dash, o = 1) {
  const pts = []; for (let m = m0; m <= m1 + 0.01; m += 5) pts.push(`${fx(m).toFixed(1)},${fy(ip(arr, m)).toFixed(1)}`);
  return `<polyline points="${pts.join(' ')}" fill="none" stroke="${stroke}" stroke-width="${w}" ${dash ? `stroke-dasharray="${dash}"` : ''} opacity="${o}" stroke-linejoin="round" stroke-linecap="round"/>`;
}
function band(arr, m0, m1, o) {
  const up = [], dn = []; for (let m = m0; m <= m1 + 0.01; m += 5) { const v = ip(arr, m), e = 3 + (m - m0) * 0.07; up.push(`${fx(m).toFixed(1)},${fy(v + e).toFixed(1)}`); dn.unshift(`${fx(m).toFixed(1)},${fy(v - e).toFixed(1)}`); }
  return `<polygon points="${up.join(' ')} ${dn.join(' ')}" fill="rgba(95,212,255,${0.16 * o})"/>`;
}
function drawFC(t) {
  const m = vmin(t), up = sm(seg(t, 33.9, 34.7));
  const key = `${m.toFixed(1)}|${up.toFixed(2)}`;
  const svg = $('fcsvg'); if (svg._k === key) return; svg._k = key;
  let s = '';
  [150, 200, 250].forEach((v) => (s += `<line x1="${PL}" x2="${FW - PR}" y1="${fy(v)}" y2="${fy(v)}" stroke="rgba(160,196,255,.14)"/><text x="${PL - 8}" y="${fy(v) + 5}" fill="#7f93b3" font-size="13" text-anchor="end" font-family="Inter">${v}</text>`));
  s += `<line x1="${PL}" x2="${FW - PR}" y1="${fy(NZ)}" y2="${fy(NZ)}" stroke="#ff4d5e" stroke-dasharray="5 4" opacity=".8"/><text x="${FW - PR}" y="${fy(NZ) - 6}" fill="#ff8a95" font-size="12" text-anchor="end" font-family="Inter" font-weight="600">capacity ${NZ}</text>`;
  ['9', '10', '11', '12', '1'].forEach((l, i) => (s += `<text x="${fx(i * 60)}" y="${FH - 8}" fill="#7f93b3" font-size="13" text-anchor="middle" font-family="Inter">${l}</text>`));
  // bookings bars (amber), in the forecast window
  const bars = (B, o) => Object.entries(B).map(([mm, n]) => { mm = +mm; if (mm + 30 < m) return ''; const h = n * 5.2; return `<rect x="${fx(mm) + 3}" y="${FH - PB - h}" width="${fx(30) - fx(0) - 6}" height="${h}" rx="3" fill="#ffb21f" opacity="${0.75 * o}"/>`; }).join('');
  s += bars(BA, 1 - up) + bars(BB, up);
  // window shading
  s += `<rect x="${fx(m)}" y="${PT}" width="${Math.max(0, Math.min(fx(m + 180), FW - PR) - fx(m))}" height="${FH - PT - PB}" fill="rgba(47,123,255,.07)"/>`;
  if (up < 1) s += band(FA, 0, 180, 1 - up) + line(FA, 0, 180, '#5fd4ff', 3, '', 1 - up);
  if (up > 0) { s += line(FA, 0, 180, '#5fd4ff', 2, '4 5', 0.35 * up); s += band(FB, 90, 270, up) + line(FB, 90, 270, '#5fd4ff', 3.5, '', up); }
  if (m > 0) s += line(TRUE, 0, m, '#f4f8ff', 3.5, '');
  s += `<line x1="${fx(m)}" x2="${fx(m)}" y1="${PT}" y2="${FH - PB}" stroke="#f4f8ff" stroke-width="1.5" opacity=".6"/><circle cx="${fx(m)}" cy="${fy(ip(TRUE, m))}" r="5.5" fill="#fff"/>`;
  svg.innerHTML = s;
  txt($('fcupd'), up < 0.5 ? 'updated 9:00' : m < 89.5 ? 'updated just now' : 'updated 10:30');
}

// connectors forecast → protected row → LED
const linksSvg = $('links');
function drawLinks(t, ledXY) {
  const o = win(t, 34.0, 38.7, 0.4);
  if (o <= 0) { html(linksSvg, ''); return; }
  const fr = $('fc').getBoundingClientRect(), dr = $('dr1').getBoundingClientRect();
  const a = [fr.left, fr.top + 110], b = [dr.left, dr.top + dr.height / 2], c = [ledXY[0] + 90, ledXY[1]];
  const p1 = `M${a[0]} ${a[1]} C ${a[0] - 90} ${a[1]}, ${b[0] - 90} ${b[1]}, ${b[0]} ${b[1]}`;
  const p2 = `M${b[0]} ${b[1]} C ${b[0] - 260} ${b[1]}, ${c[0] + 260} ${c[1]}, ${c[0]} ${c[1]}`;
  const ph = ((t * 0.9) % 1) * 100;
  html(linksSvg, `<g opacity="${o.toFixed(3)}">
    <path d="${p1}" stroke="#5fd4ff" stroke-width="2.5" fill="none" stroke-dasharray="7 9" stroke-dashoffset="${-ph}"/>
    <path d="${p2}" stroke="#ffb21f" stroke-width="2.5" fill="none" stroke-dasharray="7 9" stroke-dashoffset="${-ph}"/>
    <circle cx="${c[0]}" cy="${c[1]}" r="9" fill="none" stroke="#ffb21f" stroke-width="2.5"/>
    <text x="${(b[0] + c[0]) / 2}" y="${Math.min(b[1], c[1]) + (Math.abs(b[1] - c[1]) / 2) - 14}" fill="#ffd27a" font-size="17" font-weight="700" font-family="Inter" text-anchor="middle">plan → protected bays → entrance sign</text></g>`);
}

const LABELS = [
  [4.5, 7.95, 'Reality to 3D', 'Existing parking.<br>Untapped potential.'],
  [8.9, 17.7, 'Book', 'Reserve before<br>you arrive.'],
  [18.7, 23.9, 'Allocate', 'One zone.<br>Smarter allocation.'],
  [24.7, 31.0, '9:00 AM', 'Forecasting<br>future demand.'],
  [31.7, 38.9, '10:30 AM', 'Forecast updated.<br>Capacity reallocated.'],
  [39.7, 46.0, '12:00 PM', 'Reservations<br>protected.'],
  [46.7, 53.9, 'Booked arrival', 'Seamless<br>priority access.'],
];
let lastL = { o: -1, p: -1, w: -1 }, chgP = -9;
function updateHTML(t, L) {
  // footage
  const fo = 1 - sm(seg(t, 2.5, 3.6));
  op($('foot'), fo); if (fo > 0) { setFoot(t); ffg.style.transform = `translateX(-50%) scale(${(1 + t * 0.012).toFixed(4)})`; }
  op($('brand'), Math.min(sm(seg(t, 3.4, 4.2)), 1 - sm(seg(t, 56.4, 57)))); op($('concept'), Math.min(sm(seg(t, 3.4, 4.2)), 1 - sm(seg(t, 56.4, 57))));
  op($('dim'), Math.max(win(t, 8.0, 18.1, 0.6) * 0.5, sm(seg(t, 55.8, 57)) * 0.3));
  canvas.style.filter = t > 8 && t < 18.2 ? `blur(${(win(t, 8.0, 18.1, 0.6) * 5).toFixed(2)}px)` : 'none';
  op($('vign'), 1);
  // label
  const inBeat = GT >= NS0 && GT < NS0 + NSD, lt = inBeat ? GT : t;
  const li = inBeat ? [NS0 + 0.15, NS0 + NSD, '10:45 AM', 'No-show?<br>Back to walk-ins.'] : LABELS.find(([a, b]) => t >= a && t < b);
  if (li) {
    const o = win(lt, li[0], li[1], 0.5); op($('label'), o);
    html($('lk'), li[2]); html($('lt'), li[3]);
    $('label').style.transform = `translateY(${((1 - sm(seg(lt, li[0], li[0] + 0.6))) * 18).toFixed(1)}px)`;
  } else op($('label'), 0);
  updatePhone(t);
  // dashboard
  op($('dash'), win(t, 18.4, 54.2, 0.5));
  if (t > 18 && t < 54.6) {
    if (L.p !== lastL.p) chgP = GT;
    txt($('dv0'), String(L.o)); txt($('dv1'), String(L.p)); txt($('dv2'), String(L.w)); txt($('dtot'), String(NZ));
    $('sk0').style.width = (L.o / NZ * 100).toFixed(2) + '%'; $('sk1').style.width = (L.p / NZ * 100).toFixed(2) + '%'; $('sk2').style.width = (L.w / NZ * 100).toFixed(2) + '%';
    const g1 = Math.max(0, 1 - (GT - chgP) / 0.6), pulse1 = t >= 32 && t < 41.4 ? g1 : 0;
    $('dr1').style.background = `rgba(255,178,31,${(0.08 + pulse1 * 0.25).toFixed(3)})`;
    $('dr2').style.background = L.w === 0 ? 'rgba(255,77,94,.16)' : 'transparent';
    $('dv2').style.color = L.w === 0 ? 'var(--red)' : 'var(--green)';
    op($('dnote'), 1);
  }
  lastL = L;
  // clock, timeline, forecast
  op($('clockbox'), win(t, 24.5, 54.2, 0.5));
  op($('tlapse'), inBeat ? 0 : Math.max(win(t, 31.6, 36.7, 0.3), win(t, 39.35, 41.5, 0.3)) * (0.75 + 0.25 * Math.sin(GT * 12)));
  op($('fc'), win(t, 24.6, 46.3, 0.5));
  if (t > 24 && t < 54.6) {
    const m = vmin(t), [hm, ap] = hhmm(m);
    html($('clock'), `${hm}<small>${ap} · Sat</small>`);
    $('tlnow').style.left = tx(m) + 'px'; $('tlfill').style.width = tx(m) + 'px';
    RES.forEach(([mm, , a], i) => { const el = $('rs' + i); op(el, sm(seg(t, a, a + 0.4)) * (mm < m - 5 ? 0.35 : 1)); el.style.transform = `translate(-50%,${((1 - sm(seg(t, a, a + 0.4))) * -14).toFixed(1)}px)`; });
    drawFC(t);
  }
  // end
  op($('end'), 0);
  if (t > 56) {
    $('logo').style.opacity = sm(seg(t, 57.0, 57.7)); $('logo').style.transform = `scale(${lerp(0.92, 1, sm(seg(t, 57.0, 58.2))).toFixed(3)})`;
    $('tag1').style.opacity = sm(seg(t, 57.6, 58.2)); $('tag2').style.opacity = sm(seg(t, 58.0, 58.6)); $('tag3').style.opacity = sm(seg(t, 58.3, 58.9));
    op($('shine'), win(t, 57.2, 58.6, 0.3)); $('shine').style.transform = `translateX(${lerp(-1400, 1400, seg(t, 57.2, 58.6)).toFixed(0)}px)`;
  }
  op($('fade'), 0);
}

// ---------------------------------------------------------------- entry
const ready = (async () => {
  await document.fonts.ready;
  await Promise.all(['700 50px "Barlow Condensed"', '600 22px Inter', '800 40px Inter'].map((f) => document.fonts.load(f)));
  buildLabels(); drawGen();
})();
window.seek = async (t) => {
  await ready;
  footPromise = null;
  GT = t; REL = t >= NS0 + NS_REL; CLK15 = sm(seg(t, NS0 + 0.3, NS0 + NS_REL));
  t = worldT(t);
  const L = update3D(t);
  updateHTML(t, L);
  placeTags(t);
  const [lx, ly] = screenOf(V(-21, 7.6, 35.2));
  drawLinks(t, [lx, ly]);
  if (footPromise) await footPromise;
  return true;
};
window.ready = ready;
window.plateRect = () => { const r = document.getElementById('platebig').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; };
