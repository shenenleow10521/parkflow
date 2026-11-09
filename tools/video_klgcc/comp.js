// ParkFlow × KLGCC Mall LG — video composition. window.seek(t) draws the frame at time t (seconds).
import * as THREE from './vendor/three.module.min.js';

const $ = (id) => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, u) => a + (b - a) * u;
const sm = (u) => { u = clamp(u); return u * u * (3 - 2 * u); };
const seg = (t, a, b) => clamp((t - a) / (b - a));
const win = (t, a, b, f = 0.45) => sm(seg(t, a, a + f)) * (1 - sm(seg(t, b - f, b)));
const op = (el, v) => { const s = v.toFixed(3); if (el._o !== s) { el.style.opacity = s; el._o = s; } };
const txt = (el, v) => { if (el._t !== v) { el.textContent = v; el._t = v; } };
const fmt = (sec) => `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, '0')}`;
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

// ---------------------------------------------------------------- layout (metres)
const COLS = ['D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U'];
const SP = 8.1, BW = 2.7;
const STRIPS = [{ z0: 0, z1: 5, face: 1 }, { z0: 11.5, z1: 16.5, face: -1 }, { z0: 16.5, z1: 21.5, face: 1 }, { z0: 28, z1: 33, face: -1 }, { z0: 33, z1: 38, face: 1 }, { z0: 44.5, z1: 49.5, face: -1 }];
const AISLE = [8.25, 24.75, 41.25];
const ROWZ = [5, 11.5, 21.5, 28, 38, 44.5];
const XW = -3.5, XE = 124.75, GATE_X = -11;
const NB = 45;

const bays = [];
STRIPS.forEach((s, si) => {
  for (let i = 0; i < NB; i++) {
    const x = i * BW + BW / 2, z = (s.z0 + s.z1) / 2;
    let type = 'general';
    if (si === 1 && x > 72.9 && x < 81) type = 'oku';
    if (si === 0 && x < 8.1) type = 'closed';
    if (si === 5 && x > 81 && x < 97.2) type = 'moto';
    const zone = si >= 1 && si <= 4 && i >= 35 && type === 'general';
    const pocket = si <= 1 && i >= 12 && i <= 33 && type === 'general';
    bays.push({ k: bays.length, si, i, x, z, face: s.face, aisleZ: s.face > 0 ? s.z1 + 3.25 : s.z0 - 3.25, type, zone, pocket });
  }
});
let n = 0; bays.forEach((b) => { if (b.type === 'general' || b.type === 'oku') b.id = `LG-R${String(++n).padStart(3, '0')}`; });
const B = (si, i) => bays[si * NB + i];
const T_RED = B(1, 16), T_GREEN = B(0, 14), T_PA = B(2, 42), T_PL = B(2, 43), T_REL = B(3, 38), T_APP = B(2, 41);

// occupancy snapshot at filming time ("before") and with ParkFlow running ("after")
const r1 = rng(20261109);
const occBefore = new Set();
bays.forEach((b) => {
  if (b.type === 'closed' || b.type === 'moto') return;
  let p = 0.955;
  if (b.pocket) p = 0.4;
  if (b.zone) p = 1;
  if (b.type === 'oku') p = 0.34;
  if (r1() < p) occBefore.add(b.k);
});
[T_RED, T_GREEN].forEach((b) => occBefore.delete(b.k));
occBefore.add(B(1, 28).k); occBefore.add(B(1, 27).k);
const occAfter = new Set(occBefore);
const zoneBays = bays.filter((b) => b.zone);
zoneBays.forEach((b) => occAfter.delete(b.k));
const r2 = rng(77);
const keep = new Set([T_PA, T_PL, T_REL, T_APP].map((b) => b.k));
const cand = zoneBays.filter((b) => !keep.has(b.k));
cand.sort(() => r2() - 0.5);
cand.slice(0, 22).forEach((b) => occAfter.add(b.k));
const zoneFreeOrder = [T_PA, T_PL, T_REL, T_APP, ...zoneBays.filter((b) => !occAfter.has(b.k) && !keep.has(b.k))];

const carBays = bays.filter((b) => b.type === 'general' || b.type === 'oku');
const freeIn = (occ, f) => carBays.filter((b) => !occ.has(b.k) && f(b)).length;
const STATS = {
  totalBays: carBays.length,
  freeBefore: freeIn(occBefore, () => true),
  pocketFree: freeIn(occBefore, (b) => b.pocket),
  aisleAfter: [0, 1, 2].map((a) => freeIn(occAfter, (b) => Math.floor(b.si / 2) === a && b.type === 'general' && !b.zone)),
  zoneFree: freeIn(occAfter, (b) => b.zone),
  occAfterPct: Math.round(100 * (1 - freeIn(occAfter, () => true) / carBays.length)),
};

// ---------------------------------------------------------------- paths
function mkPath(pts) {
  const segs = []; let L = 0;
  for (let i = 0; i < pts.length - 1; i++) { const [ax, az] = pts[i], [bx, bz] = pts[i + 1]; const len = Math.hypot(bx - ax, bz - az); segs.push({ ax, az, bx, bz, len, L0: L }); L += len; }
  return { segs, L };
}
function rawAt(p, s) {
  s = clamp(s, 0, p.L);
  for (const g of p.segs) if (s <= g.L0 + g.len || g === p.segs[p.segs.length - 1]) { const u = g.len ? (s - g.L0) / g.len : 0; return [lerp(g.ax, g.bx, u), lerp(g.az, g.bz, u)]; }
}
function poseAt(p, s) {
  const r = 2.2, a = rawAt(p, s - r), b = rawAt(p, s + r), c = rawAt(p, s);
  const x = (a[0] + b[0] + c[0]) / 3, z = (a[1] + b[1] + c[1]) / 3;
  let dx = b[0] - a[0], dz = b[1] - a[1];
  if (Math.hypot(dx, dz) < 0.01) { const q = rawAt(p, s - 0.5); dx = c[0] - q[0]; dz = c[1] - q[1]; }
  return { x, z, h: Math.atan2(dx, dz) };
}
const ENTRY = [[-30, 41.25], [-3.5, 41.25]];
const P_RED = mkPath([[-30, 41.25], [XE, 41.25], [XE, 24.75], [XW, 24.75], [XW, 41.25], [XE, 41.25], [XE, 24.75], [XW, 24.75], [XW, 8.25], [T_RED.x, 8.25], [T_RED.x, T_RED.z]]);
const toZone = (b) => mkPath([[-30, 41.25], [XE, 41.25], [XE, 24.75], [b.x, 24.75], [b.x, b.z]]);
const P_PA = toZone(T_PA), P_PL = toZone(T_PL), P_APP = toZone(T_APP);
const P_GREEN = mkPath([[-30, 41.25], [XW, 41.25], [XW, 8.25], [T_GREEN.x, 8.25], [T_GREEN.x, T_GREEN.z]]);
const P_WALK = mkPath([[40, 24.75], [T_REL.x, 24.75], [T_REL.x, T_REL.z]]);
const RAMP = 30 - 3.5; // ramp metres not counted as "in the car park"
STATS.redM = Math.round(P_RED.L - RAMP + 8); STATS.paM = Math.round(P_PA.L - RAMP + 8);
STATS.redSec = 400; STATS.paSec = Math.round(STATS.paM / 3.1);
window.STATS = STATS;

