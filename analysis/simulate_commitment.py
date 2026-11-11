"""Commitment ledger + stay-risk admission: does it beat simple rules as the environment gets complex?

Protocol (written before any result): benchmarks/commitment/protocol.md
Run:  python -B analysis/simulate_commitment.py [smoke]      (writes benchmarks/commitment/results.json + report.md)
"""
import math, sys, json, os, time, itertools
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from scipy.special import ndtr

OPEN, CLOSE = 600, 1380          # 10:00-23:00
C, WINDOW, SHOW, CK = 100, 30, 0.9, 15
W_BOOK = 5                       # declared service weight, as in the decision-value study
PEAK_MID, PEAK_EVE = 750, 1050   # Sun et al. (2025)
# walk-in stay: lognormal fitted to Mueller et al. (2026) quartiles 44/87/155 min
P_SIG = math.log(155 / 44) / (2 * 0.6745)
P_MU = math.log(87)
M_SIG = math.sqrt(math.log(1 + 0.25 ** 2))     # booked stay = declared duration x noise
DURS, DUR_P = [60, 90, 120, 150, 180, 240], [0.1, 0.15, 0.25, 0.2, 0.2, 0.1]
DEMAND = dict(base=0.48, mid=0.36, eve=0.84, members=60)
LONG_MU, LONG_SIG, LABEL_ACC = math.log(240), 0.5, 0.7   # ASSUMED long-stay tail (L3 only)
LEVELS = {
    "L0": dict(adv=0.0, pulse=0, long=0.0, shock=0.0),
    "L1": dict(adv=0.3, pulse=0, long=0.0, shock=0.0),
    "L2": dict(adv=0.3, pulse=100, long=0.0, shock=0.0),
    "L3": dict(adv=0.3, pulse=100, long=0.2, shock=0.15),
}
CAL_SEEDS = range(51000, 51150)      # v2: 150 days (v1 used 60 and breach selection was unstable)
TEST_SEEDS = range(62000, 62200)     # v2: fresh seeds (v1 used 61000-61199)
TRAIN_SEEDS = range(70000, 70020)
BREACH_MAX = 0.01


def make_day(seed, lv):
    rng = np.random.default_rng(seed)
    L = LEVELS[lv]
    shock = math.exp(rng.normal(-L["shock"] ** 2 / 2, L["shock"])) if L["shock"] else 1.0
    t = np.arange(OPEN, CLOSE)
    lam = (DEMAND["base"] + DEMAND["mid"] * np.exp(-0.5 * ((t - PEAK_MID) / 90) ** 2)
           + DEMAND["eve"] * np.exp(-0.5 * ((t - PEAK_EVE) / 100) ** 2))
    pub = []   # (arrival, stay, label)  label: 0 std, 1 long, -1 unknown
    for m, n in zip(t, rng.poisson(lam)):
        for _ in range(n):
            if rng.random() < L["long"]:
                typ, st = 1, rng.lognormal(LONG_MU, LONG_SIG)
            else:
                typ, st = 0, max(15.0, rng.lognormal(P_MU, P_SIG))
            pub.append((int(m), st * shock, typ if rng.random() < LABEL_ACC else -1))
    mem = []   # dict: book, ws, d, arr, stay, show

    def add(ws, d, lead):
        ws = int(ws)
        mem.append(dict(book=ws - lead, ws=ws, d=d, arr=ws + int(rng.triangular(-5, 5, WINDOW)),
                        stay=d * rng.lognormal(-M_SIG ** 2 / 2, M_SIG) * shock, show=rng.random() < SHOW))
    for _ in range(rng.poisson(DEMAND["members"])):
        ws = np.clip(rng.normal(PEAK_MID, 90) if rng.random() < 0.4 else rng.normal(PEAK_EVE + 60, 90), OPEN + 60, CLOSE - 90)
        adv = rng.random() < L["adv"]
        add(ws, int(rng.choice(DURS, p=DUR_P)), int(rng.integers(120, 1440) if adv else rng.integers(15, 120)))
    for _ in range(L["pulse"]):
        add(np.clip(rng.normal(1170, 25), OPEN + 60, CLOSE - 90), 165, int(rng.integers(180, 1440)))
    return pub, mem


