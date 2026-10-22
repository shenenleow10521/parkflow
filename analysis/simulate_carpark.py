"""Whole car park, busy Saturday: where do drivers spend time searching, with and without ParkFlow?

simulate_pooling.py models only the 100-bay Priority Zone. This model follows every car in a
1,300-bay car park (4 levels of 325 bays; the 100-bay zone is part of B1 by the lifts) so that
redirected walk-ins, level guidance and the planet effect are counted, not assumed.

Scenarios, on the same simulated days:
  today     - a gate count only (no entry when the whole car park is full), no level guidance.
              Drivers try levels in order of preference (B1, B2, B3, L1) and only learn a level
              is full by circling it. Would-be bookers are ordinary walk-ins.
  parkflow  - entrance signs and the app show which levels have space, so drivers skip full
              levels; booked drivers go straight to the zone; walk-ins may use the zone only when
              its sign is green (the simple fixed rule is used here, which is conservative: the
              forecast rule lets more walk-ins in).
  guidance  - level guidance only, no Priority Zone (to separate the two effects).

Search time on a level with a share f of bays free: SEARCH_A / f minutes, capped at one full
loop (LOOP) when the level is full; moving to the next level takes RAMP minutes. These are
assumptions (no published Malaysian figures), so results are shown with a sensitivity range.
Planet: car-park cruising at CRUISE_KMH; fuel at crawl FUEL_L_PER_KM; 2.31 kg CO2 per litre of
petrol (UK DESNZ/DEFRA conversion factor).
Usage: python simulate_carpark.py   (writes simulate_carpark_results.txt)
"""
import os
from multiprocessing import Pool

import numpy as np

import simulate_pooling as sp

LEVELS = ["B1", "B2", "B3", "L1"]          # order of preference (B1 has the lifts and the zone)
LEVEL_BAYS = 325
ZONE = 100                                 # Priority Zone bays inside B1
DEMAND = 0.60                              # x the zone model's per-bay arrival rate (tuned so the car park
                                           # is ~95% full at the evening peak with B1 and B2 full)
SEARCH_A = 0.06                            # minutes x (1 / share free) to find a bay on a level
LOOP = 3.0                                 # minutes to circle a full level
RAMP = 1.0                                 # minutes to drive to the next level
GUIDE_MIN_FREE = 5                         # a sign shows "space" when at least this many bays are free
CRUISE_KMH = 10.0
FUEL_L_PER_KM = 0.15                       # stop-start crawl in a car park (assumption)
CO2_PER_L = 2.31                           # kg CO2 per litre petrol
DAYS = 1000


def make_day(seed, demand=DEMAND):
    rng = np.random.default_rng(seed)
    s = dict(sp.SCEN["busy"])
    scale = demand * (len(LEVELS) * LEVEL_BAYS) / 100
    t = np.arange(sp.OPEN, sp.CLOSE)
    lam = (s["base"] + s["mid"] * np.exp(-0.5 * ((t - sp.PEAK_MID) / 90) ** 2)
           + s["eve"] * np.exp(-0.5 * ((t - sp.PEAK_EVE) / 100) ** 2)) * scale
    cars = []
    for m, l in zip(t, lam):
        for _ in range(rng.poisson(l)):
            cars.append((int(m), max(15.0, rng.lognormal(sp.P_MU, sp.P_SIG)), False))
    # Booked drivers: the busy-day booking requests, arriving in their booking window (80%/95% show up).
    for _ in range(rng.poisson(s["members"])):
        ws = rng.normal(sp.PEAK_MID, 90) if rng.random() < 0.4 else rng.normal(sp.PEAK_EVE + 60, 90)
        ws = int(np.clip(ws, sp.OPEN + 60, sp.CLOSE - 90))
        show = rng.random() < (sp.SHOW_PRIME if rng.random() < sp.PRIME_SHARE else sp.SHOW_PAID)
        if show:
            d = int(rng.choice(sp.DURS, p=sp.DUR_P))
            cars.append((ws + int(rng.triangular(-5, 5, sp.WINDOW)), d * rng.lognormal(-sp.M_SIG ** 2 / 2, sp.M_SIG), True))
    cars.sort(key=lambda c: c[0])
    return cars


