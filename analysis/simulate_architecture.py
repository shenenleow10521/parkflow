"""Architecture test v3: ML stay forecast inside the commitment planner.  Protocol: benchmarks/commitment/protocol_architecture.md
Run:  python -B analysis/simulate_architecture.py [smoke]
"""
import math, sys, os, json, time, warnings
warnings.filterwarnings("ignore")
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from scipy.special import ndtr
import lightgbm as lgb
from simulate_commitment import (OPEN, CLOSE, C, WINDOW, SHOW, CK, W_BOOK, PEAK_MID, PEAK_EVE, P_SIG, P_MU, M_SIG,
                                 DURS, DUR_P, DEMAND, BREACH_MAX, agg, pick, boot)

CAL_SEEDS, TEST_SEEDS = range(51000, 51150), range(63000, 63200)
TRAIN_SEEDS, VAL_SEEDS = range(70000, 70020), range(70020, 70030)
RHOS = [0.0, 0.15, 0.3, 0.5, 0.75]
ALPHA = np.array([0.0, -0.3, 0.7, -0.6])      # shop, dine, cinema, errand  (ASSUMED)
PUR_P = [0.5, 0.2, 0.15, 0.15]
P_OBS, RAIN_P, SHOCK = 0.7, 0.25, 0.15
EVE_MIN = 1020


def lam_curve():
    t = np.arange(OPEN, CLOSE)
    return t, (DEMAND["base"] + DEMAND["mid"] * np.exp(-0.5 * ((t - PEAK_MID) / 90) ** 2)
               + DEMAND["eve"] * np.exp(-0.5 * ((t - PEAK_EVE) / 100) ** 2))


@lru_cache(maxsize=None)
def g_norm():
    """Mean/sd of the raw feature effect over the arrival population, so rho is the true explained share."""
    rng = np.random.default_rng(1)
    t, lam = lam_curve()
    n = 200000
    m = rng.choice(t, n, p=lam / lam.sum()); p = rng.choice(4, n, p=PUR_P); r = rng.random(n) < RAIN_P
    g = ALPHA[p] + 0.5 * r + 0.4 * (m >= EVE_MIN)
    return g.mean(), g.std()


def unpack(rho):
    """rho is a float (nominal world) or a tuple (rho, show, shock_sd, stay_sigma_scale, booking_scale, pulse, overstay_sd, adv_share)."""
    if isinstance(rho, tuple):
        return rho
    return (rho, SHOW, SHOCK, 1.0, 1.0, 100, 0.25, 0.3)


def make_day(seed, rho):
    rho, show_p, shock_sd, ss, bscale, pulse_n, over_sd, adv_p = unpack(rho)
    msig = math.sqrt(math.log(1 + over_sd ** 2))
    rng = np.random.default_rng(seed)
    gm, gs = g_norm()
    shock = math.exp(rng.normal(-shock_sd ** 2 / 2, shock_sd))
    rain = int(rng.random() < RAIN_P)
    t, lam = lam_curve()
    pub = []   # (arrival, stay, purpose_observed, rain, minute)
    for m, n in zip(t, rng.poisson(lam)):
        for _ in range(n):
            p = int(rng.choice(4, p=PUR_P))
            g = (ALPHA[p] + 0.5 * rain + 0.4 * (m >= EVE_MIN) - gm) / gs
            ls = P_MU + math.sqrt(rho) * P_SIG * ss * g + math.sqrt(1 - rho) * P_SIG * ss * rng.normal()
            pub.append((int(m), max(15.0, math.exp(ls)) * shock, p if rng.random() < P_OBS else -1, rain, int(m)))
    mem = []

    def add(ws, d, lead):
        ws = int(ws)
        mem.append(dict(book=ws - lead, ws=ws, d=d, arr=ws + int(rng.triangular(-5, 5, WINDOW)),
                        stay=d * rng.lognormal(-msig ** 2 / 2, msig) * shock, show=rng.random() < show_p))
    for _ in range(rng.poisson(DEMAND["members"] * bscale)):
        ws = np.clip(rng.normal(PEAK_MID, 90) if rng.random() < 0.4 else rng.normal(PEAK_EVE + 60, 90), OPEN + 60, CLOSE - 90)
        adv = rng.random() < adv_p
        add(ws, int(rng.choice(DURS, p=DUR_P)), int(rng.integers(120, 1440) if adv else rng.integers(15, 120)))
    for _ in range(pulse_n):
        add(np.clip(rng.normal(1170, 25), OPEN + 60, CLOSE - 90), 165, int(rng.integers(180, 1440)))
    return pub, mem


