"""Actual native model worker; imports CUDA only after per-process assignment."""
import collections,hashlib,json,os,pathlib,random,time,traceback

def worker_main(role,gpu,settings,commands,results):
    try:
        os.environ.update(CUDA_VISIBLE_DEVICES=str(gpu),HF_HOME=settings['hf_home'],HF_HUB_OFFLINE='1',
            TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
            CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')
        import numpy as np,torch,soundfile as sf
        torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        from native_bridge import NativeBridge
        from feedback_contract import FeedbackCut
        begun=time.perf_counter()
        model=NativeBridge(**settings['backend'],role=role)
        audio={}
        for source in settings['sources']:
            p=pathlib.Path(source['path']);raw=p.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=source['audio_sha256']:raise ValueError('frozen audio file changed')
            a,sr=sf.read(p,dtype='float32',always_2d=False)
            if sr!=16000 or a.ndim!=1 or len(a)!=source['frames']:raise ValueError('frozen native audio format changed')
            audio[source['source_id']]=(a,source['audio_sha256'])
        # One real native ASR/corrector warmup, separately accounted, no source
        # reselection or alteration; actual serving starts after both READYs.
        first=settings['sources'][0];a,h=audio[first['source_id']]
        initial=model.initial_for(h)
        _,warmup=model.step(audio=a,start=initial,end=16000,is_last=False)
        initials={sid:model.initial_for(h).state for sid,(a,h) in audio.items()}
        def dtypes(module):
            counts=collections.Counter()
            for parameter in module.parameters():counts[str(parameter.dtype)]+=parameter.numel()
            return dict(counts)
        results.put(dict(kind='ready',role=role,gpu=gpu,pid=os.getpid(),model_load_and_warmup_seconds=time.perf_counter()-begun,
            initials=initials,warmup=warmup,asr_parameter_dtypes=dtypes(model.engine.model),
            corrector_parameter_dtypes=dtypes(model.corrector_model) if role=='authority' else None))
        while True:
            command=commands.get()
            if command is None:break
            sid=command['source_id'];a,h=audio[sid];start=FeedbackCut(command['start'])
            if start.state['contract']['source_sha']!=h:raise ValueError('cross-source native cut')
            cut,row=model.step(audio=a,start=start,end=command['end'],is_last=command['end']==len(a))
            results.put(dict(kind='completed',role=role,gpu=gpu,job_id=command['job_id'],source_id=sid,
                start=start.state,end=cut.state,record=row,returned=time.perf_counter()))
        torch.cuda.synchronize();results.put(dict(kind='drained',role=role,pid=os.getpid()))
    except BaseException:
        results.put(dict(kind='failed',role=role,pid=os.getpid(),traceback=traceback.format_exc()))