// mover schedule: [path, t0, t1, bay]
const prog = (u) => 0.75 * u + 0.25 * (1 - Math.cos(Math.PI * u)) / 2;
const MOVERS = {
  red: [[P_RED, 15.6, 29.4, T_RED, 30]],
  purple: [[P_PA, 31.3, 40.5, T_PA, 50], [P_PL, 67.5, 72.2, T_PL, 82], [P_APP, 137.2, 141.6, T_APP, 145]],
  green: [[P_GREEN, 32.2, 38.6, T_GREEN, 50], [P_WALK, 78.9, 81.6, T_REL, 82]],
};
const SCENE_RANGES = [[5, 50], [65, 82], [115, 145]];
function sceneOf(t) { return SCENE_RANGES.find(([a, b]) => t >= a && t < b); }
function moverState(name, t) {
  const sc = sceneOf(t); if (!sc) return null;
  for (const [p, t0, t1, bay, tEnd] of MOVERS[name]) {
    if (t0 < sc[0] || t0 >= sc[1]) continue;
    if (t < t0 - 0.01 || t >= tEnd) continue;
    const u = seg(t, t0, t1);
    return { p, s: prog(u) * p.L, u, bay, parked: u >= 1 };
  }
  return null;
}

// ---------------------------------------------------------------- three.js scene
const canvas = $('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#0a111c');
const camera = new THREE.PerspectiveCamera(38, 16 / 9, 0.5, 900);
scene.add(new THREE.HemisphereLight(0xdfe7f5, 0x202838, 1.35));
const sun = new THREE.DirectionalLight(0xffffff, 1.1); sun.position.set(40, 120, 80); scene.add(sun);
const sun2 = new THREE.DirectionalLight(0x9db8ff, 0.35); sun2.position.set(-60, 50, -40); scene.add(sun2);

const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, metalness: 0.05, ...o });
const basic = (c, o = {}) => new THREE.MeshBasicMaterial({ color: c, ...o });
const box = (w, h, d, m, x, y, z) => { const me = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); me.position.set(x, y, z); scene.add(me); return me; };

// floor, ramps, walls
const floor = new THREE.Mesh(new THREE.PlaneGeometry(146, 58), mat('#1c2637'));
floor.rotation.x = -Math.PI / 2; floor.position.set(60.5, 0, 24.75); scene.add(floor);
const rampM = mat('#26324a');
[[41.25], [8.25]].forEach(([z]) => { const r = new THREE.Mesh(new THREE.PlaneGeometry(26, 6.5), rampM); r.rotation.x = -Math.PI / 2; r.position.set(-26, 0.01, z); scene.add(r); });
const wallM = mat('#34445e', { transparent: true, opacity: 0.75 });
const WH = 1.4;
box(135.5, WH, 0.4, wallM, 60.5, WH / 2, -0.2);
box(135.5, WH, 0.4, wallM, 60.5, WH / 2, 49.7);
[[0, 5], [11.5, 38], [44.5, 49.5]].forEach(([a, b]) => box(0.4, WH, b - a, wallM, -7.2, WH / 2, (a + b) / 2));
[[0, 16.5], [33, 49.5]].forEach(([a, b]) => box(0.4, WH, b - a, wallM, 128.2, WH / 2, (a + b) / 2));
// shutter + closed area near D2
box(8, 2.6, 0.3, mat('#6b7280'), 4, 1.3, 0.3);
const tapeM = basic('#ff5a66');
for (let x = 0.4; x < 8.2; x += 1.9) box(0.12, 0.9, 0.12, tapeM, x, 0.45, 5.2);
box(8, 0.06, 0.06, basic('#ffffff'), 4, 0.8, 5.2);
// lift lobby
const lobby = box(6, 3, 16.5, mat('#2f6fe0', { transparent: true, opacity: 0.55, emissive: '#1d3f86', emissiveIntensity: 0.5 }), 131.4, 1.5, 24.75);

// bay tiles (instanced, coloured per state)
const tileGeo = new THREE.PlaneGeometry(BW - 0.18, 4.8); tileGeo.rotateX(-Math.PI / 2);
const tiles = new THREE.InstancedMesh(tileGeo, new THREE.MeshBasicMaterial({ color: 0xffffff }), bays.length);
const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v3 = new THREE.Vector3(), sc3 = new THREE.Vector3(1, 1, 1);
bays.forEach((b, k) => { m4.makeTranslation(b.x, 0.02, b.z); tiles.setMatrixAt(k, m4); tiles.setColorAt(k, new THREE.Color('#1c2637')); });
scene.add(tiles);
// yellow bay lines
const lineGeo = new THREE.BoxGeometry(0.12, 0.03, 5);
const lineCount = STRIPS.length * (NB + 1);
const lines = new THREE.InstancedMesh(lineGeo, basic('#d9a92a'), lineCount);
let li = 0;
STRIPS.forEach((s) => { for (let i = 0; i <= NB; i++) { m4.makeTranslation(i * BW, 0.03, (s.z0 + s.z1) / 2); lines.setMatrixAt(li++, m4); } });
scene.add(lines);
// aisle arrows (chevrons) and centre dashes
const dashM = basic('#d9a92a', { transparent: true, opacity: 0.55 });
AISLE.forEach((z) => { for (let x = 4; x < 120; x += 9) box(2.2, 0.02, 0.18, dashM, x, 0.03, z); });
// zone outline (fades in "after")
const zoneM = basic('#b48cff', { transparent: true, opacity: 0 });
const zx0 = 35 * BW, zx1 = NB * BW;
[[11.5, 21.5], [28, 38]].forEach(([a, b]) => {
  box(zx1 - zx0, 0.05, 0.3, zoneM, (zx0 + zx1) / 2, 0.06, a); box(zx1 - zx0, 0.05, 0.3, zoneM, (zx0 + zx1) / 2, 0.06, b);
  box(0.3, 0.05, b - a, zoneM, zx0, 0.06, (a + b) / 2); box(0.3, 0.05, b - a, zoneM, zx1, 0.06, (a + b) / 2);
});

