"""Executable rolling LP, forecast ablation and paired synthetic stress study.

See benchmarks/v2/protocol.md before interpreting results. The guard and policy
inputs are deliberately separate from the environment's hidden future outcomes.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import time

import lightgbm as lgb
import numpy as np
import scipy
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parent
STEPS = 26
POLICIES = ['fixed0','fixed5','fixed10','reactive','rolling_average','rolling_ml','oracle_reference']
MARGIN = 2


@dataclass(frozen=True)
class Trip:
    arrival: int
    stay: float
    member: int = 0
    duration: int = 120


@dataclass(frozen=True)
class Booking:
    requested: int
    due: int
    arrival: int
    show: bool
    stay: float
    duration: int


@dataclass(frozen=True)
class Day:
    seed: int
    weekend: int
    walkins: tuple
    bookings: tuple


def make_day(seed, scale=1., scenario='base'):
    rng = np.random.default_rng(seed)
    weekend = int(seed % 7 >= 5)
    intensity = rng.lognormal(-.3**2/2,.3)*scale
    if scenario == 'spike': intensity *= 1.6
    stay_factor = 1.6 if scenario == 'long_stays' else 1.
    t = 600 + np.arange(STEPS)*30
    pub_rate = (.48+.36*np.exp(-.5*((t-750)/90)**2)+.84*np.exp(-.5*((t-1050)/100)**2))*30*intensity
    request_shape = .4*np.exp(-.5*((t-720)/90)**2)+.6*np.exp(-.5*((t-1080)/90)**2)
    request_rate = 60*intensity*request_shape/request_shape.sum()
    walkins, bookings = [], []
    sigma = math.log(155/44)/(2*.6745)
    for step in range(STEPS):
        walkins.append(tuple(Trip(step,float(max(15,rng.lognormal(math.log(87),sigma))*stay_factor)) for _ in range(rng.poisson(pub_rate[step]))))
        events=[]
        for _ in range(rng.poisson(request_rate[step])):
            duration=int(rng.choice([60,90,120,150,180,240],p=[.1,.15,.25,.2,.2,.1]))
            late = int(rng.choice([0,1,2],p=[.5,.2,.3] if scenario=='late_arrivals' else [.90,.08,.02]))
            show = bool(rng.random() < (.65 if scenario=='no_shows' else .90))
            events.append(Booking(step,step+1,step+1+late,show,float(duration*rng.lognormal(-.25**2/2,.25)*stay_factor),duration))
        bookings.append(tuple(events))
    return Day(seed,weekend,tuple(walkins),tuple(bookings))


def counts(day):
    return np.array([[len(x) for x in day.bookings],[len(x) for x in day.walkins]],float)


def features(day,t,h):
    v=counts(day)
    return [t,h,day.weekend,*v[:,t],*v[:,max(0,t-1)],*v[:,:t+1].sum(axis=1)/(t+1)]


def learner(cls=lgb.LGBMRegressor):
    return cls(n_estimators=120,num_leaves=15,min_child_samples=40,learning_rate=.05,
               verbosity=-1,n_jobs=4,random_state=901,deterministic=True,force_col_wise=True)


class Forecaster:
    def __init__(self,train):
        x,y=[],[]
        self.average=np.zeros((2,2,STEPS))
        self.means=[]
        for w in (0,1):
            self.average[w]=np.mean([counts(d) for d in train if d.weekend==w],axis=0)
        alltrips=[]
        for day in train:
            values=counts(day)
            for t in range(STEPS):
                for h in range(1,7):
                    if t+h<STEPS:
                        x.append(features(day,t,h));y.append(values[:,t+h])
            alltrips.extend(trip for batch in day.walkins for trip in batch)
            alltrips.extend(Trip(b.arrival,b.stay,1,b.duration) for batch in day.bookings for b in batch if b.show)
        x,y=np.array(x),np.array(y)
        self.models=[]
        for i in (0,1):
            model=learner();model.fit(x,y[:,i]);self.models.append(model.booster_)
        self.means=[float(np.mean([v.stay for v in alltrips if v.member==m])) for m in (0,1)]
        # At-risk snapshots: each completed training trip contributes once per
        # observed 30-minute age. No test trip contributes to this learner.
        sx,sy=[],[];rng=np.random.default_rng(901)
        for trip in alltrips[::3]:
            for age in np.arange(0,min(trip.stay,600),30):
                for horizon in rng.choice([15,30,60,90,120,150,180],2,replace=False):
                    sx.append([age,horizon,trip.arrival,trip.member,trip.duration])
                    sy.append(int(trip.stay>age+horizon))
        survival=learner(lgb.LGBMClassifier);survival.fit(np.array(sx),np.array(sy))
        self.survival=survival.booster_
        self.forecast_cache={}
        self.kernels=[]
        for member in (0,1):
            stays=np.array([v.stay for v in alltrips if v.member==member])
            self.kernels.append(np.array([(stays>age*30).mean() for age in range(6)]))

    def demand(self,day,t,kind):
        key=(day.seed,kind)
        if key not in self.forecast_cache:
            if kind=='average':
                p=np.zeros((STEPS,2,6))
                for origin in range(STEPS):
                    for h in range(1,7):
                        if origin+h<STEPS:p[origin,:,h-1]=self.average[day.weekend,:,origin+h]
            else:
                x=np.array([features(day,origin,h) for origin in range(STEPS) for h in range(1,7)])
                p=np.stack([np.maximum(0,m.predict(x,num_threads=1)) for m in self.models],axis=1).reshape(STEPS,6,2).transpose(0,2,1)
                for origin in range(STEPS):p[origin,:,max(0,STEPS-origin-1):]=0
            self.forecast_cache[key]=p
        return self.forecast_cache[key][t].copy()

    def remaining(self,active,now,horizons,kind):
        if not active:return np.zeros(len(horizons))
        if kind=='average':
            return np.array([sum(math.exp(-h/self.means[trip.member]) for trip,entered,_ in active) for h in horizons])
        x=np.array([[now-entered,h,trip.arrival,trip.member,trip.duration] for trip,entered,_ in active for h in horizons])
        p=self.survival.predict(x,num_threads=1).reshape(len(active),len(horizons))
        p=np.minimum.accumulate(np.clip(p,0,1),axis=1)
        return p.sum(axis=0)


def safe_slots(capacity,occupancy,promises,healthy=True):
    return max(0,capacity-occupancy-promises-MARGIN) if healthy else 0


def rolling_quota(capacity,pending,active,now,offered,future,model,kind,weight=5.,oracle=False,departure_factor=1.):
    start=time.perf_counter()
    if oracle:
        residual=np.array([sum(out>now+h*30 for _,_,out in active) for h in range(6)],float)
    else:
        residual=np.r_[len(active),model.remaining(active,now,np.arange(1,6)*30,kind)]
    residual=np.maximum(0,len(active)-(len(active)-residual)*departure_factor)
    # Six walk-in and six hypothetical future member-request acceptances.
    a=np.zeros((6,12))
    for h in range(6):
        for k in range(h+1):
            a[h,k]=model.kernels[0][h-k]
            # A future promise holds capacity before its due arrival.
            a[h,6+k]=1. if h-k<=1 else model.kernels[1][h-k-1]
    member=np.r_[0.,future[0,:5]]
    public=np.r_[offered,future[1,:5]]
    rhs=np.maximum(0,capacity-MARGIN-pending-residual)
    objective=-np.r_[np.ones(6),np.ones(6)*weight]
    res=linprog(objective,A_ub=a,b_ub=rhs,bounds=list(zip(np.zeros(12),np.r_[public,member])),method='highs')
    elapsed=(time.perf_counter()-start)*1000
    return (int(np.floor(res.x[0]+1e-7)) if res.success else 0),elapsed,int(not res.success)


def run_policy(day,capacity,policy,model,scenario='base',weight=5.,collect=False):
    active=[];pending=[];accepted=set();snapshots=[];latencies=[]
    metrics={k:0 for k in ['requests','accepted','fulfilled','failed','late_expired','no_show_expired','valid_accepted_arrivals','walkins','rejected',
                           'physical_violations','claim_violations','physical_entry_denials','fault_paused_requests','solver_failures']}
    metrics['idle_protected_bay_hours']=0.
    for step in range(STEPS+4):
        now=step*30
        active=[v for v in active if v[2]>now]
        healthy=not ((scenario=='count_drift' and 10<=step<=13) or (scenario=='outage' and 10<=step<=13))
        # Expire only after the disclosed due+grace window; late entries are separate.
        metrics['no_show_expired']+=sum(not b.show for b in pending if step>b.due+1)
        pending=[b for b in pending if step<=b.due+1]
        for b in sorted(accepted,key=lambda b:(b.arrival,b.requested,b.duration,b.stay)):
            if b.show and b.arrival==step:
                if b not in pending:
                    metrics['late_expired']+=1
                else:
                    pending.remove(b)
                    metrics['valid_accepted_arrivals']+=1
                    if len(active)>=capacity:metrics['failed']+=1
                    else:
                        trip=Trip(step,b.stay,1,b.duration)
                        active.append((trip,now,now+b.stay));metrics['fulfilled']+=1
        if step<STEPS:
            # Explicit negative control: both the count and independent ledger
            # lose eight occupied-car records. This is outside the safe contract.
            hidden=8 if scenario=='undetected_drift' and 10<=step<=13 else 0
            for b in day.bookings[step]:
                metrics['requests']+=1
                if not healthy:metrics['fault_paused_requests']+=1
                if safe_slots(capacity,max(0,len(active)-hidden),len(pending),healthy)>0:
                    accepted.add(b);pending.append(b);metrics['accepted']+=1
                else:metrics['rejected']+=1
            offered=len(day.walkins[step])
            hard=safe_slots(capacity,max(0,len(active)-hidden),len(pending),healthy)
            if policy.startswith('fixed'):
                quota=max(0,hard-int(policy[5:]))
            else:
                kind='average' if policy=='rolling_average' else 'ml'
                if policy=='oracle_reference':
                    values=counts(day)
                    future=np.zeros((2,6))
                    for h in range(1,7):
                        if step+h<STEPS:future[:,h-1]=values[:,step+h]
                else:future=model.demand(day,step,kind)
                if scenario=='forecast_bias':future*=.5
                if policy=='reactive':quota=max(0,hard-math.ceil(future[0,0]))
                elif hard:
                    visible=active[:-hidden] if hidden else active
                    quota,latency,failed=rolling_quota(capacity,len(pending),visible,now,offered,future,model,kind,weight,policy=='oracle_reference',1.5 if scenario=='forecast_bias' else 1.)
                    latencies.append(latency);metrics['solver_failures']+=failed
                else:quota=0
            admit=min(offered,hard,max(0,quota))
            metrics['physical_entry_denials']+=max(0,admit-(capacity-len(active)))
            admit=min(admit,max(0,capacity-len(active)))
            for trip in day.walkins[step][:admit]:active.append((trip,now,now+trip.stay))
            metrics['walkins']+=admit
            # Opportunity-cost metric, explicitly only when walk-ins lose entry.
            if offered>admit:
                metrics['idle_protected_bay_hours']+=max(0,capacity-len(active))*.5
            if collect:snapshots.append((now,tuple(active)))
        metrics['physical_violations']+=int(len(active)>capacity)
        metrics['claim_violations']+=int(len(active)+len(pending)>capacity)
    metrics['rejection_rate']=metrics['rejected']/max(1,metrics['requests'])
    metrics['solver_latency_ms_mean']=float(np.mean(latencies)) if latencies else 0.
    metrics['solver_latency_ms_p95']=float(np.quantile(latencies,.95)) if latencies else 0.
    return metrics,snapshots


def forecast_scores(model,calibration,test):
    demand=[]
    for horizon in (1,2,4,6):
        samples={}
        for name,days in [('calibration',calibration),('test',test)]:
            y,p=[],[]
            for day in days:
                actual=counts(day)
                for t in range(STEPS-horizon):
                    y.append(actual[0,t+1:t+horizon+1].sum())
                    p.append([model.demand(day,t,k)[0,:horizon].sum() for k in ['average','ml']])
            samples[name]=(np.array(y),np.array(p))
        cy,cp=samples['calibration'];y,p=samples['test']
        row={'minutes':horizon*30,'n':len(y),'models':{}}
        for i,kind in enumerate(['average','ml']):
            width=np.quantile(abs(cy-cp[:,i]),min(1.,math.ceil((len(cy)+1)*.8)/len(cy)),method='higher')
            row['models'][kind]={'mae':float(abs(y-p[:,i]).mean()),'wape':float(abs(y-p[:,i]).sum()/max(y.sum(),1)),
                                'interval80_coverage':float((abs(y-p[:,i])<=width).mean()),'half_width':float(width)}
        demand.append(row)
    turnover=[]
    for minutes in (15,30):
        samples={}
        for name,days in [('calibration',calibration),('test',test)]:
            y,p=[],[]
            for day in days:
                _,snapshots=run_policy(day,100,'fixed5',model,collect=True)
                for now,active in snapshots:
                    y.append(sum(out<=now+minutes for _,_,out in active))
                    p.append([len(active)-model.remaining(active,now,[minutes],k)[0] for k in ['average','ml']])
            samples[name]=(np.array(y),np.array(p))
        cy,cp=samples['calibration'];y,p=samples['test'];row={'minutes':minutes,'n':len(y),'models':{}}
        for i,k in enumerate(['average','ml']):
            width=np.quantile(abs(cy-cp[:,i]),min(1.,math.ceil((len(cy)+1)*.8)/len(cy)),method='higher')
            row['models'][k]={'departure_count_mae':float(abs(y-p[:,i]).mean()),'interval80_coverage':float((abs(y-p[:,i])<=width).mean())}
        turnover.append(row)
    return {'booking_demand':demand,'turnover':turnover,'data_kind':'synthetic only'}


def summarize(rows):
    return {p:{k:float(np.mean([r[k] for r in rows if r['policy']==p])) for k in rows[0] if k not in ['policy','seed','setting']} for p in POLICIES}


def paired(rows,first,second,metric):
    a={r['seed']:r[metric] for r in rows if r['policy']==first};b={r['seed']:r[metric] for r in rows if r['policy']==second}
    delta=np.array([a[s]-b[s] for s in sorted(a)])
    means=np.random.default_rng(901).choice(delta,(2000,len(delta)),replace=True).mean(axis=1)
    return {'first':first,'second':second,'metric':metric,'mean_delta':float(delta.mean()),'ci95':[float(x) for x in np.quantile(means,[.025,.975])]}


def run(days,out):
    started=time.perf_counter()
    train=[make_day(10000+i) for i in range(160)]
    cal=[make_day(20000+i) for i in range(40)]
    test=[make_day(30000+i) for i in range(days)]
    print('Fitting synthetic demand and survival models on 160 training days...',flush=True)
    model=Forecaster(train)
    scores=forecast_scores(model,cal,test)
    print('Completed synthetic demand and departure holdouts',flush=True)
    settings=[('base_100',100,1.,'base',5.,days),('size_50_same_demand',50,1.,'base',5.,days),
              ('size_150_same_demand',150,1.,'base',5.,days),('size_50_scaled',50,.5,'base',5.,days),
              ('size_150_scaled',150,1.5,'base',5.,days)]
    stress_days=min(20,days)
    settings += [(s,100,1.,s,5.,stress_days) for s in ['spike','long_stays','late_arrivals','no_shows','forecast_bias','count_drift','outage','undetected_drift']]
    settings += [('weight_1',100,1.,'base',1.,stress_days),('weight_10',100,1.,'base',10.,stress_days)]
    allrows=[];summary={}
    for name,capacity,scale,scenario,weight,n in settings:
        # The cache key includes seed; transformed generators need new seed IDs
        # in the cache, but retain exactly the same stochastic draws for pairing.
        model.forecast_cache.clear()
        rows=[]
        for i in range(n):
            day=make_day(30000+i,scale,scenario)
            for policy in POLICIES:
                metrics,_=run_policy(day,capacity,policy,model,scenario,weight)
                rows.append({'setting':name,'seed':day.seed,'policy':policy,**metrics})
        summary[name]={'days':n,'capacity':capacity,'demand_scale':scale,'member_weight':weight,'policies':summarize(rows),
                       'paired':[paired(rows,'rolling_ml',p,m) for p in ['fixed0','fixed5','fixed10','rolling_average'] for m in ['fulfilled','walkins','idle_protected_bay_hours']]}
        allrows.extend(rows)
        print(f'Completed {name}: {n} paired days x {len(POLICIES)} policies',flush=True)
    out.mkdir(parents=True,exist_ok=True)
    data=ROOT/'benchmark_data';data.mkdir(exist_ok=True)
    (data/'rolling-v2-days.json').write_text(json.dumps(allrows),encoding='utf-8')
    report={'protocol_sha256':hashlib.sha256((out/'protocol.md').read_bytes()).hexdigest(),
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'data_kind':'synthetic','train_days':160,'calibration_days':40,'test_days':days,'policy_day_runs':len(allrows),
            'runtime_seconds':time.perf_counter()-started,'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'lightgbm':lgb.__version__},
            'forecast_scores':scores,'settings':summary,
            'limits':['New offline 30-minute-batch research harness, not deployed application code.',
                      'Synthetic results depend on assumed arrival, request, stay and show-up distributions.',
                      'Oracle reference is not an optimal upper bound; fitted future-cohort kernels remain.',
                      'Safety assumes independently verified exact counts/ledger; undetected drift is not covered.',
                      'No causal customer, paid demand, retention or financial return validation.']}
    (out/'rolling.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'runtime_seconds':report['runtime_seconds'],'policy_day_runs':len(allrows),'base':summary['base_100']},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--days',type=int,default=60);parser.add_argument('--out',type=Path,default=ROOT/'benchmarks/v2')
    args=parser.parse_args();run(args.days,args.out)
