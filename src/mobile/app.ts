// ParkFlow driver app: the shopper-facing side of the command centre.
// It runs the same seeded simulation as the operator view. "I'm on my way" adds the driver's own car to the
// arrivals; the allocation engine guides it, and the app turns that guidance into sign-style instructions.

import { buildLayout, DESTINATIONS, DEST_BY_ID, DestId, FLOOR_NAMES, ZONES, ZoneId, BayType, Bay, typeText, ZONE_X0, ZONE_COUNTS, BAY_W } from '../core/layout';
import { SCENARIO_BY_ID, clockLabel } from '../core/scenarios';
import { Sim, Vehicle, Reservation } from '../core/sim';
import { DEFAULT_WEIGHTS } from '../core/allocation';
import { DEFAULT_ASSUMPTIONS } from '../core/forecast';
import { $, $$, esc, setHTML, icon, dotMatrix, loadJSON, saveJSON, fmtDist } from '../ui/dom';
import { animate, tweenNumber, SPRING_SHEET, SPRING_PUSH, reducedMotion, motionEngine } from './motion';
import { FloorMap, vehiclePose, walkPath } from './map';

type Tab = 'park' | 'reserve' | 'car';
type SheetKind = '' | 'plan' | 'profile' | 'pay' | 'paid' | 'topup' | 'dest' | 'assist';
type ResType = 'ev' | 'family' | 'member';

interface Profile {
  pace: number;
}

/** A car in the driver's garage. EV and family pass belong to the car; membership belongs to the account. */
interface CarProfile {
  plate: string;
  name: string;
  ev: boolean;
  family: boolean;
}
type PayMethod = 'wallet' | 'debit' | 'credit';
interface Card {
  id: 'debit' | 'credit';
  label: string;
  last4: string;
}
/** KL East Mall account: rewards membership, points and the mall wallet. Simulated, stored on this device only. */
interface Account {
  member: boolean;
  tier: string;
  memberNo: string;
  points: number;
  wallet: number;
  cards: Card[];
}
interface Receipt {
  at: number;
  fee: number;
  pointsUsed: number;
  pointsRM: number;
  charged: number;
  method: PayMethod;
  earned: number;
}
/** One parking stay: a car of the driver's in the simulation, from "on my way" until it leaves. */
interface Stay {
  plate: string;
  vid: number;
  demo: boolean;
  receipt: Receipt | null;
}

const POINTS_PER_RM = 100; // redeem: 100 points = RM 1
const EARN_PER_RM = 10; // earn: 10 points per RM 1 paid in money
const DEFAULT_GARAGE: CarProfile[] = [
  { plate: 'VKL 2026', name: 'My car', ev: false, family: false },
  { plate: 'WXY 8812', name: 'Family car', ev: false, family: true }
];
const DEFAULT_ACCOUNT: Account = {
  member: true,
  tier: 'Gold',
  memberNo: '8801 2026 4417',
  points: 2340,
  wallet: 12.5,
  cards: [
    { id: 'debit', label: 'Debit card', last4: '4821' },
    { id: 'credit', label: 'Credit card', last4: '1093' }
  ]
};

const ZONE_COLOUR: Record<ZoneId, string> = { A: 'blue', B: 'yellow', C: 'orange' };
const DEST_ICON: Record<DestId, string> = { cinema: 'film', grocer: 'cart', atrium: 'store', family: 'skate' };
const RES_LABEL: Record<ResType, string> = { ev: 'EV charging', family: 'Family', member: 'Member' };
const RES_ELIG: Record<ResType, string> = {
  ev: 'My car is an electric vehicle and I will charge while parked.',
  family: 'I have the KL East Mall family pass (child under 12 or a pram).',
  member: 'I am a KL East Mall member with designated parking.'
};

// Extra pictograms for the driver app (Lucide-style strokes, 24×24).
const PX: Record<string, string> = {
  film: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18M3 7.5h4M3 12h18M3 16.5h4M17 3v18M17 7.5h4M17 16.5h4"/>',
  cart: '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
  store: '<path d="M3 21h18M5 21V8l7-5 7 5v13"/><path d="M9 21v-6h6v6"/>',
  skate: '<path d="M4 17h14a3 3 0 0 0 3-3"/><path d="M6 17v-5l4-1 1-6h4v8l4 2"/><path d="M5 21h15"/>',
  pin: '<path d="M20 10c0 5-5.5 10.2-7.4 11.8a1 1 0 0 1-1.2 0C9.5 20.2 4 15 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
  user: '<circle cx="12" cy="8" r="4.5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
  park: '<rect width="18" height="18" x="3" y="3" rx="3"/><path d="M9 17V7h4a3 3 0 0 1 0 6H9"/>',
  nav: '<polygon points="3 11 22 2 13 21 11 13 3 11"/>',
  wallet: '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
  lift: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="m9 8 3-3 3 3M9 16l3 3 3-3"/>',
  walk: '<circle cx="13" cy="4" r="2"/><path d="m7 22 3-7 3 3v4M10 15l1-5 4 3 3 1M8 9l3-1"/>',
  ticket: '<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4Z"/><path d="M13 5v2M13 17v2M13 11v2"/>',
  back: '<path d="m15 18-6-6 6-6"/>',
  card: '<rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20M6 15h4"/>',
  chev: '<path d="m9 18 6-6-6-6"/>'
};
function ic(name: string, size = 18): string {
  if (!PX[name]) return icon(name, size);
  return `<svg class="ic" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PX[name]}</svg>`;
}

// Big white sign pictograms for the instruction panel (48×48).
const SIGN_PICTO: Record<string, string> = {
  gate: '<path d="M8 40V12M8 18h30" stroke-width="5"/><path d="M30 30h-10m0 0 4-4m-4 4 4 4" stroke-width="4"/>',
  down: '<path d="M24 6v32m0 0-12-12m12 12 12-12" stroke-width="6"/>',
  up: '<path d="M24 42V10m0 0L12 22m12-12 12 12" stroke-width="6"/>',
  zone: '<path d="M6 24h32m0 0-11-11m11 11-11 11" stroke-width="6"/>',
  park: '<path d="M16 40V8h10a10 10 0 0 1 0 20H16" stroke-width="6"/>',
  done: '<path d="m9 25 10 10 20-22" stroke-width="6"/>',
  alert: '<path d="M24 8v20" stroke-width="6"/><circle cx="24" cy="38" r="3.6" fill="currentColor" stroke="none"/>'
};
function picto(k: string): string {
  return `<svg viewBox="0 0 48 48" width="52" height="52" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${SIGN_PICTO[k] || SIGN_PICTO.zone}</svg>`;
}

const app = {
  L: buildLayout(),
  sim: null as unknown as Sim,
  tab: 'park' as Tab,
  screen: '' as '' | 'guide' | 'parked',
  myId: -1,
  resId: '',
  resMsg: '',
  resErr: false,
  assistMsg: '',
  resDraft: { type: 'ev' as ResType, inMin: 20, dur: 120, elig: false, touched: false, plate: '' },
  plan: { dest: 'cinema' as DestId, eta: 10, plate: '' },
  profile: loadJSON<Profile>('parkflow.driver.v2', { pace: 4 }),
  garage: loadJSON<CarProfile[]>('parkflow.garage', DEFAULT_GARAGE.map((c) => ({ ...c }))),
  account: loadJSON<Account>('parkflow.account', { ...DEFAULT_ACCOUNT, cards: DEFAULT_ACCOUNT.cards.map((c) => ({ ...c })) }),
  stays: [] as Stay[],
  carSel: '',
  addingCar: false,
  pay: { plate: '', method: 'wallet' as PayMethod, usePoints: true, topAmt: 50, topFrom: 'debit' as 'debit' | 'credit', back: false, done: null as Receipt | null },
  sheet: '' as SheetKind,
  parkedShown: false,
  lastNotice: '',
  lastGuideKey: '',
  boardVals: [-1, -1, -1],
  acc: 0,
  lastFrame: 0,
  lastUI: 0,
  dirty: true,
  booted: false,
  toastTimer: 0
};

let guideMap: FloorMap;
let carMap: FloorMap;

function persistProfile() {
  saveJSON('parkflow.driver.v2', app.profile);
  saveJSON('parkflow.garage', app.garage);
  saveJSON('parkflow.account', app.account);
}

function newSim(): Sim {
  const s = new Sim(app.L, SCENARIO_BY_ID.surge, { policy: 'guided', live: true, weights: { ...DEFAULT_WEIGHTS }, assumptions: { ...DEFAULT_ASSUMPTIONS } });
  s.runTo(480);
  return s;
}

/** Demo: the driver's first car has been parked since about 12:40 near Lift B, so My car shows a real stay. */
function seedParkedCar() {
  const sim = app.sim;
  const L = sim.L;
  const parked = sim.vehicles.filter((v) => v.state === 'parked' && v.bay >= 0 && L.bays[v.bay].type === 'general' && L.bays[v.bay].flag === 'none');
  const pick = parked.find((v) => L.bays[v.bay].floor === 1 && L.bays[v.bay].zone === 'B') || parked.find((v) => L.bays[v.bay].zone === 'B') || parked[0];
  app.stays = [];
  if (!pick || !app.garage.length) return;
  if (sim.adoptParked(pick.i, 88 * 60, 'atrium')) {
    app.stays.push({ plate: app.garage[0].plate, vid: pick.i, demo: true, receipt: null });
    app.carSel = app.garage[0].plate;
  }
}

function me(): Vehicle | null {
  return app.myId >= 0 ? app.sim.vehicles[app.myId] || null : null;
}

function myRes(): Reservation | null {
  return app.resId ? app.sim.reservations.find((r) => r.id === app.resId) || null : null;
}

function carOf(plate: string): CarProfile {
  return app.garage.find((c) => c.plate === plate) || app.garage[0];
}

function eligFor(car: CarProfile): BayType[] {
  const e: BayType[] = ['general'];
  if (car.ev) e.push('ev');
  if (car.family) e.push('family');
  if (app.account.member) e.push('member');
  return e;
}

function vOf(st: Stay | undefined | null): Vehicle | null {
  return st ? app.sim.vehicles[st.vid] || null : null;
}

/** Latest stay for a plate. */
function stayOf(plate: string): Stay | undefined {
  for (let i = app.stays.length - 1; i >= 0; i--) if (app.stays[i].plate === plate) return app.stays[i];
  return undefined;
}

function tripPlate(): string {
  const st = app.stays.find((x) => x.vid === app.myId);
  return st ? st.plate : '';
}

/** A car is busy while it is on the way, in the car park, or held by a booking. */
function carBusy(plate: string): boolean {
  const ph = phaseOf(vOf(stayOf(plate)));
  return ph === 'gate' || ph === 'driving' || ph === 'parked' || ph === 'paid' || ph === 'planned';
}

function freeCars(): CarProfile[] {
  return app.garage.filter((c) => !carBusy(c.plate));
}

function rm(x: number): string {
  return `RM ${x.toFixed(2)}`;
}

function methodLabel(m: PayMethod): string {
  if (m === 'wallet') return 'KL East Mall wallet';
  const c = app.account.cards.find((x) => x.id === m);
  return c ? `${c.label} ending ${c.last4}` : 'Card';
}

function clk(t: number): string {
  return clockLabel(app.sim.scn, t, false);
}

type Phase = 'none' | 'planned' | 'gate' | 'driving' | 'parked' | 'paid' | 'left' | 'cancelled';
function phase(): Phase {
  return phaseOf(me());
}

/** parkT is -1 until a car parks; cars parked before the demo began have a negative time, so test the sentinel. */
function everParked(v: Vehicle): boolean {
  return v.parkT !== -1;
}