// pillars (instanced) + labels
const pillars = [];
COLS.forEach((c, ci) => ROWZ.forEach((z, ri) => pillars.push({ ci, ri, x: ci * SP, z, label: c, num: ri + 2, face: ri % 2 === 0 ? 1 : -1 })));
const pLow = new THREE.InstancedMesh(new THREE.BoxGeometry(0.9, 1.2, 0.9).translate(0, 0.6, 0), mat('#ece8df'), pillars.length);
const pHigh = new THREE.InstancedMesh(new THREE.BoxGeometry(0.9, 1.9, 0.9).translate(0, 2.15, 0), mat('#d8c6a6'), pillars.length);
scene.add(pLow, pHigh);
function labelTex(letter, num) {
  const cv = document.createElement('canvas'); cv.width = 96; cv.height = 192; const g = cv.getContext('2d');
  g.fillStyle = '#d8c6a6'; g.fillRect(0, 0, 96, 192); g.fillStyle = '#56667d'; g.textAlign = 'center';
  g.font = 'bold 74px "Barlow Condensed", sans-serif'; g.fillText(letter, 48, 74);
  g.font = 'bold 58px "Barlow Condensed", sans-serif'; g.fillText(String(num), 48, 140);
  g.font = '600 22px "Barlow", sans-serif'; g.fillText('LG', 48, 178);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const labelGeo = new THREE.PlaneGeometry(0.8, 1.6);
const labels = [];
function buildLabels() {
  pillars.forEach((p) => {
    const me = new THREE.Mesh(labelGeo, new THREE.MeshBasicMaterial({ map: labelTex(p.label, p.num), transparent: true }));
    me.position.set(p.x, 2.2, p.z + p.face * 0.47); if (p.face < 0) me.rotation.y = Math.PI;
    scene.add(me); labels.push({ me, p });
  });
}
function setPillars(t) {
  const u = seg(t, 5.3, 11.5);
  pillars.forEach((p, k) => {
    const h = t < 5 ? 1 : sm((u * 1.6 - p.ci / 15 * 0.6) / 1);
    m4.compose(v3.set(p.x, 0, p.z), q.identity(), sc3.set(1, Math.max(h, 0.001), 1));
    pLow.setMatrixAt(k, m4); pHigh.setMatrixAt(k, m4);
  });
  pLow.instanceMatrix.needsUpdate = pHigh.instanceMatrix.needsUpdate = true;
  labels.forEach(({ me, p }) => { const h = t < 5 ? 1 : sm((u * 1.6 - p.ci / 15 * 0.6) / 1); me.visible = h > 0.98; });
}

// parked cars (instanced)
const CAR_COLS = ['#e9e9ea', '#c8ccd2', '#9aa1aa', '#2b3038', '#1d2026', '#5e636b', '#8e2330', '#2a4f94', '#e9e9ea', '#c8ccd2', '#2b3038', '#6f7f8c'];
const bodyGeo = new THREE.BoxGeometry(1.8, 0.75, 4.3).translate(0, 0.55, 0);
const cabGeo = new THREE.BoxGeometry(1.45, 0.5, 1.9).translate(0, 1.15, -0.2);
const pBody = new THREE.InstancedMesh(bodyGeo, new THREE.MeshStandardMaterial({ roughness: 0.45, metalness: 0.35 }), bays.length);
const pCab = new THREE.InstancedMesh(cabGeo, new THREE.MeshStandardMaterial({ color: '#56657a', roughness: 0.3, metalness: 0.4 }), bays.length);
const r3 = rng(5);
bays.forEach((b, k) => { b.col = CAR_COLS[Math.floor(r3() * CAR_COLS.length)]; b.jx = (r3() - 0.5) * 0.3; b.jz = (r3() - 0.5) * 0.4; b.jr = (r3() - 0.5) * 0.06; pBody.setColorAt(k, new THREE.Color(b.col)); });
scene.add(pBody, pCab);
let parkedKey = '';
function setParked(occ, key, buildU) {
  if (key === parkedKey && buildU === undefined) return; parkedKey = buildU === undefined ? key : '';
  bays.forEach((b, k) => {
    let s = occ.has(b.k) ? 1 : 0;
    if (s && buildU !== undefined) s = sm((buildU * 1.5 - (b.x / 122) * 0.5));
    const h = b.face > 0 ? Math.PI : 0;
    m4.compose(v3.set(b.x + b.jx, (1 - s) * 6, b.z + b.jz), q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), h + b.jr), sc3.set(s || 0.0001, s || 0.0001, s || 0.0001));
    pBody.setMatrixAt(k, m4); pCab.setMatrixAt(k, m4);
  });
  pBody.instanceMatrix.needsUpdate = pCab.instanceMatrix.needsUpdate = true;
}
// motorcycles
const motoM = mat('#4b5563');
for (let x = 82; x < 96.5; x += 1.15) box(0.55, 0.95, 1.9, motoM, x, 0.48, 47);

// gate + plate camera
const gateM = mat('#e5e7eb');
box(0.5, 1.2, 0.5, mat('#f59e0b'), GATE_X, 0.6, 44.9);
const armPivot = new THREE.Group(); armPivot.position.set(GATE_X, 1.1, 44.7); scene.add(armPivot);
const arm = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, 6.2), new THREE.MeshStandardMaterial({ color: '#ffffff', emissive: '#ff5a66', emissiveIntensity: 0.3 })); arm.position.set(0, 0, -3.1); armPivot.add(arm);
box(0.18, 3.2, 0.18, gateM, GATE_X - 4, 1.6, 37.6);
box(0.7, 0.45, 0.9, mat('#111827'), GATE_X - 4, 3.2, 37.9);

// moving cars
function mkMover(color, glow) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshStandardMaterial({ color, roughness: 0.35, metalness: 0.3, emissive: color, emissiveIntensity: 0.35 }));
  const cab = new THREE.Mesh(cabGeo, new THREE.MeshStandardMaterial({ color: '#141a24', roughness: 0.25, metalness: 0.6 }));
  const ring = new THREE.Mesh(new THREE.CircleGeometry(3.6, 40).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: glow, transparent: true, opacity: 0.35, depthWrite: false }));
  ring.position.y = 0.05;
  const pin = new THREE.Mesh(new THREE.ConeGeometry(1.1, 2.2, 4).rotateX(Math.PI), new THREE.MeshBasicMaterial({ color: glow }));
  pin.position.y = 5;
  g.add(body, cab, ring, pin); scene.add(g); g.visible = false; g.pin = pin; return g;
}
const MV = { red: mkMover('#e0343f', '#ff5a66'), purple: mkMover('#8b5cf6', '#b48cff'), green: mkMover('#2fc77a', '#34e58a') };
// trails (flat ribbons revealed with drawRange)
function mkTrail(p, color) {
  const step = 0.6, N = Math.floor(p.L / step) + 1, pos = new Float32Array(N * 6), idx = [];
  for (let i = 0; i < N; i++) {
    const a = poseAt(p, i * step), nx = Math.cos(a.h), nz = -Math.sin(a.h), w = 0.45;
    pos.set([a.x + nx * w, 0.08, a.z + nz * w, a.x - nx * w, 0.08, a.z - nz * w], i * 6);
    if (i < N - 1) { const o = i * 2; idx.push(o, o + 1, o + 2, o + 1, o + 3, o + 2); }
  }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setIndex(idx);
  const me = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthWrite: false }));
  me.visible = false; scene.add(me); me.step = step; return me;
}
const TRAILS = new Map();
[[P_RED, '#ff5a66'], [P_PA, '#b48cff'], [P_PL, '#b48cff'], [P_APP, '#b48cff'], [P_GREEN, '#34e58a'], [P_WALK, '#34e58a']].forEach(([p, c]) => TRAILS.set(p, mkTrail(p, c)));

