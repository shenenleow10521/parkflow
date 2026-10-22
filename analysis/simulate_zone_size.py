"""How big should the Priority Zone be, and does it have to be one block?

Reuses the day generator and the zone rules in simulate_pooling.py, and changes only the
zone size, the booking cap and the layout.

Size sweep
  Zone size: 2, 4, 6, 8, 10, 12, 15, 20 and 25% of a 1,300-bay car park (KL East Mall).
  Booking cap (most bookings at the same time): 10, 20 and 30% of the zone.
  Day types: busy, normal and stress, as in simulate_pooling.py.
  Rules compared on the same days: ParkFlow forecast rule, a VIP section the size of the
  cap, and the fixed rule with no safety bays (the best fixed rule in simulate_pooling.py).
  Walk-in demand grows with the zone, so every size is under the same pressure (the
  100-bay zone in simulate_pooling.py fills at peak). Booking requests stay at KL East's
  assumed level (60 busy, 25 normal, 100 stress), so bigger zones do not get more bookers.

Layout test
  The same total zone split into 2 or 4 pieces (for example the lift-side bays on each
  level). Each piece is run as its own zone with its own share of walk-ins, booking
  requests and cap. Running the pieces as one shared pool is the same calculation as one
  block in this model (it assumes the sign and app send drivers to the piece with space).

Choice rule, fixed before running
  Recommended size = the smallest zone where, for at least one cap, ParkFlow
    1) keeps at least 99.5% of bookings on the stress day, and
    2) accepts at least 90% of busy-day booking requests (otherwise a tiny zone "keeps"
       every booking by turning most of them away).
  Recommended cap at that size = the one meeting both tests with the fewest bay-hours
  held empty on a busy day.

Every figure is an average over the simulated days with a 95% range (bootstrap over days).
Usage:
  python simulate_zone_size.py size              (writes simulate_zone_size_results.txt)
  python simulate_zone_size.py layout 8 10 15    (zone sizes in % to test; appends results)
"""
import sys
from multiprocessing import Pool

import numpy as np

import simulate_pooling as sp

CAR_PARK = 1300
SIZES = [2, 4, 6, 8, 10, 12, 15, 20, 25]   # % of the car park
CAPS = [10, 20, 30]                         # % of the zone
POLICIES = [("forecast", "ParkFlow"), ("vip", "VIP section"), ("formula0", "Fixed rule")]
SCENS = ["busy", "normal", "stress"]
DAYS = 1000
CHUNK = 125
KEEP_MIN, ACCEPT_MIN = 0.995, 0.90
FIELDS = ["ok", "fail", "turned", "held", "occ", "accepted", "requests", "walkins"]


def zone_bays(pct):
    return round(CAR_PARK * pct / 100)


def cap_for(bays, pct):
    return max(1, round(bays * pct / 100))


def scenario(name, bays):
    s = dict(sp.SCEN[name])
    for k in ("base", "mid", "eve"):           # walk-in demand grows with the zone
        s[k] = s[k] * bays / 100
    return s


def run_piece(policy, pub, mem, bays, cap):
    sp.C, sp.QUOTA, sp.VIP_BAYS = bays, cap, cap
    st = {}
    ok, fail, turned, held, occ = sp.run(policy, pub, mem, stats=st)
    return np.array([ok, fail, turned, held, occ, st.get("accepted", 0), len(mem), len(pub)], float)


def task_size(args):
    scen, pct, cap_pct, d0, d1 = args
    bays = zone_bays(pct)
    cap = cap_for(bays, cap_pct)
    s = scenario(scen, bays)
    sf = s.get("stay_factor", 1.0)
    out = np.zeros((d1 - d0, len(POLICIES), len(FIELDS)))
    for i, day in enumerate(range(d0, d1)):
        pub, mem = sp.make_day(np.random.default_rng(1000 + day), s, sf)   # same days for every rule
        for j, (p, _) in enumerate(POLICIES):
            out[i, j] = run_piece(p, pub, mem, bays, cap)
    return args, out


