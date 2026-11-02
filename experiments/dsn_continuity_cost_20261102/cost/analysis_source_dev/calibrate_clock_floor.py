"""Null-target resolution/observer calibration using the unchanged 3cf probe.

This is a CPU measurement control, never legal-service or algorithm evidence.
Nothing from this calibration is subtracted from real protocol measurements.
"""
from __future__ import annotations
import argparse,os,pathlib,platform,sys,time,traceback
from analysis_common import OBSERVER,need,read,put,disk,boot,verify_source,verify_inventory,run_record,quantile

def null_target(value):return value
class Target:value=staticmethod(null_target)

def bracket_call(target,i):
    t0,p0,w0=time.thread_time_ns(),time.process_time_ns(),time.perf_counter_ns()
    value=target(i)
    w1,p1,t1=time.perf_counter_ns(),time.process_time_ns(),time.thread_time_ns()
    return value,dict(wall_ns=w1-w0,thread_cpu_ns=t1-t0,process_cpu_ns=p1-p0)

def batch(target,loops):
    t0,p0,w0=time.thread_time_ns(),time.process_time_ns(),time.perf_counter_ns();checksum=0
    for i in range(loops):checksum+=target(i)
    w1,p1,t1=time.perf_counter_ns(),time.process_time_ns(),time.thread_time_ns()
    need(checksum==loops*(loops-1)//2,'calibration null target result changed')
    return dict(batch_wall_ns=w1-w0,batch_thread_cpu_ns=t1-t0,batch_process_cpu_ns=p1-p0,checksum=checksum)

def summarize_values(data,key):
    v=[r[key] for r in data]
    return dict(count=len(v),minimum=min(v),median=quantile(v,.5),p95=quantile(v,.95),maximum=max(v),unit='ns')

def run(args):
    plan=read(args.config);identity,pre=boot(args.manifest,args.prelaunch,args.config)
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','calibration must explicitly hide CUDA')
    need((plan['loops'],plan['repeats'],plan['warmup'])==(4096,8,512),'clock calibration bounds changed')
    verify_inventory(plan['terminal_inputs'])
    terminal=read(plan['NN_terminal_gate']);need(terminal['status']=='COMPLETE_FROZEN_COST_NN_CAMPAIGN','NN16 must be terminal before clock work')
    observer=verify_source(plan['observer_source'],plan['observer_manifest'],OBSERVER)
    sys.path.insert(0,plan['observer_source']);from cost_probe import CostProbe
    out=disk(plan['raw_result_location']);out.mkdir(parents=True,exist_ok=False)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),analysis=identity,original_probe=observer,
        CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),clock_order='t0 threadCPU; p0 processCPU; w0 wall; target; w1 wall; p1 processCPU; t1 threadCPU',
        clocks={n:dict(implementation=time.get_clock_info(n).implementation,resolution=time.get_clock_info(n).resolution,monotonic=time.get_clock_info(n).monotonic,adjustable=time.get_clock_info(n).adjustable) for n in ('perf_counter','thread_time','process_time')})
    run_record(out,'COST_NULL_TARGET_CLOCK_FLOOR_CALIBRATION_V1',identity,plan,env)
    result=[];loops=plan['loops'];warmup=plan['warmup']
    try:
        for repeat in range(plan['repeats']):
            values={};order=('bare','wrapped') if repeat%2==0 else ('wrapped','bare')
            for mode in order:
                if mode=='bare':
                    for i in range(warmup):need(Target.value(i)==i,'bare warmup changed target')
                    values[mode]=batch(Target.value,loops)
                else:
                    probe=CostProbe(out/f'wrapped_r{repeat}','calibration_null_target',True,max_spans=loops+warmup)
                    probe.wrap(Target,'value','CALIBRATION.null_target')
                    try:
                        for i in range(warmup):need(Target.value(i)==i,'wrapped warmup changed target')
                        values[mode]=batch(Target.value,loops)
                        spans=probe.rows[warmup:]
                        need(len(spans)==loops and all(r['parent_span_id'] is None for r in spans),'null probe count/depth differs')
                        values['wrapped_inner_spans']={k:summarize_values(spans,k) for k in ('wall_ns','thread_cpu_ns','process_cpu_ns')}
                        values['wrapped_inner_wall_less_than_thread_count']=sum(r['wall_ns']<r['thread_cpu_ns'] for r in spans)
                    finally:probe.close()
            # Bare per-call bracket is a separate diagnostic. It has identical
            # clock ordering but does not pay the probe's RAM bookkeeping.
            bare=[]
            for i in range(loops):
                value,row=bracket_call(Target.value,i);need(value==i,'bare bracket target changed');bare.append(row)
            with (out/f'bare_brackets_r{repeat}.jsonl').open('x',encoding='utf8') as stream:
                import json
                for row in bare:stream.write(json.dumps(row,separators=(',',':'))+'\n')
            values['bare_single_call_bracket']={k:summarize_values(bare,k) for k in ('wall_ns','thread_cpu_ns','process_cpu_ns')}
            values['bare_bracket_wall_less_than_thread_count']=sum(r['wall_ns']<r['thread_cpu_ns'] for r in bare)
            values.update(repeat=repeat,order=list(order),loops=loops,warmup=warmup,
                batch_wrapped_minus_bare={k:values['wrapped'][k]-values['bare'][k] for k in ('batch_wall_ns','batch_thread_cpu_ns','batch_process_cpu_ns')})
            result.append(values)
        verify_inventory(plan['terminal_inputs'])
        put(out/'SUMMARY.json',dict(status='PASS_FIXED_NULL_TARGET_CLOCK_CALIBRATION',observer_source=OBSERVER,analysis_source=identity['source_commit'],loops=loops,repeats=plan['repeats'],warmup=warmup,
            repeats_data=result,scope='null target clock/observer resolution control; not protocol function cost',
            lower_reference_only=True,subtraction_from_real_footprints=False,wall_CPU_brackets_differ=True,
            wall_less_than_thread_is_not_negative_blocking=True,metadata_depth_and_object_costs_may_differ_in_real_calls=True))
        put(out/'GATE.json',dict(status='PASS_FIXED_NULL_TARGET_CLOCK_CALIBRATION',new_neural_calls=0))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_CLOCK_CALIBRATION_PRESERVED',failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('config','manifest','prelaunch'):p.add_argument('--'+n,required=True)
    run(p.parse_args())

