"""Metadata-only next-source reserve, no model calls and no new campaign."""
from pathlib import Path
import json,hashlib
import soundfile as sf
import numpy as np
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def main():
    manifest=B/'projects/revtrace_dependability_20261025/ck5_v6/INDEPENDENT_MANIFEST_v1.json';known=json.loads(manifest.read_text())['sessions']
    used={s['source_id'] for s in known};speakers={s['source_id'].split('-')[0] for s in known}
    data=B/'datasets/revtrace/librispeech_dev/LibriSpeech/dev-clean';options=[]
    for p in data.glob('*/*/*.flac'):
        sid=p.stem
        if sid in used or sid.split('-')[0] in speakers:continue
        info=sf.info(p)
        if info.samplerate!=16000 or info.channels!=1 or not 12<=info.duration<=30:continue
        rank=hashlib.sha256(('LP1-next-metadata-v1/'+sid).encode()).hexdigest();options.append((rank,p,info.duration))
    chosen=[];seen=set()
    for rank,p,duration in sorted(options):
        speaker=p.stem.split('-')[0]
        if speaker in seen:continue
        seen.add(speaker);v,rate=sf.read(p,dtype='float32');ref=p.parent/('-'.join(p.stem.split('-')[:2])+'.trans.txt')
        reference=next(l.split(' ',1)[1] for l in ref.read_text().splitlines() if l.startswith(p.stem+' '))
        chosen.append(dict(source_id=p.stem,speaker=speaker,path=str(p),duration=duration,rank=rank,audio_sha256=hashlib.sha256(np.asarray(v,dtype='<f4').tobytes()).hexdigest(),
            reference=reference,reference_source_sha256=hashlib.sha256(ref.read_bytes()).hexdigest()))
        if len(chosen)==8:break
    result=dict(status='METADATA_RESERVED_NOT_EXECUTED',sessions=chosen,count=len(chosen),target=8,
        exclusion_manifest=str(manifest),exclusion_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        rule='metadata hash order,12-30s,distinct speaker not in known CK5/N5 manifest; no model output selection',
        limitation='disjointness established only against identified frozen manifest, not every historical RevTrace source; full manifest audit required before a held-out claim')
    (O/'NEXT_SOURCE_RESERVE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],count=len(chosen))))
if __name__=='__main__':main()