@lru_cache(maxsize=None)
def belief(lv):
    """Empirical stay model the planner fits from 20 separate training days (never the true distribution)."""
    allst, byc = [], {0: [], 1: []}
    for s in TRAIN_SEEDS:
        for _, st, lab in make_day(s, lv)[0]:
            allst.append(st)
            if lab >= 0:
                byc[lab].append(st)
    pooled = np.sort(allst)
    return {-1: pooled, 0: np.sort(byc[0]) if len(byc[0]) > 50 else pooled, 1: np.sort(byc[1]) if len(byc[1]) > 50 else pooled}


def surv(s, x):
    return 1 - np.searchsorted(s, x, side="right") / len(s)


def project(now, K, Wc, Bc, pend, bel, signal):
    """Expected and variance of occupancy at checkpoints now+15k, from parked cars + the booking ledger."""
    taus = CK * np.arange(1, K + 1, dtype=float)
    T = now + taus
    mu, var = np.zeros(K), np.zeros(K)
    if Wc:
        age = now - np.array([c[0] for c in Wc], float)
        lab = np.array([c[2] for c in Wc])
        grp = np.where(lab >= 0, lab, -1) if signal else np.full(len(lab), -1)
        for g in np.unique(grp):
            a, s = age[grp == g], bel[g]
            sa = np.maximum(surv(s, a), 1.0 / len(s))
            p = np.minimum(surv(s, a[:, None] + taus[None, :]) / sa[:, None], 1.0)
            mu += p.sum(0); var += (p * (1 - p)).sum(0)
    if Bc:
        a = np.maximum(now - np.array([c[0] for c in Bc], float), 1.0)
        m = np.log(np.array([c[2] for c in Bc], float)) - M_SIG ** 2 / 2
        fa = ndtr((np.log(a) - m) / M_SIG)
        ft = ndtr((np.log(a[:, None] + taus[None, :]) - m[:, None]) / M_SIG)
        p = np.minimum((1 - ft) / np.maximum(1 - fa[:, None], 1e-6), 1.0)
        mu += p.sum(0); var += (p * (1 - p)).sum(0)
    if pend:
        ws = np.array([x["ws"] for x in pend], float); d = np.array([x["d"] for x in pend], float)
        n = ((T[None, :] >= ws[:, None]) & (T[None, :] <= (ws + d + 15)[:, None])).sum(0)
        mu += SHOW * n; var += SHOW * (1 - SHOW) * n
    return T, mu, var


def project_oracle(now, K, Wc, Bc, pend):
    T = now + CK * np.arange(1, K + 1, dtype=float)
    mu = np.zeros(K); var = np.zeros(K)
    outs = [c[1] for c in Wc] + [c[1] for c in Bc]
    if outs:
        mu += (np.array(outs)[:, None] > T[None, :]).sum(0)
    for x in pend:
        if x["show"]:
            mu += (T >= x["arr"]) & (T <= x["arr"] + x["stay"])
    return T, mu, var


