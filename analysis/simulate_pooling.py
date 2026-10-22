"""Booking zone: five ways to run the same 100-bay zone, on the same simulated days.

  none      - no priority: people who would book take their chances like everyone else
  vip       - fixed VIP section: 20 bays are booking-only all day, 80 are public
  formula   - shared zone, fixed rule: public may enter only if
              free bays - bookings due in the next 60 min - 5 safety bays > 0
  formula0  - the same fixed rule with no safety bays
  forecast  - shared zone, forecast rule (ParkFlow): public may enter only if, at each
              booking's arrival time, the bays forecast to be free still cover the
              bookings likely to show up, with a safety level (Z)

All accept bookings the same way (at most 20 at once), so the only difference is how the
zone protects them. Bookings follow the ParkFlow model: PRIME homeowners (30% of bookings,
free) book 2-24 hours ahead; everyone else (RM4) 15-120 minutes ahead.

Inputs taken from published evidence where it exists:
  - Stay length: lognormal fitted to the quartiles of >200,000 plate-camera stays in a
    1,300-bay mall car park (44 / 87 / 155 min; mean ~125 min).
    Mueller et al. (2026), Applied Sciences 16:6704.
  - Arrival peaks at 12-1 pm and 5-6 pm in a mall car park (166,836 records).
    Sun et al. (2025), PLOS ONE.
  - Show-up: free bookings ~80% (free reservations show 75-91%: Tse & Poon 2016, restaurant
    no-shows 9-13%; trail-parking reservations 75-80%); paid bookings ~95% (deposits cut
    no-shows sharply, e.g. OpenTable -60%).
Still our assumptions: how many cars want this zone (set so it fills at peak, which is the
problem being solved), booking requests per day, booked stay lengths.

A robustness section then breaks the forecast on purpose (stays longer than it thinks,
more show-ups than it thinks) and lets some shoppers ignore the amber sign.
Usage: python simulate_pooling.py   (writes simulate_pooling_results.txt)
"""
import math
import numpy as np
from scipy.special import ndtr

C = 100               # bays in the booking zone
QUOTA = 20            # most bookings at the same time
VIP_BAYS = 20         # fixed VIP section size, same as the quota
MARGIN = 5            # safety bays in the fixed rule
Z = 1.0               # safety level in the forecast rule (higher = more cautious)
SHOW_PRIME = 0.80     # free bookings that turn up
SHOW_PAID = 0.95      # paid (RM4) bookings that turn up
PRIME_SHARE = 0.3     # share of bookings made by PRIME homeowners
LEAD_PRIME = (120, 24 * 60)   # PRIME can book up to 24 hours ahead
LEAD_PUBLIC = (15, 120)       # everyone else up to 2 hours ahead
HORIZON = 60          # fixed rule counts bookings due in the next 60 minutes
WINDOW = 30           # arrival window + grace, minutes; after that the booking expires
OPEN, CLOSE = 10 * 60, 23 * 60
PEAK_MID, PEAK_EVE = 12 * 60 + 30, 17 * 60 + 30   # Sun et al. (2025)
DAYS = 1000           # simulated days per setting (the 300-day run is kept in simulate_pooling_results_300days.txt)

# Public stay: lognormal fitted to Mueller et al. (2026) quartiles 44 / 87 / 155 minutes.
P_SIG0 = math.log(155 / 44) / (2 * 0.6745)
P_SIG = P_SIG0
P_MU = math.log(87)
# What the forecast rule believes about stays and show-ups. By default it equals the truth; the
# LEARNED test replaces it with estimates from a simulated 2-week pilot, so the rule has to work
# with fitted (and, with cinema-goers, mis-shaped) models instead of the true distribution.
B_MU, B_SIG = P_MU, P_SIG
B_SHOW_PRIME, B_SHOW_PAID = SHOW_PRIME, SHOW_PAID
CINEMA_MEAN, CINEMA_SD = 165, 25   # stay of a film-plus-dinner visit, minutes (assumption)
# Booked stay = booked duration x noise (mean 1, sd 0.25), so some overstay.
M_SIG = math.sqrt(math.log(1 + 0.25 ** 2))
DURS, DUR_P = [60, 90, 120, 150, 180, 240], [0.1, 0.15, 0.25, 0.2, 0.2, 0.1]

