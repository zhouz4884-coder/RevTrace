"""Pure CPU sensitivity on previously audited all-offered latency rows."""
from __future__ import annotations
import csv,hashlib,json,math,pathlib,re,subprocess,sys
NN4F='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
SOURCE_RECEIPT_SHA='2040995aa06a5c7958479fe42397d65e299c8a4505de18b35f44099edd9e3b9e'
SOURCES=('BAC009S0905W0246','BAC009S0908W0369','BAC009S0913W0313','BAC009S0916W0463')
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
class GateError(RuntimeError):pass
def need(ok,text):
    if not ok:raise GateError(text)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def put(path,obj):
    with pathlib.Path(path).open('x',encoding='utf8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def csvout(path,data):
    with pathlib.Path(path).open('x',encoding='utf8',newline='') as f:
        if data:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
def verify_inputs(expected):
    for p,r in expected.items():need(pathlib.Path(p).stat().st_size==r['bytes'] and sha(p)==r['sha256'],'frozen input changed: '+p)
def verify_self(manifest):
    root=pathlib.Path(__file__).resolve().parent;m=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root,'not independent sensitivity source')
    need(git('rev-parse','HEAD')==m['source_commit'] and git('cat-file','-t',m['source_commit'])=='commit','source HEAD unresolved')
    need(git('config','--get','core.autocrlf')=='false' and not git('status','--porcelain','--untracked-files=all'),'source dirty or line conversion enabled')
    need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'source complete manifest differs')
    for row in m['files']:
        p=root/row['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root) and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'source bytes differ')
    # Original endpoint implementation is copied byte-for-byte, not redefined.
    dep=read(root/'DEPENDENCIES.json')
    for row in dep['files']:need(sha(root/'vendor'/row['path'])==row['sha256'],'original endpoint dependency changed')
    sys.path.insert(0,str(root/'vendor'))
    return dict(source_commit=m['source_commit'],manifest_sha256=sha(manifest),complete_files=len(m['files']),original_endpoint_source=dep['source_commit'])
def nearly(a,b,tol=1e-8):return (a is None and b is None) or (a is not None and b is not None and abs(a-b)<=tol)
def credit(rows,tau):
    return sum(r['audio_seconds'] for r in rows if r['D'] is not None and r['D']<=tau and r['C'] is not None and r['C']<=8.)
def denominator(rows):return sum(r['audio_seconds'] for r in rows)
def validate_source_extent(rows,spec):
    need(rows[-1]['frontier']==spec['frames'] and nearly(denominator(rows),spec['frames']/16000,1e-10),'source-specific original EOS/frame extent changed')
    need(spec['header']['sample_rate']==16000 and spec['header']['frames']==spec['frames'],'original source receipt frame contract changed')
def validate_primary(primary,sid=None,origin=None):
    from endpoints import quantile,finite
    rows=primary['frontiers'];need(rows,'missing original offered rows')
    sources={r['source_id'] for r in rows}
    need(sid is None or sources=={sid},'request mixed source identities')
    for source in sources:
        own=[r for r in rows if r['source_id']==source];last=own[-1]['frontier'];expected=list(range(8000,last,8000))+[last]
        need([r['frontier'] for r in own]==expected,'cadence/EOS obligations missing or repeated')
        previous=0;origins=[]
        for r in own:
            need(r['is_EOS'] is (r['frontier']==last),'EOS identity changed')
            need(nearly(r['audio_seconds'],(r['frontier']-previous)/16000,1e-12),'duration weight changed');previous=r['frontier']
            need(all(r[k] is None or (isinstance(r[k],(int,float)) and math.isfinite(r[k]) and r[k]>=0) for k in ('D','C')),'invalid original latency')
            need(r['D2'] is (r['D'] is not None and r['D']<=2.) and r['C8'] is (r['C'] is not None and r['C']<=8.),'original deadline flags changed')
            origins.append(r['offer']-r['frontier']/16000)
        need(max(origins)-min(origins)<1e-6,'one request mixed original clocks')
        if origin is not None:need(max(abs(x-origin) for x in origins)<1e-6,'resident request origin rebased')
    ds=[r['D'] if r['D'] is not None else math.inf for r in rows];cs=[r['C'] if r['C'] is not None else math.inf for r in rows]
    d99,c99=finite(quantile(ds,.99)),finite(quantile(cs,.99))
    need(nearly(d99,primary['primary_linear_all_offered_D99']) and nearly(c99,primary['primary_linear_all_offered_C99']),'original unweighted linear P99 changed')
    expected=dict(offered_frontiers=len(rows),offered_audio_seconds=denominator(rows),dual_deadline_audio_credit_seconds=credit(rows,2.),
        D2_misses_all_offered=sum(not r['D2'] for r in rows),C8_misses_all_offered=sum(not r['C8'] for r in rows),
        EOS_D2_misses=sum(r['is_EOS'] and not r['D2'] for r in rows),missing_D_frontiers=sum(r['D'] is None for r in rows),missing_C_frontiers=sum(r['C'] is None for r in rows))
    for key,value in expected.items():need(nearly(value,primary[key]),'original accounting changed: '+key)
    passed=all(v is not None for v in (d99,c99)) and d99<=2. and c99<=8. and not expected['missing_D_frontiers'] and not expected['missing_C_frontiers']
    need(primary['complete_coverage_and_original_quantile_pass'] is passed,'original whole-request pass changed')
    return dict(**expected,D99=d99,C99=c99,original_D2_C8_pass=passed)