def run(lv, cfg, seed):
    pub, mem = make_day(seed, lv)
    bel = belief(lv)
    kind, H, z = cfg["kind"], cfg.get("H", 180), cfg.get("z", 0.0)
    Q, margin, signal = cfg.get("Q", 10), cfg.get("margin", 0), cfg.get("signal", False)
    by_book, by_arr, by_pub = {}, {}, {}
    for m in mem:
        by_book.setdefault(m["book"], []).append(m)
    for a in pub:
        by_pub.setdefault(a[0], []).append(a)
    Wc, Bc, pend, wait = [], [], [], []     # walk-in cars (entry,out,label); booking cars (entry,out,d); pending ledger; waiting arrivals
    st = dict(honored=0, breach=0, acc=0, req=0, wi=0, den=0, den_free=0)
    cache = None
    t0 = min(min(by_book), OPEN) if by_book else OPEN
    for now in range(t0, CLOSE + WINDOW + 5):
        Wc = [c for c in Wc if c[1] > now]; Bc = [c for c in Bc if c[1] > now]
        pend = [x for x in pend if not (x["show"] and x["arr"] <= now) and now <= x["ws"] + WINDOW]
        # booking requests
        for m in by_book.get(now, ()):
            st["req"] += 1
            if kind == "strict":
                ok = len(Wc) + len(Bc) + len(wait) + len(pend) < C
            elif kind in ("quota", "buffer"):
                ok = sum(1 for x in pend if abs(x["ws"] - m["ws"]) <= 60) < Q
            else:
                K = max(2, int((m["ws"] + m["d"] + 15 - now) / CK) + 2)
                T, mu, var = (project_oracle(now, K, Wc, Bc, pend) if kind == "oracle" else project(now, K, Wc, Bc + [(now, 0, w["d"]) for w in wait], pend, bel, signal))
                k = (T >= m["ws"]) & (T <= m["ws"] + m["d"] + 15)
                ok = (not k.any()) or bool((mu[k] + SHOW + z * np.sqrt(var[k] + SHOW * (1 - SHOW)) <= C).all())
            if ok:
                st["acc"] += 1; pend.append(m); cache = None
                if m["show"]:
                    by_arr.setdefault(m["arr"], []).append(m)   # only accepted bookings ever arrive
        # booked arrivals (waiting list first so earlier arrivals keep priority)
        for m in by_arr.get(now, ()):
            wait.append(m)
        nw = []
        for m in wait:
            if len(Wc) + len(Bc) < C:
                Bc.append((now, now + m["stay"], m["d"])); st["honored"] += 1
            elif now >= m["arr"] + WINDOW:
                st["breach"] += 1
            else:
                nw.append(m)
        wait = nw
        # walk-ins
        for _, stay, lab in by_pub.get(now, ()):
            phys = len(Wc) + len(Bc) + len(wait) < C
            if not phys:
                admit = False
            elif kind == "strict":
                admit = len(Wc) + len(Bc) + len(wait) + len(pend) < C
            elif kind == "buffer":
                admit = (C - len(Wc) - len(Bc) - len(wait) - margin) >= 1
            elif kind == "quota":
                due = sum(1 for x in pend if x["ws"] - now <= 60)
                admit = (C - len(Wc) - len(Bc) - len(wait) - due - margin) >= 1
            else:
                Heff = max(CK, min(H, CLOSE + 300 - now))
                if cache is None or now - cache[0] >= 5:
                    K = int((Heff + 5) / CK) + 2
                    T, mu, var = (project_oracle(now, K, Wc, Bc, pend) if kind == "oracle" else project(now, K, Wc, Bc + [(now, 0, w["d"]) for w in wait], pend, bel, signal))
                    cache = [now, T, mu, var]
                _, T, mu, var = cache
                if kind == "oracle":
                    pn = (now + stay > T).astype(float)
                else:
                    s = bel[lab] if (signal and lab >= 0) else bel[-1]
                    pn = surv(s, np.maximum(T - now, 0.0))
                k = (T >= now) & (T <= now + Heff)
                admit = (not k.any()) or bool((mu[k] + pn[k] + z * np.sqrt(var[k] + pn[k] * (1 - pn[k])) <= C).all())
                if admit:
                    cache[2] = mu + pn; cache[3] = var + pn * (1 - pn)
            if admit:
                Wc.append((now, now + stay, lab)); st["wi"] += 1
            else:
                st["den"] += 1; st["den_free"] += int(phys)
    return st


def job(a):
    lv, cfg, seed = a
    r = run(lv, cfg, seed)
    return r


def agg(rs):
    sh = sum(r["honored"] + r["breach"] for r in rs)
    return dict(honored=np.mean([r["honored"] for r in rs]), wi=np.mean([r["wi"] for r in rs]),
                breach=sum(r["breach"] for r in rs) / max(sh, 1), acc=np.mean([r["acc"] for r in rs]),
                req=np.mean([r["req"] for r in rs]), den_free=np.mean([r["den_free"] for r in rs]),
                score=np.mean([W_BOOK * r["honored"] + r["wi"] for r in rs]))


