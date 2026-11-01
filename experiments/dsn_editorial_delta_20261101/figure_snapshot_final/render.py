"""Formal general renderer with immutable source, scenes and v7 data."""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
import matplotlib,numpy,fitz
import base_renderer as b
import draw_mechanism as dm
import draw_time as dt
import draw_statistics as ds
from numeric_reuse import core_rows,native_rows
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,d):p.write_bytes((json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def git(*args):return subprocess.check_output(['git','-C',str(HERE),*args],text=True).strip()
def environment():return dict(python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,numpy=numpy.__version__,pymupdf=fitz.VersionBind,new_model_calls=0,actual_reader_calls=0)
def gate(path):
 d=json.loads(path.read_bytes());c=git('rev-parse','HEAD');assert Path(git('rev-parse','--show-toplevel')).resolve()==HERE
 assert not git('status','--porcelain','--untracked-files=all') and c==d['code_commit']
 assert set(git('ls-files').splitlines())=={r['path'] for r in d['files']}
 for r in d['files']:assert (HERE/r['path']).stat().st_size==r['bytes'] and sha(HERE/r['path'])==r['sha256']
 return c
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--environment',type=Path,required=True);ap.add_argument('--root-preflight',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 c=gate(a.manifest);root=json.loads(a.root_preflight.read_bytes());assert root['gate']=='SOURCE_IDENTITY_PASS' and root['code_commit']==c and root['manifest_sha256']==sha(a.manifest)
 env=json.loads(a.environment.read_bytes());assert env==environment()
 controls={str(p.resolve()):sha(p) for p in [a.manifest,a.environment,a.root_preflight,HERE/'CONFIG.json',HERE/'SOURCE_MAP.json',HERE/'SCENE.json',HERE/'COLOUR_SCENE.json']}
 sm=json.loads((HERE/'SOURCE_MAP.json').read_bytes());cfg=json.loads((HERE/'CONFIG.json').read_bytes());assert cfg['input_map_sha256']==sha(HERE/'SOURCE_MAP.json')
 j={}
 for r in sm['bounded_inputs']:
  p=HERE/r['copy'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'] and sha(r['original'])==r['sha256'];j[r['key']]=json.loads(p.read_bytes())
 for r in sm['protected']:assert Path(r['path']).stat().st_size==r['bytes'] and sha(r['path'])==r['sha256']
 for r in sm['dependencies']:assert sha(HERE/r['path'])==r['sha256'] and sha(r['original'])==r['sha256']
 numeric=dict(core=core_rows(j),native=native_rows(j));assert numeric==j['original_numeric_values']
 out=a.out.resolve();out.mkdir(exist_ok=False)
 put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],source_commit=c,manifest_sha256=sha(a.manifest),config_sha256=sha(HERE/'CONFIG.json'),environment_sha256=sha(a.environment),actual_interval_analysis_commit=sm['actual_interval_analysis_commit'],raw_input_location='Frozen bounded copies; original service raw stays on designated8TB',intended_summary=str(out/'SUMMARY.json'),intended_gate=str(out/'GATE.json'),new_model_calls=0,actual_reader_calls=0))
 put(out/'CONTROL_HASHES_BEFORE.json',controls);put(out/'ENVIRONMENT.json',env)
 b.style();dm.PREVIEW_MODE=False;dt.PREVIEW_MODE=False;ds.PREVIEW_MODE=False
 qa=[dt.comparison(out,j),dm.draw(out),ds.core(out,j),ds.native(out,j)]
 assert gate(a.manifest)==c and {p:sha(p) for p in controls}==controls
 for r in sm['bounded_inputs']:assert sha(HERE/r['copy'])==r['sha256'] and sha(r['original'])==r['sha256']
 for r in sm['protected']:assert sha(r['path'])==r['sha256']
 put(out/'CONTROL_HASHES_AFTER.json',controls);put(out/'MAIN_EFFECT_NUMERIC_VALUES.json',numeric);put(out/'ACTUAL_INTERVAL_COMPARISON.json',j['actual_interval_comparison'])
 put(out/'SUMMARY.json',dict(figures=4,source_commit=c,actual_interval_analysis_commit=sm['actual_interval_analysis_commit'],new_model_calls=0,actual_reader_calls=0,all_6_inputs_and_80_protected_unchanged=True,numeric_values_equal_v7=True,QA=qa))
 put(out/'GATE.json',dict(gate='PASS_FROZEN_APPROVED_COLOUR_FIGURES_NUMERIC_VECTOR',visual_review='PENDING_ACTUAL_VIEW',new_model_calls=0,actual_reader_calls=0))
 put(out/'OUTPUT_INDEX.json',[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file()])
 print(json.dumps(dict(source_commit=c,out=str(out),figures=4,new_model_calls=0,actual_reader_calls=0)))
if __name__=='__main__':main()