function phaseOf(v: Vehicle | null): Phase {
  if (!v) return 'none';
  if (v.state === 'cancelled') return 'cancelled';
  if (v.state === 'pending') return 'planned';
  if (v.state === 'queued') return 'gate';
  if (v.state === 'driving' || v.state === 'parking') return everParked(v) ? 'parked' : 'driving';
  if (v.state === 'parked') return v.paidT <= app.sim.t ? 'paid' : 'parked';
  if (v.state === 'unparking' || v.state === 'leaving') return everParked(v) ? 'paid' : 'driving';
  return 'left';
}

function bayNo(b: Bay): string {
  return b.id.split('-').pop() || b.id;
}

function freeIn(floor: number, zone: ZoneId, types: BayType[]): number {
  const sim = app.sim;
  return sim.L.bays.filter((b) => b.floor === floor && b.zone === zone && types.includes(b.type) && sim.isFree(b.idx)).length;
}

function feeFor(parkedS: number, member: boolean): { hours: number; rm: number } {
  const hours = Math.max(1, Math.ceil(parkedS / 3600));
  const rm = member ? Math.max(0, hours - 1) * 2 : 3 + Math.max(0, hours - 1) * 2;
  return { hours, rm };
}

function fmtStay(s: number): string {
  const m = Math.max(0, Math.round(s / 60));
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')} min`;
}

function fmtShortS(s: number): string {
  const r = Math.max(0, Math.round(s));
  return r < 60 ? `${r} s` : `${Math.floor(r / 60)} min ${String(r % 60).padStart(2, '0')} s`;
}

// ---------------------------------------------------------------- guidance
interface Guidance {
  key: string;
  picto: string;
  title: string;
  sub: string;
  step: number;
  floor: number;
  zone: ZoneId | null;
  tone: 'go' | 'warn';
}

function target(v: Vehicle): { floor: number; zone: ZoneId; bay: Bay | null } | null {
  const L = app.sim.L;
  if (v.bay >= 0) {
    const b = L.bays[v.bay];
    return { floor: b.floor, zone: b.zone, bay: b };
  }
  if (v.target) return { floor: v.target.floor, zone: v.target.zone, bay: null };
  return null;
}

function guidanceFor(v: Vehicle): Guidance {
  const sim = app.sim;
  const L = sim.L;
  const lift = DEST_BY_ID[v.dest].lift;
  if (v.state === 'pending') {
    const res = myRes();
    const rb = res && res.status === 'confirmed' ? L.bays[res.bay] : null;
    const pv = rb ? null : sim.previewAllocation(v.dest, v.elig);
    const z = rb ? { floor: rb.floor, zone: rb.zone } : pv && pv.chosen ? { floor: pv.chosen.floor, zone: pv.chosen.zone } : null;
    return {
      key: 'pending',
      picto: 'gate',
      title: `Arrive at about ${clk(v.arrivalT)}`,
      sub: rb ? `Bay ${rb.id} is held for you. Use the main entrance.` : z ? `Right now that means ${FLOOR_NAMES[z.floor]}, Zone ${z.zone}. We confirm at the barrier.` : 'Use the main entrance. Guidance starts at the barrier.',
      step: 0,
      floor: z ? z.floor : 0,
      zone: z ? z.zone : null,
      tone: 'go'
    };
  }
  if (v.state === 'queued') {
    return { key: 'queued', picto: 'gate', title: 'At the entrance', sub: 'The barrier opens in a moment. Then drive straight on.', step: 0, floor: 0, zone: v.target ? v.target.zone : null, tone: 'go' };
  }
  if (v.state === 'parked' || (v.parkT >= 0 && v.state !== 'leaving')) {
    const b = L.bays[v.bay];
    return { key: 'parked', picto: 'done', title: `Parked in ${b.id}`, sub: `Walk to Lift ${lift} for ${DEST_BY_ID[v.dest].label}.`, step: 4, floor: b.floor, zone: b.zone, tone: 'go' };
  }
  if (v.state === 'leaving' || v.state === 'unparking') {
    return { key: 'leaving', picto: 'alert', title: v.gaveUp ? 'No bay found' : 'Heading to the exit', sub: v.gaveUp ? 'Sorry, the car park stayed full. Follow the exit signs.' : 'Follow the exit signs.', step: 4, floor: sim.vehicleFloor(v), zone: null, tone: 'warn' };
  }
  const tg = target(v);
  const curF = sim.vehicleFloor(v);
  if (!tg) {
    const a = v.alloc;
    return { key: `none-${curF}`, picto: 'alert', title: 'Nearly full', sub: a ? a.message : 'Looking for space. Keep following the aisle.', step: 1, floor: curF, zone: null, tone: 'warn' };
  }
  const reserved = !!v.resId && !!tg.bay;
  if (v.state === 'parking') {
    return { key: `parking-${tg.bay ? tg.bay.idx : ''}`, picto: 'park', title: `Parking in bay ${tg.bay ? bayNo(tg.bay) : ''}`, sub: tg.bay ? `${tg.bay.id}. Nice and easy.` : '', step: 3, floor: tg.floor, zone: tg.zone, tone: 'go' };
  }
  if (curF < tg.floor) {
    const two = tg.floor - curF > 1;
    return {
      key: `down-${curF}-${tg.floor}`,
      picto: 'down',
      title: `Go down to ${FLOOR_NAMES[tg.floor]}`,
      sub: two ? `Take the down ramp at the far end, then the next one too. Zone ${tg.zone} is by Lift ${tg.zone}.` : `Take the down ramp at the far end. Then Zone ${tg.zone}.`,
      step: 1,
      floor: tg.floor,
      zone: tg.zone,
      tone: 'go'
    };
  }
  if (curF > tg.floor) {
    return { key: `up-${curF}-${tg.floor}`, picto: 'up', title: `Go up to ${FLOOR_NAMES[tg.floor]}`, sub: 'Use the up ramp at the entrance end.', step: 1, floor: tg.floor, zone: tg.zone, tone: 'go' };
  }
  const e = v.edge >= 0 ? L.edges[v.edge] : null;
  const inZone = !!e && e.kind === 'aisle' && e.zone === tg.zone;
  const types = reserved ? [] : v.elig;
  const n = reserved ? 1 : freeIn(tg.floor, tg.zone, types);
  if (tg.bay) {
    return {
      key: `bay-${tg.bay.idx}`,
      picto: 'park',
      title: `Park in bay ${bayNo(tg.bay)}`,
      sub: reserved ? `${tg.bay.id} is held for you. Look for the purple light.` : `${tg.bay.id}, Zone ${tg.zone}. Its light is green.`,
      step: 3,
      floor: tg.floor,
      zone: tg.zone,
      tone: 'go'
    };
  }
  if (inZone) {
    return { key: `zone-in-${tg.floor}${tg.zone}`, picto: 'park', title: 'Park in any green-lit bay', sub: `${n} free in Zone ${tg.zone} right now.`, step: 3, floor: tg.floor, zone: tg.zone, tone: 'go' };
  }
  return {
    key: `zone-${tg.floor}${tg.zone}`,
    picto: 'zone',
    title: `Follow the aisle to Zone ${tg.zone}`,
    sub: `${ZONE_COLOUR[tg.zone][0].toUpperCase() + ZONE_COLOUR[tg.zone].slice(1)} pillar bands. ${n} bay${n === 1 ? '' : 's'} free there.`,
    step: 2,
    floor: tg.floor,
    zone: tg.zone,
    tone: 'go'
  };
}

// ---------------------------------------------------------------- rendering: shell
function renderHeader() {
  const sim = app.sim;
  setHTML($('#clock'), `${esc(sim.clock(true))}`);
  const ph = phase();
  const dot = $('#trip-dot');
  dot.hidden = !(ph === 'planned' || ph === 'gate' || ph === 'driving');
}

function renderTabs() {
  for (const b of $$('#tabbar [data-tab]')) {
    const on = b.dataset.tab === app.tab;
    b.setAttribute('aria-selected', String(on));
    b.tabIndex = on ? 0 : -1;
  }
  const carBadge = $('#tab-car-badge');
  carBadge.hidden = !app.stays.some((st) => ['parked', 'paid'].includes(phaseOf(vOf(st))));
}

// Level board: the same dot-matrix sign that hangs at the mall entrance.
function boardHTML(compact = false): string {
  const c = app.sim.counts();
  const generalTotal = app.sim.L.bays.filter((b) => b.type === 'general' && b.flag === 'none').length;
  const rows = [0, 1, 2]
    .map((f) => {
      const n = c.perFloor[f].generalFree;
      const tone = n === 0 ? 'full' : n <= 8 ? 'low' : 'ok';
      const zones = ZONES.map((z) => `<span class="zc zc-${z.toLowerCase()}"><i></i>${freeIn(f, z, ['general'])}</span>`).join('');
      return `<div class="lvl lvl-${tone}" data-floor="${f}">
        <span class="plate">${FLOOR_NAMES[f]}</span>
        <span class="led">${dotMatrix(n === 0 ? 'FULL' : String(n), 4, compact ? 3.4 : 3.8, n === 0 ? 'Full' : `${n} free`)}</span>
        <span class="lvl-z" aria-label="Free by zone">${zones}</span>
        <span class="sr">${FLOOR_NAMES[f]}: ${n} general bays free.</span>
      </div>`;
    })
    .join('');
  return `<div class="sign-h"><span>Parking available</span><span class="sign-total"><b id="board-total">${c.generalFree}</b> of ${generalTotal}</span></div>
    <div class="sign-rows">${rows}</div>
    <div class="sign-f"><span>Free bays by zone</span><span class="zkey"><span><i class="zc-a"></i>A</span><span><i class="zc-b"></i>B</span><span><i class="zc-c"></i>C</span></span></div>`;
}

function animateBoardChanges(host: HTMLElement) {
  const c = app.sim.counts();
  for (let f = 0; f < 3; f++) {
    const n = c.perFloor[f].generalFree;
    if (app.boardVals[f] >= 0 && app.boardVals[f] !== n) {
      const led = host.querySelector(`.lvl[data-floor="${f}"] .dm`);
      animate(led, { transform: [`translateY(${n > app.boardVals[f] ? 45 : -45}%)`, 'translateY(0%)'], opacity: [0, 1] }, { spring: { stiffness: 500, damping: 30 } });
    }
    app.boardVals[f] = n;
  }
}

function busyHTML(): string {
  const sim = app.sim;
  const f = sim.forecast;
  const c = sim.counts();
  const nowOcc = c.occupied / c.usable;
  if (!f) return '';
  const bars: number[] = [nowOcc];
  for (let k = 0; k < 11; k++) {
    const seg = f.intent.occ.slice(k * 5, k * 5 + 5);
    bars.push(seg.reduce((a, b) => a + b, 0) / Math.max(1, seg.length) / f.usable);
  }
  const fill = f.fillMin.intent;
  const peak = Math.max(...bars);
  let head: string;
  let advice: string;
  let tone: string;
  if (fill !== null) {
    tone = 'crit';
    head = `Nearly full by ${clk(sim.t + fill * 60)}`;
    const before = sim.t + Math.max(0, fill - 15) * 60;
    advice = fill > 20 ? `Come before ${clk(before)}, or book an EV, family or member bay.` : 'Expect a short wait. Guidance sends you to the next free zone.';
  } else if (peak >= 0.85) {
    tone = 'warn';
    head = 'Getting busy';
    advice = `About ${Math.round(peak * 100)}% full at the busiest point in the next hour.`;
  } else {
    tone = 'ok';
    head = 'Plenty of space';
    advice = 'No queue expected in the next hour.';
  }
  const W = 300, H = 64, bw = W / bars.length;
  const svg = bars
    .map((o, i) => {
      const h = Math.max(4, Math.min(1, o) * (H - 14));
      const cls = o >= 0.95 ? 'b-crit' : o >= 0.85 ? 'b-warn' : 'b-ok';
      return `<rect x="${(i * bw + 2).toFixed(1)}" y="${(H - 14 - h).toFixed(1)}" width="${(bw - 4).toFixed(1)}" height="${h.toFixed(1)}" rx="2.5" class="${cls}${i === 0 ? ' b-now' : ''}"/>`;
    })
    .join('');
  const ticks = `<text x="${bw / 2}" y="${H - 2}" class="b-t">Now</text><text x="${bw * 6 + bw / 2}" y="${H - 2}" class="b-t">${clk(sim.t + 30 * 60)}</text><text x="${W - bw / 2}" y="${H - 2}" class="b-t">${clk(sim.t + 55 * 60)}</text>`;
  return `<div class="busy-h"><span class="busy-dot t-${tone}"></span><div><b>${esc(head)}</b><p>${esc(advice)}</p></div></div>
    <svg class="busy-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Forecast occupancy for the next hour, five-minute steps">${svg}${ticks}</svg>
    <p class="fine">Forecast from typical Saturdays plus cinema, dining, event and “I’m on my way” signals.</p>`;
}