SCEN = {
    # cars per minute wanting this zone (it is next to the lifts), booking requests per day
    "busy":   dict(base=0.48, mid=0.36, eve=0.84, members=60),
    "normal": dict(base=0.30, mid=0.18, eve=0.42, members=25),
    # Stress test: stays 40% longer (e.g. a cinema-heavy evening), more bookings, bigger quota
    "stress":  dict(base=0.48, mid=0.36, eve=0.84, members=100, stay_factor=1.4, quota=30),
}


def make_day(rng, s, stay_factor=1.0, show=None, cinema=0.0):
    """stay_factor and show (prime, paid) set what really happens; the forecast keeps its own beliefs.
    cinema: share of walk-ins who are film-plus-dinner visitors with long, bell-shaped stays."""
    sp, sd = (SHOW_PRIME, SHOW_PAID) if show is None else show
    t = np.arange(OPEN, CLOSE)
    lam = (s["base"] + s["mid"] * np.exp(-0.5 * ((t - PEAK_MID) / 90) ** 2)
           + s["eve"] * np.exp(-0.5 * ((t - PEAK_EVE) / 100) ** 2))
    pub = []  # (arrival minute, stay)
    for m, l in zip(t, lam):
        for _ in range(rng.poisson(l)):
            if cinema and rng.random() < cinema:
                st = max(90.0, rng.normal(CINEMA_MEAN, CINEMA_SD))
            else:
                st = max(15.0, rng.lognormal(P_MU, P_SIG))
            pub.append((int(m), st * stay_factor))
    mem = []
    for _ in range(rng.poisson(s["members"])):
        ws = rng.normal(PEAK_MID, 90) if rng.random() < 0.4 else rng.normal(PEAK_EVE + 60, 90)
        ws = int(np.clip(ws, OPEN + 60, CLOSE - 90))
        d = int(rng.choice(DURS, p=DUR_P))
        prime = rng.random() < PRIME_SHARE
        lead = int(rng.integers(*(LEAD_PRIME if prime else LEAD_PUBLIC)))
        mem.append(dict(
            ws=ws, d=d, prime=prime, book=max(OPEN - 60, ws - lead), show=rng.random() < (sp if prime else sd),
            arr=ws + int(rng.triangular(-5, 5, WINDOW)),
            stay=d * rng.lognormal(-M_SIG ** 2 / 2, M_SIG) * stay_factor))
    return pub, mem


def leave_prob(cars, now, tau):
    """Chance each parked car has left by now+tau, given it is still here now (cars x checkpoints)."""
    el = np.array([now - c["in"] for c in cars], float)[:, None]
    mu = np.array([B_MU if c["d"] is None else math.log(c["d"]) - M_SIG ** 2 / 2 for c in cars])[:, None]
    sg = np.array([B_SIG if c["d"] is None else M_SIG for c in cars])[:, None]
    F = lambda x: ndtr((np.log(np.maximum(x, 1e-6)) - mu) / sg)
    f0 = F(el)
    return (F(el + tau[None, :]) - f0) / np.maximum(1 - f0, 1e-9)


