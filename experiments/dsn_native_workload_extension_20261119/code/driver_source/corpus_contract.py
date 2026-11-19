"""Strict metadata-first MAGICDATA68 original-test input contract; stdlib only.

The receipt is an auditable claim: bytes, membership, labels, and metadata-only
selection are independently rechecked before a reference or service campaign.
No exception for derived audio and no neural imports are accepted here.
"""
from __future__ import annotations
import hashlib, io, json, pathlib, re, tarfile, wave
from confirmation_common import B, GateError, need, read, sha, canonical

CORPUS = 'MAGICDATA68'
STATUS = 'PASS_STRICT_METADATA_SELECTED_ORIGINAL_MAGICDATA_TEST_AUDIO_AVAILABLE'
NO_GO = 'NO_GO_NO_ELIGIBLE_ORIGINAL_MAGICDATA_TEST_AUDIO'
RULE = dict(minimum_frames=192000, maximum_frames=320000, target_frames=256000,
            requested_speakers=4, speaker_order='lexicographic',
            within_speaker_order=['abs(frames-target_frames)', 'utterance_id'])
OFFICIAL_ARCHIVE_URLS = frozenset((
    'https://openslr.magicdatatech.com/resources/68/test_set.tar.gz',
    'https://www.openslr.org/resources/68/test_set.tar.gz',
    'https://openslr.org/resources/68/test_set.tar.gz'))

def _digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def _disk(path):
    p = pathlib.Path(path)
    need(p.is_absolute() and p.resolve().is_relative_to(B.resolve()), 'corpus asset outside designated8TB')
    need(p.is_file() and not p.is_symlink(), 'corpus asset missing or symlink')
    return p

def _bound_file(info):
    p = _disk(info['path'])
    need(_digest(info['sha256']) and sha(p)==info['sha256'], 'corpus receipt dependency changed')
    if 'bytes' in info: need(p.stat().st_size==info['bytes'], 'corpus dependency size changed')
    return p

def _no_labels(value):
    if isinstance(value,dict):
        for k,v in value.items():
            need(not any(term in k.lower() for term in ('transcript','reference','text')), 'labels present before ID freeze')
            _no_labels(v)
    elif isinstance(value,list):
        for v in value: _no_labels(v)

def metadata_choice(rows):
    """Select on original PCM headers and IDs alone, preserving actual shortfall."""
    need(isinstance(rows,list), 'full header census must be an array')
    seen = set(); eligible = {}
    for row in rows:
        _no_labels(row)
        uid = row['utterance_id']; speaker = row['speaker_id']
        need(isinstance(uid,str) and isinstance(speaker,str) and
             re.fullmatch('[A-Za-z0-9_-]+',uid) is not None and
             re.fullmatch('[A-Za-z0-9_-]+',speaker) is not None, 'missing or unsafe raw corpus ID')
        need(uid not in seen, 'duplicate original utterance in full census'); seen.add(uid)
        f = row.get('frames')
        good = (row.get('header_status')=='valid_RIFF' and row.get('compatible_original_input_format') is True and
                type(f) is int and RULE['minimum_frames']<=f<=RULE['maximum_frames'] and
                row.get('sample_rate')==16000 and row.get('channels')==1 and row.get('bits_per_sample')==16)
        if good:
            need(abs(row['duration_seconds']-f/16000)<1e-10, 'census duration/header mismatch')
            eligible.setdefault(speaker,[]).append(row)
    chosen = []
    for speaker in sorted(eligible)[:RULE['requested_speakers']]:
        chosen.append(min(eligible[speaker], key=lambda r:(abs(r['frames']-RULE['target_frames']),r['utterance_id'])))
    return chosen,len(eligible)

def _member(info):
    path = info['path']; p = pathlib.PurePosixPath(path)
    need(isinstance(path,str) and not p.is_absolute() and '..' not in p.parts and '\\' not in path,
         'unsafe archive member')
    need(type(info['bytes']) is int and info['bytes']>0 and _digest(info['sha256']), 'incomplete archive-member identity')
    return path

