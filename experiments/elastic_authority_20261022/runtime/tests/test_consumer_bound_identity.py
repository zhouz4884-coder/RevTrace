import pytest
from revtrace.certified_display import ContinuityView,text_sha
from revtrace.dgft import digest_tokens
def build():
 v=ContinuityView('two_lane',strict_bound=True);v.consume({'kind':'run-start','t0_perf':99,'contract_digest':'C'})
 v.consume({'kind':'commit','session_id':0,'version':1,'segment_id':'t','audio_end_sample':32000,'next_prompt_tokens':[1],'certificate':{'contract_digest':'C','display_sha256':digest_tokens([2])}})
 p={'kind':'canonical-display','session_id':0,'version':1,'time':1,'displayed':1,'display_revision':1,'transaction_id':'t','audio_end_sample':32000,'text':'alpha','contract_epoch':1,'contract_digest':'C','canonical_projection_sha256':digest_tokens([1]),'canonical_Z_sha256':digest_tokens([2]),'text_sha256':text_sha('alpha')}
 return v,p
def test_full_certified_identity_and_epoch_fence():
 v,p=build();row=v.consume(p);assert row['canonical_epoch']==1 and row['certified_transaction']=='t' and row['certified_Z_sha256']==digest_tokens([2])
 old=dict(p,contract_epoch=0,display_revision=99);assert v.consume(old) is None
 future=dict(p,contract_epoch=2,display_revision=2)
 with pytest.raises(ValueError,match='new epoch'):v.consume(future)
@pytest.mark.parametrize('field,value',[('contract_digest','wrong'),('canonical_Z_sha256','wrong'),('text_sha256','wrong'),('canonical_projection_sha256','wrong')])
def test_malformed_bound_publication_fails(field,value):
 v,p=build();p[field]=value
 with pytest.raises(ValueError):v.consume(p)