// ---------------------------------------------------------------- tab: park
function renderPark() {
  const sim = app.sim;
  const host = $('#tab-park');
  if (!host.dataset.built) {
    host.innerHTML = `<div class="sign" id="park-sign" aria-label="Parking available by level"></div>
      <div id="park-cta"></div>
      <section class="block" aria-labelledby="busy-title"><h2 id="busy-title" class="sr">Busy forecast</h2><div class="busy" id="park-busy"></div></section>
      <section class="block" aria-labelledby="sp-title"><h2 id="sp-title" class="h2">Special bays</h2><div class="sp-list" id="park-special"></div></section>
      <p class="fine center">KL East Mall pilot concept · Illustrative layout · Simulated data</p>`;
    host.dataset.built = '1';
  }
  const sign = $('#park-sign');
  setHTML(sign, boardHTML());
  animateBoardChanges(sign);
  setHTML($('#park-busy'), busyHTML());
  const ph = phase();
  const v = me();
  let cta: string;
  if (ph === 'planned' || ph === 'gate' || ph === 'driving') {
    const g = v ? guidanceFor(v) : null;
    cta = `<button type="button" class="trip-card" data-act="open-guide">
      <span class="trip-ic">${ic('nav', 20)}</span>
      <span class="trip-t"><b>${esc(tripPlate())} ${ph === 'planned' ? `on the way to ${esc(DEST_BY_ID[v!.dest].label)}` : 'guidance is on'}</b><span>${g ? esc(g.title) : ''}</span></span>
      <span class="trip-go">${ic('chev', 20)}</span></button>`;
  } else {
    cta = `<button type="button" class="cta" data-act="plan">${ic('nav', 20)}<span>I’m on my way</span></button>
      <p class="cta-sub">Tell us where you’re going in the mall. We’ll pick the level and zone nearest your lift.</p>`;
  }
  // cars already in the car park: where, how long, how much
  const parked = app.stays.filter((st) => {
    const p = phaseOf(vOf(st));
    return p === 'parked' || p === 'paid';
  });
  if (parked.length) {
    cta += `<div class="parked-list">${parked
      .map((st) => {
        const pv = vOf(st)!;
        const b = sim.L.bays[pv.bay];
        const paid = pv.paidT <= sim.t;
        const fee = st.receipt ? st.receipt.fee : feeFor(sim.t - pv.parkT, app.account.member).rm;
        return `<button type="button" class="trip-card trip-parked" data-act="car-open" data-plate="${esc(st.plate)}">
          <span class="plate plate-sm">${FLOOR_NAMES[b.floor]}</span>
          <span class="trip-t"><b>${esc(st.plate)} is in ${esc(b.id)}</b><span>${paid ? `Paid ${rm(fee)}. Exit by ${clk(pv.paidT + 15 * 60)}.` : `Parked ${fmtStay(sim.t - pv.parkT)}, ${rm(fee)} so far`}</span></span>
          <span class="trip-go">${ic('chev', 20)}</span></button>`;
      })
      .join('')}</div>`;
  }
  setHTML($('#park-cta'), cta);
  const sp = (['ev', 'family', 'member'] as ResType[])
    .map((t) => {
      const q = sim.bookable(t);
      const ico = t === 'ev' ? 'zap' : t === 'family' ? 'family' : 'star';
      return `<button type="button" class="sp" data-act="reserve-type" data-type="${t}"><span class="sp-ic sp-${t}">${ic(ico, 18)}</span><span class="sp-t"><b>${RES_LABEL[t]}</b><span>${q.bookable ? `${q.bookable} bookable now` : 'Fully booked'}</span></span>${ic('chev', 18)}</button>`;
    })
    .join('');
  setHTML(
    $('#park-special'),
    sp +
      `<button type="button" class="sp" data-act="assist"><span class="sp-ic sp-oku">${ic('oku', 18)}</span><span class="sp-t"><b>Accessible (OKU)</b><span>Kept free for permit holders. Ask for help on arrival.</span></span>${ic('chev', 18)}</button>`
  );
  if (!app.booted) {
    const tot = document.getElementById('board-total');
    const to = sim.counts().generalFree;
    if (tot) tweenNumber(0, to, 0.9, (x) => (tot.textContent = String(Math.round(x))));
    const rows = $$('#park-sign .lvl');
    rows.forEach((r, i) => animate(r, { opacity: [0, 1], transform: ['translateY(10px)', 'translateY(0px)'] }, { duration: 0.42, delay: 0.08 + i * 0.07 }));
  }
}

// ---------------------------------------------------------------- tab: reserve
function renderReserve() {
  const sim = app.sim;
  const host = $('#tab-reserve');
  if (!host.dataset.built) {
    host.innerHTML = `<header class="tab-h"><h1>Reserve a bay</h1><p>General parking needs no booking: the app guides you to a free zone. Book only an EV, family or member bay.</p></header>
      <div id="res-active"></div><div id="res-form"></div><div id="res-list"></div>`;
    host.dataset.built = '1';
  }
  const r = myRes();
  const active = r && (r.status === 'confirmed' || r.status === 'checked-in');
  if (active && r) {
    const b = sim.L.bays[r.bay];
    const holdEnd = r.windowEnd + r.grace;
    const left = holdEnd - sim.t;
    const total = holdEnd - r.createdT;
    const k = Math.max(0, Math.min(1, left / Math.max(1, total)));
    const C = 2 * Math.PI * 26;
    setHTML(
      $('#res-active'),
      `<article class="ticket" aria-label="Your reservation">
        <div class="ticket-top"><span class="ticket-ic sp-${r.type}">${ic(r.type === 'ev' ? 'zap' : r.type === 'family' ? 'family' : 'star', 18)}</span><div><b>${RES_LABEL[r.type]} bay held</b><span>${esc(r.id)}, ${r.status === 'checked-in' ? 'checked in' : 'confirmed'}</span></div></div>
        <div class="ticket-mid">
          <div class="ticket-bay"><span class="plate">${FLOOR_NAMES[b.floor]}</span><div><b>${esc(b.id)}</b><span>Zone ${b.zone}, near Lift ${b.zone}</span></div></div>
          <div class="ring" role="img" aria-label="Hold time left"><svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="26" class="ring-bg"/><circle cx="32" cy="32" r="26" class="ring-fg" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${(C * (1 - k)).toFixed(1)}"/></svg><span><b>${Math.max(0, Math.ceil(left / 60))}</b>min</span></div>
        </div>
        <dl class="ticket-facts"><div><dt>Arrive</dt><dd>${clk(r.windowStart)}–${clk(r.windowEnd)}</dd></div><div><dt>Held until</dt><dd>${clk(holdEnd)}</dd></div><div><dt>Stay</dt><dd>${Math.round(r.durationS / 60)} min</dd></div></dl>
        <p class="fine">If you’re not here 10 minutes after your window, the bay goes back to other ${typeText(r.type)} drivers.</p>
        <div class="g-actions">${r.status === 'confirmed' ? `<button type="button" class="btn btn-primary btn-wide" data-act="res-go">${ic('nav', 16)} I’m on my way</button><button type="button" class="btn btn-ghost btn-wide" data-act="res-cancel">Cancel booking</button>` : `<button type="button" class="btn btn-primary btn-wide" data-act="open-guide">${ic('nav', 16)} Open guidance</button>`}</div>
      </article>`
    );
  } else setHTML($('#res-active'), r && app.resMsg ? `<p class="note ${app.resErr ? 'warn' : ''}">${esc(app.resMsg)}</p>` : '');

  if (!active) {
    const d = app.resDraft;
    if (!d.touched && sim.bookable(d.type).bookable < 1) {
      const ok = (['ev', 'family', 'member'] as ResType[]).find((t) => sim.bookable(t).bookable > 0);
      if (ok) d.type = ok;
    }
    const freeC = freeCars();
    if (!d.plate || !freeC.find((c) => c.plate === d.plate)) d.plate = freeC[0]?.plate || '';
    const car = d.plate ? carOf(d.plate) : null;
    const verified = resVerified(d.type, car);
    const memberLocked = d.type === 'member' && !app.account.member;
    const q = sim.bookable(d.type);
    const typeBtns = (['ev', 'family', 'member'] as ResType[])
      .map((t) => {
        const qq = sim.bookable(t);
        return `<button type="button" role="radio" aria-checked="${d.type === t}" data-act="res-type" data-type="${t}" class="opt"><span class="opt-ic sp-${t}">${ic(t === 'ev' ? 'zap' : t === 'family' ? 'family' : 'star', 18)}</span><b>${RES_LABEL[t]}</b><span>${qq.bookable ? `${qq.bookable} bookable` : 'Full'}</span></button>`;
      })
      .join('');
    const chips = (vals: number[], cur: number, act: string, fmt: (x: number) => string) =>
      vals.map((x) => `<button type="button" class="chip" data-act="${act}" data-v="${x}" aria-pressed="${cur === x}">${fmt(x)}</button>`).join('');
    const disabled = q.bookable < 1 || memberLocked || !car;
    const carChips = freeC.map((c) => `<button type="button" class="chip chip-car" data-act="res-car" data-plate="${esc(c.plate)}" aria-pressed="${d.plate === c.plate}"><b>${esc(c.plate)}</b><span>${esc(c.name)}</span></button>`).join('');
    const eligHTML = memberLocked
      ? `<p class="note warn">${ic('star', 16)} Member bays are for KL East Mall Rewards members. <button type="button" class="linkbtn" data-act="profile">Join in your account</button></p>`
      : verified
      ? `<p class="note ok">${ic('check', 16)} Verified: ${esc(verified)}.</p>`
      : `<label class="check"><input type="checkbox" id="res-elig" ${d.elig ? 'checked' : ''}><span>${esc(RES_ELIG[d.type])}</span></label>`;
    setHTML(
      $('#res-form'),
      `<form class="form" id="res-form-el" novalidate>
        <fieldset><legend>Bay type</legend><div class="opts" role="radiogroup" aria-label="Bay type">${typeBtns}</div></fieldset>
        <fieldset><legend>Arriving in</legend><div class="chips">${chips([20, 30, 45, 60], d.inMin, 'res-in', (x) => `${x} min`)}</div><p class="fine">Arrival window ${clk(sim.t + d.inMin * 60)}–${clk(sim.t + (d.inMin + 15) * 60)}</p></fieldset>
        <fieldset><legend>Staying for</legend><div class="chips">${chips([60, 120, 180], d.dur, 'res-dur', (x) => `${x / 60} h`)}</div></fieldset>
        <fieldset><legend>For which car?</legend><div class="chips">${carChips || '<span class="muted">All your cars are in use. Add one in your account.</span>'}</div></fieldset>
        ${eligHTML}
        ${app.resMsg ? `<p class="note ${app.resErr ? 'warn' : ''}" role="alert">${esc(app.resMsg)}</p>` : ''}
        <button type="submit" class="btn btn-primary btn-wide" ${disabled ? 'disabled' : ''}>${q.bookable < 1 ? 'No bay can be guaranteed right now' : memberLocked ? 'Members only' : `Reserve ${RES_LABEL[d.type].toLowerCase().replace('ev', 'EV')} bay${car ? ` for ${esc(car.plate)}` : ''}`}</button>
        <p class="fine">One ${typeText(d.type)} bay is always kept for drivers who turn up without booking, so we never overbook. No payment is taken in this demo.</p>
      </form>`
    );
  } else setHTML($('#res-form'), '');
  const assist = app.sim.assistance.length
    ? `<p class="note">${esc(app.assistMsg || `Assistance request ${app.sim.assistance[app.sim.assistance.length - 1].id} logged. Staff will meet you at the entrance.`)}</p>`
    : '';
  setHTML(
    $('#res-list'),
    `<section class="block oku-block"><div class="oku-h"><span class="sp-ic sp-oku">${ic('oku', 18)}</span><div><b>Accessible (OKU) bays</b><p>These are never sold or booked. They stay free for permit holders near every lift. If you need help on arrival, let the team know.</p></div></div>
      ${assist}<button type="button" class="btn" data-act="assist">Request help on arrival</button></section>`
  );
}

