"""Real HF GPU provider for native multi-cycle tasks, with owned selection.

All calls are batch1, eager attention, greedy under the model's frozen generation
configuration. Correct-context verification includes every token and EOS, with
actual repetition-penalty processing. Unsupported selectors fail closed.
No task oracle is imported or used to generate/repair an answer.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
import traceback

from native_store import digest
from tasks import canonical, messages, validate_schema


def physical_gpu_call_count(calls):
    """Structural CPU rejection is not a neural/GPU invocation."""
    return sum(c.get('operation') in ('generate','verify') for c in calls)


def rejection_counts(calls):
    return dict(content=sum(c.get('operation')=='verify' and c.get('accepted') is False for c in calls),
                structural=sum(c.get('operation')=='verify-structural-rejection' for c in calls))


def frozen_substitution(config, request):
    patch = config.get("candidate_substitution")
    if patch is None:
        return None
    assert patch["kind"] == "fixed-json-return"
    cycles = patch.get("on_cycles", [0])
    assert isinstance(cycles, list) and all(type(c) is int and c >= 0 for c in cycles)
    if request["cycle"] not in cycles:
        return None
    value = patch["by_family"][request["family"]] if "by_family" in patch else patch["value"]
    assert isinstance(value, dict)
    return {"kind": "fixed-json-return", "value": value, "on_cycles": cycles}


def load_asset_manifest(path, model_path):
    manifest = json.loads(Path(path).read_text())
    rows = manifest["files"] if isinstance(manifest, dict) else manifest
    root = Path(model_path).resolve()
    checked = []
    for row in rows:
        rel = Path(row["path"])
        p = rel if rel.is_absolute() else root / rel
        p = p.resolve()
        assert p.is_relative_to(root), "asset manifest escaped frozen model root"
        assert p.is_file() and p.stat().st_size == row["bytes"]
        h = hashlib.sha256()
        with p.open("rb") as f:
            for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
                h.update(b)
        assert h.hexdigest() == row["sha256"]
        checked.append({"path": str(p.relative_to(root)), "sha256": row["sha256"], "bytes": row["bytes"]})
    actual_files = {str(p.relative_to(root)) for p in root.iterdir() if p.is_file()
                    and p.suffix in {".json", ".safetensors", ".model", ".txt"}}
    assert actual_files <= {r["path"] for r in checked}, "manifest omitted tokenizer/config/weights assets"
    assert any(r["path"].endswith(".safetensors") for r in checked)
    return digest(checked)


class ActualModel:
    def __init__(self, config, role, device, dtype):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        self.torch, self.role, self.device = torch, role, int(device)
        self.budget = int(config["max_new_tokens"])
        self.template_kwargs = dict(config.get("chat_template_kwargs", {}))
        assert self.budget > 0
        torch.set_num_threads(int(config.get("cpu_threads", 3)))
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        self.tokenizer = AutoTokenizer.from_pretrained(config["model_path"], local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(config["model_path"], dtype=getattr(torch, dtype),
            attn_implementation="eager", local_files_only=True, trust_remote_code=False).to("cuda:" + str(device)).eval()
        gc = self.model.generation_config
        for k, v in [("num_beams", 1), ("no_repeat_ngram_size", 0), ("encoder_repetition_penalty", 1.),
                     ("min_length", 0), ("min_new_tokens", None)]:
            assert getattr(gc, k, v) == v, "unsupported selection rule: " + k
        for k in ("bad_words_ids", "forced_bos_token_id", "forced_eos_token_id", "suppress_tokens",
                  "begin_suppress_tokens", "sequence_bias", "constraints", "forced_decoder_ids"):
            assert not getattr(gc, k, None), "unsupported selection rule: " + k
        self.eos = gc.eos_token_id
        self.eos_set = {self.eos} if isinstance(self.eos, int) else set(self.eos or [])
        assert self.eos_set
        self.contract = {"model_asset_sha256": config["verified_asset_sha256"], "role": role,
            "dtype": dtype, "device": int(device), "batch_size": 1, "attention": "eager",
            "max_new_tokens": self.budget, "do_sample": False, "eos_token_id": sorted(self.eos_set),
            "repetition_penalty": gc.repetition_penalty, "generation_config_sha256": digest(gc.to_dict()),
            "chat_template_kwargs": self.template_kwargs,
            "torch": torch.__version__, "transformers": importlib.metadata.version("transformers")}
        self.observed = None
        def before_forward(_module, args, kwargs):
            ids = kwargs.get("input_ids", args[0] if args else None)
            if self.observed is None and ids is not None:
                self.observed = ids.detach().cpu().tolist()
        self.hook = self.model.register_forward_pre_hook(before_forward, with_kwargs=True)

    def input_ids(self, m):
        return self.tokenizer.apply_chat_template(m, tokenize=True, add_generation_prompt=True, **self.template_kwargs)

    def render(self, z):
        raw = self.tokenizer.decode(z, skip_special_tokens=True)
        clean = raw.strip()
        if clean.startswith("```"):
            lines = clean.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                clean = "\n".join(lines[1:-1])
        try:
            value = json.loads(clean)
        except (ValueError, TypeError):
            value = None
        return raw, clean, value

    def generate(self, ids, purpose):
        t = self.torch
        x = t.tensor([ids], device="cuda:" + str(self.device), dtype=t.long)
        self.observed = None
        t.cuda.synchronize(self.device)
        start, perf = time.time_ns(), time.perf_counter()
        with t.inference_mode():
            out = self.model.generate(input_ids=x, attention_mask=t.ones_like(x), do_sample=False,
                max_new_tokens=self.budget, pad_token_id=self.tokenizer.eos_token_id, return_dict_in_generate=True)
        t.cuda.synchronize(self.device)
        elapsed, end = time.perf_counter() - perf, time.time_ns()
        seq = out.sequences[0].detach().cpu().tolist()
        assert self.observed == [ids] and seq[:len(ids)] == ids
        z = seq[len(ids):]
        raw, rendered, value = self.render(z)
        stop = bool(z) and z[-1] in self.eos_set and all(v not in self.eos_set for v in z[:-1])
        return {"operation": "generate", "purpose": purpose, "role": self.role,
            "actual_input_ids": self.observed[0], "logical_input_ids": ids,
            "tokens": z, "raw_decoded_text": raw, "rendered_text": rendered, "value": value,
            "terminated_by_eos": stop, "complete": stop and len(z) <= self.budget,
            "started_ns": start, "completed_ns": end, "actual_gpu_seconds": elapsed,
            "contract": self.contract, "physical_worker_drained": True}

    def verify(self, ids, z, purpose):
        from transformers import RepetitionPenaltyLogitsProcessor
        t = self.torch
        stop = bool(z) and len(z) <= self.budget and z[-1] in self.eos_set and all(v not in self.eos_set for v in z[:-1])
        if not stop:
            return {"operation": "verify-structural-rejection", "purpose": purpose, "role": self.role,
                    "accepted": False, "actual_gpu_seconds": 0., "candidate_tokens": z,
                    "reason": "complete-token-stop-budget-gate", "physical_worker_drained": True}
        x = t.tensor([ids + z], device="cuda:" + str(self.device), dtype=t.long)
        L = len(ids)
        self.observed = None
        def trim_logits(_m, args):
            return (args[0][:, L - 1:L + len(z) - 1, :],)
        hook = self.model.lm_head.register_forward_pre_hook(trim_logits)
        t.cuda.synchronize(self.device)
        start, perf = time.time_ns(), time.perf_counter()
        try:
            with t.inference_mode():
                logits = self.model(input_ids=x, attention_mask=t.ones_like(x), use_cache=False, return_dict=True).logits
                assert bool(t.isfinite(logits).all()), "nonfinite authority logits"
                penalty = self.model.generation_config.repetition_penalty
                process = RepetitionPenaltyLogitsProcessor(penalty) if penalty != 1 else None
                predicted = []
                for i in range(len(z)):
                    scores = logits[:, i, :].clone()
                    if process is not None:
                        scores = process(x[:, :L + i], scores)
                    predicted.append(int(scores.argmax(-1)[0]))
            t.cuda.synchronize(self.device)
        finally:
            hook.remove()
        elapsed, end = time.perf_counter() - perf, time.time_ns()
        assert self.observed == [ids + z]
        raw, rendered, value = self.render(z)
        return {"operation": "verify", "purpose": purpose, "role": self.role,
            "logical_input_ids": ids, "actual_input_ids": self.observed[0], "tokens": z,
            "predicted_tokens": predicted, "accepted": predicted == z,
            "raw_decoded_text": raw, "rendered_text": rendered, "value": value,
            "terminated_by_eos": True, "complete": True, "contract": self.contract,
            "started_ns": start, "completed_ns": end, "actual_gpu_seconds": elapsed,
            "physical_worker_drained": True}


class ActualProvider:
    tier = "ACTUAL_GPU_MODEL"

    def __init__(self, config):
        self.provider_init_started_ns = time.time_ns()
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        os.environ["HF_HUB_OFFLINE"] = "1"
        self.config = dict(config)
        self.identity = config["identity"]
        mode = config["selection_mode"]
        assert mode in {"direct", "strict_fallback", "candidate_only"}
        assert config["authority_dtype"] == "float32", "this study's trusted authority is FP32"
        root = Path(config["experiment_root"]).resolve()
        assert Path(config["model_path"]).resolve().is_relative_to(root)
        self.asset_validation_started_ns = time.time_ns()
        self.config["verified_asset_sha256"] = load_asset_manifest(config["model_manifest"], config["model_path"])
        self.asset_validation_completed_ns = time.time_ns()
        self.loaded_ns = time.time_ns()
        self.authority = None
        if mode != "candidate_only":
            self.authority = ActualModel(self.config, "authority", config["authority_device"], config["authority_dtype"])
        self.proposer = None
        if mode != "direct":
            self.proposer = ActualModel(self.config, "proposal", config["proposer_device"], config["proposer_dtype"])
        self.ready_ns = time.time_ns()
        self.contract = {"adapter": "native-two-family-v1", "selection_mode": mode,
            "authority": self.authority.contract if self.authority else None, "proposer": self.proposer.contract if self.proposer else None,
            "render_rule": "skip-special-strip-one-outer-code-fence-parse-json-v1",
            "injection_contract": config.get("candidate_substitution"), "physical_batch_size": 1,
            "load_policy": "mode-required-models-only"}

    def prepare(self, frozen):
        m = messages(frozen)
        ids = (self.authority or self.proposer).input_ids(m)
        if self.proposer and self.authority:
            assert self.proposer.input_ids(m) == ids, "role tokenizer identity differs"
        return {"messages": m, "input_ids": ids, "frozen_request_hash": frozen["request_hash"],
                "family": frozen["family"], "cycle": frozen["cycle"], "contract": self.contract}

    def generate(self, request):
        self.calls_in_progress = []
        start = time.time_ns()
        try:
            return self._generate(request)
        except BaseException:
            return {"status": "unfulfilled", "reason": "provider-execution-failure",
                "provider_identity": self.identity, "evidence_tier": self.tier,
                "request": request, "contract": self.contract, "actual_calls": self.calls_in_progress,
                "error": traceback.format_exc(), "started_ns": start, "completed_ns": time.time_ns(),
                "provider_init_started_ns": self.provider_init_started_ns,
                "asset_validation_started_ns": self.asset_validation_started_ns,
                "asset_validation_completed_ns": self.asset_validation_completed_ns,
                "load_started_ns": self.loaded_ns, "load_ready_ns": self.ready_ns,
                "complete": False, "terminated_by_eos": False, "physical_worker_drained": False,
                "selection_authorized": False,
                "cost_scope": "completed calls retained; failing call cost unknown and cannot be counted zero"}

    def _generate(self, request):
        start = time.time_ns()
        mode, calls = self.config["selection_mode"], self.calls_in_progress
        selected = None
        injection = None
        if mode == "direct":
            selected = self.authority.generate(request["input_ids"], "trusted-direct-selection")
            calls.append(selected)
        else:
            original = self.proposer.generate(request["input_ids"], "low-trust-proposal")
            calls.append(original)
            candidate = list(original["tokens"])
            patch = frozen_substitution(self.config, request)
            if patch is not None:
                # This is an explicit controlled low-trust return replacement,
                # never a natural incidence or a trusted-authority corruption.
                assert patch["kind"] == "fixed-json-return" and isinstance(patch["value"], dict)
                text = canonical(patch["value"])
                candidate = self.proposer.tokenizer.encode(text, add_special_tokens=False) + [min(self.proposer.eos_set)]
                injection = {"kind": "controlled-low-trust-return", "value": patch["value"],
                    "original_tokens": original["tokens"], "replacement_tokens": candidate,
                    "CPU_only_encoding": True, "actual_gpu_seconds": 0.}
            if mode == "candidate_only":
                raw, rendered, value = self.proposer.render(candidate)
                selected = {**original, "tokens": candidate, "raw_decoded_text": raw,
                            "rendered_text": rendered, "value": value,
                            "terminated_by_eos": bool(candidate and candidate[-1] in self.proposer.eos_set),
                            "complete": len(candidate) <= self.proposer.budget and bool(candidate)
                                and candidate[-1] in self.proposer.eos_set}
            else:
                verify = self.authority.verify(request["input_ids"], candidate, "strict-correct-context-selection")
                calls.append(verify)
                if verify["accepted"]:
                    selected = verify
                else:
                    selected = self.authority.generate(request["input_ids"], "actual-fp32-authority-fallback")
                    calls.append(selected)
        valid = selected["complete"] and selected["terminated_by_eos"] and validate_schema(request["family"], selected["value"])
        actual_prefix = selected["actual_input_ids"][:len(request["input_ids"])]
        assert actual_prefix == request["input_ids"]
        result = {"status": "selected" if valid else "unfulfilled", "provider_identity": self.identity,
            "evidence_tier": self.tier, "request": request, "contract": self.contract,
            "actual_input_ids": actual_prefix, "actual_selected_tensor_input_ids": selected["actual_input_ids"],
            "tokens": selected["tokens"],
            "rendered_text": selected["rendered_text"], "value": selected["value"],
            "raw_decoded_text": selected["raw_decoded_text"],
            "terminated_by_eos": selected["terminated_by_eos"], "complete": selected["complete"],
            "selection_authorized": mode != "candidate_only", "selected_call_index": next(i for i, x in enumerate(calls) if x is selected) if mode != "candidate_only" else 0,
            "physical_worker_drained": all(x["physical_worker_drained"] for x in calls),
            "actual_calls": calls, "controlled_injection": injection,
            "candidate_exposure": "none_direct_generation" if mode == "direct" else "controlled_substitution" if injection else "actual_candidate",
            "verification_rejection_observed": any(rejection_counts(calls).values()),
            "verification_rejection_counts": rejection_counts(calls),
            "started_ns": start, "completed_ns": time.time_ns(),
            "actual_gpu_seconds": sum(x["actual_gpu_seconds"] for x in calls),
            "load_started_ns": self.loaded_ns, "load_ready_ns": self.ready_ns,
            "provider_init_started_ns": self.provider_init_started_ns,
            "asset_validation_started_ns": self.asset_validation_started_ns,
            "asset_validation_completed_ns": self.asset_validation_completed_ns,
            "selected_evidence_semantics": "verification actual tensor includes candidate suffix; logical input prefix is separately bound"}
        if not valid:
            result["reason"] = "actual-model-schema-stop-budget-failure"
        return result


def create_provider(config):
    return ActualProvider(config)