// sprites (signs)
function mkSign(w, h, scale) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })); sp.scale.set(scale, scale * h / w, 1);
  sp.cv = cv; sp.tex = tex; sp.key = ''; scene.add(sp); sp.renderOrder = 5; return sp;
}
function drawSign(sp, key, fn) { if (sp.key === key) return; sp.key = key; const g = sp.cv.getContext('2d'); g.clearRect(0, 0, sp.cv.width, sp.cv.height); fn(g, sp.cv.width, sp.cv.height); sp.tex.needsUpdate = true; }
function rr(g, x, y, w, h, r, fill, stroke) { g.beginPath(); g.roundRect(x, y, w, h, r); g.fillStyle = fill; g.fill(); if (stroke) { g.lineWidth = 6; g.strokeStyle = stroke; g.stroke(); } }
const signEntry = mkSign(560, 300, 15); signEntry.position.set(4, 6.5, 47);
const signZone = mkSign(560, 240, 15); signZone.position.set(90, 7.5, 24.75);
const signLobby = mkSign(420, 120, 11); signLobby.position.set(131.4, 5.6, 24.75);
const drawLobby = () => drawSign(signLobby, 'x', (g, w, h) => { rr(g, 4, 4, w - 8, h - 8, 18, 'rgba(10,17,28,.9)', '#7ea8ff'); g.fillStyle = '#ebf0f6'; g.font = '700 54px "Barlow Condensed"'; g.textAlign = 'center'; g.fillText('LIFTS → MALL', w / 2, 80); });

// ---------------------------------------------------------------- camera rigs
const C0 = new THREE.Vector3(58, 0, 24.75);
function orbit(tg, az, el, R) { return [new THREE.Vector3(tg.x + R * Math.cos(el) * Math.sin(az), tg.y + R * Math.sin(el), tg.z + R * Math.cos(el) * Math.cos(az)), tg]; }
const V = (x, y, z) => new THREE.Vector3(x, y, z);
function moverPos(name, t, fb) { const m = moverState(name, t); if (!m) return fb; const a = poseAt(m.p, m.s); return V(a.x, 0, a.z); }
function camFor(t) {
  if (t < 5) return orbit(C0, lerp(-0.55, -0.32, t / 5), 0.66, 150);
  if (t < 15) { const u = sm(seg(t, 5, 15)); return orbit(V(50, 0, 27), lerp(-0.75, -0.5, u), lerp(0.9, 0.82, u), lerp(200, 172, u)); }
  if (t < 30) { const c = moverPos('red', t, V(-20, 0, 41)); return orbit(V(50, 0, 27).lerp(c, 0.25), lerp(-0.5, -0.42, seg(t, 15, 30)), 0.9, 168); }
  if (t < 50) return orbit(V(52, 0, 27), lerp(-0.42, -0.34, seg(t, 30, 50)), 0.92, 172);
  if (t < 65) return orbit(V(104, 0, 25), lerp(-0.75, -0.55, seg(t, 50, 65)), 0.62, 80);
  if (t < 82) {
    const gate = V(-8, 0, 40), car = moverPos('purple', t, gate), zone = V(108, 0, 26);
    let tg = gate.clone().lerp(car, sm(seg(t, 67.4, 69)));
    tg.lerp(zone, sm(seg(t, 71.3, 73.5)));
    const R = lerp(lerp(62, 92, sm(seg(t, 67.4, 69))), 82, sm(seg(t, 71.3, 73.5)));
    tg.z -= 6;
    return orbit(tg, lerp(-0.7, -0.4, seg(t, 65, 82)), 0.82, R);
  }
  if (t < 95) return orbit(V(70, 0, 25), lerp(0.25, 0.4, seg(t, 82, 95)), 0.95, 150);
  if (t < 115) return orbit(V(60, 0, 25), lerp(-0.3, -0.15, seg(t, 95, 115)), 1.1, 140);
  if (t < 145) {
    const base = V(48, 0, 27), car = moverPos('purple', t, V(-20, 0, 41));
    const tg = base.clone().lerp(car, 0.5 * sm(seg(t, 136.5, 138.5)));
    tg.lerp(V(108, 0, 26), sm(seg(t, 140.5, 142.5)));
    const R = lerp(178, 100, sm(seg(t, 136.5, 142.5)));
    return orbit(tg, lerp(-0.42, -0.5, seg(t, 115, 145)), lerp(0.92, 0.75, sm(seg(t, 136, 142))), R);
  }
  if (t < 170) return orbit(V(56, 0, 25), lerp(-0.45, -0.38, seg(t, 145, 170)), 0.95, 150);
  return orbit(C0, lerp(0.15, 0.35, seg(t, 170, 175)), 0.6, 150);
}
function rectFor(t) {
  if (t >= 5 && t < 50) return [566, 0, 1354, 1080];
  if (t >= 115 && t < 145) return [600, 0, 1320, 1080];
  if (t >= 145 && t < 170) return [292, 282, 956, 684];
  return [0, 0, 1920, 1080];
}
let rectKey = '';
function setRect(r) {
  const k = r.join(','); if (k === rectKey) return; rectKey = k;
  Object.assign(canvas.style, { left: r[0] + 'px', top: r[1] + 'px', width: r[2] + 'px', height: r[3] + 'px' });
  renderer.setSize(r[2], r[3], false); camera.aspect = r[2] / r[3]; camera.updateProjectionMatrix();
}

