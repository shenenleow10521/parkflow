"""v5: design variants (hard bookings, separate risk, hybrid) vs tuned rules, fresh seeds.  Protocol: Amendment v5.
Run: python -B analysis/simulate_v5.py [smoke]"""
import sys, os, json, time, warnings
warnings.filterwarnings("ignore")
from multiprocessing import Pool
import numpy as np
from simulate_architecture import evaluate, stay_models, CAL_SEEDS
from simulate_commitment import agg, boot, W_BOOK

TEST_SEEDS = range(65000, 65200)
TARGETS = [0.01, 0.005, 0.001]


def stats(rs):
    a = agg(rs)
    a["bpd"] = float(np.mean([r["breach"] for r in rs]))
    for c in (2, 10, 25):
        a[f"s{c}"] = a["score"] - c * a["bpd"]
    return a


def day_scores(rs, c=0):
    return np.array([W_BOOK * r["honored"] + r["wi"] - c * r["breach"] for r in rs])


def choose(cfgs, runs, target):
    a = [stats(r) for r in runs]
    ok = [i for i, x in enumerate(a) if x["breach"] <= target / 2]
    i = max(ok, key=lambda i: a[i]["score"]) if ok else min(range(len(a)), key=lambda i: a[i]["breach"])
    return cfgs[i], bool(ok)


