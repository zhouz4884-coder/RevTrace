"""Historical evidence/provenance inventory; no model call, no gate relabeling."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,importlib.util,json


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists();R=a.archive;inputs=[]
    def read(rel):
        b=(R/rel).read_bytes();inputs.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));return json.loads(b)
    traced=read('results/r7_efsc/whisper_base_quality/paired-128-traced.json')
    manifest=read('results/r8_csdr/whisper-w-quality-manifest.json');records={x['utterance_id']:x for x in manifest['records']}
    counts=Counter();roots=[];allsources=[]
    for s in traced['sessions']:
        wc,we=s['canonical_wer'],s['efsc_wer'];bad=(we-wc>10 or (we>2*max(wc,1) and we-wc>5))
        assert bad==s['catastrophic_outlier']
        ids=s['utterance_ids'];allsources+=ids
        assert all(uid in records for uid in ids)
        counts['sessions']+=1;counts['catastrophic']+=bad
        if not bad:continue
        end=0;intervals=[]
        for i,uid in enumerate(ids):
            if i:end+=1600
            start=end;end+=records[uid]['samples'];intervals.append(dict(utterance_id=uid,start=start,end=end))
        splits=[dict(frontier_sample=f,utterance_id=next((x['utterance_id'] for x in intervals if x['start']<f<x['end']),None))
                for f in range(160000,1440000,160000)]
        trace=s['efsc_trace']
        roots.append(dict(session_id=s['session_id'],split=s['split'],canonical_wer=wc,efsc_wer=we,
            feedback_off_wer=s['feedback_off_wer'],utterance_ids=ids,
            unique_speakers=len({records[u]['speaker_id'] for u in ids}),
            source_chunks=intervals,window_boundaries_from_metadata=splits,
            window_boundaries_inside_utterance=sum(x['utterance_id'] is not None for x in splits),
            actions=dict(Counter(e['decision_action'] for e in trace)),
            short_EOS_windows=[dict(window=e['window_index'],tokens=len(e['candidate_token_ids']),
                prompt_tokens=e['prompt_tokens_for_proposal'],action=e['decision_action']) for e in trace
                if e['terminated_by_eos'] and len(e['candidate_token_ids'])<=10],
            scope='Concatenated multi-utterance metadata reconstruction; no claim that an internal utterance cut intersects a word.'))
    counts['unique_utterances']=len(set(allsources));counts['utterance_reuse']=len(allsources)-len(set(allsources))
    trials=[]
    for path in sorted((R/'results/r8_csdr').glob('*.json')):
        d=read(str(path.relative_to(R)).replace('\\','/'))
        if not isinstance(d,dict) or 'metrics' not in d:continue
        trials.append(dict(file=path.name,study=d.get('study'),decision=d.get('decision'),
            selection=d.get('selection'),view=d.get('view'),metrics=d['metrics'],
            config=d.get('config'),claim_boundary=d.get('claim_boundary')))
    sp=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);c=m.ssh_client();sf=c.open_sftp();sf.get_channel().settimeout(30)
    base='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
    remote=[]
    try:
        for rel in ['projects/revtrace_r7_0849660/CODE_COMMIT',
                    'projects/revtrace_r7_0849660/SOURCE_MANIFEST.json',
                    'projects/revtrace_r7_0849660/ENVIRONMENT.json',
                    'projects/revtrace_r7_0849660/scripts/remote/run_r7_whisper_quality.py',
                    'projects/revtrace_r7_0849660/scripts/remote/run_r8_csdr_quality.py',
                    'projects/revtrace_r7_0849660/src/revtrace/feedback_coherence.py',
                    'logs/revtrace/r7_efsc/whisper_base_quality/paired-128.log',
                    'datasets/revtrace/librispeech/whisper-w-quality.json']:
            path=base+'/'+rel
            try:
                stat=sf.stat(path)
                if stat.st_size>4000000:
                    remote.append(dict(path=path,status='EXISTS_NOT_LOADED_OVER_4MB',bytes=stat.st_size));continue
                b=sf.open(path).read();row=dict(path=path,status='READ',bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
                if rel.endswith('CODE_COMMIT'):row['current_marker']=b.decode().strip()
                if rel.endswith('.log'):row['header']=b.decode(errors='replace')[:4000]
                remote.append(row)
            except FileNotFoundError:remote.append(dict(path=path,status='MISSING'))
    finally:sf.close();c.close()
    report=dict(status='COMPLETE_READ_ONLY_HISTORICAL_FEASIBILITY_AUDIT',archive_root=str(R),
        historical_execution_commit='UNKNOWN unless an independently matching original source manifest/log is recovered',
        counts=dict(counts),R7_contract=traced['config'],R7_roots=roots,R8_trials=trials,
        remote_current_observations_not_execution_proof=remote,inputs=inputs,new_GPU_calls=0,
        scientific_gate='NO_GO_FOR_CLAIMING_R7_APPROX_ERASURE_AS_CURRENT_EXACT_PATH_DEFECT; further faithful reproduction/current-contract test require new freeze',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(counts=dict(counts),roots=[dict(id=x['session_id'],speakers=x['unique_speakers'],
        internal_cuts=x['window_boundaries_inside_utterance'],short_EOS_windows=len(x['short_EOS_windows'])) for x in roots],
        R8_metric_artifacts=len(trials),remote=remote),indent=2))


if __name__=='__main__':main()
