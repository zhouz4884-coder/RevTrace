"""Official test-only acquisition and RIFF-header census; never decodes audio."""
from __future__ import annotations
from collections import Counter
import datetime,gzip,hashlib,json,os,pathlib,re,resource,struct,tarfile,time,urllib.request

class CensusError(AssertionError):pass
def need(ok,why):
    if not ok:raise CensusError(why)
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def put(path,obj):pathlib.Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def snapshot():
    def fields(path,wanted=None):
        out={}
        try:
            for line in pathlib.Path(path).read_text().splitlines():
                x=line.replace(':',' ').split()
                if len(x)>=2 and (wanted is None or x[0] in wanted):
                    try:out[x[0]]=int(x[1])
                    except ValueError:pass
        except OSError:pass
        return out
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),perf=time.perf_counter(),
        process_cpu=time.process_time(),pid=os.getpid(),process_io=fields('/proc/self/io'),
        meminfo_kB=fields('/proc/meminfo',{'Cached','MemAvailable','SwapCached','Dirty','Writeback'}),
        vmstat=fields('/proc/vmstat',{'pgfault','pgmajfault','pgpgin','pgpgout'}),
        process_faults=dict(minor=usage.ru_minflt,major=usage.ru_majflt))

def safe_name(name):
    need(name and '\\' not in name and '\x00' not in name,'unsafe_tar_path')
    p=pathlib.PurePosixPath(name)
    need(not p.is_absolute() and '..' not in p.parts and not re.match(r'^[A-Za-z]:',name),'unsafe_tar_path')
    need(not any(x.lower() in ('train','dev') for x in p.parts),'non_test_split_member')
    return p

def load_catalog(config):
    p=pathlib.Path(config['metadata_archive']);need(sha(p)==config['metadata_archive_sha256'],'metadata_archive_changed')
    with tarfile.open(p,'r:gz') as t:
        raw=t.extractfile('test.scp').read();spkraw=t.extractfile('SPKINFO.txt').read()
    need(hashlib.sha256(raw).hexdigest()==config['test_scp_sha256'],'test_scp_changed')
    need(hashlib.sha256(spkraw).hexdigest()==config['speaker_info_sha256'],'speaker_info_changed')
    speakers={line.split()[0] for line in spkraw.decode('utf-8-sig').splitlines()[1:] if line.strip()}
    catalog={}
    for line in raw.decode('ascii').splitlines():
        fields=line.split();need(len(fields)==2,'test_scp_not_path_only_schema')
        base,relative=fields;p=safe_name(relative)
        need(relative.startswith('wav/test/') and p.name==base and base.endswith('.wav'),'test_scp_path_mismatch')
        sid=p.parent.name;need(sid in speakers and base not in catalog,'speaker_join_or_duplicate_catalog')
        catalog[base]=dict(speaker_id=sid,metadata_path=relative)
    need(len(catalog)==config['expected_WAV_members'],'test_member_count_changed')
    need(len({r['speaker_id'] for r in catalog.values()})==config['expected_test_speakers'],'test_speaker_count_changed')
    return catalog

class MemberReader:
    def __init__(self,stream,size):self.stream=stream;self.size=size;self.pos=0;self.h=hashlib.sha256()
    def read(self,n):
        need(0<=n<=self.size-self.pos,'RIFF_chunk_exceeds_member')
        b=self.stream.read(n);need(len(b)==n,'truncated_WAV_member')
        self.pos+=n;self.h.update(b);return b
    def skip(self,n):
        while n:
            k=min(n,65536);self.read(k);n-=k
    def drain(self):self.skip(self.size-self.pos)

