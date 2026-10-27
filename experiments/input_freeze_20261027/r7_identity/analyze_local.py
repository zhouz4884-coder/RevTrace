"""Read-only metadata/Git-object comparison; no imports from execution source."""
from pathlib import Path
import hashlib,json,random,subprocess
P=Path(__file__).resolve().parent
A=Path(r'D:\VLA_QWEN\RevTrace\.execution\archive_main')
R=Path(r'D:\VLA_QWEN\RevTrace')
RP=P/'remote_files/projects/revtrace_r7_0849660'
manifest=json.loads((P/'remote_files/datasets/revtrace/librispeech/whisper-w-quality.json').read_text())
paired=json.loads((A/'results/r7_efsc/whisper_base_quality/paired-128.json').read_text())
traced=json.loads((A/'results/r7_efsc/whisper_base_quality/paired-128-traced.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
commits=['2112157301fc36ab6d9b2e70e918a9f42dd52b2c','b911e882a838f076ed15d291c2adf0a4315ee068','2b4eb55539de26b956a5e6fe088e6088b9b72635']
files=['scripts/remote/run_r7_whisper_quality.py','scripts/remote/run_r7_whisper_quality.sh',
 'scripts/remote/run_whisper_w_quality.py','scripts/remote/whisper_batched_executor.py',
 'src/revtrace/feedback_coherence.py','src/revtrace/feedback_metrics.py','src/revtrace/whisper_state.py']
matches=[]
for name in files:
 row=dict(path=name,current_remote_sha256=sha(RP/name),archive_sha256=sha(A/name),commits={})
 for commit in commits:
  q=subprocess.run(['git','-C',str(R),'show',commit+':'+name],capture_output=True)
  if q.returncode:row['commits'][commit]=dict(status='UNKNOWN',error=q.stderr.decode('utf8','replace'))
  else:
   digest=hashlib.sha256(q.stdout).hexdigest();row['commits'][commit]=dict(sha256=digest,remote_match=digest==row['current_remote_sha256'])
 matches.append(row)
recipes=[]
for split,seed in [('test-clean',2026080701),('test-other',2026080702)]:
 available=[r for r in manifest['records'] if r['split']==split];random.Random(seed).shuffle(available)
 for i in range(64):
  ids=[];samples=0;scan=0
  while scan<len(available) and samples<1440000:
   row=available[scan];inc=row['samples']+(1600 if ids else 0)
   if ids and samples+inc>1440000:scan+=1;continue
   row=available.pop(scan);ids.append(row['utterance_id']);samples+=inc
  if samples<1080000:raise AssertionError('metadata first-fit insufficient')
  sid=i+(0 if split=='test-clean' else 64)
  recipes.append(dict(session_id=sid,split=split,utterance_ids=ids,unpadded_samples=samples,
   tail_zero_samples=max(0,1440000-samples),matches_recorded=ids==paired['sessions'][sid]['utterance_ids']))
fields=['session_id','split','utterance_ids','canonical_text','efsc_text','feedback_off_text','canonical_wer','efsc_wer','catastrophic_outlier']
diff=[]
for a,b in zip(paired['sessions'],traced['sessions']):
 changed=[k for k in fields if a[k]!=b[k]]
 if changed:diff.append(dict(session_id=a['session_id'],fields=changed))
out=dict(current_remote_CODE_COMMIT=(RP/'CODE_COMMIT').read_text().strip(),
 historical_quality_execution_commit='UNKNOWN: output and log do not bind loaded source or environment',
 source_files=matches,seed_recipe_matches=sum(r['matches_recorded'] for r in recipes),sessions=recipes,
 paired_vs_traced_changed_rows=diff,quality_outliers=[r['session_id'] for r in paired['sessions'] if r['catastrophic_outlier']],
 original_paired_sha256=sha(A/'results/r7_efsc/whisper_base_quality/paired-128.json'),
 original_traced_sha256=sha(A/'results/r7_efsc/whisper_base_quality/paired-128-traced.json'),
 original_paired_top_keys=list(paired),traced_top_keys=list(traced),
 original_session_keys=list(paired['sessions'][0]),traced_session_keys=list(traced['sessions'][0]),
 warning='Current remote CODE_COMMIT and current env are observations, not historical execution attestation')
(P/'LOCAL_RECONCILIATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('source_files','sessions')}))
print(json.dumps(dict(source_matches={r['path']:{c:x.get('remote_match') for c,x in r['commits'].items()} for r in matches})))
