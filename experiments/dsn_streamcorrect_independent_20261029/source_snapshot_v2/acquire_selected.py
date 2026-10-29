"""Four preselected public ZIP members. No transcript-based selection or models."""
import argparse,datetime,hashlib,io,json,os,pathlib,platform,struct,subprocess,time,urllib.error,urllib.request,wave,zlib
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())
def verify_staged(stage):
    b=pathlib.Path(stage['path']).read_bytes()
    if len(b)!=stage['bytes'] or hashlib.sha256(b).hexdigest()!=stage['sha256']:raise ValueError('staged same-source Range size/SHA mismatch')
    return b
def extract_member(raw,entry):
    if len(raw)<30:raise ValueError('truncated local ZIP header')
    v=struct.unpack_from('<4s5H3L2H',raw)
    if v[0]!=b'PK\x03\x04' or v[3]!=entry['method']:raise ValueError('ZIP local header/method mismatch')
    pos=30+v[-2]+v[-1]
    if raw[30:30+v[-2]].decode('utf-8')!=entry['path']:raise ValueError('ZIP member filename mismatch')
    comp=raw[pos:pos+entry['compressed']]
    if len(comp)!=entry['compressed']:raise ValueError('compressed member truncated')
    data=zlib.decompress(comp,-15) if entry['method']==8 else comp if entry['method']==0 else None
    if data is None or len(data)!=entry['bytes'] or zlib.crc32(data)!=entry['crc32']:raise ValueError('ZIP member size/CRC mismatch')
    return data
def inspect_wave(data):
    with wave.open(io.BytesIO(data)) as w:
        meta=dict(channels=w.getnchannels(),sample_width=w.getsampwidth(),sample_rate=w.getframerate(),frames=w.getnframes(),compression=w.getcomptype())
        pcm=w.readframes(w.getnframes())
    if meta['channels']!=1 or meta['sample_width']!=2 or meta['sample_rate']!=16000 or meta['compression']!='NONE':raise ValueError('technical header requires PCM16 mono16k')
    if not 8<=meta['frames']/16000<=15:raise ValueError('actual frame duration outside fixed reference-generator8to15 contract')
    if len(pcm)!=meta['frames']*2:raise ValueError('truncated WAV PCM body')
    return dict(meta,PCM_sha256=hashlib.sha256(pcm).hexdigest(),duration=meta['frames']/16000)