def metadata_inputs(receipt):
    need(receipt.get('corpus')==CORPUS and receipt.get('split')=='test', 'not original MAGICDATA68 official test split')
    need(receipt.get('status') in (STATUS,NO_GO), 'MD68 selection is not terminal')
    need(receipt.get('metadata_first') is True and type(receipt.get('model_calls')) is int and receipt['model_calls']==0,
         'metadata selection must precede all model calls')
    need(all(receipt.get(k) is True for k in ('no_concat','no_trim','no_resample')), 'modified corpus audio forbidden')
    need(receipt.get('selection_rule')==RULE and receipt.get('requested_source_count')==4, 'metadata-only choice rule changed')
    archive = receipt['archive']
    need(archive.get('official_url') in OFFICIAL_ARCHIVE_URLS, 'non-official corpus archive origin')
    need(type(archive.get('bytes')) is int and archive['bytes']>0, 'full compressed archive size required')
    archive_path = _bound_file(archive)
    census_path = _bound_file(receipt['metadata_census'])
    rows = [json.loads(line) for line in census_path.read_text(encoding='utf8').splitlines() if line.strip()]
    choice, eligible_count = metadata_choice(rows)
    need(receipt['eligible_speaker_count']==eligible_count, 'eligible-speaker census count differs')
    ids_path = _bound_file(receipt['ids_frozen']); ids = read(ids_path); _no_labels(ids)
    need(ids.get('corpus')==CORPUS and ids.get('split')=='test' and ids.get('metadata_first') is True and
         ids.get('access_phase')=='ID_SELECTION_COMPLETE_BEFORE_LABEL_ACCESS', 'ID freeze was not before label access')
    need(type(ids.get('model_calls')) is int and ids['model_calls']==0, 'ID freeze lacks explicit zero model-call accounting')
    need(ids.get('selection_rule')==RULE and ids.get('full_census_sha256')==receipt['metadata_census']['sha256'] and
         ids.get('archive_sha256')==archive['sha256'], 'ID freeze/census/archive bindings differ')
    return archive,archive_path,choice,ids

def validate_empty_selection(receipt):
    archive,path,choice,ids=metadata_inputs(receipt)
    need(receipt['status']==NO_GO and not choice and receipt['sources']==[] and
         ids['selected_source_ids']==[] and ids['selected']==[], 'NO-GO must be a fully bound empty metadata selection')
    return True

