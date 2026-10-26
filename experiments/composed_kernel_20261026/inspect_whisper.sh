set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
import inspect
from transformers.models.whisper.generation_whisper import WhisperGenerationMixin as W
for name in ['_postprocess_outputs','_retrieve_segment','generate_with_fallback']:
 f=getattr(W,name,None)
 if f:
  source=inspect.getsource(f).splitlines()
  print(name)
  for i,line in enumerate(source):
   if any(x in line for x in ['eos','sequences','[:-1]','return','GenerationMixin','super()']):
    print(i,line)
print(inspect.getsource(W.generate).splitlines()[-80:])
PY