def request_member(url,entry):
    start=entry['local_offset'];length=entry['compressed']+4096;end=start+length-1
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
    with urllib.request.urlopen(req,timeout=45) as r:
        if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {start}-'):raise ValueError('public server did not honor bounded exact Range')
        data=r.read(length+1)
    if len(data)!=length:raise ValueError('bounded Range length mismatch')
    return data
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);a=ap.parse_args();cfg=read(a.config)
    src=pathlib.Path(__file__).resolve().parent;commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
    assert commit==cfg['source_commit'] and not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
    for x in cfg['source_files']:assert sha(src/x['path'])==x['sha256']
    selection=read(cfg['selection']);assert sha(cfg['selection'])==cfg['selection_sha256'] and selection['metadata_only_before_neural'] and not selection['reference_read'] and not selection['WAV_bytes_read']
    B=pathlib.Path(cfg['designated_disk']);out=pathlib.Path(cfg['out']);data_root=pathlib.Path(cfg['dataset_root'])
    assert out.resolve().is_relative_to(B) and data_root.resolve().is_relative_to(B)
    out.mkdir(exist_ok=False);(out/'ranges').mkdir();(data_root/'audio').mkdir(parents=True,exist_ok=True)
    save=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
    save(out/'CONFIG.json',cfg);save(out/'ENVIRONMENT.json',dict(python=platform.python_version(),platform=platform.platform(),model_calls=0,gpu_calls=0))
    save(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,config_sha256=sha(a.config),selection_sha256=cfg['selection_sha256'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw=str(out),summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json')))
    sources=[];attempts=[]
    try:
        # Selection is already irrevocably frozen. Reference content is read
        # only now and is never used to choose or replace a source.
        assert sha(cfg['reference_metadata'])==cfg['reference_metadata_sha256']
        references=read(cfg['reference_metadata']);ref={}
        for row in references:
            sid=pathlib.PurePosixPath(row.get('audio_path','')).stem;text=row.get('text_zh','')
            if sid and text:
                if sid in ref and ref[sid]!=text:raise ValueError('conflicting original transcript reference')
                ref[sid]=text
        for group in selection['selected']:
            for candidate_index,entry in enumerate(group['technical_fallback_order']):
                raw=None;stage=cfg.get('staged_ranges',{}).get(entry['source_id'])
                if stage:
                    assert pathlib.Path(stage['path']).resolve().is_relative_to(B)
                    assert stage['public_source']==selection['archive_public_url']
                    assert stage['content_range'].startswith('bytes %d-%d/'%(entry['local_offset'],entry['local_offset']+entry['compressed']+4095))
                    raw=verify_staged(stage)
                else:
                    for network_attempt in range(3):
                        try:raw=request_member(selection['archive_public_url'],entry);break
                        except (urllib.error.URLError,TimeoutError,OSError) as exc:
                            # Never log redirect/signed URL or exception repr.
                            attempts.append(dict(source_id=entry['source_id'],network_attempt=network_attempt,error_type=type(exc).__name__,http_status=getattr(exc,'code',None),selected_member_unchanged=True))
                            if network_attempt==2:raise RuntimeError('same selected member public Range unavailable after3 network attempts') from None
                rp=out/'ranges'/f"{entry['source_id']}.range";rp.write_bytes(raw)
                data=extract_member(raw,entry) # CRC/transport corruption fails; never select a different source.
                try:header=inspect_wave(data)
                except (ValueError,wave.Error,EOFError) as exc:
                    attempts.append(dict(source_id=entry['source_id'],technical_header_rejected=True,reason=str(exc),next_predeclared_candidate_only=True));save(out/'ATTEMPTS.json',attempts);continue
                sid=entry['source_id'];assert sid in ref,'missing reference must stop, not select another source'
                dest=data_root/'audio'/f'{sid}.wav';preexisting=dest.exists()
                if preexisting:
                    if dest.read_bytes()!=data:raise ValueError('preserved original WAV differs from frozen same-member CRC-verified bytes')
                else:
                    with dest.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
                    dest.chmod(0o444)
                source=dict(source_id=sid,speaker_id=entry['speaker_id'],path=str(dest),audio_sha256=sha(dest),frames=header['frames'],duration=header['duration'],reference=ref[sid],
                    header=header,archive_member=entry,technical_fallback_index=candidate_index,range_file=str(rp),range_sha256=sha(rp),preexisting_verified_WAV=preexisting,transport=stage.get('transport') if stage else 'remote_official_public_Range')
                sources.append(source);save(out/'PROGRESS.json',dict(completed_sources=len(sources),sources=sources,attempts=attempts));print(json.dumps(dict(source_id=sid,bytes=len(data),audio_sha256=source['audio_sha256'],actual_duration=header['duration'])),flush=True);break
            else:raise RuntimeError('all predeclared same-speaker candidates failed technical header checks')
        assert len(sources)==4 and len({s['speaker_id'] for s in sources})==4 and not set(s['speaker_id'] for s in sources)&set(selection['excluded_speakers'])
        receipt=dict(status='PASS_FOUR_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE',method_source_commit=selection['method_source_commit'],selection_source_commit=selection['selection_source_commit'],acquisition_source_commit=commit,selection_sha256=cfg['selection_sha256'],selection_created_utc=selection['selection_created_utc'],
            metadata_only_before_neural=True,excluded_speakers=selection['excluded_speakers'],seed=selection['seed'],estimated_band=selection['selected_estimated_duration_band'],sources=sources,all_selected_valid_sources_retained=True,no_resampling=True,model_calls=0,gpu_calls=0,attempts=attempts,
            reference_metadata_path=cfg['reference_metadata'],reference_metadata_sha256=sha(cfg['reference_metadata']),frozen_method_sha256=selection['method_freeze_sha256'])
        save(out/'SOURCE_RECEIPT.json',receipt);save(data_root/'SOURCE_RECEIPT_v1.json',receipt)
        save(out/'SUMMARY.json',dict(status=receipt['status'],sources=len(sources),WAV_bytes=sum(pathlib.Path(s['path']).stat().st_size for s in sources),receipt_sha256=sha(out/'SOURCE_RECEIPT.json'),model_calls=0))
        save(out/'GATE.json',dict(status=receipt['status'],source_receipt_sha256=sha(out/'SOURCE_RECEIPT.json'),all_CRC_headers_SHA_passed=True,model_calls=0,gpu_calls=0))
        print(json.dumps(dict(status=receipt['status'],receipt_sha256=sha(out/'SOURCE_RECEIPT.json'))),flush=True)
    except BaseException as exc:
        save(out/'FAILURE.json',dict(error_type=type(exc).__name__,error=str(exc) if not isinstance(exc,urllib.error.URLError) else 'public Range transport failure; URLs omitted',completed_sources=len(sources),attempts=attempts))
        save(out/'GATE.json',dict(status='FAIL_DATA_AVAILABILITY_OR_TECHNICAL_GATE',completed_sources=len(sources),model_calls=0,gpu_calls=0));raise
if __name__=='__main__':main()