def wav_header(reader):
    begin=reader.read(12);need(begin[:4]==b'RIFF' and begin[8:]==b'WAVE','unsupported_RIFF_container')
    riff_end=8+struct.unpack('<I',begin[4:8])[0]
    need(12<=riff_end==reader.size,'RIFF_size_does_not_match_member')
    fmt=None;data_bytes=[];chunks=[]
    while reader.pos<riff_end:
        need(riff_end-reader.pos>=8,'truncated_RIFF_chunk_header')
        header=reader.read(8);kind=header[:4];n=struct.unpack('<I',header[4:])[0]
        need(n+(n&1)<=riff_end-reader.pos,'RIFF_chunk_exceeds_container')
        chunks.append(dict(id=kind.decode('ascii',errors='replace'),bytes=n))
        if kind==b'fmt ':
            need(fmt is None and 16<=n<=1024*1024,'invalid_or_duplicate_fmt_chunk')
            body=reader.read(n);tag,channels,sr,rate,align,bits=struct.unpack('<HHIIHH',body[:16]);subtype=None;valid_bits=None
            if tag==65534:
                need(n>=40 and struct.unpack('<H',body[16:18])[0]>=22,'truncated_extensible_fmt')
                valid_bits=struct.unpack('<H',body[18:20])[0];subtype=body[24:40].hex()
            fmt=dict(format_tag=tag,channels=channels,sample_rate=sr,byte_rate=rate,block_align=align,bits_per_sample=bits,
                     extensible_valid_bits=valid_bits,extensible_subtype=subtype)
        elif kind==b'data':data_bytes.append(n);reader.skip(n)
        else:reader.skip(n)
        if n&1:reader.read(1)
    need(fmt is not None and len(data_bytes)==1,'missing_fmt_or_ambiguous_data_chunks')
    need(fmt['sample_rate']>0 and fmt['channels']>0 and fmt['block_align']>0,'invalid_wave_dimensions')
    need(data_bytes[0]%fmt['block_align']==0,'partial_PCM_frame')
    pcm=fmt['format_tag']==1 or (fmt['format_tag']==65534 and fmt['extensible_subtype']=='0100000000001000800000aa00389b71' and fmt['extensible_valid_bits']==16)
    linear=fmt['format_tag'] in (1,3) or (fmt['format_tag']==65534 and fmt['extensible_subtype'] in ('0100000000001000800000aa00389b71','0300000000001000800000aa00389b71'))
    if linear:
        need(fmt['block_align']==fmt['channels']*((fmt['bits_per_sample']+7)//8) and fmt['byte_rate']==fmt['sample_rate']*fmt['block_align'],'invalid_linear_PCM_rate_or_alignment')
    frames=data_bytes[0]//fmt['block_align'] if linear else None;seconds=frames/fmt['sample_rate'] if linear else None
    eligible_format=pcm and fmt['channels']==1 and fmt['sample_rate']==16000 and fmt['bits_per_sample']==16 and fmt['block_align']==2 and fmt['byte_rate']==32000
    return dict(**fmt,frames=frames,duration_seconds=seconds,data_bytes=data_bytes[0],RIFF_chunks=chunks,
        compatible_original_input_format=eligible_format,stratum='6to12' if eligible_format and 6<=seconds<12 else '12to20' if eligible_format and 12<=seconds<=20 else None)

def validate_response(response,offset,config):
    expected=config['archive_bytes'];status=response.status;headers=response.headers
    need(response.url in config['allowed_archive_urls'],'unexpected_archive_redirect')
    if offset:
        need(status==206,'resume_requires_HTTP206')
        need(headers.get('Content-Range')==f'bytes {offset}-{expected-1}/{expected}','resume_content_range_changed')
    else:need(status==200,'initial_download_requires_HTTP200')
    need(int(headers.get('Content-Length','-1'))==expected-offset,'HTTP_content_length_changed')
    need(headers.get('ETag')==config['expected_ETag'],'HTTP_ETag_changed')

def download(config,out,events):
    archive=out/'test_set.tar.gz';part=out/'test_set.tar.gz.part';need(not archive.exists(),'never_overwrite_archive')
    need(not part.exists(),'new_run_requires_new_partial_path')
    part.touch(exist_ok=False);attempts=[];started=time.perf_counter()
    for attempt in range(config['maximum_download_attempts']):
        offset=part.stat().st_size
        if offset==config['archive_bytes']:break
        request=urllib.request.Request(config['archive_url'],headers={'User-Agent':'RevTrace-header-census/1.0',**({'Range':f'bytes={offset}-'} if offset else {})})
        try:
            with urllib.request.urlopen(request,timeout=config['network_socket_timeout_seconds']) as response:
                validate_response(response,offset,config)
                with part.open('ab') as f:
                    last=0.
                    while True:
                        need(time.perf_counter()-started<=config['maximum_download_wall_seconds'],'download_wall_budget_exceeded')
                        b=response.read(4*1024*1024)
                        if not b:break
                        need(f.tell()+len(b)<=config['archive_bytes'],'transport_larger_than_frozen_archive')
                        f.write(b)
                        now=time.perf_counter()
                        if now-last>=5:
                            f.flush();put(out/'DOWNLOAD_PROGRESS.json',dict(bytes=f.tell(),expected=config['archive_bytes'],attempt=attempt,snapshot=snapshot()));last=now
                    f.flush();os.fsync(f.fileno())
            attempts.append(dict(attempt=attempt,status='HTTP_stream_completed',bytes=part.stat().st_size))
        except (OSError,TimeoutError) as exc:
            attempts.append(dict(attempt=attempt,status='transport_error_preserved_partial',bytes=part.stat().st_size,error=type(exc).__name__+':'+str(exc)))
        if part.stat().st_size==config['archive_bytes']:break
    put(out/'DOWNLOAD_ATTEMPTS.json',attempts)
    need(part.stat().st_size==config['archive_bytes'],'incomplete_archive_transport')
    need(time.perf_counter()-started<=config['maximum_download_wall_seconds'],'download_wall_budget_exceeded')
    part.rename(archive)
    hashes={name:hashlib.new(name) for name in ('sha256','md5')}
    with archive.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):
            for h in hashes.values():h.update(b)
    identity=dict(path=str(archive),bytes=archive.stat().st_size,sha256=hashes['sha256'].hexdigest(),md5=hashes['md5'].hexdigest(),
        official_expected_sha256=config['official_expected_sha256'],official_expected_md5=config['official_expected_md5'],
        independent_published_checksum_available=bool(config['official_expected_sha256'] or config['official_expected_md5']),wall_seconds=time.perf_counter()-started)
    for name in ('sha256','md5'):
        expected=config['official_expected_'+name]
        if expected:need(identity[name]==expected,'official_archive_checksum_mismatch')
    put(out/'ARCHIVE_IDENTITY.json',identity);events('archive_transport_and_hash_complete',identity=identity)
    return archive,identity

def scan_archive(archive,catalog,out,config,events):
    seen=set();member_names=set();technical=Counter();by_speaker={sid:Counter() for sid in sorted({r['speaker_id'] for r in catalog.values()})}
    wav_count=total_members=expanded=ignored=0;rows_path=out/'WAV_HEADERS.jsonl'
    with rows_path.open('x',encoding='utf8') as rows,gzip.open(archive,'rb') as gz:
        with tarfile.open(fileobj=gz,mode='r|') as tar:
            for member in tar:
                total_members+=1;need(total_members<=config['maximum_tar_members'],'too_many_tar_members')
                p=safe_name(member.name);need(member.name not in member_names,'duplicate_tar_member');member_names.add(member.name)
                need(member.isdir() or member.isfile(),'links_or_special_tar_members_forbidden')
                need(not member.issparse(),'sparse_tar_members_forbidden')
                expanded+=member.size;need(expanded<=config['maximum_expanded_member_bytes'],'expanded_archive_bound_exceeded')
                if member.isdir():continue
                if p.suffix.lower()!='.wav':ignored+=1;continue # TRANS body is never opened or parsed.
                need(p.name in catalog and p.name not in seen,'unexpected_or_duplicate_test_WAV')
                expected=catalog[p.name];need(p.parent.name==expected['speaker_id'] and 'test' in p.parts,'test_speaker_directory_mismatch')
                seen.add(p.name);wav_count+=1
                by_speaker[expected['speaker_id']]['WAV_members']+=1
                need(member.size<=config['maximum_single_WAV_bytes'],'WAV_member_bound_exceeded')
                reader=MemberReader(tar.extractfile(member),member.size)
                row=dict(utterance_id=p.stem,speaker_id=expected['speaker_id'],tar_path=member.name,metadata_path=expected['metadata_path'],WAV_bytes=member.size)
                try:row.update(header_status='valid_RIFF',**wav_header(reader))
                except CensusError as exc:row.update(header_status='technical_reject',reason=str(exc),stratum=None)
                reader.drain();row['WAV_sha256']=reader.h.hexdigest();technical[row['header_status']]+=1
                if row['header_status']=='valid_RIFF':
                    technical['compatible_format' if row['compatible_original_input_format'] else 'incompatible_format']+=1
                    by_speaker[row['speaker_id']]['compatible_format' if row['compatible_original_input_format'] else 'incompatible_format']+=1
                    if row['stratum']:by_speaker[row['speaker_id']][row['stratum']]+=1
                    elif row['compatible_original_input_format']:by_speaker[row['speaker_id']]['outside_duration_strata']+=1
                else:by_speaker[row['speaker_id']]['technical_reject']+=1
                rows.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                if wav_count%500==0:rows.flush();put(out/'SCAN_PROGRESS.json',dict(WAV_members=wav_count,tar_members=total_members,snapshot=snapshot()))
            need(not any(getattr(tar.fileobj,'buf',b'')),'nonzero_trailing_tar_bytes')
        # Force gzip EOF: validates the full member CRC/ISIZE and transport tail.
        for tail in iter(lambda:gz.read(1024*1024),b''):need(not any(tail),'nonzero_trailing_tar_bytes')
    need(seen==set(catalog),'missing_expected_test_WAV_members')
    summary=dict(status='PASS_OFFICIAL_TEST_TRANSPORT_GZIP_AND_RIFF_HEADER_CENSUS_NOT_SELECTED',WAV_members=wav_count,
        metadata_speakers=len(by_speaker),all_expected_WAVs_present=True,all_test_speaker_joins_valid=True,
        tar_members=total_members,ignored_non_WAV_regular_members=ignored,ignored_TRANS_body=True,expanded_member_bytes=expanded,
        technical_counts=dict(technical),candidate_counts_by_speaker={sid:{k:c[k] for k in ('WAV_members','compatible_format','incompatible_format','technical_reject','outside_duration_strata','6to12','12to20')} for sid,c in by_speaker.items()},
        potential_speakers_by_stratum={k:sum(c[k]>0 for c in by_speaker.values()) for k in ('6to12','12to20')},
        potential_speakers_either_stratum=sum(bool(c['6to12'] or c['12to20']) for c in by_speaker.values()),
        history_census_status='REQUIRED_NOT_COMPLETED_NO_UNUSED_CLAIM',selection_status='NO_SPEAKERS_OR_UTTERANCES_SELECTED',
        audio_decoded=False,TRANS_body_opened=False,model_calls=0,GPU_calls=0,
        file_identity_note='WAV byte hashes computed while skipping member payload; samples never decoded or analyzed',
        scope='technical metadata readiness only; not task performance, source-history independence or a16speaker selection')
    put(out/'CANDIDATE_COUNTS.json',summary['candidate_counts_by_speaker']);events('full_gzip_EOF_and_header_census_complete',WAV_members=wav_count)
    return summary
