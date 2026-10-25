"""CPU fixture for actual-vs-declared field binding; no neural execution."""
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from row_delivery_worker import RowDeliveryTap
from revtrace.row_lifecycle import RowBinding

class Tok:
    def decode(self,*a,**k):return 'word'
    def encode(self,x):return [17]
class Sink:
    def __init__(self):self.items=[]
    def put(self,x):self.items.append(x)

def test_native_receipt_does_not_echo_false_declared_audio_hash():
    sink=Sink();cfg={'runtime_digest':'rt','max_new_tokens':256}
    tap=RowDeliveryTap(sink,SimpleNamespace(tokenizer=Tok()),lambda text,**kw:('English',text),cfg,[3])
    b=RowBinding('w','inc','batch','a',0,'authority',0,1,'chi','rt',0,32000,'interval','input')
    j={'job_id':'a','language':'English','prompt_tokens':[],'chunk_id':0,'prefix_audio_sha256':'wrong-declared',
       '_delivery':{'worker':'w','incarnation':'inc','batch_id':'batch','binding':asdict(b)}}
    tap.prepare([j],prefixes=[''],contexts=[{'actual_audio_sha256':'actual-waveform'}],audits=[{'CPU_fixture_only':True}],started=0.)
    tap.set_phase('CPU-fixture',.1,[0]);tap.emit(0,[3],terminal=time.perf_counter())
    body=sink.items[0]['message'].decode()
    assert body['prefix_audio_sha256']=='actual-waveform'
    assert body['prefix_audio_sha256']!=j['prefix_audio_sha256'] # Existing owner check must reject.
