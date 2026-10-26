"""Negative tests of the independent checker, on retained pilot trace, zero GPU."""
from pathlib import Path
from unittest.mock import patch
import copy,json
import pytest
import audit_role_probe_v2 as A
W=Path(__file__).resolve().parent
D=W/'role_pilot_collected_v2/pilot/strict-coherent-proposer-3729-6852-0003-r0'
H='b08fa4262d1c3ab7e07137eea340d0bb92be200c'

def changed_read(filename,mutator):
 original=A.read
 def reader(p):
  x=original(p)
  if Path(p).name==filename:x=copy.deepcopy(x);mutator(x)
  return x
 return reader

def changed_lines(filename,mutator):
 original=A.lines
 def reader(p):
  x=original(p)
  if Path(p).name==filename:x=copy.deepcopy(x);mutator(x)
  return x
 return reader

def test_original_trace_passes():assert A.audit(D,H)['actual_private_chain_consumer_violations']==0

@pytest.mark.parametrize('filename,mutator',[
 ('provenance.json',lambda x:x.__setitem__('harness_commit','foreign')),
 ('config.json',lambda x:x.__setitem__('rho',3)),
 ('PHYSICAL_CALLS.json',lambda x:x['calls'][0]['job']['prompt_tokens'].append(999)),
 ('PHYSICAL_CALLS.json',lambda x:x['calls'][0]['result']['token_ids'].append(999)),
 ('PHYSICAL_CALLS.json',lambda x:x['calls'][0]['job'].__setitem__('audio_ready_perf',float('inf'))),
])
def test_bad_read_fails(filename,mutator):
 with patch.object(A,'read',changed_read(filename,mutator)):
  with pytest.raises(AssertionError):A.audit(D,H)

def test_wrong_consumer_root_fails():
 def bad(rows):
  row=next(r for r in rows if 'canonical_version' in r);row['canonical_version']+=100
 with patch.object(A,'lines',changed_lines('consumer.jsonl',bad)):
  with pytest.raises(AssertionError):A.audit(D,H)

def test_repeated_commit_fails():
 def bad(rows):
  at=next(i for i,r in enumerate(rows) if r.get('kind')=='commit');rows.insert(at+1,copy.deepcopy(rows[at]))
 with patch.object(A,'lines',changed_lines('events.jsonl',bad)):
  with pytest.raises(AssertionError):A.audit(D,H)

def test_native_receipt_digest_fails():
 def bad(rows):
  row=next(r for r in rows if r['kind']=='row-complete');row['message']['payload_digest']='0'*64
 worker=next(p.name for p in D.glob('worker-*-receipts.jsonl'))
 with patch.object(A,'lines',changed_lines(worker,bad)):
  with pytest.raises(AssertionError):A.audit(D,H)
