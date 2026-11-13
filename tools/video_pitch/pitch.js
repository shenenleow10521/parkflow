// ParkFlow · 2-minute pitch film compositor. window.seek(t) draws the frame at time t (seconds).
// Layers: 3D frames (twin/NNNNN.jpg, rendered from the forked 60 s film), deck pages 05-09 built part by part,
// shared-element flights between them, data-dot particles, tagline and end card.
(() => {
const $ = (id) => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, u) => a + (b - a) * u;
const sm = (u) => { u = clamp(u); return u * u * (3 - 2 * u); };
const eo = (u) => 1 - Math.pow(1 - clamp(u), 3);
const ei = (u) => Math.pow(clamp(u), 3);
const seg = (t, a, b) => clamp((t - a) / (b - a));
const win = (t, a, b, f = 0.35) => sm(seg(t, a, a + f)) * (1 - sm(seg(t, b - f, b)));
const op = (el, v) => { const s = (+v).toFixed(3); if (el._o !== s) { el.style.opacity = s; el._o = s; } };
const css = (el, k, v) => { el._c = el._c || {}; if (el._c[k] !== v) { el.style[k] = v; el._c[k] = v; } };
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const FPS = 30;
const PARTS = window.PARTS, META = window.META, TWF = window.TWIN_FRAMES;

// ---------------------------------------------------------------- slides 05-09
// build: [part, time, kind, dur]; hl: [rect name, from, to]; cam: [t, scale, cx, cy]
const SL = {
  service: { url: 'service', vis: (t) => sm(seg(t, 3.85, 4.15)) * (1 - sm(seg(t, 12.0, 12.7))),
    build: [['title', 4.05], ['sub', 4.3], ['map', 4.55], ['howh', 4.9], ['s1', 5.45, 'left'], ['s2', 6.45, 'left'], ['s3', 7.45, 'left'], ['cap', 8.5], ['ben', 9.0]],
    hl: [['c1', 5.75, 6.9], ['c2', 6.9, 8.0], ['c3', 8.0, 9.6]],
    cam: [[4.0, 1, 960, 540], [10.3, 1.035, 975, 540], [12.4, 2.5, 449, 441]] },
  member: { url: 'member', vis: (t) => (t >= 23.4 ? 1 : 0) * (1 - sm(seg(t, 30.1, 30.7))), dx: (t) => (1 - eo(seg(t, 23.4, 24.05))) * 1920,
    build: [['title', 23.85], ['ph1', 24.3, 'pop'], ['a1', 24.55, 'left'], ['ph2', 24.75, 'pop'], ['a2', 25.0, 'left'], ['ph3', 25.2, 'pop'], ['a3', 25.45, 'left'], ['ph4', 25.65, 'pop'],
            ['fnh', 26.2], ['fn1', 26.5], ['fn2', 26.9], ['fn3', 27.3]],
    hl: [['phones', 26.0, 27.7], ['fn1', 27.8, 29.3]],
    cam: [[24.0, 1, 960, 540], [29.5, 1.03, 940, 545]] },
  mechanism: { url: 'mechanism', vis: (t) => sm(seg(t, 43.8, 44.4)), out: (t) => eo(seg(t, 52.6, 53.2)),
    build: [['title', 44.1], ['col1', 44.3], ['arr1', 44.9, 'left'], ['ctl', 45.1, 'pop'], ['arr2', 45.6, 'left'], ['col2', 45.8],
            ['ptab', 46.6], ['pfee', 46.8], ['ptbl', 47.0], ['pbox', 47.6], ['rule', 48.4]],
    hl: [['ctl', 45.6, 47.3], ['col2', 47.3, 48.7], ['ptbl', 49.7, 51.2], ['rule', 51.2, 52.0], ['ctl', 52.0, 52.65]],
    cam: [[44.2, 1, 960, 540], [48.8, 1.03, 960, 540], [50.0, 1.17, 1505, 560], [51.3, 1.17, 1505, 560], [52.1, 1, 960, 540]] },
  admission: { url: 'admission', vis: (t) => sm(seg(t, 59.7, 60.2)) * (1 - sm(seg(t, 68.4, 69.0))),
    build: [['title', 59.9], ['lh', 60.3], ['chart', 60.5, 'wipe', 1.6], ['rh', 61.6],
            ['t1', 62.2, 'pop'], ['x1', 62.3], ['bar1', 62.5, 'wipe', 0.6], ['t2', 63.0, 'pop'], ['x2', 63.1], ['bar2', 63.3, 'wipe', 0.6],
            ['t3', 63.8, 'pop'], ['x3', 63.9], ['bar3', 64.1, 'wipe', 0.6], ['key', 64.7], ['L1', 65.2], ['L2', 65.5], ['L3', 65.8], ['L4', 66.1]],
    hl: [['chart', 61.0, 63.0], ['rows', 63.2, 65.4], ['L3', 66.3, 67.3], ['t1', 67.4, 67.95]],
    cam: [[60.0, 1, 960, 540], [66.0, 1.03, 960, 560], [67.6, 1, 960, 540]] },
  operator: { url: 'operator', vis: (t) => sm(seg(t, 104.9, 105.4)) * (1 - sm(seg(t, 113.3, 114.1))),
    build: [['title', 105.0], ['fig', 105.45, 'fade', 0.25], ['ah', 106.2], ['d1', 106.7, 'left'], ['d2', 107.4, 'left'], ['d3', 108.1, 'left'], ['d4', 108.8, 'left'], ['note', 109.6]],
    hl: [['d1', 106.9, 107.7], ['d2', 107.7, 108.5], ['d3', 108.5, 109.4], ['d4', 109.4, 110.3], ['img', 110.6, 112.3]],
    cam: [[105.0, 1, 960, 540], [110.4, 1.03, 960, 540], [112.7, 1.24, 636, 559]] },
};
const PAD = 6;
const slideEls = {};
for (const [id, S] of Object.entries(SL)) {
  const el = document.createElement('div'); el.className = 'sl';
  const base = document.createElement('img'); base.className = 'base'; base.src = `slides/${S.url}_base.png`; el.appendChild(base);
  S.parts = S.build.map(([name, at, kind = 'up', dur]) => {
    const r = PARTS[id][name]; if (!r) throw new Error('no part ' + id + ' ' + name);
    const d = document.createElement('div'); d.className = 'part';
    const x = r[0] - PAD, y = r[1] - PAD, w = r[2] + 2 * PAD, h = r[3] + 2 * PAD;
    Object.assign(d.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px', backgroundImage: `url(slides/${S.url}_full.png)`, backgroundSize: '1920px 1080px', backgroundPosition: `${-x}px ${-y}px` });
    el.appendChild(d); return { d, at, kind, dur: dur || (kind === 'wipe' ? 1.0 : 0.5) };
  });
  $('slides').appendChild(el); slideEls[id] = el; S.el = el;
}
function camAt(keys, t) {
  if (t <= keys[0][0]) return keys[0].slice(1);
  for (let i = 0; i < keys.length - 1; i++) if (t < keys[i + 1][0]) { const a = keys[i], b = keys[i + 1], u = sm((t - a[0]) / (b[0] - a[0])); return [lerp(a[1], b[1], u), lerp(a[2], b[2], u), lerp(a[3], b[3], u)]; }
  return keys[keys.length - 1].slice(1);
}
function xf(id, t) { // slide transform: screen = (p - c) * s + center + d
  const S = SL[id]; let [s, cx, cy] = camAt(S.cam, t);
  if (S.out) s *= lerp(1, 0.9, S.out(t));
  return { s, cx, cy, dx: S.dx ? S.dx(t) : 0, dy: 0 };
}
const toScreen = (id, r, t) => { const X = xf(id, t); return [(r[0] - X.cx) * X.s + 960 + X.dx, (r[1] - X.cy) * X.s + 540 + X.dy, r[2] * X.s, r[3] * X.s]; };
function drawSlides(t) {
  let hlBest = null;
  for (const [id, S] of Object.entries(SL)) {
    const v = S.vis(t) * (S.out ? 1 - S.out(t) : 1);
    if (v <= 0.001) { if (S.el._shown) { S.el.style.display = 'none'; S.el._shown = false; } continue; }
    if (!S.el._shown) { S.el.style.display = 'block'; S.el._shown = true; }
    const X = xf(id, t);
    css(S.el, 'transform', `translate(${(960 + X.dx).toFixed(2)}px,${(540 + X.dy).toFixed(2)}px) scale(${X.s.toFixed(5)}) translate(${(-X.cx).toFixed(2)}px,${(-X.cy).toFixed(2)}px)`);
    op(S.el, v);
    for (const P of S.parts) {
      const u = seg(t, P.at, P.at + P.dur);
      if (P.kind === 'wipe') { op(P.d, u > 0 ? 1 : 0); css(P.d, 'clipPath', `inset(0 ${(100 * (1 - eo(u))).toFixed(2)}% 0 0)`); continue; }
      const e = eo(u); op(P.d, P.kind === 'fade' ? sm(u) : e);
      const tr = P.kind === 'left' ? `translateX(${((1 - e) * -36).toFixed(1)}px)` : P.kind === 'pop' ? `scale(${(0.86 + 0.14 * e + Math.sin(e * Math.PI) * 0.03).toFixed(4)})` : P.kind === 'fade' ? 'none' : `translateY(${((1 - e) * 26).toFixed(1)}px)`;
      css(P.d, 'transform', tr);
    }
    if (v > 0.98) for (const [name, a, b] of S.hl) { const o = win(t, a, b, 0.28); if (o > 0 && (!hlBest || o > hlBest.o)) hlBest = { o, id, r: PARTS[id][name], a }; }
  }
  const hl = $('hl');
  if (hlBest) {
    const [x, y, w, h] = toScreen(hlBest.id, hlBest.r, t), g = 10 * xf(hlBest.id, t).s, k = 1 + 0.04 * (1 - eo(seg(t, hlBest.a, hlBest.a + 0.35)));
    css(hl, 'left', `${(x - g).toFixed(1)}px`); css(hl, 'top', `${(y - g).toFixed(1)}px`); css(hl, 'width', `${(w + 2 * g).toFixed(1)}px`); css(hl, 'height', `${(h + 2 * g).toFixed(1)}px`);
    css(hl, 'transform', `scale(${k.toFixed(4)})`); op(hl, hlBest.o);
  } else op(hl, 0);
}

// ---------------------------------------------------------------- 3D frames
const twin = $('twin'), ghosts = [...document.querySelectorAll('#ghosts img')];
const twinSet = new Set(TWF);
function twinSrc(t) {
  let k = Math.round(t * FPS);
  if (!twinSet.has(k)) { let best = TWF[0], d = 1e9; for (const f of TWF) { const dd = Math.abs(f - k); if (dd < d) { d = dd; best = f; } } k = best; }
  return `twin/${String(k).padStart(5, '0')}.jpg`;
}
function twinOpacity(t) {
  if (t >= 11.9 && t < 24.1) return sm(seg(t, 11.9, 12.4)) * (1 - sm(seg(t, 23.7, 24.1)));
  if (t >= 30.2 && t < 44.8) return sm(seg(t, 30.3, 30.9));
  if (t >= 52.4 && t < 60.6) return 1;
  if (t >= 68.4 && t < 106.4) return 1 - sm(seg(t, 105.7, 106.3));
  if (t >= 113.5 && t < 117.8) return sm(seg(t, 113.7, 114.3)) * (1 - sm(seg(t, 117.0, 117.6)));
  return 0;
}
let pend = [];
function setImg(el, src) { if (el._src !== src) { el._src = src; el.src = src; pend.push(el.decode().catch(() => {})); } }
function drawTwin(t) {
  const o = twinOpacity(t);
  op(twin, o); ghosts.forEach((g) => op(g, 0));
  css(twin, 'zIndex', t >= 104.8 && t < 106.4 ? '3' : '1');
  if (o <= 0) return;
  setImg(twin, twinSrc(t));
  let tr = 'none', filt = 'none', rad = '0px';
  if (t >= 22.9 && t < 24.1) { // dive toward the lifts
    const u = ei(seg(t, 22.9, 23.95)), s = 1 + 0.65 * u, ox = 1450, oy = 560;
    tr = `translate(${(ox - ox * s).toFixed(1)}px,${(oy - oy * s).toFixed(1)}px) scale(${s.toFixed(4)})`; filt = `blur(${(u * 7).toFixed(2)}px)`;
  }
  if (t >= 94.5 && t < 95.5) { // whip pan
    const w = win(t, 94.55, 95.45, 0.42); filt = `blur(${(w * 2.5).toFixed(2)}px)`;
    [-110, -55, 55, 110].forEach((dx, i) => { setImg(ghosts[i], twin._src); css(ghosts[i], 'transform', `translateX(${(dx * w).toFixed(1)}px)`); op(ghosts[i], 0.17 * w); });
  }
  if (t >= 104.8 && t < 106.4) { // shrink into the operator screenshot
    const R = PARTS.operator.img, u = sm(seg(t, 104.8, 105.7)), s = lerp(1, R[2] / 1920, u), h = 1080 * s;
    const x = lerp(0, R[0], u), y = lerp(0, R[1] + (R[3] - h) / 2, u);
    tr = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(${s.toFixed(5)})`; rad = `${(u * 22).toFixed(1)}px`;
  }
  css(twin, 'transform', tr); css(twin, 'filter', filt); css(twin, 'borderRadius', rad);
}

// ---------------------------------------------------------------- flights and effects
const fly = $('fly'), badge = $('badge');
function crop(el, url, iw, ih, src, dst) {
  const sc = dst[2] / src[2];
  css(el, 'left', dst[0].toFixed(1) + 'px'); css(el, 'top', dst[1].toFixed(1) + 'px'); css(el, 'width', dst[2].toFixed(1) + 'px'); css(el, 'height', (src[3] * sc).toFixed(1) + 'px');
  css(el, 'backgroundImage', `url(${url})`); css(el, 'backgroundSize', `${(iw * sc).toFixed(1)}px ${(ih * sc).toFixed(1)}px`);
  css(el, 'backgroundPosition', `${(-src[0] * sc).toFixed(1)}px ${(-src[1] * sc).toFixed(1)}px`);
}
const lerpR = (a, b, u) => a.map((v, i) => lerp(v, b[i], u));
function drawFx(t) {
  let fo = 0; css(fly, 'transform', 'none');
  // slide 06 HOME screen lifts off and becomes the live phone
  if (t >= 29.55 && t < 31.15) {
    const src = PARTS.member.fig1, from = toScreen('member', src, 29.6), to = [774, 119, 392, 392 * src[3] / src[2]];
    const lift = eo(seg(t, 29.55, 29.9)), u = sm(seg(t, 29.9, 30.9));
    crop(fly, 'slides/member_full.png', 1920, 1080, src, lerpR(from, to, u));
    css(fly, 'transform', `perspective(1400px) rotateY(${(-14 * Math.sin(u * Math.PI) - 8 * u).toFixed(2)}deg) scale(${(1 + 0.06 * lift * (1 - u)).toFixed(4)})`);
    css(fly, 'borderRadius', `${lerp(16, 40, u).toFixed(1)}px`);
    fo = 1 - sm(seg(t, 30.75, 31.1));
  }
  // C -> slide 08: the live count panel flies onto the held-bay rows
  if (t >= 59.35 && t < 60.6) {
    const k = String(Math.round(59.4 * FPS)).padStart(5, '0'), src = META.dash, to = toScreen('admission', PARTS.admission.rows, t);
    const u = sm(seg(t, 59.4, 60.25)), dst = lerpR(src, [to[0] + to[2] * 0.2, to[1] + 40, to[2] * 0.6, src[3] * (to[2] * 0.6) / src[2]], u);
    crop(fly, `twin/${k}.jpg`, 1920, 1080, src, dst); css(fly, 'borderRadius', '18px');
    fo = 1 - sm(seg(t, 60.1, 60.55));
  }
  // slide 08's 9:00 badge pops out and becomes the 3D clock
  if (t >= 67.8 && t < 69.4) {
    const src = PARTS.admission.t1, from = toScreen('admission', src, 67.8), c = META.clock;
    const to = [c[0] + c[2] / 2 - 130, c[1] - 6, 260, 260 * src[3] / src[2]];
    const pop = Math.sin(seg(t, 67.8, 68.15) * Math.PI) * 0.18, u = sm(seg(t, 68.15, 69.0));
    crop(fly, 'slides/admission_full.png', 1920, 1080, src, lerpR(from, to, u));
    css(fly, 'transform', `scale(${(1 + pop).toFixed(4)})`); css(fly, 'borderRadius', '14px');
    fo = 1 - sm(seg(t, 68.95, 69.35));
  }
  op(fly, fo);
  // phone plate -> slide 07 booking-app card
  let bo = 0;
  if (t >= 43.25 && t < 44.9) {
    const p = META.plate, card = toScreen('mechanism', PARTS.mechanism.appcard, 44.4);
    const to = [card[0] + 14, card[1] + card[3] * 0.32, 150, 150 * p[3] / p[2]], u = sm(seg(t, 43.35, 44.4));
    const r = lerpR(p, to, u), arc = Math.sin(u * Math.PI) * -120;
    css(badge, 'left', r[0].toFixed(1) + 'px'); css(badge, 'top', (r[1] + arc).toFixed(1) + 'px'); css(badge, 'width', r[2].toFixed(1) + 'px'); css(badge, 'height', r[3].toFixed(1) + 'px');
    css(badge, 'fontSize', (r[3] * 0.62).toFixed(1) + 'px'); css(badge, 'transform', `rotate(${(Math.sin(u * Math.PI) * -8).toFixed(2)}deg)`);
    bo = sm(seg(t, 43.25, 43.4)) * (1 - sm(seg(t, 44.5, 44.9)));
  }
  op(badge, bo);
  // white light sweep between the 3D zone and slide 06
  const sw = $('sweep'), su = seg(t, 23.1, 23.8);
  op(sw, su > 0 && su < 1 ? Math.sin(su * Math.PI) : 0); css(sw, 'transform', `translateX(${lerp(-2900, 1000, su).toFixed(0)}px)`);
  // controller pulse drops a light beam into the 3D floor
  const bm = $('beam'), bu = seg(t, 52.2, 52.75);
  if (t >= 52.15 && t < 53.4) {
    const c = toScreen('mechanism', PARTS.mechanism.ctl, t), x = c[0] + c[2] / 2, y0 = c[1] + c[3];
    css(bm, 'left', x.toFixed(1) + 'px'); css(bm, 'top', y0.toFixed(1) + 'px'); css(bm, 'height', (eo(bu) * (1100 - y0)).toFixed(1) + 'px');
    op(bm, sm(seg(t, 52.15, 52.3)) * (1 - sm(seg(t, 52.95, 53.4))));
  } else op(bm, 0);
  op($('dim'), win(t, 113.6, 117.1, 0.5) * 1);
}

// ---------------------------------------------------------------- data dots, tagline, logo
const cv = $('dots'), g = cv.getContext('2d');
const N = 560, R = rng(20261112);
const DOT = Array.from({ length: N }, () => ({ hx: R() * 2100 - 90, hy: R() * 1080, ph: R() * 6.28, sp: 0.6 + R() * 0.8, r: 1.4 + R() * 2.2, c: R() < 0.55 ? '#5fd4ff' : '#4f8dff', d: R() * 0.28, vx: R() * 2 - 1, vy: -0.4 - R() * 0.9, sx: R(), sy: R() }));
const LOGO = { tile: 118, gap: 26, font: '800 132px Inter' };
function samplePoints(draw) {
  const oc = document.createElement('canvas'); oc.width = 1920; oc.height = 1080; const o = oc.getContext('2d');
  draw(o); const d = o.getImageData(0, 0, 1920, 1080).data, pts = [];
  for (let y = 0; y < 1080; y += 3) for (let x = 0; x < 1920; x += 3) if (d[(y * 1920 + x) * 4 + 3] > 140) pts.push([x, y]);
  const r = rng(77); for (let i = pts.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [pts[i], pts[j]] = [pts[j], pts[i]]; }
  return Array.from({ length: N }, (_, i) => pts[i % pts.length]);
}
let LOGO_PTS, TAG_PTS, LX;
function logoGeom(o) { o.font = LOGO.font; const tw = o.measureText('ParkFlow').width; const total = LOGO.tile + LOGO.gap + tw; LX = 960 - total / 2; return tw; }
function drawLogo(o, alpha, zoom, wordAlpha) {
  o.save(); o.font = LOGO.font; o.textBaseline = 'alphabetic';
  o.globalAlpha = alpha * wordAlpha; o.fillStyle = '#f4f8ff'; o.fillText('ParkFlow', LX + LOGO.tile + LOGO.gap, 540 + 48);
  o.globalAlpha = alpha; const cx = LX + LOGO.tile / 2, cy = 540;
  o.translate(cx, cy); o.scale(zoom, zoom);
  const gr = o.createLinearGradient(-59, -59, 59, 59); gr.addColorStop(0, '#2f7bff'); gr.addColorStop(1, '#5fd4ff');
  o.fillStyle = gr; o.beginPath(); o.roundRect(-59, -59, 118, 118, 30); o.fill();
  o.fillStyle = '#ffffff'; o.font = '800 76px Inter'; o.textAlign = 'center'; o.textBaseline = 'middle'; o.fillText('P', 0, 4);
  o.restore();
}
const TAGTEXT = 'Your parking data tells you more than you think.';
function drawTagCanvas(o, alpha) { o.save(); o.globalAlpha = alpha; o.font = '800 62px Inter'; o.textAlign = 'center'; o.textBaseline = 'middle'; o.fillStyle = '#f4f8ff'; o.fillText(TAGTEXT, 960, 520); o.restore(); }
function dot(x, y, r, c, a) { if (a <= 0.01) return; g.globalAlpha = a * 0.16; g.fillStyle = c; g.beginPath(); g.arc(x, y, r * 3.2, 0, 6.283); g.fill(); g.globalAlpha = a; g.beginPath(); g.arc(x, y, r, 0, 6.283); g.fill(); }
function drawDots(t) {
  g.clearRect(0, 0, 1920, 1080);
  if (t < 4.4) { // opening: drifting data gathers into the logo, then the tile zooms through
    for (let i = 0; i < N; i++) {
      const p = DOT[i], x0 = ((p.hx + 40 * Math.sin(0.6 * t + p.ph) + 70 * t * p.sp) % 2100 + 2100) % 2100 - 90, y0 = p.hy + 30 * Math.cos(0.5 * t + p.ph * 1.3);
      const u = sm(seg(t, 2.55 + p.d, 3.3 + p.d)), [tx, ty] = LOGO_PTS[i];
      dot(lerp(x0, tx, u), lerp(y0, ty, u), p.r * lerp(1, 0.8, u), p.c, sm(seg(t, p.d * 0.5, 0.8 + p.d * 0.5)) * (1 - sm(seg(t, 3.35, 3.65))) * 0.9);
    }
    const la = sm(seg(t, 3.2, 3.5)), z = 1 + 44 * ei(seg(t, 3.62, 4.25));
    if (la > 0) drawLogo(g, la * (1 - sm(seg(t, 4.0, 4.35))), z, 1 - sm(seg(t, 3.5, 3.75)));
  }
  if (t >= 112.9 && t < 117.2) { // close: the dashboard breaks into data, which forms the tagline
    const F = toScreen('operator', PARTS.operator.img, 113.0);
    for (let i = 0; i < N; i++) {
      const p = DOT[i], sx = F[0] + p.sx * F[2], sy = F[1] + p.sy * F[3];
      const a1 = eo(seg(t, 113.0, 114.7)), x1 = sx + p.vx * 260 * a1 + 18 * Math.sin(2 * t + p.ph), y1 = sy + p.vy * 260 * a1 + 14 * Math.cos(1.7 * t + p.ph);
      const u = sm(seg(t, 114.5 + p.d, 115.85 + p.d)), [tx, ty] = TAG_PTS[i];
      dot(lerp(x1, tx, u), lerp(y1, ty, u), p.r * lerp(1, 0.75, u), p.c, sm(seg(t, 113.0, 113.35)) * (1 - sm(seg(t, 116.05, 116.5))) * 0.95);
    }
    drawTagCanvas(g, sm(seg(t, 115.75, 116.15)) * (1 - sm(seg(t, 116.95, 117.2))));
  }
}
// opening tagline, word by word
const tagEl = $('tagline');
tagEl.innerHTML = TAGTEXT.split(' ').map((w) => `<span class="${w === 'more' ? 'hi' : ''}">${w}</span>`).join(' ');
const words = [...tagEl.querySelectorAll('span')];
function drawTagline(t) {
  const vis = t < 3.3; op(tagEl, vis ? 1 - sm(seg(t, 2.7, 3.1)) : 0);
  if (!vis) return;
  css(tagEl, 'filter', `blur(${(sm(seg(t, 2.7, 3.1)) * 8).toFixed(2)}px)`);
  words.forEach((w, i) => { const u = eo(seg(t, 0.3 + i * 0.2, 0.75 + i * 0.2)); op(w, u); css(w, 'transform', `translateY(${((1 - u) * 22).toFixed(1)}px)`); css(w, 'filter', `blur(${((1 - u) * 6).toFixed(2)}px)`); });
}
function drawEnd(t) {
  op($('end'), sm(seg(t, 116.9, 117.4)));
  if (t < 116.8) return;
  $('elogo').style.opacity = sm(seg(t, 117.1, 117.7)); $('elogo').style.transform = `scale(${lerp(0.9, 1, eo(seg(t, 117.1, 118.2))).toFixed(4)})`;
  $('tag1').style.opacity = sm(seg(t, 117.6, 118.1)); $('tag2').style.opacity = sm(seg(t, 118.0, 118.5)); $('tag3').style.opacity = sm(seg(t, 118.3, 118.8));
  op($('shine'), win(t, 117.4, 118.8, 0.3)); $('shine').style.transform = `translateX(${lerp(-1400, 1400, seg(t, 117.4, 118.8)).toFixed(0)}px)`;
}

// ---------------------------------------------------------------- entry
const ready = (async () => {
  await document.fonts.ready;
  await Promise.all(['800 132px Inter', '800 62px Inter', '800 76px Inter', '700 56px Inter'].map((f) => document.fonts.load(f)));
  logoGeom(g);
  LOGO_PTS = samplePoints((o) => { o.font = LOGO.font; drawLogo(o, 1, 1, 1); });
  TAG_PTS = samplePoints((o) => drawTagCanvas(o, 1));
  const imgs = Object.values(SL).flatMap((S) => [`slides/${S.url}_base.png`, `slides/${S.url}_full.png`]).map((src) => { const i = new Image(); i.src = src; return i.decode(); });
  await Promise.all([...imgs, ...[...document.querySelectorAll('.sl img.base')].map((i) => i.decode())]);
})();
window.seek = async (t) => {
  await ready;
  pend = [];
  drawTwin(t); drawSlides(t); drawFx(t); drawDots(t); drawTagline(t); drawEnd(t);
  op($('fade'), Math.max(1 - seg(t, 0, 0.35), seg(t, 119.35, 120)));
  if (pend.length) await Promise.all(pend);
  return true;
};
window.ready = ready;
})();