def selected_md68_sources(receipt, expected=None):
    archive,archive_path,choice,ids=metadata_inputs(receipt)
    need(receipt['status']==STATUS, 'zero eligible is NO-GO, never a launchable selection')
    sources = receipt['sources']
    n = len(choice)
    need(0<n<=4 and len(sources)==n and (expected is None or expected==n), 'actual eligible selection count differs')
    need(len({s['speaker_id'] for s in sources})==len({s['source_id'] for s in sources})==n, 'repeated speaker/source')
    expected_ids = ['MD68_'+r['utterance_id'] for r in choice]
    need([s['source_id'] for s in sources]==ids.get('selected_source_ids')==expected_ids,
         'selection is not exact metadata-first speaker/nearest16s choice')
    frozen = ids['selected']
    need(len(frozen)==n, 'frozen-ID selection scope differs')
    labels_path = _bound_file(receipt['transcript_binding']); labels = read(labels_path)
    need(labels.get('ids_frozen_sha256')==receipt['ids_frozen']['sha256'] and
         type(labels.get('model_calls')) is int and labels['model_calls']==0,
         'selected labels are not downstream of the immutable ID freeze')
    need(set(labels['selected'])=={r['utterance_id'] for r in choice}, 'label bank includes unselected or missing IDs')
    members = {}; wav_paths = {}
    for source,row,fr in zip(sources,choice,frozen):
        uid = row['utterance_id']; spk = row['speaker_id']
        need(source['raw_source_id']==uid and source['raw_speaker_id']==spk and
             source['speaker_id']=='MD68_'+spk, 'raw/namespaced corpus identity differs')
        need(fr['raw_source_id']==uid and fr['raw_speaker_id']==spk and fr['source_id']==source['source_id'] and
             fr['speaker_id']==source['speaker_id'], 'source differs from pre-label frozen ID')
        parts=pathlib.PurePosixPath(row['tar_path']).parts
        need('test' in parts, 'source is not in original test directory')
        splitdir=pathlib.PurePosixPath(*parts[:parts.index('test')+1]).as_posix()
        need(source['original_split']=='MD68/test@'+archive['sha256'] and source['split_directory']==splitdir,
             'source split is not bound to original test archive bytes')
        member = source['archive_member']; member_path = _member(member)
        need(member_path==row['tar_path'] and pathlib.PurePosixPath(member_path).stem==uid and
             spk in pathlib.PurePosixPath(member_path).parts[:-1], 'WAV original speaker/member path differs')
        need(member['bytes']==row['WAV_bytes'] and member['sha256']==row['WAV_sha256']==source['audio_sha256'],
             'census/fullWAV/member digest differs')
        need(source['frames']==row['frames'] and abs(source['duration']-source['frames']/16000)<1e-10,
             'full original duration changed')
        p = _disk(source['path'])
        need(p.stat().st_size==member['bytes'] and sha(p)==source['audio_sha256'], 'extracted full original WAV bytes differ')
        with wave.open(str(p),'rb') as wav:
            header=source['header']
            need(wav.getcomptype()=='NONE' and wav.getframerate()==header['sample_rate']==16000 and
                 wav.getnchannels()==header['channels']==1 and wav.getsampwidth()==header['sample_width']==2 and
                 wav.getnframes()==header['frames']==source['frames'], 'original PCM/header differs')
            need(_digest(header['PCM_sha256']) and hashlib.sha256(wav.readframes(wav.getnframes())).hexdigest()==header['PCM_sha256'],
                 'original complete PCM digest differs')
        entry = labels['selected'][uid]
        need(isinstance(source['reference'],str) and source['reference']==entry['text'] and source['reference'],
             'selected official transcript changed')
        label_member = entry['archive_member']; _member(label_member)
        for info in (member,label_member):
            old = members.setdefault(info['path'],info)
            need(old==info, 'same archive member has conflicting identity')
        wav_paths[member_path] = p
    found = {}; label_bytes = {}
    with tarfile.open(archive_path,'r:*') as tar:
        for item in tar:
            if item.name not in members: continue
            need(item.isfile() and item.name not in found, 'selected archive member missing, duplicate, or not a regular file')
            expected_member = members[item.name]
            need(item.size==expected_member['bytes'], 'original archive member size differs')
            stream=tar.extractfile(item); need(stream is not None, 'original member unreadable')
            data=stream.read()
            need(hashlib.sha256(data).hexdigest()==expected_member['sha256'], 'original archive member digest differs')
            found[item.name]=True
            if item.name not in wav_paths: label_bytes[item.name]=data
    need(set(found)==set(members), 'original archive lacks a selected WAV/TRANS member')
    for row in choice:
        entry=labels['selected'][row['utterance_id']]
        original=label_bytes[entry['archive_member']['path']]
        # IDs were fixed before this label lookup. Only the chosen ID's row is accepted.
        matches=[]
        for line in original.splitlines():
            fields=line.strip().split(None,1)
            if not fields: continue
            try: key=fields[0].decode('ascii')
            except UnicodeDecodeError: continue
            key=key[:-4] if key.endswith('.wav') else key
            if key==row['utterance_id']:
                text=fields[1].decode('utf-8-sig').strip() if len(fields)==2 else ''
                rest=text.split(maxsplit=1)
                has_speaker=bool(rest) and rest[0]==row['speaker_id']
                if has_speaker: text=rest[1].strip() if len(rest)==2 else ''
                matches.append((text,'key_speaker_text' if has_speaker else 'key_text',
                                hashlib.sha256(line).hexdigest()))
        need(matches==[(entry['text'],entry['layout'],entry['raw_row_sha256'])],
             'selected transcript/layout/raw row is not the unique official ID/text row')
    return sources
