"""A private generation recipe cannot acquire authority by GPU placement."""
import hashlib,json

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()

def make_job(recipe,audio_bytes,*,runtime_digest,contract_digest,label,now):
    start,end=recipe['parent_frontier'],recipe['target_frontier']
    if not 0<=start<end<=len(audio_bytes)//4:raise ValueError('invalid or unreleased recipe interval')
    if recipe['parent_window']*32000!=start:raise ValueError('parent window/frontier mismatch')
    if recipe['target_window']!=(end+31999)//32000:raise ValueError('fine target must include partial final window')
    if recipe['target_window']<=recipe['parent_window']:raise ValueError('noncausal private target')
    return {'job_id':label,'session_id':recipe['session_id'],'source_id':recipe['source_id'],'language':recipe['language'],
      'role':'proposal','contract_epoch':recipe['parent_epoch'],'parent':recipe['parent_version'],
      'prompt_tokens':list(recipe['parent_P']),'parent_prompt_digest':hashlib.sha256(','.join(map(str,recipe['parent_P'])).encode('ascii')).hexdigest(),
      'chunk_id':recipe['parent_window'],'chunk_advance':recipe['target_window']-recipe['parent_window'],
      'end_window':recipe['target_window'],'audio_start_sample':start,'audio_end_sample':end,
      'audio_ready_perf':0.,'enqueue_perf':now,'contract_digest':contract_digest,'runtime_digest':runtime_digest,
      'prefix_audio_sha256':hashlib.sha256(audio_bytes[:end*4]).hexdigest(),
      'interval_audio_sha256':hashlib.sha256(audio_bytes[start*4:end*4]).hexdigest(),'branch_generation':0,
      'base_canonical_parent_contract_digest':recipe['parent_contract_digest'],
      'purpose':'offline-fresh-private-FP32-cost-only','Canonical_admission_or_publication_permitted':False}
