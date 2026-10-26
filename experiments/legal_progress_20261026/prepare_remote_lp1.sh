set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$P"
test ! -e "$O"
mkdir "$P"
mkdir "$O"
"$B/envs/revbatch-cu128/bin/python" - "$P" "$O" <<'PY'
import pathlib,inspect,hashlib,json,sys,importlib.metadata
p,o=map(pathlib.Path,sys.argv[1:]);b=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
r=b/'projects/revtrace_dependability_20261025/ck5_v6/runtime'
s=json.loads((r/'SOURCE_MANIFEST.json').read_text())
for f in s['files']:assert hashlib.sha256((r/f['path']).read_bytes()).hexdigest()==f['sha256']
from transformers.cache_utils import DynamicCache
from qwen_asr.core.transformers_backend.modeling_qwen3_asr import Qwen3ASRForConditionalGeneration,Qwen3ASRThinkerForConditionalGeneration
chunks=[]
for obj in [DynamicCache.crop,DynamicCache.get_seq_length,Qwen3ASRForConditionalGeneration.prepare_inputs_for_generation,Qwen3ASRThinkerForConditionalGeneration.prepare_inputs_for_generation,Qwen3ASRThinkerForConditionalGeneration.forward]:
 chunks.append(str(obj)+'\n'+inspect.getsource(obj))
out='\n\n'.join(chunks);(o/'MODEL_CACHE_API.txt').write_text(out)
(o/'SOURCE_AND_ENV.json').write_text(json.dumps(dict(baseline=s['code_commit'],source_files=len(s['files']),python=sys.version,
 packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']},model_api_sha256=hashlib.sha256(out.encode()).hexdigest()),indent=2)+'\n')
print(json.dumps(dict(status='BASELINE_VERIFIED_NO_GPU',api_bytes=len(out))))
PY
