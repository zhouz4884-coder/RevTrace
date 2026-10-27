"""Meaningful parser/render rejection checks; no model, network or GPU."""
import hashlib,json,struct
import pytest
from audit_recovery import frames,render
from prepare_holdout import plans


def frame(row):
    b=json.dumps(row).encode();return struct.pack('>I',len(b))+b+hashlib.sha256(b).digest()


def test_checksum_and_chain_reject_tampered_committed_evidence(tmp_path):
    p=tmp_path/'wal';a={'sequence':0,'previous_sha256':'','kind':'init'}
    p.write_bytes(frame(a));assert frames(p)==[a]
    bad=bytearray(p.read_bytes());bad[-1]^=1;p.write_bytes(bad)
    with pytest.raises(AssertionError):frames(p)


def test_sequence_gap_is_not_silently_recovered(tmp_path):
    p=tmp_path/'wal';p.write_bytes(frame({'sequence':1,'previous_sha256':''}))
    with pytest.raises(AssertionError):frames(p)


class Tok:
    def decode(self,z,**kw):return ''.join(chr(x) for x in z if x!=0)
    def encode(self,s):return [ord(x) for x in s]


def parser(s,**kw):return 'English',s


def test_render_uses_actual_job_parent_instead_of_cached_text():
    j=dict(prompt_tokens=list(map(ord,'abcdefg')),chunk_id=2,language='English')
    P,text=render(Tok(),parser,j,[ord('Z'),0],{0})
    assert text=='abZ' and P==list(map(ord,'abZ'))


def test_early_eos_and_short_unterminated_sequences_fail_closed():
    j=dict(prompt_tokens=[],chunk_id=0,language='English')
    with pytest.raises(AssertionError):render(Tok(),parser,j,[0,65],{0})
    with pytest.raises(AssertionError):render(Tok(),parser,j,[65],{0})


def test_holdout_is_speaker_disjoint_and_keeps_chronological_nonreused_units():
    rows=[dict(id=f'{s}-10-{i:04}',speaker_id=str(s),chapter_id='10',duration=30.) for s in (1,2,3) for i in range(6)]
    config=dict(separator_seconds=.1,target_seconds=90.,minimum_seconds=60.,sessions_per_speaker=2,speakers=2)
    chosen,excluded=plans(list(reversed(rows)),set(),{'1'},config)
    assert [g['speaker'] for g in chosen]==['2','3'] and len(excluded)==6
    ids=[r['id'] for g in chosen for session in g['sessions'] for r in session]
    assert len(ids)==len(set(ids)) and ids[:2]==['2-10-0000','2-10-0001']