def run(policy, pub, mem, ignore=0.0, rng=None, stats=None):
    """ignore: share of shoppers who park anyway when the zone is held (there is no barrier).
    stats: optional dict; receives "accepted", the booking requests accepted under the quota."""
    booked = np.zeros(CLOSE + 400, int)   # bookings counted against the quota, per minute
    parked = []                           # dicts: in, out, d (None for public), vip
    pend = []                             # accepted bookings not yet arrived or expired
    by_book, by_arr, by_pub = {}, {}, {}
    for m in mem:
        by_book.setdefault(m["book"], []).append(m)
    for a, st in pub:
        by_pub.setdefault(a, []).append(st)
    ok = fail = turned = acc = 0
    held = held_w = 0.0
    occ_eve = []
    for now in range(OPEN - 60, CLOSE):
        parked = [c for c in parked if c["out"] > now]
        for b in [b for b in pend if now > b["ws"] + WINDOW]:      # expired: release quota
            pend.remove(b)
            booked[now:b["ws"] + b["d"]] -= 1
        for m in by_book.get(now, []):                              # new booking requests
            if policy == "none":
                if m["show"]:
                    by_arr.setdefault(m["arr"], []).append(m)
                continue
            if booked[m["ws"]:m["ws"] + m["d"]].max() < QUOTA:
                booked[m["ws"]:m["ws"] + m["d"]] += 1
                acc += 1
                pend.append(m)
                if m["show"]:
                    by_arr.setdefault(m["arr"], []).append(m)
        if now < OPEN:
            continue
        for m in by_arr.get(now, []):                               # booked cars arrive
            if m in pend:
                pend.remove(m)
            elif policy != "none":
                continue  # arrived after the booking expired
            nv = sum(c["vip"] for c in parked)
            if policy == "vip" and nv < VIP_BAYS:
                parked.append(dict(out=now + m["stay"], d=m["d"], vip=True, **{"in": now})); ok += 1
            elif len(parked) < C and (policy != "vip" or len(parked) - nv < C - VIP_BAYS):
                parked.append(dict(out=now + m["stay"], d=m["d"], vip=False, **{"in": now})); ok += 1
            else:
                fail += 1
        free = C - len(parked)
        if policy in ("none", "vip"):
            allow = free if policy == "none" else max(0, C - VIP_BAYS - sum(not c["vip"] for c in parked))
        elif policy in ("formula", "formula0"):
            due = sum(1 for b in pend if b["ws"] - now <= HORIZON)
            allow = max(0, free - due - (MARGIN if policy == "formula" else 0))
        else:
            allow = free
            if pend:
                p_show = np.array([B_SHOW_PRIME if b["prime"] else B_SHOW_PAID for b in pend])
                order = sorted(range(len(pend)), key=lambda i: pend[i]["ws"])
                arr_hi = np.cumsum(p_show[order]) + Z * np.sqrt(np.cumsum((p_show * (1 - p_show))[order]))
                if parked:
                    tau = np.array([max(0, pend[i]["ws"] - 5 - now) for i in order], float)
                    q = leave_prob(parked, now, tau)
                    dep_lo = np.maximum(q.sum(0) - Z * np.sqrt((q * (1 - q)).sum(0)), 0)
                else:
                    dep_lo = np.zeros(len(order))
                allow = int(max(0, min(free, np.floor((free + dep_lo - arr_hi).min()))))
        want = len(by_pub.get(now, []))
        enter = min(want, allow)
        turned += want - enter
        for st in by_pub.get(now, [])[:enter]:
            parked.append(dict(out=now + st, d=None, vip=False, **{"in": now}))
        if ignore and policy != "none":
            for st in by_pub.get(now, [])[enter:]:      # turned away, but some park anyway
                if rng.random() >= ignore:
                    continue
                nv = sum(c["vip"] for c in parked)
                if policy == "vip" and nv < VIP_BAYS:
                    parked.append(dict(out=now + st, d=None, vip=True, **{"in": now})); turned -= 1
                elif policy != "vip" and len(parked) < C:
                    parked.append(dict(out=now + st, d=None, vip=False, **{"in": now})); turned -= 1
        free = C - len(parked)
        blocked = max(0, free - max(0, allow - enter)) if policy != "none" else 0
        held += blocked / 60                    # bays held back from walk-ins
        if want > enter:
            held_w += blocked / 60              # ... in minutes when a walk-in was actually turned away
        if 17 * 60 <= now < 21 * 60:
            occ_eve.append(len(parked) / C)
    if stats is not None:
        stats["accepted"] = acc
        stats["held_wanted"] = held_w
    return ok, fail, turned, held, np.mean(occ_eve)


def fit_beliefs(n_sets=50, days=14, cinema=0.0):
    """Stay model the forecast would fit from weeks 1-2 of the pilot (measure only: no bookings yet,
    so show-up rates stay at the published priors). One fitted model per simulated pilot."""
    sets = []
    for k in range(n_sets):
        logs = []
        for j in range(days):
            pub, _ = make_day(np.random.default_rng(50000 + k * days + j), SCEN["busy" if j % 7 >= 5 else "normal"], 1.0, None, cinema)
            logs += [math.log(st) for _, st in pub]
        logs = np.array(logs)
        sets.append((float(logs.mean()), float(logs.std()), SHOW_PRIME, SHOW_PAID))
    return sets