def families(smoke):
    q = [dict(kind="quota", Q=Q, margin=m) for Q in (6, 10, 15, 25, 40, 60, 100) for m in (0, 2, 4, 6, 10, 15)]
    b = [dict(kind="buffer", Q=Q, margin=m) for Q in (10, 25, 40, 60, 100) for m in (0, 5, 10, 15, 20, 30, 40)]
    c = lambda **k: dict(kind="commit", model="ml", **k)
    v0 = [c(H=H, z=z, ps=0.9) for H in (300, 480) for z in (0, 1, 2)]
    v1 = [c(H=H, z=z, ps=1.0) for H in (300, 480) for z in (0, 1, 2)]
    v2 = [c(H=H, z=z, zb=zb, ps=ps) for H in (300, 480) for z in (0, 1, 2) for zb in (0, 1, 2, 3) for ps in (0.9, 1.0)]
    v3 = [c(H=480, z=z, zb=zb, ps=ps, Qcap=Qc) for z in (0, 1, 2) for zb in (0, 1, 2) for ps in (0.9, 1.0) for Qc in (40, 60)]
    fam = {"quota": q, "buffer": b, "V0_reference": v0, "V1_hard_bookings": v1, "V2_separate_risk": v2, "V3_hybrid": v3}
    if smoke:
        fam = {k: v[::max(1, len(v) // 4)] for k, v in fam.items()}
    return fam


def study(pool, rho, smoke):
    cal = list(CAL_SEEDS)[:6] if smoke else list(CAL_SEEDS)
    test = list(TEST_SEEDS)[:10] if smoke else list(TEST_SEEDS)
    fam = families(smoke)
    allc = sum(fam.values(), [])
    cr = evaluate(pool, rho, allc, cal)
    runs, off = {}, 0
    for k, g in fam.items():
        runs[k] = cr[off:off + len(g)]; off += len(g)
    picks = {(t, k): choose(g, runs[k], t) for t in TARGETS for k, g in fam.items()}
    uniq, idx = [], {}
    for c, ok in picks.values():
        s = json.dumps(c, sort_keys=True)
        if s not in idx:
            idx[s] = len(uniq); uniq.append(c)
    extra = [dict(kind="strict"), dict(kind="oracle", H=9999)]
    tr = evaluate(pool, rho, uniq + extra, test)
    out = dict(r2=stay_models(rho)["r2"], n_configs=len(allc), res={}, diff={})
    for (t, k), (c, ok) in picks.items():
        r = tr[idx[json.dumps(c, sort_keys=True)]]
        out["res"][f"{t}|{k}"] = dict(cfg=c, cal_ok=ok, test=stats(r))
    for t in TARGETS:
        base = tr[idx[json.dumps(picks[(t, "quota")][0], sort_keys=True)]]
        for k in fam:
            if k.startswith("V"):
                r = tr[idx[json.dumps(picks[(t, k)][0], sort_keys=True)]]
                out["diff"][f"{t}|{k}"] = dict(score=boot(day_scores(r) - day_scores(base)),
                                               fail=boot(np.array([x["breach"] for x in r]) - np.array([x["breach"] for x in base])),
                                               s2=boot(day_scores(r, 2) - day_scores(base, 2)), s10=boot(day_scores(r, 10) - day_scores(base, 10)))
    out["res"]["P0_strict"] = dict(cfg=extra[0], test=stats(tr[-2])); out["res"]["Oracle"] = dict(cfg=extra[1], test=stats(tr[-1]))
    return out


def knob(c):
    if c["kind"] in ("quota", "buffer"):
        return f"Q={c['Q']} m={c['margin']}"
    s = f"H={c['H']} z={c['z']} zb={c.get('zb', c['z'])} ps={c.get('ps')}"
    return s + (f" Qcap={c['Qcap']}" if c.get("Qcap") else "")


def md(results):
    L = ["# v5: design variants vs tuned rules (fresh seeds)", "",
         "Synthetic; protocol_architecture.md Amendment v5. Selected on 150 calibration days (calibration failures <= half the target); test = 200 fresh days. "
         "`!` = test failure rate above the target. s2/s10/s25 = score minus 2/10/25 per failed booking (s2 ~ fallback + refund). Diffs are variant minus tuned quota rule, paired, 95% interval.", ""]
    f = lambda t: f"{t[0]:+.1f} [{t[1]:+.1f}, {t[2]:+.1f}]"
    for rho, o in results.items():
        L += [f"## rho = {rho} (ML R^2 {o['r2']:.2f}); {o['n_configs']} configs searched", ""]
        for t in TARGETS:
            L += [f"### Failure target {100*t:.1f}%", "", "| Policy | Honoured | Walk-ins | Test failures | Failures/day | Score | s2 | s10 | s25 | Chosen |", "|---|---|---|---|---|---|---|---|---|---|"]
            for k in ("quota", "buffer", "V0_reference", "V1_hard_bookings", "V2_separate_risk", "V3_hybrid"):
                x = o["res"][f"{t}|{k}"]; s = x["test"]
                L.append(f"| {k} | {s['honored']:.1f} | {s['wi']:.1f} | {100*s['breach']:.2f}%{' !' if s['breach'] > t else ''} | {s['bpd']:.2f} | {s['score']:.1f} | {s['s2']:.1f} | {s['s10']:.1f} | {s['s25']:.1f} | {knob(x['cfg'])}{'' if x['cal_ok'] else ' (infeasible on calibration)'} |")
            L += ["", "| Variant minus quota | Score | Failures/day | s2 | s10 |", "|---|---|---|---|---|"]
            for k in ("V0_reference", "V1_hard_bookings", "V2_separate_risk", "V3_hybrid"):
                d = o["diff"][f"{t}|{k}"]
                L.append(f"| {k} | {f(d['score'])} | {f(d['fail'])} | {f(d['s2'])} | {f(d['s10'])} |")
            L.append("")
        for n in ("P0_strict", "Oracle"):
            s = o["res"][n]["test"]
            L.append(f"{n}: honoured {s['honored']:.1f}, walk-ins {s['wi']:.1f}, failures {100*s['breach']:.2f}%, score {s['score']:.1f}  ")
    return "\n".join(L)


if __name__ == "__main__":
    smoke = "smoke" in sys.argv
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmarks", "commitment")
    results, t0 = {}, time.time()
    with Pool(min(14, os.cpu_count() or 4)) as pool:
        for rho in ([0.5] if smoke else [0.5, 0.0]):
            results[rho] = study(pool, rho, smoke)
            print(f"rho={rho} done {time.time()-t0:.0f}s", flush=True)
    tag = "_smoke" if smoke else ""
    open(os.path.join(outdir, f"report_v5{tag}.md"), "w").write(md(results))
    json.dump({str(k): v for k, v in results.items()}, open(os.path.join(outdir, f"results_v5{tag}.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(md(results))
