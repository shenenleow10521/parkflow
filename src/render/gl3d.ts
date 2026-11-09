// WebGL2 scene with an HDR post-processing pipeline: per-floor shadow maps, emissive ceiling lights and
// bay guidance indicators with bloom, ACES tone mapping. Procedural geometry only (cars, pillars, lift
// lobbies, ramps, CCTV). Labels and tooltips are HTML overlays. Falls back to scene3d.ts without WebGL2.

import { store, emit } from '../ui/store';
import { Layout, Bay, FLOOR_NAMES, ZONES, ZoneId, LIFT_X, LIFT_Z, SLAB, ZONE_X0, ZONE_COUNTS, BAY_W, ROW_Z, A1_Z, A2_Z, DEST_BY_ID, BAY_TYPE_LABEL } from '../core/layout';
import { Sim, Vehicle, VState, MANEUVER_S, GAP } from '../core/sim';
import { prefersReducedMotion, esc } from '../ui/dom';
import { hash01 } from '../core/rng';

const GL_DEG = Math.PI / 180;
export const GL_FLOOR_SPACING = 21;
const SHADOW_RES = 1024;

interface GlCam { yaw: number; pitch: number; dist: number; tx: number; ty: number; tz: number }

// ---------- small math ----------
function m4Persp(fovy: number, aspect: number, near: number, far: number): Float32Array {
  const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
  return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0]);
}
function m4Ortho(l: number, r: number, b: number, t: number, n: number, f: number): Float32Array {
  return new Float32Array([2 / (r - l), 0, 0, 0, 0, 2 / (t - b), 0, 0, 0, 0, -2 / (f - n), 0, -(r + l) / (r - l), -(t + b) / (t - b), -(f + n) / (f - n), 1]);
}
function m4Look(e: number[], t: number[]): Float32Array {
  let zx = e[0] - t[0], zy = e[1] - t[1], zz = e[2] - t[2];
  let l = Math.hypot(zx, zy, zz); zx /= l; zy /= l; zz /= l;
  let xx = zz, xy = 0, xz = -zx;
  l = Math.hypot(xx, xy, xz) || 1; xx /= l; xy /= l; xz /= l;
  const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
  return new Float32Array([xx, yx, zx, 0, xy, yy, zy, 0, xz, yz, zz, 0, -(xx * e[0] + xy * e[1] + xz * e[2]), -(yx * e[0] + yy * e[1] + yz * e[2]), -(zx * e[0] + zy * e[1] + zz * e[2]), 1]);
}
function m4Mul(a: Float32Array, b: Float32Array): Float32Array {
  const o = new Float32Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
  return o;
}
function m4Apply(m: Float32Array, x: number, y: number, z: number): number[] {
  return [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14]];
}
function rgbOf(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
}

// ---------- shaders ----------
const GLSL_COMMON = `
uniform highp sampler2DShadow uShadow;
uniform mat4 uLightVP[3];
uniform float uFloorY[3];
uniform int uShadowOn;
uniform vec3 uEye;
uniform vec3 uFog;
float shadowAt(vec3 w, vec3 n){
  if(uShadowOn==0) return 1.0;
  int idx=0; float best=1e9;
  for(int i=0;i<3;i++){ float d=w.y-uFloorY[i]; if(d>-0.8 && d<best){best=d; idx=i;} }
  vec4 ls=uLightVP[idx]*vec4(w+n*0.06,1.0);
  vec3 p=ls.xyz/ls.w*0.5+0.5;
  if(p.x<0.0||p.x>1.0||p.y<0.0||p.y>1.0||p.z>1.0) return 1.0;
  p.x=(p.x+float(idx))/3.0;
  vec2 tx=vec2(1.0/${SHADOW_RES * 3}.0, 1.0/${SHADOW_RES}.0)*1.25;
  float s=0.0;
  for(int x=-1;x<=1;x++) for(int y=-1;y<=1;y++) s+=texture(uShadow, vec3(p.xy+vec2(float(x),float(y))*tx, p.z-0.0018));
  return s/9.0;
}
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
vec3 fogged(vec3 c, vec3 w){ float d=length(uEye-w); float f=1.0-exp(-pow(d*0.0022,2.0)); return mix(c,uFog,f*0.5); }
`;

const VS_MESH = `#version 300 es
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNor; layout(location=2) in vec4 aCol;
uniform mat4 uVP; out vec3 vNor; out vec4 vCol; out vec3 vW;
void main(){ vNor=aNor; vCol=aCol; vW=aPos; gl_Position=uVP*vec4(aPos,1.0); }`;

// aCol.a: 0 fixed colour, 1 tinted by instance colour, 2 fixed emissive, 3 tinted emissive
const VS_CAR = `#version 300 es
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNor; layout(location=2) in vec4 aCol;
layout(location=3) in vec4 iPose; layout(location=4) in vec4 iCol;
uniform mat4 uVP; uniform float uScale; out vec3 vNor; out vec4 vCol; out vec3 vW;
void main(){
  float cp=cos(iCol.a), sp=sin(iCol.a), cy=cos(iPose.w), sy=sin(iPose.w);
  vec3 p=aPos*uScale; p=vec3(p.x*cp-p.y*sp, p.x*sp+p.y*cp, p.z);
  vec3 n=aNor; n=vec3(n.x*cp-n.y*sp, n.x*sp+n.y*cp, n.z);
  p=vec3(p.x*cy-p.z*sy, p.y, p.x*sy+p.z*cy);
  n=vec3(n.x*cy-n.z*sy, n.y, n.x*sy+n.z*cy);
  vec3 w=p+iPose.xyz; vW=w; vNor=n;
  bool tint = (aCol.a>0.5 && aCol.a<1.5) || aCol.a>2.5;
  float em = aCol.a>1.5 ? 1.0 : 0.0;
  vCol=vec4(tint ? iCol.rgb*aCol.rgb : aCol.rgb, em);
  gl_Position=uVP*vec4(w,1.0);
}`;

const FS_LIT = `#version 300 es
precision highp float;
in vec3 vNor; in vec4 vCol; in vec3 vW;
uniform vec3 uLight; uniform float uGloss; uniform float uEmis;
${GLSL_COMMON}
out vec4 o;
void main(){
  vec3 n=normalize(vNor);
  vec3 base=vCol.rgb;
  if(vCol.a<0.01 && n.y>0.9){
    float g=vnoise(vW.xz*0.9)*0.6+vnoise(vW.xz*4.3)*0.4;
    base*=0.9+0.16*g;
  }
  float sh=shadowAt(vW,n);
  float d=max(dot(n,uLight),0.0)*sh;
  float hemi=0.5+0.5*n.y;
  vec3 amb=mix(vec3(0.16,0.18,0.24), vec3(0.42,0.45,0.52), hemi)*mix(0.7,1.0,sh);
  vec3 c=base*(amb+d*vec3(0.72,0.70,0.66));
  vec3 v=normalize(uEye-vW); vec3 h=normalize(uLight+v);
  c+=pow(max(dot(n,h),0.0),mix(16.0,90.0,uGloss))*mix(0.08,0.55,uGloss)*d;
  float fr=pow(1.0-max(dot(n,v),0.0),4.0)*uGloss*0.25; c+=fr*vec3(0.55,0.65,0.85);
  if(vCol.a>0.0) c=base*(1.0+uEmis);
  o=vec4(fogged(c,vW),1.0);
}`;

const VS_INST = `#version 300 es
layout(location=0) in vec2 aQ;
layout(location=3) in vec4 iA; layout(location=4) in vec4 iB; layout(location=5) in vec4 iC;
uniform mat4 uVP; out vec2 vUV; out vec4 vB; out vec4 vC; out vec3 vW;
void main(){
  float cy=cos(iA.w), sy=sin(iA.w);
  vec2 l=aQ*iC.xy;
  vec3 w=vec3(iA.x + l.x*cy - l.y*sy, iA.y, iA.z + l.x*sy + l.y*cy);
  vUV=aQ; vB=iB; vC=iC; vW=w;
  gl_Position=uVP*vec4(w,1.0);
}`;

// kind (iC.z): 0 solid bay, 1 hatch, 2 cross hatch, 3 soft shadow, 4 glow ring, 5 translucent zone, 6 light pool, 7 camera wedge
const FS_INST = `#version 300 es
precision highp float;
in vec2 vUV; in vec4 vB; in vec4 vC; in vec3 vW;
${GLSL_COMMON}
out vec4 o;
void main(){
  float k=vC.z; vec3 col=vB.rgb; float a=vB.a;
  vec2 e=abs(vUV)*2.0;
  if(k<2.5){
    if(k>0.5 && k<1.5){ float s=step(0.5,fract((vW.x+vW.z)*1.4)); col=mix(col, col*1.7, s); }
    if(k>1.5){ float s=max(step(0.5,fract((vW.x+vW.z)*1.4)), step(0.5,fract((vW.x-vW.z)*1.4))); col=mix(col, col*1.6, s); }
    float g=vnoise(vW.xz*3.1); col*=0.92+0.1*g;
    float sh=shadowAt(vW, vec3(0,1,0));
    col*=mix(0.5,1.0,sh);
    if(vC.w>0.5){ if(e.x>1.0-0.36/vC.x || e.y>1.0-0.36/vC.y) col=vec3(1.4); }
  } else if(k<3.5){
    float r=length(max(e-vec2(0.55),0.0))/0.45; a*=1.0-smoothstep(0.0,1.0,r);
  } else if(k<4.5){
    float r=length(vUV)*2.0; a*=smoothstep(0.55,0.78,r)*(1.0-smoothstep(0.82,1.0,r)) + 0.22*(1.0-smoothstep(0.0,0.8,r));
    col*=1.6;
  } else if(k<5.5){
    float edge=max(e.x,e.y); a*= edge>0.95 ? 1.0 : 0.18; col*= edge>0.95 ? 1.5 : 1.0;
  } else if(k<6.5){
    float r=length(vUV)*2.0; a*=(1.0-smoothstep(0.0,1.0,r))*0.9;
  } else {
    // camera field of view: a 70-degree wedge facing local +x, soft fill with a crisp rim
    float r=length(vUV)*2.0; float ang=abs(atan(vUV.y, vUV.x));
    float hf=0.61;
    if(r>1.0 || ang>hf) discard;
    float rim=max(smoothstep(0.95,0.99,r), smoothstep(hf-0.03,hf-0.005,ang));
    float fill=0.28*(1.0-0.65*r);
    a*=max(fill, rim*0.9); col*=mix(1.0,1.8,rim);
  }
  o=vec4(fogged(col,vW), a);
}`;

const VS_RIB = `#version 300 es
layout(location=0) in vec3 aPos; layout(location=1) in float aD;
uniform mat4 uVP; out float vD;
void main(){ vD=aD; gl_Position=uVP*vec4(aPos,1.0); }`;
const FS_RIB = `#version 300 es
precision highp float; in float vD; uniform vec4 uCol; uniform float uDash; uniform float uTime; out vec4 o;
void main(){ if(uDash>0.0 && fract(vD/uDash)>0.55) discard;
  float pulse = uDash<0.0 ? 0.65+0.35*smoothstep(0.0,0.2,fract(vD/7.0-uTime*0.6))*(1.0-smoothstep(0.2,0.6,fract(vD/7.0-uTime*0.6))) : 1.0;
  o=vec4(uCol.rgb*(1.0+pulse*0.6), uCol.a); }`;

const VS_SH = `#version 300 es
layout(location=0) in vec3 aPos;
uniform mat4 uLVP; uniform float uFY;
void main(){ gl_Position = (aPos.y<uFY-0.8 || aPos.y>uFY+2.6) ? vec4(0.0,0.0,2.0,1.0) : uLVP*vec4(aPos,1.0); }`;
const VS_SH_CAR = `#version 300 es
layout(location=0) in vec3 aPos; layout(location=3) in vec4 iPose; layout(location=4) in vec4 iCol;
uniform mat4 uLVP; uniform float uFY; uniform float uScale;
void main(){
  float cp=cos(iCol.a), sp=sin(iCol.a), cy=cos(iPose.w), sy=sin(iPose.w);
  vec3 p=aPos*uScale; p=vec3(p.x*cp-p.y*sp, p.x*sp+p.y*cp, p.z); p=vec3(p.x*cy-p.z*sy, p.y, p.x*sy+p.z*cy);
  vec3 w=p+iPose.xyz;
  gl_Position = (w.y<uFY-0.8 || w.y>uFY+2.6) ? vec4(0.0,0.0,2.0,1.0) : uLVP*vec4(w,1.0);
}`;
const FS_SH = `#version 300 es
precision highp float; out vec4 o; void main(){ o=vec4(1.0); }`;

