"""Strict full-WAV acquisition contracts, no model imports."""
from __future__ import annotations
import hashlib,io,json,pathlib,re,subprocess,sys,wave
ARCHIVE_URL='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/StreamCorrect.zip'
SPLIT_DIRECTORY='StreamCorrect/aishell1_testset'
SPLIT_NAMESPACE='AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96'
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
class AcquisitionError(RuntimeError):pass
class TechnicalHeaderError(AcquisitionError):pass
class IndependenceError(AcquisitionError):pass
def need(ok,text):
    if not ok:raise AcquisitionError(text)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def bytes_sha(data):return hashlib.sha256(data).hexdigest()
def put(path,obj,replace=False):
    with pathlib.Path(path).open('w' if replace else 'x',encoding='utf8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def disk(path):
    p=pathlib.Path(path);need(p.is_absolute() and p.resolve().is_relative_to(B.resolve()),'new data outside designated8TB');return p
def verify_source(manifest):
    root=pathlib.Path(__file__).resolve().parent;m=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root and git('rev-parse','HEAD')==m['source_commit'] and git('cat-file','-t',m['source_commit'])=='commit','independent full source identity changed')
    need(git('config','--get','core.autocrlf')=='false' and not git('status','--porcelain','--untracked-files=all'),'dirty source or line conversion')
    need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'source manifest incomplete')
    for row in m['files']:
        p=root/row['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root) and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'source bytes changed')
    dep=read(root/'DEPENDENCIES.json');need(sha(root/'vendor'/'acquire_selected.py')==dep['sha256'],'verified original ZIP/Range helper changed')
    return dict(source_commit=m['source_commit'],source_manifest_sha256=sha(manifest),complete_files=len(m['files']),verified_transport_dependency=dep)
def validate_metadata(selection,rule,expected):
    need(selection['status']=='PASS_STRICT_SAME_SPLIT_METADATA_SELECTION_PENDING_AUDIO','metadata not locked PENDING_AUDIO')
    need(selection['metadata_first'] is True and selection['model_calls']==0 and selection['new_reference_text_read'] is False and selection['new_WAV_bytes_read'] is False,'metadata-first prerequisite changed')
    need(selection['selected_speaker_count']==selection['selected_utterance_count']==expected and expected>0,'frozen actualN changed')
    need(selection['original_split']==rule['split_namespace']==SPLIT_NAMESPACE and rule['duration_seconds']==[8,9],'strict split/duration contract changed')
    groups=selection['selected_sources'];need(len(groups)==expected and len({g['speaker_id'] for g in groups})==expected,'missing/duplicate frozen speakers')
    need(not {g['speaker_id'] for g in groups}&set(selection['excluded_speakers']),'frozen historical speaker collision')
    for g in groups:
        order=g['technical_header_fallback_order'];need(order and g['archive_member']==order[0] and g['source_id']==order[0]['source_id'],'frozen primary/cyclic fallback changed')
        need(len({e['source_id'] for e in order})==len(order),'fallback repeats member')
        for e in order:
            match=re.fullmatch(r'BAC009(S\d{4})W\d{4}',e['source_id'])
            need(match and match.group(1)==e['speaker_id']==g['speaker_id'],'fallback changed speaker')
            need(e['path']==SPLIT_DIRECTORY+'/'+e['source_id']+'.wav' and e['method'] in (0,8),'fallback not original strict test WAV')
            need(8<=(e['bytes']-44)/32000<=9 and e['compressed']>0 and e['local_offset']>=0,'frozen candidate metadata outside band')
    return groups
def original_reference_map(references,allowed):
    # Same original public reference.json fields as verified1129; no text
    # normalization, quality scoring or outcome-based candidate replacement.
    ref={}
    for row in references:
        sid=pathlib.PurePosixPath(row.get('audio_path','')).stem;text=row.get('text_zh','')
        if sid in allowed and text:
            need(sid not in ref or ref[sid]==text,'conflicting original transcript reference')
            ref[sid]=text
    return ref
def inspect_pcm(data):
    try:
        with wave.open(io.BytesIO(data)) as w:
            h=dict(channels=w.getnchannels(),sample_width=w.getsampwidth(),sample_rate=w.getframerate(),frames=w.getnframes(),compression=w.getcomptype());pcm=w.readframes(w.getnframes())
    except (wave.Error,EOFError,ValueError) as exc:raise TechnicalHeaderError('invalid_original_WAV_header') from None
    if h['channels']!=1 or h['sample_width']!=2 or h['sample_rate']!=16000 or h['compression']!='NONE':raise TechnicalHeaderError('requires_original_PCM16_mono_16k')
    if len(pcm)!=h['frames']*2:raise TechnicalHeaderError('truncated_original_PCM')
    return dict(h,PCM_sha256=bytes_sha(pcm),duration=h['frames']/16000)
def check_duration(header):
    if not 128000<=header['frames']<=144000:raise TechnicalHeaderError('actual_original_duration_outside_8to9')
def check_independence(wav_hash,pcm_hash,excluded,accepted):
    if wav_hash in excluded or (pcm_hash is not None and pcm_hash in excluded):raise IndependenceError('historical_WAV_or_PCM_hash_collision_STOP')
    if wav_hash in accepted or (pcm_hash is not None and pcm_hash in accepted):raise IndependenceError('new_selected_WAV_or_PCM_hash_collision_STOP')