def _days(args):
    """Worker: run every policy on days d0..d1 of one setting. Returns days x policies x 7."""
    global QUOTA, VIP_BAYS, Z, B_MU, B_SIG, B_SHOW_PRIME, B_SHOW_PAID
    policies, scen, sf, show, ign, quota, z, beliefs, cinema, shock, d0, d1 = args
    QUOTA = VIP_BAYS = quota
    Z = z
    out = np.zeros((d1 - d0, len(policies), 7))
    for i, day in enumerate(range(d0, d1)):
        if beliefs:
            B_MU, B_SIG, B_SHOW_PRIME, B_SHOW_PAID = beliefs[day % len(beliefs)]
        else:
            B_MU, B_SIG, B_SHOW_PRIME, B_SHOW_PAID = P_MU, P_SIG, SHOW_PRIME, SHOW_PAID
        dsf, dshow = sf, show
        if shock:
            # Correlated day-level shock the forecast does not see: every stay that day is longer or
            # shorter together (e.g. a film runs late, rain), and show-up rates shift together.
            r = np.random.default_rng(70000 + day)
            dsf = sf * math.exp(r.normal(0, shock))
            d = r.normal(0, shock / 2)
            base = (SHOW_PRIME, SHOW_PAID) if show is None else show
            dshow = (float(np.clip(base[0] + d, 0.5, 1.0)), float(np.clip(base[1] + d / 2, 0.7, 1.0)))
        pub, mem = make_day(np.random.default_rng(1000 + day), scen, dsf, dshow, cinema)
        for j, p in enumerate(policies):
            st = {}
            r = run(p, pub, mem, ign, np.random.default_rng(9000 + day), stats=st)
            out[i, j] = [*r, st["held_wanted"], st["accepted"]]
    return out


def simulate(pool, policies, scen, sf=1.0, show=None, ign=0.0, quota=20, z=None, beliefs=None, cinema=0.0, shock=0.0, per_day=False):
    """Average per day for each policy: ok, fail, turned, held, occ, held_wanted, accepted.
    per_day=True returns the raw days x policies x 7 array instead."""
    z = Z if z is None else z
    chunks = [(policies, scen, sf, show, ign, quota, z, beliefs, cinema, shock, d, min(d + 50, DAYS)) for d in range(0, DAYS, 50)]
    allr = np.concatenate(pool.map(_days, chunks))
    if per_day:
        return allr
    return {p: allr[:, j].mean(0) for j, p in enumerate(policies)}


