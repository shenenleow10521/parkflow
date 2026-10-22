"""Rolling weekly backtest of car park occupancy forecasts on UCI Parking Birmingham.

Data: download https://archive.ics.uci.edu/static/public/482/parking+birmingham.zip and unzip dataset.csv
Usage: python backtest_birmingham.py <path to dataset.csv>
Compares LightGBM against two simple baselines at 30/60/90 minute look-ahead,
and checks calibration of a "nearly full" probability at 60 minutes.
"""
import sys
import pandas as pd
import lightgbm as lgb

FULL = 0.90  # "nearly full" threshold, share of capacity

raw = pd.read_csv(sys.argv[1], parse_dates=["LastUpdated"])
raw = raw[(raw.Occupancy >= 0) & (raw.Capacity > 0)]
raw["rate"] = raw.Occupancy / raw.Capacity
raw = raw[raw.rate <= 1.1]

# Readings arrive roughly every 30 minutes; snap to the nearest half hour.
raw["slot_time"] = raw.LastUpdated.dt.round("30min")
df = (raw.groupby(["SystemCodeNumber", "slot_time"], as_index=False)
         .agg(rate=("rate", "mean"), cap=("Capacity", "max")))
df["date"] = df.slot_time.dt.normalize()
df["slot"] = (df.slot_time.dt.hour * 60 + df.slot_time.dt.minute - 8 * 60) // 30
df = df[(df.slot >= 0) & (df.slot <= 17)]  # 08:00 .. 16:30

# Lookup of occupancy by (park, date, slot) for building features.
key = df.set_index(["SystemCodeNumber", "date", "slot"]).rate
def lookup(park, date, slot):
    return key.reindex(pd.MultiIndex.from_arrays([park, date, slot])).to_numpy()

rows = []
for h in (1, 2, 3):
    d = df.copy()
    d["h"] = h
    d["t_slot"] = d.slot + h
    d = d[d.t_slot <= 17]
    wk = d.date - pd.Timedelta(days=7)
    d["y"] = lookup(d.SystemCodeNumber, d.date, d.t_slot)
    d["lag1"] = lookup(d.SystemCodeNumber, d.date, d.slot - 1)
    d["lag2"] = lookup(d.SystemCodeNumber, d.date, d.slot - 2)
    d["lw_target"] = lookup(d.SystemCodeNumber, wk, d.t_slot)
    d["lw_now"] = lookup(d.SystemCodeNumber, wk, d.slot)
    rows.append(d)
data = pd.concat(rows)
data = data.dropna(subset=["y", "lw_target", "lw_now"])
data["dow"] = data.date.dt.dayofweek
data["park"] = data.SystemCodeNumber.astype("category")
data["week"] = ((data.date - data.date.min()).dt.days // 7).astype(int)
data["lw_gap"] = data.rate - data.lw_now  # how today differs from last week so far

FEATS = ["park", "cap", "h", "slot", "t_slot", "dow", "rate", "lag1", "lag2",
         "lw_target", "lw_now", "lw_gap"]

weeks = sorted(data.week.unique())
test_weeks = weeks[-6:]  # last 6 weeks, each predicted using only earlier weeks
preds = []
for w in test_weeks:
    tr, te = data[data.week < w], data[data.week == w].copy()
    reg = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            min_child_samples=20, verbose=-1)
    reg.fit(tr[FEATS], tr.y)
    te["pred"] = reg.predict(te[FEATS])
    clf = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                             min_child_samples=20, verbose=-1)
    clf.fit(tr[FEATS], (tr.y >= FULL).astype(int))
    te["p_full"] = clf.predict_proba(te[FEATS])[:, 1]
    preds.append(te)
res = pd.concat(preds)

print(f"Car parks: {df.SystemCodeNumber.nunique()}, readings used: {len(df)}, "
      f"test weeks: {len(test_weeks)}, test predictions: {len(res)}")
print("\nAverage error, % of capacity (lower is better)")
print(f"{'Look-ahead':<12}{'Last week':>11}{'No change':>11}{'LightGBM':>10}{'vs last wk':>12}{'vs no chg':>11}")
for h in (1, 2, 3):
    r = res[res.h == h]
    e_lw = (r.y - r.lw_target).abs().mean() * 100
    e_nc = (r.y - r.rate).abs().mean() * 100
    e_m = (r.y - r.pred).abs().mean() * 100
    print(f"{h*30:>3} min      {e_lw:>10.1f}{e_nc:>11.1f}{e_m:>10.1f}"
          f"{(1-e_m/e_lw)*100:>11.0f}%{(1-e_m/e_nc)*100:>10.0f}%")

r = res[res.h == 2].copy()
y = (r.y >= FULL).astype(int)
brier = ((r.p_full - y) ** 2).mean()
base = ((y.mean() - y) ** 2).mean()
print(f"\n'Nearly full (>= {FULL:.0%}) in 60 min' probability: "
      f"share of cases nearly full = {y.mean():.1%}, Brier = {brier:.3f} "
      f"(always-guess-average = {base:.3f})")
r["bin"] = pd.cut(r.p_full, [0, .1, .3, .5, .7, .9, 1.0], include_lowest=True)
cal = r.groupby("bin", observed=True).apply(
    lambda g: pd.Series({"cases": len(g), "said": g.p_full.mean(), "happened": (g.y >= FULL).mean()}),
    include_groups=False)
print("\nCalibration at 60 min (when we said X%, how often was it nearly full?)")
print(cal.to_string(float_format=lambda v: f"{v:.2f}"))

# Example day for the slides: among busy days (peak >= 90%), take the one with
# the median 60-minute error, so the chart shows a typical day, not the best one.
days = r.groupby(["SystemCodeNumber", "date"]).agg(
    peak=("y", "max"), mae=("pred", lambda p: (r.loc[p.index, "y"] - p).abs().mean()), n=("y", "size"))
busy = days[(days.peak >= FULL) & (days.n >= 14)].sort_values("mae")
park, date = busy.index[len(busy) // 2]
day = r[(r.SystemCodeNumber == park) & (r.date == date)].sort_values("t_slot")
day = day.assign(time=day.t_slot.map(lambda s: f"{8 + s // 2:02d}:{30 * (s % 2):02d}"))
day[["time", "y", "pred"]].round(3).to_csv("backtest_sample_day.csv", index=False)
print(f"\nExample day: {park} on {date.date()}, busy days to choose from: {len(busy)}, "
      f"its 60-min error: {busy.loc[(park, date), 'mae']*100:.1f}% (saved backtest_sample_day.csv)")