def feats(pub):
    return np.array([[w[2], w[3], w[4]] for w in pub], float).reshape(-1, 3)


@lru_cache(maxsize=None)
def stay_models(rho):
    """Pooled lognormal and LightGBM log-stay model, fitted on training days only; residual sd from validation days."""
    def collect(seeds):
        X, y = [], []
        for s in seeds:
            pub, _ = make_day(s, rho)
            X.append(feats(pub)); y += [math.log(w[1]) for w in pub]
        return np.vstack(X), np.array(y)
    X, y = collect(TRAIN_SEEDS); Xv, yv = collect(VAL_SEEDS)
    m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=8, min_child_samples=50, verbose=-1, random_state=0, n_jobs=1)
    m.fit(X, y)
    res = yv - m.predict(Xv)
    return dict(mu0=float(y.mean()), sd0=float(y.std()), model=m, sd_ml=float(res.std()),
                r2=float(1 - res.var() / yv.var()))


def Phi_sf(mu, sd, x):
    return 1 - ndtr((np.log(np.maximum(x, 1e-6)) - mu) / sd)


def project(now, K, Wc, Bc, pend, ps=SHOW):
    """Wc: (entry, out, mu, sd) planner-belief walk-in cars."""
    taus = CK * np.arange(1, K + 1, dtype=float)
    T = now + taus
    mu, var = np.zeros(K), np.zeros(K)
    if Wc:
        a = np.maximum(now - np.array([c[0] for c in Wc], float), 1.0)
        m_ = np.array([c[2] for c in Wc])[:, None]; s_ = np.array([c[3] for c in Wc])[:, None]
        p = np.minimum(Phi_sf(m_, s_, a[:, None] + taus[None, :]) / np.maximum(Phi_sf(m_, s_, a[:, None]), 1e-6), 1.0)
        mu += p.sum(0); var += (p * (1 - p)).sum(0)
    if Bc:
        a = np.maximum(now - np.array([c[0] for c in Bc], float), 1.0)
        m_ = (np.log(np.array([c[2] for c in Bc], float)) - M_SIG ** 2 / 2)[:, None]
        p = np.minimum(Phi_sf(m_, M_SIG, a[:, None] + taus[None, :]) / np.maximum(Phi_sf(m_, M_SIG, a[:, None]), 1e-6), 1.0)
        mu += p.sum(0); var += (p * (1 - p)).sum(0)
    if pend:
        ws = np.array([x["ws"] for x in pend], float); d = np.array([x["d"] for x in pend], float)
        n = ((T[None, :] >= ws[:, None]) & (T[None, :] <= (ws + d + 15)[:, None])).sum(0)
        mu += ps * n; var += ps * (1 - ps) * n
    return T, mu, var


def project_oracle(now, K, Wc, Bc, pend):
    T = now + CK * np.arange(1, K + 1, dtype=float)
    mu = np.zeros(K)
    outs = [c[1] for c in Wc] + [c[1] for c in Bc]
    if outs:
        mu += (np.array(outs)[:, None] > T[None, :]).sum(0)
    for x in pend:
        if x["show"]:
            mu += (T >= x["arr"]) & (T <= x["arr"] + x["stay"])
    return T, mu, np.zeros(K)


