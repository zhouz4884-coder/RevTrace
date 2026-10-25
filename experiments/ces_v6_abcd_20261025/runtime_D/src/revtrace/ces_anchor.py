"""Small Fine-anchored evidence choice; forecasts never authorize state."""
import math
import numpy as np
from .ces_v5_policy import predict_batch,_row_cdf

def quantile(values,q):
    values=sorted(values);i=(len(values)-1)*q;a=int(i)
    return values[a] if a==len(values)-1 else values[a]+(i-a)*(values[a+1]-values[a])

def features(rows):
    n=len(rows)
    return [max(t.audio_seconds for t in rows)/20.,max(t.prompt_tokens for t in rows)/256.,
        max(t.candidate_tokens for t in rows)/256.,sum(t.candidate_tokens for t in rows)/n/256.,
        sum(t.same_birth for t in rows)/n,sum(t.previous_reject for t in rows)/n]

def fixed_count_marginals(probabilities,k):
    """P(row fails | sum failures=k), weighted subsets, not independent K."""
    n=len(probabilities)
    if k==0:return [0.]*n
    if k==n:return [1.]*n
    odds=[max(.01,min(.99,p))/(1-max(.01,min(.99,p))) for p in probabilities]
    left=[[0.]*(k+1) for _ in range(n+1)];right=[[0.]*(k+1) for _ in range(n+1)]
    left[0][0]=right[n][0]=1.
    for i,w in enumerate(odds):
        for j in range(k+1):left[i+1][j]=left[i][j]+(w*left[i][j-1] if j else 0.)
    for i in range(n-1,-1,-1):
        for j in range(k+1):right[i][j]=right[i+1][j]+(odds[i]*right[i+1][j-1] if j else 0.)
    return [min(1.,max(0.,odds[i]*sum(left[i][j]*right[i+1][k-1-j] for j in range(k))/left[n][k])) for i in range(n)]

class ConditionalRiskModel:
    def __init__(self,table):
        self.table={}
        for op,records in table.items():
            for n in {r['n'] for r in records}:
                bank=[r for r in records if r['n']==n]
                self.table[op,n]=(bank,np.asarray([r['x'] for r in bank],dtype=np.float64))

    def predict(self,op,rows,options):
        bank,xs=self.table.get((op,len(rows)),([],None));support=len(bank)
        if support<int(options.get('minimum_support',8)):return None,support
        x=np.asarray(features(rows));indices=np.argsort(np.square(xs-x).sum(axis=1),kind='stable')[:min(16,support)]
        ranked=[bank[int(i)] for i in indices];flat=[r for b in ranked for r in b['rows']]
        vectors=np.asarray([r['x'] for r in flat],dtype=np.float64);nearby={};ps=[]
        for t in rows:
            target=np.asarray([t.audio_seconds/20.,t.prompt_tokens/256.,t.candidate_tokens/256.,float(t.same_birth),float(t.previous_reject)])
            ids=np.argsort(np.square(vectors-target).sum(axis=1),kind='stable')[:min(8,len(flat))]
            near=[flat[int(i)] for i in ids];nearby[t.sid]=near
            ps.append((sum(r.get('failed',False) for r in near)+.5)/(len(near)+1))
        scenarios=[]
        for sample in ranked:
            failures=fixed_count_marginals(ps,int(sample['K'])) if op=='verify' else [0.]*len(rows)
            row_models={}
            for t,p in zip(rows,failures):
                near=nearby[t.sid];values=[]
                for bad,mass in [(False,1-p),(True,p)]:
                    if mass<=0:continue
                    subset=[r for r in near if bool(r.get('failed',False))==bad]
                    if not subset:
                        values.append((mass,sample['lease']));continue
                    for r in subset:
                        if op=='generate':at=sample['lease']*r['fraction']
                        elif bad:at=sample['fallback_start']+sample['fallback_time']*r['fraction']+r.get('render_overhead',0.)
                        else:at=sample['verify_start']+sample['verify_time']*r['fraction']+r.get('render_overhead',0.)
                        values.append((mass/len(subset),min(sample['lease'],max(0.,at))))
                row_models[t.sid]=values
            scenarios.append({'weight':1./len(ranked),'lease':sample['lease'],'K':sample['K'],'rows':row_models})
        return scenarios,support

def conditional_batch(cal,op,rows,options,predictor=None):
    """Observed complete-batch samples retain correlated K and phase costs.

    Row identity changes its completion distribution using known input features.
    Sparse support is returned explicitly; no future output length is supplied.
    """
    model=predictor or ConditionalRiskModel(cal.get('v6_joint_risk',{}))
    scenarios,support=model.predict(op,rows,options)
    if scenarios is None:
        ds=predict_batch(cal,op,rows)
        answer=[]
        for d in ds:
            times,cdf,_=_row_cdf(d)
            distribution=[(cdf[i+1]-cdf[i],at) for i,at in enumerate(times)]
            answer.append({'weight':d.weight,'lease':d.lease,'K':d.reject_fraction*len(rows),'rows':{t.sid:distribution for t in rows}})
        return answer,False,support
    return scenarios,True,support