// ---------------------------------------------------------------- tab: my car
function findSteps(b: Bay, lift: ZoneId): string {
  const walk = b.walk[lift];
  const colour = ZONE_COLOUR[b.zone];
  const toward = b.zone === lift ? `Stay in Zone ${b.zone}, the ${colour} pillar bands outside the lift.` : `Head toward the ${colour} pillar bands of Zone ${b.zone}.`;
  return `<ol class="find">
    <li><span class="find-ic">${ic('lift', 16)}</span><div><b>Take Lift ${lift} to ${FLOOR_NAMES[b.floor]}</b><span>Lift ${lift} serves ${esc(DESTINATIONS.filter((d) => d.lift === lift).map((d) => d.label).join(' and ') || 'this side of the mall')}.</span></div></li>
    <li><span class="find-ic">${ic('walk', 16)}</span><div><b>Walk about ${walk} m</b><span>${esc(toward)} The dotted line on the map shows the way.</span></div></li>
    <li><span class="find-ic">${ic('park', 16)}</span><div><b>Bay ${bayNo(b)}</b><span>Number painted at the bay end: ${esc(b.id)}.</span></div></li>
  </ol>`;
}

function walletHTML(): string {
  const a = app.account;
  return `<div class="w-item"><span>${ic('wallet', 15)} Wallet</span><b>${rm(a.wallet)}</b></div>
    <div class="w-item">${a.member ? `<span>${ic('star', 15)} ${esc(a.tier)} points</span><b>${a.points.toLocaleString('en-MY')}</b>` : `<span>${ic('star', 15)} Rewards</span><b class="w-off">Not a member</b>`}</div>
    <button type="button" class="btn btn-sm" data-act="topup">${ic('plus', 15)} Top up</button>`;
}

function renderCar() {
  const sim = app.sim;
  const host = $('#tab-car');
  if (!host.dataset.built) {
    host.innerHTML = `<header class="tab-h tab-h-row"><div><h1>My cars</h1><p id="car-sub"></p></div><button type="button" class="btn btn-sm btn-primary" data-act="plan-new">${ic('plus', 15)} Park a new car</button></header>
      <div class="wallet" id="car-wallet"></div>
      <div class="car-tabs" id="car-tabs" role="tablist" aria-label="Your cars"></div>
      <div id="car-top"></div><div class="map-card" id="car-mapwrap" hidden><div class="map-host" id="car-map"></div></div><div id="car-bottom"></div>
      <div class="paybar" id="car-paybar" hidden></div>`;
    host.dataset.built = '1';
    carMap = new FloorMap($('#car-map'), 'Map of the level where your car is parked');
  }
  setHTML($('#car-wallet'), walletHTML());
  const shown = app.stays.filter((st) => phaseOf(vOf(st)) !== 'cancelled' && phaseOf(vOf(st)) !== 'none');
  const inside = shown.filter((st) => ['parked', 'paid'].includes(phaseOf(vOf(st)))).length;
  setHTML($('#car-sub'), shown.length ? `${inside} parked, ${app.garage.length} in your garage` : 'Nothing parked right now');
  if (!shown.find((st) => st.plate === app.carSel)) app.carSel = shown.length ? shown[0].plate : '';
  const statusOf = (st: Stay) => {
    const p = phaseOf(vOf(st));
    const v = vOf(st)!;
    if (p === 'parked') return v.bay >= 0 ? sim.L.bays[v.bay].id : 'Parked';
    if (p === 'paid') return 'Paid, leaving';
    if (p === 'left') return 'Trip complete';
    if (p === 'planned') return st.vid === app.myId || !app.resId ? 'Planned' : 'Booked';
    return 'On the way';
  };
  setHTML(
    $('#car-tabs'),
    shown.length > 1
      ? shown.map((st) => `<button type="button" role="tab" class="car-tab" data-act="car-sel" data-plate="${esc(st.plate)}" aria-selected="${st.plate === app.carSel}"><b>${esc(st.plate)}</b><span>${esc(statusOf(st))}</span></button>`).join('')
      : ''
  );
  const st = shown.find((x) => x.plate === app.carSel);
  const v = vOf(st);
  const ph = phaseOf(v);
  const wrap = $('#car-mapwrap');
  const bar = $('#car-paybar');
  bar.hidden = true;
  if (!st || !v) {
    wrap.hidden = true;
    setHTML($('#car-top'), `<div class="empty"><span class="empty-ic">${ic('park', 26)}</span><h1>No car parked</h1><p>When you park with guidance, the bay is saved here with directions back from the lift, the time and the fee.</p><button type="button" class="btn btn-primary" data-act="plan-new">${ic('nav', 16)} Park a car</button></div>`);
    setHTML($('#car-bottom'), '');
    return;
  }
  if (ph === 'planned' || ph === 'gate' || ph === 'driving') {
    wrap.hidden = true;
    setHTML($('#car-top'), `<div class="empty"><span class="empty-ic">${ic('nav', 26)}</span><h1>${esc(st.plate)} is on the way</h1><p>Its bay is saved here automatically once it parks.</p>${st.vid === app.myId ? `<button type="button" class="btn btn-primary" data-act="open-guide">Open guidance</button>` : ''}</div>`);
    setHTML($('#car-bottom'), '');
    return;
  }
  const b = sim.L.bays[v.bay];
  const lift = DEST_BY_ID[v.dest].lift;
  if (ph === 'left') {
    wrap.hidden = true;
    const r = st.receipt;
    setHTML(
      $('#car-top'),
      `<div class="done-card"><span class="done-ic">${ic('check', 26)}</span><h1>${esc(st.plate)} has left</h1><p>Thanks for visiting KL East Mall.</p>
        <dl class="stats3"><div><dt>Parked for</dt><dd>${fmtStay((r ? r.at : v.exitT) - v.parkT)}</dd></div><div><dt>Paid</dt><dd>${rm(r ? r.fee : 0)}</dd></div><div><dt>Points earned</dt><dd>${r ? `+${r.earned}` : '–'}</dd></div></dl>
        <button type="button" class="btn btn-wide" data-act="car-clear" data-plate="${esc(st.plate)}">Remove from this list</button></div>`
    );
    setHTML($('#car-bottom'), '');
    return;
  }
  wrap.hidden = false;
  const paid = v.paidT <= sim.t;
  const parkedS = (paid ? v.paidT : sim.t) - v.parkT;
  const fee = st.receipt ? st.receipt.fee : feeFor(parkedS, app.account.member).rm;
  setHTML(
    $('#car-top'),
    `<div class="bay-sign" aria-label="${esc(st.plate)} parked in ${esc(b.id)}">
       <span class="plate plate-lg">${FLOOR_NAMES[b.floor]}</span>
       <div class="bay-sign-t"><span class="bs-zone zc-${b.zone.toLowerCase()}"><i></i>Zone ${b.zone}</span><b>Bay ${bayNo(b)}</b><span>${esc(b.id)}, ${esc(st.plate)}</span></div>
     </div>`
  );
  const r = st.receipt;
  setHTML(
    $('#car-bottom'),
    `<section class="block fee">
       <div class="fee-row fee-3"><div><span>Parked since</span><b>${clk(v.parkT)}</b></div><div><span>Parked for</span><b>${fmtStay(parkedS)}</b></div><div><span>${paid ? 'Paid' : 'Fee so far'}</span><b>${rm(fee)}</b></div></div>
       <p class="fine">Illustrative rates: ${app.account.member ? 'members park the first hour free, then RM 2 per hour' : 'RM 3 for the first hour, then RM 2 per hour'}.</p>
       ${paid && r ? `<p class="note ok">${ic('check', 16)} Paid at ${clk(r.at)}${r.pointsUsed ? ` with ${r.pointsUsed.toLocaleString('en-MY')} points` : ''}${r.charged > 0 ? `${r.pointsUsed ? ' and' : ''} ${rm(r.charged)} from your ${esc(methodLabel(r.method))}` : ''}. Exit by ${clk(r.at + 15 * 60)}; the barrier reads ${esc(st.plate)}.</p>` : ''}
     </section>
     <section class="block"><h2 class="h2">Find your car</h2>${findSteps(b, lift)}</section>`
  );
  if (!paid) {
    bar.hidden = false;
    setHTML(bar, `<div class="paybar-t"><b>${fee > 0 ? rm(fee) : 'Free so far'}</b><span>${esc(st.plate)}, ${fmtStay(parkedS)}${fee > 0 ? '' : ', first hour'}</span></div><button type="button" class="btn btn-primary" data-act="pay" data-plate="${esc(st.plate)}">${ic('wallet', 17)} Pay</button>`);
  }
}