const VS_FULL = `#version 300 es
out vec2 vUV; void main(){ vec2 p=vec2((gl_VertexID<<1)&2, gl_VertexID&2); vUV=p; gl_Position=vec4(p*2.0-1.0,0.0,1.0); }`;
const FS_BRIGHT = `#version 300 es
precision highp float; in vec2 vUV; uniform sampler2D uSrc; uniform float uThr; out vec4 o;
void main(){ vec3 c=texture(uSrc,vUV).rgb; float l=max(max(c.r,c.g),c.b); o=vec4(c*smoothstep(uThr,uThr+0.5,l),1.0); }`;
const FS_BLUR = `#version 300 es
precision highp float; in vec2 vUV; uniform sampler2D uSrc; uniform vec2 uDir; out vec4 o;
void main(){ vec3 c=texture(uSrc,vUV).rgb*0.2270270270;
  c+=texture(uSrc,vUV+uDir*1.3846153846).rgb*0.3162162162; c+=texture(uSrc,vUV-uDir*1.3846153846).rgb*0.3162162162;
  c+=texture(uSrc,vUV+uDir*3.2307692308).rgb*0.0702702703; c+=texture(uSrc,vUV-uDir*3.2307692308).rgb*0.0702702703;
  o=vec4(c,1.0); }`;
const FS_COMP = `#version 300 es
precision highp float; in vec2 vUV; uniform sampler2D uScene; uniform sampler2D uBloom; uniform sampler2D uBloom2; uniform float uBloomK; out vec4 o;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
void main(){
  vec4 s=texture(uScene,vUV);
  vec3 bg=mix(vec3(0.030,0.045,0.075), vec3(0.085,0.115,0.165), vUV.y);
  vec2 q=(vUV-vec2(0.5,0.62))*vec2(1.1,1.8); bg+=vec3(0.05,0.07,0.10)*exp(-dot(q,q)*2.5);
  vec3 c=mix(bg, s.rgb, clamp(s.a,0.0,1.0));
  c+=(texture(uBloom,vUV).rgb*0.65+texture(uBloom2,vUV).rgb*0.55)*uBloomK;
  c=aces(c*1.18);
  float v=smoothstep(1.15,0.3,length((vUV-0.5)*vec2(1.0,1.15))); c*=mix(0.78,1.0,v);
  c+= (fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453)-0.5)/255.0;
  o=vec4(c,1.0);
}`;

// ---------- mesh building ----------
class MeshB {
  d: number[] = [];
  vert(x: number, y: number, z: number, nx: number, ny: number, nz: number, c: number[], a: number) {
    this.d.push(x, y, z, nx, ny, nz, c[0], c[1], c[2], a);
  }
  tri(p: number[][], n: number[], c: number[], a = 0) {
    for (const q of p) this.vert(q[0], q[1], q[2], n[0], n[1], n[2], c, a);
  }
  quad(p0: number[], p1: number[], p2: number[], p3: number[], c: number[], a = 0, up = false) {
    const ux = p1[0] - p0[0], uy = p1[1] - p0[1], uz = p1[2] - p0[2];
    const vx = p3[0] - p0[0], vy = p3[1] - p0[1], vz = p3[2] - p0[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
    if (up && ny < 0) { nx = -nx; ny = -ny; nz = -nz; }
    const n = [nx, ny, nz];
    this.tri([p0, p1, p2], n, c, a);
    this.tri([p0, p2, p3], n, c, a);
  }
  flat(x0: number, x1: number, z0: number, z1: number, y: number, c: number[], a = 0) {
    this.quad([x0, y, z1], [x1, y, z1], [x1, y, z0], [x0, y, z0], c, a, true);
  }
  box(cx: number, y0: number, cz: number, sx: number, sy: number, sz: number, c: number[], top?: number[], yaw = 0, a = 0) {
    const ca = Math.cos(yaw), sa = Math.sin(yaw);
    const P = (lx: number, ly: number, lz: number) => [cx + lx * ca - lz * sa, y0 + ly, cz + lx * sa + lz * ca];
    const hx = sx / 2, hz = sz / 2;
    const b = [P(-hx, 0, -hz), P(hx, 0, -hz), P(hx, 0, hz), P(-hx, 0, hz)];
    const t = [P(-hx, sy, -hz), P(hx, sy, -hz), P(hx, sy, hz), P(-hx, sy, hz)];
    this.quad(t[3], t[2], t[1], t[0], top || c, a);
    this.quad(b[1], b[0], t[0], t[1], c, a);
    this.quad(b[2], b[1], t[1], t[2], c, a);
    this.quad(b[3], b[2], t[2], t[3], c, a);
    this.quad(b[0], b[3], t[3], t[0], c, a);
  }
  prism(profile: number[][], w: number, side: number[], cap: number[], sideA = 0, capA = 0) {
    const n = profile.length;
    for (let i = 1; i < n - 1; i++) {
      this.tri([[profile[0][0], profile[0][1], w], [profile[i][0], profile[i][1], w], [profile[i + 1][0], profile[i + 1][1], w]], [0, 0, 1], side, sideA);
      this.tri([[profile[0][0], profile[0][1], -w], [profile[i + 1][0], profile[i + 1][1], -w], [profile[i][0], profile[i][1], -w]], [0, 0, -1], side, sideA);
    }
    for (let i = 0; i < n; i++) {
      const p = profile[i], q = profile[(i + 1) % n];
      this.quad([p[0], p[1], -w], [q[0], q[1], -w], [q[0], q[1], w], [p[0], p[1], w], cap, capA);
    }
  }
  /** Loft between two convex profiles at z=-w2..w2 (outer) narrowing to the cabin; used for rounded flanks. */
  cylZ(cx: number, cy: number, cz: number, r: number, hw: number, seg: number, c: number[], hub: number[]) {
    for (let i = 0; i < seg; i++) {
      const a0 = (i / seg) * Math.PI * 2, a1 = ((i + 1) / seg) * Math.PI * 2;
      const p0 = [cx + Math.cos(a0) * r, cy + Math.sin(a0) * r], p1 = [cx + Math.cos(a1) * r, cy + Math.sin(a1) * r];
      this.quad([p0[0], p0[1], cz - hw], [p1[0], p1[1], cz - hw], [p1[0], p1[1], cz + hw], [p0[0], p0[1], cz + hw], c);
      const hr = 0.62;
      this.tri([[cx, cy, cz + hw], [cx + (p0[0] - cx) * hr, cy + (p0[1] - cy) * hr, cz + hw], [cx + (p1[0] - cx) * hr, cy + (p1[1] - cy) * hr, cz + hw]], [0, 0, 1], hub);
      this.tri([[cx, cy, cz - hw], [cx + (p1[0] - cx) * hr, cy + (p1[1] - cy) * hr, cz - hw], [cx + (p0[0] - cx) * hr, cy + (p0[1] - cy) * hr, cz - hw]], [0, 0, -1], hub);
      this.quad([cx + (p0[0] - cx) * hr, cy + (p0[1] - cy) * hr, cz + hw], [p0[0], p0[1], cz + hw], [p1[0], p1[1], cz + hw], [cx + (p1[0] - cx) * hr, cy + (p1[1] - cy) * hr, cz + hw], c);
      this.quad([p0[0], p0[1], cz - hw], [cx + (p0[0] - cx) * hr, cy + (p0[1] - cy) * hr, cz - hw], [cx + (p1[0] - cx) * hr, cy + (p1[1] - cy) * hr, cz - hw], [p1[0], p1[1], cz - hw], c);
    }
  }
}

/** Hatchback-style car, 4.3 m long, built from layered convex sections so the flanks taper. */
function buildCarMesh(): Float32Array {
  const m = new MeshB();
  const body = [1, 1, 1];
  const glass = rgbOf('#16222f');
  const trim = rgbOf('#1c2026');
  const tyre = rgbOf('#101215');
  const hub = rgbOf('#9aa1ab');
  // lower body: bumper-to-bumper side profile, slightly tapered top via a second narrower band
  m.prism([[-2.08, 0.3], [2.04, 0.3], [2.18, 0.42], [2.2, 0.64], [2.1, 0.78], [-2.05, 0.82], [-2.16, 0.66], [-2.15, 0.42]], 0.86, body, body, 1, 1);
  m.prism([[-2.0, 0.78], [2.05, 0.76], [1.95, 0.9], [1.05, 0.96], [-1.75, 0.98], [-2.02, 0.9]], 0.8, body, body, 1, 1);
  // dark rocker panel and bumpers
  m.box(0, 0.26, 0, 3.2, 0.12, 1.74, trim);
  m.box(2.12, 0.3, 0, 0.16, 0.18, 1.6, trim);
  m.box(-2.12, 0.3, 0, 0.16, 0.18, 1.6, trim);
  // cabin: glass sides and screens with a body-coloured roof and pillars
  const cab = [[1.0, 0.96], [0.38, 1.42], [-1.05, 1.46], [-1.68, 0.98]];
  const w = 0.71;
  for (let i = 1; i < cab.length - 1; i++) {
    m.tri([[cab[0][0], cab[0][1], w], [cab[i][0], cab[i][1], w], [cab[i + 1][0], cab[i + 1][1], w]], [0, 0, 1], glass);
    m.tri([[cab[0][0], cab[0][1], -w], [cab[i + 1][0], cab[i + 1][1], -w], [cab[i][0], cab[i][1], -w]], [0, 0, -1], glass);
  }
  for (let i = 0; i < cab.length; i++) {
    const p = cab[i], q = cab[(i + 1) % cab.length];
    const roof = i === 1;
    m.quad([p[0], p[1], -w], [q[0], q[1], -w], [q[0], q[1], w], [p[0], p[1], w], roof ? body : glass, roof ? 1 : 0);
  }
  m.box(-0.33, 0.97, w - 0.02, 0.09, 0.47, 0.05, body, body, 0, 1);
  m.box(-0.33, 0.97, -w + 0.02, 0.09, 0.47, 0.05, body, body, 0, 1);
  // mirrors
  m.box(0.85, 0.9, 0.93, 0.18, 0.12, 0.16, body, body, 0, 1);
  m.box(0.85, 0.9, -0.93, 0.18, 0.12, 0.16, body, body, 0, 1);
  // wheels with hubs
  for (const x of [-1.32, 1.36]) for (const z of [-0.79, 0.79]) m.cylZ(x, 0.33, z, 0.33, 0.12, 12, tyre, hub);
  // head and tail lights (emissive)
  const head = [1.0, 0.96, 0.86], tail = [0.95, 0.1, 0.12];
  m.quad([2.205, 0.6, -0.78], [2.205, 0.6, -0.42], [2.205, 0.72, -0.42], [2.205, 0.72, -0.78], head, 2);
  m.quad([2.205, 0.6, 0.42], [2.205, 0.6, 0.78], [2.205, 0.72, 0.78], [2.205, 0.72, 0.42], head, 2);
  m.quad([-2.165, 0.64, 0.8], [-2.165, 0.64, 0.45], [-2.165, 0.76, 0.45], [-2.165, 0.76, 0.8], tail, 2);
  m.quad([-2.165, 0.64, -0.45], [-2.165, 0.64, -0.8], [-2.165, 0.76, -0.8], [-2.165, 0.76, -0.45], tail, 2);
  return new Float32Array(m.d);
}

/** Bay guidance indicator: a small dome lamp in a dark housing, lamp tinted per instance and emissive. */
function buildLedMesh(): Float32Array {
  const m = new MeshB();
  m.box(0, 0.12, 0, 0.42, 0.1, 0.42, rgbOf('#2a3140'));
  m.box(0, -0.1, 0, 0.4, 0.22, 0.4, [1, 1, 1], [1, 1, 1], 0, 3);
  m.box(0, 0.22, 0, 0.05, 0.5, 0.05, rgbOf('#4a5263'));
  return new Float32Array(m.d);
}

const CAR_PALETTE = ['#e9e8e4', '#cfd2d6', '#a3a9b2', '#5d6673', '#2a313c', '#8c2b2b', '#2c4a72', '#b9a382', '#3d5a52', '#f2f0ea', '#1d2430', '#c7c9cc'];
const ZONE_BAND: Record<ZoneId, string> = { A: '#2f7cf6', B: '#f2c230', C: '#f0703c' };

const GC = {
  slabTop: rgbOf('#565c66'),
  slabSide: rgbOf('#2c323c'),
  lane: rgbOf('#33373e'),
  laneLine: rgbOf('#e9edf2'),
  laneYellow: rgbOf('#e8b931'),
  walk: rgbOf('#6c7380'),
  wall: rgbOf('#7d8591'),
  wallTop: rgbOf('#a3aab4'),
  column: rgbOf('#8d949f'),
  lift: rgbOf('#e3e7ea'),
  liftGlass: rgbOf('#2c6b75'),
  liftSign: rgbOf('#2f7cf6'),
  ramp: rgbOf('#4a5058'),
  road: rgbOf('#33383f'),
  booth: rgbOf('#b8c0cb'),
  bayLine: rgbOf('#f1f3f6'),
  rail: rgbOf('#2b3038'),
  tube: rgbOf('#e8f1ff'),
  available: rgbOf('#27845b'),
  occupied: rgbOf('#4a515c'),
  reserved: rgbOf('#6a54bd'),
  departing: rgbOf('#b97c27'),
  hatch: rgbOf('#555c67'),
  typeOku: rgbOf('#3d7cf0'),
  typeLadies: rgbOf('#ef7fa9'),
  typeMember: rgbOf('#e3c35a'),
  ledFree: rgbOf('#2bff88'),
  ledTaken: rgbOf('#ff3344'),
  ledLeaving: rgbOf('#ffae1a'),
  ledHeld: rgbOf('#a77bff'),
  ledOku: rgbOf('#3d8bff'),
  ledLadies: rgbOf('#ff6fb8'),
  ringSearch: rgbOf('#2dd4bf'),
  ringSlow: rgbOf('#f5a524'),
  ringRes: rgbOf('#a78bfa'),
  ringSel: rgbOf('#ffffff'),
  route: rgbOf('#38e1c8'),
  fog: rgbOf('#121a26')
};
const GL_TYPE_COL: Record<string, number[]> = { oku: GC.typeOku, ladies: GC.typeLadies, member: GC.typeMember };

interface GlPick { kind: 'vehicle' | 'bay'; id: number }

/** What main.ts and the presentation need from either renderer. */
export interface SceneView {
  ok: boolean;
  dirty: boolean;
  readonly animating: boolean;
  resize(): void;
  fit(animate?: boolean): void;
  render(alpha: number): void;
  focusVehicle(v: Vehicle): void;
  focusBay(b: Bay): void;
  followId: number | null;
  stopFollow(): void;
}

interface PostTargets {
  w: number;
  h: number;
  msaaFbo: WebGLFramebuffer;
  sceneFbo: WebGLFramebuffer;
  sceneTex: WebGLTexture;
  bloomA: WebGLTexture;
  bloomB: WebGLTexture;
  bloomC: WebGLTexture;
  bloomD: WebGLTexture;
  fbA: WebGLFramebuffer;
  fbB: WebGLFramebuffer;
  fbC: WebGLFramebuffer;
  fbD: WebGLFramebuffer;
  rbs: WebGLRenderbuffer[];
}

export class GLScene {
  canvas: HTMLCanvasElement;
  gl: WebGL2RenderingContext;
  ok = true;
  dirty = true;
  w = 800;
  h = 500;
  dpr = 1;
  fov = 30 * GL_DEG;
  cam: GlCam = { yaw: -8 * GL_DEG, pitch: 27 * GL_DEG, dist: 160, tx: 28, ty: -20, tz: 16 };
  followId: number | null = null;
  private tween: { from: GlCam; to: GlCam; t0: number; dur: number } | null = null;
  private progLit!: WebGLProgram;
  private progCar!: WebGLProgram;
  private progInst!: WebGLProgram;
  private progRib!: WebGLProgram;
  private progSh!: WebGLProgram;
  private progShCar!: WebGLProgram;
  private progBright!: WebGLProgram;
  private progBlur!: WebGLProgram;
  private progComp!: WebGLProgram;
  private staticVao!: WebGLVertexArrayObject;
  private staticBuf!: WebGLBuffer;
  private staticCount = 0;
  private staticKey = '';
  private carVao!: WebGLVertexArrayObject;
  private carInst!: WebGLBuffer;
  private carCount = 0;
  private ledVao!: WebGLVertexArrayObject;
  private ledInst!: WebGLBuffer;
  private ledCount = 0;
  private quadVao!: WebGLVertexArrayObject;
  private instBuf!: WebGLBuffer;
  private ribVao!: WebGLVertexArrayObject;
  private ribBuf!: WebGLBuffer;
  private fullVao!: WebGLVertexArrayObject;
  private shadowTex: WebGLTexture | null = null;
  private shadowFbo: WebGLFramebuffer | null = null;
  private post: PostTargets | null = null;
  private postOk = true;
  private hdr = false;
  private lightVP: Float32Array[] = [new Float32Array(16), new Float32Array(16), new Float32Array(16)];
  private vp: Float32Array = new Float32Array(16);
  private eye = [0, 0, 0];
  private labels: HTMLElement;
  private tip: HTMLElement;
  private labelPool = new Map<string, HTMLElement>();
  private hover: GlPick | null = null;
  private hoverXY = [0, 0];
  private drag: { x: number; y: number; moved: number; mode: 'orbit' | 'pan'; id: number } | null = null;
  private pointers = new Map<number, { x: number; y: number }>();
  private pinch: { d: number; cx: number; cy: number } | null = null;
  private lastAlpha = 1;
  private lastFrame = performance.now();
  private interactT = 0;
  /** True while something on screen moves by itself (blinking bay light, flowing route). */
  private liveFx = false;
  private carPoses: { v: Vehicle; x: number; y: number; z: number; a: number }[] = [];
  private uniformCache = new Map<WebGLProgram, Map<string, WebGLUniformLocation | null>>();

