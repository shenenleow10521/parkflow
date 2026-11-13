// ParkFlow · pitch film v2 compositor. window.seek(t) draws the frame at time t (seconds).
// Real footage, the 3D twin (twin/), the real driver app (drv/) and operator dashboard (cmd/) recordings,
// and animated scenes that retell deck pages 05-08 as one revenue story.
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
const cls = (el, c, on) => { if (el.classList.contains(c) !== on) el.classList.toggle(c, on); };
function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const FPS = 30, META = window.META, DRV = window.DRV, CMD = window.CMD, TWF = window.TWIN_FRAMES;
const pad = (k, n = 4) => String(k).padStart(n, '0');
let pend = [];
function setImg(el, src) { if (el._src !== src) { el._src = src; el.src = src; pend.push(el.decode().catch(() => {})); } }
const lerpR = (a, b, u) => a.map((v, i) => lerp(v, b[i], u));

// ---------------------------------------------------------------- 3D twin
const twin = $('twin'), ghosts = [...document.querySelectorAll('#ghosts img')];
function twinFrame(k) { let best = TWF[0], d = 1e9; if (TWF.includes(k)) return k; for (const f of TWF) { const dd = Math.abs(f - k); if (dd < d) { d = dd; best = f; } } return best; }
const twinSrc = (k) => `twin/${pad(twinFrame(k), 5)}.jpg`;
function drawTwin(t) {
  let o = 0, k = Math.round(t * FPS), filt = 'none', tr = 'none', z = '1', rad = '0px';
  if (t >= 13.6 && t < 35.4) { // zone, then the blurred backdrop of the phone scene
    o = sm(seg(t, 13.6, 14.3)) * (1 - sm(seg(t, 34.6, 35.4)));
    if (t >= 20.0) { k = 600; const b = sm(seg(t, 19.8, 20.8)); filt = `blur(${(b * 16).toFixed(1)}px) brightness(${(1 - 0.35 * b).toFixed(3)})`; const s = 1.04 + 0.05 * seg(t, 20, 35); tr = `translate(${(-960 * (s - 1)).toFixed(1)}px,${(-540 * (s - 1)).toFixed(1)}px) scale(${s.toFixed(4)})`; }
  } else if (t >= 45.8 && t < 51.6) o = sm(seg(t, 45.9, 46.5));
  else if (t >= 57.6 && t < 82.6) o = 1;
  else if (t >= 82.9 && t < 89.95) {
    o = sm(seg(t, 83.15, 83.8));
    if (t >= 88.7) { // shrink into the dashboard's live 3D view
      const R = (CMD.overview && CMD.overview.canvas) || [100, 190, 1420, 640], u = sm(seg(t, 88.7, 89.6));
      const s = lerp(1, R[2] / 1920, u), x = lerp(0, R[0], u), y = lerp(0, R[1] + (R[3] - 1080 * s) / 2, u);
      tr = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(${s.toFixed(5)})`; rad = `${(u * 16).toFixed(1)}px`; z = '6';
      o *= 1 - sm(seg(t, 89.45, 89.95));
    }
  }
  op(twin, o); css(twin, 'zIndex', z); ghosts.forEach((g) => op(g, 0));
  if (o <= 0) return;
  setImg(twin, twinSrc(k)); css(twin, 'filter', filt); css(twin, 'transform', tr); css(twin, 'borderRadius', rad);
  if (t >= 81.5 && t < 82.4) { // whip pan out of the 3D
    const w = win(t, 81.5, 82.4, 0.4);
    css(twin, 'filter', `blur(${(w * 3).toFixed(2)}px)`);
    [-120, -60, 60, 120].forEach((dx, i) => { setImg(ghosts[i], twin._src); css(ghosts[i], 'transform', `translateX(${(dx * w).toFixed(1)}px)`); op(ghosts[i], 0.17 * w); });
  }
}

// ---------------------------------------------------------------- opening footage
const foot = $('foot'), footbg = $('footbg'), footfg = $('footfg');
function drawFoot(t) {
  const o = 1 - sm(seg(t, 3.7, 4.3)); op(foot, o); if (o <= 0) return;
  const src = `foot/${pad(clamp(Math.round(t * 24), 0, 119), 5)}.jpg`; setImg(footfg, src); setImg(footbg, src);
  css(footfg, 'transform', `scale(${(1 + t * 0.015).toFixed(4)})`);
}

// ---------------------------------------------------------------- S05: the service
const svc = $('s-svc');
{ // mini bays for card 3 and the claim grid
  let h = ''; for (let i = 0; i < 5; i++) h += `<i id="v3b${i}" style="position:absolute;left:${10 + i * 27}px;top:28px;width:22px;height:54px;border-radius:5px;border:2px solid rgba(255,214,90,.6);background:${i % 2 ? '#3a4352' : 'transparent'}"></i>`;
  $('v3').innerHTML = h;
  const occ = new Set([0, 1, 3, 4, 6, 8, 9, 11, 12, 14, 15, 17]); let g = '';
  for (let r = 0; r < 2; r++) for (let c = 0; c < 9; c++) { const i = r * 9 + c, x = 50 + c * 100, y = 10 + r * 150;
    g += `<div class="bay" style="left:${x}px;top:${y}px;${occ.has(i) ? 'background:#3a4352;border-color:rgba(255,214,90,.25)' : 'background:rgba(47,220,132,.13);border-color:rgba(47,220,132,.7)'}">${occ.has(i) ? '<div style="margin:22px 14px;height:70px;border-radius:8px;background:#6b7584"></div>' : ''}</div>`; }
  $('claim-bays').innerHTML = g;
}
const FREE = [[0, 2], [0, 5], [1, 1], [0, 7], [1, 7], [1, 4]].map(([r, c]) => [50 + c * 100 + 42, 10 + r * 150 + 60]);
function drawSvc(t) {
  const o = sm(seg(t, 4.0, 4.4)) * (1 - sm(seg(t, 13.4, 14.2))); op(svc, o); if (o <= 0) return;
  const ph = $('svc-photo'), dim = sm(seg(t, 9.3, 10.0));
  css(ph, 'transform', `scale(${lerp(1.12, 1.0, eo(seg(t, 4, 11))).toFixed(4)})`); css(ph, 'filter', `blur(${(dim * 10).toFixed(1)}px) brightness(${(1 - 0.45 * dim).toFixed(3)})`);
  const hd = $('svc-head'), hu = eo(seg(t, 5.0, 5.6)), ho = 1 - sm(seg(t, 9.3, 9.8));
  op(hd, hu * ho); css(hd, 'transform', `translateY(${((1 - hu) * 30 - (1 - ho) * 40).toFixed(1)}px)`);
  ['st1', 'st2', 'st3'].forEach((id, i) => { const u = eo(seg(t, 6.3 + i * 0.8, 6.85 + i * 0.8)), x = 1 - sm(seg(t, 9.25, 9.75)); op($(id), u * x); css($(id), 'transform', `translateY(${((1 - u) * 40 + (1 - x) * 30).toFixed(1)}px)`); });
  const r = seg(t, 6.9, 7.4); op($('v1rip'), r > 0 && r < 1 ? 1 - r : 0); css($('v1rip'), 'transform', `scale(${(0.6 + r * 1.4).toFixed(3)})`);
  css($('v2scan'), 'top', `${lerp(-30, 110, seg(t, 7.5, 8.7) % 1).toFixed(1)}px`);
  for (let i = 0; i < 5; i += 2) css($('v3b' + i), 'background', t >= 8.3 + i * 0.15 ? 'rgba(47,220,132,.75)' : 'transparent');
  // the claim: a booking floats over free bays, never pinned to one
  const cl = $('claim'), co = win(t, 9.8, 13.9, 0.45); op(cl, co);
  const z = ei(seg(t, 13.0, 13.9)); css(cl, 'transform', `scale(${(0.94 + 0.06 * eo(seg(t, 9.8, 10.4)) + z * 0.8).toFixed(4)})`); css(cl, 'filter', `blur(${(z * 8).toFixed(1)}px)`);
  const hops = FREE.length - 1, u = seg(t, 10.4, 12.9) * hops, i = Math.min(hops - 1, Math.floor(u)), f = sm((u - i) * 1.6);
  const [x, y] = lerpR(FREE[i], FREE[i + 1], f); css($('token'), 'left', `${x.toFixed(1)}px`); css($('token'), 'top', `${(y - Math.sin(f * Math.PI) * 26).toFixed(1)}px`);
  op($('claim-cap'), sm(seg(t, 10.3, 10.8)));
}

// ---------------------------------------------------------------- phone: the real driver app
const app = $('s-app'), phone = $('phone'), drv = $('drv'), tap = $('tap'), rip = $('ripple');
const ND = DRV.n;
function phoneRect() { return [740, 96, 418, 872]; }
function drawApp(t) {
  const o = sm(seg(t, 19.9, 20.5)) * (1 - sm(seg(t, 35.1, 35.5))); op(app, o); if (o <= 0) return;
  op($('phonebg'), 1 - sm(seg(t, 34.4, 35.1)));
  setImg(drv, `drv/${pad(clamp(Math.round((t - 20) * FPS), 0, ND - 1))}.jpg`);
  const e = eo(seg(t, 19.9, 20.75));
  let tr = `perspective(1600px) translateY(${((1 - e) * 90).toFixed(1)}px) rotateY(${lerp(-18, -5, e) + 3 * seg(t, 21, 34)}deg) scale(${lerp(0.92, 1, e).toFixed(4)})`;
  if (t >= 34.2) { // the phone flies into the system map as the "booking app" node
    const u = sm(seg(t, 34.2, 35.2)), from = phoneRect(), to = [1440 + 65 - 36, 330 + 3, 72, 150];
    const r = lerpR(from, to, u), s = r[2] / from[2];
    tr = `translate(${(r[0] - from[0] + (r[2] - from[2]) / 2).toFixed(1)}px,${(r[1] - from[1] + (r[3] - from[3]) / 2).toFixed(1)}px) scale(${s.toFixed(4)}) rotateY(${(-5 * (1 - u)).toFixed(2)}deg)`;
  }
  css(phone, 'transform', tr); op(phone, 1 - sm(seg(t, 35.0, 35.35)));
  // taps from the recording
  let to = 0, ro = 0;
  for (const ev of DRV.taps) {
    if (!ev.xy) continue; const tt = 20 + ev.f / FPS, ww = win(t, tt - 0.45, tt + 0.22, 0.14);
    if (ww > to) { to = ww; css(tap, 'left', ev.xy[0] + 'px'); css(tap, 'top', ev.xy[1] + 'px'); css(rip, 'left', ev.xy[0] + 'px'); css(rip, 'top', ev.xy[1] + 'px'); }
    const ru = seg(t, tt, tt + 0.5); if (ru > 0 && ru < 1) { ro = 1 - ru; css(rip, 'transform', `scale(${(1 + ru * 1.7).toFixed(2)})`); }
  }
  op(tap, to); op(rip, ro);
  const tagIn = (id, a, b, dx) => { const w = win(t, a, b, 0.35); op($(id), w); css($(id), 'transform', `translateX(${((1 - eo(seg(t, a, a + 0.4))) * dx).toFixed(1)}px)`); };
  tagIn('tg1', 21.6, 25.0, 30); tagIn('tg2', 25.9, 29.8, -30); tagIn('tg3', 30.5, 34.0, 30);
  const p = $('price'), pu = eo(seg(t, 25.7, 26.3)); op(p, win(t, 25.7, 34.2, 0.4)); css(p, 'transform', `translateX(${((1 - pu) * 60).toFixed(1)}px)`);
  op($('pr1'), sm(seg(t, 26.2, 26.7))); op($('pr2'), sm(seg(t, 27.6, 28.1)));
  css($('price'), 'top', t > 30 ? `${lerp(330, 300, sm(seg(t, 30, 30.5))).toFixed(1)}px` : '330px');
}

// ---------------------------------------------------------------- S07: the parts
const sys = $('s-sys'), links = $('links');
setImg($('n4img'), 'drv/0200.jpg'); setImg($('n5img'), 'cmd/0090.jpg');
const LINKS = [[480, 345, 740, 400], [480, 525, 740, 520], [480, 705, 740, 640], [1180, 420, 1440, 405], [1180, 600, 1440, 635]];
links.innerHTML = LINKS.map(([x1, y1, x2, y2], i) => `<path id="lk${i}" d="M${x1} ${y1} C ${x1 + 120} ${y1}, ${x2 - 120} ${y2}, ${x2} ${y2}" stroke="#2f4a73" stroke-width="3" fill="none"/>` +
  [0, 1, 2].map((j) => `<circle id="ld${i}_${j}" r="5.5" fill="#5fd4ff" opacity="0"/>`).join('')).join('');
const lkP = LINKS.map((_, i) => $('lk' + i));
function drawSys(t) {
  const o = sm(seg(t, 34.9, 35.5)) * (1 - sm(seg(t, 45.7, 46.4))); op(sys, o); if (o <= 0) return;
  const hu = eo(seg(t, 35.3, 35.9)); op($('sys-head'), hu); css($('sys-head'), 'transform', `translateY(${((1 - hu) * 24).toFixed(1)}px)`);
  [['n4', 35.15], ['n1', 35.6], ['n2', 35.9], ['n3', 36.2], ['n5', 36.5]].forEach(([id, a]) => { const u = eo(seg(t, a, a + 0.5)); op($(id), u); css($(id), 'transform', `translateY(${((1 - u) * 30).toFixed(1)}px)`); });
  const cu = eo(seg(t, 36.0, 36.6)), pulse = win(t, 44.9, 45.7, 0.25);
  op($('ctl'), cu); css($('ctl'), 'transform', `scale(${(0.9 + 0.1 * cu + 0.03 * pulse).toFixed(4)})`);
  css($('ctl'), 'boxShadow', `0 24px 70px rgba(0,0,0,.4), 0 0 ${(20 + 60 * pulse).toFixed(0)}px rgba(95,212,255,${(0.2 + 0.5 * pulse).toFixed(2)})`);
  ['m1', 'm2', 'm3', 'm4'].forEach((id, i) => cls($(id), 'on', t >= 37.6 + i * 0.8));
  lkP.forEach((p, i) => {
    const L = p.getTotalLength(), u = sm(seg(t, 36.6 + i * 0.1, 37.4 + i * 0.1));
    css(p, 'strokeDasharray', `${L}`); css(p, 'strokeDashoffset', `${(L * (1 - u)).toFixed(1)}`); css(p, 'stroke', u >= 1 ? '#3d6aa8' : '#2f4a73');
    for (let j = 0; j < 3; j++) { const d = $(`ld${i}_${j}`); if (u < 1) { d.setAttribute('opacity', 0); continue; }
      let ph = ((t - 37.4) * 0.55 + j / 3 + i * 0.13) % 1; if (i >= 3) ph = 1 - ph; const pt = p.getPointAtLength(ph * L);
      d.setAttribute('cx', pt.x.toFixed(1)); d.setAttribute('cy', pt.y.toFixed(1)); d.setAttribute('opacity', '0.95'); }
  });
  const ru = eo(seg(t, 41.2, 41.8)); op($('rule'), ru * (1 - sm(seg(t, 45.0, 45.5)))); css($('rule'), 'transform', `translateY(${((1 - ru) * 30).toFixed(1)}px)`);
  const bm = $('beam'), bu = eo(seg(t, 45.25, 45.8));
  if (t >= 45.2 && t < 46.4) { css(bm, 'left', '960px'); css(bm, 'top', '750px'); css(bm, 'height', `${(bu * 340).toFixed(1)}px`); op(bm, (1 - sm(seg(t, 45.9, 46.3)))); } else op(bm, 0);
}

// ---------------------------------------------------------------- S08: the plan
const plan = $('s-plan'), chart = $('chart');
const SER = [['#2fdc84', '', [0.55, 0.6, 0.62, 0.6, 0.56, 0.5, 0.45], 'walk-ins'], ['#ffb21f', '', [0.05, 0.1, 0.18, 0.3, 0.48, 0.7, 0.86], 'bookings'], ['#8ab8ff', '7 7', [0.2, 0.3, 0.42, 0.5, 0.52, 0.48, 0.42], 'departures']];
const CX = (m) => 70 + (m / 180) * 840, CY = (v) => 420 - v * 360;
function sAt(a, m) { const i = Math.min(5, Math.floor(m / 30)), u = (m - i * 30) / 30; return lerp(a[i], a[i + 1], u); }
function drawPlan(t) {
  const o = sm(seg(t, 50.7, 51.3)) * (1 - sm(seg(t, 57.7, 58.4))); op(plan, o); if (o <= 0 && !(t >= 57 && t < 58.6)) return;
  const hu = eo(seg(t, 51.2, 51.8)); op($('plan-head'), hu); css($('plan-head'), 'transform', `translateY(${((1 - hu) * 24).toFixed(1)}px)`);
  const m = 180 * sm(seg(t, 51.6, 54.6));
  if (chart._m !== m.toFixed(1)) {
    chart._m = m.toFixed(1);
    let s = `<rect x="${CX(120)}" y="40" width="${CX(180) - CX(120)}" height="380" fill="rgba(255,178,31,.08)"/><text x="${(CX(120) + CX(180)) / 2}" y="62" fill="#ffd27a" font-size="17" font-weight="700" text-anchor="middle" font-family="Inter">booking peak</text>`;
    for (let k = 0; k <= 6; k++) s += `<line x1="${CX(k * 30)}" x2="${CX(k * 30)}" y1="40" y2="420" stroke="rgba(138,184,255,.08)"/><text x="${CX(k * 30)}" y="452" fill="#7f93b3" font-size="17" text-anchor="middle" font-family="Inter">${['9:00', '9:30', '10:00', '10:30', '11:00', '11:30', '12:00'][k]}</text>`;
    for (const [c, dash, a, lab] of SER) {
      const pts = []; for (let mm = 0; mm <= m + 0.01; mm += 3) pts.push(`${CX(mm).toFixed(1)},${CY(sAt(a, Math.min(mm, 180))).toFixed(1)}`);
      if (pts.length > 1) s += `<polyline points="${pts.join(' ')}" fill="none" stroke="${c}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" ${dash ? `stroke-dasharray="${dash}"` : ''}/>`;
      if (m > 2) s += `<circle cx="${CX(m)}" cy="${CY(sAt(a, m))}" r="7" fill="${c}"/>`;
      if (m >= 179) s += `<text x="${CX(180) + 16}" y="${CY(a[6]) + 6}" fill="${c}" font-size="19" font-weight="700" font-family="Inter">${lab}</text>`;
    }
    s += `<line x1="${CX(m)}" x2="${CX(m)}" y1="40" y2="420" stroke="#fff" stroke-width="2" opacity=".5"/>`;
    chart.innerHTML = s;
  }
  const hh = Math.floor(9 + m / 60), mm = Math.round(m % 60) === 60 ? 0 : Math.round(m % 60);
  $('pclock').textContent = `${hh > 12 ? hh - 12 : hh}:${String(mm).padStart(2, '0')} ${hh >= 12 ? 'PM' : 'AM'}`;
  [[1, 0, 8], [2, 90, 18], [3, 180, 25]].forEach(([i, at, n]) => { const u = eo(clamp((m - at + 8) / 22)); css($('hb' + i), 'width', `${(u * n / 30 * 100).toFixed(1)}%`); $('hl' + i).textContent = u > 0.6 ? `${n} held` : ''; });
  op($('held'), eo(seg(t, 51.3, 51.9)));
  ['ly1', 'ly2', 'ly3', 'ly4'].forEach((id, i) => cls($(id), 'on', t >= 54.8 + i * 0.6));
  op($('pclock'), t < 57.2 ? sm(seg(t, 51.4, 51.9)) : 0);
}
const flyclk = document.createElement('div'); flyclk.style.cssText = 'position:absolute;z-index:19;font-weight:800;font-size:44px;opacity:0;white-space:nowrap;transform-origin:0 0'; flyclk.textContent = '9:00 AM'; document.body.appendChild(flyclk);
const flyimg = document.createElement('div'); flyimg.style.cssText = 'position:absolute;z-index:19;opacity:0;border-radius:18px;background-repeat:no-repeat;box-shadow:0 24px 60px rgba(0,0,0,.45)'; document.body.appendChild(flyimg);
function drawFlights(t) {
  // 3D count panel flies into the held-for-bookings card
  if (t >= 50.6 && t < 51.8) {
    const src = META.dash, to = [1260, 300, 500, 470], u = sm(seg(t, 50.6, 51.45)), r = lerpR(src, to, u), sc = r[2] / src[2];
    Object.assign(flyimg.style, { left: r[0] + 'px', top: r[1] + 'px', width: r[2] + 'px', height: src[3] * sc + 'px', backgroundImage: `url(${twinSrc(Math.round(50.8 * FPS))})`, backgroundSize: `${1920 * sc}px ${1080 * sc}px`, backgroundPosition: `${-src[0] * sc}px ${-src[1] * sc}px` });
    op(flyimg, 1 - sm(seg(t, 51.3, 51.75)));
  } else op(flyimg, 0);
  // the 12:00 clock of the plan becomes the 3D clock at 9:00
  if (t >= 57.2 && t < 58.9) {
    const c = META.clock, u = sm(seg(t, 57.25, 58.25)), x = lerp(1260, c[0] + c[2] / 2 - 120, u), y = lerp(226, c[1] - 2, u);
    flyclk.textContent = '9:00 AM'; css(flyclk, 'left', x + 'px'); css(flyclk, 'top', y + 'px'); css(flyclk, 'transform', `scale(${lerp(1, 1.5, u).toFixed(3)})`);
    op(flyclk, sm(seg(t, 57.2, 57.4)) * (1 - sm(seg(t, 58.3, 58.85))));
  } else op(flyclk, 0);
}

// ---------------------------------------------------------------- the real entry barrier
function drawGate(t) {
  const g = $('gate'), o = sm(seg(t, 81.95, 82.35)) * (1 - sm(seg(t, 83.3, 83.95))); op(g, o); if (o <= 0) return;
  const z = ei(seg(t, 83.1, 83.95)), s = 1 + 0.05 * seg(t, 82, 83.1) + 1.4 * z;
  css(g, 'transform', `scale(${s.toFixed(4)})`); css(g, 'transformOrigin', '62% 55%'); css(g, 'filter', `blur(${(z * 6).toFixed(1)}px)`);
  css($('gscan'), 'top', `${lerp(-120, 820, seg(t, 82.3, 83.2)).toFixed(0)}px`);
}

// ---------------------------------------------------------------- operator dashboard: where the money comes from
const cmdwrap = $('cmdwrap'), cmd = $('cmd'), NC = CMD.n;
const fr = [98, 452, 1806, 341];                // 'Where it fills first' grid (forecast tab)
const im = [98, 282, 1806, 92];                 // matched-run headline: gate-to-park and search distance, with vs without
const CKEYS = [[89.0, 1, 960, 540], [102.8, 1, 960, 540], [104.2, 1.06, 1001, 640], [108.6, 1.06, 1001, 640], [109.6, 1, 960, 540], [110.6, 1.06, 1001, 520], [115.0, 1.06, 1001, 520], [115.8, 1, 960, 540]];
function camAt(keys, t) {
  if (t <= keys[0][0]) return keys[0].slice(1);
  for (let i = 0; i < keys.length - 1; i++) if (t < keys[i + 1][0]) { const a = keys[i], b = keys[i + 1], u = sm((t - a[0]) / (b[0] - a[0])); return [lerp(a[1], b[1], u), lerp(a[2], b[2], u), lerp(a[3], b[3], u)]; }
  return keys[keys.length - 1].slice(1);
}
const VL = [[89.7, 94.9, 'Operator dashboard', 'Where the money comes from,<br>in one place.'], [104.4, 108.9, 'Protect', 'See where it fills first.<br>Act before a level jams.'], [110.4, 115.1, 'Prove', 'Every decision logged and measured.<br>The case for the next SDP mall.']];
function drawOps(t) {
  const o = sm(seg(t, 88.8, 89.5)) * (1 - sm(seg(t, 116.3, 116.9))); op(cmdwrap, o); css(cmdwrap, 'zIndex', '5');
  op($('opcap'), win(t, 89.6, 116.2, 0.4));
  const show = o > 0;
  if (show) {
    setImg(cmd, `cmd/${pad(clamp(Math.round((t - 89) * FPS), 0, NC - 1))}.jpg`);
    const [s, cx, cy] = camAt(CKEYS, t);
    css(cmd, 'transform', `translate(${(960 - cx * s).toFixed(1)}px,${(540 - cy * s).toFixed(1)}px) scale(${s.toFixed(4)})`);
    const zb = $('zoombox'); let zr = null, zo = 0;
    if (t >= 104.4 && t < 109.0) { zr = fr; zo = win(t, 104.4, 109.0, 0.35); }
    if (t >= 110.7 && t < 115.1) { zr = im; zo = win(t, 110.7, 115.1, 0.35); }
    if (zr) { const X = (x) => 960 + (x - cx) * s, Y = (y) => 540 + (y - cy) * s; css(zb, 'left', `${X(zr[0]) - 10}px`); css(zb, 'top', `${Y(zr[1]) - 10}px`); css(zb, 'width', `${zr[2] * s + 20}px`); css(zb, 'height', `${zr[3] * s + 20}px`); }
    op(zb, zo);
  } else op($('zoombox'), 0);
  const rv = $('rev'), ru = eo(seg(t, 95.0, 95.6)), rx = sm(seg(t, 102.4, 103.0));
  op(rv, win(t, 95.0, 103.0, 0.3)); css(rv, 'transform', `translateX(${((1 - ru) * 560 + rx * 560).toFixed(1)}px)`);
  ['r1', 'r2', 'r3', 'r4'].forEach((id, i) => cls($(id), 'on', t >= 95.8 + i * 1.8));
  const vl = VL.find(([a, b]) => t >= a && t < b), v = $('vline');
  if (vl) { op(v, win(t, vl[0], vl[1], 0.4)); $('vk').textContent = vl[2]; if ($('vt')._h !== vl[3]) { $('vt').innerHTML = vl[3]; $('vt')._h = vl[3]; } css(v, 'transform', `translateY(${((1 - eo(seg(t, vl[0], vl[0] + 0.5))) * 20).toFixed(1)}px)`); } else op(v, 0);
  const f4 = $('four'); op(f4, win(t, 115.2, 116.5, 0.25)); css(f4, 'transform', `scale(${(0.9 + 0.1 * eo(seg(t, 115.2, 115.6))).toFixed(4)})`);
}

// ---------------------------------------------------------------- money trail, brand
const STEPS = [['Book', 5.4], ['Fee', 26.0], ['Hold', 46.4], ['Re-sell', 73.2], ['Verify', 84.6], ['Report', 89.6]];
$('trail').innerHTML = STEPS.map(([n], i) => `${i ? '<span class="a">›</span>' : ''}<span class="s" id="ts${i}"><i></i>${n}</span>`).join('');
function drawTrail(t) {
  op($('trail'), win(t, 5.0, 116.2, 0.5));
  let cur = -1; STEPS.forEach(([, a], i) => { if (t >= a) cur = i; });
  STEPS.forEach((_, i) => { const el = $('ts' + i); cls(el, 'on', i === cur); cls(el, 'done', i < cur); });
  op($('brand'), Math.max(win(t, 4.3, 14.0, 0.4), win(t, 20.0, 35.6, 0.4), win(t, 35.0, 46.3, 0.4), win(t, 50.8, 58.2, 0.4), win(t, 82.0, 83.9, 0.3)));
}

// ---------------------------------------------------------------- data dots, tagline, logo, end card
const cv = $('dots'), g = cv.getContext('2d'), N = 560, R = rng(20261112);
const DOT = Array.from({ length: N }, () => ({ hx: R() * 2100 - 90, hy: R() * 1080, ph: R() * 6.28, sp: 0.6 + R() * 0.8, r: 1.4 + R() * 2.2, c: R() < 0.55 ? '#5fd4ff' : '#4f8dff', d: R() * 0.28, vx: R() * 2 - 1, vy: -0.4 - R() * 0.9, sx: R(), sy: R() }));
const LOGO = { tile: 118, gap: 26, font: '800 132px Inter' }; let LX, LOGO_PTS, TAG_PTS;
const TAGTEXT = 'Your parking data tells you more than you think.';
function samplePoints(draw) {
  const oc = document.createElement('canvas'); oc.width = 1920; oc.height = 1080; const o = oc.getContext('2d'); draw(o);
  const d = o.getImageData(0, 0, 1920, 1080).data, pts = [];
  for (let y = 0; y < 1080; y += 3) for (let x = 0; x < 1920; x += 3) if (d[(y * 1920 + x) * 4 + 3] > 140) pts.push([x, y]);
  const r = rng(77); for (let i = pts.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [pts[i], pts[j]] = [pts[j], pts[i]]; }
  return Array.from({ length: N }, (_, i) => pts[i % pts.length]);
}
function drawLogo(o, alpha, zoom, wordAlpha) {
  o.save(); o.font = LOGO.font; o.globalAlpha = alpha * wordAlpha; o.fillStyle = '#f4f8ff'; o.fillText('ParkFlow', LX + LOGO.tile + LOGO.gap, 588);
  o.globalAlpha = alpha; o.translate(LX + LOGO.tile / 2, 540); o.scale(zoom, zoom);
  const gr = o.createLinearGradient(-59, -59, 59, 59); gr.addColorStop(0, '#2f7bff'); gr.addColorStop(1, '#5fd4ff');
  o.fillStyle = gr; o.beginPath(); o.roundRect(-59, -59, 118, 118, 30); o.fill();
  o.fillStyle = '#fff'; o.font = '800 76px Inter'; o.textAlign = 'center'; o.textBaseline = 'middle'; o.fillText('P', 0, 4); o.restore();
}
function drawTagCanvas(o, a) { o.save(); o.globalAlpha = a; o.font = '800 62px Inter'; o.textAlign = 'center'; o.textBaseline = 'middle'; o.fillStyle = '#f4f8ff'; o.fillText(TAGTEXT, 960, 520); o.restore(); }
function dot(x, y, r, c, a) { if (a <= 0.01) return; g.globalAlpha = a * 0.16; g.fillStyle = c; g.beginPath(); g.arc(x, y, r * 3.2, 0, 6.283); g.fill(); g.globalAlpha = a; g.beginPath(); g.arc(x, y, r, 0, 6.283); g.fill(); }
function drawDots(t) {
  g.clearRect(0, 0, 1920, 1080);
  if (t < 4.4) {
    for (let i = 0; i < N; i++) { const p = DOT[i], x0 = ((p.hx + 40 * Math.sin(0.6 * t + p.ph) + 70 * t * p.sp) % 2100 + 2100) % 2100 - 90, y0 = p.hy + 30 * Math.cos(0.5 * t + p.ph * 1.3);
      const u = sm(seg(t, 2.55 + p.d, 3.3 + p.d)), [tx, ty] = LOGO_PTS[i]; dot(lerp(x0, tx, u), lerp(y0, ty, u), p.r * lerp(1, 0.8, u), p.c, sm(seg(t, p.d * 0.5, 0.8 + p.d * 0.5)) * (1 - sm(seg(t, 3.35, 3.65))) * 0.9); }
    const la = sm(seg(t, 3.2, 3.5)); if (la > 0) drawLogo(g, la * (1 - sm(seg(t, 4.0, 4.35))), 1 + 44 * ei(seg(t, 3.62, 4.25)), 1 - sm(seg(t, 3.5, 3.75)));
  }
  if (t >= 115.9 && t < 118.0) { // the dashboard breaks into data, which forms the tagline
    for (let i = 0; i < N; i++) { const p = DOT[i], sx = p.sx * 1920, sy = p.sy * 1080, a1 = eo(seg(t, 116.0, 116.8));
      const x1 = sx + p.vx * 160 * a1 + 14 * Math.sin(2 * t + p.ph), y1 = sy + p.vy * 160 * a1, u = sm(seg(t, 116.3 + p.d, 117.2 + p.d)), [tx, ty] = TAG_PTS[i];
      dot(lerp(x1, tx, u), lerp(y1, ty, u), p.r * lerp(1, 0.75, u), p.c, sm(seg(t, 115.95, 116.2)) * (1 - sm(seg(t, 117.35, 117.7))) * 0.95); }
    drawTagCanvas(g, sm(seg(t, 117.15, 117.5)) * (1 - sm(seg(t, 117.7, 118.0))));
  }
}
const tagEl = $('tagline'); tagEl.innerHTML = TAGTEXT.split(' ').map((w) => `<span class="${w === 'more' ? 'hi' : ''}">${w}</span>`).join(' ');
const words = [...tagEl.querySelectorAll('span')];
function drawTagline(t) {
  const vis = t < 3.3; op(tagEl, vis ? 1 - sm(seg(t, 2.7, 3.1)) : 0); if (!vis) return;
  css(tagEl, 'filter', `blur(${(sm(seg(t, 2.7, 3.1)) * 8).toFixed(2)}px)`);
  words.forEach((w, i) => { const u = eo(seg(t, 0.3 + i * 0.2, 0.75 + i * 0.2)); op(w, u); css(w, 'transform', `translateY(${((1 - u) * 22).toFixed(1)}px)`); css(w, 'filter', `blur(${((1 - u) * 6).toFixed(2)}px)`); });
}
function drawEnd(t) {
  op($('end'), sm(seg(t, 117.6, 118.0))); if (t < 117.5) return;
  $('elogo').style.opacity = sm(seg(t, 117.8, 118.3)); $('elogo').style.transform = `scale(${lerp(0.9, 1, eo(seg(t, 117.8, 118.8))).toFixed(4)})`;
  $('tag1').style.opacity = sm(seg(t, 118.2, 118.6)); $('tag2').style.opacity = sm(seg(t, 118.5, 118.9)); $('tag3').style.opacity = sm(seg(t, 118.8, 119.2));
  op($('shine'), win(t, 118.0, 119.3, 0.3)); $('shine').style.transform = `translateX(${lerp(-1400, 1400, seg(t, 118.0, 119.3)).toFixed(0)}px)`;
}

// ---------------------------------------------------------------- transitions
// sweep: a diagonal light band wipes across and hides the cut; flash: a quick white-out; ring: a shockwave where the beam lands
const TRANS = [['sweep', 19.95], ['sweep', 50.95], ['sweep', 102.75], ['sweep', 108.95], ['sweep', 13.75],
  ['flash', 81.95], ['flash', 83.55], ['flash', 3.98], ['ring', 45.82, 960, 1010]];
function drawTrans(t) {
  let wo = 0, wx = 0, w2 = 0, fo = 0, ro = 0;
  for (const [k, a, x, y] of TRANS) {
    if (k === 'sweep' && t >= a - 0.32 && t < a + 0.32) {
      const u = seg(t, a - 0.32, a + 0.32); wo = Math.max(wo, Math.sin(u * Math.PI)); wx = lerp(-1700, 2500, sm(u)); w2 = Math.sin(u * Math.PI) * 0.9;
      fo = Math.max(fo, 0.22 * Math.max(0, 1 - Math.abs(t - a) / 0.12));
    }
    if (k === 'flash' && t >= a - 0.12 && t < a + 0.35) fo = Math.max(fo, t < a ? sm(seg(t, a - 0.12, a)) * 0.85 : 0.85 * (1 - sm(seg(t, a, a + 0.35))));
    if (k === 'ring' && t >= a && t < a + 0.9) {
      const u = seg(t, a, a + 0.9), r = $('ring'); ro = (1 - u) * 0.95; css(r, 'left', x + 'px'); css(r, 'top', y + 'px');
      css(r, 'transform', `scale(${(0.2 + eo(u) * 9).toFixed(3)}) scaleY(.38)`); fo = Math.max(fo, 0.35 * (1 - sm(seg(t, a, a + 0.25))));
    }
  }
  op($('wipe'), wo); css($('wipe'), 'transform', `translateX(${wx.toFixed(0)}px) rotate(14deg)`);
  op($('wipe2'), w2); css($('wipe2'), 'transform', `translateX(${(wx + 460).toFixed(0)}px) rotate(14deg)`);
  op($('flash'), fo); op($('ring'), ro);
  // push-zoom: the planning chart zooms through into the 3D clock
  const pz = ei(seg(t, 57.6, 58.4));
  if (t >= 57.0 && t < 58.6) { css(plan, 'transform', `scale(${(1 + 0.35 * pz).toFixed(4)})`); css(plan, 'filter', `blur(${(pz * 10).toFixed(1)}px)`); }
  else { css(plan, 'transform', 'none'); css(plan, 'filter', 'none'); }
  // zone -> phone: a quick zoom punch on the 3D before the blur
  if (t >= 19.6 && t < 20.4) { const u = sm(seg(t, 19.6, 20.0)) * (1 - sm(seg(t, 20.0, 20.4))); css(twin, 'scale', (1 + 0.06 * u).toFixed(4)); } else css(twin, 'scale', '1');
}

// ---------------------------------------------------------------- entry
const ready = (async () => {
  await document.fonts.ready;
  await Promise.all(['800 132px Inter', '800 62px Inter', '800 76px Inter', '700 22px Inter'].map((f) => document.fonts.load(f)));
  g.font = LOGO.font; LX = 960 - (LOGO.tile + LOGO.gap + g.measureText('ParkFlow').width) / 2;
  LOGO_PTS = samplePoints((o) => drawLogo(o, 1, 1, 1)); TAG_PTS = samplePoints((o) => drawTagCanvas(o, 1));
  await Promise.all([...document.images].filter((i) => i.src).map((i) => i.decode().catch(() => {})));
})();
window.seek = async (t) => {
  await ready; pend = [];
  drawFoot(t); drawTwin(t); drawSvc(t); drawApp(t); drawSys(t); drawPlan(t); drawFlights(t); drawGate(t); drawOps(t); drawTrail(t); drawDots(t); drawTagline(t); drawEnd(t); drawTrans(t);
  op($('fade'), Math.max(1 - seg(t, 0, 0.35), seg(t, 119.35, 120)));
  if (pend.length) await Promise.all(pend);
  return true;
};
window.ready = ready;
})();
