"""Build a bounded anonymous companion, with exact code and path-remapped records."""
from pathlib import Path
import csv, hashlib, io, json, shutil, subprocess, zipfile
E=Path(__file__).resolve().parents[1];R=E.parents[1]
P=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13';A=E/'package_build/anonymous_evidence_v13'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not A.exists();A.mkdir(parents=True)
entries=[];snapshots=[]
REMOTE='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
replacements=[(str(R),'REPOSITORY'),(str(R).replace('\\','/'),'REPOSITORY'),(REMOTE,'EXPERIMENT_DISK'),('C:\\Users\\LENOVO','LOCAL_USER'),('C:/Users/LENOVO','LOCAL_USER')]
def clean(x):
 if isinstance(x,str):
  for old,new in replacements:x=x.replace(old,new)
  return x
 if isinstance(x,list):return [clean(v) for v in x]
 if isinstance(x,dict):return {clean(k):clean(v) for k,v in x.items()}
 return x
def add(src,name,mode='exact'):
 src=Path(src);dst=A/name;dst.parent.mkdir(parents=True,exist_ok=True);b=src.read_bytes()
 if mode=='json_paths':b=(json.dumps(clean(json.loads(b)),indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
 elif mode=='text_paths':b=clean(b.decode('utf-8-sig')).encode()
 dst.write_bytes(b);entries.append(dict(path=name,bytes=len(b),sha256=sha(dst),source_path=src.relative_to(R).as_posix(),source_bytes=src.stat().st_size,source_sha256=sha(src),transformation=mode))
def snapshot(name,source,manifest):
 source=R/source;mp=R/manifest;m=json.loads(mp.read_bytes());commit=m.get('code_commit',m.get('source_commit'))
 git=lambda *args:subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
 assert git('rev-parse','HEAD')==commit and not git('status','--porcelain','--untracked-files=all')
 assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:
  f=source/r['path'];assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256'];add(f,'source_snapshots/'+name+'/'+r['path'])
 add(mp,'source_snapshots/'+name+'/SOURCE_IDENTITY.json','json_paths');snapshots.append(dict(name=name,source_commit=commit,complete_source_files=len(m['files']),source_manifest_sha256=sha(mp),all_source_bytes_exact=True))
snapshot('native_runtime_NN4f','experiments/dsn_native_resilience_20261030/source_v2','experiments/dsn_native_resilience_20261030/packages/SOURCE_v2.json')
snapshot('service_controller','experiments/dsn_native_confirmation_20261102/confirmation/driver_source_v2','experiments/dsn_native_confirmation_20261102/packages/CONFIRMATION_V2_SOURCE.json')
snapshot('production_support','experiments/dsn_strengthening_20261031/paired_resident_source_v2','experiments/dsn_strengthening_20261031/paired_resident_packages_v2/PAIRED_RESIDENT_SOURCE_v2.json')
snapshot('original_endpoint_checker','experiments/dsn_native_refinement_20261030/trace_source_v2','experiments/dsn_native_refinement_20261030/packages/TRACE_SOURCE_v2.json')
snapshot('native_report','experiments/dsn_native_confirmation_20261102/confirmation/report_source_v2','experiments/dsn_native_confirmation_20261102/packages/REPORT_V2_SOURCE.json')
snapshot('recorded_event_accounting','experiments/dsn_v11_closure_20261102/trace_source_v3','experiments/dsn_v11_closure_20261102/packages/TRACE_V3_SOURCE.json')
for p in sorted((E/'figure_source').rglob('*')):
 if p.is_file() and '.git' not in p.relative_to(E/'figure_source').parts and '__pycache__' not in p.parts:
  rel=p.relative_to(E/'figure_source').as_posix();add(p,'figure_source/'+rel,'json_paths' if p.suffix=='.json' else 'exact')
base=R/'experiments/dsn_native_confirmation_20261102/confirmation'
for name in ['PAPER_DATA.json','SUMMARY.json','GATE.json','RUN_RECORD.json','ENVIRONMENT.json','ALL32_CELLS.csv','SOURCE8_PAIRED.csv']:
 p=base/'FINAL_REPORT'/name;add(p,'data/new8/'+name,'json_paths' if p.suffix=='.json' else 'text_paths')
for name in ['SERVICE_PLAN_v1.json','STATISTICAL_PLAN_v1.json','ASSET_BYTE_GATE_v1.json','SERVICE_ASSET_GATE_v1.json']:
 add(base/name,'configurations/'+name,'json_paths')
for p in sorted((base/'service_configs_v1').glob('*.json')):add(p,'configurations/cells/'+p.name,'json_paths')
for name,src in [('COMPLETE_RAW_INPUT_HASH_INDEX.json','experiments/dsn_v11_closure_20261102/analysis/FINAL/INPUT_HASHES_BEFORE.json'),('RAW_CELL_INDEX.json','experiments/dsn_v11_closure_20261102/baseline/RAW_INDEX_v1.json'),('EVENT_ACCOUNTING_SUMMARY.json','experiments/dsn_v11_closure_20261102/analysis/FINAL/SUMMARY.json'),('EVENT_CLAIMS.json','experiments/dsn_v11_closure_20261102/review/EVENT_CLAIMS.json'),('COST_PAPER_DATA.json','experiments/dsn_continuity_cost_20261102/cost/FINAL_AGGREGATE/PAPER_DATA.json')]:
 add(R/src,'data/'+name,'json_paths')
for n in ['ENDPOINTS.csv','SOURCE_DEFICIT_LEDGER.csv']:add(R/'experiments/dsn_v11_closure_20261102/analysis/FINAL'/n,'data/'+n,'text_paths')
for name in ['reproduce_figures.py','verify_reported_statistics.py']:add(E/'ops'/name,name)
readme='''# Anonymous RevTrace DSN companion, editorial v13

This package is a bounded evidence companion, not a new experiment.
The frozen native confirmation has eight speakers, two policies and two
timing repeats (32 trials); selected histories and all metrics are unchanged.

## What is included

- Exact complete file snapshots and identities of NN4f, its service controller,
  production support, the original endpoint checker, the frozen reporting code,
  and the later recorded-event accounting code.
- Frozen model/data configuration records for all 32 cells, statistical plan,
  byte/asset gates, per-run summaries, paired source effects, complete endpoint
  rows and raw-journal hash indices. Location prefixes in JSON/CSV records are
  remapped to EXPERIMENT_DISK or REPOSITORY; numerical values, hashes, source
  commits and experimental identities are retained. MANIFEST.json records both
  the original and packaged digests. This remapping does not relabel a run.
- Editable matplotlib source, five frozen plotting inputs, and reproduction
  commands. Four figures are in the paper; source8_paired_effects is artifact-only.

## Local checks without models

Use Python 3.12+ with matplotlib and PyMuPDF installed:

    python verify_reported_statistics.py
    python reproduce_figures.py --out output_figures

The first command checks the archived 32-row summary, eight paired source
effects, energy normalization and the predeclared 20,000-resample speaker-paired
bootstrap. It does not remeasure raw endpoints. The second reproduces all four
main figures and the optional paired-effect figure, including PDF/SVG outputs.
Both commands first check every packaged file against MANIFEST.json.

## Materials not included

Model weights, recordings, the author StreamCorrect dependency checkout,
environment caches, and full original journals are not redistributed here.
Raw journals remain on the designated experiment disk; their identifiers,
byte lengths and hashes are indexed here. Running the original full endpoint
checkers or service controllers requires those inputs, dependencies and source
identities, with location mappings set appropriately. These source snapshots
are code evidence; their historical README files are not completion gates.
The actual completed run gates are in the data records. No claim of a complete
one-command service rerun is made by this bounded package.
'''
(A/'README.md').write_text(readme,encoding='utf-8')
entries.append(dict(path='README.md',bytes=(A/'README.md').stat().st_size,sha256=sha(A/'README.md'),source_path=None,transformation='new package documentation'))
for p in A.rglob('*'):
 if not p.is_file():continue
 text=p.read_text(encoding='utf-8',errors='replace').lower()
 for token in ['lenovo','vla_qwen','zhouz4884','10.15.1.57','begin private key']:
  assert token not in text,(p.relative_to(A).as_posix(),token)
manifest=dict(scope='Anonymous bounded evidence companion; exact original code snapshots and location-remapped data records',snapshots=snapshots,source_code_changed=False,method_changed=False,new_model_calls=0,full_raw_journals_included=False,weights_included=False,files=entries)
(A/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
archive=P/'RevTrace_DSN2027_anonymous_evidence_v13.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(A.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(A).as_posix())
out=dict(status='BUILT_ANONYMOUS_EVIDENCE_PENDING_FRESH_EXTRACT_CHECK',archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,archive_files=len(entries)+1,snapshots=snapshots,manifest_sha256=sha(A/'MANIFEST.json'),exact_model_runtime_source_unchanged=True,numerical_records_path_remap_only=True,model_weights_or_full_journals_included=False,new_model_calls=0)
(E/'paper_qa/ANONYMOUS_EVIDENCE_BUILD.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8');print(json.dumps(out))
