"""Independent arithmetic/paired-bootstrap check of the frozen reported summaries."""
from pathlib import Path
import csv, hashlib, json, math, random
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'MANIFEST.json').read_bytes())
for row in manifest['files']:
 p=ROOT/row['path'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
data=json.loads((ROOT/'data/new8/PAPER_DATA.json').read_bytes())
cells=list(csv.DictReader((ROOT/'data/new8/ALL32_CELLS.csv').open(encoding='utf-8-sig',newline='')))
pairs=list(csv.DictReader((ROOT/'data/new8/SOURCE8_PAIRED.csv').open(encoding='utf-8-sig',newline='')))
assert len(cells)==32 and len(pairs)==8 and len({c['speaker_id'] for c in cells})==8
near=lambda a,b:abs(a-b)<1e-8
for policy,expected in data['policies'].items():
 selected=[r for r in cells if r['policy']==policy];assert len(selected)==16
 for key,col in [('offered_audio_s','offered_audio_s'),('credit_audio_s','credit_audio_s'),('common_model_drain_board_J','common_model_drain_board_J')]:
  actual=sum(float(r[col]) for r in selected)
  if key in expected:assert near(actual,expected[key]),(policy,key)
 assert sum(r['D2_C8_pass']=='True' for r in selected)==expected['D2_C8_passes']
 assert all(r['task_reference_equal']=='True' for r in selected)
 energy=sum(float(r['common_model_drain_board_J']) for r in selected)
 assert near(energy/sum(float(r['offered_audio_s']) for r in selected),expected['J_per_offered_audio_s'])
assert sum(int(r['checked_original_steps']) for r in cells)==564
for r in pairs:
 sid=r['speaker_id'];arms={p:[c for c in cells if c['speaker_id']==sid and c['policy']==p] for p in ['conservative','fullcall']}
 for policy in arms:assert len(arms[policy])==2 and near(sum(float(c['credit_audio_s']) for c in arms[policy]),float(r[policy+'_credit_audio_s']))
 assert float(r['paired_gain_pp'])>0
def effect(chosen):
 offered=sum(float(r['offered_audio_s']) for r in chosen)
 c=sum(float(r['conservative_credit_audio_s']) for r in chosen);f=sum(float(r['fullcall_credit_audio_s']) for r in chosen)
 return 100*(f/offered-c/offered)
def percentile(v,q):
 v=sorted(v);x=(len(v)-1)*q;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
rng=random.Random(20261102);samples=[effect([pairs[rng.randrange(8)] for _ in range(8)]) for _ in range(20000)]
ci=data['bootstrap']['intervals']['duration_weighted_ratio_gain_pp']
assert near(effect(pairs),ci['point_estimate']) and near(percentile(samples,.025),ci['lower95']) and near(percentile(samples,.975),ci['upper95'])
print(json.dumps(dict(gate='PASS_FROZEN_SUMMARY_ARITHMETIC_AND_PAIRED_BOOTSTRAP',independent_sources=8,trials=32,selected_transitions=564,paired_gain_pp=effect(pairs),lower95=percentile(samples,.025),upper95=percentile(samples,.975),new_model_calls=0,scope='Verifies archived summaries and fixed bootstrap; does not remeasure raw endpoints or rerun models')))