// ---------------------------------------------------------------- 3D anchored tags
const TAGS = [
  { id: 'a1', t: 'Aisle 1', w: V(14, 0.5, 8.25), on: [11, 30], c: '#ebf0f6' },
  { id: 'a2', t: 'Aisle 2', w: V(14, 0.5, 24.75), on: [11, 30], c: '#ebf0f6' },
  { id: 'a3', t: 'Aisle 3 · entrance', w: V(14, 0.5, 41.25), on: [11, 30], c: '#ebf0f6' },
  { id: 'pocket', t: `${STATS.pocketFree} bays free on aisle 1`, s: 'nothing at the entrance says so', w: V(62, 1, 8.25), on: [21.5, 30], c: '#34e58a' },
  { id: 'zone', t: 'Priority Zone · 40 bays', s: 'by the lift lobby, booked cars', w: V(112, 0.5, 38), on: [33, 44], c: '#b48cff' },
  { id: 'walkin', t: `Walk-in → aisle 1`, s: 'sent by the entrance sign', w: V(30, 1, 8.25), on: [36.5, 44], c: '#34e58a' },
  { id: 'lpr', t: 'VKL 8821  ✓ checked in', s: 'Booking PZ-0417 · plate read 2:28 pm', w: V(GATE_X, 3.5, 41.25), on: [66.4, 70.5], c: '#34e58a' },
  { id: 'parked', t: 'Parked in a zone bay', s: 'any free bay counts', w: V(T_PL.x, 2, T_PL.z), on: [72.3, 75], c: '#b48cff' },
  { id: 'rel', t: 'Released at 2:55 pm', s: 'walk-in takes the bay', w: V(T_REL.x, 2, T_REL.z), on: [78.6, 82], c: '#ffb21f' },
  { id: 'lpr2', t: 'VKL 8821  ✓ checked in', s: 'plate read at the gate', w: V(GATE_X, 3.5, 41.25), on: [137, 140], c: '#34e58a' },
];
const tagLayer = $('tags');
TAGS.forEach((g) => { const el = document.createElement('div'); el.className = 'tag'; el.style.color = g.c; el.style.borderColor = g.c; el.innerHTML = `${g.t}${g.s ? `<small>${g.s}</small>` : ''}`; tagLayer.appendChild(el); g.el = el; });
function placeTags(t, r) {
  TAGS.forEach((g) => {
    const o = win(t, g.on[0], g.on[1], 0.35);
    if (o <= 0) { op(g.el, 0); return; }
    const p = g.w.clone().project(camera);
    g.el.style.left = (r[0] + (p.x + 1) / 2 * r[2]).toFixed(1) + 'px';
    g.el.style.top = (r[1] + (1 - p.y) / 2 * r[3] - 6).toFixed(1) + 'px';
    op(g.el, o);
  });
}

// ---------------------------------------------------------------- per-frame 3D state
const COL = { floor: new THREE.Color('#1c2637'), occ: new THREE.Color('#6b2a36'), free: new THREE.Color('#2fd27f'), held: new THREE.Color('#a77cff'), oku: new THREE.Color('#2f6fe0'), closed: new THREE.Color('#353d4b') };
const tc = new THREE.Color();
function heldCount(t) {
  if (t < 50) return 9;
  if (t < 65) return 9 + [56.7, 58.2, 59.7, 61.2].filter((x) => t >= x).length;
  if (t < 82) return t >= 78.5 ? 11 : 12;
  if (t < 145) return 11;
  return 12;
}
function update3D(t) {
  setRect(rectFor(t));
  const [pos, tg] = camFor(t); camera.position.copy(pos); camera.lookAt(tg);
  setPillars(t);
  const after = t >= 30;
  const tint = t < 30 ? 0 : sm(seg(t, 30, 31.2));
  const occ = after ? occAfter : occBefore;
  if (t >= 5 && t < 15) setParked(occ, 'b', seg(t, 9, 14.5)); else setParked(occ, after ? 'a' : 'b');
  // which free zone bays show as held (purple)
  const H = heldCount(t), held = new Set(zoneFreeOrder.slice(0, H).map((b) => b.k));
  if (t >= 78.5 && t < 82) held.delete(T_REL.k);
  const moving = {};
  for (const name of ['red', 'purple', 'green']) {
    const m = moverState(name, t), g = MV[name];
    if (!m) { g.visible = false; continue; }
    const a = poseAt(m.p, m.s);
    g.visible = true; g.position.set(a.x, 0, a.z); g.rotation.y = a.h;
    g.pin.position.y = 5 + Math.sin(t * 4) * 0.4; g.pin.rotation.y = t * 2;
    moving[name] = m;
  }
  TRAILS.forEach((tr, p) => {
    const m = Object.values(moving).find((mm) => mm.p === p);
    if (!m) { tr.visible = false; return; }
    tr.visible = true; tr.geometry.setDrawRange(0, Math.floor(m.s / tr.step) * 6);
    tr.material.opacity = m.parked ? 0.85 * (1 - seg(t, MOVERS_END(p) + 1.5, MOVERS_END(p) + 3)) : 0.85;
  });
  const bDur = [[15, 17], [31, 34.6], [66.8, 68.6], [136.6, 138.4]];
  let ang = 0; bDur.forEach(([a, b]) => { ang = Math.max(ang, sm(seg(t, a, a + 0.5)) * (1 - sm(seg(t, b - 0.5, b)))); });
  armPivot.rotation.x = ang * 1.35;
  bays.forEach((b, k) => {
    let c = COL.floor;
    if (b.type === 'oku') c = COL.oku;
    else if (b.type === 'closed') c = COL.closed;
    else if (b.type === 'general') {
      const taken = occ.has(b.k) || Object.values(moving).some((m) => m.parked && m.bay === b);
      const target = taken ? COL.occ : held.has(b.k) ? COL.held : COL.free;
      tc.copy(COL.floor).lerp(target, tint * (taken ? 0.8 : 0.75)); c = tc;
    }
    tiles.setColorAt(k, c);
  });
  tiles.instanceColor.needsUpdate = true;
  zoneM.opacity = tint * 0.95;
  // signs
  signEntry.visible = after && t < 145; signZone.visible = after;
  const af = STATS.aisleAfter;
  drawSign(signEntry, 'e', (g, w, h) => {
    rr(g, 4, 4, w - 8, h - 8, 22, 'rgba(8,13,22,.94)', '#34e58a'); g.textAlign = 'left';
    g.fillStyle = '#34e58a'; g.font = '700 72px "Barlow Condensed"'; g.fillText(`LG  ${af[0] + af[1] + af[2]} FREE`, 30, 86);
    g.fillStyle = '#ebf0f6'; g.font = '600 46px "Barlow Condensed"'; g.fillText(`Aisle 1  →  ${af[0]} free`, 30, 154);
    g.fillStyle = '#c4a6ff'; g.fillText('Priority Zone: booked', 30, 214);
    g.fillStyle = '#8696ad'; g.font = '500 30px "Barlow"'; g.fillText('updated every minute', 30, 266);
  });
  const green = t >= 78.5 && t < 82;
  drawSign(signZone, green ? 'g' : 'a', (g, w, h) => {
    const c = green ? '#34e58a' : '#ffb21f';
    rr(g, 4, 4, w - 8, h - 8, 22, 'rgba(8,13,22,.94)', c); g.textAlign = 'center';
    g.fillStyle = '#c4a6ff'; g.font = '700 60px "Barlow Condensed"'; g.fillText('PRIORITY ZONE', w / 2, 80);
    g.fillStyle = c; g.font = '700 56px "Barlow Condensed"'; g.fillText(green ? 'WALK-INS WELCOME' : 'BOOKED CARS ONLY', w / 2, 152);
    g.fillStyle = '#8696ad'; g.font = '500 30px "Barlow"'; g.fillText(green ? '1 bay released' : 'walk-ins: follow aisle signs', w / 2, 204);
  });
  renderer.render(scene, camera);
}
function MOVERS_END(p) { for (const k in MOVERS) for (const [pp, , t1] of MOVERS[k]) if (pp === p) return t1; return 0; }