def evaluate(pool, lv, cfgs, seeds):
    jobs = [(lv, c, s) for c in cfgs for s in seeds]
    out = pool.map(job, jobs, chunksize=4)
    n = len(seeds)
    return [out[i * n:(i + 1) * n] for i in range(len(cfgs))]


def pick(cfgs, runs):
    """best calibration score subject to breach <= 1%; fallback = lowest breach."""
    a = [agg(r) for r in runs]
    ok = [i for i, x in enumerate(a) if x["breach"] <= BREACH_MAX]
    i = max(ok, key=lambda i: a[i]["score"]) if ok else min(range(len(a)), key=lambda i: a[i]["breach"])
    return cfgs[i], a[i], bool(ok)


def boot(d, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    d = np.asarray(d, float)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def study(pool, lv, signal, smoke=False):
    cal = list(CAL_SEEDS)[:6] if smoke else list(CAL_SEEDS)
    test = list(TEST_SEEDS)[:10] if smoke else list(TEST_SEEDS)
    Hs = [60, 120, 180, 300, 480, 9999]
    zs = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    quota_grid = [dict(kind="quota", Q=q, margin=m) for q in (6, 10, 15, 25, 40, 60, 100) for m in (0, 2, 4, 6, 10, 15)]
    buffer_grid = [dict(kind="buffer", Q=q, margin=b) for q in (10, 25, 40, 60, 100) for b in (0, 5, 10, 15, 20, 30, 40)]
    commit_grid = {H: [dict(kind="commit", H=H, z=z, signal=signal) for z in zs] for H in Hs}
    if smoke:
        quota_grid, buffer_grid, Hs, zs = quota_grid[::6], buffer_grid[::5], [180, 9999], [0.0, 1.5]
        commit_grid = {H: [dict(kind="commit", H=H, z=z, signal=signal) for z in zs] for H in Hs}
    chosen = {}
    allc = quota_grid + buffer_grid + [c for H in Hs for c in commit_grid[H]]
    cr = evaluate(pool, lv, allc, cal)
    ca = dict(zip(range(len(allc)), cr))
    chosen["P1_quota"] = pick(quota_grid, cr[:len(quota_grid)])
    nq = len(quota_grid)
    chosen["P1b_buffer"] = pick(buffer_grid, cr[nq:nq + len(buffer_grid)])
    off = nq + len(buffer_grid)
    for H in Hs:
        n = len(commit_grid[H])
        chosen[f"P3_H{H}"] = pick(commit_grid[H], cr[off:off + n]); off += n
    fixed = {"P0_strict": dict(kind="strict"), "P2_expected_H180": dict(kind="commit", H=180, z=0.0, signal=signal),
             "P4_fullinfo": dict(kind="oracle", H=9999, z=0.0)}
    names = list(fixed) + list(chosen)
    cfgs = [fixed[n] for n in fixed] + [chosen[n][0] for n in chosen]
    tr = evaluate(pool, lv, cfgs, test)
    res = {n: dict(cfg=c, test=agg(r), cal_feasible=(chosen[n][2] if n in chosen else True)) for n, c, r in zip(names, cfgs, tr)}
    sc = {n: np.array([W_BOOK * r["honored"] + r["wi"] for r in rs]) for n, rs in zip(names, tr)}
    cs = {n: chosen[n][1]["score"] for n in chosen}
    # simple comparator: better of P0/P1 on CALIBRATION (P0 calibration score from its own runs)
    p0cal = np.mean([W_BOOK * r["honored"] + r["wi"] for r in evaluate(pool, lv, [fixed["P0_strict"]], cal)[0]])
    cs["P0_strict"] = p0cal
    simple = max(["P0_strict", "P1_quota", "P1b_buffer"], key=lambda n: cs[n])
    thr = [n for n in chosen if n.startswith("P3") and res[n]["test"]["breach"] <= BREACH_MAX * 1.5]
    best3 = max([n for n in chosen if n.startswith("P3")], key=lambda n: cs[n])
    out = dict(res=res, simple=simple, best_commit_by_cal=best3)
    out["diff_best_commit_vs_simple"] = boot(sc[best3] - sc[simple])
    out["diff_H180_vs_simple"] = boot(sc["P3_H180"] - sc[simple])
    out["diff_H9999_vs_H180"] = boot(sc["P3_H9999"] - sc["P3_H180"]) if "P3_H9999" in sc and "P3_H180" in sc else None
    return out


def md(results):
    L = ["# Commitment-ledger + stay-risk admission: results", "",
         "Synthetic, 100 bays. See protocol.md for calibration vs assumptions. Score = 5 x bookings honoured + walk-ins admitted. Breach = shown-up booking with no bay within 30 min. "
         "Knobs tuned on calibration days to breach <= 1%; test breach shown (flagged with ! if above 1%).", ""]
    for key, o in results.items():
        L += [f"## {key}", "", "| Policy | Honoured/day | Walk-ins/day | Score (W=5) | Score W=1 | Score W=10 | Test breach | Walk-ins denied with a free bay/day | Chosen knob |", "|---|---|---|---|---|---|---|---|---|"]
        for n, r in o["res"].items():
            t, c = r["test"], r["cfg"]
            knob = f"Q={c.get('Q')} margin={c.get('margin')}" if c["kind"] in ("quota", "buffer") else (f"z={c.get('z')}" if c["kind"] in ("commit", "oracle") else "")
            flag = " !" if t["breach"] > BREACH_MAX else ""
            L.append(f"| {n} | {t['honored']:.1f} | {t['wi']:.1f} | {t['score']:.1f} | {t['honored']+t['wi']:.1f} | {10*t['honored']+t['wi']:.1f} | {100*t['breach']:.2f}%{flag} | {t['den_free']:.1f} | {knob} |")
        d, lo, hi = o["diff_best_commit_vs_simple"]
        d2 = o["diff_H180_vs_simple"]
        L += ["", f"Simple comparator (better on calibration): **{o['simple']}**. Best commit policy on calibration: **{o['best_commit_by_cal']}**.",
              f"Paired score difference, best commit minus simple: **{d:+.1f}/day** (95% CI {lo:+.1f} to {hi:+.1f}). Fixed 3-hour commit minus simple: {d2[0]:+.1f} ({d2[1]:+.1f} to {d2[2]:+.1f}).",
              ""]
        sm = o["res"][o["simple"]]["test"]
        for n, r in o["res"].items():
            if n.startswith("P3") and r["test"]["breach"] <= BREACH_MAX:
                db, dw = r["test"]["honored"] - sm["honored"], r["test"]["wi"] - sm["wi"]
                be = (-dw / db) if db > 0 and dw < 0 else None
                L.append(f"- {n} vs {o['simple']}: {db:+.1f} bookings/day, {dw:+.1f} walk-ins/day" + (f"; break-even booking weight = {be:.1f} (commit wins only if a booking is worth more than this many walk-ins)." if be else "."))
        L.append("")
        if o.get("diff_H9999_vs_H180"):
            e = o["diff_H9999_vs_H180"]
            L += [f"End-of-day horizon minus 3-hour horizon: {e[0]:+.1f}/day ({e[1]:+.1f} to {e[2]:+.1f}).", ""]
    return "\n".join(L)


if __name__ == "__main__":
    smoke = "smoke" in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "benchmarks", "commitment")
    settings = [("L0", "L0", False), ("L1", "L1", False), ("L2", "L2", False), ("L3 no class signal", "L3", False), ("L3 with class signal", "L3", True)]
    if smoke:
        settings = settings[:1] + settings[3:4]
    results, t0 = {}, time.time()
    with Pool(min(14, os.cpu_count() or 4)) as pool:
        for name, lv, sig in settings:
            results[name] = study(pool, lv, sig, smoke)
            print(f"{name} done {time.time()-t0:.0f}s", flush=True)
    tag = "_smoke" if smoke else ""
    json.dump(results, open(os.path.join(outdir, f"results{tag}.json"), "w"), indent=1, default=float)
    open(os.path.join(outdir, f"report{tag}.md"), "w").write(md(results))
    print(md(results))
