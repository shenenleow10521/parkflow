"""V3 extension: whole-level zone (~200 bays), grace period, LPR count drift, revenue.

Self-contained and synthetic. It does NOT modify benchmark_decision_value.py or any V2 result.
Every demand number is a scenario input, not a measured KLGCC value. Policies are the
guard-only and fixed-buffer baselines (the V2 study found no clear ML advantage).

Run from repo root:  python -B analysis/v3_zone200.py
Writes analysis/benchmarks/v3/results.json
"""
from __future__ import annotations
import json, math
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from v3_costs import NET, RUN, CAPEX

OUT = Path(__file__).resolve().parent / 'benchmarks/v3'
END, REQUEST_END, SAFETY = 780, 600, 2
WEEKDAY_FEE, PEAK_FEE = 4.0, 5.0


@dataclass(frozen=True)
class Ev:
    id: int; minute: int; request: bool; order: float; stay: float
    due: int = 0; arrival: int = 0; show: bool = True; duration: int = 120


def bill(stay_min, weekend):
    """KLGCC tariff per financial-sources.md: weekday RM3 flat; weekend RM3 first 3h, RM2/h after, cap RM10."""
    if not weekend:
        return 3.0
    h = math.ceil(stay_min / 60)
    return min(10.0, 3.0 if h <= 3 else 3.0 + 2.0 * (h - 3))


LATE_BINS = [(0, 0), (1, 15), (16, 30), (31, 60)]
LATE_P = [.80, .12, .06, .02]  # ASSUMPTION: punctuality mix, tested by sensitivity below


def make_day(seed, capacity=200, req_per_day=90, weekend=None):
    """Demand scaled to zone size. req_per_day = mean booking requests/day (scenario input)."""
    rng = np.random.default_rng(seed); t = np.arange(END)
    wk = int(seed % 7 >= 5) if weekend is None else weekend
    scale = rng.lognormal(-.3 ** 2 / 2, .3) * (1.0 if wk else .8)
    public = (.48 + .36 * np.exp(-.5 * ((t - 150) / 90) ** 2) + .84 * np.exp(-.5 * ((t - 450) / 100) ** 2)) * scale * (capacity / 100)
    shape = .4 * np.exp(-.5 * ((t - 120) / 90) ** 2) + .6 * np.exp(-.5 * ((t - 480) / 90) ** 2); shape[t >= REQUEST_END] = 0
    request = req_per_day * scale * shape / shape.sum()
    pc, rc = rng.poisson(public), rng.poisson(request)
    ev, uid = [], 0; sigma = math.log(155 / 44) / (2 * .6745)
    for m in range(END):
        for _ in range(pc[m]):
            ev.append(Ev(uid, m, False, float(rng.random()), float(max(15, rng.lognormal(math.log(87), sigma))))); uid += 1
        for _ in range(rc[m]):
            dur = int(rng.choice([60, 90, 120, 150, 180, 240], p=[.1, .15, .25, .2, .2, .1]))
            due = m + int(rng.integers(15, 181))
            lo, hi = LATE_BINS[int(rng.choice(4, p=LATE_P))]
            late = int(rng.integers(lo, hi + 1))
            ev.append(Ev(uid, m, True, float(rng.random()), float(dur * rng.lognormal(-.25 ** 2 / 2, .25)),
                         due, due + late, bool(rng.random() < .90), dur)); uid += 1
    ev.sort(key=lambda e: (e.minute, e.order))
    return wk, ev


