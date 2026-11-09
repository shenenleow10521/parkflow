"""Minute-resolution, mixed-lead-time forecast decision-value experiment.

Read benchmarks/decision_value/protocol.md. All demand and signals are synthetic;
ordinary models see only events strictly before the forecast origin. This module
does not alter earlier benchmarks or either deck.
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
from scipy.special import ndtr
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'benchmarks/decision_value'
END=780
REQUEST_END=600
BIN=15
H=12
SAFETY=2
POLICIES=['guard','fixed5','fixed10','calibrated_fixed','reactive','lp_mean','lp_adaptive','lp_linear','lp_ml','request_oracle']


@dataclass(frozen=True)
class Event:
    id:int
    minute:int
    request:bool
    order:float
    stay:float
    due:int=0
    arrival:int=0
    show:bool=True
    duration:int=120


@dataclass(frozen=True)
class Day:
    seed:int
    weekend:int
    events:tuple
    requests:np.ndarray
    walkins:np.ndarray


def make_day(seed,kind='mixed',long_lead=False):
    rng=np.random.default_rng(seed);t=np.arange(END)
    scale=rng.lognormal(-.3**2/2,.3)
    if kind=='quiet':scale*=.5
    public=(.48+.36*np.exp(-.5*((t-150)/90)**2)+.84*np.exp(-.5*((t-450)/100)**2))*scale
    shape=.4*np.exp(-.5*((t-120)/90)**2)+.6*np.exp(-.5*((t-480)/90)**2)
    shape[t>=REQUEST_END]=0
    request=45*scale*shape/shape.sum()
    if kind!='quiet' and rng.random()<.65:
        center=int(rng.integers(180,510));amplitude=float(rng.uniform(60,110))*scale
        pulse=np.exp(-.5*((t-center)/12)**2);pulse[t>=REQUEST_END]=0
        request+=amplitude*pulse/pulse.sum()
        informative=rng.random()<.8
        if informative and kind!='unannounced':
            cue_center=center-(85 if kind=='shifted' else 35)
            cue=np.exp(-.5*((t-cue_center)/12)**2)
            public+=80*scale*cue/cue.sum()
    pc=rng.poisson(public);rc=rng.poisson(request)
    events=[];uid=0;sigma=math.log(155/44)/(2*.6745)
    for minute in range(END):
        for _ in range(pc[minute]):
            events.append(Event(uid,minute,False,float(rng.random()),float(max(15,rng.lognormal(math.log(87),sigma)))))
            uid+=1
        for _ in range(rc[minute]):
            duration=int(rng.choice([60,90,120,150,180,240],p=[.1,.15,.25,.2,.2,.1]))
            lead=int(rng.integers(90 if long_lead else 15,181));due=minute+lead
            late=int(rng.choice([0,10,25],p=[.90,.08,.02]))
            events.append(Event(uid,minute,True,float(rng.random()),float(duration*rng.lognormal(-.25**2/2,.25)),due,due+late,bool(rng.random()<.90),duration))
            uid+=1
    events.sort(key=lambda e:(e.minute,e.order))
    # Input arrays are immutable, preventing policy-specific event mutation.
    pc.setflags(write=False);rc.setflags(write=False)
    return Day(seed,int(seed%7>=5),tuple(events),rc,pc)


def history_features(day,origin):
    values=[origin/END,math.sin(origin/END*2*math.pi),math.cos(origin/END*2*math.pi),day.weekend]
    for stream in [day.requests,day.walkins]:
        values.extend(float(stream[max(0,origin-span):origin].sum()) for span in [5,15,30,60])
        values.append(float(stream[:origin].sum())/max(1,origin))
    return np.array(values,float)


class Forecasts:
    def __init__(self,train):
        self.profile=np.zeros((2,2,END))
        for w in (0,1):
            days=[d for d in train if d.weekend==w]
            self.profile[w]=np.mean([np.stack([d.requests,d.walkins]) for d in days],axis=0)
        x=[];ys=[];flatx=[];flaty=[];trips=[]
        for d in train:
            trips.extend(d.events)
            for t in range(0,END,BIN):
                f=history_features(d,t)
                targets=np.array([d.requests[t+h*BIN:min(END,t+(h+1)*BIN)].sum() for h in range(H)],float)
                x.append(f);ys.append(targets)
                for h,target in enumerate(targets):
                    flatx.append(np.r_[f,h]);flaty.append(target)
        x=np.array(x);ys=np.array(ys)
        self.scaler=StandardScaler().fit(x)
        self.linear=Ridge(alpha=20.).fit(self.scaler.transform(x),ys)
        learner=lgb.LGBMRegressor(n_estimators=180,num_leaves=15,min_child_samples=60,learning_rate=.05,
                                 verbosity=-1,n_jobs=4,random_state=812,deterministic=True,force_col_wise=True)
        learner.fit(np.array(flatx),np.array(flaty));self.ml=learner.booster_
        walk=np.array([e.stay for e in trips if not e.request])
        member_ratio=np.array([e.stay/e.duration for e in trips if e.request and e.show])
        self.walk_mu=float(np.log(walk).mean());self.walk_sigma=float(np.log(walk).std())
        self.member_mu=float(np.log(member_ratio).mean());self.member_sigma=float(np.log(member_ratio).std())
        claims=np.array([(e.arrival-e.minute+e.stay if e.show else e.due-e.minute+21) for e in trips if e.request])
        self.walk_kernel=np.array([(walk>h*BIN).mean() for h in range(H)])
        self.claim_kernel=np.array([(claims>h*BIN).mean() for h in range(H)])
        self.matrix=np.zeros((H,2*H))
        for h in range(H):
            for k in range(h+1):
                self.matrix[h,k]=self.walk_kernel[h-k]
                self.matrix[h,H+k]=self.claim_kernel[h-k]

    def predict_day(self,day):
        origins=np.arange(0,END,BIN)
        x=np.array([history_features(day,int(t)) for t in origins])
        ml_x=np.array([np.r_[f,h] for f in x for h in range(H)])
        learned=np.maximum(0,self.ml.predict(ml_x,num_threads=1)).reshape(len(origins),H)
        linear=np.maximum(0,self.linear.predict(self.scaler.transform(x)))
        mean=np.zeros_like(learned);adaptive=np.zeros_like(learned);public=np.zeros_like(learned);oracle=np.zeros_like(learned)
        for i,t in enumerate(origins):
            past=max(0,int(t)-60)
            rq_ratio=(day.requests[past:t].sum()+3)/(self.profile[day.weekend,0,past:t].sum()+3)
            walk_ratio=(day.walkins[past:t].sum()+20)/(self.profile[day.weekend,1,past:t].sum()+20)
            rq_scale=np.clip(.7*rq_ratio+.3*walk_ratio,.25,4.)
            for h in range(H):
                a=int(t+h*BIN);z=min(END,a+BIN)
                if a<END:
                    mean[i,h]=self.profile[day.weekend,0,a:z].sum()
                    adaptive[i,h]=mean[i,h]*rq_scale
                    public[i,h]=self.profile[day.weekend,1,a:z].sum()*np.clip(walk_ratio,.25,4.)
                    oracle[i,h]=day.requests[a:z].sum()
                if a>=REQUEST_END:learned[i,h]=linear[i,h]=0.
        return {'mean':mean,'adaptive':adaptive,'linear':linear,'ml':learned,'oracle':oracle,'public':public}

    def remaining(self,visible,now):
        # visible tuples contain observed entry, member flag and requested
        # duration only. Future exit times cannot reach this calculation.
        if not visible:return np.zeros(H)
        ages=np.array([now-v[0] for v in visible],float)[:,None]
        member=np.array([v[1] for v in visible],bool)[:,None]
        durations=np.array([v[2] for v in visible],float)[:,None]
        mu=np.where(member,np.log(durations)+self.member_mu,self.walk_mu)
        sigma=np.where(member,self.member_sigma,self.walk_sigma)
        times=ages+np.arange(H)[None,:]*BIN
        survival=ndtr((mu-np.log(np.maximum(times,1e-6)))/sigma)
        present=ndtr((mu-np.log(np.maximum(ages,1e-6)))/sigma)
        result=(survival/np.maximum(present,1e-9)).sum(axis=0)
        result[0]=len(visible)
        return result


def hard_slots(capacity,occupied,pending):return max(0,capacity-occupied-pending-SAFETY)


def plan_protection(capacity,pending,visible,now,demand,public,model,weight):
    started=time.perf_counter();hard=hard_slots(capacity,len(visible),pending)
    if not hard:return 0,0,0.
    residual=model.remaining(visible,now)
    rhs=np.maximum(0,capacity-SAFETY-pending-residual)
    upper=np.r_[hard,public[1:],demand]
    objective=-np.r_[np.ones(H),np.ones(H)*weight*.90]
    solution=linprog(objective,A_ub=model.matrix,b_ub=rhs,bounds=list(zip(np.zeros(2*H),upper)),method='highs')
    if not solution.success:return hard,1,(time.perf_counter()-started)*1000
    allowed=int(np.floor(solution.x[0]+1e-7))
    return max(0,hard-allowed),0,(time.perf_counter()-started)*1000


def simulate(day,capacity,policy,forecast,model,weight=5.,fixed=10,trace=False):
    active=[];pending={};arrivals={};by_time={};reserve=0;trace_rows=[]
    for e in day.events:by_time.setdefault(e.minute,[]).append(e)
    m={k:0 for k in ['requests','accepted','rejected','fulfilled','valid_arrivals','failed','no_shows','expired_late','walkins',
                      'claim_violations','physical_violations','solver_failures']}
    m['idle_protected_bay_hours']=0.;latencies=[];protections=[]
    for now in range(END+205):
        active=[v for v in active if v[3]>now]
        for key,e in list(pending.items()):
            if now>e.due+20:
                pending.pop(key)
                m['no_shows' if not e.show else 'expired_late']+=1
        for e in arrivals.get(now,[]):
            if e.id in pending:
                pending.pop(e.id);m['valid_arrivals']+=1
                if len(active)>=capacity:m['failed']+=1
                else:
                    active.append((now,True,e.duration,now+e.stay));m['fulfilled']+=1
        if now<END and now%BIN==0:
            i=now//BIN
            if policy=='guard':reserve=0
            elif policy.startswith('fixed'):reserve=int(policy[5:])
            elif policy=='calibrated_fixed':reserve=fixed
            elif policy=='reactive':reserve=int(math.ceil(forecast['adaptive'][i,:2].sum()))
            else:
                kind='oracle' if policy=='request_oracle' else policy[3:]
                visible=[v[:3] for v in active]
                reserve,failed,latency=plan_protection(capacity,len(pending),visible,now,forecast[kind][i],forecast['public'][i],model,weight)
                m['solver_failures']+=failed;latencies.append(latency)
            protections.append(reserve)
            if trace:trace_rows.append({'minute':now,'occupied':len(active),'pending':len(pending),'protection':reserve})
        denied=False
        for e in by_time.get(now,[]):
            available=hard_slots(capacity,len(active),len(pending))
            if e.request:
                m['requests']+=1
                if available>0:
                    m['accepted']+=1;pending[e.id]=e
                    if e.show:arrivals.setdefault(e.arrival,[]).append(e)
                    if policy.startswith('lp_') or policy in ['request_oracle','reactive']:
                        reserve=max(0,reserve-1)
                else:m['rejected']+=1
            elif available>reserve:
                active.append((now,False,e.duration,now+e.stay));m['walkins']+=1
            else:denied=True
        if denied:m['idle_protected_bay_hours']+=max(0,capacity-len(active))/60
        m['claim_violations']+=int(len(active)+len(pending)>capacity)
        m['physical_violations']+=int(len(active)>capacity)
    m['weighted_score']=weight*m['fulfilled']+m['walkins']
    m['rejection_rate']=m['rejected']/max(1,m['requests'])
    m['mean_protection']=float(np.mean(protections))
    m['solver_ms_mean']=float(np.mean(latencies)) if latencies else 0.
    return m,np.array(protections),trace_rows


def choose_fixed(cal,predictions,model,weight,capacity=100):
    scores={}
    for buffer in [0,5,10,15,20,30,40]:
        scores[buffer]=float(np.mean([simulate(d,capacity,'calibrated_fixed',predictions[d.seed],model,weight,buffer)[0]['weighted_score'] for d in cal]))
    chosen=max(scores,key=lambda b:(scores[b],-b))
    return chosen,scores


def paired(rows,comparator,metric):
    a={v['seed']:v[metric] for v in rows if v['policy']=='lp_ml'}
    b={v['seed']:v[metric] for v in rows if v['policy']==comparator}
    delta=np.array([a[s]-b[s] for s in sorted(a)])
    boot=np.random.default_rng(812).choice(delta,(2000,len(delta)),replace=True).mean(axis=1)
    return {'comparator':comparator,'metric':metric,'mean_delta':float(delta.mean()),'ci95':[float(x) for x in np.quantile(boot,[.025,.975])]}


def run(days=60,quick=False):
    started=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    print('Fitting shared models and request forecasters...',flush=True)
    train=[make_day(41000+i) for i in range(160 if not quick else 30)]
    calibration=[make_day(51000+i) for i in range(40 if not quick else 8)]
    model=Forecasts(train)
    cal_predictions={d.seed:model.predict_day(d) for d in calibration}
    fixed_choices={}
    for capacity,weight in [(100,1.),(100,5.),(100,10.),(50,5.),(150,5.)]:
        chosen,scores=choose_fixed(calibration,cal_predictions,model,weight,capacity)
        fixed_choices[f'{capacity}:{weight:g}']={'chosen':chosen,'calibration_scores':scores}
    n=min(30,days)
    settings=[('mixed_100','mixed',100,False,5.,days),('quiet','quiet',100,False,5.,n),
              ('unannounced','unannounced',100,False,5.,n),('shifted','shifted',100,False,5.,n),
              ('size_50','mixed',50,False,5.,n),('size_150','mixed',150,False,5.,n),
              ('long_lead','mixed',100,True,5.,n),('weight_1','mixed',100,False,1.,n),('weight_10','mixed',100,False,10.,n)]
    allrows=[];summaries={};forecast_metrics=[];example=[]
    for name,kind,capacity,long_lead,weight,count in settings:
        chosen_buffer=fixed_choices[f'{capacity}:{weight:g}']['chosen']
        rows=[];actions=[];actuals=[];forecasts={k:[] for k in ['mean','adaptive','linear','ml']}
        for j in range(count):
            day=make_day(61000+j,kind,long_lead);pred=model.predict_day(day);day_actions={}
            for policy in POLICIES:
                metrics,protection,trace=simulate(day,capacity,policy,pred,model,weight,chosen_buffer,trace=(name=='mixed_100' and j==0 and policy in ['lp_adaptive','lp_ml']))
                rows.append({'setting':name,'seed':day.seed,'policy':policy,**metrics})
                day_actions[policy]=protection
                if trace:example.append({'policy':policy,'trace':trace})
            actions.append({k:float(np.mean(day_actions[k]!=day_actions['lp_ml'])) for k in ['lp_mean','lp_adaptive','lp_linear']})
            for i,t in enumerate(range(0,REQUEST_END-H*BIN+1,BIN)):
                targets=np.array([day.requests[t+h*BIN:t+(h+1)*BIN].sum() for h in range(H)])
                actuals.append(targets)
                for k in forecasts:forecasts[k].append(pred[k][i])
        policies={p:{k:float(np.mean([v[k] for v in rows if v['policy']==p])) for k in rows[0] if k not in ['setting','seed','policy']} for p in POLICIES}
        comparisons=[paired(rows,p,k) for p in ['guard','calibrated_fixed','lp_mean','lp_adaptive','lp_linear'] for k in ['fulfilled','walkins','weighted_score']]
        score_rows=[];truth=np.array(actuals)
        for horizon in [2,4,8,12]:
            target=truth[:,:horizon].sum(axis=1)
            score_rows.append({'minutes':horizon*BIN,'n':len(target),'models':{k:{'mae':float(np.abs(np.array(v)[:,:horizon].sum(axis=1)-target).mean()),
                             'wape':float(np.abs(np.array(v)[:,:horizon].sum(axis=1)-target).sum()/max(1,target.sum()))} for k,v in forecasts.items()}})
        summaries[name]={'days':count,'capacity':capacity,'member_weight':weight,'kind':kind,'long_lead':long_lead,
                         'fixed_buffer':chosen_buffer,'policies':policies,'paired':comparisons,
                         'different_action_fraction':{k:float(np.mean([v[k] for v in actions])) for k in actions[0]},'forecast_errors':score_rows}
        allrows.extend(rows)
        print(f'Completed {name}: {count} paired days x {len(POLICIES)} policies',flush=True)
    assert all(v[k]==0 for v in allrows for k in ['failed','claim_violations','physical_violations','solver_failures'])
    assert all(v['accepted']==v['fulfilled']+v['no_shows']+v['expired_late'] for v in allrows)
    assert all(v['requests']==v['accepted']+v['rejected'] for v in allrows)
    data=ROOT/'benchmark_data';data.mkdir(exist_ok=True)
    (data/'decision-value-days.json').write_text(json.dumps(allrows),encoding='utf-8')
    report={'date':'2026-11-08','quick_development_run':quick,'train_days':len(train),'calibration_days':len(calibration),
            'policy_day_runs':len(allrows),'runtime_seconds':time.perf_counter()-started,
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((OUT/'protocol.md').read_bytes()).hexdigest(),
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'lightgbm':lgb.__version__},
            'data_kind':'synthetic only','calibrated_buffers':fixed_choices,'settings':summaries,'first_seed_trace':example,
            'limits':['Synthetic cue relationships are assumptions, not measured local behaviour.','Operating score is a service preference, not money.',
                      'Models share as-of information; only request forecasts change between LP variants.',
                      'Oracle is a request-count reference, not a global upper bound.','Accurate observed counts and independent ledger are assumed.',
                      'Exploratory paired intervals do not correct for multiple comparisons.']}
    target=OUT/('development.json' if quick else 'results.json')
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'run_file':str(target),'policy_day_runs':len(allrows),'main_comparisons':summaries['mixed_100']['paired']},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--days',type=int,default=60);parser.add_argument('--quick',action='store_true')
    args=parser.parse_args();run(args.days,args.quick)