def run_day(cars, mode, search_a=SEARCH_A):
    """Returns total search minutes, booked search minutes, walk-in search minutes, drivers who
    found no bay, drivers searching > 10 min, number of drivers, peak occupancy."""
    # Each level: list of departure times of parked cars. B1 split into zone and general part.
    cap = {"Z": ZONE, "B1": LEVEL_BAYS - ZONE, "B2": LEVEL_BAYS, "B3": LEVEL_BAYS, "L1": LEVEL_BAYS}
    out = {k: [] for k in cap}
    booked_due = []                            # arrival minutes of booked cars still to come
    zone_on = mode == "parkflow"
    if zone_on:
        booked_due = sorted(a for a, _, b in cars if b)
    tot = bk = wk = lost = long = n = 0.0
    peak = 0.0
    for a, stay, booked in cars:
        for k in out:                          # cars that left before this arrival
            out[k] = [o for o in out[k] if o > a]
        if zone_on:
            while booked_due and booked_due[0] < a:
                booked_due.pop(0)
        free = {k: cap[k] - len(out[k]) for k in cap}
        peak = max(peak, 1 - sum(free.values()) / sum(cap.values()))
        n += 1
        if sum(free.values()) <= 0:            # the gate count shows FULL (common today): no entry, no search
            lost += 1
            continue
        if zone_on and booked:
            # Straight to the zone; ParkFlow keeps a bay (if the zone is full, search like others).
            if free["Z"] > 0:
                out["Z"].append(a + stay)
                continue
        # Which parts of B1 this driver may use, and which levels the driver will try.
        if zone_on:
            due = sum(1 for d in booked_due if d - a <= sp.HORIZON)
            zone_open = free["Z"] - due > 0
        else:
            zone_open = True
        b1_parts = ["B1", "Z"] if zone_open else ["B1"]
        order = []
        for lv in LEVELS:
            parts = b1_parts if lv == "B1" else [lv]
            f = sum(free[p] for p in parts)
            if mode in ("parkflow", "guidance") and f < GUIDE_MIN_FREE:
                continue                       # the sign says full: skip without searching
            order.append((lv, parts, f, sum(cap[p] for p in parts)))
        t = 0.0
        placed = False
        for i, (lv, parts, f, c) in enumerate(order):
            if i > 0:
                t += RAMP
            if f <= 0:
                t += LOOP
                continue
            t += min(LOOP, search_a / (f / c))
            p = max(parts, key=lambda q: free[q])      # take a bay where most are free
            out[p].append(a + t + stay)
            placed = True
            break
        if not placed:
            if not order:                       # every sign said full: no search, the driver goes elsewhere
                t = 0.0
            lost += 1
        tot += t
        if booked:
            bk += t
        else:
            wk += t
        if t > 10:
            long += 1
    return np.array([tot, bk, wk, lost, long, n, peak])


def _chunk(args):
    mode, d0, d1, search_a, demand = args
    return np.array([run_day(make_day(1000 + d, demand), mode, search_a) for d in range(d0, d1)])


def simulate(pool, mode, search_a=SEARCH_A, demand=DEMAND, days=DAYS):
    chunks = [(mode, d, min(d + 50, days), search_a, demand) for d in range(0, days, 50)]
    return np.concatenate(pool.map(_chunk, chunks))


