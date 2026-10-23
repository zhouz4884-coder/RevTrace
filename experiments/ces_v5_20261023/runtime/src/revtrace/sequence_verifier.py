"""Full token and stopping-condition check; projection certification is separate."""
def token_stop_certificate(candidate,predicted,*,eos_token_ids,max_new_tokens):
    row=list(candidate);pred=list(predicted);stops=set(eos_token_ids)
    if not row or len(row)>max_new_tokens:return False,'invalid-length'
    first=next((i for i,t in enumerate(row) if t in stops),None)
    if first is not None and first!=len(row)-1:return False,'tokens-after-stop'
    if first is None and len(row)!=max_new_tokens:return False,'early-nonterminal-prefix'
    if len(pred)<len(row):return False,'incomplete-prediction'
    if row!=pred[:len(row)]:return False,'argmax-mismatch'
    return True,'eos' if first is not None else 'budget-cap'
