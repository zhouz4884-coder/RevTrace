"""Bounded publication hygiene scan: never prints matched credential values."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

W = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else W / 'runtime'
assert root.is_relative_to(W) and root.is_dir()
patterns = {'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
            'github_token': re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
            'AWS_access_key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')}
sensitive_names = {'PASSWORD', 'PASSWD', 'API_KEY', 'ACCESS_TOKEN', 'GITHUB_TOKEN', 'HF_TOKEN', 'SECRET_KEY', 'CLIENT_SECRET'}
findings = []; checked = []
for f in sorted(root.rglob('*')):
    if not f.is_file() or '.git' in f.parts or '__pycache__' in f.parts: continue
    if f.suffix not in ['.py', '.json', '.jsonl', '.md', '.txt', '.log', '.csv', '.patch', '.ini', '.toml'] and f.name != '.gitattributes': continue
    raw = f.read_bytes()
    if len(raw) > 25_000_000: raise ValueError('Explicit review required for large text asset')
    text = raw.decode('utf-8'); rel = f.relative_to(root).as_posix()
    checked.append({'path': rel, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    for name, pattern in patterns.items():
        for m in pattern.finditer(text): findings.append({'path': rel, 'line': text.count('\n', 0, m.start()) + 1, 'rule': name})
    if f.suffix == '.py':
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)): continue
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str) or len(value.value) < 8: continue
            for target in targets:
                if isinstance(target, ast.Name):
                    name = target.id.upper()
                    if name in sensitive_names or any(name.endswith('_' + s) for s in sensitive_names):
                        findings.append({'path': rel, 'line': node.lineno, 'rule': 'sensitive_literal_assignment'})
report = {'status': 'NO_PATTERN_FINDINGS' if not findings else 'NEEDS_MANUAL_REVIEW_DO_NOT_PUBLISH',
          'root': str(root), 'checked_text_files': len(checked), 'findings_without_values': findings,
          'scope': 'bounded credential-pattern/literal scan; not a proof of complete secrecy or anonymity',
          'files': checked}
out = W / ('PUBLICATION_HYGIENE_' + root.name + '.json')
assert not out.exists(), 'Retain prior scan; choose a fresh release root if rescanning'
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
assert not findings
