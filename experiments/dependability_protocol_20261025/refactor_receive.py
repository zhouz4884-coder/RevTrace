"""Mechanical extraction only; assertions retain the original handler body."""
from pathlib import Path
import hashlib, json
W=Path(__file__).resolve().parent
p=W/'runtime/src/revtrace/live_qwen.py'
s=p.read_text(encoding='utf8')
begin=s.index('            for result in results:\n',s.index('    def _receive(self):'))
end=s.index('\n    def _commit_ready(self):',begin)
body=s[begin+len('            for result in results:\n'):end]
assert body.count('                        continue\n')==1
dedented='\n'.join(line[8:] if line.startswith('        ') else line for line in body.split('\n'))
dedented=dedented.replace('                continue\n','                return\n')
new=s[:begin]+'            for result in results:\n                self._accept_result(name, result)\n\n    def _accept_result(self, name, result):\n'+dedented+s[end:]
assert new.count('    def _accept_result(')==1
p.write_text(new,encoding='utf8',newline='\n')
(W/'RECEIVE_REFACTOR.json').write_text(json.dumps({'before_sha256':hashlib.sha256(s.encode()).hexdigest(),
    'after_sha256':hashlib.sha256(new.encode()).hexdigest(),
    'mechanical_change':'Extract result-loop body with identical statements; loop continue becomes handler return.'},indent=2)+'\n')
