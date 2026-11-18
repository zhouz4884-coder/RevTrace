"""Read-only Consumer text endpoints for all fourteen completed native cells.

Audio-frontier credit is retained verbatim in meaning. Text event classes and
LCP-versioned code-point occurrences have no token/audio alignment semantics.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter,defaultdict
import argparse,hashlib,json,platform,subprocess,sys

def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def put(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def normalize(text):return ''.join(c for c in text if not c.isspace())
def prefix(a,b):
    n=0
    for x,y in zip(a,b):
        if x!=y:break
        n+=1
    return n
def event_type(before,after):
    n=prefix(before,after)
    return ('unchanged' if before==after else 'strict_append' if n==len(before) else
            'erase_only' if n==len(after) else 'replacement'),n

class Occurrences:
    def __init__(self,cell,source,mode):
        self.cell,self.source,self.mode=cell,source,mode;self.text='';self.active=[];self.closed=[]
    def retire(self,units,observed,closing_row,kind,censored=False):
        groups=[]
        for unit in units:
            if groups and unit['birth_row']==groups[-1][-1]['birth_row'] and unit['offset']==groups[-1][-1]['offset']+1:groups[-1].append(unit)
            else:groups.append([unit])
        for g in groups:
            t=g[0]['first_observed'];assert observed>=t
            self.closed.append(dict(cell_id=self.cell,source_id=self.source,mode=self.mode,
                occurrence_id=f"{g[0]['birth_row']}:{g[0]['offset']}:{g[-1]['offset']+1}",
                first_observed_row=g[0]['birth_row'],first_observed_perf=t,last_observed_perf=observed,
                code_points=len(g),text=''.join(x['char'] for x in g),observed_lifetime_seconds=observed-t,
                retracted=not censored,right_censored_at_last_source_observation=censored,
                closing_row=closing_row,closing_kind=kind))
    def observe(self,text,observed,row,kind):
        classification,n=event_type(self.text,text)
        assert ''.join(x['char'] for x in self.active)==self.text
        self.retire(self.active[n:],observed,row,kind)
        erased=len(self.text)-n;introduced=len(text)-n
        self.active=self.active[:n]+[dict(birth_row=row,offset=i,char=c,first_observed=observed) for i,c in enumerate(text[n:])]
        self.text=text
        return dict(classification=classification,LCP_code_points=n,introduced_code_points=introduced,
            erased_code_points=erased,visible_code_points=len(text),text_empty=not bool(text))
    def finish(self,observed,row):self.retire(self.active,observed,row,'last-source-observation',True)

def analyze_cell(meta,rows,sources,origin):
    by_source=defaultdict(list);trackers={};events=[];last={};classes={}
    for index,r in enumerate(rows):
        sid=r['source_id'];t=r['observed'];assert sid in sources
        if sid in last:assert t>=last[sid]['observed']
        previous=last.get(sid,dict(text='',visible_frontier=0,certified_frontier=0))
        text=r['text'];assert isinstance(text,str)
        ev=dict(cell_id=meta['cell_id'],source_id=sid,row_index=index,kind=r['kind'],observed_perf=t,
            since_original_origin_seconds=t-origin,first_source_snapshot=sid not in last,
            visible_frontier=r['visible_frontier'],certified_processed_frontier=r['certified_frontier'],
            visible_frontier_delta_samples=r['visible_frontier']-previous['visible_frontier'],
            certified_processed_frontier_delta_samples=r['certified_frontier']-previous['certified_frontier'],
            text_sha256=sha(text.encode('utf8')))
        for mode,value in [('raw',text),('whitespace_stripped',normalize(text))]:
            key=sid,mode
            if key not in trackers:trackers[key]=Occurrences(meta['cell_id'],sid,mode)
            ev[mode]=trackers[key].observe(value,t,index,r['kind'])
        events.append(ev);classes[index]=ev;by_source[sid].append((index,r));last[sid]=r
    assert set(by_source)==set(sources)
    spans=[]
    for (sid,mode),tracker in trackers.items():
        end_index,end_row=by_source[sid][-1];tracker.finish(end_row['observed'],end_index);spans.extend(tracker.closed)
    frontiers=[];credit=0.
    for sid,spec in sources.items():
        offered=spec['frames'];past=0
        for F in list(range(8000,offered,8000))+[offered]:
            ready=origin+F/16000
            d=next(((i,r) for i,r in by_source[sid] if r['observed']>=ready and r['visible_frontier']>=F),None)
            c=next(((i,r) for i,r in by_source[sid] if r['observed']>=ready and r['certified_frontier']>=F),None)
            D=d[1]['observed']-ready if d else None;C=c[1]['observed']-ready if c else None
            weight=(F-past)/16000;past=F;ok=D is not None and C is not None and D<=2. and C<=8.
            if ok:credit+=weight
            fr=dict(cell_id=meta['cell_id'],source_id=sid,frontier=F,audio_seconds=weight,
                original_ready_perf=ready,D=D,C=C,original_dual_credit=ok,first_visible_row=d[0] if d else None,
                first_certified_row=c[0] if c else None)
            for mode in ('raw','whitespace_stripped'):
                fr[mode]=dict(first_visible_event_class=classes[d[0]][mode]['classification'] if d else 'not_observed',
                    first_visible_introduced_code_points=classes[d[0]][mode]['introduced_code_points'] if d else None,
                    first_visible_text_empty=classes[d[0]][mode]['text_empty'] if d else None,
                    first_certified_event_class=classes[c[0]][mode]['classification'] if c else 'not_observed')
            frontiers.append(fr)
    summary=dict(meta,actual_consumer_rows=len(rows),sources=len(sources),offered_audio_seconds=sum(x['frames']/16000 for x in sources.values()),
        offered_frontiers=len(frontiers),original_dual_credit_audio_seconds=credit,
        clock='Actual observed perf; final surviving occurrences are right-censored at last actual same-source observation, not hypothetical UI close.')
    for mode in ('raw','whitespace_stripped'):
        ee=[e[mode] for e in events];ss=[s for s in spans if s['mode']==mode];closed=[s for s in ss if s['retracted']]
        buckets={k:sum(f['audio_seconds'] for f in frontiers if f['original_dual_credit'] and f[mode]['first_visible_event_class']==k)
            for k in ('unchanged','strict_append','replacement','erase_only','not_observed')}
        assert abs(sum(buckets.values())-credit)<1e-7
        summary[mode]=dict(row_event_classes=dict(Counter(e['classification'] for e in ee)),
            introduced_code_point_occurrences=sum(e['introduced_code_points'] for e in ee),
            LCP_erased_code_point_occurrences=sum(e['erased_code_points'] for e in ee),
            observed_text_changes=sum(e['classification']!='unchanged' for e in ee),
            positive_F_advance_with_unchanged_text_rows=sum(e['visible_frontier_delta_samples']>0 and e[mode]['classification']=='unchanged' for e in events),
            positive_certified_F_advance_with_unchanged_text_rows=sum(e['certified_processed_frontier_delta_samples']>0 and e[mode]['classification']=='unchanged' for e in events),
            original_credit_by_first_visible_row_class=buckets,
            original_credit_on_whole_text_empty_rows=sum(f['audio_seconds'] for f in frontiers if f['original_dual_credit'] and f[mode]['first_visible_text_empty']),
            retracted_occurrence_code_points=sum(s['code_points'] for s in closed),
            still_visible_occurrence_code_points=sum(s['code_points'] for s in ss if not s['retracted']),
            closed_occurrence_code_point_seconds=sum(s['code_points']*s['observed_lifetime_seconds'] for s in closed),
            longest_closed_observed_lifetime_seconds=max((s['observed_lifetime_seconds'] for s in closed),default=0.),
            final_observed_text_code_points=sum(len(normalize(last[sid]['text']) if mode=='whitespace_stripped' else last[sid]['text']) for sid in last))
        assert summary[mode]['introduced_code_point_occurrences']==summary[mode]['retracted_occurrence_code_points']+summary[mode]['still_visible_occurrence_code_points']
    return summary,events,spans,frontiers

def source_gate(manifest):
    root=Path(__file__).resolve().parent
    git=lambda *args:subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    assert Path(git('rev-parse','--show-toplevel')).resolve()==root
    assert git('rev-parse','HEAD')==manifest['code_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={f['path'] for f in manifest['files']}
    for f in manifest['files']:assert (root/f['path']).stat().st_size==f['bytes'] and sha((root/f['path']).read_bytes())==f['sha256']

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    config=load(a.config);manifest=load(a.source_manifest);source_gate(manifest);out=a.out;out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),executable=sys.executable,new_model_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=manifest['code_commit'],source_manifest_sha256=sha(a.source_manifest.read_bytes()),
        frozen_config_sha256=sha(a.config.read_bytes()),environment_sha256=sha((out/'ENVIRONMENT.json').read_bytes()),measured_neural_commit=config['measured_neural_commit'],
        raw_result_location=[c['path'] for c in config['cells']],aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    inputs={};total=0
    def checked(path,expected,lines=False):
        nonlocal total
        b=Path(path).read_bytes();total+=len(b);assert total<=config['max_input_bytes']
        assert sha(b)==expected;inputs[str(path)]=dict(bytes=len(b),sha256=sha(b))
        return [json.loads(x) for x in b.decode('utf8').splitlines() if x] if lines else json.loads(b)
    try:
        runs=[];events=[];spans=[];frontiers=[]
        assert len(config['cells'])==14
        for cell in config['cells']:
            root=Path(cell['path']);old=checked(root/'CONFIG.json',cell['expected']['config_sha256'])
            origin=checked(root/'ORIGIN.json',cell['expected']['origin_sha256'])
            rows=checked(root/'consumer.jsonl',cell['expected']['consumer_sha256'],True)
            assert old['code_commit']==config['measured_neural_commit'] and old['arm']==cell['arm']
            assert origin['original_D']==2. and origin['original_C']==8.
            sources={s['source_id']:s for s in old['settings']['sources']}
            meta={k:cell[k] for k in ('cell_id','stage','cohort','arm','repeat')}
            rr,ee,ss,ff=analyze_cell(meta,rows,sources,origin['origin_perf'])
            assert rr['offered_frontiers']==cell['offered_frontiers']
            assert abs(rr['offered_audio_seconds']-cell['offered_audio_seconds'])<1e-7
            assert abs(rr['original_dual_credit_audio_seconds']-cell['original_dual_credit_audio_seconds'])<1e-7
            runs.append(rr);events.extend(ee);spans.extend(ss);frontiers.extend(ff)
        for name,v in [('RUNS',runs),('ACTUAL_TEXT_EVENTS',events),('LCP_OCCURRENCE_SPANS',spans),('FIRST_COVER_EVENT_CLASSES',frontiers),('INPUT_HASHES',inputs)]:put(out/(name+'.json'),v)
        total_output=sum(p.stat().st_size for p in out.iterdir() if p.is_file());assert total_output<=config['max_output_bytes']
        source_gate(manifest)
        put(out/'SUMMARY.json',dict(status='COMPLETE_ALL14_NATIVE_TEXT_CONTENT_RECOUNT',cells=len(runs),new_model_calls=0,all_original_credit_unchanged=True,input_bytes=total,
            interpretation='Row-event association and LCP-versioned Unicode code-point occurrences; not new transcript-audio credit, semantic correctness, token/audio alignment, or throughput.'))
        put(out/'GATE.json',dict(gate='PASS_ALL14_ORIGINAL_CREDIT_AND_TEXT_ENDPOINTS',cells=len(runs),new_model_calls=0))
        print(json.dumps(load(out/'SUMMARY.json')))
    except BaseException as e:
        put(out/'GATE.json',dict(gate='FAIL_PRESERVED_NATIVE_TEXT_RECOUNT',exception_type=type(e).__name__,reason=str(e)));raise
if __name__=='__main__':main()
