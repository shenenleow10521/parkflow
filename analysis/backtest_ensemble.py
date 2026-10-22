"""Does an ensemble beat LightGBM alone on UCI Parking Birmingham?

Models (all forecast occupancy 30/60/90 min ahead):
  lastweek  - same time last week
  adjusted  - last week's shape, shifted to today's level: now + (last week target - last week now)
  gbm       - LightGBM on time, day, current and recent occupancy, last-week values
  ensemble  - weighted blend of adjusted + gbm; weights fitted on the PREVIOUS week only
Also: 80% range from split conformal (previous week's ensemble errors), checked for coverage.
Data: https://archive.ics.uci.edu/static/public/482/parking+birmingham.zip (dataset.csv)
Usage: python backtest_ensemble.py <dataset.csv>   (writes backtest_ensemble_day.csv)
"""
import sys
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.optimize import nnls

raw = pd.read_csv(sys.argv[1], parse_dates=["LastUpdated"])
raw = raw[(raw.Occupancy >= 0) & (raw.Capacity > 0)]
raw["rate"] = raw.Occupancy / raw.Capacity
raw = raw[raw.rate <= 1.1]
raw["slot_time"] = raw.LastUpdated.dt.round("30min")
df = (raw.groupby(["SystemCodeNumber", "slot_time"], as_index=False)
         .agg(rate=("rate", "mean"), cap=("Capacity", "max")))
df["date"] = df.slot_time.dt.normalize()
df["slot"] = (df.slot_time.dt.hour * 60 + df.slot_time.dt.minute - 8 * 60) // 30
df = df[(df.slot >= 0) & (df.slot <= 17)]
key = df.set_index(["SystemCodeNumber", "date", "slot"]).rate
look = lambda p, d, s: key.reindex(pd.MultiIndex.from_arrays([p, d, s])).to_numpy()

rows = []
for h in (1, 2, 3):
    d = df.copy(); d["h"] = h; d["t_slot"] = d.slot + h; d = d[d.t_slot <= 17]
    wk = d.date - pd.Timedelta(days=7)
    d["y"] = look(d.SystemCodeNumber, d.date, d.t_slot)
    d["lag1"] = look(d.SystemCodeNumber, d.date, d.slot - 1)
    d["lag2"] = look(d.SystemCodeNumber, d.date, d.slot - 2)
    d["lw_target"] = look(d.SystemCodeNumber, wk, d.t_slot)
    d["lw_now"] = look(d.SystemCodeNumber, wk, d.slot)
    rows.append(d)
data = pd.concat(rows).dropna(subset=["y", "lw_target", "lw_now"])
data["dow"] = data.date.dt.dayofweek
data["park"] = data.SystemCodeNumber.astype("category")
data["week"] = ((data.date - data.date.min()).dt.days // 7).astype(int)
data["lw_gap"] = data.rate - data.lw_now
data["adjusted"] = (data.rate + data.lw_target - data.lw_now).clip(0, 1.1)
FEATS = ["park", "cap", "h", "slot", "t_slot", "dow", "rate", "lag1", "lag2", "lw_target", "lw_now", "lw_gap"]


def gbm_predict(train, test):
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=20, verbose=-1)
    m.fit(train[FEATS], train.y)
    return m.predict(test[FEATS])


weeks = sorted(data.week.unique())
out = []
for w in weeks[-6:]:
    # 1) Fit blend weights and conformal widths on the previous week, using a model that never saw it.
    val = data[data.week == w - 1].copy()
    val["gbm"] = gbm_predict(data[data.week < w - 1], val)
    weights, conf = {}, {}
    for h in (1, 2, 3):
        v = val[val.h == h]
        wts, _ = nnls(np.c_[v.adjusted, v.gbm], v.y.to_numpy())
        weights[h] = wts / wts.sum()
        blend = weights[h][0] * v.adjusted + weights[h][1] * v.gbm
        conf[h] = np.quantile((v.y - blend).abs(), 0.80)
    # 2) Predict the test week with everything trained on earlier weeks only.
    te = data[data.week == w].copy()
    te["gbm"] = gbm_predict(data[data.week < w], te)
    te["ensemble"] = [weights[h][0] * a + weights[h][1] * g for h, a, g in zip(te.h, te.adjusted, te.gbm)]
    te["half_width"] = te.h.map(conf)
    te["w_gbm"] = te.h.map(lambda h: weights[h][1])
    out.append(te)
res = pd.concat(out)

print(f"Test forecasts: {len(res)} over 6 weeks, 30 car parks\n")
print("Average error, % of capacity (lower is better)")
print(f"{'Ahead':<8}{'Last wk':>9}{'Adjusted':>10}{'LightGBM':>10}{'Ensemble':>10}{'Ens vs GBM':>12}{'GBM weight':>12}")
for h in (1, 2, 3):
    r = res[res.h == h]
    e = {m: (r.y - r[m]).abs().mean() * 100 for m in ("lw_target", "adjusted", "gbm", "ensemble")}
    print(f"{h*30:>3} min {e['lw_target']:>9.2f}{e['adjusted']:>10.2f}{e['gbm']:>10.2f}{e['ensemble']:>10.2f}"
          f"{(1 - e['ensemble']/e['gbm'])*100:>11.1f}%{r.w_gbm.mean():>12.2f}")
print("\n80% range check (should contain the real value ~80% of the time)")
for h in (1, 2, 3):
    r = res[res.h == h]
    cover = ((r.y - r.ensemble).abs() <= r.half_width).mean()
    print(f"{h*30:>3} min: contained {cover:.1%}, average range +/- {r.half_width.mean()*100:.1f}% of capacity")

# Example day for the fan chart: the same typical busy day used in backtest_birmingham.py.
day = res[(res.SystemCodeNumber == "BHMNCPNHS01") & (res.date == "2016-12-15") & (res.h == 2)].sort_values("t_slot")
day = day.assign(time=day.t_slot.map(lambda s: f"{8 + s // 2:02d}:{30 * (s % 2):02d}"),
                 low=(day.ensemble - day.half_width).clip(0, 1), high=(day.ensemble + day.half_width).clip(0, 1))
day[["time", "y", "ensemble", "low", "high"]].round(3).to_csv("backtest_ensemble_day.csv", index=False)
