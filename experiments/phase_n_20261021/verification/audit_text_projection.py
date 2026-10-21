"""Rebuild persisted/public transcript and Phi from selected Z plus frozen parent."""
import argparse,hashlib,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    from qwen_asr import Qwen3ASRModel,parse_asr_output
    from transformers import AutoProcessor
    processor=AutoProcessor.from_pretrained(a.model,local_files_only=True);tok=processor.tokenizer
    cache={};results=[]
    for cell in sorted(a.root.iterdir()):
        if not (cell/'result.json').exists():continue
        events=[json.loads(l) for l in (cell/'events.jsonl').read_text().splitlines()]
        jobs={e['job_id']:e for e in events if e['kind']=='enqueue'}
        transcript={(e['session_id'],e['version']):e for e in events if e['kind']=='canonical-display'}
        commits=[e for e in events if e['kind']=='commit'];mismatches=[]
        walpath=Path(json.loads((cell/'provenance.json').read_text())['durable_journal_path'])
        rawwal=walpath.read_bytes();position=0;waltext={}
        while position<len(rawwal):
            width=int.from_bytes(rawwal[position:position+4],'big');start=position+4;end=start+width
            payload=rawwal[start:end];assert hashlib.sha256(payload).digest()==rawwal[end:end+32]
            record=json.loads(payload);position=end+32
            if record['kind']=='commit':waltext[record['session_id'],record['parent_checkpoint_id']+1]=record['event']['committed_text']
        parents={(e['session_id'],e['state']['checkpoint_id']):e['state']['prompt_tokens'] for e in json.loads((cell/'initial_states.json').read_text())}
        for e in commits:
            job=jobs[e['job_id']];parent=job.get('declared_prompt_tokens',parents[e['session_id'],e['parent']]);Z=e['segment_tokens']
            key=json.dumps([parent,job['chunk_id'],Z,job['language']],separators=(',',':'))
            if key not in cache:
                raw=tok.decode(parent,skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
                if job['chunk_id']>=2 and raw:
                    ids=tok.encode(raw);k=5
                    while True:
                        prefix=tok.decode(ids[:max(0,len(ids)-k)])
                        if '\ufffd' not in prefix or k>=len(ids):break
                        k+=1
                raw=prefix+tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                _,text=parse_asr_output(raw,user_language=job['language'])
                cache[key]=(tok.encode(raw),text)
            P,text=cache[key];published=transcript[e['session_id'],e['version']]
            if P!=e['next_prompt_tokens'] or text!=published['text'] or text!=waltext[e['session_id'],e['version']]:
                mismatches.append({'session_id':e['session_id'],'version':e['version'],
                    'projection_equal':P==e['next_prompt_tokens'],'text_equal':text==published['text']})
            parents[e['session_id'],e['version']]=e['next_prompt_tokens']
        results.append({'cell':cell.name,'canonical_transitions':len(commits),'mismatches':mismatches,
            'events_sha256':hashlib.sha256((cell/'events.jsonl').read_bytes()).hexdigest()})
    record={'decision':'PASS_INDEPENDENT_Z_PARENT_TO_PHI_AND_ACTUAL_TEXT' if all(not r['mismatches'] for r in results) else 'FAIL_ADAPTER_MAPPING',
        'cells':results,'unique_decoder_contexts':len(cache),
        'scope':'CPU adapter reconstruction of executed GPU selected outputs; not a new GPU trial or neural-execution attestation'}
    a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'decision':record['decision'],'cells':len(results),'transitions':sum(r['canonical_transitions'] for r in results)}))
    assert record['decision'].startswith('PASS_')
if __name__=='__main__':main()