def evaluate_plan(plan,all_rows,*,now,cal,options,observed_rate=0.,predictor=None):
    """At most two homogeneous physical calls, same complete target set."""
    cursor=now;credit=0.;lower_credit=0.;upper_credit=0.;work=0.;late_risk=0.;supports=[]
    delivery=float(cal.get('v5_risk_model',{}).get('owner_delivery_seconds',0.))
    for op,rows in plan:
        ds,supported,n=conditional_batch(cal,op,rows,options,predictor);supports.append({'op':op,'n':len(rows),'samples':n,'supported':supported})
        leases=[s['lease'] for s in ds];upper=quantile(leases,float(options.get('risk_quantile',.9)))
        lower=quantile(leases,.1);mean=sum(s['weight']*s['lease'] for s in ds)
        for t in rows:
            probabilities=[]
            for s in ds:
                p=0.
                for mass,finish in s['rows'][t.sid]:
                    at=cursor+finish+delivery
                    if at<=t.deadline and (t.display_met or (not t.display_expired and at<=t.ready+2.)):p+=mass
                probabilities.append(min(1.,max(0.,p)))
            w=max(0.,t.audio_weight);credit+=w*sum(s['weight']*p for s,p in zip(ds,probabilities))
            lower_credit+=w*min(probabilities);upper_credit+=w*max(probabilities)
            late_risk+=w*sum(s['weight']*float(cursor+s['lease']+delivery>t.deadline) for s in ds)
        cursor+=upper;work+=mean
    return {'credit':credit,'lower_credit':lower_credit,'upper_credit':upper_credit,
        'upper_wall':cursor-now+delivery,'mean_work':work,'late_audio_risk':late_risk,
        'supports':supports,'all_supported':all(x['supported'] for x in supports)}

def choose_anchor(rows,*,now,cal,options,deferrals=None,risk=None,observed_rate=0.,predictor=None):
    rows=tuple(sorted(rows,key=lambda t:(t.ready,t.sid)))
    baseline=[('generate',rows)]
    if not rows:return {'operation':None,'sids':[],'reason':'anchor-no-released-target'}
    candidates=tuple(t for t in rows if t.candidate_ready)
    if not candidates:return {'operation':'generate','sids':[t.sid for t in rows],'reason':'anchor-no-ready-candidate',
        'plan':[{'operation':'generate','sids':[t.sid for t in rows]}],'prediction_not_authorization':True}
    plans=[baseline]
    if len(candidates)==len(rows):plans.append([('verify',rows)])
    # One declared prefix candidate, not a search over every partition.
    urgent=tuple(sorted(candidates,key=lambda t:(t.deadline if t.display_met else min(t.deadline,t.ready+2.),t.sid))[:4])
    ids={t.sid for t in urgent};rest=tuple(t for t in rows if t.sid not in ids)
    if rest:plans.append([('verify',urgent),('generate',rest)])
    stats=[evaluate_plan(p,rows,now=now,cal=cal,options=options,observed_rate=observed_rate,predictor=predictor) for p in plans]
    reference=stats[0];chosen=0;forced={t.sid for t in rows if (deferrals or {}).get(t.sid,0)>=2}
    scores=[]
    for i,(plan,s) in enumerate(zip(plans,stats)):
        extra_risk=0.
        if risk and options.get('policy')=='causal':
            # Only a separately randomized and frozen causal estimate may price
            # future, unissued work. Already running work is never reclaimable.
            extra_risk=sum(float(risk.get(t.sid,0.)) for op,rs in plan[1:] for t in rs)
        gain=s['lower_credit']-reference['upper_credit']
        saving=reference['mean_work']-s['mean_work']
        utility=s['credit']-observed_rate*s['upper_wall']-extra_risk
        safe_queue=s['late_audio_risk']<=reference['late_audio_risk']+1e-12
        viable=(i>0 and s['all_supported'] and reference['all_supported'] and safe_queue and
            forced<={t.sid for t in plan[0][1]} and
            ((gain>1e-9 and s['upper_wall']<=reference['upper_wall']*1.05) or
             (s['lower_credit']>=reference['upper_credit']-1e-12 and saving>max(.03,.1*reference['mean_work']))))
        scores.append({'index':i,'viable':viable,'conservative_credit_gain':gain,'predicted_work_saving':saving,
            'future_unissued_risk':extra_risk,'utility':utility,**s})
        if viable and (chosen==0 or utility>scores[chosen]['utility']):chosen=i
    op,first=plans[chosen][0]
    return {'operation':op,'sids':[t.sid for t in first],'reason':'fine-anchor-default' if chosen==0 else 'fine-anchor-supported-deviation',
        'plan':[{'operation':op,'sids':[t.sid for t in rs]} for op,rs in plans[chosen]],
        'anchor_scores':scores,'chosen_index':chosen,'forced_sids':sorted(forced),
        'planning_time_compensated_now':now,'prediction_not_authorization':True,
        'no_performance_lower_bound':True,'wait_seconds':0.}
