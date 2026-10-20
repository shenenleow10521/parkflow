// Motion layer for the driver app.
// Uses the Motion library (motion.dev, loaded as a pinned UMD script) when it is available, and falls back to
// the browser's Web Animations API with a sampled spring curve when it is not (offline, blocked CDN, tests).
// Every call respects prefers-reduced-motion by jumping straight to the final frame.

type Keyframes = Record<string, (string | number)[]>;

export interface MotionOpts {
  /** seconds */
  duration?: number;
  /** seconds */
  delay?: number;
  ease?: [number, number, number, number];
  spring?: { stiffness?: number; damping?: number; mass?: number };
}

interface MotionLib {
  animate: (el: Element, kf: Keyframes, o: Record<string, unknown>) => unknown;
}

export function reducedMotion(): boolean {
  try {
    return matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

function motionLib(): MotionLib | null {
  const m = (window as unknown as { Motion?: MotionLib }).Motion;
  return m && typeof m.animate === 'function' ? m : null;
}

export function motionEngine(): 'motion' | 'waapi' {
  return motionLib() ? 'motion' : 'waapi';
}

// Each element remembers its latest animation, so a superseded one never writes its end frame late.
const generation = new WeakMap<Element, number>();
const running = new WeakMap<Element, Animation>();

function applyFinal(el: Element, kf: Keyframes) {
  const st = (el as HTMLElement).style as unknown as Record<string, string>;
  for (const k of Object.keys(kf)) {
    const v = kf[k];
    st[k] = String(v[v.length - 1]);
  }
}

// Damped spring position (0 → 1) for the WAAPI fallback, sampled into a CSS linear() easing.
function springCurve(stiffness: number, damping: number, mass: number): { dur: number; ease: string } {
  const w0 = Math.sqrt(stiffness / mass);
  const zeta = damping / (2 * Math.sqrt(stiffness * mass));
  const x = (t: number) => {
    if (zeta < 1) {
      const wd = w0 * Math.sqrt(1 - zeta * zeta);
      return 1 - Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + ((zeta * w0) / wd) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
  };
  let dur = 0.2;
  while (dur < 2 && Math.abs(1 - x(dur)) > 0.002) dur += 0.05;
  const n = 32;
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) pts.push(x((dur * i) / n).toFixed(4));
  pts[n] = '1';
  return { dur, ease: `linear(${pts.join(', ')})` };
}

let linearOK: boolean | null = null;
function supportsLinear(): boolean {
  if (linearOK === null) {
    try {
      linearOK = CSS.supports('animation-timing-function', 'linear(0, 0.5, 1)');
    } catch {
      linearOK = false;
    }
  }
  return linearOK;
}

function waapi(el: Element, kf: Keyframes, o: MotionOpts, gen: number): Promise<void> {
  const prev = running.get(el);
  if (prev) {
    try {
      prev.commitStyles();
    } catch {
      /* element may be hidden */
    }
    prev.cancel();
  }
  const keys = Object.keys(kf);
  const n = Math.max(...keys.map((k) => kf[k].length));
  const frames: Keyframe[] = [];
  for (let i = 0; i < n; i++) {
    const f: Record<string, string> = {};
    for (const k of keys) f[k] = String(kf[k][Math.min(i, kf[k].length - 1)]);
    frames.push(f as Keyframe);
  }
  let dur = o.duration ?? 0.3;
  let easing = `cubic-bezier(${(o.ease ?? [0.2, 0.8, 0.2, 1]).join(',')})`;
  if (o.spring) {
    const sc = springCurve(o.spring.stiffness ?? 380, o.spring.damping ?? 32, o.spring.mass ?? 1);
    dur = sc.dur;
    easing = supportsLinear() ? sc.ease : 'cubic-bezier(.2,.9,.25,1.05)';
  }
  try {
    const a = (el as HTMLElement).animate(frames, { duration: dur * 1000, delay: (o.delay ?? 0) * 1000, easing, fill: 'both' });
    running.set(el, a);
    return a.finished.then(
      () => {
        if (generation.get(el) === gen) applyFinal(el, kf);
        a.cancel();
        if (running.get(el) === a) running.delete(el);
      },
      () => undefined
    );
  } catch {
    applyFinal(el, kf);
    return Promise.resolve();
  }
}

/** Animate CSS properties (transform, opacity, strokeDashoffset …) with tween or spring options. */
export function animate(el: Element | null | undefined, kf: Keyframes, o: MotionOpts = {}): Promise<void> {
  if (!el) return Promise.resolve();
  const gen = (generation.get(el) ?? 0) + 1;
  generation.set(el, gen);
  if (reducedMotion()) {
    applyFinal(el, kf);
    return Promise.resolve();
  }
  const M = motionLib();
  if (M) {
    try {
      const opts: Record<string, unknown> = o.spring
        ? { type: 'spring', stiffness: o.spring.stiffness ?? 380, damping: o.spring.damping ?? 32, mass: o.spring.mass ?? 1, delay: o.delay ?? 0 }
        : { duration: o.duration ?? 0.3, delay: o.delay ?? 0, ease: o.ease ?? [0.2, 0.8, 0.2, 1] };
      const controls = M.animate(el, kf, opts);
      const cap = (o.spring ? 1.4 : o.duration ?? 0.3) + (o.delay ?? 0) + 0.2;
      // Resolve when Motion reports completion, or after a safe cap; then make sure the final frame sticks.
      const settle = () => {
        if (generation.get(el) === gen) applyFinal(el, kf);
      };
      return Promise.race([Promise.resolve(controls as PromiseLike<unknown>), new Promise((r) => setTimeout(r, cap * 1000))]).then(settle, settle);
    } catch {
      /* fall back below */
    }
  }
  return waapi(el, kf, o, gen);
}

/** Tween a number (for count-ups); calls back every frame. */
export function tweenNumber(from: number, to: number, seconds: number, onUpdate: (v: number) => void): void {
  if (reducedMotion() || from === to) {
    onUpdate(to);
    return;
  }
  const t0 = performance.now();
  const step = (now: number) => {
    const k = Math.min(1, (now - t0) / (seconds * 1000));
    const e = 1 - Math.pow(1 - k, 3);
    onUpdate(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

export const SPRING_SHEET = { stiffness: 420, damping: 38 };
export const SPRING_PUSH = { stiffness: 360, damping: 36 };
export const SPRING_POP = { stiffness: 520, damping: 30 };
