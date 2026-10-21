"""Bounded legal scheduling counterfactuals. NO GPU or serving performance claims."""
import hashlib,importlib.util,json,platform,sys
from pathlib import Path
import numpy as np
W=Path(__file__).resolve().parent;SDK=W/'sdk';sys.path.insert(0,str(SDK/'src'))
from revtrace.live_qwen import LiveQwenScheduler
spec=importlib.util.spec_from_file_location('cf_fixture',SDK/'tests/test_live_qwen.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
out=W/'cpu_counterfactuals';out.mkdir(exist_ok=False)
scenarios=[('self-dependency',1,1,1,'decoupled',.001,.03),('self-dependency',1,1,2,'decoupled',.001,.03),
    ('capacity-first-transition',2,3,1,'decoupled',.001,.02),('capacity-first-transition',2,3,2,'decoupled',.001,.02),
    ('barrier-pending-result',1,3,1,'segment',.025,.001),('barrier-pending-result',1,3,1,'decoupled',.025,.001)]
results=[]
for index,(scenario,count,rho,workers,barrier,pdelay,adelay) in enumerate(scenarios):
    histories=[];runs=[]
    for repeat in range(2):
        clock=fixture.Clock();reference=fixture.build(count=count,rho=rho)
        config=dict(reference.contract,rho=rho,microbatch=1,proposal_barrier=barrier,proposal_reconciliation='lazy',
            display_protocol='canonical-snapshot-v1',publish_canonical_display=True,blocking_instrumentation=True,timeout_seconds=10)
        specs=[{'session_id':sid,'source_id':str(sid),'language':'English','offset':0.,
            'audio':np.zeros(960,dtype='<f4').tobytes()} for sid in range(count)]
        sched=LiveQwenScheduler(sessions=specs,contract=config,clock=clock,sleep=clock.sleep,emit=lambda e:None,
            executors={'proposal':[fixture.Fake('p',clock,pdelay)],
                       'authority':[fixture.Fake('a'+str(i),clock,adelay) for i in range(workers)]})
        result=sched.run();jobs=[e for e in sched.events if e['kind']=='enqueue' and e['role']=='authority']
        commits=[e for e in sched.events if e['kind']=='commit'];first=[e for e in jobs if e['parent']==0]
        history={sid:[{'Z':list(t)} for t in s.state.stable_token_segments] for sid,s in sched.sessions.items()}
        expected=tuple((window,) for window in range(rho,7,rho))
        assert all(s.state.stable_token_segments==expected and s.state.prompt_tokens==(6,) for s in sched.sessions.values())
        row={'experiment_id':f'CPU-CF-{index}-R{repeat}','scenario':scenario,'sessions':count,'authority_workers':workers,
            'rho':rho,'barrier':barrier,'proposal_delay_fixture':pdelay,'authority_delay_fixture':adelay,
            'clock_domain':'deterministic Fake Clock; not GPU time','evidence':'CPU_SYNTHETIC_LEGAL_SCHEDULING_COUNTERFACTUAL',
            'first_target_ready_to_enqueue':[e['enqueue_perf']-e['audio_ready_perf'] for e in first],
            'all_target_ready_to_enqueue':[e['enqueue_perf']-e['audio_ready_perf'] for e in jobs],
            'first_commit':min(e['installed'] for e in commits),'canonical_oracle':history,
            'config':config,'raw_trace':sched.events}
        path=out/(row['experiment_id']+'.json');path.write_text(json.dumps(row,indent=2)+'\n')
        runs.append({k:v for k,v in row.items() if k not in ['raw_trace','config']});histories.append(history)
        sched.close()
    assert histories[0]==histories[1]
    results.append({'scenario':scenario,'workers':workers,'barrier':barrier,'runs':runs})
# Capacity cannot shorten a single session's required ancestry chain here.
assert results[0]['runs'][0]['all_target_ready_to_enqueue']==results[1]['runs'][0]['all_target_ready_to_enqueue']
assert max(results[2]['runs'][0]['first_target_ready_to_enqueue'])>max(results[3]['runs'][0]['first_target_ready_to_enqueue'])
assert results[4]['runs'][0]['first_commit']>results[5]['runs'][0]['first_commit']
summary={'decision':'PASS_LEGAL_COUNTERFACTUALS','results':results,'environment':platform.python_version(),
    'scheduler_sha256':hashlib.sha256((SDK/'src/revtrace/live_qwen.py').read_bytes()).hexdigest(),
    'interpretation':'Separates existence of semantic self-dependency, other-session capacity and private barrier holds; does NOT assign causal percentages to measured GPU waits.'}
(W/'CPU_BLOCKING_COUNTERFACTUALS.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'decision':summary['decision'],'configurations':6,'repeats_per_configuration':2,
    'self_one_vs_two_workers_same_wait':True,'capacity_control_improves_first_transition':True,'barrier_can_hold_after_gpu_result':True}))
