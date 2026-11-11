"""Do weather and event signals improve the forecast layer on REAL data (UCI Parking Birmingham)?

Walk-forward, same protocol as backtest_ensemble.py (train on earlier weeks only, test the last 6 weeks), but
horizons 30..180 min, so the 3-hour planning horizon is covered. LightGBM variants differ only in features:
  base       - time, day, current/recent occupancy, last-week values (as backtest_ensemble.py)
  +cal       - + approximate event calendar (school half-term, Christmas market, Black Friday)
  +wx_now    - + weather at the forecast origin (realistic: no look-ahead)
  +wx_target - + weather at the target time (OPTIMISTIC: assumes a perfect weather forecast)
  +all_now   - + calendar + weather at origin
Weather: Open-Meteo historical archive for Birmingham (52.48,-1.90). Calendar dates are approximate public knowledge, not verified.
Usage: python backtest_signals.py benchmark_data/dataset.csv     (writes backtest_signals_results.txt)
"""
import sys, json, os, urllib.request
import numpy as np, pandas as pd, lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__))
raw = pd.read_csv(sys.argv[1], parse_dates=["LastUpdated"])
raw = raw[(raw.Occupancy >= 0) & (raw.Capacity > 0)]
raw["rate"] = raw.Occupancy / raw.Capacity
raw = raw[raw.rate <= 1.1]
raw["slot_time"] = raw.LastUpdated.dt.round("30min")
df = raw.groupby(["SystemCodeNumber", "slot_time"], as_index=False).agg(rate=("rate", "mean"), cap=("Capacity", "max"))
df["date"] = df.slot_time.dt.normalize()
df["slot"] = (df.slot_time.dt.hour * 60 + df.slot_time.dt.minute - 8 * 60) // 30
df = df[(df.slot >= 0) & (df.slot <= 17)]

# ---- weather (cached)
d0, d1 = df.date.min().date(), df.date.max().date()
cache = os.path.join(HERE, "benchmark_data", "birmingham_weather.json")
if not os.path.exists(cache):
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude=52.48&longitude=-1.90"
           f"&start_date={d0}&end_date={d1}&hourly=temperature_2m,precipitation,cloud_cover&timezone=Europe%2FLondon")
    open(cache, "wb").write(urllib.request.urlopen(url, timeout=60).read())
w = json.load(open(cache))["hourly"]
wx = pd.DataFrame(w); wx["time"] = pd.to_datetime(wx["time"]).dt.tz_localize(None)
wx = wx.set_index("time")
def wxat(slot_time, col):   # weather for the hour containing the slot
    return wx[col].reindex(slot_time.dt.floor("h")).to_numpy()
wx["rain3h"] = wx.precipitation.rolling(3, min_periods=1).sum()

key = df.set_index(["SystemCodeNumber", "date", "slot"]).rate
look = lambda p, d, s: key.reindex(pd.MultiIndex.from_arrays([p, d, s])).to_numpy()
H = (1, 2, 3, 4, 5, 6)
rows = []
for h in H:
    d = df.copy(); d["h"] = h; d["t_slot"] = d.slot + h; d = d[d.t_slot <= 17]
    wk = d.date - pd.Timedelta(days=7)
    d["y"] = look(d.SystemCodeNumber, d.date, d.t_slot)
    d["lag1"] = look(d.SystemCodeNumber, d.date, d.slot - 1)
    d["lag2"] = look(d.SystemCodeNumber, d.date, d.slot - 2)
    d["lw_target"] = look(d.SystemCodeNumber, wk, d.t_slot)
    d["lw_now"] = look(d.SystemCodeNumber, wk, d.slot)
    tt = d.date + pd.to_timedelta(8 * 60 + d.t_slot * 30, unit="m")
    d["t_time"] = tt
    rows.append(d)
