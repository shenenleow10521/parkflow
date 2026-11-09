"""Causal weekly 30/60/120/180-minute public-data benchmark; never writes V1.

Observations are CEILED to grid availability, not rounded backwards. For each
test week: fit before blend week, fit blend on week -2, calibrate intervals on
week -1, and freeze both for the test week. No new-site generalisation claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
HORIZONS = (1, 2, 4, 6)
FEATURES = ['park', 'cap', 'h', 'slot', 't_slot', 'dow', 'rate', 'lag1', 'lag2',
            'lw_target', 'lw_now', 'lw_gap']


def download(path):
    payload=urlopen('https://archive.ics.uci.edu/static/public/482/parking+birmingham.zip',timeout=45).read()
    with ZipFile(BytesIO(payload)) as archive:
        name=next(n for n in archive.namelist() if n.endswith('dataset.csv'))
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(archive.read(name))


def prepare(path):
    raw = pd.read_csv(path, parse_dates=['LastUpdated'])
    raw['rate'] = raw.Occupancy / raw.Capacity
    raw = raw[(raw.Capacity > 0) & raw.rate.between(0, 1)].copy()
    raw['slot_time'] = raw.LastUpdated.dt.ceil('30min')
    # Last available observation within each half-hour, never a later reading.
    df = raw.sort_values('LastUpdated').drop_duplicates(['SystemCodeNumber', 'slot_time'], keep='last')
    assert (df.LastUpdated <= df.slot_time).all()
    df = df.rename(columns={'Capacity': 'cap'})
    df['date'] = df.slot_time.dt.normalize()
    df['slot'] = (df.slot_time.dt.hour * 60 + df.slot_time.dt.minute - 480) // 30
    df = df[df.slot.between(0, 17)]
    key = df.set_index(['SystemCodeNumber', 'date', 'slot']).rate
    def look(p, d, s):
        return key.reindex(pd.MultiIndex.from_arrays([p, d, s])).to_numpy()
    rows = []
    for h in HORIZONS:
        d = df.copy(); d['h'] = h; d['t_slot'] = d.slot + h
        d = d[d.t_slot <= 17]
        previous = d.date - pd.Timedelta(days=7)
        d['y'] = look(d.SystemCodeNumber, d.date, d.t_slot)
        d['lag1'] = look(d.SystemCodeNumber, d.date, d.slot - 1)
        d['lag2'] = look(d.SystemCodeNumber, d.date, d.slot - 2)
        d['lw_target'] = look(d.SystemCodeNumber, previous, d.t_slot)
        d['lw_now'] = look(d.SystemCodeNumber, previous, d.slot)
        rows.append(d)
    data = pd.concat(rows, ignore_index=True).dropna(subset=['y', 'lw_target', 'lw_now'])
    data['dow'] = data.date.dt.dayofweek
    data['park'] = data.SystemCodeNumber.astype('category')
    data['week'] = (data.date - data.date.min()).dt.days // 7
    data['lw_gap'] = data.rate - data.lw_now
    data['adjusted'] = (data.rate + data.lw_target - data.lw_now).clip(0, 1)
    return data, len(df)


def run(path, out):
    data, readings = prepare(path)
    predictions, splits = [], []
    for week in sorted(data.week.unique())[-6:]:
        train = data[data.week < week-2]
        blend = data[data.week == week-2].copy()
        calibrate = data[data.week == week-1].copy()
        test = data[data.week == week].copy()
        assert len(train) and len(blend) and len(calibrate) and len(test)
        assert train.date.max() < blend.date.min() <= blend.date.max() < calibrate.date.min() <= calibrate.date.max() < test.date.min()
        model = lgb.LGBMRegressor(n_estimators=300, learning_rate=.05, num_leaves=31,
                                 min_child_samples=30, verbosity=-1, n_jobs=4,
                                 random_state=482, deterministic=True, force_col_wise=True)
        model.fit(train[FEATURES], train.y)
        for sample in [blend, calibrate, test]:
            sample['ml'] = np.clip(model.predict(sample[FEATURES]), 0, 1)
        weights = {}
        for h in HORIZONS:
            b = blend[blend.h == h]
            # One-dimensional convex least-squares blend, fitted before calibration.
            diff = (b.ml - b.adjusted).to_numpy()
            w = np.clip(np.dot(diff, b.y-b.adjusted) / max(np.dot(diff, diff), 1e-12), 0, 1)
            weights[h] = float(w)
            for sample in [calibrate, test]:
                mask = sample.h == h
                sample.loc[mask, 'ensemble'] = w*sample.loc[mask, 'ml'] + (1-w)*sample.loc[mask, 'adjusted']
            c = calibrate[calibrate.h == h]
            quantile = min(1., np.ceil((len(c)+1)*.8)/len(c))
            width = np.quantile(abs(c.y-c.ensemble), quantile, method='higher')
            test.loc[test.h == h, 'width'] = width
        predictions.append(test)
        splits.append({'test_week':int(week), 'train_end':str(train.date.max().date()),
                       'blend_start':str(blend.date.min().date()), 'calibration_start':str(calibrate.date.min().date()),
                       'test_start':str(test.date.min().date()), 'test_end':str(test.date.max().date()),
                       'test_predictions':len(test), 'ml_weights':weights})
        print(f'Completed occupancy week {week}: {len(test)} predictions', flush=True)
    result = pd.concat(predictions, ignore_index=True)
    metrics = []
    for h in HORIZONS:
        r = result[result.h == h]
        row = {'minutes':h*30, 'n':len(r), 'car_parks':int(r.SystemCodeNumber.nunique()),
               'mae_pct_capacity':{name:float(abs(r.y-r[col]).mean()*100) for name,col in
                                   [('last_week','lw_target'), ('persistence','rate'), ('adjusted','adjusted'), ('ml','ml'), ('ensemble','ensemble')]},
               'interval_80_coverage':float((abs(r.y-r.ensemble) <= r.width).mean()),
               'interval_mean_half_width_pct':float(r.width.mean()*100)}
        # Resample dates, not thousands of correlated park/horizon observations.
        dates = r.assign(delta=(abs(r.y-r.ensemble)-abs(r.y-r.lw_target))*100).groupby('date').delta.mean().to_numpy()
        boot = np.random.default_rng(482+h).choice(dates, (2000,len(dates)), replace=True).mean(axis=1)
        row['paired_daily_mae_delta_vs_last_week_ci95'] = [float(x) for x in np.quantile(boot,[.025,.975])]
        metrics.append(row)
    report = {'dataset':'UCI Parking Birmingham', 'source':'https://archive.ics.uci.edu/dataset/482/parking+birmingham',
              'csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'readings':readings,
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'lightgbm':lgb.__version__},
              'car_parks':int(data.SystemCodeNumber.nunique()), 'test_forecasts':len(result),
              'protocol':'Ceil observation availability; rolling train / blend / calibration / test weeks; horizon-specific comparisons.',
              'limitations':['Historical UK occupancy only; no booking requests or entry/exit turnover labels.',
                             'Same car parks in train and test, not new-site validation.',
                             'Weekly pooling of interval residuals is empirical; temporal dependence limits nominal conformal guarantees.',
                             'Ceiling availability changes the sample relative to the earlier rounded-time benchmark.'],
              'metrics':metrics, 'splits':splits}
    out.mkdir(parents=True, exist_ok=True)
    (out/'occupancy.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ROOT/'benchmark_data').mkdir(exist_ok=True)
    result[['SystemCodeNumber','slot_time','h','y','lw_target','rate','ml','ensemble','width']].to_csv(ROOT/'benchmark_data/occupancy-v2-predictions.csv',index=False)
    print(json.dumps(metrics,indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=ROOT/'benchmark_data/dataset.csv')
    parser.add_argument('--out',type=Path,default=ROOT/'benchmarks/v2')
    parser.add_argument('--download',action='store_true',help='Fetch the official UCI CSV to --data before running.')
    args = parser.parse_args()
    if args.download:download(args.data)
    run(args.data,args.out)