def extra():
    """Harder tests asked for by reviewers; appended to simulate_pooling_results.txt.
    1) more shoppers ignoring amber (20-40%), 2) correlated day-level shocks the forecast cannot see,
    3) both together with a learned model, 4) how many pilot days a switchback test needs."""
    from multiprocessing import Pool
    import os
    LP = [("vip", "VIP section"), ("formula0", "Fixed rule (0 safety)"), ("forecast", "ParkFlow")]
    L = ["\nHARDER TESTS, busy day, 1000 days. Bookings got a bay (failed per day) / held back while walk-ins waited (bay-h)"]
    L.append(f"{'Scenario':<58}" + "".join(f"{lab:>30}" for _, lab in LP))
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        learned = fit_beliefs(cinema=0.4)
        rows = [("20% of shoppers ignore amber", dict(ign=0.20)),
                ("30% ignore amber", dict(ign=0.30)),
                ("40% ignore amber", dict(ign=0.40)),
                ("Day-level shock, sd 15% (stays and show-ups move together)", dict(shock=0.15)),
                ("Day-level shock, sd 30%", dict(shock=0.30)),
                ("30% ignore + shock 30% + learned model + 40% cinema", dict(ign=0.30, shock=0.30, beliefs=learned, cinema=0.4))]
        for name, kw in rows:
            res = simulate(pool, [p for p, _ in LP], SCEN["busy"], **kw)
            cells = []
            for p, _ in LP:
                ok, fail, turned, held, occ, held_w, acc = res[p]
                cells.append(f"{ok / (ok + fail):.2%} ({fail:.2f}) / {held_w:.0f}")
            L.append(f"{name:<58}" + "".join(f"{c:>30}" for c in cells))
        # Pilot power: busy days alternate between the fixed rule and ParkFlow at random (switchback).
        raw = simulate(pool, ["formula0", "forecast"], SCEN["busy"], ign=0.10, shock=0.15, per_day=True)
        hw_f, hw_p = raw[:, 0, 5], raw[:, 1, 4 + 1]
        tw_f, tw_p = raw[:, 0, 2], raw[:, 1, 2]
        L.append("\nPILOT POWER (switchback: each busy day randomly runs the fixed rule or ParkFlow; 10% ignore amber, shock 15%)")
        L.append(f"Per busy day: held back while walk-ins waited {hw_f.mean():.1f} vs {hw_p.mean():.1f} bay-h (sd {hw_f.std():.1f} / {hw_p.std():.1f}); "
                 f"walk-ins turned away {tw_f.mean():.0f} vs {tw_p.mean():.0f} (sd {tw_f.std():.0f} / {tw_p.std():.0f})")
        rng = np.random.default_rng(3)
        for n in (6, 10, 16, 24, 32):
            wins = 0
            for _ in range(4000):
                a = rng.choice(hw_f, n // 2); b = rng.choice(hw_p, n // 2)
                se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
                wins += (a.mean() - b.mean()) / max(se, 1e-9) > 1.96
            L.append(f"  {n:>2} busy days ({n // 2} per rule): chance the pilot detects ParkFlow's advantage = {wins / 4000:.0%}")
    out = "\n".join(L)
    print(out)
    with open("simulate_pooling_results.txt", "a") as f:
        f.write(out.rstrip() + "\n")


def main():
    from multiprocessing import Pool
    import os
    lines = []
    POL = [("none", "No priority"), ("vip", "Fixed VIP section"), ("formula", "Fixed rule (5 safety bays)"),
           ("formula0", "Fixed rule (0 safety bays)"), ("forecast", "Forecast rule (ParkFlow)")]
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        for name, s in SCEN.items():
            sf = s.get("stay_factor", 1.0)
            quota = s.get("quota", 20)
            # Same days for every policy. In the stress test the forecast is not told stays are longer.
            res = simulate(pool, [p for p, _ in POL], s, sf, quota=quota)
            lines.append(f"\n{name.upper()} DAY, {DAYS} simulated days, {C}-bay zone, stays x{sf}, "
                         f"{s['members']} booking requests, quota {quota}, averages per day")
            lines.append(f"{'Policy':<28}{'Bookings got a bay':>19}{'Bookings failed':>16}{'Public turned away':>20}"
                         f"{'Bays held back (bay-h)':>24}{'...while walk-ins turned away':>31}{'Occupied 5-9 pm':>17}")
            for p, label in POL:
                ok, fail, turned, held, occ, held_w, acc = res[p]
                lines.append(f"{label:<28}{ok / (ok + fail):>18.1%}{fail:>16.2f}{turned:>20.0f}{held:>24.0f}{held_w:>31.0f}{occ:>16.0%}")

        # Robustness: busy day, the forecast is wrong on purpose and some shoppers ignore amber.
        ROB = [("As assumed", 1.0, None, 0.0),
               ("Stays 20% longer than forecast", 1.2, None, 0.0),
               ("More show up (95%/99% vs 80%/95%)", 1.0, (0.95, 0.99), 0.0),
               ("10% of shoppers ignore amber", 1.0, None, 0.10),
               ("All three at once", 1.2, (0.95, 0.99), 0.10)]
        RP = [p for p in POL if p[0] != "none"]
        lines.append(f"\nROBUSTNESS, busy day, {DAYS} days. Bookings got a bay (failed per day) / bays held back (bay-h)")
        lines.append(f"{'Scenario':<36}" + "".join(f"{label:>30}" for _, label in RP))
        for name, sf, sh, ig in ROB:
            res = simulate(pool, [p for p, _ in RP], SCEN["busy"], sf, sh, ig)
            cells = []
            for p, _ in RP:
                ok, fail, turned, held, occ, held_w, acc = res[p]
                cells.append(f"{ok / (ok + fail):.2%} ({fail:.2f}) / {held:.0f}")
            lines.append(f"{name:<36}" + "".join(f"{c:>30}" for c in cells))

        # Caution level: the forecast rule's safety level Z is a dial. Same busy days, as assumed and worst case.
        lines.append("\nCAUTION LEVEL (forecast rule only), busy day. Bookings got a bay (failed per day) / bays held back (bay-h)")
        for z in (1.0, 1.5, 2.0):
            cells = []
            for sf, sh, ig in ((1.0, None, 0.0), (1.2, (0.95, 0.99), 0.10)):
                ok, fail, turned, held, occ, held_w, acc = simulate(pool, ["forecast"], SCEN["busy"], sf, sh, ig, z=z)["forecast"]
                cells.append(f"{ok / (ok + fail):.2%} ({fail:.2f}) / {held:.0f}")
            lines.append(f"Z={z:<4}  as assumed: {cells[0]:<24} all three at once: {cells[1]}")

        # Learned model: the forecast fits its stay model from a simulated 2-week pilot instead of
        # knowing the truth. 50 different pilots, so estimation error varies from day to day.
        LP = [("vip", "Fixed VIP section"), ("formula0", "Fixed rule (0 safety bays)"), ("forecast", "Forecast rule (ParkFlow)")]
        plain = fit_beliefs(cinema=0.0)
        mixed = fit_beliefs(cinema=0.4)
        LEARN = [("Learned from 2 weeks, stays as in research", plain, 0.0, 1.0, None, 0.0),
                 ("Learned, 40% cinema-goers (stays not lognormal)", mixed, 0.4, 1.0, None, 0.0),
                 ("Learned + cinema + more show-ups + 10% ignore amber", mixed, 0.4, 1.0, (0.95, 0.99), 0.10)]
        lines.append(f"\nLEARNED MODEL, busy day, {DAYS} days. The forecast fits its stay model from a simulated 2-week pilot "
                     "(50 different pilots); show-up rates stay at the published priors (80% free / 95% paid).")
        lines.append(f"{'Scenario':<54}{'Rule':<30}{'Bookings got a bay':>19}{'Failed/day':>11}{'Turned away':>12}{'Held back':>10}{'...while turned away':>22}")
        for name, bel, cin, sf, sh, ig in LEARN:
            res = simulate(pool, [p for p, _ in LP], SCEN["busy"], sf, sh, ig, beliefs=bel, cinema=cin)
            for p, label in LP:
                ok, fail, turned, held, occ, held_w, acc = res[p]
                lines.append(f"{name:<54}{label:<30}{ok / (ok + fail):>18.2%}{fail:>11.2f}{turned:>12.0f}{held:>10.0f}{held_w:>22.0f}")
        mu = np.mean([b[0] for b in plain]); sg = np.mean([b[1] for b in plain])
        mu2 = np.mean([b[0] for b in mixed]); sg2 = np.mean([b[1] for b in mixed])
        lines.append(f"Fitted stay model (median, minutes): research-like stays {math.exp(mu):.0f} (true {math.exp(P_MU):.0f}), "
                     f"log-sd {sg:.2f} (true {P_SIG:.2f}); with 40% cinema-goers median {math.exp(mu2):.0f}, log-sd {sg2:.2f}.")

    lines.append(f"\nInputs: stays lognormal median 87 min, mean ~125 min (Mueller et al. 2026); peaks 12:30 and 17:30 (Sun et al. 2025); "
                 f"show-up {SHOW_PRIME:.0%} free / {SHOW_PAID:.0%} paid; {PRIME_SHARE:.0%} of bookings by PRIME, "
                 f"{LEAD_PRIME[0] // 60}-{LEAD_PRIME[1] // 60} h ahead, others {LEAD_PUBLIC[0]}-{LEAD_PUBLIC[1]} min; window+grace {WINDOW} min; "
                 f"fixed rule counts bookings due in {HORIZON} min, safety bays {MARGIN}; forecast Z={Z}. Same simulated days for every policy. "
                 f"'Bays held back' = free bays closed to walk-ins; '...while walk-ins turned away' counts only minutes when a walk-in was refused.")
    out = "\n".join(lines)
    print(out)
    with open("simulate_pooling_results.txt", "w") as f:
        f.write(out.strip() + "\n")


if __name__ == "__main__":
    import sys
    extra() if sys.argv[1:] == ["extra"] else main()
