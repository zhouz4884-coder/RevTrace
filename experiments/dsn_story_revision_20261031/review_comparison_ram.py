"""Independent review controls: synthetic dictionaries only, no measurement inputs."""
from pathlib import Path
from copy import deepcopy
import hashlib,importlib.util,json,sys

E=Path(__file__).resolve().parent
S=E/'figure_source_dev'
sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('reviewed_comparison',S/'extract_comparison.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
before=hashlib.sha256((S/'extract_comparison.py').read_bytes()).hexdigest()
SOURCE='3570-5694-0003'
NN='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
STREAM='69560358173834f45fa284c472bdfab8f284f82ff13034efcc4408a7f492ea04'

def record(jid,role,end,prompt,out,text,chunk):
    return dict(job=dict(job_id=jid,role=role,session_id=7,source_id=SOURCE,
        contract_epoch=1,contract_digest='synthetic-review-only',branch_generation=0,
        audio_end_sample=end,prompt_tokens=prompt,chunk_id=chunk,end_window=chunk+1,
        enqueue_perf=110.),result=dict(token_ids=[len(text)],state_tokens=out,text=text,
        execution_context_audit=dict(executed_prompt_tokens=prompt),received_perf=111.))

def fixture(retain=False,skip_G=False):
    # Purely invented clock/state dictionaries exercise the reader, not NN behavior.
    rows=[];events=[dict(kind='run-start',t0_perf=100.)]
    def row(kind,t,visible,cert,text,ctext,version,jid=None):
        pub=t-100.-.1
        r=dict(source_kind=kind,session_id=7,observed_perf=t,server_time=pub,
            valid_visible_frontier=visible,certified_frontier=cert,
            visible_text=text,certified_text=ctext,canonical_version=version)
        rows.append(r)
        ev=dict(kind=kind,session_id=7,displayed=pub,text=ctext if kind=='canonical-display' else text,
            audio_end_sample=cert if kind=='canonical-display' else visible)
        if jid:ev['job_id']=jid
        events.append(ev)
    row('view-mode',115.,0,0,'','',0)
    row('display',117.25,224000,160000,'alpha','before',5,'j')
    row('canonical-display',117.75,224000 if retain else 192000,192000,
        'alpha' if retain else 'root','root',6,'a6')
    records=[record('j','proposal',224000,[1],[3],'alpha',6),
             record('a6','authority',192000,[0],[1],'root',5)]
    if retain:
        row('display',118.75,256000,192000,'beta','root',6,'k')
        records.append(record('k','proposal',256000,[3],[5],'beta',7))
    end=256000 if skip_G else 224000
    final_text='omega' if skip_G else 'alpha'
    row('canonical-display',119.75,256000 if retain else end,end,
        'beta' if retain else final_text,final_text,7,'a7')
    records.append(record('a7','authority',end,[1],[3],final_text,6))
    for rec,version in [(records[1],6),(records[-1],7)]:
        events.append(dict(kind='commit',version=version,job_id=rec['job']['job_id'],
            audio_end_sample=rec['job']['audio_end_sample'],segment_tokens=rec['result']['token_ids'],
            next_prompt_tokens=rec['result']['state_tokens']))
    return dict(CONSUMER=rows,EVENTS=events,WORKER_RECORDS=records,
        SESSION=dict(session_id=7,source_id=SOURCE,audio_sha256='synthetic-audio',offset=1.75,duration=19.025),
        EPISODE=dict(origin_perf=100.,identity=dict(source_commit=NN,manifest_sha256=STREAM)),
        MANIFEST_ROW=dict(source_id=SOURCE,audio_sha256='synthetic-audio'),PROOF={})

results=[]
def check(name,fn):
    fn();results.append(dict(name=name,pass_=True))
def need(v):
    if not v:raise AssertionError('Independent synthetic control mismatch')
def rejected(data):
    try:m.arm_extract(data,'synthetic')
    except (ValueError,StopIteration):return
    raise AssertionError('Expected fail-closed rejection')

base=fixture()
def compatible_gap():
    r=m.arm_extract(base,'synthetic')
    need(r['first_visible']==1.5 and r['first_certified']==4.)
    need(len(r['observed_target_loss_windows'])==1)
    w=r['observed_target_loss_windows'][0]
    need(w['start']==2. and w['end']==4. and w['gap_seconds']==2. and w['classification']=='compatible')
    need(w['right_censored'] is False and r['last_observation']==4.)
check('full_arm_compatible_withdrawal_and_actual_return',compatible_gap)

def selected_text_separate():
    d=fixture(True);r=m.arm_extract(d,'synthetic')
    need(d['CONSUMER'][-1]['visible_text']=='beta')
    need(r['first_certified_whole_text']=='alpha' and r['first_and_certified_whole_text_equal'])
    need(r['posterior_same_actual_G_text_support'] is True and not r['observed_target_loss_windows'])
check('certified_text_is_not_the_retained_ahead_visible_text',selected_text_separate)

def missing_G():
    r=m.arm_extract(fixture(True,True),'synthetic')
    need(r['first_visible_F']==224000 and r['first_certified_F']==256000)
    need(r['posterior_same_actual_G_text_support'] is None)
check('covering_F_is_not_selected_text_at_actual_G',missing_G)

d=deepcopy(base);d['EPISODE']['identity']['source_commit']='60211b74f78b8420ea48f7a08746aedbbcbfb868'
check('plot_commit_cannot_substitute_for_original_model_commit',lambda:rejected(d))
d=deepcopy(base);d['CONSUMER'][1]['server_time']=30.;d['EVENTS'][2]['displayed']=30.
check('Consumer_use_before_publication_rejected',lambda:rejected(d))
d=deepcopy(base);d['CONSUMER'][-1]['certified_text']='corrupt'
check('canonical_actual_text_binding_rejected',lambda:rejected(d))
d=deepcopy(base);d['WORKER_RECORDS'][0]['job']['audio_end_sample']=256000
check('display_job_target_binding_rejected',lambda:rejected(d))

def necessary_withdrawal():
    d=deepcopy(base);d['WORKER_RECORDS'][0]['job']['prompt_tokens']=[9]
    d['WORKER_RECORDS'][0]['result']['execution_context_audit']['executed_prompt_tokens']=[9]
    r=m.arm_extract(d,'synthetic')
    need(r['observed_target_loss_windows'][0]['classification']=='incompatible')
check('same_frontier_actual_parent_mismatch_is_necessary_withdrawal',necessary_withdrawal)

own=m.controls()
after=hashlib.sha256((S/'extract_comparison.py').read_bytes()).hexdigest()
assert before==after
out=dict(gate='PASS_INDEPENDENT_SYNTHETIC_COMPARISON_READER_REVIEW',
    synthetic_controls=len(results),upstream_controls=own['passed'],checks=results,upstream=own,
    reader_sha256=after,real_input_reader_invocations=0,new_model_calls=0,SSH_calls=0,
    scope='RAM-only constructed dicts; no actual measurement JSON opened by these controls')
p=E/'FIGURE_COMPARISON_RAM_REVIEW_v1.json'
with p.open('x',encoding='utf8',newline='\n') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out))
