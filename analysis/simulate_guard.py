"""v4: does a hard near-term hold (architecture layer 4) and a longer horizon bring booking failures near zero, and at what cost?
Protocol: benchmarks/commitment/protocol_architecture.md (Amendment v4).   Run: python -B analysis/simulate_guard.py [smoke]
"""
import sys, os, json, time, warnings
warnings.filterwarnings("ignore")
from multiprocessing import Pool
import numpy as np
from simulate_architecture import evaluate, stay_models, CAL_SEEDS
from simulate_commitment import agg, W_BOOK

TEST_SEEDS = range(64000, 64200)
TARGETS = [0.01, 0.005, 0.001]
THRESH = [0.02, 0.01, 0.005, 0.0025, 0.001, 0.0005]


def stats(rs):
    a = agg(rs)
    a["bpd"] = float(np.mean([r["breach"] for r in rs]))
    for c in (10, 25):
        a[f"s{c}"] = a["score"] - c * a["bpd"]
    return a


def choose(cfgs, runs, target):
    a = [stats(r) for r in runs]
    ok = [i for i, x in enumerate(a) if x["breach"] <= target / 2]
    i = max(ok, key=lambda i: a[i]["score"]) if ok else min(range(len(a)), key=lambda i: a[i]["breach"])
    return cfgs[i], bool(ok)


def study(pool, rho, smoke):
    cal = list(CAL_SEEDS)[:6] if smoke else list(CAL_SEEDS)
    test = list(TEST_SEEDS)[:10] if smoke else list(TEST_SEEDS)
    quota = [dict(kind="quota", Q=q, margin=m) for q in (6, 10, 15, 25, 40, 60, 100) for m in (0, 2, 4, 6, 10, 15)]
    buf = [dict(kind="buffer", Q=q, margin=b) for q in (10, 25, 40, 60, 100) for b in (0, 5, 10, 15, 20, 30, 40)]
    zs, Hs = [0.0, 1.0, 2.0], [180, 300, 480]
    nohold = [dict(kind="commit", model="ml", H=H, z=z) for H in Hs for z in zs]
    hold = [dict(kind="commit", model="ml", H=H, z=z, hold=h, swing=s) for H in Hs for z in zs for h in (60, 90) for s in (0, 2, 4)]
    if smoke:
        quota, buf, hold, nohold = quota[::10], buf[::10], hold[::9], nohold[::4]
    fam = dict(quota=quota, buffer=buf, commit_nohold=nohold, commit_hold=hold)
    allc = sum(fam.values(), [])
    cr = evaluate(pool, rho, allc, cal)
    runs, off = {}, 0
    for k, g in fam.items():
        runs[k] = cr[off:off + len(g)]; off += len(g)
    # frontier from calibration
    frontier = {}
    for k, g in fam.items():
        a = [stats(r) for r in runs[k]]
        frontier[k] = {}
        for t in THRESH:
            ok = [x for x in a if x["breach"] <= t]
            frontier[k][t] = max(ok, key=lambda x: x["score"]) if ok else None
    # selection per target and test
    picks = {}
    for t in TARGETS:
        for k, g in fam.items():
            picks[(t, k)] = choose(g, runs[k], t)
    uniq, idx = [], {}
    for key, (c, ok) in picks.items():
        s = json.dumps(c, sort_keys=True)
        if s not in idx:
            idx[s] = len(uniq); uniq.append(c)
    extra = [dict(kind="strict"), dict(kind="oracle", H=9999)]
    tr = evaluate(pool, rho, uniq + extra, test)
    res = {}
    for (t, k), (c, ok) in picks.items():
        res[f"{t}|{k}"] = dict(cfg=c, cal_ok=ok, test=stats(tr[idx[json.dumps(c, sort_keys=True)]]))
    res["P0_strict"] = dict(cfg=extra[0], test=stats(tr[-2])); res["Oracle"] = dict(cfg=extra[1], test=stats(tr[-1]))
    return dict(res=res, frontier=frontier, r2=stay_models(rho)["r2"])


def knob(c):
    if c["kind"] in ("quota", "buffer"):
        return f"Q={c['Q']} m={c['margin']}"
    if c["kind"] == "commit":
        return f"H={c['H']} z={c['z']}" + (f" hold={c['hold']} swing={c['swing']}" if c.get("hold") else " no hold")
    return ""


def md(results):
    L = ["# v4: safety guard and horizon", "",
         "Synthetic; see protocol_architecture.md (Amendment v4). Selection on 150 calibration days with calibration breach <= half the target; test = 200 fresh days. "
         "`!` = test breach above the target. s10/s25 = score minus 10 or 25 per failed booking. A failure counts as a failure; fallback to another level is not modelled.", ""]
    for rho, o in results.items():
        L += [f"## rho = {rho} (ML R^2 {o['r2']:.2f})", "", "### Frontier from calibration days: best score at each failure ceiling", "",
              "| Failure ceiling | " + " | ".join(o["frontier"]) + " |", "|---|" + "---|" * len(o["frontier"])]
        for t in THRESH:
            cells = []
            for k in o["frontier"]:
                x = o["frontier"][k][t]
                cells.append("none" if x is None else f"{x['score']:.0f} ({x['honored']:.0f} bk / {x['wi']:.0f} wi, {100*x['breach']:.2f}%)")
            L.append(f"| <= {100*t:.2f}% | " + " | ".join(cells) + " |")
        for t in TARGETS:
            L += ["", f"### Target {100*t:.1f}% failures (test)", "",
                  "| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |", "|---|---|---|---|---|---|---|---|---|"]
            for k in ("quota", "buffer", "commit_nohold", "commit_hold"):
                x = o["res"][f"{t}|{k}"]; s = x["test"]
                L.append(f"| {k} | {s['honored']:.1f} | {s['wi']:.1f} | {100*s['breach']:.2f}%{' !' if s['breach'] > t else ''} | {s['bpd']:.2f} | {s['score']:.1f} | {s['s10']:.1f} | {s['s25']:.1f} | {knob(x['cfg'])}{'' if x['cal_ok'] else ' (infeasible)'} |")
        for n in ("P0_strict", "Oracle"):
            s = o["res"][n]["test"]
            L.append(f"\n{n}: honoured {s['honored']:.1f}, walk-ins {s['wi']:.1f}, breach {100*s['breach']:.2f}%, score {s['score']:.1f}")
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
    open(os.path.join(outdir, f"report_guard{tag}.md"), "w").write(md(results))
    json.dump({str(k): v for k, v in results.items()}, open(os.path.join(outdir, f"results_guard{tag}.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(md(results))
