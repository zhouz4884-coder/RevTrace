"""Independent tokenizer/render reconstruction for the offline checker.

No model execution or production admission function is called. Asset byte hashes
are verified against the frozen manifest, including tokenizer and generation cfg.
"""
import hashlib
import json
from pathlib import Path


class Codec:
    def __init__(self, model_path, manifest_path):
        from transformers import AutoTokenizer
        root = Path(model_path).resolve()
        data = json.loads(Path(manifest_path).read_text())
        rows = data["files"] if isinstance(data, dict) else data
        covered = set()
        for row in rows:
            p = Path(row["path"])
            p = (p if p.is_absolute() else root / p).resolve()
            assert p.is_relative_to(root) and p.stat().st_size == row["bytes"]
            h = hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
                    h.update(chunk)
            assert h.hexdigest() == row["sha256"]
            covered.add(p.name)
        assert "tokenizer_config.json" in covered and "generation_config.json" in covered
        self.tokenizer = AutoTokenizer.from_pretrained(root, local_files_only=True, trust_remote_code=False)
        self.generation = json.loads((root / "generation_config.json").read_text())

    def encode(self, messages, contract):
        spec = contract.get("authority") or contract["proposer"]
        return self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                   **spec.get("chat_template_kwargs", {}))

    def decode(self, tokens, contract):
        spec = contract.get("authority") or contract["proposer"]
        eos = set(spec["eos_token_id"])
        assert 0 < len(tokens) <= spec["max_new_tokens"]
        assert tokens[-1] in eos and not any(t in eos for t in tokens[:-1])
        text = self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
        if text.startswith("```"):
            rows = text.splitlines()
            assert len(rows) >= 3 and rows[-1].strip() == "```"
            text = "\n".join(rows[1:-1])
        json.loads(text)
        return text
