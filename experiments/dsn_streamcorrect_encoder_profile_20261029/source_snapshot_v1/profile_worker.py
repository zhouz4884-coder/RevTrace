"""Original model execution with an explicit E-only observation/substitution hook."""
import hashlib,json,os,pathlib,time,traceback
from encoder_wire import encode,decode

class EncoderCaptured(Exception):pass

def worker_main(gpu,config,commands,results):
    try:
        cache=pathlib.Path(config['cache_root'])
        for k,rel in [('HF_HOME','huggingface'),('HF_MODULES_CACHE','huggingface/modules'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','xdg'),('TRITON_CACHE_DIR','triton'),('TORCHINDUCTOR_CACHE_DIR','inductor'),('CUDA_CACHE_PATH','cuda'),('NUMBA_CACHE_DIR','numba')]:
            p=cache/rel;p.mkdir(parents=True,exist_ok=True);os.environ[k]=str(p)
        (cache/'xdg/torch/kernels').mkdir(parents=True,exist_ok=True)
        os.environ.update(CUDA_VISIBLE_DEVICES=str(gpu),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8',PYTHONDONTWRITEBYTECODE='1')
        import sys,random,types,numpy as np,soundfile as sf,torch
        torch.set_num_threads(1);torch.manual_seed(1701);np.random.seed(1701);random.seed(1701)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        import importlib.metadata
        actual_packages={k:importlib.metadata.version(k) for k in config['expected_packages']}
        assert actual_packages==config['expected_packages']
        sys.path.insert(0,config['imported_runtime_root'])
        from candidate_bridge import CandidateBridge
        from feedback_contract import FeedbackCut
        settings=config['settings'];begun=time.perf_counter()
        model=CandidateBridge(**settings['backend'],stage_role='authority',source_commit=config['imported_runtime_commit'],corrector_dtype='float32')
        audio={}
        for s in settings['model_sources']:
            p=pathlib.Path(s['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==s['audio_sha256']
            a,sr=sf.read(p,dtype='float32');assert sr==16000 and a.ndim==1 and len(a)==s['frames'];audio[s['source_id']]=a
        warm=settings['warmup'];wsrc=next(x for x in settings['model_sources'] if x['source_id']==warm['source_id'])
        wc=model.rebind_warm_cut(warm['original_reference_start_state'],wsrc['audio_sha256'])
        wr=model.warm_neural_ready(audio=audio[warm['source_id']],start=wc,end=32000)
        enc=model.engine.model.encoder;assert 'forward' not in vars(enc)
        from simul_whisper.whisper.model import MultiHeadAttention
        assert MultiHeadAttention.use_sdpa is False
        assert not any(m._forward_hooks or m._forward_pre_hooks for m in enc.modules()),'unexpected encoder hooks'
        assert not model.engine.model.training and not torch.is_autocast_enabled()
        identity=dict(config['encoder_identity'],dimensions=vars(model.engine.model.dims),
            precision='float32',autocast=False,TF32=False,SDPA=False,eval=True)
        results.put(dict(kind='ready',gpu=gpu,pid=os.getpid(),identity=identity,
            load_and_neural_ready_seconds=time.perf_counter()-begun,warmup=wr,
            environment=dict(python=sys.version,executable=sys.executable,packages=actual_packages,torch_version=torch.__version__,cuda=torch.version.cuda,autocast=False,TF32=False),
            memory_allocated=torch.cuda.memory_allocated(),sent_perf=time.perf_counter()))
        while True:
            cmd=commands.get()
            if cmd is None:break
            start=FeedbackCut(cmd['start']);stats={};wire=None;job_begin=time.perf_counter();received=time.perf_counter()
            original=enc.forward
            def wrapped(mel,*args,**kwargs):
                nonlocal wire
                if args or kwargs:raise ValueError('changed encoder invocation')
                torch.cuda.synchronize();entry=time.perf_counter()
                mbegin=time.perf_counter();mel_cpu=mel.detach().cpu().contiguous();mel_bytes=mel_cpu.numpy().tobytes();mel_sha=hashlib.sha256(mel_bytes).hexdigest();mend=time.perf_counter()
                stats.update(encoder_entry_perf=entry,actual_mel_sha256=mel_sha,mel_shape=list(mel.shape),mel_dtype=str(mel.dtype),mel_stride=list(mel.stride()),mel_finite=bool(torch.isfinite(mel).all().item()),mel_hash_seconds=mend-mbegin)
                if cmd['kind']=='received_E_full':
                    decbegin=time.perf_counter();header,data=decode(cmd['wire'],expected_identity=identity,expected_mel=mel_sha,expected_shape=(1,model.engine.model.dims.n_audio_ctx,model.engine.model.dims.n_audio_state));decoded=time.perf_counter()
                    host=np.frombuffer(data,dtype='<f4').reshape(header['shape']).copy();prepared=time.perf_counter()
                    feature=torch.from_numpy(host).to(model.engine.model.device);torch.cuda.synchronize();restored=time.perf_counter()
                    stats.update(original_encoder_executed=False,wire_receive_to_encoder_entry_seconds=entry-received,
                        wire_decode_verify_seconds=decoded-decbegin,cpu_tensor_prepare_seconds=prepared-decoded,
                        H2D_sync_seconds=restored-prepared,actual_import_and_verify_seconds=restored-decbegin,
                        feature_shape=list(feature.shape),feature_dtype=str(feature.dtype),feature_stride=list(feature.stride()),
                        feature_sha256=header['feature_sha256'],feature_finite=bool(torch.isfinite(feature).all().item()),received_E_provenance=header['execution_provenance'],encoder_return_perf=restored)
                    stats['actual_import_verify_finite_seconds']=time.perf_counter()-decbegin
                    return feature
                torch.cuda.synchronize();ebegin=time.perf_counter();feature=original(mel);torch.cuda.synchronize();eend=time.perf_counter()
                stats.update(original_encoder_executed=True,encoder_begin_perf=ebegin,encoder_return_perf=eend,
                    encoder_seconds=eend-ebegin,feature_shape=list(feature.shape),feature_dtype=str(feature.dtype),
                    feature_stride=list(feature.stride()),feature_finite=bool(torch.isfinite(feature).all().item()))
                assert feature.dtype==torch.float32 and feature.ndim==3
                cbegin=time.perf_counter();owned=feature.detach().clone();torch.cuda.synchronize();cloned=time.perf_counter()
                host=owned.to('cpu').contiguous();torch.cuda.synchronize();copied=time.perf_counter()
                data=host.numpy().tobytes();hashed=time.perf_counter();feature_sha=hashlib.sha256(data).hexdigest();hashend=time.perf_counter()
                stats.update(feature_sha256=feature_sha,feature_bytes=len(data),owned_clone_seconds=cloned-cbegin,
                    D2H_sync_seconds=copied-cloned,cpu_feature_bytes_seconds=hashed-copied,feature_hash_seconds=hashend-hashed)
                if cmd['kind']=='wrong_E_only':
                    packbegin=time.perf_counter();wire=encode(data,shape=feature.shape,mel_sha256=mel_sha,identity=identity,
                        provenance=dict(worker_gpu=gpu,job_id=cmd['job_id'],source_id=cmd['source_id'],full_birth_start_sha=start.sha256,target=cmd['end'],profile_source_commit=config['profile_source_commit']))
                    packed=time.perf_counter();stats.update(binary_pack_and_hash_seconds=packed-packbegin,
                        actual_capture_export_seconds=packed-cbegin,feature_wire_bytes=len(wire),feature_wire_sha256=hashlib.sha256(wire).hexdigest())
                    raise EncoderCaptured()
                return feature
            enc.forward=wrapped
            try:
                try:
                    cut,row=model.full_step(audio=audio[cmd['source_id']],start=start,end=cmd['end'],is_last=cmd['is_last'])
                    assert cmd['kind']!='wrong_E_only','missing actual encoder observation'
                    outcome=dict(end=cut.state,record=row,full_infer_completed=True)
                except EncoderCaptured:
                    assert cmd['kind']=='wrong_E_only';torch.cuda.synchronize();model.engine._clean_cache()
                    outcome=dict(full_infer_completed=False,original_C_U_executed=False,feedback_cut_emitted=False,encoder_only=True)
            finally:del enc.forward
            assert enc.forward.__func__ is original.__func__
            results.put(dict(kind='completed',gpu=gpu,job_id=cmd['job_id'],source_id=cmd['source_id'],operation=cmd['kind'],
                frozen_start_sha=start.sha256,end_frontier=cmd['end'],encoder=stats,wire=wire,
                command_received_perf=received,parent_dispatch_perf=cmd['parent_dispatch_perf'],
                worker_job_begin_perf=job_begin,worker_job_end_perf=time.perf_counter(),sent_perf=time.perf_counter(),**outcome))
        results.put(dict(kind='stopped',gpu=gpu,pid=os.getpid(),sent_perf=time.perf_counter()))
    except BaseException as exc:
        results.put(dict(kind='failed',gpu=gpu,error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),sent_perf=time.perf_counter()))
        raise