// ---------------------------------------------------------------- push screen: guidance
function renderGuide() {
  const sim = app.sim;
  const host = $('#scr-guide');
  if (!host.dataset.built) {
    host.innerHTML = `<header class="push-h"><button type="button" class="icon-btn" data-act="close-guide" aria-label="Back">${ic('back', 22)}</button><div class="push-t" id="g-title"></div><span class="eta" id="g-eta"></span></header>
      <div class="push-body">
        <div class="dsign" id="g-sign" aria-live="polite"></div>
        <div class="map-card"><div class="map-h" id="g-maph"></div><div class="map-host" id="g-map"></div></div>
        <ol class="steps" id="g-steps" aria-label="Trip steps"></ol>
        <div id="g-alt"></div>
        <div class="g-actions" id="g-actions"></div>
      </div>`;
    host.dataset.built = '1';
    guideMap = new FloorMap($('#g-map'), 'Live map of the level you are on, with your route');
  }
  const v = me();
  if (!v) return;
  const g = guidanceFor(v);
  const lift = DEST_BY_ID[v.dest].lift;
  setHTML($('#g-title'), `<b>${esc(DEST_BY_ID[v.dest].label)}</b><span>via Lift ${lift}</span>`);
  let eta = '';
  if (v.state === 'pending') eta = `${Math.max(1, Math.ceil((v.arrivalT - sim.t) / 60))} min away`;
  else if (v.state === 'driving' && v.parkT < 0) eta = `≈ ${fmtShortS(sim.routeLength(v) / 2.6 + 8)} to park`;
  else if (v.state === 'queued') eta = 'At the gate';
  setHTML($('#g-eta'), esc(eta));
  const zoneChip = g.zone ? `<span class="dsign-zone zc-${g.zone.toLowerCase()}"><i></i>Zone ${g.zone}</span>` : '';
  setHTML(
    $('#g-sign'),
    `<div class="dsign-in t-${g.tone}"><span class="dsign-p">${picto(g.picto)}</span><div class="dsign-t"><b>${esc(g.title)}</b><span>${esc(g.sub)}</span></div></div>
     <div class="dsign-f"><span class="plate plate-sm">${FLOOR_NAMES[g.floor]}</span>${zoneChip}<span class="dsign-lift">${ic('lift', 15)} Lift ${lift}</span></div>`
  );
  if (g.key !== app.lastGuideKey) {
    if (app.lastGuideKey) {
      animate($('#g-sign .dsign-t'), { opacity: [0, 1], transform: ['translateY(14px)', 'translateY(0px)'] }, { spring: { stiffness: 420, damping: 32 } });
      animate($('#g-sign .dsign-p'), { transform: ['scale(0.6)', 'scale(1)'], opacity: [0.2, 1] }, { spring: { stiffness: 520, damping: 22 } });
      if (navigator.vibrate && !reducedMotion()) {
        try {
          navigator.vibrate(18);
        } catch {
          /* not allowed */
        }
      }
    }
    app.lastGuideKey = g.key;
  }
  const curF = v.state === 'pending' ? g.floor : sim.vehicleFloor(v);
  const freeHere = g.zone ? freeIn(g.floor, g.zone, v.resId ? ['general'] : v.elig) : 0;
  setHTML($('#g-maph'), `<span><b>${FLOOR_NAMES[curF]}</b> ${v.state === 'pending' ? 'expected level' : 'you are here'}</span><span class="live-dot">Live</span>${g.zone && g.floor === curF ? `<span class="muted">${freeHere} free in Zone ${g.zone}</span>` : ''}`);
  const steps = ['Entrance', g.floor >= 0 ? `Level ${FLOOR_NAMES[g.floor]}` : 'Level', g.zone ? `Zone ${g.zone}` : 'Zone', 'Park'];
  setHTML(
    $('#g-steps'),
    steps.map((s, i) => `<li class="${i < g.step ? 'done' : i === g.step ? 'cur' : ''}"${i === g.step ? ' aria-current="step"' : ''}><span class="st-n">${i < g.step ? ic('check', 13) : i + 1}</span><span>${esc(s)}</span></li>`).join('')
  );
  const a = v.alloc;
  const needAlt = a && (a.mode === 'none' || a.mode === 'expected-departure') && v.parkT < 0;
  setHTML(
    $('#g-alt'),
    needAlt
      ? `<div class="alt"><b>${ic('alert', 16)} The car park is nearly full</b><ul><li>Keep going: departures are expected and you’ll be sent to the first bay that frees up.</li><li>Overflow car park (illustrative): about 650 m away, shuttle every 10 min.</li></ul></div>`
      : ''
  );
  let actions = '';
  if (v.state === 'pending') actions = `<button type="button" class="btn btn-primary btn-wide" data-act="arrive">${ic('pin', 16)} I’m at the entrance</button><button type="button" class="btn btn-wide" data-act="dest">Change destination</button><button type="button" class="btn btn-ghost btn-wide" data-act="cancel-trip">Cancel trip</button>`;
  else if (v.state === 'driving' && v.parkT < 0) actions = `<button type="button" class="btn" data-act="dest">Change destination</button>`;
  setHTML($('#g-actions'), actions);
}

// ---------------------------------------------------------------- push screen: parked confirmation
function showParked() {
  const sim = app.sim;
  const v = me();
  if (!v || v.bay < 0) return;
  const b = sim.L.bays[v.bay];
  const host = $('#scr-parked');
  host.innerHTML = `<div class="parked">
    <svg class="parked-check" viewBox="0 0 96 96" aria-hidden="true"><circle cx="48" cy="48" r="44" class="pc-bg"/><path d="M28 50 l13 13 l27 -29" class="pc-tick"/></svg>
    <h1 class="pk-1">Parked</h1>
    <div class="bay-sign pk-2"><span class="plate plate-lg">${FLOOR_NAMES[b.floor]}</span><div class="bay-sign-t"><span class="bs-zone zc-${b.zone.toLowerCase()}"><i></i>Zone ${b.zone}</span><b>Bay ${bayNo(b)}</b><span>${esc(b.id)}</span></div></div>
    <dl class="stats3 pk-3"><div><dt>Gate to parked</dt><dd>${fmtShortS(v.parkT - v.gateT)}</dd></div><div><dt>Driven inside</dt><dd>${fmtDist(v.searchDist)}</dd></div><div><dt>Walk to Lift ${DEST_BY_ID[v.dest].lift}</dt><dd>${b.walk[DEST_BY_ID[v.dest].lift]} m</dd></div></dl>
    <p class="pk-4">Saved to My car, with directions back from the lift.</p>
    <div class="pk-5"><button type="button" class="btn btn-primary btn-wide" data-act="parked-done">Done</button></div>
  </div>`;
  app.screen = 'parked';
  host.hidden = false;
  $('#scr-guide').hidden = true;
  setTabbar(false);
  animate(host, { opacity: [0, 1] }, { duration: 0.2 });
  animate(host.querySelector('.parked-check'), { transform: ['scale(0.4)', 'scale(1)'], opacity: [0, 1] }, { spring: { stiffness: 380, damping: 18 } });
  const tick = host.querySelector('.pc-tick') as SVGPathElement;
  tick.style.strokeDasharray = '80';
  animate(tick, { strokeDashoffset: [80, 0] }, { duration: 0.5, delay: 0.25, ease: [0.4, 0, 0.2, 1] });
  ['.pk-1', '.pk-2', '.pk-3', '.pk-4', '.pk-5'].forEach((s, i) => animate(host.querySelector(s), { opacity: [0, 1], transform: ['translateY(16px)', 'translateY(0px)'] }, { duration: 0.45, delay: 0.35 + i * 0.07 }));
  if (navigator.vibrate && !reducedMotion()) {
    try {
      navigator.vibrate([20, 60, 30]);
    } catch {
      /* not allowed */
    }
  }
}

// ---------------------------------------------------------------- navigation and motion
function setTabbar(show: boolean) {
  const tb = $('#tabbar');
  if (show === !tb.classList.contains('away')) return;
  tb.classList.toggle('away', !show);
  animate(tb, { transform: show ? ['translateY(100%)', 'translateY(0%)'] : ['translateY(0%)', 'translateY(100%)'] }, { duration: 0.28, ease: [0.3, 0.7, 0.2, 1] });
}

function goTab(t: Tab) {
  if (app.screen) closePush(false);
  const changed = t !== app.tab;
  app.tab = t;
  for (const id of ['park', 'reserve', 'car'] as Tab[]) $(`#tab-${id}`).hidden = id !== t;
  renderAll();
  if (changed) {
    $('#tabview').scrollTop = 0;
    animate($(`#tab-${t}`), { opacity: [0, 1], transform: ['translateY(8px)', 'translateY(0px)'] }, { duration: 0.26 });
  }
}

function openGuide() {
  if (!me()) return;
  closeSheet();
  app.screen = 'guide';
  const g = $('#scr-guide');
  g.hidden = false;
  $('#scr-parked').hidden = true;
  renderGuide();
  setTabbar(false);
  g.scrollTop = 0;
  animate(g, { transform: ['translateX(100%)', 'translateX(0%)'] }, { spring: SPRING_PUSH });
  animate($('#tabview'), { transform: ['translateX(0%)', 'translateX(-22%)'], opacity: [1, 0.6] }, { duration: 0.3 });
  ($('#scr-guide .icon-btn') as HTMLElement).focus({ preventScroll: true });
}

function closePush(anim = true) {
  const which = app.screen;
  if (!which) return;
  app.screen = '';
  const el = $(which === 'guide' ? '#scr-guide' : '#scr-parked');
  setTabbar(true);
  const tv = $('#tabview');
  if (anim && which === 'guide') {
    animate(el, { transform: ['translateX(0%)', 'translateX(100%)'] }, { duration: 0.26, ease: [0.4, 0, 0.6, 1] }).then(() => {
      if (app.screen !== 'guide') el.hidden = true;
    });
  } else el.hidden = true;
  animate(tv, { transform: [anim ? 'translateX(-22%)' : 'translateX(0%)', 'translateX(0%)'], opacity: [anim ? 0.6 : 1, 1] }, { duration: anim ? 0.3 : 0.01 });
  renderAll();
}