def simulate(wk, events, capacity, buffer, grace):
    """Guard + fixed buffer. Soft release: an expired booking is released to the pool; a late
    customer may still enter as a walk-in if capacity allows (no guarantee)."""
    active, pending, arrivals, by_t = [], {}, {}, {}
    for e in events: by_t.setdefault(e.minute, []).append(e)
    m = dict(requests=0, accepted=0, rejected=0, fulfilled=0, noshow=0, expired=0, late_in=0, late_denied=0,
             walkins=0, walkins_denied=0, idle_bayh=0.0)
    outcomes = []  # (kind, stay) per accepted booking, for revenue
    reserve = buffer
    for now in range(END + 240):
        active = [v for v in active if v > now]
        for k, e in list(pending.items()):
            if now > e.due + grace:
                pending.pop(k)
                if not e.show: m['noshow'] += 1; outcomes.append(('noshow', e.stay))
                else: m['expired'] += 1; outcomes.append(('noshow', e.stay))
        for e in arrivals.get(now, []):
            if e.id in pending:
                pending.pop(e.id)
                if len(active) < capacity: active.append(now + e.stay); m['fulfilled'] += 1; outcomes.append(('ok', e.stay))
                else: m['late_denied'] += 1
            else:  # released booking, late arrival
                if capacity - len(active) - SAFETY > 0: active.append(now + e.stay); m['late_in'] += 1
                else: m['late_denied'] += 1
        denied = False
        for e in by_t.get(now, []):
            free = max(0, capacity - len(active) - len(pending) - SAFETY)
            if e.request:
                m['requests'] += 1
                if free > 0:
                    m['accepted'] += 1; pending[e.id] = e
                    if e.show: arrivals.setdefault(e.arrival, []).append(e)
                else: m['rejected'] += 1
            elif free > reserve: active.append(now + e.stay); m['walkins'] += 1
            else: denied = True; m['walkins_denied'] += 1
        if denied: m['idle_bayh'] += max(0, capacity - len(active)) / 60
    return m, outcomes


def revenue(wk, outcomes, s_member, fee_override=None):
    """Incremental booking revenue/day. Fee deposit is credited to the bill for members who arrive.
    Non-members pay fee on top. No-shows (any customer) lose the deposit."""
    fee = (PEAK_FEE if wk else WEEKDAY_FEE) if fee_override is None else fee_override
    total = 0.0
    for kind, stay in outcomes:
        if kind == 'noshow': total += fee
        else: total += fee if np.random.random() >= s_member else max(0.0, fee - bill(stay, wk))
    return total


def net_cash(gross, bookings):
    return gross * NET  # operator share on the ex-SST fee, card fee on the amount collected: see v3_costs.py


def run_main(days=40):
    res = {}
    # 1. capacity / volume sweep at 200 bays, buffer 10, grace 15
    sweep = []
    for rpd in [25, 50, 90, 140, 200]:
        rows = []
        for j in range(days):
            wk, ev = make_day(71000 + j, 200, rpd)
            m, out = simulate(wk, ev, 200, 10, 15)
            rows.append((m, out, wk))
        agg = {k: float(np.mean([r[0][k] for r in rows])) for k in rows[0][0]}
        agg['rejection_pct'] = 100 * agg['rejected'] / max(1, agg['requests'])
        np.random.seed(5)
        for s in [.3, .5, .7]:
            g = [revenue(r[2], r[1], s) for r in rows]
            agg[f'gross_per_day_s{int(s*100)}'] = float(np.mean(g))
        agg['req_per_day'] = rpd; sweep.append(agg)
    res['volume_sweep_200bays'] = sweep
    # 2. grace period test at 90 req/day
    grace = []
    for g in [10, 15, 20, 30]:
        rows = [simulate(*make_day(72000 + j, 200, 90), 200, 10, g)[0] for j in range(days)]
        grace.append({'grace_min': g, **{k: float(np.mean([r[k] for r in rows])) for k in rows[0]}})
    res['grace_test'] = grace
    # 3. buffer test
    buf = []
    for b in [0, 5, 10, 20]:
        rows = [simulate(*make_day(73000 + j, 200, 90), 200, b, 15)[0] for j in range(days)]
        buf.append({'buffer': b, **{k: float(np.mean([r[k] for r in rows])) for k in rows[0]}})
    res['buffer_test'] = buf
    return res


