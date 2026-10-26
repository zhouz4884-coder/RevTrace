"""Persistent HF/eager GPU executor; shared by 3090 and V100 live runs."""
from __future__ import annotations
import hashlib
import json
import multiprocessing as mp
import os
import queue
import time
import traceback
from pathlib import Path


def execution_tokens(job, enabled=False):
    """Fault-fixture seam before model execution, never a post-score mutation."""
    if 'fault_actual_prompt_tokens' in job:
        if not enabled:
            raise ValueError('execution-context override requires declared fault-probe mode')
        return tuple(int(x) for x in job['fault_actual_prompt_tokens'])
    return tuple(int(x) for x in job['prompt_tokens'])


def worker_main(commands, results, config):
    if config.get('model_adapter')=='whisper':
        from whisper_kernel_worker import worker_main as whisper_main
        return whisper_main(commands,results,config)
    os.environ["CUDA_VISIBLE_DEVICES"] = str(config["gpu"])
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "2"
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from qwen_asr import Qwen3ASRModel, parse_asr_output
        from revtrace.dgft import digest_tokens
        from revtrace.sequence_verifier import token_stop_certificate
        torch.set_num_threads(2)
        if config.get('render_contract'):
            import inspect,importlib.metadata
            declared=config['render_contract']
            for name,wanted in declared['assets'].items():
                if Path(name).name!=name:raise ValueError('unsafe renderer asset path')
                if hashlib.sha256((Path(config['model'])/name).read_bytes()).hexdigest()!=wanted:raise ValueError('renderer/worker asset mismatch')
            if hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest()!=declared['parse_source_sha256']:raise ValueError('renderer/parser source mismatch')
            if importlib.metadata.version('tokenizers')!=declared['tokenizers_version']:raise ValueError('renderer/tokenizer runtime mismatch')
        dtype = torch.float16 if config["dtype"] == "float16" else torch.float32
        manifest = json.load(open(config["manifest"], encoding="utf-8"))
        sources = {}
        for row in manifest["sessions"]:
            source = Path(row["path"])
            if not source.is_file():
                source = Path(config["manifest"]).parent / source.name
            audio, rate = sf.read(source, dtype="float32")
            if rate != 16000 or audio.ndim != 1:
                raise ValueError("prepared mono 16 kHz audio required")
            sources[row["source_id"]] = np.asarray(audio, dtype="<f4")
            if hashlib.sha256(sources[row["source_id"]].tobytes()).hexdigest() != row["audio_sha256"]:
                raise ValueError("prepared audio checksum mismatch")
        engine = Qwen3ASRModel.from_pretrained(config["model"], torch_dtype=dtype,
            device_map={"": "cuda:0"}, attn_implementation="eager",
            low_cpu_mem_usage=True, local_files_only=True,
            max_inference_batch_size=config["microbatch"],
            max_new_tokens=config["max_new_tokens"])
        model, processor = engine.model, engine.processor
        tokenizer = processor.tokenizer
        delivery = None
        if config.get('row_delivery') == 'row':
            from row_delivery_worker import RowDeliveryTap
            eos_value=model.generation_config.eos_token_id
            delivery=RowDeliveryTap(results,processor,parse_asr_output,config,
                [eos_value] if isinstance(eos_value,int) else list(eos_value or []))
        if config.get('render_contract'):
            if hashlib.sha256(Path(inspect.getfile(type(processor))).read_bytes()).hexdigest()!=config['render_contract']['processor_source_sha256']:raise ValueError('renderer/worker processor source mismatch')
        bases = {lang: engine._build_text_prompt(context="", force_language=lang)
                 for lang in ("English", "Chinese")}

        def verify_tokens(moved, candidates, prompt_width):
            """Fixed candidate width, grouped teacher-forced greedy checks.

            This is an ASR mechanism adaptation, not SGLang/LLM-42. A failing
            candidate is repaired with the frozen FP32 generation operation.
            Only the matching initial prefix is meaningful after a mismatch.
            """
            window = int(config["verification_tokens"])
            width = ((max(map(len,candidates))+window-1)//window)*window
            assert all(0 < len(row) <= config["max_new_tokens"] for row in candidates)
            padding = tokenizer.pad_token_id
            if padding is None:
                padding = 0
            candidate_ids = torch.full((len(candidates), width), padding,
                                      dtype=torch.long, device="cuda:0")
            candidate_mask = torch.zeros_like(candidate_ids)
            for index, row in enumerate(candidates):
                candidate_ids[index, :len(row)] = torch.tensor(row, device="cuda:0")
                candidate_mask[index, :len(row)] = 1
            checked = dict(moved)
            checked["input_ids"] = torch.cat((moved["input_ids"], candidate_ids), dim=1)
            checked["attention_mask"] = torch.cat((moved["attention_mask"], candidate_mask), dim=1)
            # Avoid materializing vocabulary logits for the entire audio prompt.
            def restrict_head(_module, values):
                return (values[0][:, prompt_width-1:prompt_width+width-1, :],)
            hook = model.thinker.lm_head.register_forward_pre_hook(restrict_head)
            try:
                with torch.inference_mode():
                    output = model.thinker(**checked, use_cache=False, return_dict=True)
                    predictions = output.logits.argmax(dim=-1).cpu().tolist()
            finally:
                hook.remove()
            matches = []
            for row, pred in zip(candidates, predictions):
                matches.append(next((i for i,(a,b) in enumerate(zip(row,pred)) if a != b), len(row)))
            return matches, [pred[:len(row)] for row,pred in zip(candidates,predictions)]

        def execute(jobs, warmup=False):
            start = time.perf_counter()
            tap=delivery if not warmup else None
            lifecycle=config.get('lifecycle_instrumentation',True)
            if not warmup and lifecycle:results.put({'kind':'batch-started','started_perf':start,'job_ids':[j['job_id'] for j in jobs]})
            original_jobs = jobs
            grouped = config.get("verification_policy") == "grouped_replay" and not warmup
            if grouped:
                # Fixed row count; dummy rows carry no application effects.
                fixed_rows = int(config["verification_rows"])
                assert len(jobs) <= fixed_rows
                jobs = jobs + [jobs[-1]] * (fixed_rows-len(jobs))
            wavs, prompts, prefixes, digests, contexts = [], [], [], [], []
            for job in jobs:
                if not warmup and start < job["audio_ready_perf"]:
                    raise AssertionError("worker consumed future audio")
                wav = np.zeros(job['audio_end_sample'],dtype='<f4') if warmup else sources[job["source_id"]][:job["audio_end_sample"]]
                digests.append(hashlib.sha256(wav.tobytes()).hexdigest())
                actual_tokens=execution_tokens(job,config.get('allow_execution_context_override',False))
                raw = tokenizer.decode(actual_tokens, skip_special_tokens=False,
                                       clean_up_tokenization_spaces=False)
                prefix = ""
                if job["chunk_id"] >= 2 and raw:
                    ids, k = tokenizer.encode(raw), 5
                    while True:
                        prefix = tokenizer.decode(ids[:max(0,len(ids)-k)])
                        if "\ufffd" not in prefix or k >= len(ids):
                            break
                        k += 1
                prefixes.append(prefix)
                contexts.append({'declared_prompt_digest':digest_tokens(job['prompt_tokens']),
                    'executed_prompt_digest':digest_tokens(actual_tokens),
                    'executed_prompt_tokens':list(actual_tokens),
                    'actual_audio_sha256':digests[-1],
                    'conditioning_prefix_sha256':hashlib.sha256(prefix.encode()).hexdigest(),
                    'fault_override': 'fault_actual_prompt_tokens' in job,
                    'scope':'Observer instrumentation; not a trusted execution attestation'})
                prompts.append(bases[job["language"]]+prefix)
                wavs.append(wav)
            inputs = processor(text=prompts, audio=wavs, return_tensors="pt", padding=True)
            audits=[]
            if (config.get('capture_model_inputs',False) or config.get('online_selection_mode')) and not warmup:
                def tensor_identity(x):
                    y=x.detach().cpu().contiguous()
                    return {'shape':list(y.shape),'dtype':str(y.dtype),'sha256':hashlib.sha256(y.numpy().tobytes()).hexdigest()}
                batch_tensors={k:tensor_identity(v) for k,v in inputs.items()}
                for i,job in enumerate(jobs):
                    mask=inputs['attention_mask'][i].bool()
                    row_features={k:tensor_identity(v[i]) for k,v in inputs.items() if k not in ['input_ids','attention_mask'] and v.shape[0]==len(jobs)}
                    eos=model.generation_config.eos_token_id
                    audits.append({'source_id':job['source_id'],'audio_end_sample':job['audio_end_sample'],
                        'waveform_sha256':digests[i],'declared_prompt_tokens':job['prompt_tokens'],
                        'chunk_id':job['chunk_id'],'rollback_prefix':prefixes[i],
                        'input_ids':inputs['input_ids'][i].tolist(),'attention_mask':inputs['attention_mask'][i].tolist(),
                        'unpadded_input_ids':inputs['input_ids'][i][mask].tolist(),
                        'batch_tensors':batch_tensors,'row_features':row_features,
                        'language':job['language'],'dtype':config['dtype'],'batch_rows':len(jobs),
                        'prompt_width':inputs['input_ids'].shape[1],'max_new_tokens':config['max_new_tokens'],
                        'eos_token_ids':[eos] if isinstance(eos,int) else list(eos or []),
                        'adapter':'qwen-text-rollback5-unfixed2','do_sample':False,
                        'scope':'observed processed model inputs, not trusted attestation'})
            moved = {k: v.to("cuda:0", dtype=dtype) if torch.is_floating_point(v)
                     else v.to("cuda:0") for k,v in inputs.items()}
            length = moved["input_ids"].shape[1]
            if tap is not None:
                if len(audits)!=len(jobs):raise ValueError('row delivery requires actual input capture')
                tap.prepare(jobs,prefixes=prefixes,contexts=contexts,audits=audits,started=start)
            if not warmup and config.get('current_prefix_mode'):
                from current_prefix_worker import select_prefix
                return select_prefix(model=model,processor=processor,moved=moved,jobs=jobs,
                    prefixes=prefixes,contexts=contexts,audits=audits,config=config,start=start,
                    results=results,delivery=delivery)
            if not warmup and config.get('online_selection_mode'):
                if any('fault_actual_prompt_tokens' in j for j in jobs):raise ValueError('target verifier must not consume a fault override')
                from online_selection_worker import select_online
                return select_online(model=model,processor=processor,moved=moved,jobs=jobs,
                    prefixes=prefixes,contexts=contexts,audits=audits,config=config,start=start,results=results,delivery=tap)
            if not warmup and any('audit_rescore_tokens' in job for job in jobs):
                assert all('audit_rescore_tokens' in job for job in jobs)
                candidates=[job['audit_rescore_tokens'] for job in jobs]
                assert all(0<len(row)<=config['max_new_tokens'] for row in candidates)
                width=max(map(len,candidates)); pad=tokenizer.pad_token_id or 0
                candidate_ids=torch.full((len(jobs),width),pad,dtype=torch.long,device='cuda:0')
                mask=torch.zeros_like(candidate_ids)
                for i,row in enumerate(candidates):
                    candidate_ids[i,:len(row)]=torch.tensor(row,device='cuda:0');mask[i,:len(row)]=1
                checked=dict(moved)
                checked['input_ids']=torch.cat((moved['input_ids'],candidate_ids),dim=1)
                checked['attention_mask']=torch.cat((moved['attention_mask'],mask),dim=1)
                def restrict(_module,values):return (values[0][:,length-1:length+width-1,:],)
                hook=model.thinker.lm_head.register_forward_pre_hook(restrict)
                try:
                    with torch.inference_mode():
                        logits=model.thinker(**checked,use_cache=False,return_dict=True).logits
                        top=logits.topk(2,dim=-1)
                        chosen=logits.gather(-1,candidate_ids.unsqueeze(-1)).squeeze(-1).float()
                        competitor=torch.where(top.indices[:,:,0]==candidate_ids,top.values[:,:,1],top.values[:,:,0]).float()
                        margins=(chosen-competitor).cpu().tolist()
                        greedy=top.indices[:,:,0].cpu().tolist()
                    torch.cuda.synchronize()
                finally:hook.remove()
                end=time.perf_counter()
                return [{'job_id':job['job_id'],'runtime_digest':config['runtime_digest'],
                    'prefix_audio_sha256':digests[i],'started_perf':start,'completed_perf':end,
                    'token_ids':[],'state_tokens':[],'text':'','generated_tokens':0,
                    'hit_token_limit':False,'record_type':'teacher_forced_audit_only',
                    'scored_tokens':len(candidates[i]),'minimum_candidate_margin':min(margins[i][:len(candidates[i])]),
                    'matched_prefix_tokens':next((k for k,(a,b) in enumerate(zip(candidates[i],greedy[i])) if a!=b),len(candidates[i])),
                    'execution_context_audit':contexts[i]}
                    for i,job in enumerate(jobs)]
            if grouped:
                verify_start = time.perf_counter()
                candidates = [job["candidate_token_ids"] for job in jobs]
                matched, predicted = verify_tokens(moved, candidates, length)
                torch.cuda.synchronize()
                verify_seconds = time.perf_counter()-verify_start
                eos=model.generation_config.eos_token_id
                stop_ids=[eos] if isinstance(eos,int) else list(eos or [])
                certificates=[token_stop_certificate(c,p,eos_token_ids=stop_ids,max_new_tokens=config['max_new_tokens']) for c,p in zip(candidates,predicted)]
                failed = [i for i,j in enumerate(original_jobs) if not certificates[i][0]]
                repairs = None
                repair_seconds = 0.0
                if failed:
                    repair_start = time.perf_counter()
                    # Keep the same row schedule during repair. Only failing
                    # outputs replace candidates; all work is charged online.
                    with torch.inference_mode():
                        repairs = model.generate(**moved, do_sample=False,
                            max_new_tokens=config["max_new_tokens"], output_scores=False)
                    repair_ids = repairs.sequences[:, length:]
                    repair_text = processor.batch_decode(repair_ids, skip_special_tokens=True,
                        clean_up_tokenization_spaces=False)
                    repair_tokens = repair_ids.cpu().tolist()
                    torch.cuda.synchronize()
                    repair_seconds = time.perf_counter()-repair_start
                rows = []
                for index,job in enumerate(original_jobs):
                    if index in failed:
                        tokens = repair_tokens[index]
                        stops = set(stop_ids)
                        stop = next((i+1 for i,t in enumerate(tokens) if t in stops),len(tokens))
                        tokens = tokens[:stop]
                        next_raw = prefixes[index]+repair_text[index]
                        lang,text = parse_asr_output(next_raw,user_language=job["language"])
                        state_tokens = tokenizer.encode(next_raw)
                    else:
                        tokens = candidates[index]
                        raw = tokenizer.decode(tokens,skip_special_tokens=True,
                            clean_up_tokenization_spaces=False)
                        next_raw = prefixes[index]+raw
                        lang,text = parse_asr_output(next_raw,user_language=job["language"])
                        state_tokens = tokenizer.encode(next_raw)
                        if job.get("candidate_parent_bound",True) and list(state_tokens) != list(job["candidate_state_tokens"]):
                            raise AssertionError("verified tokens do not reconstruct proposed state projection")
                    rows.append({"job_id":job["job_id"],"runtime_digest":config["runtime_digest"],
                        "prefix_audio_sha256":digests[index],"started_perf":start,
                        "state_tokens":state_tokens,"token_ids":tokens,
                        "generated_tokens":len(tokens),"text":text,"language":lang,
                        "hit_token_limit":len(tokens)>=config["max_new_tokens"] and not any(t in {151645,151643} for t in tokens),
                        "verification":{"kind":"grouped_fixed_width_teacher_forced_asr_adaptation",
                            "batch_rows":len(jobs),"real_rows":len(original_jobs),
                            "window_tokens":config["verification_tokens"],
                            "candidate_parent_bound":job.get("candidate_parent_bound",True),
                            "matched_prefix_tokens":matched[index],"candidate_tokens":len(candidates[index]),
                            "predicted_token_ids":predicted[index],
                            "repaired":index in failed,"verify_batch_seconds":verify_seconds,
                            "stop_certificate":certificates[index],
                            "repair_batch_seconds":repair_seconds}})
                completed = time.perf_counter()
                for row in rows:
                    row["completed_perf"] = completed
                return rows
            model_started=model_completed=None
            if lifecycle:
                torch.cuda.synchronize();model_started=time.perf_counter()
                if not warmup:results.put({'kind':'model-started','started_perf':model_started,'job_ids':[j['job_id'] for j in jobs]})
            stream_kwargs={}
            if tap is not None:
                tap.set_phase('independent-generate',model_started or time.perf_counter(),range(len(jobs)))
                stream_kwargs['streamer']=tap.stream()
            with torch.inference_mode():
                generated = model.generate(**moved, do_sample=False,
                    max_new_tokens=config["max_new_tokens"],
                    output_scores=bool(config.get("collect_margins",False)),**stream_kwargs)
            if lifecycle:
                torch.cuda.synchronize();model_completed=time.perf_counter()
                if not warmup:results.put({'kind':'model-completed','completed_perf':model_completed,'job_ids':[j['job_id'] for j in jobs]})
            ids = generated.sequences[:, length:]
            decoded = processor.batch_decode(ids, skip_special_tokens=True,
                            clean_up_tokenization_spaces=False)
            token_rows = ids.detach().cpu().tolist()
            torch.cuda.synchronize()
            rows = []
            margins=None
            if config.get("collect_margins",False):
                # Diagnostic replay harness only; absent in frozen live cells.
                top=[score.float().topk(2,dim=-1).values for score in generated.scores]
                margins=torch.stack([x[:,0]-x[:,1] for x in top],dim=1).cpu().tolist()
            for row_index,(job,prefix,raw,tokens,audio_digest) in enumerate(zip(jobs,prefixes,decoded,token_rows,digests)):
                next_raw = prefix+raw
                lang,text = parse_asr_output(next_raw, user_language=job["language"])
                eos = model.generation_config.eos_token_id
                stops = {eos} if isinstance(eos,int) else set(eos or [])
                stop = next((i+1 for i,t in enumerate(tokens) if t in stops),len(tokens))
                tokens = tokens[:stop]
                rows.append({"job_id":job["job_id"], "runtime_digest":config["runtime_digest"],
                    "prefix_audio_sha256":audio_digest, "started_perf":start,
                    "model_started_perf":model_started,"model_completed_perf":model_completed,
                    "state_tokens":tokenizer.encode(next_raw), "token_ids":tokens,
                    "generated_tokens":len(tokens), "text":text, "language":lang,
                    "execution_context_audit":contexts[row_index],
                    "hit_token_limit":len(tokens)>=config["max_new_tokens"] and
                                      not any(t in stops for t in tokens)})
                if margins is not None:
                    rows[-1]["minimum_margin"]=min(margins[row_index][:len(tokens)])
                if 'fault_actual_prompt_tokens' in job:
                    # Real wrong-context GPU Z with declared-parent fields.
                    # This reconstruction is not correct-context generation.
                    from revtrace.certified_display import TrustedQwenRender
                    renderer=TrustedQwenRender(tokenizer,parse_asr_output,stops,config['max_new_tokens'])
                    normalize_start=time.perf_counter();P,text=renderer(job,tokens)
                    rows[-1]['F2_raw_execution_state_tokens']=list(rows[-1]['state_tokens'])
                    rows[-1]['F2_raw_execution_text']=rows[-1]['text']
                    rows[-1]['state_tokens']=P;rows[-1]['text']=text
                    rows[-1]['F2_field_normalization_seconds']=time.perf_counter()-normalize_start
                    rows[-1]['F2_normalization_scope']='deterministic fields of wrong-context GPU Z, not regeneration'
            completed = time.perf_counter()
            for row in rows:
                row["completed_perf"] = completed
            if audits:
                for row,audit in zip(rows,audits):
                    row['model_input_audit']=audit
                    row['terminated_by_eos']=bool(row['token_ids'] and row['token_ids'][-1] in audit['eos_token_ids'])
            return rows

        row = manifest["sessions"][0]
        execute([{"source_id":"__synthetic_zero_warmup__", "audio_end_sample":32000,
                  "prompt_tokens":[], "chunk_id":0, "language":row["language"],
                  "job_id":"warmup"}], warmup=True)
        results.put({"kind":"ready", "gpu":config["gpu"], "torch":torch.__version__,
                     "warmup_policy":"synthetic-zero-audio-not-a-serving-input",
                     "warmup_audio_sha256":hashlib.sha256(np.zeros(32000,dtype='<f4').tobytes()).hexdigest(),
                     "device":torch.cuda.get_device_name(0), "runtime_digest":config["runtime_digest"]})
        while True:
            jobs = commands.get()
            if jobs is None:
                return
            rows=execute(jobs)
            if delivery is not None:delivery.finish(rows)
            else:results.put({"kind":"result", "rows":rows})
    except BaseException:
        results.put({"kind":"error", "traceback":traceback.format_exc()})


class GPUExecutor:
    def __init__(self, name, config):
        self.name = name
        self.result_delay_seconds = float(config.get('result_delay_seconds',0.))
        if self.result_delay_seconds < 0:
            raise ValueError('result delay must be nonnegative')
        self._held_result = None
        self._deliver_after = 0.
        self.execution_phase='idle';self._telemetry=[]
        self.lifecycle_instrumentation=config.get('lifecycle_instrumentation',True)
        self.delay_every=int(config.get('delay_every',1))
        self.delay_offset=int(config.get('delay_offset',0))
        context = mp.get_context("spawn")
        self.commands, self.results = context.Queue(), context.Queue()
        self.process = context.Process(target=worker_main,
            args=(self.commands,self.results,config), name=name)
        self.process.start()
        self.ready = None

    def wait_ready(self):
        result = self.results.get(timeout=900)
        if result["kind"] != "ready":
            raise RuntimeError(result)
        self.ready = result

    def submit(self, jobs):
        self.execution_phase='submitted'
        self._delay_selected=any((int(j.get('end_window',0))-self.delay_offset)%self.delay_every==0 for j in jobs)
        self.commands.put(jobs)

    def drain_telemetry(self):
        value,self._telemetry=self._telemetry,[]
        return value

    def poll(self):
        if self._held_result is not None:
            if time.perf_counter()<self._deliver_after:
                return None
            result,self._held_result=self._held_result,None
            self.execution_phase='idle'
            return result
        try:
            result = self.results.get_nowait()
        except queue.Empty:
            if not self.process.is_alive():
                raise RuntimeError(f"GPU worker {self.name} exited")
            return None
        if result['kind'] in ['batch-started','model-started','model-completed']:
            self.execution_phase={'batch-started':'preprocessing','model-started':'model-executing','model-completed':'postprocessing'}[result['kind']]
            self._telemetry.append(result);return None
        if result["kind"] != "result":
            raise RuntimeError(result)
        rows=result['rows']
        if not hasattr(self,'_telemetry'):self._telemetry=[]
        self.execution_phase='completed'
        if getattr(self,'lifecycle_instrumentation',True):
            self._telemetry.append({'kind':'batch-completed','completed_perf':max(r['completed_perf'] for r in rows),
                                    'job_ids':[r['job_id'] for r in rows]})
        # Sparse delivery delay is frozen by logical target window, never outcome.
        # Submit records logical batch targets before observing outcomes.
        selected=getattr(self,'_delay_selected',True)
        if self.result_delay_seconds and selected:
            self.execution_phase='delivery-hold'
            self._held_result=rows
            self._deliver_after=time.perf_counter()+self.result_delay_seconds
            return None
        return rows

    def close(self):
        self.commands.put(None)
        self.process.join(timeout=15)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=10)