  constructor(canvas: HTMLCanvasElement, labels: HTMLElement, tip: HTMLElement) {
    this.canvas = canvas;
    this.labels = labels;
    this.tip = tip;
    const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, premultipliedAlpha: false, powerPreference: 'high-performance' });
    if (!gl) { this.ok = false; this.gl = null as unknown as WebGL2RenderingContext; return; }
    this.gl = gl;
    try {
      this.init();
    } catch (e) {
      console.warn('WebGL scene unavailable, using canvas fallback', e);
      this.ok = false;
      return;
    }
    this.bindInput();
    this.resize();
    this.fit(false);
  }

  private U(p: WebGLProgram, name: string): WebGLUniformLocation | null {
    let m = this.uniformCache.get(p);
    if (!m) { m = new Map(); this.uniformCache.set(p, m); }
    if (!m.has(name)) m.set(name, this.gl.getUniformLocation(p, name));
    return m.get(name) as WebGLUniformLocation | null;
  }

  // ---------- setup ----------
  private program(vs: string, fs: string): WebGLProgram {
    const gl = this.gl;
    const mk = (type: number, src: string) => {
      const s = gl.createShader(type) as WebGLShader;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader');
      return s;
    };
    const p = gl.createProgram() as WebGLProgram;
    gl.attachShader(p, mk(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'link');
    return p;
  }

  private meshAttribs(stride = 40) {
    const gl = this.gl;
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 3, gl.FLOAT, false, stride, 12);
    gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 4, gl.FLOAT, false, stride, 24);
  }

  private instancedMesh(data: Float32Array): { vao: WebGLVertexArrayObject; inst: WebGLBuffer; count: number } {
    const gl = this.gl;
    const vao = gl.createVertexArray() as WebGLVertexArrayObject;
    gl.bindVertexArray(vao);
    const b = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    this.meshAttribs();
    const inst = gl.createBuffer() as WebGLBuffer;
    gl.bindBuffer(gl.ARRAY_BUFFER, inst);
    gl.enableVertexAttribArray(3); gl.vertexAttribPointer(3, 4, gl.FLOAT, false, 32, 0); gl.vertexAttribDivisor(3, 1);
    gl.enableVertexAttribArray(4); gl.vertexAttribPointer(4, 4, gl.FLOAT, false, 32, 16); gl.vertexAttribDivisor(4, 1);
    return { vao, inst, count: data.length / 10 };
  }

  private init() {
    const gl = this.gl;
    this.hdr = !!gl.getExtension('EXT_color_buffer_float');
    gl.getExtension('OES_texture_float_linear');
    this.progLit = this.program(VS_MESH, FS_LIT);
    this.progCar = this.program(VS_CAR, FS_LIT);
    this.progInst = this.program(VS_INST, FS_INST);
    this.progRib = this.program(VS_RIB, FS_RIB);
    this.progSh = this.program(VS_SH, FS_SH);
    this.progShCar = this.program(VS_SH_CAR, FS_SH);
    this.progBright = this.program(VS_FULL, FS_BRIGHT);
    this.progBlur = this.program(VS_FULL, FS_BLUR);
    this.progComp = this.program(VS_FULL, FS_COMP);
    this.staticVao = gl.createVertexArray() as WebGLVertexArrayObject;
    this.staticBuf = gl.createBuffer() as WebGLBuffer;
    gl.bindVertexArray(this.staticVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.staticBuf);
    this.meshAttribs();
    const car = this.instancedMesh(buildCarMesh());
    this.carVao = car.vao; this.carInst = car.inst; this.carCount = car.count;
    const led = this.instancedMesh(buildLedMesh());
    this.ledVao = led.vao; this.ledInst = led.inst; this.ledCount = led.count;
    this.quadVao = gl.createVertexArray() as WebGLVertexArrayObject;
    gl.bindVertexArray(this.quadVao);
    const qb = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, qb);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5, 0.5, -0.5, 0.5]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 8, 0);
    this.instBuf = gl.createBuffer() as WebGLBuffer;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf);
    for (let i = 0; i < 3; i++) {
      gl.enableVertexAttribArray(3 + i);
      gl.vertexAttribPointer(3 + i, 4, gl.FLOAT, false, 48, i * 16);
      gl.vertexAttribDivisor(3 + i, 1);
    }
    this.ribVao = gl.createVertexArray() as WebGLVertexArrayObject;
    gl.bindVertexArray(this.ribVao);
    this.ribBuf = gl.createBuffer() as WebGLBuffer;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.ribBuf);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 16, 0);
    gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 16, 12);
    this.fullVao = gl.createVertexArray() as WebGLVertexArrayObject;
    gl.bindVertexArray(null);
    this.initShadow();
    this.canvas.addEventListener('webglcontextlost', (e) => { e.preventDefault(); this.ok = false; });
  }

  private initShadow() {
    const gl = this.gl;
    try {
      const t = gl.createTexture() as WebGLTexture;
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texStorage2D(gl.TEXTURE_2D, 1, gl.DEPTH_COMPONENT24, SHADOW_RES * 3, SHADOW_RES);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_MODE, gl.COMPARE_REF_TO_TEXTURE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_FUNC, gl.LEQUAL);
      const fb = gl.createFramebuffer() as WebGLFramebuffer;
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, t, 0);
      gl.drawBuffers([gl.NONE]);
      gl.readBuffer(gl.NONE);
      const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      if (ok) { this.shadowTex = t; this.shadowFbo = fb; }
    } catch {
      this.shadowTex = null;
      this.shadowFbo = null;
    }
  }

  private makeTex(w: number, h: number, fmt: number): WebGLTexture {
    const gl = this.gl;
    const t = gl.createTexture() as WebGLTexture;
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texStorage2D(gl.TEXTURE_2D, 1, fmt, w, h);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  private fbFor(t: WebGLTexture): WebGLFramebuffer {
    const gl = this.gl;
    const fb = gl.createFramebuffer() as WebGLFramebuffer;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    return fb;
  }

  private ensurePost() {
    const gl = this.gl;
    const W = this.canvas.width, H = this.canvas.height;
    if (!this.postOk) return;
    if (this.post && this.post.w === W && this.post.h === H) return;
    if (this.post) {
      const p = this.post;
      for (const f of [p.msaaFbo, p.sceneFbo, p.fbA, p.fbB, p.fbC, p.fbD]) gl.deleteFramebuffer(f);
      for (const t of [p.sceneTex, p.bloomA, p.bloomB, p.bloomC, p.bloomD]) gl.deleteTexture(t);
      for (const r of p.rbs) gl.deleteRenderbuffer(r);
      this.post = null;
    }
    try {
      const fmt = this.hdr ? gl.RGBA16F : gl.RGBA8;
      const samples = Math.min(4, gl.getParameter(gl.MAX_SAMPLES) as number);
      const msaaFbo = gl.createFramebuffer() as WebGLFramebuffer;
      gl.bindFramebuffer(gl.FRAMEBUFFER, msaaFbo);
      const crb = gl.createRenderbuffer() as WebGLRenderbuffer;
      gl.bindRenderbuffer(gl.RENDERBUFFER, crb);
      gl.renderbufferStorageMultisample(gl.RENDERBUFFER, samples, fmt, W, H);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.RENDERBUFFER, crb);
      const drb = gl.createRenderbuffer() as WebGLRenderbuffer;
      gl.bindRenderbuffer(gl.RENDERBUFFER, drb);
      gl.renderbufferStorageMultisample(gl.RENDERBUFFER, samples, gl.DEPTH_COMPONENT24, W, H);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, drb);
      if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('msaa fbo');
      const sceneTex = this.makeTex(W, H, fmt);
      const sceneFbo = this.fbFor(sceneTex);
      const hw = Math.max(1, W >> 1), hh = Math.max(1, H >> 1), qw = Math.max(1, W >> 2), qh = Math.max(1, H >> 2);
      const bloomA = this.makeTex(hw, hh, fmt), bloomB = this.makeTex(hw, hh, fmt);
      const bloomC = this.makeTex(qw, qh, fmt), bloomD = this.makeTex(qw, qh, fmt);
      const fbA = this.fbFor(bloomA), fbB = this.fbFor(bloomB), fbC = this.fbFor(bloomC), fbD = this.fbFor(bloomD);
      if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('bloom fbo');
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      this.post = { w: W, h: H, msaaFbo, sceneFbo, sceneTex, bloomA, bloomB, bloomC, bloomD, fbA, fbB, fbC, fbD, rbs: [crb, drb] };
    } catch (e) {
      console.warn('Post-processing unavailable; rendering directly', e);
      this.postOk = false;
      this.post = null;
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    }
  }

  resize() {
    if (!this.ok) return;
    const r = this.canvas.getBoundingClientRect();
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.w = Math.max(200, r.width);
    this.h = Math.max(200, r.height);
    this.canvas.width = Math.round(this.w * this.dpr);
    this.canvas.height = Math.round(this.h * this.dpr);
    this.dirty = true;
  }

  floorY(f: number): number {
    if (store.floorView === 'all') return -f * GL_FLOOR_SPACING;
    return -(f - (store.floorView as number)) * GL_FLOOR_SPACING;
  }

  floorVisible(f: number): boolean {
    return store.floorView === 'all' || store.floorView === f;
  }

  // ---------- static geometry ----------
  private buildStatic() {
    const L = store.sim.L;
    const m = new MeshB();
    const lights = store.layers.lights;
    const cctv = store.layers.cctv;
    for (const f of [0, 1, 2]) {
      if (!this.floorVisible(f)) continue;
      const y = this.floorY(f);
      m.box((SLAB.x0 + SLAB.x1) / 2, y - 0.7, (SLAB.z0 + SLAB.z1) / 2, SLAB.x1 - SLAB.x0, 0.7, SLAB.z1 - SLAB.z0, GC.slabSide, GC.slabTop);
      m.flat(0.4, 73.6, A1_Z - 3, A1_Z + 3, y + 0.01, GC.lane);
      m.flat(0.4, 73.6, A2_Z - 3, A2_Z + 3, y + 0.01, GC.lane);
      m.flat(0.4, 6.4, A1_Z + 3, A2_Z - 3, y + 0.01, GC.lane);
      m.flat(66.6, 73.6, A1_Z + 3, A2_Z - 3, y + 0.01, GC.lane);
      m.flat(6.6, 66.4, 16.15, 20.85, y + 0.012, GC.walk);
      m.flat(6.6, 66.4, 16.1, 16.25, y + 0.02, GC.laneYellow);
      m.flat(6.6, 66.4, 20.75, 20.9, y + 0.02, GC.laneYellow);
      for (let x = 8; x < 66; x += 4) {
        m.flat(x, x + 2, A1_Z - 0.07, A1_Z + 0.07, y + 0.02, GC.laneLine);
        m.flat(x, x + 2, A2_Z - 0.07, A2_Z + 0.07, y + 0.02, GC.laneLine);
      }
      for (let x = 12; x < 66; x += 12) { this.arrow(m, x, y + 0.025, A1_Z + 1.6, 1, 0); this.arrow(m, x + 4, y + 0.025, A2_Z - 1.6, -1, 0); }
      this.arrow(m, 70, y + 0.025, 16, 0, 1);
      this.arrow(m, 3.4, y + 0.025, 16, 0, -1);
      for (const z of ZONES) {
        const lx = LIFT_X[z];
        for (let k = -1.4; k <= 1.41; k += 0.7) {
          m.flat(lx + k - 0.2, lx + k + 0.2, A1_Z - 2.8, A1_Z + 2.8, y + 0.02, GC.laneLine);
          m.flat(lx + k - 0.2, lx + k + 0.2, A2_Z - 2.8, A2_Z + 2.8, y + 0.02, GC.laneLine);
        }
      }
      for (const zone of ZONES) {
        const x0 = ZONE_X0[zone];
        const n = ZONE_COUNTS[zone];
        for (let row = 0; row < 3; row++) {
          const zc = ROW_Z[row];
          for (let k = 0; k <= n; k++) {
            const x = x0 + k * BAY_W;
            m.flat(x - 0.06, x + 0.06, zc - 2.5, zc + 2.5, y + 0.035, GC.bayLine);
          }
          const back = row === 0 ? zc - 2.5 : zc + 2.5;
          m.flat(x0, x0 + n * BAY_W, back - 0.06, back + 0.06, y + 0.035, GC.bayLine);
          // wheel stops
          for (let k = 0; k < n; k++) {
            const x = x0 + k * BAY_W + BAY_W / 2;
            const zs = row === 0 ? zc - 1.9 : zc + 1.9;
            m.box(x, y, zs, 1.5, 0.12, 0.2, rgbOf('#c9ccd1'), rgbOf('#e8b931'));
          }
        }
      }
      const H = 1.0;
      const walls: [number, number, number, number][] = [
        [SLAB.x0, SLAB.x1, SLAB.z0, SLAB.z0 + 0.3], [SLAB.x0, SLAB.x1, SLAB.z1 - 0.3, SLAB.z1],
        [SLAB.x0, SLAB.x0 + 0.3, SLAB.z0, A1_Z - 3], [SLAB.x0, SLAB.x0 + 0.3, A1_Z + 3, A2_Z - 3], [SLAB.x0, SLAB.x0 + 0.3, A2_Z + 3, SLAB.z1],
        [SLAB.x1 - 0.3, SLAB.x1, SLAB.z0, A1_Z - 3], [SLAB.x1 - 0.3, SLAB.x1, A1_Z + 3, A2_Z - 3], [SLAB.x1 - 0.3, SLAB.x1, A2_Z + 3, SLAB.z1]
      ];
      for (const w of walls) m.box((w[0] + w[1]) / 2, y, (w[2] + w[3]) / 2, w[1] - w[0], H, w[3] - w[2], GC.wall, GC.wallTop);
      // structural columns with zone colour bands (wayfinding paint)
      for (const zone of ZONES) {
        const x0 = ZONE_X0[zone];
        const n = ZONE_COUNTS[zone];
        const band = rgbOf(ZONE_BAND[zone]);
        for (let k = 0; k <= n; k += n === 6 ? 3 : 7) {
          const x = x0 + k * BAY_W;
          for (const zc of [0.6, 31.4, 16.6]) {
            m.box(x, y, zc, 0.6, 2.6, 0.6, GC.column, GC.wallTop);
            m.box(x, y + 1.05, zc, 0.64, 0.5, 0.64, band, band);
            m.box(x, y, zc, 0.66, 0.25, 0.66, rgbOf('#e8b931'), rgbOf('#e8b931'));
          }
        }
      }
      // lift lobbies
      for (const z of ZONES) {
        const lx = LIFT_X[z];
        m.box(lx, y, LIFT_Z, 4.6, 2.7, 4.0, GC.lift, rgbOf('#c9d0d8'));
        m.box(lx, y + 0.1, LIFT_Z - 2.02, 2.2, 2.1, 0.06, GC.liftGlass, undefined, 0, 0);
        m.box(lx, y + 0.1, LIFT_Z + 2.02, 2.2, 2.1, 0.06, GC.liftGlass, undefined, 0, 0);
        m.box(lx, y + 2.7, LIFT_Z, 4.7, 0.3, 4.1, GC.liftSign, GC.liftSign, 0, 0);
        m.box(lx, y + 2.55, LIFT_Z - 2.07, 2.4, 0.08, 0.04, rgbOf('#bfe0ff'), undefined, 0, 2);
        m.box(lx, y + 2.55, LIFT_Z + 2.07, 2.4, 0.08, 0.04, rgbOf('#bfe0ff'), undefined, 0, 2);
        m.box(lx - 1.6, y, LIFT_Z - 2.6, 0.2, 0.9, 0.2, rgbOf('#e8b931'));
        m.box(lx + 1.6, y, LIFT_Z - 2.6, 0.2, 0.9, 0.2, rgbOf('#e8b931'));
      }
      if (lights) {
        // cable trays above each bay row and fluorescent tubes above the aisles
        for (const zone of ZONES) {
          const x0 = ZONE_X0[zone], x1 = x0 + ZONE_COUNTS[zone] * BAY_W;
          for (const zc of [ROW_Z[0] + 2.3, ROW_Z[1] - 2.3, ROW_Z[2] - 2.3]) m.box((x0 + x1) / 2, y + 2.95, zc, x1 - x0, 0.06, 0.12, GC.rail);
        }
        for (let x = 6; x < 70; x += 7) {
          m.box(x + 1.2, y + 3.1, A1_Z, 2.4, 0.08, 0.14, GC.tube, GC.tube, 0, 2);
          m.box(x + 1.2, y + 3.1, A2_Z, 2.4, 0.08, 0.14, GC.tube, GC.tube, 0, 2);
        }
      }
      if (cctv) {
        for (const c of this.cctvSpots(f)) {
          m.box(c.x, y + 2.35, c.z, 0.5, 0.26, 0.26, rgbOf('#e6e9ee'), rgbOf('#f4f6f8'), c.a);
          m.box(c.x + Math.cos(c.a) * 0.3, y + 2.4, c.z + Math.sin(c.a) * 0.3, 0.08, 0.14, 0.14, rgbOf('#ff3344'), rgbOf('#ff3344'), c.a, 2);
        }
      }
      for (const e of L.edges) {
        if (e.kind === 'aisle' || e.kind === 'connector') continue;
        const a = L.nodes[e.from], b = L.nodes[e.to];
        if (e.kind === 'ramp') {
          if (store.floorView === 'all') this.ramp(m, a.x, a.z, this.floorY(a.floor), b.x, b.z, this.floorY(b.floor), 0, 1);
          else if (a.floor === f) this.ramp(m, a.x, a.z, this.floorY(a.floor), b.x, b.z, this.floorY(b.floor), 0, 0.35);
          else if (b.floor === f) this.ramp(m, a.x, a.z, this.floorY(a.floor), b.x, b.z, this.floorY(b.floor), 0.65, 1);
          continue;
        }
        if (a.floor !== f || b.floor !== f) continue;
        this.road(m, a.x, a.z, b.x, b.z, y + 0.005);
      }
      if (f === 0) {
        m.box(-12, y, 4.3, 1.8, 2.3, 1.8, GC.booth, rgbOf('#d5dbe4'));
        m.box(-12, y, 27.7, 1.8, 2.3, 1.8, GC.booth, rgbOf('#d5dbe4'));
        m.box(-12, y + 2.3, 4.3, 2.2, 0.15, 2.2, rgbOf('#2f7cf6'), rgbOf('#2f7cf6'));
        m.box(-12, y + 2.3, 27.7, 2.2, 0.15, 2.2, rgbOf('#2f7cf6'), rgbOf('#2f7cf6'));
        m.box(-12, y, 24, 0.25, 1.05, 0.25, rgbOf('#f2c14e'));
        m.box(-12, y + 1.0, 24.0, 0.18, 0.18, 5.4, rgbOf('#f2c14e'));
        m.box(-12, y, 8, 0.25, 1.05, 0.25, rgbOf('#f2c14e'));
        // overhead entrance gantry with an LED availability board
        m.box(-16, y, 4.4, 0.3, 4.2, 0.3, GC.column);
        m.box(-16, y, 11.6, 0.3, 4.2, 0.3, GC.column);
        m.box(-16, y + 3.6, 8, 0.6, 1.0, 7.6, rgbOf('#15181d'));
      }
    }
    const data = new Float32Array(m.d);
    const gl = this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.staticBuf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    this.staticCount = data.length / 10;
  }

  private cctvSpots(f: number): { x: number; z: number; a: number }[] {
    void f;
    const out: { x: number; z: number; a: number }[] = [];
    for (const zone of ZONES) {
      const xm = ZONE_X0[zone] + (ZONE_COUNTS[zone] * BAY_W) / 2;
      out.push({ x: xm, z: 0.9, a: Math.PI / 2 });
      out.push({ x: xm, z: 31.1, a: -Math.PI / 2 });
    }
    out.push({ x: 1.2, z: 16, a: 0 });
    out.push({ x: 72.8, z: 16, a: Math.PI });
    return out;
  }

  private arrow(m: MeshB, x: number, y: number, z: number, dx: number, dz: number) {
    const px = -dz, pz = dx, s = 0.9;
    const tip = [x + dx * 1.6, y, z + dz * 1.6];
    const l = [x + px * s, y, z + pz * s];
    const r = [x - px * s, y, z - pz * s];
    const c = GC.laneLine.map((v) => v * 0.85);
    m.tri([tip, r, l], [0, 1, 0], c);
    m.flat(Math.min(x, x - dx * 1.4) - (dz ? 0.18 : 0), Math.max(x, x - dx * 1.4) + (dz ? 0.18 : 0), Math.min(z, z - dz * 1.4) - (dx ? 0.18 : 0), Math.max(z, z - dz * 1.4) + (dx ? 0.18 : 0), y, c);
  }

  private road(m: MeshB, x0: number, z0: number, x1: number, z1: number, y: number) {
    const a = Math.atan2(z1 - z0, x1 - x0);
    const wx = -Math.sin(a) * 3, wz = Math.cos(a) * 3;
    const ex = Math.cos(a) * 3, ez = Math.sin(a) * 3;
    m.quad([x0 - ex - wx, y, z0 - ez - wz], [x1 + ex - wx, y, z1 + ez - wz], [x1 + ex + wx, y, z1 + ez + wz], [x0 - ex + wx, y, z0 - ez + wz], GC.road, 0, true);
  }

  private rampKeys = new Set<string>();
  private ramp(m: MeshB, ax: number, az: number, ay: number, bx: number, bz: number, by: number, k0: number, k1: number) {
    const key = `${ax},${az},${ay},${bx},${bz},${by},${k0},${k1}`;
    if (this.rampKeys.has(key)) return;
    this.rampKeys.add(key);
    const P = (k: number) => [ax + (bx - ax) * k, ay + (by - ay) * k, az + (bz - az) * k];
    const p0 = P(k0), p1 = P(k1);
    const w = 3;
    m.quad([p0[0] - w, p0[1], p0[2]], [p0[0] + w, p0[1], p0[2]], [p1[0] + w, p1[1], p1[2]], [p1[0] - w, p1[1], p1[2]], GC.ramp, 0, true);
    m.quad([p1[0] - w, p1[1] - 0.4, p1[2]], [p1[0] + w, p1[1] - 0.4, p1[2]], [p0[0] + w, p0[1] - 0.4, p0[2]], [p0[0] - w, p0[1] - 0.4, p0[2]], GC.slabSide);
    for (const s of [-1, 1]) {
      const x = p0[0] + s * w;
      m.quad([x, p0[1], p0[2]], [x, p1[1], p1[2]], [x, p1[1] + 0.8, p1[2]], [x, p0[1] + 0.8, p0[2]], GC.wall);
      m.quad([x, p0[1] + 0.8, p0[2]], [x, p1[1] + 0.8, p1[2]], [x, p1[1], p1[2]], [x, p0[1], p0[2]], GC.wall);
      // yellow kerb line on the deck edge
      m.quad([x - s * 0.25, p0[1] + 0.02, p0[2]], [x - s * 0.05, p0[1] + 0.02, p0[2]], [x - s * 0.05, p1[1] + 0.02, p1[2]], [x - s * 0.25, p1[1] + 0.02, p1[2]], GC.laneYellow, 0, true);
    }
    const dz = Math.sign(bz - az);
    for (let k = k0 + 0.12; k < k1 - 0.06; k += 0.22) {
      const c = P(k);
      const tip = [c[0], c[1] + 0.03, c[2] + dz * 1.2];
      m.tri([tip, [c[0] + 1.1 * dz, c[1] + 0.03, c[2]], [c[0] - 1.1 * dz, c[1] + 0.03, c[2]]], [0, 1, 0], GC.laneLine.map((x) => x * 0.7));
    }
  }

  // ---------- camera ----------
  defaultCam(): GlCam {
    if (store.planView) return { yaw: 0, pitch: 88 * GL_DEG, dist: 120, tx: 28, ty: 0, tz: 16 };
    // On a tall, narrow viewport (phones) turn the long side of the deck away from the viewer so the
    // model fills the frame instead of shrinking to fit its width.
    const narrow = this.w < 640 && this.h > this.w * 0.9;
    if (narrow) return store.floorView === 'all' ? { yaw: -52 * GL_DEG, pitch: 30 * GL_DEG, dist: 160, tx: 28, ty: -20, tz: 16 } : { yaw: -50 * GL_DEG, pitch: 44 * GL_DEG, dist: 110, tx: 30, ty: 0, tz: 16 };
    return store.floorView === 'all' ? { yaw: -8 * GL_DEG, pitch: 27 * GL_DEG, dist: 160, tx: 28, ty: -20, tz: 16 } : { yaw: -16 * GL_DEG, pitch: 40 * GL_DEG, dist: 110, tx: 30, ty: 0, tz: 16 };
  }

  private basisOf(c: GlCam) {
    const cp = Math.cos(c.pitch), sp = Math.sin(c.pitch), cy = Math.cos(c.yaw), sy = Math.sin(c.yaw);
    const back = [cp * sy, sp, cp * cy];
    const right = [cy, 0, -sy];
    const up = [-sy * sp, cp, -cy * sp];
    return { back, right, up };
  }

  private padR(): number {
    return store.driver.collapsed || this.w < 640 ? 24 : Math.min(282, this.w * 0.34);
  }

  fit(animate = true) {
    if (!this.ok) return;
    this.followId = null;
    const target = this.defaultCam();
    const { right, up } = this.basisOf(target);
    const floors = [0, 1, 2].filter((f) => this.floorVisible(f));
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    const cx = 28, cz = 16, cyMid = floors.reduce((a, f) => a + this.floorY(f), 0) / floors.length;
    for (const f of floors) {
      const y0 = this.floorY(f);
      const xs = f === 0 ? [-30, 82] : [-8, 82];
      for (const x of xs) for (const z of [-1, 35]) for (const y of [y0 - 0.7, y0 + 3]) {
        const px = x - cx, py = y - cyMid, pz = z - cz;
        const sx = px * right[0] + pz * right[2];
        const sy = px * up[0] + py * up[1] + pz * up[2];
        minX = Math.min(minX, sx); maxX = Math.max(maxX, sx); minY = Math.min(minY, sy); maxY = Math.max(maxY, sy);
      }
    }
    const padL = 24, padR = this.padR(), padT = 56, padB = 46;
    const ppm = Math.min((this.w - padL - padR) / (maxX - minX), (this.h - padT - padB) / (maxY - minY)) * 1.0;
    const dist = this.h / (2 * Math.tan(this.fov / 2) * ppm);
    const ox = (minX + maxX) / 2 + (padR - padL) / 2 / ppm;
    const oy = (minY + maxY) / 2 + (padB - padT) / 2 / ppm;
    target.tx = cx + right[0] * ox + up[0] * oy;
    target.ty = cyMid + up[1] * oy;
    target.tz = cz + right[2] * ox + up[2] * oy;
    target.dist = dist;
    this.setCam(target, animate);
  }

  setCam(to: GlCam, animate = true) {
    if (!animate || prefersReducedMotion()) { this.cam = to; this.tween = null; }
    else this.tween = { from: { ...this.cam }, to, t0: performance.now(), dur: 800 };
    this.dirty = true;
  }

  stopFollow() {
    this.followId = null;
  }

  focusOn(x: number, y: number, z: number, ppm = 20) {
    const dist = this.h / (2 * Math.tan(this.fov / 2) * ppm);
    const { right } = this.basisOf(this.cam);
    const k = this.padR() / 2 / ppm;
    this.setCam({ ...this.cam, tx: x + right[0] * k, ty: y, tz: z + right[2] * k, dist }, true);
  }

  focusVehicle(v: Vehicle) {
    const sim = store.sim;
    const f = sim.vehicleFloor(v);
    if (store.floorView !== 'all' && store.floorView !== f) { store.floorView = f; emit('floor'); }
    const p = this.vehiclePos(sim, v, 1);
    if (p) this.focusOn(p.x, p.y, p.z, 11);
    const moving = v.state === 'driving' || v.state === 'parking' || v.state === 'leaving' || v.state === 'queued' || v.state === 'unparking';
    this.followId = moving ? v.i : null;
  }

  focusBay(b: Bay) {
    if (store.floorView !== 'all' && store.floorView !== b.floor) { store.floorView = b.floor; emit('floor'); }
    this.followId = null;
    this.focusOn(b.x, this.floorY(b.floor), b.z, 14);
  }

  get animating(): boolean {
    return !!this.tween || store.layers.autoRotate || this.liveFx || this.followId !== null;
  }

  private stepTween() {
    if (!this.tween) return;
    const k = Math.min(1, (performance.now() - this.tween.t0) / this.tween.dur);
    const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
    const a = this.tween.from, b = this.tween.to;
    let dyaw = b.yaw - a.yaw;
    while (dyaw > Math.PI) dyaw -= 2 * Math.PI;
    while (dyaw < -Math.PI) dyaw += 2 * Math.PI;
    this.cam = { yaw: a.yaw + dyaw * e, pitch: a.pitch + (b.pitch - a.pitch) * e, dist: a.dist * Math.pow(b.dist / a.dist, e), tx: a.tx + (b.tx - a.tx) * e, ty: a.ty + (b.ty - a.ty) * e, tz: a.tz + (b.tz - a.tz) * e };
    if (k >= 1) this.tween = null;
    this.dirty = true;
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
      this.interactT = performance.now();
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
        this.cam.dist = Math.min(600, Math.max(12, this.cam.dist * (this.pinch.d / d)));
        this.panBy(cx - this.pinch.cx, cy - this.pinch.cy);
        this.pinch = { d, cx, cy };
        this.dirty = true;
        return;
      }
      const r = cv.getBoundingClientRect();
      this.hoverXY = [e.clientX - r.left, e.clientY - r.top];
      if (!this.drag || this.drag.id !== e.pointerId) { this.updateHover(); return; }
      const dx = e.clientX - this.drag.x, dy = e.clientY - this.drag.y;
      this.drag.x = e.clientX; this.drag.y = e.clientY;
      this.drag.moved += Math.abs(dx) + Math.abs(dy);
      if (this.drag.moved < 4) return;
      this.setTip(null);
      if (this.drag.mode === 'orbit') {
        this.cam.yaw -= dx * 0.006;
        this.cam.pitch = Math.min(88 * GL_DEG, Math.max(10 * GL_DEG, this.cam.pitch + dy * 0.005));
      } else this.panBy(dx, dy);
      this.dirty = true;
    });
    const end = (e: PointerEvent) => {
      this.pointers.delete(e.pointerId);
      if (this.pointers.size < 2) this.pinch = null;
      if (this.drag && this.drag.id === e.pointerId) {
        if (this.drag.moved < 5) {
          const r = cv.getBoundingClientRect();
          this.click(e.clientX - r.left, e.clientY - r.top);
        }
        this.drag = null;
      }
    };
    cv.addEventListener('pointerup', end);
    cv.addEventListener('pointercancel', end);
    cv.addEventListener('pointerleave', () => { this.hover = null; this.setTip(null); this.dirty = true; });
    cv.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.interactT = performance.now();
      const r = cv.getBoundingClientRect();
      const mx = e.clientX - r.left - this.w / 2, my = e.clientY - r.top - this.h / 2;
      const d0 = this.cam.dist;
      const d1 = Math.min(600, Math.max(12, d0 * Math.exp(e.deltaY * 0.0015)));
      // zoom towards the cursor
      const ppm0 = this.h / (2 * Math.tan(this.fov / 2) * d0), ppm1 = this.h / (2 * Math.tan(this.fov / 2) * d1);
      const k = 1 / ppm0 - 1 / ppm1;
      const { right, up } = this.basisOf(this.cam);
      this.cam.tx += right[0] * mx * k - up[0] * my * k;
      this.cam.ty += -up[1] * my * k;
      this.cam.tz += right[2] * mx * k - up[2] * my * k;
      this.cam.dist = d1;
      this.tween = null;
      this.dirty = true;
    }, { passive: false });
    // Refit when the viewport box changes size (window resize, panels filling in, layout breakpoints).
    // Until the viewer has moved the camera themselves, any change refits; after that only large ones do.
    const onSize = () => {
      // ignore the zero-size box while the overview is hidden behind another page
      const box = this.canvas.getBoundingClientRect();
      if (box.width < 10 || box.height < 10) return;
      const w0 = this.w, h0 = this.h;
      this.resize();
      const dw = Math.abs(this.w - w0), dh = Math.abs(this.h - h0);
      if (dw < 1 && dh < 1) return;
      if (this.followId === null && !this.tween && (this.interactT === 0 ? dw + dh > 2 : dw > 120 || dh > 120)) this.fit(false);
    };
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(onSize).observe(this.canvas);
    else window.addEventListener('resize', onSize);
  }

  private panBy(dx: number, dy: number) {
    this.followId = null;
    const ppm = this.h / (2 * Math.tan(this.fov / 2) * this.cam.dist);
    const { right, up } = this.basisOf(this.cam);
    this.cam.tx -= (right[0] * dx - up[0] * dy) / ppm;
    this.cam.ty -= (-up[1] * dy) / ppm;
    this.cam.tz -= (right[2] * dx - up[2] * dy) / ppm;
  }

  private ray(sx: number, sy: number) {
    const { back, right, up } = this.basisOf(this.cam);
    const t = Math.tan(this.fov / 2);
    const nx = (2 * sx) / this.w - 1, ny = 1 - (2 * sy) / this.h;
    const asp = this.w / this.h;
    let dx = -back[0] + right[0] * nx * t * asp + up[0] * ny * t;
    let dy = -back[1] + up[1] * ny * t;
    let dz = -back[2] + right[2] * nx * t * asp + up[2] * ny * t;
    const l = Math.hypot(dx, dy, dz); dx /= l; dy /= l; dz /= l;
    return { o: this.eye.slice(), d: [dx, dy, dz] };
  }

  pickAt(sx: number, sy: number): GlPick | null {
    const sim = store.sim;
    const { o, d } = this.ray(sx, sy);
    let best: GlPick | null = null;
    let bestT = Infinity;
    // vehicles: ray vs oriented box in the car's frame
    for (const c of this.carPoses) {
      const px = o[0] - c.x, py = o[1] - c.y, pz = o[2] - c.z;
      const ca = Math.cos(c.a), sa = Math.sin(c.a);
      const lo = [px * ca + pz * sa, py, -px * sa + pz * ca];
      const ld = [d[0] * ca + d[2] * sa, d[1], -d[0] * sa + d[2] * ca];
      const mn = [-2.4, 0, -1.1], mx = [2.4, 1.6, 1.1];
      let t0 = -Infinity, t1 = Infinity;
      for (let i = 0; i < 3; i++) {
        if (Math.abs(ld[i]) < 1e-9) { if (lo[i] < mn[i] || lo[i] > mx[i]) { t0 = Infinity; break; } continue; }
        let a = (mn[i] - lo[i]) / ld[i], b = (mx[i] - lo[i]) / ld[i];
        if (a > b) [a, b] = [b, a];
        t0 = Math.max(t0, a); t1 = Math.min(t1, b);
      }
      if (t0 <= t1 && t0 > 0 && t0 < bestT) { bestT = t0; best = { kind: 'vehicle', id: c.v.i }; }
    }
    if (best) return best;
    // bays: intersect each visible floor plane, nearest first
    for (const f of [0, 1, 2]) {
      if (!this.floorVisible(f)) continue;
      const y = this.floorY(f);
      if (Math.abs(d[1]) < 1e-6) continue;
      const t = (y - o[1]) / d[1];
      if (t <= 0 || t >= bestT) continue;
      const x = o[0] + d[0] * t, z = o[2] + d[2] * t;
      if (x < SLAB.x0 || x > SLAB.x1 || z < SLAB.z0 || z > SLAB.z1) continue;
      const bay = sim.L.bays.find((b) => b.floor === f && Math.abs(b.x - x) <= BAY_W / 2 && Math.abs(b.z - z) <= 2.5);
      bestT = t;
      best = bay ? { kind: 'bay', id: bay.idx } : null;
    }
    return best;
  }

  private updateHover() {
    const p = this.pickAt(this.hoverXY[0], this.hoverXY[1]);
    const changed = (p && (!this.hover || p.kind !== this.hover.kind || p.id !== this.hover.id)) || (!p && this.hover);
    this.hover = p;
    this.canvas.style.cursor = p ? 'pointer' : 'grab';
    this.setTip(p);
    if (changed) this.dirty = true;
  }

  private setTip(p: GlPick | null) {
    const tip = this.tip;
    if (!p) { tip.hidden = true; return; }
    const sim = store.sim;
    let html = '';
    if (p.kind === 'vehicle') {
      const v = sim.vehicles[p.id];
      const st = v.state === 'parked' ? `Parked${v.bay >= 0 ? ' in ' + sim.L.bays[v.bay].id : ''}` : v.state === 'leaving' || v.state === 'unparking' ? 'Leaving' : v.resId && v.bay >= 0 ? `To reserved bay ${sim.L.bays[v.bay].id}` : v.target ? `Searching · guided to ${FLOOR_NAMES[v.target.floor]} Zone ${v.target.zone}` : v.state === 'queued' ? 'Waiting at the entrance' : 'Searching';
      html = `<b>${esc(v.code)}</b><span>${esc(st)}</span><span class="tip-sub">${esc(DEST_BY_ID[v.dest].label)} · click for details</span>`;
    } else {
      const b = sim.L.bays[p.id];
      const st = sim.bayStatus(p.id);
      const lab: Record<string, string> = { available: 'Available', occupied: 'Occupied', reserved: 'Reserved', departing: 'Occupied · likely leaving soon', uncertain: 'Status uncertain (camera view blocked)', unavailable: 'Closed for maintenance' };
      html = `<b>${esc(b.id)}</b><span>${esc(lab[st])}</span><span class="tip-sub">${esc(BAY_TYPE_LABEL[b.type])} bay · click for details</span>`;
    }
    if (tip.innerHTML !== html) tip.innerHTML = html;
    tip.hidden = false;
    const x = Math.min(this.w - 210, this.hoverXY[0] + 14), y = Math.max(8, this.hoverXY[1] - 56);
    tip.style.transform = `translate(${x}px, ${y}px)`;
  }

  private click(sx: number, sy: number) {
    const p = this.pickAt(sx, sy);
    if (!p) { store.selected = null; emit('select'); return; }
    store.selected = { kind: p.kind, id: p.id };
    if (p.kind === 'bay' || store.rightTab === 'actions') store.rightTab = 'vehicle';
    if (p.kind === 'vehicle' && store.driver.collapsed && store.driver.autoOpen) { store.driver.collapsed = false; }
    emit('select');
  }

  // ---------- vehicle placement (mirrors scene3d.ts) ----------
  private edgePoint(L: Layout, eid: number, s: number) {
    const e = L.edges[eid];
    const a = L.nodes[e.from], b = L.nodes[e.to];
    const k = Math.max(0, Math.min(1, s / e.len));
    const ya = this.floorY(a.floor), yb = this.floorY(b.floor);
    const horiz = Math.hypot(b.x - a.x, b.z - a.z);
    return { x: a.x + (b.x - a.x) * k, y: ya + (yb - ya) * k, z: a.z + (b.z - a.z) * k, a: Math.atan2(b.z - a.z, b.x - a.x), pitch: Math.atan2(yb - ya, horiz || 1) };
  }

  private placeAt(sim: Sim, v: Vehicle, state: VState, edge: number, s: number, man: number) {
    const L = sim.L;
    if (state === 'parked') {
      const b = L.bays[v.bay];
      return { x: b.x, y: this.floorY(b.floor), z: b.z, a: b.row === 0 ? -Math.PI / 2 : Math.PI / 2, pitch: 0 };
    }
    if (state === 'parking' || state === 'unparking') {
      const b = L.bays[v.bay];
      const az = b.row < 2 ? A1_Z : A2_Z;
      let k = Math.min(1, man / MANEUVER_S);
      if (state === 'unparking') k = 1 - k;
      const into = b.row === 0 ? -Math.PI / 2 : Math.PI / 2;
      const along = b.row < 2 ? 0 : Math.PI;
      const turn = Math.min(1, k * 2);
      return { x: b.x, y: this.floorY(b.floor), z: az + (b.z - az) * k, a: along + (into - along) * turn, pitch: 0 };
    }
    if (state === 'queued') {
      const idx = sim.gateQueue.indexOf(v.i);
      if (idx < 0 || idx > 1) return null;
      return this.edgePoint(L, L.approachEdge, L.edges[L.approachEdge].len - 1 - idx * GAP);
    }
    if (edge < 0) return null;
    return this.edgePoint(L, edge, s);
  }

  vehiclePos(sim: Sim, v: Vehicle, alpha: number) {
    const cur = this.placeAt(sim, v, v.state, v.edge, v.s, v.man);
    if (!cur) return null;
    if (alpha >= 1 || v.pState === 'pending') return cur;
    const prev = this.placeAt(sim, v, v.pState, v.pEdge, v.pS, v.pMan);
    if (!prev) return cur;
    if (Math.hypot(prev.x - cur.x, prev.z - cur.z) > 9 || Math.abs(prev.y - cur.y) > 8) return cur;
    let da = cur.a - prev.a;
    while (da > Math.PI) da -= 2 * Math.PI;
    while (da < -Math.PI) da += 2 * Math.PI;
    return { x: prev.x + (cur.x - prev.x) * alpha, y: prev.y + (cur.y - prev.y) * alpha, z: prev.z + (cur.z - prev.z) * alpha, a: prev.a + da * Math.min(1, alpha * 1.6), pitch: prev.pitch + (cur.pitch - prev.pitch) * alpha };
  }

  private visibleForFloor(sim: Sim, v: Vehicle): boolean {
    if (store.floorView === 'all') return true;
    return sim.vehicleFloor(v) === store.floorView;
  }

  // ---------- frame ----------
  private setCommon(p: WebGLProgram, L3: number[], useShadow: boolean) {
    const gl = this.gl;
    gl.useProgram(p);
    gl.uniformMatrix4fv(this.U(p, 'uVP'), false, this.vp);
    gl.uniform3fv(this.U(p, 'uLight'), L3);
    gl.uniform3fv(this.U(p, 'uEye'), this.eye);
    gl.uniform3fv(this.U(p, 'uFog'), GC.fog);
    gl.uniform1i(this.U(p, 'uShadowOn'), useShadow ? 1 : 0);
    gl.uniform1fv(this.U(p, 'uFloorY'), [this.floorY(0), this.floorY(1), this.floorY(2)]);
    const all = new Float32Array(48);
    for (let i = 0; i < 3; i++) all.set(this.lightVP[i], i * 16);
    gl.uniformMatrix4fv(this.U(p, 'uLightVP'), false, all);
    gl.activeTexture(gl.TEXTURE3);
    gl.bindTexture(gl.TEXTURE_2D, this.shadowTex);
    gl.uniform1i(this.U(p, 'uShadow'), 3);
  }

  private computeLights(L3: number[]) {
    for (let f = 0; f < 3; f++) {
      const y = this.floorY(f);
      const c = [28, y, 16];
      const eye = [c[0] + L3[0] * 120, c[1] + L3[1] * 120, c[2] + L3[2] * 120];
      const view = m4Look(eye, c);
      let mnx = Infinity, mxx = -Infinity, mny = Infinity, mxy = -Infinity, mnz = Infinity, mxz = -Infinity;
      for (const x of [-30, 84]) for (const yy of [y - 1, y + 3]) for (const z of [-2, 36]) {
        const p = m4Apply(view, x, yy, z);
        mnx = Math.min(mnx, p[0]); mxx = Math.max(mxx, p[0]); mny = Math.min(mny, p[1]); mxy = Math.max(mxy, p[1]); mnz = Math.min(mnz, p[2]); mxz = Math.max(mxz, p[2]);
      }
      this.lightVP[f] = m4Mul(m4Ortho(mnx, mxx, mny, mxy, -mxz - 5, -mnz + 5), view);
    }
  }

  private shadowPass(carData: Float32Array, carN: number) {
    const gl = this.gl;
    if (!this.shadowFbo) return;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.shadowFbo);
    gl.viewport(0, 0, SHADOW_RES * 3, SHADOW_RES);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.POLYGON_OFFSET_FILL);
    gl.polygonOffset(2.0, 3.0);
    for (let f = 0; f < 3; f++) {
      if (!this.floorVisible(f)) continue;
      gl.viewport(f * SHADOW_RES, 0, SHADOW_RES, SHADOW_RES);
      gl.useProgram(this.progSh);
      gl.uniformMatrix4fv(this.U(this.progSh, 'uLVP'), false, this.lightVP[f]);
      gl.uniform1f(this.U(this.progSh, 'uFY'), this.floorY(f));
      gl.bindVertexArray(this.staticVao);
      gl.drawArrays(gl.TRIANGLES, 0, this.staticCount);
      if (carN) {
        gl.useProgram(this.progShCar);
        gl.uniformMatrix4fv(this.U(this.progShCar, 'uLVP'), false, this.lightVP[f]);
        gl.uniform1f(this.U(this.progShCar, 'uFY'), this.floorY(f));
        gl.uniform1f(this.U(this.progShCar, 'uScale'), 1);
        gl.bindVertexArray(this.carVao);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.carInst);
        gl.bufferData(gl.ARRAY_BUFFER, carData, gl.DYNAMIC_DRAW);
        gl.drawArraysInstanced(gl.TRIANGLES, 0, this.carCount, carN);
      }
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  render(alpha: number) {
    if (!this.ok) return;
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.lastFrame) / 1000);
    this.lastFrame = now;
    this.lastAlpha = alpha;
    this.stepTween();
    if (store.layers.autoRotate && !this.drag && !this.tween && now - this.interactT > 2500) { this.cam.yaw += dt * 0.06; this.dirty = true; }
    if (this.followId !== null && !this.tween) {
      const fv = store.sim.vehicles[this.followId];
      const sel = store.selected;
      if (!fv || !sel || sel.kind !== 'vehicle' || sel.id !== fv.i || fv.state === 'exited' || fv.state === 'parked') this.followId = null;
      else {
        const p = this.vehiclePos(store.sim, fv, alpha);
        if (p) {
          const ppm = this.h / (2 * Math.tan(this.fov / 2) * this.cam.dist);
          const { right } = this.basisOf(this.cam);
          const k = this.padR() / 2 / ppm;
          this.cam.tx += (p.x + right[0] * k - this.cam.tx) * 0.12;
          this.cam.ty += (p.y - this.cam.ty) * 0.12;
          this.cam.tz += (p.z + right[2] * k - this.cam.tz) * 0.12;
          this.dirty = true;
        }
      }
    }
    const gl = this.gl;
    const sim = store.sim;
    const key = `${store.floorView}|${store.planView}|${store.layers.lights}|${store.layers.cctv}`;
    if (key !== this.staticKey) { this.rampKeys.clear(); this.buildStatic(); this.staticKey = key; }
    const c = this.cam;
    const { back } = this.basisOf(c);
    this.eye = [c.tx + back[0] * c.dist, c.ty + back[1] * c.dist, c.tz + back[2] * c.dist];
    const proj = m4Persp(this.fov, this.w / this.h, Math.max(1, c.dist * 0.05), c.dist * 6 + 400);
    this.vp = m4Mul(proj, m4Look(this.eye, [c.tx, c.ty, c.tz]));
    const light = [-0.42, 0.8, 0.43];
    const ll = Math.hypot(light[0], light[1], light[2]);
    const L3 = [light[0] / ll, light[1] / ll, light[2] / ll];
    this.computeLights(L3);

    // ----- gather dynamic instances -----
    const sel = store.selected;
    const selV = sel && sel.kind === 'vehicle' ? sim.vehicles[sel.id] : null;
    const bays: number[] = [];
    const leds: number[] = [];
    const blink = 0.55 + 0.45 * Math.sin(now / 160);
    let blinkSeen = false;
    const pushQ = (arr: number[], x: number, y: number, z: number, yaw: number, col: number[], a: number, sx: number, sz: number, kind: number, hl = 0) => {
      arr.push(x, y, z, yaw, col[0], col[1], col[2], a, sx, sz, kind, hl);
    };
    for (const b of sim.L.bays) {
      if (!this.floorVisible(b.floor)) continue;
      const fy = this.floorY(b.floor);
      const y = fy + 0.03;
      const st = sim.bayStatus(b.idx);
      const isSel = !!sel && sel.kind === 'bay' && sel.id === b.idx;
      const isHov = !!this.hover && this.hover.kind === 'bay' && this.hover.id === b.idx;
      const col = st === 'available' ? GC.available : st === 'reserved' ? GC.reserved : st === 'departing' ? GC.departing : st === 'occupied' ? GC.occupied : GC.hatch;
      const kind = st === 'uncertain' ? 1 : st === 'unavailable' ? 2 : 0;
      pushQ(bays, b.x, y, b.z, 0, col, 1, BAY_W - 0.2, 4.8, kind, isSel || isHov ? 1 : 0);
      if (b.type !== 'general') {
        const zEdge = b.row === 0 ? b.z + 2.15 : b.z - 2.15;
        pushQ(bays, b.x, y + 0.006, zEdge, 0, GL_TYPE_COL[b.type], 1, BAY_W - 0.25, 0.5, 0);
      }
      if (store.layers.lights && st !== 'unavailable') {
        let lc: number[];
        if (st === 'available') lc = b.type === 'oku' ? GC.ledOku : b.type === 'ladies' ? GC.ledLadies : b.type === 'member' ? GC.ledHeld : GC.ledFree;
        else if (st === 'reserved') lc = GC.ledHeld;
        else if (st === 'departing') { lc = GC.ledLeaving.map((v) => v * blink); blinkSeen = true; }
        else if (st === 'uncertain') lc = [0.25, 0.27, 0.3];
        else lc = GC.ledTaken;
        const zl = b.row === 0 ? b.z + 2.3 : b.z - 2.3;
        leds.push(b.x, fy + 2.55, zl, 0, lc[0], lc[1], lc[2], 0);
      }
    }
    this.liveFx = (store.layers.lights && blinkSeen) || (!!selV && store.layers.route && selV.parkT < 0 && selV.state !== 'exited');
    const zoneQ: number[] = [];
    if (selV && selV.target && selV.parkT < 0 && (selV.state === 'driving' || selV.state === 'parking') && this.floorVisible(selV.target.floor)) {
      const z = selV.target.zone, y = this.floorY(selV.target.floor) + 0.06;
      const x0 = ZONE_X0[z] - 0.3, x1 = ZONE_X0[z] + ZONE_COUNTS[z] * BAY_W + 0.3;
      zoneQ.push((x0 + x1) / 2, y, (ROW_Z[0] + ROW_Z[1]) / 2, 0, ...GC.ringSearch, 0.9, x1 - x0, ROW_Z[1] - ROW_Z[0] + 5.4, 5, 0);
      zoneQ.push((x0 + x1) / 2, y, ROW_Z[2], 0, ...GC.ringSearch, 0.9, x1 - x0, 5.4, 5, 0);
    }
    this.carPoses = [];
    const carData: number[] = [];
    const fx: number[] = [];
    for (const v of sim.vehicles) {
      if (v.state === 'pending' || v.state === 'exited' || v.state === 'cancelled' || v.state === 'diverted') continue;
      if (!this.visibleForFloor(sim, v)) continue;
      const p = this.vehiclePos(sim, v, alpha);
      if (!p) continue;
      if (store.floorView !== 'all') {
        const e = v.edge >= 0 && (v.state === 'driving' || v.state === 'leaving') ? sim.L.edges[v.edge] : null;
        if (e && e.kind === 'ramp') {
          const k = v.s / e.len;
          const fromHere = sim.L.nodes[e.from].floor === store.floorView;
          if ((fromHere && k > 0.35) || (!fromHere && k < 0.65)) continue;
        }
      }
      this.carPoses.push({ v, x: p.x, y: p.y, z: p.z, a: p.a });
      const col = rgbOf(CAR_PALETTE[Math.floor(hash01(v.key) * CAR_PALETTE.length)]);
      carData.push(p.x, p.y + 0.02, p.z, p.a, col[0], col[1], col[2], p.pitch);
      fx.push(p.x, p.y + 0.05, p.z, p.a, 0, 0, 0, 0.45, 4.9, 2.3, 3, 0);
      const moving = v.state === 'driving' || v.state === 'parking' || v.state === 'queued';
      const isSel = selV === v;
      const isHov = !!this.hover && this.hover.kind === 'vehicle' && this.hover.id === v.i;
      let ring: number[] | null = null;
      if (moving) ring = v.resId ? GC.ringRes : v.gateT >= 0 && sim.t - v.gateT > 300 ? GC.ringSlow : GC.ringSearch;
      if (isSel || isHov) ring = GC.ringSel;
      if (ring) fx.push(p.x, p.y + 0.07, p.z, 0, ring[0], ring[1], ring[2], isSel ? 1 : 0.95, 7.2, 7.2, 4, 0);
      if (moving && store.layers.lights) {
        // headlight pools on the floor ahead of moving cars
        fx.push(p.x + Math.cos(p.a) * 4.2, p.y + 0.06, p.z + Math.sin(p.a) * 4.2, p.a, 1, 0.95, 0.8, 0.22, 5.5, 3.2, 6, 0);
      }
    }
    if (store.layers.cctv) {
      for (const f of [0, 1, 2]) {
        if (!this.floorVisible(f)) continue;
        for (const cs of this.cctvSpots(f)) fx.push(cs.x, this.floorY(f) + 0.09, cs.z, cs.a, 0.38, 0.7, 1, 1, 30, 30, 7, 0);
      }
    }
    const carArr = new Float32Array(carData);
    const carN = carData.length / 8;

    // ----- shadow maps (one tile per floor) -----
    const useShadow = !!this.shadowFbo;
    if (useShadow) this.shadowPass(carArr, carN);

    // ----- main pass -----
    this.ensurePost();
    const post = this.post;
    if (post) gl.bindFramebuffer(gl.FRAMEBUFFER, post.msaaFbo);
    else gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    if (post) gl.clearColor(0, 0, 0, 0);
    else gl.clearColor(GC.fog[0], GC.fog[1], GC.fog[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    gl.disable(gl.BLEND);

    this.setCommon(this.progLit, L3, useShadow);
    gl.uniform1f(this.U(this.progLit, 'uGloss'), 0.15);
    gl.uniform1f(this.U(this.progLit, 'uEmis'), this.hdr ? 1.6 : 0.2);
    gl.bindVertexArray(this.staticVao);
    gl.drawArrays(gl.TRIANGLES, 0, this.staticCount);

    this.setCommon(this.progInst, L3, useShadow);
    gl.bindVertexArray(this.quadVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(bays), gl.DYNAMIC_DRAW);
    gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, bays.length / 12);

    if (carN) {
      this.setCommon(this.progCar, L3, useShadow);
      gl.uniform1f(this.U(this.progCar, 'uGloss'), 0.6);
      gl.uniform1f(this.U(this.progCar, 'uEmis'), this.hdr ? 1.2 : 0.2);
      gl.uniform1f(this.U(this.progCar, 'uScale'), 1);
      gl.bindVertexArray(this.carVao);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.carInst);
      gl.bufferData(gl.ARRAY_BUFFER, carArr, gl.DYNAMIC_DRAW);
      gl.drawArraysInstanced(gl.TRIANGLES, 0, this.carCount, carN);
    }
    if (leds.length) {
      this.setCommon(this.progCar, L3, false);
      gl.uniform1f(this.U(this.progCar, 'uGloss'), 0.3);
      gl.uniform1f(this.U(this.progCar, 'uEmis'), this.hdr ? 4.0 : 0.3);
      gl.uniform1f(this.U(this.progCar, 'uScale'), 1);
      gl.bindVertexArray(this.ledVao);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.ledInst);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(leds), gl.DYNAMIC_DRAW);
      gl.drawArraysInstanced(gl.TRIANGLES, 0, this.ledCount, leds.length / 8);
    }

    gl.enable(gl.BLEND);
    gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.depthMask(false);
    this.setCommon(this.progInst, L3, false);
    gl.bindVertexArray(this.quadVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf);
    const all = fx.concat(zoneQ);
    if (all.length) {
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(all), gl.DYNAMIC_DRAW);
      gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, all.length / 12);
    }
    if (selV && store.layers.route) this.drawPaths(sim, selV, alpha, now);
    gl.depthMask(true);
    gl.disable(gl.BLEND);
    gl.bindVertexArray(null);

    if (post) this.postProcess(post);
    this.drawLabels(sim, selV, alpha);
    this.dirty = false;
  }

  private postProcess(p: PostTargets) {
    const gl = this.gl;
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, p.msaaFbo);
    gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, p.sceneFbo);
    gl.blitFramebuffer(0, 0, p.w, p.h, 0, 0, p.w, p.h, gl.COLOR_BUFFER_BIT, gl.NEAREST);
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
    gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
    gl.disable(gl.DEPTH_TEST);
    gl.bindVertexArray(this.fullVao);
    const hw = Math.max(1, p.w >> 1), hh = Math.max(1, p.h >> 1), qw = Math.max(1, p.w >> 2), qh = Math.max(1, p.h >> 2);
    const pass = (prog: WebGLProgram, src: WebGLTexture, dst: WebGLFramebuffer | null, w: number, h: number, set: () => void) => {
      gl.bindFramebuffer(gl.FRAMEBUFFER, dst);
      gl.viewport(0, 0, w, h);
      gl.useProgram(prog);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, src);
      gl.uniform1i(this.U(prog, 'uSrc'), 0);
      set();
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    const thr = this.hdr ? 1.0 : 0.82;
    pass(this.progBright, p.sceneTex, p.fbA, hw, hh, () => gl.uniform1f(this.U(this.progBright, 'uThr'), thr));
    pass(this.progBlur, p.bloomA, p.fbB, hw, hh, () => gl.uniform2f(this.U(this.progBlur, 'uDir'), 1 / hw, 0));
    pass(this.progBlur, p.bloomB, p.fbA, hw, hh, () => gl.uniform2f(this.U(this.progBlur, 'uDir'), 0, 1 / hh));
    pass(this.progBlur, p.bloomA, p.fbC, qw, qh, () => gl.uniform2f(this.U(this.progBlur, 'uDir'), 1.5 / qw, 0));
    pass(this.progBlur, p.bloomC, p.fbD, qw, qh, () => gl.uniform2f(this.U(this.progBlur, 'uDir'), 0, 1.5 / qh));
    pass(this.progBlur, p.bloomD, p.fbC, qw, qh, () => gl.uniform2f(this.U(this.progBlur, 'uDir'), 3 / qw, 0));
    pass(this.progBlur, p.bloomC, p.fbD, qw, qh, () => gl.uniform2f(this.U(this.progBlur, 'uDir'), 0, 3 / qh));
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, p.w, p.h);
    gl.useProgram(this.progComp);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, p.sceneTex); gl.uniform1i(this.U(this.progComp, 'uScene'), 0);
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, p.bloomA); gl.uniform1i(this.U(this.progComp, 'uBloom'), 1);
    gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, p.bloomD); gl.uniform1i(this.U(this.progComp, 'uBloom2'), 2);
    gl.uniform1f(this.U(this.progComp, 'uBloomK'), 1.0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.bindVertexArray(null);
    gl.enable(gl.DEPTH_TEST);
  }

  private ribbon(pts: number[][], width: number, col: number[], a: number, dash: number, time = 0) {
    if (pts.length < 2) return;
    const gl = this.gl;
    const d: number[] = [];
    let acc = 0;
    for (let i = 0; i < pts.length - 1; i++) {
      const p = pts[i], q = pts[i + 1];
      const dx = q[0] - p[0], dz = q[2] - p[2];
      const l = Math.hypot(dx, q[1] - p[1], dz);
      if (l < 1e-4) continue;
      const hl = Math.hypot(dx, dz) || 1;
      const nx = (-dz / hl) * width / 2, nz = (dx / hl) * width / 2;
      const a0 = acc, a1 = acc + l;
      d.push(p[0] - nx, p[1], p[2] - nz, a0, p[0] + nx, p[1], p[2] + nz, a0, q[0] + nx, q[1], q[2] + nz, a1);
      d.push(p[0] - nx, p[1], p[2] - nz, a0, q[0] + nx, q[1], q[2] + nz, a1, q[0] - nx, q[1], q[2] - nz, a1);
      acc = a1;
    }
    gl.useProgram(this.progRib);
    gl.uniformMatrix4fv(this.U(this.progRib, 'uVP'), false, this.vp);
    gl.uniform4f(this.U(this.progRib, 'uCol'), col[0], col[1], col[2], a);
    gl.uniform1f(this.U(this.progRib, 'uDash'), dash);
    gl.uniform1f(this.U(this.progRib, 'uTime'), time);
    gl.bindVertexArray(this.ribVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.ribBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(d), gl.DYNAMIC_DRAW);
    gl.drawArrays(gl.TRIANGLES, 0, d.length / 4);
  }

  private drawPaths(sim: Sim, v: Vehicle, alpha: number, now: number) {
    const L = sim.L;
    const pos = this.vehiclePos(sim, v, alpha);
    if (!pos) return;
    if ((v.state === 'driving' || v.state === 'leaving') && v.edge >= 0) {
      const pts: number[][] = [[pos.x, pos.y + 0.12, pos.z]];
      const edges = [v.edge, ...v.route];
      for (let i = 0; i < edges.length; i++) {
        const e = L.edges[edges[i]];
        const last = i === edges.length - 1;
        if (last && v.bay >= 0 && e.id === L.bays[v.bay].edge) {
          const b = L.bays[v.bay];
          const ep = this.edgePoint(L, e.id, b.accessS);
          pts.push([ep.x, ep.y + 0.12, ep.z], [b.x, ep.y + 0.12, b.z]);
          break;
        }
        const n = L.nodes[e.to];
        if (!this.floorVisible(n.floor)) { const ep = this.edgePoint(L, e.id, e.len * 0.35); pts.push([ep.x, ep.y + 0.12, ep.z]); break; }
        pts.push([n.x, this.floorY(n.floor) + 0.12, n.z]);
      }
      this.ribbon(pts, 2.4, GC.route, 0.18, 0);
      this.ribbon(pts, 0.75, GC.route, 0.95, -1, now / 1000);
    }
    const lift = DEST_BY_ID[v.dest].lift;
    let from: number[] | null = null;
    let f = -1;
    if (v.bay >= 0) { const b = L.bays[v.bay]; from = [b.x, b.z]; f = b.floor; }
    else if (v.target) { from = [ZONE_X0[v.target.zone] + (ZONE_COUNTS[v.target.zone] * BAY_W) / 2, ROW_Z[1]]; f = v.target.floor; }
    if (from && f >= 0 && this.floorVisible(f)) {
      const y = this.floorY(f) + 0.14;
      this.ribbon([[from[0], y, from[1]], [LIFT_X[lift], y, from[1]], [LIFT_X[lift], y, LIFT_Z]], 0.45, [1, 1, 1], 0.95, 1.2);
    }
  }

  // ---------- labels ----------
  private project(x: number, y: number, z: number): [number, number] | null {
    const m = this.vp;
    const cx = m[0] * x + m[4] * y + m[8] * z + m[12];
    const cy = m[1] * x + m[5] * y + m[9] * z + m[13];
    const cw = m[3] * x + m[7] * y + m[11] * z + m[15];
    if (cw <= 0.01) return null;
    return [(cx / cw * 0.5 + 0.5) * this.w, (1 - (cy / cw * 0.5 + 0.5)) * this.h];
  }

  private ppmAt(x: number, y: number, z: number): number {
    const d = Math.hypot(x - this.eye[0], y - this.eye[1], z - this.eye[2]);
    return this.h / (2 * Math.tan(this.fov / 2) * d);
  }

  private drawLabels(sim: Sim, selV: Vehicle | null, alpha: number) {
    const want = new Map<string, { x: number; y: number; html: string; cls: string }>();
    const add = (id: string, wx: number, wy: number, wz: number, html: string, cls: string, minPpm = 0) => {
      if (minPpm && this.ppmAt(wx, wy, wz) < minPpm) return;
      const p = this.project(wx, wy, wz);
      if (!p || p[0] < -40 || p[0] > this.w + 40 || p[1] < -20 || p[1] > this.h + 20) return;
      want.set(id, { x: p[0], y: p[1], html, cls });
    };
    const counts = sim.counts();
    for (const f of [0, 1, 2]) {
      if (!this.floorVisible(f)) continue;
      const y = this.floorY(f);
      if (store.floorView === 'all') add(`fl${f}`, f === 0 ? -2 : -8, y, f === 0 ? 37 : 34, `<b>${FLOOR_NAMES[f]}</b> ${counts.perFloor[f].generalFree} free`, 'lb-floor');
      for (const z of ZONES) {
        add(`lift${f}${z}`, LIFT_X[z], y + 3.4, LIFT_Z, `Lift ${z}`, 'lb-lift', 4);
        add(`zone${f}${z}`, ZONE_X0[z] + (ZONE_COUNTS[z] * BAY_W) / 2, y, 34.5, `Zone ${z}`, 'lb-zone', 3);
      }
    }
    if (this.floorVisible(0)) {
      const y = this.floorY(0);
      add('ent', -19, y + 0.3, A1_Z - 5, 'Entrance', 'lb-road', 2.5);
      add('exit', -19, y + 0.3, A2_Z + 5, 'Exit', 'lb-road', 2.5);
      const q = sim.gateQueue.length;
      if (q > 0) add('queue', -28, y + 1.5, A1_Z, `${q} waiting`, q > 3 ? 'lb-queue crit' : 'lb-queue', 0);
    }
    for (const e of sim.L.edges) {
      if (e.kind !== 'ramp') continue;
      const a = sim.L.nodes[e.from], b = sim.L.nodes[e.to];
      if (!this.floorVisible(a.floor)) continue;
      const down = b.floor > a.floor;
      add(`ramp${e.id}`, a.x, this.floorY(a.floor) + 1.2, a.z + (down ? -4.5 : 4.5), `${down ? '↓' : '↑'} ${FLOOR_NAMES[b.floor]}`, 'lb-ramp', 3.5);
    }
    if (selV) {
      const p = this.vehiclePos(sim, selV, alpha);
      if (p) add('selv', p.x, p.y + 2.6, p.z, esc(selV.code), 'lb-sel');
      const lift = DEST_BY_ID[selV.dest].lift;
      let f = -1, walk = 0;
      if (selV.bay >= 0) { f = sim.L.bays[selV.bay].floor; walk = sim.L.bays[selV.bay].walk[lift]; }
      else if (selV.target && selV.alloc && selV.alloc.chosen) { f = selV.target.floor; walk = Math.round(selV.alloc.chosen.walk); }
      if (f >= 0 && this.floorVisible(f)) add('walk', LIFT_X[lift], this.floorY(f) + 4.6, LIFT_Z, `Walk ≈ ${walk} m`, 'lb-walk');
    }
    // reconcile DOM
    for (const [id, el] of this.labelPool) if (!want.has(id)) { el.hidden = true; }
    for (const [id, l] of want) {
      let el = this.labelPool.get(id);
      if (!el) {
        el = document.createElement('div');
        this.labels.appendChild(el);
        this.labelPool.set(id, el);
      }
      el.hidden = false;
      if (el.dataset.h !== l.html) { el.innerHTML = l.html; el.dataset.h = l.html; }
      if (el.className !== `lb ${l.cls}`) el.className = `lb ${l.cls}`;
      el.style.transform = `translate(${l.x.toFixed(1)}px, ${l.y.toFixed(1)}px)`;
    }
  }
}


function canvasLost(cv: HTMLCanvasElement, onLost: () => void) {
  cv.addEventListener('webglcontextlost', (e) => { e.preventDefault(); onLost(); });
}
