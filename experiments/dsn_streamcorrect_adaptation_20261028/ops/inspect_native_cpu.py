import pathlib,json,subprocess,importlib.metadata as md
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f'
print('EXISTING MODELS',json.dumps([p.name for p in (B/'models').iterdir()]))
print('ENV',json.dumps({p:md.version(p) if md.packages_distributions().get(p.replace('-','_')) else None for p in ['torch','transformers','peft','tiktoken','accelerate','soundfile']}))
for rel in ['simul_whisper/simul_whisper.py','whisper_streaming/vac_online_processor.py','simul_whisper/config.py']:
 lines=(P/rel).read_text().splitlines()
 print('FILE',rel)
 if 'vac_' in rel:
  indices=[i for i,line in enumerate(lines) if any(k in line for k in ['from_pretrained','PeftModel','corrector_ckpt','AutoModel','AutoProcessor'])]
 elif 'config' in rel:indices=[0]
 else:indices=[i for i,line in enumerate(lines) if 'self.' in line and '=' in line and i<300]
 for i in indices:print('\n'.join(f'{n+1} {lines[n]}' for n in range(max(0,i-2),min(len(lines),i+5))))
