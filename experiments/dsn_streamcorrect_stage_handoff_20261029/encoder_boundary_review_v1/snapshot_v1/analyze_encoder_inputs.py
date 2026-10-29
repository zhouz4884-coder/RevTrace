"""Static boundary/input witness only. Never imports torch or executes a model."""
import argparse,ast,copy,datetime,hashlib,json,pathlib,platform,subprocess
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def key(start,end):
    return dict(ordered_buffer_segments=start['audio_segments'],
        added_immutable_audio=dict(source_sha256=start['contract']['source_sha'],begin=start['frontier'],end=end),
        complete_static_contract=start['contract'],
        caveat='Conservative structural PCM+static key, not an implemented cache or empirical E equality proof')
def controls(start,end):
    k=key(start,end);rows=[]
    for field in ('tokens','transcript','last_attend_frame','context'):
        s=copy.deepcopy(start);s[field]=dict(changed_feedback=True)
        assert key(s,end)==k;rows.append(dict(control='feedback_'+field,encoder_structural_key_same=True))
    for what in ('source','segment','end','static'):
        s=copy.deepcopy(start);e=end
        if what=='source':s['contract']['source_sha']='f'*64
        if what=='segment':s['audio_segments'][0]['sha256']='e'*64
        if what=='end':e+=1
        if what=='static':s['contract']['dtype']='bfloat16'
        assert key(s,e)!=k;rows.append(dict(control='different_'+what,encoder_structural_key_same=False))
    return rows
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);cfg=read(ap.parse_args().config)
    src=pathlib.Path(__file__).resolve().parent
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip();assert commit==cfg['source_commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
    for name,h in cfg['source_files'].items():assert sha(src/name)==h
    for path,h in cfg['input_files'].items():assert sha(pathlib.Path(path))==h
    pilot=pathlib.Path(cfg['pilot']);ledger=read(pilot/'FULLSPEC_LEDGER.json');dispatches=read(pilot/'DISPATCHES.json')
    jobs=[json.loads(x) for x in (pilot/'native_jobs.jsonl').read_text(encoding='utf-8').splitlines()]
    rows=[]
    for a in ledger['abandoned']:
        matches=[b for b in jobs if b['record']['start']==a['start']['frontier'] and b['record']['end']==a['target_end']]
        assert len(matches)==1;b=matches[0];sa=a['start'];sb=b['start'];end=a['target_end']
        same=key(sa,end)==key(sb,end);assert same
        assert sa['audio_segments']==sb['audio_segments'] and sa['contract']==sb['contract']
        assert [k for k in sa if sa[k]!=sb[k]]==['tokens','transcript']
        assert end/16000<sa['contract']['audio_buffer_seconds']
        rows.append(dict(wrong_job=a['job_id'],correct_fallback=b['job_id'],start=sa['frontier'],end=end,
            changed_complete_cut_fields=[k for k in sa if sa[k]!=sb[k]],ordered_audio_descriptor_count=len(sa['audio_segments']),
            buffered_samples=sum(x['samples'] for x in sa['audio_segments']),added_samples=end-sa['frontier'],
            audio_structural_key_sha256=hashlib.sha256(json.dumps(key(sa,end),sort_keys=True).encode()).hexdigest(),
            structural_audio_and_static_key_equal=same,old_gpu=a['gpu'],new_gpu=b['gpu'],cross_gpu=a['gpu']!=b['gpu'],
            old_worker_begin=a['worker_job_begin_perf'],old_worker_end=a['worker_job_end_perf'],
            correct_model_start=b['record']['model_start'],correct_model_end=b['record']['model_end'],
            actual_encoder_ready_time_recorded=False,actual_encoder_tensor_comparison_performed=False))
    author=pathlib.Path(cfg['author_infer']);tree=ast.parse(author.read_text(encoding='utf-8'))
    infer=next(n for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='infer')
    enc=next(n for n in infer.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='encoder_feature')
    assert ast.unparse(enc.value)=='self.model.encoder(mel)'
    output=dict(status='PASS_STATIC_READSET_AND_FOUR_ACTUAL_STRUCTURAL_AUDIO_INPUT_WITNESSES',
        source_commit=commit,rows=rows,controls=controls(ledger['abandoned'][0]['start'],ledger['abandoned'][0]['target_end']),
        actual_speculative_dispatches=sum(x['start_sha']!=x['birth_canonical_sha'] for x in dispatches),
        author_encoder_call_line=enc.lineno,author_encoder_call=ast.unparse(enc),
        encoder_ready=False,neural_oracle_run=False,cache_implemented=False,
        conclusion='Four full feedback starts differ while audio encoder structural inputs agree; actual mel/E numerical equality, readiness, copy cost and service benefit remain unmeasured.')
    out=pathlib.Path(cfg['out']);out.mkdir(exist_ok=False)
    for name,obj in [('SUMMARY.json',output),('GATE.json',dict(status=output['status'],scope='static CPU/source and existing actual descriptor checks only')),
        ('CONFIG.json',cfg),('ENVIRONMENT.json',dict(python=platform.python_version(),torch_imported=False,gpu_calls=False)),
        ('RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],source_commit=commit,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_inputs=cfg['input_files'],summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json')))]:
        (out/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=output['status'],pairs=len(rows),controls=len(output['controls']),summary_sha256=sha(out/'SUMMARY.json'))))
if __name__=='__main__':main()