// ---------------------------------------------------------------- sheets
function sheetHTML(kind: SheetKind): string {
  const sim = app.sim;
  if (kind === 'plan') {
    const p = app.plan;
    const dests = DESTINATIONS.map(
      (d) => `<button type="button" class="dest" data-act="plan-dest" data-v="${d.id}" aria-pressed="${p.dest === d.id}"><span class="dest-ic">${ic(DEST_ICON[d.id], 20)}</span><b>${esc(d.label)}</b><span>Lift ${d.lift}</span></button>`
    ).join('');
    const etas = [0, 10, 20, 30].map((x) => `<button type="button" class="chip" data-act="plan-eta" data-v="${x}" aria-pressed="${p.eta === x}">${x === 0 ? 'Now' : `${x} min`}</button>`).join('');
    const free = freeCars();
    if (!free.find((c) => c.plate === p.plate)) p.plate = free.length ? free[0].plate : '';
    const car = p.plate ? carOf(p.plate) : null;
    const pv = sim.previewAllocation(p.dest, car ? eligFor(car) : ['general']);
    const f = sim.forecast;
    const occAt = f && p.eta > 0 ? f.intent.occ[Math.min(f.intent.occ.length - 1, p.eta)] / f.usable : NaN;
    const ch = pv.chosen;
    const heldRes = myRes();
    const heldBay = heldRes && heldRes.status === 'confirmed' ? sim.L.bays[heldRes.bay] : null;
    const carChips = free
      .map((c) => `<button type="button" class="chip chip-car" data-act="plan-car" data-plate="${esc(c.plate)}" aria-pressed="${p.plate === c.plate}"><b>${esc(c.plate)}</b><span>${esc(c.name)}</span></button>`)
      .join('');
    const pref = car
      ? `<div class="prefs"><span>This car</span>${(['ev', 'family'] as const)
          .map((k) => `<button type="button" class="tog" data-act="car-attr" data-k="${k}" data-plate="${esc(car.plate)}" aria-pressed="${car[k]}">${k === 'ev' ? 'Electric' : 'Family pass'}</button>`)
          .join('')}</div>`
      : '';
    const member = app.account.member
      ? `<div class="member-line">${ic('star', 16)}<span><b>${esc(app.account.tier)} member</b> from your account: first hour free and member bays included.</span></div>`
      : `<div class="member-line off">${ic('star', 16)}<span>Not a Rewards member. <button type="button" class="linkbtn" data-act="profile">Join to get the first hour free</button></span></div>`;
    return `<h2 class="sheet-t" id="sheet-title">Where are you going?</h2>
      <div class="dests">${dests}</div>
      <h3 class="sheet-s">Arriving in</h3><div class="chips">${etas}</div>
      <h3 class="sheet-s">Which car?</h3>
      <div class="chips">${carChips}${app.addingCar ? '' : `<button type="button" class="chip chip-add" data-act="car-add">${ic('plus', 15)} Add a car</button>`}</div>
      ${app.addingCar ? addCarHTML() : ''}
      ${free.length ? '' : '<p class="note warn">All your cars are parked or on the way. Add another car to park it.</p>'}
      ${pref}
      ${member}
      <div class="preview" aria-live="polite">${
        heldBay
          ? `<span class="plate plate-sm">${FLOOR_NAMES[heldBay.floor]}</span><div><b>Bay ${esc(heldBay.id)} is held for you</b><span>Arrive ${clk(heldRes!.windowStart)}–${clk(heldRes!.windowEnd)}. The purple light marks it; we guide you straight there.</span></div>`
          : ch
          ? `<span class="plate plate-sm">${FLOOR_NAMES[ch.floor]}</span><div><b>Zone ${ch.zone}, about ${Math.round(ch.walk)} m to Lift ${DEST_BY_ID[p.dest].lift}</b><span>${ch.free} suitable bay${ch.free === 1 ? '' : 's'} free there now.${isFinite(occAt) ? ` By ${clk(sim.t + p.eta * 60)} the car park should be about ${Math.round(occAt * 100)}% full, so we check again at the barrier.` : ' We confirm at the barrier.'}</span></div>`
          : `<span class="plate plate-sm plate-warn">!</span><div><b>Nearly full right now</b><span>${esc(pv.message)}</span></div>`
      }</div>
      <button type="button" class="btn btn-primary btn-wide" data-act="start" ${car ? '' : 'disabled'}>${ic('nav', 18)} Start guidance${car ? ` for ${esc(car.plate)}` : ''}</button>
      <p class="fine">Your arrival time is shared anonymously so the forecast can plan for you.</p>`;
  }
  if (kind === 'dest') {
    const v = me();
    const dests = DESTINATIONS.map(
      (d) => `<button type="button" class="dest" data-act="set-dest" data-v="${d.id}" aria-pressed="${v ? v.dest === d.id : false}"><span class="dest-ic">${ic(DEST_ICON[d.id], 20)}</span><b>${esc(d.label)}</b><span>Lift ${d.lift}</span></button>`
    ).join('');
    return `<h2 class="sheet-t" id="sheet-title">Change destination</h2><p class="sheet-p">Guidance re-checks the best zone from your next junction.</p><div class="dests">${dests}</div>`;
  }
  if (kind === 'pay') {
    const q = payQuote();
    if (!q) return '<p class="sheet-p">Nothing to pay for this car.</p>';
    const a = app.account;
    const b = sim.L.bays[q.v.bay];
    const methods = (['wallet', 'debit', 'credit'] as PayMethod[])
      .map((m) => {
        const card = a.cards.find((c) => c.id === m);
        const sub = m === 'wallet' ? `Balance ${rm(a.wallet)}` : card ? 'Connected' : '';
        return `<button type="button" role="radio" class="method" data-act="pay-method" data-v="${m}" aria-checked="${app.pay.method === m}">
          <span class="m-ic m-${m}">${ic(m === 'wallet' ? 'wallet' : 'card', 18)}</span>
          <span class="m-t"><b>${esc(methodLabel(m))}</b><span>${esc(sub)}</span></span>
          <span class="radio" aria-hidden="true"></span></button>`;
      })
      .join('');
    const pts = a.member
      ? `<button type="button" class="tog tog-row tog-pts" data-act="pay-points" aria-pressed="${app.pay.usePoints}"><b>Use member points</b><span>${a.points.toLocaleString('en-MY')} points available. ${POINTS_PER_RM} points = RM 1.</span></button>`
      : `<p class="fine">Rewards members can pay with points and earn ${EARN_PER_RM} points per RM 1.</p>`;
    const payLabel = q.remaining > 0 ? `Pay ${rm(q.remaining)}` : q.pointsUsed > 0 ? `Pay with ${q.pointsUsed.toLocaleString('en-MY')} points` : 'Nothing to pay, leave now';
    return `<h2 class="sheet-t" id="sheet-title">Pay for parking</h2>
      <div class="pay-sum"><span class="plate plate-sm">${FLOOR_NAMES[b.floor]}</span><div><b>${esc(q.st.plate)}, ${esc(b.id)}</b><span>${clk(q.v.parkT)} to ${clk(sim.t)}, ${fmtStay(q.parkedS)}, ${q.fee.hours} charged hour${q.fee.hours === 1 ? '' : 's'}</span></div><b class="pay-amt">${rm(q.fee.rm)}</b></div>
      ${a.member ? `<p class="note ok">${ic('star', 16)} ${esc(a.tier)} member rate: your first hour is free.</p>` : ''}
      <h3 class="sheet-s">Pay with</h3>
      <div class="methods" role="radiogroup" aria-label="Payment method">${methods}</div>
      <button type="button" class="linkbtn pay-topup" data-act="topup-from-pay">${ic('plus', 15)} Top up wallet</button>
      ${pts}
      <dl class="receipt">
        <div><dt>Parking fee</dt><dd>${rm(q.fee.rm)}</dd></div>
        ${q.pointsUsed ? `<div><dt>Points (${q.pointsUsed.toLocaleString('en-MY')})</dt><dd>−${rm(q.pointsRM)}</dd></div>` : ''}
        <div class="total"><dt>${q.remaining > 0 ? `From ${esc(methodLabel(app.pay.method))}` : 'To pay'}</dt><dd>${rm(q.remaining)}</dd></div>
      </dl>
      ${q.short > 0 ? `<div class="note warn"><span>Your wallet is ${rm(q.short)} short. Top up, use points, or pay by card.</span></div><button type="button" class="btn btn-wide" data-act="topup-from-pay">${ic('plus', 16)} Top up wallet</button>` : ''}
      <button type="button" class="btn btn-primary btn-wide" data-act="pay-confirm" ${q.short > 0 ? 'disabled' : ''}>${ic('wallet', 18)} ${payLabel}</button>
      <p class="fine">Simulated payment for this prototype: no card details are collected and no money moves. After paying you have 15 minutes to exit.</p>`;
  }
  if (kind === 'paid') {
    const r = app.pay.done;
    if (!r) return '';
    const a = app.account;
    return `<div class="paid-ok"><svg class="paid-check" viewBox="0 0 96 96" aria-hidden="true"><circle cx="48" cy="48" r="44" class="pc-bg"/><path d="M28 50 l13 13 l27 -29" class="pc-tick"/></svg>
        <h2 class="sheet-t" id="sheet-title">Paid</h2><p class="sheet-p">Exit by ${clk(r.at + 15 * 60)}. The barrier reads ${esc(app.pay.plate)} and opens by itself.</p></div>
      <dl class="receipt">
        <div><dt>Parking fee</dt><dd>${rm(r.fee)}</dd></div>
        ${r.pointsUsed ? `<div><dt>Points used</dt><dd>${r.pointsUsed.toLocaleString('en-MY')} (−${rm(r.pointsRM)})</dd></div>` : ''}
        ${r.charged > 0 ? `<div><dt>${esc(methodLabel(r.method))}</dt><dd>${rm(r.charged)}</dd></div>` : ''}
        ${a.member && r.earned > 0 ? `<div><dt>Points earned</dt><dd>+${r.earned}</dd></div>` : ''}
        <div class="total"><dt>${a.member ? 'Points balance' : 'Wallet balance'}</dt><dd>${a.member ? a.points.toLocaleString('en-MY') : rm(a.wallet)}</dd></div>
      </dl>
      <button type="button" class="btn btn-primary btn-wide" data-act="sheet-close">Done</button>`;
  }
  if (kind === 'topup') {
    const a = app.account;
    const amts = [20, 50, 100].map((x) => `<button type="button" class="chip" data-act="top-amt" data-v="${x}" aria-pressed="${app.pay.topAmt === x}">RM ${x}</button>`).join('');
    const from = a.cards
      .map((c) => `<button type="button" role="radio" class="method" data-act="top-from" data-v="${c.id}" aria-checked="${app.pay.topFrom === c.id}"><span class="m-ic m-${c.id}">${ic('card', 18)}</span><span class="m-t"><b>${esc(c.label)} ending ${esc(c.last4)}</b><span>Connected</span></span><span class="radio" aria-hidden="true"></span></button>`)
      .join('');
    return `<h2 class="sheet-t" id="sheet-title">Top up wallet</h2>
      <p class="sheet-p">Balance <b>${rm(a.wallet)}</b>. Wallet payments are one tap at the exit and the pay stations.</p>
      <h3 class="sheet-s">Amount</h3><div class="chips">${amts}</div>
      <h3 class="sheet-s">From</h3><div class="methods" role="radiogroup" aria-label="Top up from">${from}</div>
      <button type="button" class="btn btn-primary btn-wide" data-act="topup-confirm">${ic('plus', 18)} Top up RM ${app.pay.topAmt}</button>
      <p class="fine">Simulated top-up: no card details are collected and no money moves. Adding new cards is not part of this demo.</p>`;
  }
  if (kind === 'assist') {
    return `<h2 class="sheet-t" id="sheet-title">Help on arrival</h2>
      <p class="sheet-p">Accessible bays are kept free for OKU permit holders and are never booked. Tell the team you’re coming and someone will meet you at the entrance.</p>
      <h3 class="sheet-s">Arriving in</h3><div class="chips">${[10, 20, 30].map((x) => `<button type="button" class="chip" data-act="assist-eta" data-v="${x}" aria-pressed="${app.plan.eta === x}">${x} min</button>`).join('')}</div>
      <label class="check"><input type="checkbox" id="assist-permit"><span>I hold a valid OKU parking permit and will display it.</span></label>
      <p class="note warn" id="assist-err" hidden>Tick the permit box first. Staff check permits on arrival.</p>
      <button type="button" class="btn btn-primary btn-wide" data-act="assist-send">Send request</button>`;
  }
  if (kind === 'profile') {
    const p = app.profile;
    const a = app.account;
    const paces = [1, 4, 10].map((x) => `<button type="button" class="chip" data-act="pace" data-v="${x}" aria-pressed="${p.pace === x}">${x === 1 ? 'Real time' : `${x}× faster`}</button>`).join('');
    const card = a.member
      ? `<div class="mcard"><div class="mcard-top"><span class="mark mark-sm" aria-hidden="true">P</span><span>KL East Mall Rewards</span><b>${esc(a.tier)}</b></div>
          <div class="mcard-pts"><b>${a.points.toLocaleString('en-MY')}</b><span>points, worth ${rm(a.points / POINTS_PER_RM)} in parking</span></div>
          <div class="mcard-no">Member ${esc(a.memberNo)}</div></div>
         <ul class="perks"><li>First hour of parking free</li><li>Designated member bays near the lifts</li><li>Earn ${EARN_PER_RM} points per RM 1, pay parking with points</li></ul>
         <button type="button" class="btn btn-ghost btn-wide" data-act="member-toggle">Demo: continue as a non-member</button>`
      : `<div class="mcard mcard-off"><div class="mcard-top"><span class="mark mark-sm" aria-hidden="true">P</span><span>KL East Mall Rewards</span></div><div class="mcard-pts"><b>Not a member</b><span>Join free for the first hour of parking, member bays and points.</span></div></div>
         <button type="button" class="btn btn-primary btn-wide" data-act="member-toggle">Join Rewards (demo)</button>`;
    const cars = app.garage
      .map((c) => `<div class="gar"><div class="gar-t"><b>${esc(c.plate)}</b><span>${esc(c.name)}${carBusy(c.plate) ? ', in use' : ''}</span></div>${(['ev', 'family'] as const)
        .map((k) => `<button type="button" class="tog" data-act="car-attr" data-k="${k}" data-plate="${esc(c.plate)}" aria-pressed="${c[k]}">${k === 'ev' ? 'Electric' : 'Family pass'}</button>`)
        .join('')}</div>`)
      .join('');
    return `<h2 class="sheet-t" id="sheet-title">Your account</h2>
      ${card}
      <h3 class="sheet-s">Wallet</h3>
      <div class="wallet wallet-sheet">${walletHTML()}</div>
      <h3 class="sheet-s">Your cars</h3>
      <div class="garage">${cars}</div>
      ${app.addingCar ? addCarHTML() : `<button type="button" class="btn btn-wide" data-act="car-add">${ic('plus', 16)} Add a car</button>`}
      <h3 class="sheet-s">Demo clock</h3><div class="chips">${paces}</div>
      <p class="fine">This app runs on simulated data for the KL East Mall pilot concept. Account, wallet and cars are stored on this device only. Reloading restarts the demo day at 14:08.</p>
      <button type="button" class="btn btn-ghost btn-wide" data-act="restart">Restart demo day</button>`;
  }
  return '';
}

