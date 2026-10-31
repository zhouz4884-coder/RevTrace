"""Read back emitted observations and original bounded rows; never call the reader."""
from pathlib import Path
import hashlib,json,math

E=Path(__file__).resolve().parent
S=E/'figure_snapshot_v1';O=E/'FIGURES_v1'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=load(E/'FIGURE_SOURCE_v1.json');run=load(O/'RUN_RECORD.json')
assert source['code_commit']==run['actual_figure_source_commit']=='73026a11f6db202d723e6028ad85e6833888ec78'
assert run['source_manifest_sha256']==sha(E/'FIGURE_SOURCE_v1.json')
for item in source['files']:
    p=S/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
sm=load(S/'SOURCE_MAP.json')
for item in sm['bounded_inputs']:
    p=S/item['copy'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
data_path=O/'ACTUAL_INTERVAL_COMPARISON.json';before=sha(data_path);data=load(data_path)
assert data['status']=='PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS'
assert not data['same_execution_interleaving'] and not data['paired_counterfactual'] and data['new_model_calls']==0
checked=[]
for arm,r in data['arms'].items():
    rows=load(S/'inputs'/(arm+'_CONSUMER.json'))
    episode=load(S/'inputs'/(arm+'_EPISODE.json'));session=load(S/'inputs'/(arm+'_SESSION.json'))
    assert r['ready_perf']==episode['origin_perf']+session['offset']+224000/16000
    assert r['origin_perf']==episode['origin_perf'] and r['session_offset']==session['offset']
    assert episode['identity']['source_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
    assert r['original_neural_identity']==episode['identity']
    trace=r['complete_trace'];assert len(trace)==len(rows)
    assert [t['input_row'] for t in trace]==list(range(len(rows)))
    for i,(row,t) in enumerate(zip(rows,trace)):
        assert t['t']==row['observed_perf']-r['ready_perf']
        assert t['visible_F']==row['valid_visible_frontier']/16000
        assert t['certified_F']==row['certified_frontier']/16000
        assert t['visible_text_sha256']==hashlib.sha256(row['visible_text'].encode()).hexdigest()
        if i:assert rows[i-1]['observed_perf']<=row['observed_perf']
    first=rows[r['first_visible_row']];cert=rows[r['first_certified_row']]
    assert first['valid_visible_frontier']==r['first_visible_F']==224000
    assert cert['certified_frontier']==r['first_certified_F']==224000
    assert r['first_visible']==first['observed_perf']-r['ready_perf']
    assert r['first_certified']==cert['observed_perf']-r['ready_perf']
    assert r['first_visible_whole_text']==first['visible_text']
    assert r['first_certified_whole_text']==cert['certified_text']
    assert r['first_and_certified_whole_text_equal']==(first['visible_text']==cert['certified_text'])
    assert r['posterior_same_actual_G_text_support'] is True
    assert r['last_observation']==rows[-1]['observed_perf']-r['ready_perf']
    assert r['first_D2_pass']==(r['first_visible']<=2.)
    assert r['first_C8_pass']==(r['first_certified']<=8.)
    for w in r['observed_target_loss_windows']:
        start=rows[w['start_row']];end=rows[w['end_row']]
        assert start['valid_visible_frontier']<224000
        assert w['start']==start['observed_perf']-r['ready_perf']
        assert w['end']==end['observed_perf']-r['ready_perf']
        assert math.isclose(w['gap_seconds'],w['end']-w['start'],abs_tol=1e-12)
        if not w['right_censored']:assert end['valid_visible_frontier']>=224000
        else:assert w['end_row']==len(rows)-1
    # The actual claimed witness routes here are direct one-node inputs.
    # Check those emitted witnesses rather than execute the general chain reader.
    events=load(S/'inputs'/(arm+'_EVENTS.json'))
    records={z['job']['job_id']:z for z in load(S/'inputs'/(arm+'_WORKER_RECORDS.json'))}
    for app in r['canonical_ahead_applications']:
        row=rows[app['row']];prior=rows[app['row']-1]
        assert app['before_visible_F']==prior['valid_visible_frontier']
        assert app['after_visible_F']==row['valid_visible_frontier']
        assert app['whole_view_unchanged']==(prior['visible_text']==row['visible_text'] and prior['valid_visible_frontier']==row['valid_visible_frontier'])
        assert app['classification']=='compatible' and app['reason']=='exact_selected_root' and len(app['chain'])==1
        rec=records[app['chain'][0]]
        commit=next(x for x in events if x['kind']=='commit' and x['version']==row['canonical_version'])
        assert rec['job']['chunk_id']==round(app['selected_F']/32000)
        assert rec['job']['prompt_tokens']==rec['result']['execution_context_audit']['executed_prompt_tokens']==commit['next_prompt_tokens']
    checked.append(dict(arm=arm,rows=len(rows),first_visible_s=r['first_visible'],first_certified_s=r['first_certified'],
        first_view_G=r['first_visible_F'],first_D2_pass=r['first_D2_pass'],first_C8_pass=r['first_C8_pass'],
        actual_loss_windows=len(r['observed_target_loss_windows']),last_observation_s=r['last_observation'],
        direct_complete_witnesses_checked=len(r['canonical_ahead_applications'])))
a,z=data['arms']['R1_S0'],data['arms']['R1_S1']
assert a['first_visible_whole_text']==z['first_visible_whole_text']==a['first_certified_whole_text']==z['first_certified_whole_text']
assert len(a['observed_target_loss_windows'])==1 and not z['observed_target_loss_windows']
assert z['first_visible']>2. and z['first_certified']<8.
assert sha(data_path)==before
out=dict(gate='PASS_INDEPENDENT_EMITTED_COMPARISON_OBSERVATION_QA',
    actual_extraction_commit=run['actual_figure_source_commit'],original_NN_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
    comparison_sha256=before,source_snapshot_files_checked=len(source['files']),input_pins_checked=len(sm['bounded_inputs']),
    arms=checked,same_actual_G_and_whole_text=True,Joint_D2_miss_ms=(z['first_visible']-2.)*1000,
    actual_joint_avoided_old_interleaving_claim=False,first_render_whole_CLI_pass=False,
    whole_CLI_failure='Comparison rendering tick endpoint; reader output already emitted. Must retain original failed invocation.',
    general_reader_real_input_invocations_by_reviewer=0,SSH_calls=0,new_model_calls=0,
    scope='Checks emitted points, texts and direct one-node claimed witnesses against pinned local rows; not a second general-reader run or new service experiment')
with (E/'FIGURE_COMPARISON_ACTUAL_RESULT_REVIEW_v1.json').open('x',encoding='utf8',newline='\n') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out))
