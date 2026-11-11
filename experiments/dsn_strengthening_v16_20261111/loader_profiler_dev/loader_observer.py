"""Isolated opt-in loader observations; not integrated or a launch command.

No torch import, cache eviction, weight reads, tensor CPU copies or peak reset.
The optional mincore helper maps files privately and never indexes their data.
Any probe latency belongs to the caller's measured experiment interval.
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import platform
import resource
import shutil
import time


MEMINFO_KEYS=frozenset(('MemTotal','MemAvailable','MemFree','Buffers','Cached',
    'SReclaimable','Shmem','Dirty','Writeback','SwapCached','SwapTotal','SwapFree'))
VMSTAT_KEYS=frozenset(('pgfault','pgmajfault','pgpgin','pgpgout','pswpin','pswpout',
    'pgscan_kswapd','pgscan_direct','pgsteal_kswapd','pgsteal_direct'))


def _numeric_file(path, wanted=None, meminfo=False):
    values={}
    try:
        for line in Path(path).read_text().splitlines():
            cols=line.replace(':',' ').split()
            if len(cols)<2 or (wanted is not None and cols[0] not in wanted):continue
            try:value=int(cols[1])
            except ValueError:continue
            if meminfo and len(cols)>2 and cols[2]=='kB':value*=1024
            values[cols[0]]=value
        return dict(status='observed',values=values)
    except OSError as exc:return dict(status='unavailable',reason=type(exc).__name__)


def host_snapshot():
    begun=time.perf_counter();usage=resource.getrusage(resource.RUSAGE_SELF)
    result=dict(pid=os.getpid(),observed_perf=begun,process_cpu_seconds=time.process_time(),
        meminfo_bytes=_numeric_file('/proc/meminfo',MEMINFO_KEYS,True),
        vmstat=_numeric_file('/proc/vmstat',VMSTAT_KEYS),
        process_io=_numeric_file('/proc/self/io'),
        process_status=_numeric_file('/proc/self/status',frozenset(('VmRSS','RssAnon','RssFile','RssShmem','VmSwap')),True),
        process_faults=dict(minor=usage.ru_minflt,major=usage.ru_majflt),
        maxrss_bytes=usage.ru_maxrss*1024 if platform.system()=='Linux' else None,
        scope='global cache/counters plus this process only; not per-service causal attribution')
    result['probe_wall_seconds']=time.perf_counter()-begun
    return result


def residency_capability():
    try:available=hasattr(ctypes.CDLL(None,use_errno=True),'mincore')
    except OSError:available=False
    return dict(platform=platform.system(),mincore_symbol_available=available,
        vmtouch_path=shutil.which('vmtouch'),
        policy='observations only; no drop_caches, madvise eviction, vmtouch touch/evict or global cache controls')


def file_residency_readonly(path, chunk_bytes=64*1024*1024):
    """Linux page-cache residency without reading or touching mapped bytes.

    ACCESS_COPY supplies a private writable VMA solely so ctypes can obtain its
    address. No write/index/load occurs; the file is opened read-only. mincore
    is an instantaneous page-residency observation, not a latency guarantee.
    """
    begun=time.perf_counter();p=Path(path);before=p.stat()
    if platform.system()!='Linux':return dict(path=str(p),status='unavailable',reason='Linux_only')
    libc=ctypes.CDLL(None,use_errno=True)
    if not hasattr(libc,'mincore'):return dict(path=str(p),status='unavailable',reason='mincore_missing')
    page=os.sysconf('SC_PAGE_SIZE');chunk_bytes=max(page,(chunk_bytes//page)*page)
    libc.mincore.argtypes=(ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_ubyte))
    libc.mincore.restype=ctypes.c_int
    total=resident=0
    with p.open('rb') as stream:
        for offset in range(0,before.st_size,chunk_bytes):
            size=min(chunk_bytes,before.st_size-offset);n=math.ceil(size/page)
            with mmap.mmap(stream.fileno(),size,access=mmap.ACCESS_COPY,offset=offset) as mapping:
                address_view=ctypes.c_char.from_buffer(mapping)
                address=ctypes.addressof(address_view);vec=(ctypes.c_ubyte*n)()
                rc=libc.mincore(address,size,vec);del address_view
                if rc!=0:raise OSError(ctypes.get_errno(),'mincore failed')
                resident+=sum(bool(v&1) for v in vec);total+=n
    after=p.stat()
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
        raise RuntimeError('file identity changed during residency observation')
    return dict(path=str(p),status='observed',device=before.st_dev,inode=before.st_ino,
        file_bytes=before.st_size,mtime_ns=before.st_mtime_ns,page_bytes=page,
        pages=total,resident_pages=resident,resident_page_fraction=resident/total if total else None,
        observed_begin_perf=begun,probe_wall_seconds=time.perf_counter()-begun,
        probe='private mapping plus mincore; no file data read/touch or cache mutation',
        limitation='resident pages can change immediately; does not prove model tensor/CUDA residency or cold/warm latency')


def torch_allocator_snapshot(torch):
    """Caller passes already-imported torch; never initializes CUDA to observe it."""
    result=dict(cuda_initialized=bool(torch.cuda.is_initialized()),
        PYTORCH_CUDA_ALLOC_CONF=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),
        PYTORCH_ALLOC_CONF=os.environ.get('PYTORCH_ALLOC_CONF'))
    if not result['cuda_initialized']:
        result.update(status='not_initialized',cuda_metrics=None)
        return result
    device=torch.cuda.current_device();stats=torch.cuda.memory_stats(device)
    result.update(status='observed',logical_device=device,
        allocated_bytes=torch.cuda.memory_allocated(device),reserved_bytes=torch.cuda.memory_reserved(device),
        peak_allocated_since_worker_start_bytes=torch.cuda.max_memory_allocated(device),
        peak_reserved_since_worker_start_bytes=torch.cuda.max_memory_reserved(device),
        allocator_stats={k:stats.get(k) for k in ('active_bytes.all.current','inactive_split_bytes.all.current','num_alloc_retries','num_ooms')},
        current_stream_is_capturing=bool(torch.cuda.is_current_stream_capturing()),
        capture_scope='instant current-stream observation only; graph capture history remains unknown without API event counting',
        reset_peak_memory_stats_called=False)
    return result


def module_metadata(module):
    """Counts references without moving, hashing or materializing tensor data."""
    if module is None:return None
    counts={}
    if not hasattr(module,'parameters'):return dict(type=type(module).__name__,parameters='not_a_module')
    for tensor in module.parameters():
        key=str(tensor.dtype)+'@'+str(tensor.device)
        row=counts.setdefault(key,dict(parameter_tensors=0,elements=0,bytes=0))
        row['parameter_tensors']+=1;row['elements']+=tensor.numel();row['bytes']+=tensor.numel()*tensor.element_size()
    buffers={}
    for tensor in module.buffers():
        key=str(tensor.dtype)+'@'+str(tensor.device)
        row=buffers.setdefault(key,dict(buffer_tensors=0,elements=0,bytes=0))
        row['buffer_tensors']+=1;row['elements']+=tensor.numel();row['bytes']+=tensor.numel()*tensor.element_size()
    cfg=getattr(module,'config',None)
    device_map=getattr(module,'hf_device_map',None)
    if isinstance(device_map,dict):device_map={str(k):str(v) for k,v in device_map.items()}
    native_config={k:getattr(cfg,k,None) for k in ('max_position_embeddings','max_length','use_cache','_attn_implementation')}
    native_config['torch_dtype']=str(getattr(cfg,'torch_dtype',None))
    return dict(type=type(module).__name__,parameter_summary=counts,buffer_summary=buffers,
        hf_device_map=device_map,native_config=native_config,
        note='parameter byte sums may include aliased storage; unique storage/tensor-byte hashes belong to separate correctness gate')


def native_backend_fields(model):
    engine=model.engine;dims=getattr(engine.model,'dims',None)
    return dict(backend='native_author_StreamCorrect_PyTorch_Whisper_plus_HF_Peft_C_U',
        vllm_fields={key:dict(value=None,status='not_applicable',reason='not_a_vLLM_engine') for key in ('max_model_len','gpu_memory_utilization','KV_cache_blocks','vllm_CUDA_graph_capture_sizes')},
        asr_context_limits={k:getattr(dims,k,None) for k in ('n_text_ctx','n_audio_ctx','n_vocab')},
        asr=module_metadata(engine.model),corrector=module_metadata(model.corrector_model),
        native_KV=dict(engine_entries=len(engine.kv_cache),decoder_entries=len(engine.inference.kv_cache),
            representation='native dictionary cache, not block pool',
            cut_check='native_mutable_state requires both dictionaries empty at closed cut'),
        cuda_graph=dict(application_explicitly_enabled=False,
            evidence='audited application has no CUDAGraph/torch.cuda.graph/torch.compile path',
            runtime_capture_count=None,runtime_capture_count_status='unknown_unless_API_events_instrumented'),
        note='record observed limits/devices; do not substitute native context limits for vLLM max_model_len')