def task_layout(args):
    scen, pct, cap_pct, pieces, d0, d1 = args
    bays = zone_bays(pct)
    cap = cap_for(bays, cap_pct)
    s = scenario(scen, bays)
    sf = s.get("stay_factor", 1.0)
    sizes = [bays // pieces + (1 if k < bays % pieces else 0) for k in range(pieces)]
    caps = [max(1, round(cap * b / bays)) for b in sizes]
    out = np.zeros((d1 - d0, len(FIELDS)))
    for i, day in enumerate(range(d0, d1)):
        pub, mem = sp.make_day(np.random.default_rng(1000 + day), s, sf)
        if pieces == 1:
            out[i] = run_piece("forecast", pub, mem, bays, cap)
            continue
        rng = np.random.default_rng(5000 + day)
        w = np.array(sizes) / bays
        pp = rng.choice(pieces, size=len(pub), p=w)        # each walk-in heads for one piece
        mp = rng.choice(pieces, size=len(mem), p=w)        # each booking is for one piece
        for k in range(pieces):
            r = run_piece("forecast", [x for x, q in zip(pub, pp) if q == k],
                          [x for x, q in zip(mem, mp) if q == k], sizes[k], caps[k])
            r[4] *= sizes[k] / bays                        # occupancy: weight by piece size
            out[i] += r
    return args, out


def chunks():
    return [(d, min(d + CHUNK, DAYS)) for d in range(0, DAYS, CHUNK)]


def summarise(a, rng):
    """a: days x fields. Means per day plus 95% bootstrap ranges for the ratios that matter."""
    idx = rng.integers(0, len(a), size=(2000, len(a)))
    tot = a.sum(0)
    boot = a[idx].sum(1)                                   # 2000 x fields
    def ratio(num, den):
        point = tot[num] / max(tot[den], 1e-9)
        b = boot[:, num] / np.maximum(boot[:, den], 1e-9)
        return point, np.percentile(b, 2.5), np.percentile(b, 97.5)
    okf = a[:, 0] + a[:, 1]
    tk = a[:, 0].sum() / max(okf.sum(), 1e-9)
    bk = a[idx, 0].sum(1) / np.maximum(okf[idx].sum(1), 1e-9)
    kept = (tk, np.percentile(bk, 2.5), np.percentile(bk, 97.5))
    held_b = a[idx, 3].mean(1)
    return dict(
        kept=kept,
        fail=a[:, 1].mean(),
        accept=ratio(5, 6),
        held=(a[:, 3].mean(), np.percentile(held_b, 2.5), np.percentile(held_b, 97.5)),
        redirected=ratio(2, 7),
        occ=a[:, 4].mean(),
    )


def fmt_pct(t, d=1):
    return f"{t[0]:.{d}%} ({t[1]:.{d}%}-{t[2]:.{d}%})"


def main_size():
    tasks = [(sc, pct, cp, d0, d1) for sc in SCENS for pct in SIZES for cp in CAPS for d0, d1 in chunks()]
    res = {}
    with Pool(max(1, __import__("os").cpu_count() - 2)) as pool:
        for n, (args, out) in enumerate(pool.imap_unordered(task_size, tasks), 1):
            sc, pct, cp, d0, _ = args
            res.setdefault((sc, pct, cp), {})[d0] = out
            if n % 50 == 0:
                print(f"{n}/{len(tasks)} chunks", flush=True)
    data = {k: np.concatenate([v[d] for d in sorted(v)]) for k, v in res.items()}
    np.savez_compressed("simulate_zone_size_days.npz",
                        **{f"{sc}_{pct}_{cp}": a for (sc, pct, cp), a in data.items()})
    rng = np.random.default_rng(7)
    summ = {k: [summarise(a[:, j, :], rng) for j in range(len(POLICIES))] for k, a in data.items()}

    lines = [f"ZONE SIZE SWEEP: {DAYS} simulated days per setting, {CAR_PARK}-bay car park. "
             f"Averages per day; 95% ranges in brackets.",
             "Kept = bookings that got a bay. Accepted = booking requests accepted under the cap. "
             "Held = bay-hours held empty while shoppers wanted them. Redirected = share of walk-ins sent to general parking."]
    for sc in SCENS:
        lines.append(f"\n{sc.upper()} DAY")
        lines.append(f"{'Zone':<14}{'Cap':<10}{'Rule':<13}{'Kept':>26}{'Failed/day':>12}{'Accepted':>12}{'Held (bay-h)':>22}{'Redirected':>12}{'Full 5-9pm':>12}")
        for pct in SIZES:
            bays = zone_bays(pct)
            for cp in CAPS:
                cap = cap_for(bays, cp)
                for j, (_, label) in enumerate(POLICIES):
                    m = summ[(sc, pct, cp)][j]
                    held = f"{m['held'][0]:.0f} ({m['held'][1]:.0f}-{m['held'][2]:.0f})"
                    lines.append(f"{f'{pct}% ({bays})':<14}{f'{cp}% ({cap})':<10}{label:<13}{fmt_pct(m['kept'], 2):>26}"
                                 f"{m['fail']:>12.2f}{m['accept'][0]:>12.0%}{held:>22}{m['redirected'][0]:>12.1%}{m['occ']:>12.0%}")
            lines.append("")

    # Choice rule (fixed before running): ParkFlow only.
    lines.append("CHOICE RULE: smallest zone where some cap keeps >= 99.5% of bookings on the stress day "
                 "and accepts >= 90% of busy-day requests; then the cap with the fewest busy-day bay-hours held empty.")
    lines.append(f"{'Zone':<14}{'Cap':<10}{'Stress kept':>14}{'Busy accepted':>15}{'Busy held':>11}  Passes")
    best = None
    for pct in SIZES:
        bays = zone_bays(pct)
        passing = []
        for cp in CAPS:
            st, bu = summ[("stress", pct, cp)][0], summ[("busy", pct, cp)][0]
            ok = st["kept"][0] >= KEEP_MIN and bu["accept"][0] >= ACCEPT_MIN
            lines.append(f"{f'{pct}% ({bays})':<14}{f'{cp}% ({cap_for(bays, cp)})':<10}{st['kept'][0]:>14.2%}"
                         f"{bu['accept'][0]:>15.0%}{bu['held'][0]:>11.0f}  {'yes' if ok else 'no'}")
            if ok:
                passing.append((bu["held"][0], cp))
        if passing and best is None:
            best = (pct, min(passing)[1])
    if best:
        pct, cp = best
        lines.append(f"\nRECOMMENDED: zone {pct}% of the car park ({zone_bays(pct)} bays at KL East), "
                     f"booking cap {cp}% of the zone ({cap_for(zone_bays(pct), cp)} at once).")
    else:
        lines.append("\nRECOMMENDED: no setting passed both tests.")
    out = "\n".join(lines)
    print(out)
    with open("simulate_zone_size_results.txt", "w", encoding="utf-8") as f:
        f.write(out.strip() + "\n")


def main_layout(sizes, cap_pct=20):
    tasks = [(sc, pct, cap_pct, k, d0, d1) for sc in SCENS for pct in sizes for k in (1, 2, 4) for d0, d1 in chunks()]
    res = {}
    with Pool(max(1, __import__("os").cpu_count() - 2)) as pool:
        for args, out in pool.imap_unordered(task_layout, tasks):
            sc, pct, cp, k, d0, _ = args
            res.setdefault((sc, pct, k), {})[d0] = out
    data = {key: np.concatenate([v[d] for d in sorted(v)]) for key, v in res.items()}
    rng = np.random.default_rng(11)
    lines = [f"\nLAYOUT: one block vs the same zone split into 2 or 4 pieces run separately "
             f"(ParkFlow rule, cap {cap_pct}% of the zone, {DAYS} days). A shared pool across pieces equals one block here."]
    lines.append(f"{'Day':<8}{'Zone':<14}{'Pieces':<8}{'Kept':>26}{'Failed/day':>12}{'Accepted':>12}{'Held (bay-h)':>22}{'Redirected':>12}")
    for sc in SCENS:
        for pct in sizes:
            for k in (1, 2, 4):
                m = summarise(data[(sc, pct, k)], rng)
                held = f"{m['held'][0]:.0f} ({m['held'][1]:.0f}-{m['held'][2]:.0f})"
                lines.append(f"{sc:<8}{f'{pct}% ({zone_bays(pct)})':<14}{k:<8}{fmt_pct(m['kept'], 2):>26}"
                             f"{m['fail']:>12.2f}{m['accept'][0]:>12.0%}{held:>22}{m['redirected'][0]:>12.1%}")
        lines.append("")
    out = "\n".join(lines)
    print(out)
    with open("simulate_zone_size_results.txt", "a", encoding="utf-8") as f:
        f.write(out.rstrip() + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "layout":
        main_layout([int(x) for x in sys.argv[2:]] or [8, 10, 15])
    else:
        main_size()