function addCarHTML(): string {
  return `<div class="addcar"><label class="field"><span>Number plate</span><input id="new-plate" maxlength="10" autocomplete="off" spellcheck="false" placeholder="e.g. BKN 4410"></label>
    <div class="row2"><button type="button" class="btn btn-primary" data-act="car-add-save">Add car</button><button type="button" class="btn btn-ghost" data-act="car-add-cancel">Cancel</button></div>
    <p class="note warn" id="addcar-err" hidden>Enter a plate with letters and numbers, for example BKN 4410.</p></div>`;
}

/** What paying for the selected car costs now, after member points, and whether the wallet covers it. */
function payQuote() {
  const st = stayOf(app.pay.plate);
  const v = vOf(st);
  if (!st || !v || v.state !== 'parked' || v.paidT <= app.sim.t) return null;
  const a = app.account;
  const parkedS = app.sim.t - v.parkT;
  const fee = feeFor(parkedS, a.member);
  const pointsRM = a.member && app.pay.usePoints ? Math.min(fee.rm, Math.floor(a.points / POINTS_PER_RM)) : 0;
  const pointsUsed = pointsRM * POINTS_PER_RM;
  const remaining = Math.max(0, +(fee.rm - pointsRM).toFixed(2));
  const short = app.pay.method === 'wallet' ? Math.max(0, +(remaining - a.wallet).toFixed(2)) : 0;
  return { st, v, fee, parkedS, pointsRM, pointsUsed, remaining, short };
}

function renderSheet() {
  if (!app.sheet) return;
  const body = $('#sheet-body');
  const a = document.activeElement as HTMLElement | null;
  if (a && body.contains(a) && a.tagName === 'INPUT') return;
  setHTML(body, sheetHTML(app.sheet));
}

function openSheet(kind: SheetKind) {
  const was = app.sheet;
  app.sheet = kind;
  const sh = $('#sheet');
  const scrim = $('#scrim');
  setHTML($('#sheet-body'), sheetHTML(kind));
  if (was) return;
  sh.hidden = false;
  scrim.hidden = false;
  sh.setAttribute('aria-labelledby', 'sheet-title');
  animate(scrim, { opacity: [0, 1] }, { duration: 0.22 });
  animate(sh, { transform: ['translateY(100%)', 'translateY(0%)'] }, { spring: SPRING_SHEET });
  setTimeout(() => {
    const first = sh.querySelector('button, input') as HTMLElement | null;
    if (first) first.focus({ preventScroll: true });
  }, 60);
}

function closeSheet() {
  if (!app.sheet) return;
  app.sheet = '';
  const sh = $('#sheet');
  const scrim = $('#scrim');
  animate(scrim, { opacity: [1, 0] }, { duration: 0.2 });
  animate(sh, { transform: [sh.style.transform || 'translateY(0%)', 'translateY(100%)'] }, { duration: 0.24, ease: [0.4, 0, 0.6, 1] }).then(() => {
    if (!app.sheet) {
      sh.hidden = true;
      scrim.hidden = true;
      sh.style.transform = '';
    }
  });
}

function bindSheetDrag() {
  const sh = $('#sheet');
  let y0 = 0, t0 = 0, dy = 0, dragging = false;
  sh.addEventListener('pointerdown', (e) => {
    const t = e.target as HTMLElement;
    if (!t.closest('.grip') && !(t.closest('.sheet-t') && sh.scrollTop <= 0)) return;
    dragging = true;
    y0 = e.clientY;
    t0 = performance.now();
    dy = 0;
    sh.setPointerCapture(e.pointerId);
  });
  sh.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    dy = Math.max(0, e.clientY - y0);
    sh.style.transform = `translateY(${dy}px)`;
  });
  const end = () => {
    if (!dragging) return;
    dragging = false;
    const vel = dy / Math.max(1, performance.now() - t0);
    if (dy > 110 || vel > 0.7) closeSheet();
    else animate(sh, { transform: [`translateY(${dy}px)`, 'translateY(0px)'] }, { spring: SPRING_SHEET });
  };
  sh.addEventListener('pointerup', end);
  sh.addEventListener('pointercancel', end);
}

function toast(msg: string) {
  const t = $('#toast');
  t.textContent = msg;
  t.hidden = false;
  animate(t, { transform: ['translateY(-130%)', 'translateY(0%)'], opacity: [0, 1] }, { spring: { stiffness: 460, damping: 30 } });
  clearTimeout(app.toastTimer);
  app.toastTimer = window.setTimeout(() => {
    animate(t, { transform: ['translateY(0%)', 'translateY(-130%)'], opacity: [1, 0] }, { duration: 0.22 }).then(() => (t.hidden = true));
  }, 3200);
}

// ---------------------------------------------------------------- actions
function startTrip() {
  const sim = app.sim;
  const car = app.plan.plate ? carOf(app.plan.plate) : null;
  if (!car) return;
  const etaS = Math.max(1, app.plan.eta * 60);
  const existing = stayOf(car.plate);
  const ev = existing ? vOf(existing) : null;
  if (existing && ev && ev.state === 'pending') {
    // the car already has a pending trip (for example a booked bay): just update it
    ev.dest = app.plan.dest;
    sim.setDriverArrival(ev.i, etaS);
    app.myId = ev.i;
  } else {
    const v = sim.addDriver({ dest: app.plan.dest, etaS, elig: eligFor(car), cls: car.ev ? 'ev' : 'ice', member: app.account.member });
    app.myId = v.i;
    app.stays.push({ plate: car.plate, vid: v.i, demo: false, receipt: null });
  }
  app.parkedShown = false;
  app.lastGuideKey = '';
  app.lastNotice = '';
  closeSheet();
  openGuide();
}

function addCarFromInput(): boolean {
  const inp = document.getElementById('new-plate') as HTMLInputElement | null;
  const plate = (inp ? inp.value : '').toUpperCase().replace(/[^A-Z0-9 ]/g, '').replace(/\s+/g, ' ').trim();
  if (!/^[A-Z]{1,3} ?\d{1,4} ?[A-Z]?$/.test(plate)) {
    const e = document.getElementById('addcar-err');
    if (e) {
      e.hidden = false;
      animate(e, { transform: ['translateX(-6px)', 'translateX(6px)', 'translateX(-3px)', 'translateX(0px)'] }, { duration: 0.3 });
    }
    return false;
  }
  if (!app.garage.find((c) => c.plate === plate)) app.garage.push({ plate, name: 'New car', ev: false, family: false });
  app.addingCar = false;
  app.plan.plate = plate;
  persistProfile();
  toast(`${plate} added to your cars`);
  return true;
}

function act(el: HTMLElement) {
  const a = el.dataset.act as string;
  const sim = app.sim;
  switch (a) {
    case 'tab':
      goTab(el.dataset.tab as Tab);
      break;
    case 'plan':
      if (phase() === 'planned' || phase() === 'gate' || phase() === 'driving') openGuide();
      else {
        if (!app.plan.plate || carBusy(app.plan.plate)) app.plan.plate = freeCars()[0]?.plate || '';
        openSheet('plan');
      }
      break;
    case 'plan-dest':
      app.plan.dest = el.dataset.v as DestId;
      renderSheet();
      break;
    case 'plan-eta':
      app.plan.eta = Number(el.dataset.v);
      renderSheet();
      break;
    case 'car-attr': {
      const c = carOf(el.dataset.plate || '');
      const k = el.dataset.k as 'ev' | 'family';
      c[k] = !c[k];
      persistProfile();
      renderSheet();
      break;
    }
    case 'plan-car':
      app.plan.plate = el.dataset.plate || '';
      renderSheet();
      break;
    case 'plan-new':
      app.plan.plate = freeCars()[0]?.plate || '';
      if (phase() === 'planned' || phase() === 'gate' || phase() === 'driving') toast(`${tripPlate()} is still on the way; guidance switches to the new car`);
      openSheet('plan');
      break;
    case 'car-add':
      app.addingCar = true;
      renderSheet();
      setTimeout(() => (document.getElementById('new-plate') as HTMLInputElement | null)?.focus(), 30);
      break;
    case 'car-add-save':
      if (addCarFromInput()) renderSheet();
      break;
    case 'car-add-cancel':
      app.addingCar = false;
      renderSheet();
      break;
    case 'car-open':
      app.carSel = el.dataset.plate || '';
      goTab('car');
      break;
    case 'car-sel':
      app.carSel = el.dataset.plate || '';
      animate($('#car-top'), { opacity: [0, 1], transform: ['translateY(6px)', 'translateY(0px)'] }, { duration: 0.22 });
      break;
    case 'car-clear':
      app.stays = app.stays.filter((x) => !(x.plate === el.dataset.plate && phaseOf(vOf(x)) === 'left'));
      break;
    case 'member-toggle':
      app.account.member = !app.account.member;
      persistProfile();
      toast(app.account.member ? `Welcome to KL East Mall Rewards (${app.account.tier})` : 'Continuing as a non-member');
      renderSheet();
      break;
    case 'pace':
      app.profile.pace = Number(el.dataset.v);
      persistProfile();
      renderSheet();
      break;
    case 'start':
      startTrip();
      break;
    case 'open-guide':
      openGuide();
      break;
    case 'close-guide':
      closePush(true);
      break;
    case 'arrive': {
      const v = me();
      if (!v) break;
      const r = myRes();
      if (r && r.status === 'confirmed' && r.vehicle === v.i) sim.checkInNow(r.id);
      else sim.setDriverArrival(v.i, 1);
      toast('You’re at the entrance. Guidance starts at the barrier.');
      break;
    }
    case 'cancel-trip': {
      const v = me();
      if (v && sim.cancelDriver(v.i)) {
        const r = myRes();
        if (r && r.vehicle === v.i && r.status === 'confirmed') sim.cancelReservation(r.id);
        app.stays = app.stays.filter((x) => x.vid !== v.i);
        app.myId = -1;
        toast('Trip cancelled');
        closePush(true);
      }
      break;
    }
    case 'dest':
      openSheet('dest');
      break;
    case 'set-dest': {
      const v = me();
      if (v) toast(sim.changeDestination(v.i, el.dataset.v as DestId));
      closeSheet();
      break;
    }
    case 'parked-done':
      app.carSel = tripPlate() || app.carSel;
      closePush(false);
      goTab('car');
      break;
    case 'pay':
      app.pay.plate = el.dataset.plate || app.carSel;
      app.pay.done = null;
      if (app.pay.method === 'wallet' && !app.account.wallet && !app.account.member) app.pay.method = 'debit';
      openSheet('pay');
      break;
    case 'pay-method':
      app.pay.method = el.dataset.v as PayMethod;
      renderSheet();
      break;
    case 'pay-points':
      app.pay.usePoints = !app.pay.usePoints;
      renderSheet();
      break;
    case 'pay-confirm': {
      const q = payQuote();
      if (!q || q.short > 0) break;
      const a = app.account;
      a.points -= q.pointsUsed;
      if (app.pay.method === 'wallet') a.wallet = +(a.wallet - q.remaining).toFixed(2);
      const earned = a.member ? Math.floor(q.remaining) * EARN_PER_RM : 0;
      a.points += earned;
      const r: Receipt = { at: sim.t, fee: q.fee.rm, pointsUsed: q.pointsUsed, pointsRM: q.pointsRM, charged: q.remaining, method: app.pay.method, earned };
      persistProfile();
      sim.driverPay(q.v.i);
      q.st.receipt = r;
      app.pay.done = r;
      openSheet('paid');
      const host = $('#sheet-body');
      animate(host.querySelector('.paid-check'), { transform: ['scale(0.4)', 'scale(1)'], opacity: [0, 1] }, { spring: { stiffness: 380, damping: 18 } });
      const tick = host.querySelector('.pc-tick') as SVGPathElement | null;
      if (tick) {
        tick.style.strokeDasharray = '80';
        animate(tick, { strokeDashoffset: [80, 0] }, { duration: 0.45, delay: 0.2, ease: [0.4, 0, 0.2, 1] });
      }
      break;
    }
    case 'topup':
      app.pay.back = false;
      openSheet('topup');
      break;
    case 'topup-from-pay':
      app.pay.back = true;
      openSheet('topup');
      break;
    case 'top-amt':
      app.pay.topAmt = Number(el.dataset.v);
      renderSheet();
      break;
    case 'top-from':
      app.pay.topFrom = el.dataset.v as 'debit' | 'credit';
      renderSheet();
      break;
    case 'topup-confirm': {
      const before = app.account.wallet;
      app.account.wallet = +(app.account.wallet + app.pay.topAmt).toFixed(2);
      persistProfile();
      toast(`Wallet topped up: ${rm(app.pay.topAmt)}`);
      if (app.pay.back) {
        app.pay.back = false;
        app.pay.method = 'wallet';
        openSheet('pay');
      } else closeSheet();
      requestAnimationFrame(() => {
        for (const b of $$('.wallet .w-item:first-child b')) tweenNumber(before, app.account.wallet, 0.7, (x) => (b.textContent = rm(x)));
      });
      break;
    }
    case 'sheet-close':
      closeSheet();
      break;
    case 'new-trip':
      app.myId = -1;
      app.resId = '';
      goTab('park');
      break;
    case 'res-car':
      app.resDraft.plate = el.dataset.plate || '';
      break;
    case 'reserve-type':
      app.resDraft.type = el.dataset.type as ResType;
      app.resDraft.touched = true;
      app.resDraft.elig = false;
      app.resMsg = '';
      goTab('reserve');
      break;
    case 'res-type':
      app.resDraft.type = el.dataset.type as ResType;
      app.resDraft.touched = true;
      app.resDraft.elig = false;
      app.resMsg = '';
      break;
    case 'res-in':
      app.resDraft.inMin = Number(el.dataset.v);
      break;
    case 'res-dur':
      app.resDraft.dur = Number(el.dataset.v);
      break;
    case 'res-go': {
      const r = myRes();
      app.plan.eta = Math.max(0, Math.round(((r?.windowStart ?? sim.t) - sim.t) / 60));
      const st = r ? app.stays.find((x) => x.vid === r.vehicle) : undefined;
      if (st) app.plan.plate = st.plate;
      openSheet('plan');
      break;
    }
    case 'res-cancel': {
      const r = myRes();
      if (r) {
        app.resMsg = sim.cancelReservation(r.id);
        app.resErr = false;
        if (app.myId === r.vehicle) app.myId = -1;
        app.stays = app.stays.filter((x) => x.vid !== r.vehicle);
      }
      break;
    }
    case 'assist':
      openSheet('assist');
      break;
    case 'assist-eta':
      app.plan.eta = Number(el.dataset.v);
      renderSheet();
      break;
    case 'assist-send': {
      const ok = (document.getElementById('assist-permit') as HTMLInputElement | null)?.checked;
      if (!ok) {
        const e = document.getElementById('assist-err');
        if (e) {
          e.hidden = false;
          animate(e, { transform: ['translateX(-6px)', 'translateX(6px)', 'translateX(-3px)', 'translateX(0px)'] }, { duration: 0.3 });
        }
        break;
      }
      const req = sim.requestAssistance(Math.max(5, app.plan.eta || 10));
      app.assistMsg = `Request ${req.id} sent. Staff will meet you at the entrance in about ${req.etaMin} min and check your permit.`;
      closeSheet();
      toast('Help request sent');
      break;
    }
    case 'profile':
      openSheet('profile');
      break;
    case 'restart':
      app.sim = newSim();
      seedParkedCar();
      app.myId = -1;
      app.resId = '';
      app.resMsg = '';
      app.assistMsg = '';
      app.boardVals = [-1, -1, -1];
      closeSheet();
      closePush(false);
      goTab('park');
      toast('Demo day restarted at 14:08');
      break;
    case 'scrim':
      closeSheet();
      break;
  }
  app.dirty = true;
}

