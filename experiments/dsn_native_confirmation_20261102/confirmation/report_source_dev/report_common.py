"""Predeclared eight-speaker paired reporting; pure stdlib, no model imports."""
from __future__ import annotations
import csv,hashlib,json,math,pathlib,random,subprocess
NN4F='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
DRIVER='d865af11e9a8d6c451146942d1708a8caed8d1d9'
CHECKER='c4dde9ea9c7abf80fae084bc2293e193262c71e6'
SEED=20261102;DRAWS=20000;SPEAKERS=8;CELLS=32
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
class ReportError(RuntimeError):pass
def need(ok,text):
    if not ok:raise ReportError(text)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def put(path,obj):
    with pathlib.Path(path).open('x',encoding='utf8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvout(path,data):
    with pathlib.Path(path).open('x',encoding='utf8',newline='') as f:
        if data:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
def inventory(paths):return {str(p):dict(bytes=pathlib.Path(p).stat().st_size,sha256=sha(p)) for p in sorted(set(map(str,paths)))}
def verify_inputs(expected):need(inventory(expected)==expected,'frozen report inputs changed')
def identity(manifest):
    root=pathlib.Path(__file__).resolve().parent;m=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root and git('rev-parse','HEAD')==m['source_commit'] and git('cat-file','-t',m['source_commit'])=='commit','report source identity changed')
    need(git('config','--get','core.autocrlf')=='false' and not git('status','--porcelain','--untracked-files=all'),'report source dirty/line conversion enabled')
    need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'complete report manifest differs')
    for r in m['files']:
        p=root/r['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root) and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'report source bytes changed')
    return dict(source_commit=m['source_commit'],manifest_sha256=sha(manifest),complete_files=len(m['files']))
def percentile(values,q):
    need(bool(values),'empty percentile data');v=sorted(values);p=(len(v)-1)*q;i=int(p);j=min(i+1,len(v)-1)
    if math.isinf(v[j]):return math.inf
    return v[i]+(v[j]-v[i])*(p-i)
def finite(v):return v if math.isfinite(v) else None
def run_p99_distribution(values):
    v=[x if x is not None else math.inf for x in values]
    return dict(run_count=len(v),finite_run_count=sum(math.isfinite(x) for x in v),missing_or_unbounded_runs=sum(not math.isfinite(x) for x in v),
        median_seconds=finite(percentile(v,.5)),minimum_seconds=finite(min(v)),maximum_seconds=finite(max(v)),
        null_means='missing/unbounded; never zero; no failed run excluded')
def effect_points(source_rows):
    need(len(source_rows)==SPEAKERS,'bootstrap must use exactly eight speakers')
    diffs=[];cs=fs=ds=0.
    for r in source_rows:
        d=r['offered_audio_s'];c=r['conservative_credit_audio_s'];f=r['fullcall_credit_audio_s']
        need(d>0 and 0<=c<=d+1e-8 and 0<=f<=d+1e-8,'source credit bounds invalid')
        diffs.append(100*(f-c)/d);cs+=c;fs+=f;ds+=d
    return dict(mean_speaker_paired_gain_pp=sum(diffs)/SPEAKERS,
        duration_weighted_ratio_gain_pp=100*(fs/ds-cs/ds),conservative_duration_weighted_coverage_percent=100*cs/ds,
        fullcall_duration_weighted_coverage_percent=100*fs/ds)
def paired_bootstrap(source_rows):
    points=effect_points(source_rows);rng=random.Random(SEED);samples=[]
    for draw in range(DRAWS):
        indices=[rng.randrange(SPEAKERS) for _ in range(SPEAKERS)];chosen=[source_rows[i] for i in indices];e=effect_points(chosen)
        samples.append(dict(draw=draw,sampled_source_indices=','.join(map(str,indices)),**e))
    ci={key:dict(point_estimate=value,lower95=percentile([r[key] for r in samples],.025),upper95=percentile([r[key] for r in samples],.975)) for key,value in points.items()}
    return dict(method='paired nonparametric speaker bootstrap; two timing repeats held together',independent_speakers=SPEAKERS,
        draws=DRAWS,seed=SEED,quantile='linear interpolation at index (n-1)*p',primary_estimand='duration_weighted_ratio_gain_pp',
        secondary_source_consistency_estimand='mean_speaker_paired_gain_pp',intervals=ci,negative_gains_preserved=True),samples

