import json
from content_fault import replace_value_tokens,parse_json_memory
EOS=100000
class T:
    def encode(self,s,**kw):return list(map(ord,s))
    def decode(self,ids,**kw):return ''.join(chr(i) for i in ids if i!=EOS)
def test_content_only_preserves_compact_pretty_and_fence():
    for raw in ['{"destination":"LOC_04_OLD","owner":"OWN_04"}',
                '{\n  "destination": "LOC_04_OLD",\n  "owner": "OWN_04"\n}',
                '```json\n{ "destination": "LOC_04_OLD", "owner": "OWN_04" }\n```']:
        z=T().encode(raw)+[EOS];new,c=replace_value_tokens(T(),z,'LOC_04_OLD','LOC_04_FAULT',{EOS})
        assert T().decode(new)==raw.replace('LOC_04_OLD','LOC_04_FAULT')
        assert parse_json_memory(T().decode(new))==dict(destination='LOC_04_FAULT',owner='OWN_04')
        assert c['same_terminal_EOS'] and c['preserves_all_non_destination_bytes']