data = pd.concat(rows).dropna(subset=["y", "lw_target", "lw_now"]).copy()
data["dow"] = data.date.dt.dayofweek
data["park"] = data.SystemCodeNumber.astype("category")
data["week"] = ((data.date - data.date.min()).dt.days // 7).astype(int)
data["lw_gap"] = data.rate - data.lw_now
# approximate event calendar
D = data.date
data["halfterm"] = ((D >= "2016-10-24") & (D <= "2016-10-28")).astype(int)
data["xmas_mkt"] = (D >= "2016-11-10").astype(int)
data["blackfri"] = (D == "2016-11-25").astype(int)
data["wx_temp_now"] = wxat(data.slot_time, "temperature_2m")
data["wx_rain_now"] = wxat(data.slot_time, "precipitation")
data["wx_rain3h_now"] = wx["rain3h"].reindex(data.slot_time.dt.floor("h")).to_numpy()
data["wx_temp_tgt"] = wxat(data.t_time, "temperature_2m")
data["wx_rain_tgt"] = wxat(data.t_time, "precipitation")

BASE = ["park", "cap", "h", "slot", "t_slot", "dow", "rate", "lag1", "lag2", "lw_target", "lw_now", "lw_gap"]
CAL = ["halfterm", "xmas_mkt", "blackfri"]
NOW = ["wx_temp_now", "wx_rain_now", "wx_rain3h_now"]
TGT = ["wx_temp_tgt", "wx_rain_tgt"]
VAR = {"base": BASE, "+cal": BASE + CAL, "+wx_now": BASE + NOW, "+wx_target": BASE + NOW + TGT, "+all_now": BASE + CAL + NOW}

def fit_pred(feats, train, test):
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=20, verbose=-1, random_state=0)
    m.fit(train[feats], train.y)
    return m.predict(test[feats])

weeks = sorted(data.week.unique())[-6:]
res = []
for wk_ in weeks:
    te = data[data.week == wk_].copy(); tr = data[data.week < wk_]
    for name, f in VAR.items():
        te[name] = fit_pred(f, tr, te)
    te["adjusted"] = (te.rate + te.lw_target - te.lw_now).clip(0, 1.1)
    res.append(te)
res = pd.concat(res)
out = [f"Test forecasts: {len(res)//len(H)} per horizon over 6 weeks, {res.SystemCodeNumber.nunique()} car parks (UCI Parking Birmingham)",
       "Average absolute error, % of capacity (lower is better). Weather: Open-Meteo archive. Calendar: approximate.", "",
       f"{'Ahead':<9}{'LastWk':>8}{'Adjusted':>9}" + "".join(f"{k:>12}" for k in VAR) + f"{'best vs base':>14}"]
for h in H:
    r = res[res.h == h]
    e = {m: (r.y - r[m]).abs().mean() * 100 for m in ["lw_target", "adjusted"] + list(VAR)}
    best = min(VAR, key=lambda k: e[k])
    out.append(f"{h*30:>4} min {e['lw_target']:>8.2f}{e['adjusted']:>9.2f}" + "".join(f"{e[k]:>12.2f}" for k in VAR) + f"{best+' '+format((1-e[best]/e['base'])*100,'.1f')+'%':>14}")
# paired bootstrap over test days (clustered by date) for the realistic variants
out += ["", "Paired difference vs base, mean abs error (percentage points of capacity; negative = better), 95% interval over test days:"]
rng = np.random.default_rng(0)
for h in (1, 3, 6):
    r = res[res.h == h]
    for k in ("+cal", "+wx_now", "+all_now", "+wx_target"):
        day = (r.assign(d=(r.y - r[k]).abs() - (r.y - r["base"]).abs()).groupby("date").d.mean() * 100).to_numpy()
        bs = day[rng.integers(0, len(day), (2000, len(day)))].mean(1)
        out.append(f"  {h*30:>3} min {k:<11}{day.mean():+.3f} [{np.percentile(bs,2.5):+.3f}, {np.percentile(bs,97.5):+.3f}] over {len(day)} days")
txt = "\n".join(out); print(txt)
open(os.path.join(HERE, "backtest_signals_results.txt"), "w").write(txt + "\n")