def run_drift(p_miss_list=(.005, .01, .02, .03), days=300, entries_per_day=900, stay_mean=100, ghost_timeout_h=5):
    """LPR plate-ledger drift. Missed entry => unseen car until it exits (transient undercount);
    missed exit => ghost car (overcount, safe direction) until timeout/night reset."""
    rng = np.random.default_rng(9); out = []
    for p in p_miss_list:
        unseen_max, ghost_max = [], []
        for _ in range(days):
            t_in = np.sort(rng.uniform(0, 780, entries_per_day))
            stay = np.maximum(15, rng.lognormal(math.log(87), .6, entries_per_day))
            t_out = t_in + stay
            missed_in = rng.random(entries_per_day) < p
            missed_out = rng.random(entries_per_day) < p
            grid = np.arange(0, 780 + 240, 5)
            unseen = np.array([np.sum(missed_in & (t_in <= x) & (t_out > x)) for x in grid])
            ghosts = np.array([np.sum(missed_out & (~missed_in) & (t_out <= x) & (x < t_out + ghost_timeout_h * 60)) for x in grid])
            unseen_max.append(unseen.max()); ghost_max.append(ghosts.max())
        out.append({'p_miss': p, 'unseen_p50': float(np.percentile(unseen_max, 50)), 'unseen_p99': float(np.percentile(unseen_max, 99)),
                    'ghost_p50': float(np.percentile(ghost_max, 50)), 'ghost_p99': float(np.percentile(ghost_max, 99))})
    return out


def run_monte_carlo(n=20000, seed=11):
    """Annual contribution distribution. Inputs are RANGES (assumption tier unless noted) and the
    capacity limit comes from the simulation sweep (served bookings saturate)."""
    rng = np.random.default_rng(seed)
    sweep = json.loads((OUT / 'results.json').read_text())['volume_sweep_200bays']
    xs = np.array([r['req_per_day'] for r in sweep], float)
    served = np.array([r['fulfilled'] + r['noshow'] + r['expired'] for r in sweep])  # accepted/day
    up = RUN  # annual running, derived in v3_costs.py
    capex = CAPEX  # upfront, derived in v3_costs.py
    res = []
    for _ in range(n):
        rpd = np.exp(rng.uniform(math.log(15), math.log(160)))   # booking requests/day (wide prior)
        accepted = np.interp(rpd, xs, served)
        s = rng.uniform(.2, .8)                                  # member share of bookers
        non_member_fee_share = (1 - s)
        fee_wk, fee_pk = rng.uniform(3, 6), rng.uniform(4, 8)    # anchored: RM4-5 plan; ParkEasy RM6-8
        wk_days, pk_days = 261, 104
        noshow = rng.uniform(.05, .20)
        # incremental per booking: nonmember fee; member excess over bill (~RM0 weekend, ~fee-3 weekday)
        member_exc_wk = max(0, fee_wk - 3.0); member_exc_pk = 0.4
        per_wk = (1 - s) * fee_wk + s * member_exc_wk
        per_pk = (1 - s) * fee_pk + s * member_exc_pk
        showed = accepted * (1 - noshow)
        gross = showed * (wk_days * per_wk + pk_days * per_pk)
        gross += accepted * noshow * (wk_days * fee_wk + pk_days * fee_pk)
        net = net_cash(gross, accepted)
        res.append(net - up)
    a = np.array(res)
    return {'n': n, 'p10': float(np.percentile(a, 10)), 'p50': float(np.percentile(a, 50)), 'p90': float(np.percentile(a, 90)),
            'prob_positive': float((a > 0).mean()), 'prob_5y_recovery': float((a > capex / 5).mean()),
            'prob_3y_recovery': float((a > capex / 3).mean())}


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    r = run_main(); r['lpr_drift'] = run_drift()
    (OUT / 'results.json').write_text(json.dumps(r, indent=2))
    r['monte_carlo'] = run_monte_carlo()
    (OUT / 'results.json').write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
