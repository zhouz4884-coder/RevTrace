"""Recheck NN1145's existing whitespace-only final-task CER, stdlib only.

The normalize expression is identical to content_endpoints.normalize in the
frozen runtime. Punctuation/case/Unicode forms receive no additional mapping.
"""
import math

SCOPE='Fixed whitespace-only original native CER; final task quality, not provisional correctness.'

def need(ok,message):
    if not ok:raise ValueError(message)

def normalize(text):return ''.join(c for c in text if not c.isspace())

def character_edits(reference,actual):
    """Unit-cost code-point insertion/deletion/substitution edit distance."""
    previous=list(range(len(actual)+1))
    for i,expected in enumerate(reference,1):
        current=[i]
        for j,observed in enumerate(actual,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(expected!=observed)))
        previous=current
    return previous[-1]

def verify_quality(qualities,source,expected_original_final_text):
    need(isinstance(qualities,list)and len(qualities)==1,'one original source quality row required per cell')
    q=qualities[0]
    need(q['source_id']==source['source_id']and q['scope']==SCOPE,'original native quality identity/scope differs')
    need(isinstance(source['reference'],str)and isinstance(q['final_text'],str),'original reference/final transcript is not text')
    need(q['final_text']==expected_original_final_text,'final quality transcript differs from original complete-state reference')
    reference=normalize(source['reference']);actual=normalize(q['final_text'])
    edits=character_edits(reference,actual);n=len(reference);cer=edits/n if n else None
    need(type(q['reference_characters'])is int and q['reference_characters']==n,'original normalized reference-character count differs')
    need(type(q['character_edits'])is int and q['character_edits']==edits,'original unit-cost character edit count differs')
    if cer is None:need(q['CER']is None,'zero-character reference CER must remain unknown')
    else:need(not isinstance(q['CER'],bool)and isinstance(q['CER'],(int,float))and math.isfinite(q['CER'])and abs(q['CER']-cer)<=1e-12,'original CER differs')
    return dict(source_id=source['source_id'],reference_characters=n,character_edits=edits,CER=cer,final_text=q['final_text'],scope=SCOPE)

def pool_quality(rows):
    n=sum(r['reference_characters']for r in rows);edits=sum(r['character_edits']for r in rows)
    return dict(evaluated_outputs=len(rows),distinct_sources=len({r['source_id']for r in rows}),reference_characters=n,
        character_edits=edits,CER=edits/n if n else None,scope=SCOPE)
