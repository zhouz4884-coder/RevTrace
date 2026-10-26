from revtrace.certified_display import ContinuityView
def fixture(n):
 v=ContinuityView('localagreement'+str(n));v.consume({'kind':'run-start','t0_perf':1})
 v.consume({'kind':'commit','session_id':0,'version':1,'segment_id':'t','audio_end_sample':32000,'next_prompt_tokens':[1]})
 v.consume({'kind':'canonical-display','session_id':0,'time':1,'displayed':1,'display_revision':1,'version':1,'transaction_id':'t','audio_end_sample':32000,'text':'alpha'})
 return v
def update(v,revision,text):return v.consume({'kind':'display','job_id':str(revision),'session_id':0,'time':revision,'displayed':revision,'display_revision':revision,'version':1,'canonical_version':1,'audio_end_sample':revision*32000,'text':text})
def test_no_blank_while_waiting_for_second_update():
 v=fixture(2);assert update(v,2,'alpha beta')['visible_text']=='alpha'
 assert update(v,3,'alpha beta gamma')['visible_text']=='alpha beta'
 assert update(v,4,'alpha delta')['visible_text']=='alpha beta'
def test_three_updates_full_word_agreement_not_partial_character():
 v=fixture(3);assert update(v,2,'alpha beta cart')['visible_text']=='alpha'
 assert update(v,3,'alpha beta car')['visible_text']=='alpha'
 assert update(v,4,'alpha beta cared')['visible_text']=='alpha beta'
def test_authority_correction_still_overrides_confirmed_display():
 v=fixture(2);update(v,2,'alpha beta');update(v,3,'alpha beta gamma')
 v.consume({'kind':'commit','session_id':0,'version':2,'segment_id':'u','audio_end_sample':64000,'next_prompt_tokens':[2]})
 r=v.consume({'kind':'canonical-display','session_id':0,'time':4,'displayed':4,'display_revision':4,'version':2,'transaction_id':'u','audio_end_sample':64000,'text':'alpha delta'})
 assert r['visible_text']=='alpha delta' and r['erased_characters']>0