// ---------------------------------------------------------------- HTML scenes
const footImg = $('footimg');
let footPromise = null;
function setFoot(t) {
  const k = clamp(Math.round(t * 30), 150, 1499);
  const src = `foot/${String(k).padStart(5, '0')}.jpg`;
  if (footImg._src !== src) { footImg._src = src; footImg.src = src; footPromise = footImg.decode().catch(() => {}); }
}
const SC = ['title', 'ba', 'ledger', 'life', 'rules', 'ml', 'app', 'dash', 'end'].map((s) => $('s-' + s));
const SCT = [[0, 5], [5, 50], [50, 65], [65, 82], [82, 95], [95, 115], [115, 145], [145, 170], [170, 176]];
const CHAP = ['Intro', 'A · Before vs after', 'B · Booking mechanism', 'B · Booking mechanism', 'B · Booking mechanism', 'C · Machine learning', 'D · Member booking', 'E · Admin dashboard', 'ParkFlow'];

// ledger cells
const cells = $('cells'); for (let i = 0; i < 40; i++) cells.appendChild(document.createElement('i'));
const dcells = $('dcells');
for (let i = 0; i < 40; i++) { const c = document.createElement('i'); c.style.cssText = 'display:block;height:22px;border-radius:4px;background:' + (i < 24 ? '#5b6578' : i < 32 ? '#b48cff' : i < 36 ? '#ffb21f' : '#34e58a'); dcells.appendChild(c); }
const REQS = [['Gold member', 'VKL 8821 · 2:30 pm', 1], ['Care booking · OKU', 'WTA 3307 · 2:30 pm', 1], ['Platinum member', 'BME 5593 · 2:30 pm', 1], ['Paid · RM4', 'VFF 1248 · 2:30 pm', 1], ['Member', 'PKA 9062 · 2:30 pm', 0]];
const REQT = [56.2, 57.7, 59.2, 60.7, 62.2];
const reqEls = REQS.map(([w, d, ok], i) => {
  const el = document.createElement('div'); el.className = 'req';
  el.innerHTML = `<div><div class="who">${w}</div><div class="muted">${d}</div></div><div class="res ${ok ? 'ok' : 'no'}">${ok ? `✓ Accepted · ${3 - i} left` : 'Full → offer 2:45 pm'}</div>`;
  $('reqs').appendChild(el); return el;
});
// app dots
const APP = [[115, 'a1', 'See live space'], [119.5, 'a2', 'Pick an arrival time'], [124, 'a3', 'Membership & voucher'], [128.5, 'a4', 'Booking confirmed'], [132.5, 'a5', 'On the way'], [137, 'a6', 'Plate check-in'], [141, 'a7', 'Parked by the lifts']];
APP.forEach(([, , l], i) => { const d = document.createElement('div'); d.innerHTML = `<i>${i + 1}</i>${l}`; $('appdots').appendChild(d); });
const TAPS = [[118.8, 'a1btn'], [121.5, 'slot230'], [123.3, 'a2btn'], [127.8, 'a3btn'], [131.8, 'a4btn']];
// camera health table
const CAMS = [['LG-D2', 98.9], ['LG-J7', 99.2], ['LG-L5', 98.7], ['LG-N3', 88.4], ['LG-R4', 99.0], ['LG-U3', 98.8], ['Gate in · plate', 99.6], ['Gate out · plate', 99.4]];
$('camtab').innerHTML = CAMS.map(([c, v]) => {
  const bad = v < 95, r = rng(c.length * 13 + v * 10);
  const bars = Array.from({ length: 14 }, (_, i) => { const y = bad ? lerp(97, v, i / 13) + r() * 0.6 : v + (r() - 0.5) * 0.6; const h = clamp((y - 85) / 15) * 30; return `<rect x="${i * 9}" y="${32 - h}" width="6" height="${h}" fill="${bad && i > 9 ? '#ffb21f' : '#2f6fe0'}"/>`; }).join('');
  return `<tr><td style="font-family:var(--semi);font-weight:700">${c}</td><td><svg width="126" height="32">${bars}</svg></td><td style="font-family:var(--cond);font-weight:700;font-size:26px">${v.toFixed(1)}%</td><td class="st" style="color:${bad ? 'var(--wait)' : 'var(--free)'}">${bad ? 'Check lens' : 'OK'}</td></tr>`;
}).join('');
// charts (backtest day, public data)
const BT = [['09:00', .584, .613, .586, .64], ['09:30', .704, .77, .743, .797], ['10:00', .754, .782, .755, .808], ['10:30', .816, .854, .827, .881], ['11:00', .846, .866, .839, .893], ['12:00', .87, .894, .868, .921], ['13:00', .91, .896, .869, .923], ['13:30', .906, .888, .861, .915], ['14:00', .91, .904, .877, .931], ['14:30', .892, .885, .858, .912], ['15:00', .874, .862, .835, .889], ['15:30', .868, .829, .802, .856], ['16:00', .824, .789, .762, .815], ['16:30', .73, .747, .721, .774]];
const hrs = (s) => +s.slice(0, 2) + +s.slice(3) / 60;
function chart(svg, W, H, pad, labels) {
  const X = (s) => pad[3] + (hrs(s) - 9) / 7.5 * (W - pad[1] - pad[3]), Y = (v) => pad[0] + (1 - (v - 0.5) / 0.5) * (H - pad[0] - pad[2]);
  const band = BT.map((r) => `${X(r[0])},${Y(r[4])}`).join(' ') + ' ' + BT.slice().reverse().map((r) => `${X(r[0])},${Y(r[3])}`).join(' ');
  let s = `<polygon points="${band}" fill="rgba(126,168,255,.22)"/>`;
  s += `<polyline points="${BT.map((r) => `${X(r[0])},${Y(r[2])}`).join(' ')}" fill="none" stroke="#7ea8ff" stroke-width="3" stroke-dasharray="7 5"/>`;
  s += `<polyline points="${BT.map((r) => `${X(r[0])},${Y(r[1])}`).join(' ')}" fill="none" stroke="#ebf0f6" stroke-width="3.5"/>`;
  if (labels) {
    [0.6, 0.8, 1.0].forEach((v) => { s += `<text x="${pad[3] - 10}" y="${Y(v) + 6}" fill="#8696ad" font-size="16" text-anchor="end" font-family="Barlow">${v * 100}%</text><line x1="${pad[3]}" x2="${W - pad[1]}" y1="${Y(v)}" y2="${Y(v)}" stroke="#22324a"/>`; });
    ['10:00', '12:00', '14:00', '16:00'].forEach((h) => { s += `<text x="${X(h)}" y="${H - 8}" fill="#8696ad" font-size="16" text-anchor="middle" font-family="Barlow">${h}</text>`; });
    BT.forEach((r) => { s += `<circle cx="${X(r[0])}" cy="${Y(r[1])}" r="4.5" fill="#34e58a"/>`; });
  }
  s += `<text x="${W - pad[1]}" y="${pad[0] + 4}" fill="#ebf0f6" font-size="17" text-anchor="end" font-family="Barlow">— actual   <tspan fill="#7ea8ff">- - forecast, 80% range</tspan></text>`;
  svg.innerHTML = s;
}
chart($('mlsvg'), 716, 170, [20, 10, 10, 10], false);
chart($('dsvg'), 960, 470, [30, 20, 34, 60], true);
$('dsvg').insertAdjacentHTML('beforeend', '<text x="60" y="465" fill="#8696ad" font-size="15" font-family="Barlow">Backtest day on public car-park data. Green dots: logged outcomes the model is scored on.</text>');
// ML connectors
const pipe = $('pipesvg');
const CON = [[300, 40, 420, 60], [300, 150, 420, 80], [300, 150, 420, 270], [300, 260, 420, 290], [300, 370, 420, 310], [655, 150, 655, 220], [890, 290, 1010, 180], [890, 60, 1010, 160], [1370, 170, 1470, 40], [1370, 180, 1470, 180], [1370, 190, 1470, 320]];
pipe.innerHTML = CON.map(([x1, y1, x2, y2], i) => {
  const d = x1 === x2 ? `M${x1} ${y1 + 10} L${x2} ${y2 - 10}` : `M${x1} ${y1} C ${x1 + 60} ${y1}, ${x2 - 60} ${y2}, ${x2} ${y2}`;
  return `<path id="cp${i}" d="${d}" stroke="#2f4360" stroke-width="3" fill="none"/><circle id="cd${i}" r="6" fill="#7ea8ff" opacity="0"/>`;
}).join('');
const conPaths = CON.map((_, i) => $('cp' + i)), conDots = CON.map((_, i) => $('cd' + i));
document.querySelectorAll('.pocketN').forEach((e) => (e.textContent = STATS.aisleAfter[0]));
document.querySelectorAll('.pocketTot').forEach((e) => (e.textContent = `${STATS.aisleAfter.reduce((a, b) => a + b)} free`));
$('nbays').textContent = STATS.totalBays;
$('a7bay').textContent = `${T_APP.id} · by the lift lobby`;
$('k-occ').textContent = STATS.occAfterPct + '%';
$('cmpT0').textContent = fmt(STATS.redSec); $('cmpT1').textContent = fmt(STATS.paSec);
$('cmpD0').textContent = STATS.redM + ' m'; $('cmpD1').textContent = STATS.paM + ' m';
$('cmpC0').textContent = Math.round(STATS.redM * 0.18) + ' g'; $('cmpC1').textContent = Math.round(STATS.paM * 0.18) + ' g';

