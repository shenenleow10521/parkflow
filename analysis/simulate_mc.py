"""v6: Monte Carlo over assumptions. 60 random "worlds"; policy settings are the nominal-world v5 picks and are NOT retuned.
Protocol: benchmarks/commitment/protocol_architecture.md (Amendment v6). Needs results_v5.json.   Run: python -B analysis/simulate_mc.py [smoke]
"""
import sys, os, json, time, warnings
warnings.filterwarnings("ignore")
from multiprocessing import Pool
import numpy as np
from simulate_architecture import evaluate
from simulate_commitment import W_BOOK

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "benchmarks", "commitment")
TARGETS = ["0.01", "0.005", "0.001"]
FAMS = ["quota", "V0_reference", "V1_hard_bookings", "V2_separate_risk", "V3_hybrid"]
RANGES = dict(show=(0.75, 0.95), shock=(0.05, 0.30), sigscale=(0.8, 1.2), bscale=(0.6, 1.5), pulse=(50, 150),
              oversd=(0.15, 0.40), rho=(0.0, 0.75), adv=(0.1, 0.5))


def draw_world(i):
    r = np.random.default_rng(6000 + i)
    u = lambda k: float(r.uniform(*RANGES[k]))
    return (round(u("rho"), 3), round(u("show"), 3), round(u("shock"), 3), round(u("sigscale"), 3), round(u("bscale"), 3),
            int(r.integers(RANGES["pulse"][0], RANGES["pulse"][1] + 1)), round(u("oversd"), 3), round(u("adv"), 3))


def main(smoke=False):
    v5 = json.load(open(os.path.join(OUT, "results_v5.json")))["0.5"]["res"]
    cfgs, names = [], []
    for t in TARGETS:
        for f in FAMS:
            cfgs.append(v5[f"{t}|{f}"]["cfg"]); names.append((t, f))
    nw, nd = (6, 4) if smoke else (60, 30)
    worlds = [draw_world(i) for i in range(nw)]
    rows = []
    t0 = time.time()
    with Pool(min(14, os.cpu_count() or 4)) as pool:
        for i, w in enumerate(worlds):
            seeds = list(range(66000 + i * 100, 66000 + i * 100 + nd))
            runs = evaluate(pool, w, cfgs, seeds)
            row = dict(world=w, res={})
            for (t, f), rs in zip(names, runs):
                honored = float(np.mean([r["honored"] for r in rs])); wi = float(np.mean([r["wi"] for r in rs]))
                shown = sum(r["honored"] + r["breach"] for r in rs)
                row["res"][f"{t}|{f}"] = dict(score=W_BOOK * honored + wi, honored=honored, wi=wi,
                                              fail=sum(r["breach"] for r in rs) / max(shown, 1),
                                              fpd=float(np.mean([r["breach"] for r in rs])))
            rows.append(row)
            if (i + 1) % 10 == 0:
                print(f"{i+1} worlds {time.time()-t0:.0f}s", flush=True)
    summ = {}
    for t in TARGETS:
        q = np.array([r["res"][f"{t}|quota"]["score"] for r in rows]); qf = np.array([r["res"][f"{t}|quota"]["fail"] for r in rows])
        qd = np.array([r["res"][f"{t}|quota"]["fpd"] for r in rows])
        summ[t] = dict(quota=dict(under=float((qf <= float(t)).mean()), med_fail=float(np.median(qf)), p90_fail=float(np.percentile(qf, 90))))
        for f in FAMS[1:]:
            s = np.array([r["res"][f"{t}|{f}"]["score"] for r in rows]); fl = np.array([r["res"][f"{t}|{f}"]["fail"] for r in rows])
            fd = np.array([r["res"][f"{t}|{f}"]["fpd"] for r in rows])
            d = s - q
            summ[t][f] = dict(win=float((d > 0).mean()), med_diff=float(np.median(d)), p10=float(np.percentile(d, 10)), p90=float(np.percentile(d, 90)),
                              under=float((fl <= float(t)).mean()), med_fail=float(np.median(fl)), p90_fail=float(np.percentile(fl, 90)),
                              win_s10=float(((s - 10 * fd) > (q - 10 * qd)).mean()),
                              win_under=float(((d > 0) & (fl <= float(t))).mean()))
    tag = "_smoke" if smoke else ""
    json.dump(dict(ranges=RANGES, n_worlds=nw, days=nd, summary=summ, rows=rows), open(os.path.join(OUT, f"results_v6{tag}.json"), "w"), indent=1)
    L = ["# v6: Monte Carlo over assumptions", "", f"{nw} random worlds x {nd} days per policy; settings = nominal-world v5 picks, not retuned. Ranges: {RANGES}.", ""]
    for t in TARGETS:
        L += [f"## Failure target {100*float(t):.1f}%", "", "| Variant | Beats quota (share of worlds) | Median score diff [p10, p90] | Failures <= target (share) | Median / p90 failure rate | Beats quota at 10 per failure |", "|---|---|---|---|---|---|",
              f"| quota | - | - | {100*summ[t]['quota']['under']:.0f}% | {100*summ[t]['quota']['med_fail']:.2f}% / {100*summ[t]['quota']['p90_fail']:.2f}% | - |"]
        for f in FAMS[1:]:
            x = summ[t][f]
            L.append(f"| {f} | {100*x['win']:.0f}% | {x['med_diff']:+.1f} [{x['p10']:+.1f}, {x['p90']:+.1f}] | {100*x['under']:.0f}% | {100*x['med_fail']:.2f}% / {100*x['p90_fail']:.2f}% | {100*x['win_s10']:.0f}% |")
        L.append("")
    open(os.path.join(OUT, f"report_v6{tag}.md"), "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main("smoke" in sys.argv)
