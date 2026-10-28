"""Coherent content-only intervention, never a new authority selection."""
import json
def parse_json_memory(raw):
    text=raw.strip()
    if text.startswith('```'):
        lines=text.splitlines();assert len(lines)>=3 and lines[-1].strip()=='```';text='\n'.join(lines[1:-1])
    value=json.loads(text);assert set(value)=={'destination','owner'} and all(isinstance(v,str) for v in value.values())
    return value

def replace_value_tokens(tok,original,old,new,eos):
    assert original and original[-1] in eos and not any(t in eos for t in original[:-1])
    ids=list(original[:-1]);raw=tok.decode(ids,skip_special_tokens=True);needle=json.dumps(old,ensure_ascii=False)
    assert raw.count(needle)==1,'replacement must name one exact JSON value'
    start=raw.index(needle);end=start+len(needle)
    lengths=[len(tok.decode(ids[:i],skip_special_tokens=True)) for i in range(len(ids)+1)]
    assert lengths==sorted(lengths),'nonmonotone decoded prefix outside declared ASCII-ID control'
    a=max(i for i,n in enumerate(lengths) if n<=start);b=min(i for i,n in enumerate(lengths) if n>=end)
    pre=tok.decode(ids[:a],skip_special_tokens=True);suffix=tok.decode(ids[b:],skip_special_tokens=True)
    assert raw.startswith(pre) and raw.endswith(suffix)
    stop=len(raw)-len(suffix) if suffix else len(raw)
    segment=raw[len(pre):start]+json.dumps(new,ensure_ascii=False)+raw[end:stop]
    new_ids=tok.encode(segment,add_special_tokens=False);z=ids[:a]+new_ids+ids[b:]+[original[-1]]
    expected=raw[:start]+json.dumps(new,ensure_ascii=False)+raw[end:]
    assert tok.decode(z,skip_special_tokens=True)==expected
    assert z[:a]==original[:a] and z[a+len(new_ids):-1]==original[b:-1] and z[-1]==original[-1]
    value=parse_json_memory(expected);before=parse_json_memory(raw)
    assert value==dict(before,destination=new)
    return z,dict(original_token_span=[a,b],replacement_tokens=new_ids,changed_char_span=[start,end],
        unchanged_prefix_token_ids=ids[:a],unchanged_suffix_token_ids=ids[b:],same_terminal_EOS=True,
        preserves_all_non_destination_bytes=True,decoded=expected)