function resVerified(type: ResType, car: CarProfile | null): string {
  if (type === 'member') return app.account.member ? `${app.account.tier} member ${app.account.memberNo}` : '';
  if (type === 'ev') return car && car.ev ? `${car.plate} is registered as electric` : '';
  return car && car.family ? `${car.plate} has a family pass` : '';
}

function submitReservation() {
  const sim = app.sim;
  const d = app.resDraft;
  const car = d.plate ? carOf(d.plate) : null;
  if (!car) {
    app.resMsg = 'Add a car first. Every booking is tied to a number plate.';
    app.resErr = true;
    renderReserve();
    return;
  }
  if (d.type === 'member' && !app.account.member) {
    app.resMsg = 'Member bays are for KL East Mall Rewards members. Join in your account to book one.';
    app.resErr = true;
    renderReserve();
    return;
  }
  const box = document.getElementById('res-elig') as HTMLInputElement | null;
  d.elig = !!resVerified(d.type, car) || (!!box && box.checked);
  if (!d.elig) {
    app.resMsg = 'Confirm that you are eligible for this bay type first. Staff may check at the bay.';
    app.resErr = true;
    app.dirty = true;
    renderReserve();
    const n = document.querySelector('#res-form .note');
    animate(n, { transform: ['translateX(-6px)', 'translateX(6px)', 'translateX(-3px)', 'translateX(0px)'] }, { duration: 0.3 });
    return;
  }
  const res = sim.createReservation(d.type, d.inMin, d.dur);
  if (!res.ok) {
    app.resMsg = res.error;
    app.resErr = true;
  } else {
    app.resId = res.r.id;
    app.resMsg = '';
    app.resErr = false;
    if (d.type === 'ev' && !car.ev) car.ev = true;
    if (d.type === 'family' && !car.family) car.family = true;
    persistProfile();
    app.stays.push({ plate: car.plate, vid: res.r.vehicle, demo: false, receipt: null });
    if (!me() || ['left', 'cancelled', 'parked', 'paid'].includes(phase())) app.myId = res.r.vehicle;
    toast(`${RES_LABEL[d.type]} bay ${sim.L.bays[res.r.bay].id} held for ${car.plate}`);
  }
  app.dirty = true;
  renderReserve();
  const t = document.querySelector('#res-active .ticket');
  if (t) animate(t, { transform: ['scale(0.94)', 'scale(1)'], opacity: [0, 1] }, { spring: { stiffness: 420, damping: 26 } });
}

function bindEvents() {
  document.addEventListener('click', (e) => {
    const t = e.target as HTMLElement;
    const tab = t.closest('#tabbar [data-tab]') as HTMLElement | null;
    if (tab) {
      goTab(tab.dataset.tab as Tab);
      return;
    }
    const a = t.closest('[data-act]') as HTMLElement | null;
    if (a && !(a as HTMLButtonElement).disabled) act(a);
  });
  document.addEventListener('submit', (e) => {
    const f = e.target as HTMLElement;
    if (f.id === 'res-form-el') {
      e.preventDefault();
      submitReservation();
    }
  });
  document.addEventListener('change', (e) => {
    const t = e.target as HTMLInputElement;
    if (t.id === 'res-elig') {
      app.resDraft.elig = t.checked;
      if (t.checked && app.resErr) app.resMsg = '';
    }
  });
  document.addEventListener('input', (e) => {
    const t = e.target as HTMLInputElement;
    if (t.id === 'new-plate') {
      const err = document.getElementById('addcar-err');
      if (err) err.hidden = true;
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.target as HTMLElement).id === 'new-plate') {
      e.preventDefault();
      if (addCarFromInput()) renderSheet();
      return;
    }
    if (e.key === 'Escape') {
      if (app.sheet) closeSheet();
      else if (app.screen === 'guide') closePush(true);
    }
    const t = e.target as HTMLElement;
    if (t.getAttribute('role') === 'tab' && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
      const tabs = $$('#tabbar [role="tab"]');
      const i = tabs.indexOf(t);
      const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      n.click();
      n.focus();
    }
  });
  $('#scrim').addEventListener('click', () => closeSheet());
  bindSheetDrag();
}

// ---------------------------------------------------------------- loop
function onTick() {
  const v = me();
  if (!v) return;
  if (v.parkT >= 0 && !app.parkedShown && v.state === 'parked') {
    app.parkedShown = true;
    closeSheet();
    showParked();
  }
  if (v.notice && v.notice !== app.lastNotice) {
    app.lastNotice = v.notice;
    if (/^Updated route/.test(v.notice) && v.parkT < 0) toast(v.notice.replace(/\.$/, ''));
  }
  const r = myRes();
  if (r && r.status === 'expired' && app.resMsg.indexOf('expired') < 0) {
    app.resMsg = `${r.id} expired: you weren’t at the bay within 10 minutes of your window, so it went back to other drivers.`;
    app.resErr = true;
    toast('Your held bay was released');
  }
}

function renderAll() {
  renderHeader();
  renderTabs();
  if (!app.screen) {
    if (app.tab === 'park') renderPark();
    else if (app.tab === 'reserve') renderReserve();
    else renderCar();
  } else if (app.screen === 'guide') renderGuide();
  renderSheet();
  app.dirty = false;
  app.lastUI = performance.now();
}

/** What the guidance map keeps in frame: the car, the target zone on this level, and the lift. */
function guideFocus(v: Vehicle, floor: number, zone: ZoneId | null, alpha: number): number[][] | null {
  const pts: number[][] = [];
  const p = vehiclePose(app.sim, v, alpha);
  if (p && p.floor === floor && v.state !== 'pending') pts.push([p.x, p.z]);
  const tg = target(v);
  if (tg && tg.bay && tg.floor === floor) pts.push([tg.bay.x, tg.bay.z]);
  else if (zone && (!tg || tg.floor === floor)) {
    const x0 = ZONE_X0[zone], x1 = x0 + ZONE_COUNTS[zone] * BAY_W;
    pts.push([x0, 2], [x1, 16]);
  }
  if (!pts.length) return null;
  if (pts.length === 1) pts.push([pts[0][0] + 6, pts[0][1] + 4], [pts[0][0] - 6, pts[0][1] - 4]);
  return pts;
}

function frame(now: number) {
  const sim = app.sim;
  const dt = app.lastFrame ? Math.min(0.25, (now - app.lastFrame) / 1000) : 0;
  app.lastFrame = now;
  if (sim.t < sim.tEnd) {
    app.acc += dt * app.profile.pace;
    let n = 0;
    while (app.acc >= 1 && n < 40) {
      sim.step();
      app.acc -= 1;
      n++;
    }
    if (n) onTick();
  }
  const alpha = Math.max(0, Math.min(1, app.acc));
  if (app.dirty || now - app.lastUI > 250) renderAll();
  const v = me();
  if (app.screen === 'guide' && v && guideMap) {
    const g = guidanceFor(v);
    const floor = v.state === 'pending' || v.state === 'queued' ? (v.state === 'queued' ? 0 : g.floor) : sim.vehicleFloor(v);
    const zone = g.zone && v.parkT < 0 ? { floor: g.floor, zone: g.zone } : null;
    guideMap.update(sim, { floor, me: v, route: true, zone, walk: null, alpha, focus: guideFocus(v, floor, zone ? zone.zone : null, alpha) });
  }
  const cv = vOf(stayOf(app.carSel));
  if (!app.screen && app.tab === 'car' && cv && cv.bay >= 0 && cv.state === 'parked' && carMap && !$('#car-mapwrap').hidden) {
    const b = sim.L.bays[cv.bay];
    const lift = DEST_BY_ID[cv.dest].lift;
    carMap.update(sim, { floor: b.floor, me: cv, route: false, zone: null, walk: { bay: cv.bay, lift }, alpha, focus: walkPath(sim.L, cv.bay, lift) });
  }
  requestAnimationFrame(frame);
}

function init() {
  app.sim = newSim();
  seedParkedCar();
  bindEvents();
  const eng = document.getElementById('engine');
  if (eng) eng.textContent = motionEngine() === 'motion' ? 'Motion' : 'Web Animations';
  renderAll();
  app.booted = true;
  requestAnimationFrame(frame);
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
