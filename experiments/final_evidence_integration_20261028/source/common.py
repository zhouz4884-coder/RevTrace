"""Read-only, indexed evidence access. No runtime/model/admission imports."""
from pathlib import Path
import hashlib,json,platform,re,subprocess,sys


def wire(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return hashlib.sha256(wire(x)).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def config_value(x):
    if isinstance(x,Path):return str(x)
    if isinstance(x,(list,tuple)):return [config_value(v) for v in x]
    if isinstance(x,dict):return {k:config_value(v) for k,v in x.items()}
    return x


class Evidence:
    def __init__(self,root,indices):
        self.root=Path(root);self.expected={};self.used={}
        for p in indices:
            for r in load(p)['files']:
                old=self.expected.get(r['path'])
                if old:assert old['sha256']==r['sha256'] and old['bytes']==r['bytes']
                self.expected[r['path']]=r
    def raw(self,relative):
        p=(self.root/relative).resolve();assert p.is_relative_to(self.root.resolve())
        r=self.expected[relative];b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],relative
        self.used[relative]=dict(path=relative,bytes=len(b),sha256=r['sha256']);return b
    def json(self,p):return json.loads(self.raw(p))
    def lines(self,p):return [json.loads(x) for x in self.raw(p).splitlines() if x]


def begin(args,kind):
    source=load(args.source_manifest);root=Path(__file__).parent
    assert re.fullmatch('[0-9a-f]{40}',source['code_commit'])
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==source['code_commit']
    assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip()
    tracked=subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines()
    assert set(tracked)=={r['path'] for r in source['files']},'incomplete source manifest'
    for r in source['files']:assert file_sha(root/r['path'])==r['sha256']
    out=Path(args.out);assert not out.exists();out.mkdir(parents=True)
    env=dict(python=sys.version,platform=platform.platform(),GPU_inference_calls=0)
    put(out/'ENVIRONMENT.json',env)
    put(out/'FREEZE.json',dict(experiment_id='REVTRACE-FINAL-EVIDENCE-'+kind+'-20261028',code_commit=source['code_commit'],source_manifest_sha256=file_sha(args.source_manifest),config=config_value(vars(args)),environment_sha256=file_sha(out/'ENVIRONMENT.json'),input_indices={str(p):file_sha(p) for p in args.indices},raw_result_location=str(out),aggregate_summary_location=str(out/'RESULT.json'),gate_decision_location=str(out/'GATE.json'),GPU_inference_calls=0))
    return source,Evidence(args.root,args.indices)


def put(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