function updateHTML(t) {
  SC.forEach((el, i) => op(el, win(t, SCT[i][0], SCT[i][1], 0.4)));
  const si = SCT.findIndex(([a, b]) => t >= a && t < b); txt($('chapter'), CHAP[Math.max(si, 0)]);
  const fades = [5, 50, 65, 82, 95, 115, 145, 170];
  let f = Math.max(1 - seg(t, 0, 0.6), seg(t, 174.2, 175));
  fades.forEach((b) => { f = Math.max(f, 0.85 * (1 - Math.abs(t - b) / 0.32)); });
  op($('fade'), clamp(f));
  const dims = [[0, 5, 0.45], [50, 65, 0.86], [82, 95, 0.84], [95, 115, 0.9], [170, 176, 0.6]];
  op($('dim'), dims.reduce((m, [a, b, v]) => Math.max(m, win(t, a, b, 0.4) * v), 0));
  $('foot').style.opacity = t >= 145 && t < 170 ? 0 : 1; $('brand').style.opacity = t >= 145 && t < 170 ? 0 : 1;

  if (t >= 5 && t < 50) {
    setFoot(t);
    txt($('speed'), t < 15 ? '3× speed' : t < 30 ? '5× speed' : '3× speed');
    const fb = $('footbadge');
    if (t < 15) { txt(fb, 'Walkthrough · 9 Nov 2026'); fb.style.background = 'rgba(47,111,224,.88)'; }
    else if (t < 30) { txt(fb, 'BEFORE · no free-bay information'); fb.style.background = 'rgba(200,40,55,.9)'; }
    else { txt(fb, 'AFTER · with ParkFlow'); fb.style.background = 'rgba(25,150,90,.92)'; }
    op($('foothud'), win(t, 32, 50, 0.4));
    const st = $('bastate'), sub = $('basub');
    if (t < 15) { txt(st, 'Digital twin'); st.style.color = 'var(--chalk)'; txt(sub, 'LG level · rebuilt from the walkthrough'); }
    else if (t < 30) { txt(st, 'Before'); st.style.color = 'var(--stop)'; txt(sub, 'Enters on aisle 3 · no idea where the space is'); }
    else { txt(st, 'After'); st.style.color = 'var(--free)'; txt(sub, 'Live free bays · Priority Zone by the lifts'); }
    document.querySelectorAll('#buildstats .st').forEach((e, i) => op(e, win(t, 7 + i * 1.2, 15, 0.4)));
    const ck = $('clock');
    if (t < 30) {
      op(ck, win(t, 15.5, 30, 0.4)); const m = moverState('red', t); const u = m ? m.u : 0;
      txt($('clocklab'), u >= 1 ? 'Found a bay after' : 'Searching'); $('clockval').style.color = 'var(--stop)';
      txt($('clockval'), fmt(u * STATS.redSec)); txt($('clockval2'), `${Math.round(u * STATS.redM)} m driven`);
    } else {
      op(ck, win(t, 31, 44, 0.4)); const m = moverState('purple', t); const u = m ? m.u : 0;
      txt($('clocklab'), u >= 1 ? 'Booked member · parked in' : 'Booked member · gate to bay'); $('clockval').style.color = 'var(--free)';
      txt($('clockval'), fmt(u * STATS.paSec)); txt($('clockval2'), `${Math.round(u * STATS.paM)} m driven`);
    }
    op($('compare'), win(t, 44, 50, 0.45));
  }
  if (t >= 50 && t < 65) {
    const acc = REQT.slice(0, 4).filter((x) => t >= x + 0.5).length;
    // parked 22 | booked 9+acc | forecast 5 | promise 4-acc
    [...cells.children].forEach((c, i) => {
      const cc = i < 22 ? '#5b6578' : i < 31 + acc ? '#b48cff' : i < 36 + acc ? '#ffb21f' : '#34e58a';
      if (c._c !== cc) { c.style.background = cc; c._c = cc; }
    });
    txt($('lg-b'), String(9 + acc)); txt($('lg-a'), String(4 - acc)); txt($('eqb'), String(9 + acc)); txt($('eqa'), String(4 - acc));
    reqEls.forEach((el, i) => { op(el, win(t, REQT[i], 65, 0.35)); op(el.lastChild, sm(seg(t, REQT[i] + 0.4, REQT[i] + 0.7))); });
    op($('guar'), win(t, 63, 65, 0.35));
  }
  if (t >= 65 && t < 82) {
    const ST = [65, 66, 67, 69, 73, 75, 82];
    document.querySelectorAll('#steps .step').forEach((el, i) => { const on = t >= ST[i] && t < ST[i + 1], done = t >= ST[i + 1]; const c = on ? 'step on' : done ? 'step done' : 'step'; if (el.className !== c) el.className = c; });
    op($('noshow'), win(t, 75, 82, 0.4));
    const mins = Math.round(lerp(41, 55, seg(t, 75.4, 78.4)));
    txt($('nsclock'), `2:${mins} pm`);
    txt($('nstext'), t >= 78.5 ? 'No-show: released to everyone' : 'Held until 2:55 pm');
    $('nstext').style.color = t >= 78.5 ? 'var(--wait)' : '';
  }
  if (t >= 82 && t < 95) {
    document.querySelectorAll('.price').forEach((e, i) => op(e, sm(seg(t, 83.2 + i * 0.9, 83.7 + i * 0.9))));
    document.querySelectorAll('.fr').forEach((e, i) => op(e, sm(seg(t, 88.2 + i * 0.7, 88.7 + i * 0.7))));
  }
  if (t >= 95 && t < 115) {
    const nodes = document.querySelectorAll('#pipe .node');
    const NT = [96, 96.3, 96.6, 96.9, 98, 98.6, 100.5, 101.5, 101.8, 102.1];
    nodes.forEach((e, i) => op(e, sm(seg(t, NT[i], NT[i] + 0.5))));
    conPaths.forEach((p, i) => {
      const t0 = i < 5 ? 97.6 : i < 7 ? 99.6 : i < 8 ? 100.6 : 101.6;
      const L = p.getTotalLength(), u = sm(seg(t, t0, t0 + 0.7));
      p.style.strokeDasharray = L; p.style.strokeDashoffset = L * (1 - u); p.style.stroke = u >= 1 ? '#3d5a86' : '#2f4360';
      const d = conDots[i], ph = ((t - t0) * 0.6 + i * 0.17) % 1;
      if (u >= 1) { const pt = p.getPointAtLength(ph * L); d.setAttribute('cx', pt.x); d.setAttribute('cy', pt.y); d.setAttribute('opacity', 1); } else d.setAttribute('opacity', 0);
    });
    op($('mlchart'), win(t, 102.5, 115, 0.5)); op($('mlnote'), win(t, 103, 115, 0.5)); op($('mlrule'), win(t, 109, 115, 0.5));
  }
  if (t >= 115 && t < 145) {
    let cur = 0; APP.forEach(([a], i) => { if (t >= a) cur = i; });
    APP.forEach(([a, id], i) => { const b = i < APP.length - 1 ? APP[i + 1][0] : 146; op($(id), Math.min(1, win(t, a, b + 0.3, 0.3) + (i === 0 && t < 115.3 ? 1 : 0))); });
    txt($('appst'), APP[cur][2]);
    [...$('appdots').children].forEach((d, i) => { const c = i <= cur ? 'on' : ''; if (d.className !== c) d.className = c; });
    const tap = $('tap'); let to = 0;
    TAPS.forEach(([tt, id]) => { const o = win(t, tt - 0.35, tt + 0.3, 0.15); if (o > to) { to = o; const r = $(id).getBoundingClientRect(), pr = $('screen').getBoundingClientRect(); tap.style.left = (r.left - pr.left + r.width / 2 + 16) + 'px'; tap.style.top = (r.top - pr.top + r.height / 2 + 16) + 'px'; } });
    op(tap, to);
    $('slot230').className = t >= 121.6 ? 'slot sel' : 'slot';
    const chk = t >= 125.4;
    txt($('a3txt'), chk ? '✓ Gold member verified' : 'Checking membership…'); $('a3txt').style.color = chk ? 'var(--free)' : '';
    $('a3chk').style.borderColor = chk ? 'var(--free)' : '';
    $('route').style.strokeDashoffset = (520 * (1 - sm(seg(t, 132.9, 136.6)))).toFixed(1);
  }
  if (t >= 145 && t < 170) {
    const tab = t < 153 ? 0 : t < 161 ? 1 : 2;
    [0, 1, 2].forEach((i) => { op($('t' + i), win(t, [145, 153, 161][i], [153, 161, 170][i], 0.3)); $('nv' + i).className = i === tab ? 'nav on' : 'nav'; });
    txt($('dtitle'), ['Operations', 'Model performance', 'Maintenance'][tab]);
    canvas.style.visibility = t < 153 ? 'visible' : 'hidden'; canvas.style.zIndex = '5'; canvas.style.opacity = win(t, 145, 153, 0.4).toFixed(3);
    const cur = $('cursor');
    const P = [[700, 700, 150.5], [130, 470, 152.5], [130, 470, 153.2], [130, 524, 160.5], [130, 524, 161.5]];
    let x = P[0][0], y = P[0][1];
    for (let i = 0; i < P.length - 1; i++) if (t >= P[i][2]) { const u = sm(seg(t, P[i][2], P[i + 1][2])); x = lerp(P[i][0], P[i + 1][0], u); y = lerp(P[i][1], P[i + 1][1], u); }
    cur.style.left = x + 'px'; cur.style.top = y + 'px'; op(cur, win(t, 150.3, 162, 0.3));
  } else { canvas.style.visibility = 'visible'; canvas.style.zIndex = '0'; canvas.style.opacity = '1'; }
}

// ---------------------------------------------------------------- entry
const ready = (async () => { await document.fonts.ready; await document.fonts.load('700 50px "Barlow Condensed"'); await document.fonts.load('600 22px Barlow'); buildLabels(); drawLobby(); })();
window.seek = async (t) => {
  await ready;
  footPromise = null;
  updateHTML(t);
  update3D(t);
  const r = rectFor(t); placeTags(t, r);
  if (footPromise) await footPromise;
  return true;
};
window.ready = ready;
