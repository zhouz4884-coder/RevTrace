"""Historical development-only contextual physical cost fit, never target labels.

Ridge/robust regression conditions on released audio, declared parent length and
known candidate length, not future generation lengths or injected fault tags.
The same fitted curves are supplied to Cost-only and CES.
"""
from pathlib import Path
import collections,hashlib,json,sys
import numpy as np
B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';D=O/'calibration_v4';assert not D.exists();D.mkdir()
base=json.loads((O/'calibration_v3/CALIBRATION.json').read_text());root=B/'results/revtrace/row_completion_20261023/formal_row_v1'
samples=[];files=[]
def profile(jobs,mode):
 n=len(jobs);a=max(j['audio_end_sample']/16000 for j in jobs)
 return [1.,float(n),sum(j['audio_end_sample']/16000 for j in jobs)/10.,n*a*a/100.,
   n*max(len(j['prompt_tokens']) for j in jobs)/256.,
   n*max((j['audio_end_sample']-j['audio_start_sample'])/16000 for j in jobs)/2.,
   n*max(len(j.get('candidate_token_ids',[])) for j in jobs)/32. if mode=='verify' else 0.]
for p in sorted(root.glob('*/worker_batch_accounting.jsonl')):
 files.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 rs=[json.loads(l) for l in (p.parent/'worker_records.jsonl').read_text().splitlines()];byid={r['job']['job_id']:r for r in rs}
 for line in p.read_text().splitlines():
  ac=json.loads(line);pp=ac['phases'];n=len(ac['job_ids'])
  overhead=max(0.,ac['batch_drained_perf']-ac['worker_started_perf']-sum(q['completed_perf']-q['started_perf'] for q in pp))
  for q in pp:
   mode={'independent-generate':'proposal' if ac['worker'].startswith('proposal') else 'generate','correct-context-strict':'verify','fresh-FP32-fallback':'fallback'}.get(q['phase'])
   if mode is None:continue
   jobs=[byid[jid]['job'] for jid in q['executed_job_ids']]
   # Failed-row fallback retains original padded width. Its expected target
   # profile is priced conservatively using the original whole peer context.
   x=profile(jobs,mode);y=q['completed_perf']-q['started_perf']+(overhead if mode!='fallback' else 0.)
   samples.append({'mode':mode,'x':x,'seconds':y,'cell':p.parent.name,'batch_id':ac['batch_id']})
def fit(X,y):
 scales=np.maximum(np.sqrt((X*X).mean(0)),1.);Z=X/scales;w=np.ones(len(y));coef=np.zeros(X.shape[1])
 for _ in range(15):
  coef=np.linalg.solve(Z.T@(w[:,None]*Z)+.1*np.eye(Z.shape[1]),Z.T@(w*y))
  residual=y-Z@coef;s=max(.02,np.median(abs(residual-np.median(residual)))*1.4826)
  w=np.minimum(1.,1.5*s/np.maximum(abs(residual),1e-9))
 return coef/scales
models={};diagnostics={}
for mode in ['generate','verify','fallback','proposal']:
 rows=[r for r in samples if r['mode']==mode];X=np.array([r['x'] for r in rows]);y=np.array([r['seconds'] for r in rows])
 assert len(rows)>10
 hold=np.array([int(hashlib.sha256(r['cell'].encode()).hexdigest()[:8],16)%5==0 for r in rows])
 assert hold.any() and (~hold).any()
 coef=fit(X[~hold],y[~hold]);pred=np.maximum(.001,X[hold]@coef)
 diagnostics[mode]={'n':len(rows),'held_cell_samples':int(hold.sum()),'held_MAE_s':float(np.median(abs(pred-y[hold]))),
   'held_median_relative_error':float(np.median(abs(pred-y[hold])/y[hold])),'not_serving_benefit':True}
 models[mode]={'coefficients':fit(X,y).tolist(),'feature_order':['intercept','rows','sum_audio_10s','rows_max_audio_sq_100','rows_max_prompt_256','rows_max_interval_2s','rows_max_candidate_32_if_verify'],
   'prediction_floor_s':.001}
base.update(schema='CES-calibration-v4',contextual_cost_models=models,contextual_fit_diagnostics=diagnostics,
 contextual_fit_sources='120 completed development Row study cells only; old72+120 rejection priors retained; validation30 excluded',
 contextual_input_files=files,fit_rule='15 fixed robust-ridge iterations, lambda0.1; deterministic20pct cell holdout for diagnostics; refit all development only',
 fit_frozen_before_v3_pilot=True)
(D/'CALIBRATION.json').write_text(json.dumps(base,indent=2)+'\n')
with (D/'COST_TRAINING_ROWS.jsonl').open('w') as f:
 for r in samples:f.write(json.dumps(r)+'\n')
print(json.dumps({'models':models,'diagnostics':diagnostics},indent=2))
