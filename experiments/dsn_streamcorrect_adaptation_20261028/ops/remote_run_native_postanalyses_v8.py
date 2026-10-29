"""Run only after native controller ends and root releases CPU/IO window."""
import pathlib,json,hashlib,subprocess,sys,os,platform,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
plan=P/'NATIVE_CAMPAIGN_v8_FROZEN.json';controller=O/'native_campaign_v8_continuation_auditfix_v1'
assert (controller/'GATE.json').exists(),'no native controller terminal gate'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'timed GPU window still active'
base=O/'native_postanalyses_v8';base.mkdir(exist_ok=False)
envrec=base/'ENVIRONMENT.json';envrec.write_text(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),dependencies='Python standard library only',native_neural_calls=0),indent=2))
specs=[dict(name='primary_quantiles',prefix='PRIMARY_QUANTILES_SOURCE_v1',commit='776c99d884080818c6f708d9e34e8c6298c59d1b',
 bundle_sha='24d56382d7faba322af7b3b06b2a86a0e7f4f91c21eb669d40984b71c39b2851',script='native_primary_quantiles.py'),
 dict(name='feedback_characterization',prefix='FEEDBACK_CHARACTERIZATION_SOURCE_v1',commit='662859b9978fed35d9f5e118176aa77a84d96154',
 bundle_sha='492e65bf6b42081511c9e40c0c416b917dfccd4cd57ac5b3266f500cd4fd6e72',script='native_feedback_characterization.py')]
results=[]
for spec in specs:
 bundle=P/(spec['prefix']+'.bundle');mf=P/(spec['prefix']+'.json');assert hashlib.sha256(bundle.read_bytes()).hexdigest()==spec['bundle_sha']
 manifest=json.loads(mf.read_text());assert manifest['source_commit']==spec['commit']
 source=P/('postanalysis_'+spec['name']+'_v1')
 if not source.exists():
  subprocess.run(['git','clone','--no-hardlinks',str(bundle),str(source)],check=True)
  subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
  subprocess.run(['git','-C',str(source),'checkout','--detach',spec['commit']],check=True)
 assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==spec['commit']
 assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True)
 assert set(subprocess.check_output(['git','-C',str(source),'ls-files'],text=True).splitlines())=={x['path'] for x in manifest['files']}
 for row in manifest['files']:
  b=(source/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 cfg=base/(spec['name']+'_CONFIG.json');out=base/spec['name']
 config=dict(experiment_id='SC_NATIVE_POST_'+spec['name'].upper()+'_V1',code_commit=spec['commit'],input_plan=str(plan),input_plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
  input_controller_gate=str(controller/'GATE.json'),input_controller_gate_sha256=hashlib.sha256((controller/'GATE.json').read_bytes()).hexdigest(),
  scope='post-run read only; no native outputs, original gates, denominators or source selection changed')
 cfg.write_text(json.dumps(config,indent=2))
 record=dict(experiment_id=config['experiment_id'],code_commit=spec['commit'],source_manifest=str(mf),source_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),
  frozen_config=str(cfg),frozen_config_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),environment_record=str(envrec),environment_record_sha256=hashlib.sha256(envrec.read_bytes()).hexdigest(),
  raw_result_location=str(O/'native_campaign_v8_cells'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 (base/(spec['name']+'_PRELAUNCH_RECORD.json')).write_text(json.dumps(record,indent=2))
 command=[sys.executable,'-B',str(source/spec['script']),'--plan',str(plan),'--out',str(out)]
 if spec['name']=='feedback_characterization':command.extend(['--controller-out',str(controller)])
 e=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
 with (base/(spec['name']+'_PROCESS.log')).open('x') as f:r=subprocess.run(command,env=e,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(name=spec['name'],returncode=r.returncode,gate=json.loads((out/'GATE.json').read_text()) if (out/'GATE.json').exists() else None))
summary=dict(status='COMPLETED_POSTANALYSES_ORIGINAL_NATIVE_GATES_PRESERVED',native_controller_gate=json.loads((controller/'GATE.json').read_text()),original_failed_v8_controller_gate=json.loads((O/'native_campaign_v8_controller/GATE.json').read_text()),corrective_witness_recount_gate=json.loads((O/'witness_recount_auditfix_v1/GATE.json').read_text()),original_witness_gate=json.loads((O/'witness_recount_auditfix_v1/WITNESS_GATE.json').read_text()),analyses=results,
 interpretation='Tool process completion is not evidence that unexecuted conditional formal cells exist; original native gate and each analysis coverage remain explicit.')
(base/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