def main():
    lines = [f"WHOLE CAR PARK, busy Saturday, {DAYS} simulated days, {len(LEVELS) * LEVEL_BAYS} bays "
             f"({ZONE}-bay Priority Zone in B1). Per day; 95% range over days in brackets."]
    hdr = f"{'Scenario':<34}{'Search min (all)':>22}{'Min per driver':>16}{'Booked drivers':>16}{'Searched >10 min':>18}{'No bay found':>14}{'Peak full':>11}"
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        res = {m: simulate(pool, m) for m in ("today", "guidance", "parkflow")}
        lines.append(hdr)
        label = {"today": "Today (no guidance, no zone)", "guidance": "Level guidance only", "parkflow": "ParkFlow (guidance + zone)"}
        for m, r in res.items():
            tot = r[:, 0]
            lo, hi = np.percentile(tot, [2.5, 97.5])
            lines.append(f"{label[m]:<34}{tot.mean():>10.0f} ({lo:.0f}-{hi:.0f}){r[:, 0].mean() / r[:, 5].mean():>16.2f}"
                         f"{r[:, 1].mean():>16.0f}{r[:, 4].mean():>18.0f}{r[:, 3].mean():>14.1f}{r[:, 6].mean():>10.0%}")
        today, pf = res["today"], res["parkflow"]
        saved = today[:, 0] - pf[:, 0]                          # paired: same days
        lo, hi = np.percentile(saved, [2.5, 97.5])
        mins = saved.mean()
        km = mins / 60 * CRUISE_KMH
        co2 = km * FUEL_L_PER_KM * CO2_PER_L
        lines.append(f"\nSAVED BY PARKFLOW vs today, per busy Saturday: {mins:.0f} driver-minutes ({lo:.0f}-{hi:.0f}), "
                     f"{km:.0f} vehicle-km of cruising, {km * FUEL_L_PER_KM:.0f} litres of petrol, {co2:.0f} kg CO2.")
        share = 1 - pf[:, 0].mean() / today[:, 0].mean()
        lines.append(f"Search time cut by {share:.0%}. Booked drivers: {today[:, 1].mean():.0f} -> {pf[:, 1].mean():.0f} minutes. "
                     f"Walk-ins: {today[:, 2].mean():.0f} -> {pf[:, 2].mean():.0f} minutes.")
        g = res["guidance"]
        lines.append(f"Of the saving, level guidance alone gives {today[:, 0].mean() - g[:, 0].mean():.0f} min; "
                     f"the Priority Zone adds {g[:, 0].mean() - pf[:, 0].mean():.0f} min.")
        # Year: busy weekend days at full effect; other days assumed at a quarter (they rarely fill).
        yr_min = mins * (104 + 261 * 0.25)
        yr_co2 = yr_min / 60 * CRUISE_KMH * FUEL_L_PER_KM * CO2_PER_L / 1000
        lines.append(f"Per year (104 weekend days at the busy-day saving, 261 other days at a quarter of it): "
                     f"{yr_min / 60:,.0f} driver-hours and about {yr_co2:.1f} tonnes CO2.")

        lines.append("\nSENSITIVITY (saving vs today, driver-minutes per busy Saturday, 300 days each)")
        for name, sa, dm in (("Search 50% faster (SEARCH_A x0.5)", SEARCH_A * 0.5, DEMAND),
                             ("Search 50% slower (SEARCH_A x1.5)", SEARCH_A * 1.5, DEMAND),
                             ("Demand 10% lower", SEARCH_A, DEMAND * 0.9),
                             ("Demand 10% higher", SEARCH_A, DEMAND * 1.1)):
            a = simulate(pool, "today", sa, dm, 300)
            b = simulate(pool, "parkflow", sa, dm, 300)
            lines.append(f"{name:<40}{(a[:, 0] - b[:, 0]).mean():>8.0f}  (today {a[:, 0].mean():.0f}, ParkFlow {b[:, 0].mean():.0f})")

    lines.append(f"\nAssumptions: search {SEARCH_A} min / share of bays free, capped at a {LOOP:.0f}-min loop of a full level; "
                 f"{RAMP:.0f} min between levels; signs show space at >= {GUIDE_MIN_FREE} free bays; cruising {CRUISE_KMH:.0f} km/h; "
                 f"{FUEL_L_PER_KM} L/km at crawl; {CO2_PER_L} kg CO2/L petrol (DESNZ/DEFRA). Stays and arrival peaks as in simulate_pooling.py. "
                 f"Walk-in demand {DEMAND} x the zone model's rate per bay. The zone uses the simple fixed rule here (conservative).")
    out = "\n".join(lines)
    print(out)
    with open("simulate_carpark_results.txt", "w", encoding="utf-8") as f:
        f.write(out.strip() + "\n")


if __name__ == "__main__":
    main()
