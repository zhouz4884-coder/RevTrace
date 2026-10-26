"""Read-only exact canonical histories and fair-arm input/config recount."""
from pathlib import Path
from collections import defaultdict
import json,hashlib,struct
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def commits(p):
    raw=p.read_bytes();offset=0;out=[]
    while offset<len(raw):
        n=struct.unpack_from('>I',raw,offset)[0];body=raw[offset+4:offset+4+n]
        assert hashlib.sha256(body).digest()==raw[offset+4+n:offset+4+n+32]
        r=json.loads(body);offset+=4+n+32
        if r['kind']=='commit':
            e=r['event'];d=r['state_delta']
            out.append(dict(sid=r['session_id'],parent=r['parent_checkpoint_id'],
                start=d['audio_start_sample'],end=d['audio_end_sample'],Z=d['segment_tokens'],P=d['next_prompt_tokens'],text=e['committed_text']))
    return sorted(out,key=lambda r:(r['sid'],r['parent']))
def main():
    assert any((O/n).exists() for n in ['CAMPAIGN_COMPLETE_v3.json','CAMPAIGN_COMPLETE_v2.json'])
    dest=O/'HISTORY_COMPARISON_v1.json';assert not dest.exists()
    source=read(P/'runtime/SOURCE_MANIFEST.json');checks=[];allrefs=set();ns=set()
    for stage in ['normal','fault','boundary','post_sync']:
        done=read(O/stage/'SUMMARY.json');freeze=read(O/stage/'FREEZE.json');groups=defaultdict(list)
        for name,c in zip(done['completed'],freeze['cells']):
            E=O/stage/name;attempt=1 if (E/'attempt1').exists() else 0;D=E/f'attempt{attempt}'
            cfg=read(D/'config.json');cfg.pop('episode_origin_perf',None)
            specs=read(D/'sessions.json');ids=[s['source_id'] for s in specs];allrefs.update(ids);ns.add(len(set(ids)))
            assert len(ids)==len(set(ids))==c['load']
            normalized=commits(E/'canonical.wal')
            groups[(c['adapter'],c['method'],c['repeat'],c.get('probe'))].append(dict(episode=name,
                arm=[c['readiness'],c['kernel']],normalized_history_sha256=digest(normalized),
                immutable_sources_sha256=digest([(s['source_id'],s['audio_sha256'],s['duration'],s['offset']) for s in specs]),
                config_without_origin_sha256=digest(cfg),commits=len(normalized)))
        for key,items in groups.items():
            assert len({r['immutable_sources_sha256'] for r in items})==1
            if stage in ['normal','fault']:
                assert len(items)==3
                assert len({r['config_without_origin_sha256'] for r in items})==1,'arms changed execution contract or policy'
            checks.append(dict(stage=stage,group=list(key),runs=items,
                exact_canonical_histories_equal=len({r['normalized_history_sha256'] for r in items})==1))
    result=dict(status='COMPLETE_EXACT_HISTORY_AND_FAIR_ARM_RECOUNT',source=source['code_commit'],
        unique_sources_actually_run=sorted(allrefs),unique_source_count=len(allrefs),sessions_per_run=sorted(ns),
        comparisons=checks,not_claimed='population model determinism, independent samples per row, cross-model WER equivalence')
    dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(groups=len(checks),history_equal_groups=sum(c['exact_canonical_histories_equal'] for c in checks))))
if __name__=='__main__':main()