def run(rho, cfg, seed):
    pub, mem = make_day(seed, rho)
    sm = stay_models(rho)
    n = len(pub)
    if cfg.get("model") == "ml" and n:
        mus = sm["model"].predict(feats(pub)); sds = np.full(n, sm["sd_ml"])
    else:
        mus = np.full(n, sm["mu0"]); sds = np.full(n, sm["sd0"])
    kind, H, z = cfg["kind"], cfg.get("H", 180), cfg.get("z", 0.0)
    ps, zb = cfg.get("ps", SHOW), cfg.get("zb", z)      # planned show-up prob of a booking (1.0 = hard constraint); booking-acceptance z
    Q, margin = cfg.get("Q", 10), cfg.get("margin", 0)
    by_book, by_arr, by_pub = {}, {}, {}
    for m in mem:
        by_book.setdefault(m["book"], []).append(m)
    for i, w in enumerate(pub):
        by_pub.setdefault(w[0], []).append((w[1], mus[i], sds[i]))
    Wc, Bc, pend, wait = [], [], [], []
    st = dict(honored=0, breach=0, acc=0, req=0, wi=0, den=0, den_free=0)
    cache = None
    t0 = min(min(by_book), OPEN) if by_book else OPEN
    for now in range(t0, CLOSE + WINDOW + 5):
        Wc = [c for c in Wc if c[1] > now]; Bc = [c for c in Bc if c[1] > now]
        pend = [x for x in pend if not (x["show"] and x["arr"] <= now) and now <= x["ws"] + WINDOW]
        for m in by_book.get(now, ()):
            st["req"] += 1
            if kind == "strict":
                ok = len(Wc) + len(Bc) + len(wait) + len(pend) < C
            elif kind in ("quota", "buffer"):
                ok = sum(1 for x in pend if abs(x["ws"] - m["ws"]) <= 60) < Q
            else:
                K = max(2, int((m["ws"] + m["d"] + 15 - now) / CK) + 2)
                bx = Bc + [(now, 0, w["d"]) for w in wait]
                T, mu, var = project_oracle(now, K, Wc, bx, pend) if kind == "oracle" else project(now, K, Wc, bx, pend, ps)
                k = (T >= m["ws"]) & (T <= m["ws"] + m["d"] + 15)
                ok = (not k.any()) or bool((mu[k] + ps + zb * np.sqrt(var[k] + ps * (1 - ps)) <= C).all())
                if ok and kind == "commit" and cfg.get("Qcap"):     # hybrid: also keep the quota rule's selective booking cap
                    ok = sum(1 for x in pend if abs(x["ws"] - m["ws"]) <= 60) < cfg["Qcap"]
            if ok:
                st["acc"] += 1; pend.append(m); cache = None
                if m["show"]:
                    by_arr.setdefault(m["arr"], []).append(m)
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
        for stay, mu_i, sd_i in by_pub.get(now, ()):
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
                    bx = Bc + [(now, 0, w["d"]) for w in wait]
                    T, mu, var = project_oracle(now, K, Wc, bx, pend) if kind == "oracle" else project(now, K, Wc, bx, pend, ps)
                    cache = [now, T, mu, var]
                _, T, mu, var = cache
                pn = (now + stay > T).astype(float) if kind == "oracle" else np.minimum(Phi_sf(mu_i, sd_i, np.maximum(T - now, 0.5)), 1.0)
                k = (T >= now) & (T <= now + Heff)
                admit = (not k.any()) or bool((mu[k] + pn[k] + z * np.sqrt(var[k] + pn[k] * (1 - pn[k])) <= C).all())
                if admit and cfg.get("hold"):      # layer 4: hard near-term hold for bookings due soon
                    free = C - len(Wc) - len(Bc) - len(wait)
                    due = sum(1 for x in pend if x["ws"] - now <= cfg["hold"])
                    admit = (free - due - cfg.get("swing", 0)) >= 1
                if admit:
                    cache[2] = mu + pn; cache[3] = var + pn * (1 - pn)
            if admit:
                Wc.append((now, now + stay, mu_i, sd_i)); st["wi"] += 1
            else:
                st["den"] += 1; st["den_free"] += int(phys)
    return st


def job(a):
    return run(*a)


def evaluate(pool, rho, cfgs, seeds):
    out = pool.map(job, [(rho, c, s) for c in cfgs for s in seeds], chunksize=4)
    n = len(seeds)
    return [out[i * n:(i + 1) * n] for i in range(len(cfgs))]


def sc(rs, w):
    return np.array([w * r["honored"] + r["wi"] for r in rs])


