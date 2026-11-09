// ParkFlow driver prototype: reserve shared Priority Zone access, show a demo QR,
// and inspect availability. Counts and forecasts are illustrative, not live site data.
import { esc, dotMatrix } from '../ui/dom';

type DriverPage = 'home' | 'reserve' | 'confirmed' | 'bookings' | 'zone' | 'profile';
type DriverBayStatus = 'available' | 'reserved' | 'occupied';
interface DriverBay { id: string; floor: number; status: DriverBayStatus; booked: boolean; }
interface DriverBooking { id: string; mall: string; date: string; time: string; plate: string; bayId: string; status: 'confirmed' | 'cancelled'; fee: number; }
interface DriverData { plate: string; bookings: DriverBooking[]; pools: Record<string, DriverBay[]>; }
const DRV_MALLS: Record<string, string> = { klgcc: 'KLGCC Mall', kleast: 'KL East Mall', elmina: 'Elmina Lakeside Mall' };
const DRV_KEY = 'parkflow.priority.reference.v1';
const DRV_ICONS: Record<string, string> = {
  back: '<path d="m14 6-6 6 6 6M8 12h12"/>',
  home: '<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18"/>',
  ticket: '<path d="M3 6h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4Z"/><path d="M14 6v2M14 11v2M14 16v2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  car: '<path d="m5 8 2-5h10l2 5M3 8h18v10H3ZM6 18v3M18 18v3M6 12h2M16 12h2"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  walk: '<circle cx="13" cy="4" r="2"/><path d="m7 22 3-7 3 3v4M10 15l1-5 4 3 3 1M8 9l3-1"/>'
};
function driverIcon(name: string, size = 22): string {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${DRV_ICONS[name] || DRV_ICONS.info}</svg>`;
}
function driverSeedPool(): DriverBay[] {
  const capacities = [34, 33, 33], occupied = [27, 24, 21], reserved = [2, 2, 2];
  return capacities.flatMap((capacity, floor) => Array.from({ length: capacity }, (_, index) => ({
    id: `B${floor + 1}-P${String(index + 1).padStart(2, '0')}`, floor,
    status: (index < occupied[floor] ? 'occupied' : index < occupied[floor] + reserved[floor] ? 'reserved' : 'available') as DriverBayStatus,
    booked: index < [14, 12, 10][floor]
  })));
}
function driverLoad(): DriverData {
  const fallback: DriverData = { plate: 'WXY 8812', bookings: [], pools: {} };
  try {
    const raw = JSON.parse(localStorage.getItem(DRV_KEY) || 'null');
    if (!raw || typeof raw !== 'object') return fallback;
    const bookings = Array.isArray(raw.bookings) ? raw.bookings.filter((b: DriverBooking) => b && typeof b.id === 'string' && DRV_MALLS[b.mall] && typeof b.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(b.date) && Number.isFinite(Date.parse(b.date + 'T12:00:00+08:00')) && typeof b.time === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(b.time) && typeof b.plate === 'string' && typeof b.bayId === 'string' && ['confirmed', 'cancelled'].includes(b.status)) : [];
    const pools: Record<string, DriverBay[]> = {};
    for (const mall of Object.keys(DRV_MALLS)) {
      const pool = raw.pools?.[mall];
      const expected = driverSeedPool();
      if (Array.isArray(pool) && pool.length === expected.length && pool.every((bay: DriverBay, i: number) => bay && bay.id === expected[i].id && bay.floor === expected[i].floor && ['available', 'reserved', 'occupied'].includes(bay.status) && typeof bay.booked === 'boolean')) pools[mall] = pool;
    }
    // Reconcile saved commitments against the persisted pool; restore the same hold on reload.
    for (const booking of bookings.filter((b: DriverBooking) => b.status === 'confirmed')) {
      if (!pools[booking.mall]) pools[booking.mall] = driverSeedPool();
      const bay = pools[booking.mall].find((b) => b.id === booking.bayId);
      if (!bay || bay.status === 'occupied') booking.status = 'cancelled';
      else bay.status = 'reserved';
    }
    return { plate: typeof raw.plate === 'string' && /^[A-Z0-9 ]{2,12}$/.test(raw.plate) ? raw.plate : fallback.plate, bookings, pools };
  } catch { return fallback; }
}
function driverToday(): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kuala_Lumpur', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  return `${parts.find((p) => p.type === 'year')!.value}-${parts.find((p) => p.type === 'month')!.value}-${parts.find((p) => p.type === 'day')!.value}`;
}
function driverDefaultDate(): string {
  const date = new Date(`${driverToday()}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + ((6 - date.getUTCDay() + 7) % 7 || 7));
  return date.toISOString().slice(0, 10);
}
const DRV_APP = { page: 'home' as DriverPage, mall: 'klgcc', date: driverDefaultDate(), time: '18:45', data: driverLoad(), selected: '', error: '', notice: '' };
function driverPool(mall = DRV_APP.mall): DriverBay[] {
  return DRV_APP.data.pools[mall] || (DRV_APP.data.pools[mall] = driverSeedPool());
}
function driverCounts(pool = driverPool()) {
  return { total: pool.length, available: pool.filter((b) => b.status === 'available').length, reserved: pool.filter((b) => b.status === 'reserved').length, occupied: pool.filter((b) => b.status === 'occupied').length, bookedParked: pool.filter((b) => b.status === 'occupied' && b.booked).length, walkIns: pool.filter((b) => b.status === 'occupied' && !b.booked).length };
}
function driverSave() { try { localStorage.setItem(DRV_KEY, JSON.stringify(DRV_APP.data)); } catch { DRV_APP.notice = 'Storage is unavailable. Keep this page open to retain your demo booking.'; } }
function driverDateLabel(date: string): string { return new Date(`${date}T12:00:00+08:00`).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Asia/Kuala_Lumpur' }); }
function driverTimeLabel(time: string): string { const [h, m] = time.split(':').map(Number); return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; }
function driverGo(page: DriverPage) { DRV_APP.page = page; DRV_APP.error = ''; driverRender(); document.getElementById('driver-scroll')!.scrollTop = 0; }
function driverSelected(): DriverBooking | undefined { return DRV_APP.data.bookings.find((b) => b.id === DRV_APP.selected); }

// Standards-compliant QR Model 2, version 4-L, byte mode, mask 0.
// Payload is a demo booking reference, never a real gate credential or payment token.
function driverQrMatrix(payload: string): boolean[][] {
  const bytes = Array.from(new TextEncoder().encode(payload));
  if (bytes.length > 78) throw new Error('Demo QR payload is too long.');
  const bits: number[] = [];
  const append = (value: number, count: number) => { for (let i = count - 1; i >= 0; i--) bits.push((value >>> i) & 1); };
  append(4, 4); append(bytes.length, 8); bytes.forEach((b) => append(b, 8));
  append(0, Math.min(4, 640 - bits.length)); while (bits.length % 8) bits.push(0);
  const data: number[] = []; for (let i = 0; i < bits.length; i += 8) data.push(bits.slice(i, i + 8).reduce((a, b) => a * 2 + b, 0));
  for (let pad = 0; data.length < 80; pad++) data.push(pad % 2 ? 0x11 : 0xec);
  const mul = (a: number, b: number): number => { let r = 0; for (let i = 0; i < 8; i++) { if (b & 1) r ^= a; a = (a << 1) ^ ((a & 0x80) ? 0x11d : 0); b >>>= 1; } return r; };
  let gen = [1], root = 1;
  for (let i = 0; i < 20; i++) { const next = Array(gen.length + 1).fill(0); gen.forEach((v, j) => { next[j] ^= v; next[j + 1] ^= mul(v, root); }); gen = next; root = mul(root, 2); }
  const remainder = data.concat(Array(20).fill(0));
  for (let i = 0; i < 80; i++) { const factor = remainder[i]; for (let j = 0; j < gen.length; j++) remainder[i + j] ^= mul(gen[j], factor); }
  const words = data.concat(remainder.slice(80)), size = 33;
  const matrix = Array.from({ length: size }, () => Array(size).fill(false));
  const fixed = Array.from({ length: size }, () => Array(size).fill(false));
  const put = (x: number, y: number, value: boolean) => { if (x >= 0 && y >= 0 && x < size && y < size) { matrix[y][x] = value; fixed[y][x] = true; } };
  for (const [cx, cy] of [[3, 3], [size - 4, 3], [3, size - 4]]) for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) { const distance = Math.max(Math.abs(dx), Math.abs(dy)); put(cx + dx, cy + dy, distance !== 2 && distance !== 4); }
  for (let i = 8; i < size - 8; i++) { put(6, i, i % 2 === 0); put(i, 6, i % 2 === 0); }
  for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) put(26 + dx, 26 + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
  let rem = 8; for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  const format = ((8 << 10) | rem) ^ 0x5412, bit = (i: number) => ((format >>> i) & 1) !== 0;
  for (let i = 0; i <= 5; i++) put(8, i, bit(i)); put(8, 7, bit(6)); put(8, 8, bit(7)); put(7, 8, bit(8));
  for (let i = 9; i < 15; i++) put(14 - i, 8, bit(i));
  for (let i = 0; i < 8; i++) put(size - 1 - i, 8, bit(i));
  for (let i = 8; i < 15; i++) put(8, size - 15 + i, bit(i)); put(8, size - 8, true);
  let index = 0;
  for (let right = size - 1; right >= 1; right -= 2) { if (right === 6) right = 5; for (let vertical = 0; vertical < size; vertical++) { const y = ((right + 1) & 2) === 0 ? size - 1 - vertical : vertical; for (let j = 0; j < 2; j++) { const x = right - j; if (fixed[y][x]) continue; const value = index < words.length * 8 && ((words[index >>> 3] >>> (7 - (index & 7))) & 1) !== 0; matrix[y][x] = value !== ((x + y) % 2 === 0); index++; } } }
  return matrix;
}
function driverQr(booking: DriverBooking): string {
  const payload = `PF|${booking.id}|${booking.mall}|${booking.date}|${booking.time}|${booking.plate}`;
  const matrix = driverQrMatrix(payload);
  const path = matrix.flatMap((row, y) => row.map((dark, x) => dark ? `M${x} ${y}h1v1h-1z` : '')).join('');
  return `<svg class="booking-qr" viewBox="-4 -4 41 41" role="img" aria-label="Demo booking QR for ${esc(booking.id)}" shape-rendering="crispEdges"><rect x="-4" y="-4" width="41" height="41" fill="white"/><path d="${path}" fill="#111"/></svg>`;
}
function driverBook(): boolean {
  DRV_APP.error = '';
  if (!DRV_MALLS[DRV_APP.mall] || !/^\d{4}-\d{2}-\d{2}$/.test(DRV_APP.date) || !/^\d{2}:\d{2}$/.test(DRV_APP.time)) { DRV_APP.error = 'Choose a mall, date and arrival time.'; return false; }
  const when = new Date(`${DRV_APP.date}T${DRV_APP.time}:00+08:00`);
  if (!Number.isFinite(when.getTime()) || when.getTime() <= Date.now()) { DRV_APP.error = 'Choose an arrival time in the future.'; return false; }
  if (!/^[A-Z0-9 ]{2,12}$/.test(DRV_APP.data.plate)) { DRV_APP.error = 'Add a valid vehicle plate in Profile first.'; return false; }
  const duplicate = DRV_APP.data.bookings.find((b) => b.status === 'confirmed' && b.mall === DRV_APP.mall && b.date === DRV_APP.date && b.time === DRV_APP.time && b.plate === DRV_APP.data.plate);
  if (duplicate) { DRV_APP.selected = duplicate.id; return true; }
  const bay = driverPool().find((b) => b.status === 'available');
  if (!bay) { DRV_APP.error = 'Priority Zone is fully reserved in this demo. Choose another mall or release an existing booking.'; return false; }
  const id = `PF-${Date.now().toString(36).toUpperCase()}-${DRV_APP.data.bookings.length + 1}`;
  const booking: DriverBooking = { id, mall: DRV_APP.mall, date: DRV_APP.date, time: DRV_APP.time, plate: DRV_APP.data.plate, bayId: bay.id, status: 'confirmed', fee: 5 };
  bay.status = 'reserved'; bay.booked = true; DRV_APP.data.bookings.unshift(booking); DRV_APP.selected = id; driverSave(); return true;
}
function driverCancel(id: string) {
  const booking = DRV_APP.data.bookings.find((b) => b.id === id && b.status === 'confirmed'); if (!booking) return;
  const bay = driverPool(booking.mall).find((b) => b.id === booking.bayId); if (bay?.status === 'reserved') { bay.status = 'available'; bay.booked = false; }
  booking.status = 'cancelled'; driverSave(); driverRender();
}
function driverHeader(title: string, back = 'home'): string { return `<header class="driver-header"><button class="icon-btn" data-driver="go" data-page="${back}" aria-label="Back">${driverIcon('back')}</button><h1>${title}</h1><button class="icon-btn" data-driver="go" data-page="profile" aria-label="Profile">${driverIcon('user', 20)}</button></header>`; }
function driverForm(): string {
  return `${driverHeader('Reserve Parking')}<div class="page-content"><form id="priority-booking-form"><label class="field"><span>Mall</span><select id="booking-mall">${Object.entries(DRV_MALLS).map(([id, name]) => `<option value="${id}" ${DRV_APP.mall === id ? 'selected' : ''}>${name}</option>`).join('')}</select></label><label class="field"><span>Date</span><input id="booking-date" type="date" min="${driverToday()}" value="${DRV_APP.date}" required></label><label class="field"><span>Time</span><input id="booking-time" type="time" value="${DRV_APP.time}" required></label>
    <div class="zone-offer"><span>${driverIcon('car', 30)}</span><div><b>Priority Zone</b><p>100 shared bays<br>Near the mall lifts</p></div>${driverIcon('info', 18)}</div>
    <div class="vehicle-line">${driverIcon('car', 17)}<span>${esc(DRV_APP.data.plate)}</span><button type="button" class="text-btn" data-driver="go" data-page="profile">Change</button></div><div class="fee-line"><span>Booking Fee</span><b>RM5.00</b></div><p class="fine">Proposed fee, additional to normal parking charges.</p>${DRV_APP.error ? `<p class="error" role="alert">${esc(DRV_APP.error)}</p>` : ''}<button class="button button-red" type="submit">Confirm Booking</button><p class="fine center">Demo booking only. No payment is taken.</p></form></div>`;
}
function driverConfirmation(): string {
  const booking = driverSelected(); if (!booking) return `${driverHeader('My Booking')}<div class="empty">No booking selected.</div>`;
  const active = booking.status === 'confirmed';
  return `${driverHeader('My Booking', 'bookings')}<div class="page-content confirmation"><div class="confirmation-mark ${active ? '' : 'cancelled'}">${driverIcon(active ? 'check' : 'info', 48)}</div><h2>${active ? 'Booking Confirmed!' : 'Booking Cancelled'}</h2><div class="booking-facts"><p>${driverIcon('pin')}<b>${DRV_MALLS[booking.mall]}</b></p><p>${driverIcon('calendar')}<b>${driverDateLabel(booking.date)}, ${driverTimeLabel(booking.time)}</b></p><p>${driverIcon('car')}<b>Priority Zone Access</b></p><small>${esc(booking.plate)} · ${esc(booking.id)}</small></div>${active ? `${driverQr(booking)}<p class="qr-caption">Show this QR at the zone entrance ${driverIcon('info', 15)}</p><p class="fine center">Demo entry pass. No live gate connection.</p>` : ''}<button class="button button-red" data-driver="view-zone" data-mall="${booking.mall}">View Priority Zone</button>${active ? `<button class="text-btn cancel-booking" data-driver="cancel" data-id="${esc(booking.id)}">Cancel booking</button>` : ''}</div>`;
}
function driverBoard(): string {
  const pool = driverPool(), counts = driverCounts(pool);
  const floors = [0, 1, 2].map((floor) => { const bays = pool.filter((b) => b.floor === floor), c = driverCounts(bays); return `<div class="status-row"><span class="floor-plate">B${floor + 1}</span><div class="available-count">${dotMatrix(String(c.available), 4, 3.7, `${c.available} available`)}<span><i></i>Available</span></div><div class="status-stat reserved"><span><i></i>Reserved</span><b>${c.reserved}</b></div><div class="status-stat occupied"><span><i></i>Occupied</span><b>${c.occupied}</b></div></div>`; }).join('');
  const free = pool.filter((b) => b.status === 'available');
  return `<section class="status-board" aria-label="Priority Zone availability by level"><div class="status-heading"><b>Parking available</b><span><strong>${counts.available}</strong> available<small>${counts.total} total priority bays</small></span></div>${floors}<div class="status-footer">Priority Zone only · Simulated availability</div></section><details class="available-details"><summary>See available bay numbers <span>${free.length}</span></summary><div class="available-list">${free.length ? free.map((b) => `<span>${b.id}</span>`).join('') : '<p>No bays available.</p>'}</div></details>`;
}
function driverForecast(): string {
  const c = driverCounts(), values = [c.occupied, Math.min(100, c.occupied + 4), Math.min(100, c.occupied + 9), Math.min(100, c.occupied + 14), Math.min(100, c.occupied + 17), Math.min(100, c.occupied + 20), Math.min(100, c.occupied + 22)];
  const points = values.map((value, i) => `${34 + i * 41},${134 - value * 1.08}`).join(' '), area = `34,134 ${points} 280,134`;
  return `<section class="forecast-card"><h3>Next 3 Hours <span>(Forecast)</span></h3><svg viewBox="0 0 310 164" role="img" aria-label="Illustrative three-hour occupancy forecast, bounded by 100 bays"><defs><linearGradient id="priority-forecast-fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#2995d8" stop-opacity=".25"/><stop offset="1" stop-color="#2995d8" stop-opacity=".02"/></linearGradient></defs>${[0, 50, 100].map((n) => `<line x1="34" y1="${134 - n * 1.08}" x2="280" y2="${134 - n * 1.08}" stroke="#eceef2"/><text x="25" y="${138 - n * 1.08}" text-anchor="end">${n}</text>`).join('')}<polygon points="${area}" fill="url(#priority-forecast-fill)"/><polyline points="${points}" fill="none" stroke="#258bd1" stroke-width="2.5"/>${values.map((v, i) => `<circle cx="${34 + i * 41}" cy="${134 - v * 1.08}" r="3.8" fill="#258bd1"/>`).join('')}<text x="34" y="155">Now</text><text x="116" y="155" text-anchor="middle">+1h</text><text x="198" y="155" text-anchor="middle">+2h</text><text x="280" y="155" text-anchor="end">+3h</text></svg><p class="fine">Illustrative demo forecast. No live model is connected.</p></section>`;
}
function driverZone(): string {
  const c = driverCounts(), first = c.occupied / c.total * 100, second = (c.occupied + c.reserved) / c.total * 100;
  return `${driverHeader('Priority Zone')}<div class="page-content zone-content"><div class="mall-label">${DRV_MALLS[DRV_APP.mall]}<span class="demo-pill">Demo data</span></div><div class="occupancy-ring" style="--ring:conic-gradient(#f05252 0 ${first}%,#f0c543 ${first}% ${second}%,#82b7ed ${second}% 100%)"><div><b>${c.occupied}<span> / ${c.total}</span></b><small>Bays Occupied</small></div></div><div class="ring-key"><span class="occupied"><i></i>Occupied</span><span class="reserved"><i></i>Reserved</span><span class="available"><i></i>Available</span></div><div class="metric-grid"><div>${driverIcon('calendar', 29)}<span>Bookings</span><b>${c.bookedParked}</b><small>parked · ${c.reserved} reserved</small></div><div>${driverIcon('walk', 29)}<span>Walk-ins</span><b>${c.walkIns}</b><small>parked in the zone</small></div></div>${driverBoard()}${driverForecast()}</div>`;
}
function driverBookings(): string {
  return `${driverHeader('My Bookings')}<div class="page-content">${DRV_APP.data.bookings.length ? DRV_APP.data.bookings.map((booking) => `<button class="booking-card" data-driver="open-booking" data-id="${esc(booking.id)}"><span class="booking-card-icon">${driverIcon('ticket', 26)}</span><span><b>${DRV_MALLS[booking.mall]}</b><small>${driverDateLabel(booking.date)} · ${driverTimeLabel(booking.time)}</small><small>${esc(booking.plate)} · Priority Zone</small><em class="${booking.status}">${booking.status === 'confirmed' ? 'Confirmed' : 'Cancelled'}</em></span>${driverIcon('chevron', 18)}</button>`).join('') : `<div class="empty">${driverIcon('ticket', 40)}<h2>No bookings yet</h2><p>Reserve Priority Zone access for your next visit.</p><button class="button button-red" data-driver="go" data-page="reserve">Reserve Parking</button></div>`}</div>`;
}
function driverProfile(): string { return `${driverHeader('Profile')}<div class="page-content"><div class="profile-intro">${driverIcon('user', 36)}<h2>Your vehicle</h2><p>Use the same plate when you arrive.</p></div><form id="driver-profile-form"><label class="field"><span>Vehicle plate</span><input id="driver-plate" maxlength="12" value="${esc(DRV_APP.data.plate)}" autocomplete="off" required></label>${DRV_APP.error ? `<p class="error" role="alert">${esc(DRV_APP.error)}</p>` : ''}<button class="button button-red" type="submit">Save vehicle</button></form><p class="fine">Prototype profile stored on this device. Existing bookings keep their original plate.</p><a class="operator-link" data-site="command" href="command.html">Open operator dashboard ${driverIcon('chevron', 16)}</a></div>`; }
function driverHome(): string { return `<section class="home-hero"><div class="hero-top"><a data-site="home" href="index.html" aria-label="ParkFlow project home">${driverIcon('back')}</a><span>PROTOTYPE</span></div><div class="hero-copy"><p class="hero-mall">KLGCC MALL</p><h1>park<span>flow</span><i>//</i></h1><p>Reserve. Park. Shop.</p></div><div class="hero-actions"><button class="button button-red" data-driver="go" data-page="reserve">${driverIcon('calendar')} Reserve Parking</button><button class="button button-white" data-driver="go" data-page="bookings">${driverIcon('ticket')} My Bookings</button><button class="hero-zone" data-driver="view-zone" data-mall="klgcc">Check Priority Zone availability ${driverIcon('chevron', 16)}</button></div></section>`; }
function driverRender() {
  const pages: Record<DriverPage, () => string> = { home: driverHome, reserve: driverForm, confirmed: driverConfirmation, bookings: driverBookings, zone: driverZone, profile: driverProfile };
  const content = document.getElementById('driver-scroll')!; content.classList.toggle('is-home', DRV_APP.page === 'home'); content.innerHTML = pages[DRV_APP.page]();
  const active = DRV_APP.page === 'reserve' || DRV_APP.page === 'confirmed' ? 'bookings' : DRV_APP.page;
  document.querySelectorAll<HTMLButtonElement>('[data-driver-tab]').forEach((button) => { const selected = button.dataset.driverTab === active; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; });
  document.getElementById('driver-notice')!.textContent = DRV_APP.notice;
  document.getElementById('driver-notice')!.hidden = !DRV_APP.notice;
}
function driverInit() {
  driverPool(); driverRender();
  document.addEventListener('click', (event) => {
    const target = event.target as HTMLElement;
    const tab = target.closest<HTMLButtonElement>('[data-driver-tab]'); if (tab) { driverGo(tab.dataset.driverTab as DriverPage); return; }
    const button = target.closest<HTMLElement>('[data-driver]'); if (!button) return;
    const action = button.dataset.driver;
    if (action === 'go') driverGo(button.dataset.page as DriverPage);
    else if (action === 'view-zone') { if (button.dataset.mall && DRV_MALLS[button.dataset.mall]) DRV_APP.mall = button.dataset.mall; driverGo('zone'); }
    else if (action === 'open-booking') { DRV_APP.selected = button.dataset.id || ''; driverGo('confirmed'); }
    else if (action === 'cancel') driverCancel(button.dataset.id || '');
  });
  document.addEventListener('change', (event) => { const input = event.target as HTMLInputElement; if (input.id === 'booking-mall') DRV_APP.mall = input.value; if (input.id === 'booking-date') DRV_APP.date = input.value; if (input.id === 'booking-time') DRV_APP.time = input.value; });
  document.addEventListener('submit', (event) => {
    const form = event.target as HTMLFormElement;
    if (form.id === 'priority-booking-form') { event.preventDefault(); DRV_APP.mall = (document.getElementById('booking-mall') as HTMLSelectElement).value; DRV_APP.date = (document.getElementById('booking-date') as HTMLInputElement).value; DRV_APP.time = (document.getElementById('booking-time') as HTMLInputElement).value; if (driverBook()) driverGo('confirmed'); else driverRender(); }
    if (form.id === 'driver-profile-form') { event.preventDefault(); const plate = (document.getElementById('driver-plate') as HTMLInputElement).value.toUpperCase().replace(/\s+/g, ' ').trim(); if (!/^[A-Z0-9 ]{2,12}$/.test(plate)) { DRV_APP.error = 'Use letters and numbers, for example WXY 8812.'; driverRender(); } else { DRV_APP.data.plate = plate; driverSave(); DRV_APP.notice = 'Vehicle saved.'; driverGo('reserve'); setTimeout(() => { DRV_APP.notice = ''; const notice = document.getElementById('driver-notice'); if (notice) notice.hidden = true; }, 2500); } }
  });
  document.getElementById('driver-tabs')!.addEventListener('keydown', (event) => { if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return; const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>('[data-driver-tab]')); const index = tabs.indexOf(event.target as HTMLButtonElement); if (index < 0) return; event.preventDefault(); const next = tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; next.click(); next.focus(); });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', driverInit); else driverInit();