def study(pool, rho, smoke=False):
    cal = list(CAL_SEEDS)[:6] if smoke else list(CAL_SEEDS)
    test = list(TEST_SEEDS)[:10] if smoke else list(TEST_SEEDS)
    zs = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    Hs = [180, 300, 9999]
    quota = [dict(kind="quota", Q=q, margin=m) for q in (6, 10, 15, 25, 40, 60, 100) for m in (0, 2, 4, 6, 10, 15)]
    buf = [dict(kind="buffer", Q=q, margin=b) for q in (10, 25, 40, 60, 100) for b in (0, 5, 10, 15, 20, 30, 40)]
    cp = [dict(kind="commit", H=H, z=z, model="pooled") for H in Hs for z in zs]
    cm = [dict(kind="commit", H=H, z=z, model="ml") for H in Hs for z in zs]
    if smoke:
        quota, buf, zs = quota[::8], buf[::8], [0.0, 1.5]
        cp = [dict(kind="commit", H=H, z=z, model="pooled") for H in Hs for z in zs]
        cm = [dict(kind="commit", H=H, z=z, model="ml") for H in Hs for z in zs]
    groups = [quota, buf, cp, cm]
    cr = evaluate(pool, rho, sum(groups, []), cal)
    ch, off = [], 0
    for g in groups:
        ch.append(pick(g, cr[off:off + len(g)])); off += len(g)
    p0 = dict(kind="strict")
    p0cal = sc(evaluate(pool, rho, [p0], cal)[0], W_BOOK).mean()
    names = ["P0_strict", "P1_quota", "P1b_buffer", "C_pooled", "C_ml", "Oracle"]
    cfgs = [p0, ch[0][0], ch[1][0], ch[2][0], ch[3][0], dict(kind="oracle", H=9999)]
    tr = dict(zip(names, evaluate(pool, rho, cfgs, test)))
    cs = {"P0_strict": p0cal, "P1_quota": ch[0][1]["score"], "P1b_buffer": ch[1][1]["score"]}
    simple = max(cs, key=cs.get)
    res = {n: dict(cfg=c, test=agg(tr[n]), cal_ok=(ch[i - 1][2] if 1 <= i <= 4 else True)) for i, (n, c) in enumerate(zip(names, cfgs))}
    out = dict(res=res, simple=simple, r2=stay_models(rho)["r2"], sd_ml=stay_models(rho)["sd_ml"], sd0=stay_models(rho)["sd0"], diffs={})
    for w in (1, 5, 10):
        out["diffs"][w] = dict(ml_vs_simple=boot(sc(tr["C_ml"], w) - sc(tr[simple], w)),
                               pooled_vs_simple=boot(sc(tr["C_pooled"], w) - sc(tr[simple], w)),
                               ml_vs_pooled=boot(sc(tr["C_ml"], w) - sc(tr["C_pooled"], w)),
                               oracle_vs_pooled=boot(sc(tr["Oracle"], w) - sc(tr["C_pooled"], w)))
    return out


def md(results):
    L = ["# Architecture test v3: ML stay forecast in the commitment planner", "",
         "Synthetic (stay marginal calibrated to Mueller et al. 2026; feature effects assumed). 100 bays, advance bookings 30%, evening pulse 100, stay shock sd 0.15. "
         "Knobs tuned on 150 calibration days to breach <= 1%; test = 200 fresh days. `!` = test breach above 1%. Score = W x bookings honoured + walk-ins.", "",
         "## Summary by informativeness rho (share of log-stay variance explained by features)", "",
         "| rho | ML out-of-sample R^2 | Pooled commit score | ML commit score | Best simple | Oracle | ML - simple (W=5) | ML - pooled (W=5) | ML - simple W=1 | ML - simple W=10 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda t: f"{t[0]:+.1f} [{t[1]:+.1f}, {t[2]:+.1f}]"
    for rho, o in results.items():
        r = o["res"]; s = r[o["simple"]]["test"]; d = o["diffs"]
        L.append(f"| {rho} | {o['r2']:.2f} | {r['C_pooled']['test']['score']:.1f} | {r['C_ml']['test']['score']:.1f} | {s['score']:.1f} ({o['simple']}) | {r['Oracle']['test']['score']:.1f} | "
                 f"{f(d[5]['ml_vs_simple'])} | {f(d[5]['ml_vs_pooled'])} | {f(d[1]['ml_vs_simple'])} | {f(d[10]['ml_vs_simple'])} |")
    for rho, o in results.items():
        L += ["", f"## rho = {rho}  (ML R^2 {o['r2']:.2f}; residual sd {o['sd_ml']:.2f} vs pooled sd {o['sd0']:.2f})", "",
              "| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Chosen |", "|---|---|---|---|---|---|"]
        for n, x in o["res"].items():
            t, c = x["test"], x["cfg"]
            k = f"Q={c.get('Q')} m={c.get('margin')}" if c["kind"] in ("quota", "buffer") else (f"H={c.get('H')} z={c.get('z')}" if c["kind"] == "commit" else "")
            L.append(f"| {n} | {t['honored']:.1f} | {t['wi']:.1f} | {t['score']:.1f} | {100*t['breach']:.2f}%{' !' if t['breach'] > BREACH_MAX else ''} | {k} |")
    return "\n".join(L)


if __name__ == "__main__":
    smoke = "smoke" in sys.argv
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmarks", "commitment")
    rhos = [0.0, 0.5] if smoke else RHOS
    results, t0 = {}, time.time()
    with Pool(min(14, os.cpu_count() or 4)) as pool:
        for rho in rhos:
            results[rho] = study(pool, rho, smoke)
            print(f"rho={rho} done {time.time()-t0:.0f}s", flush=True)
    tag = "_smoke" if smoke else ""
    json.dump({str(k): v for k, v in results.items()}, open(os.path.join(outdir, f"results_arch{tag}.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    open(os.path.join(outdir, f"report_arch{tag}.md"), "w").write(md(results))
    print(md(results))
