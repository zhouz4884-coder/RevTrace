"""Declared Whisper conditioning; full Canonical history is never truncated.

The optional capacity policy is an explicit conventional bounded-context
control, not a recovery algorithm. It reserves the configured generation
budget in the model decoder. Only the conditioning view, never the committed
text or accepted audio history, is shortened.
"""
import json
from pathlib import Path


def whisper_conditioning_config(model_path, policy='unbounded-native-v1'):
    if policy not in ('unbounded-native-v1','reserve-generation-tail-v1'):
        raise ValueError('unknown Whisper conditioning policy')
    cfg=json.loads((Path(model_path)/'config.json').read_text())
    gen=json.loads((Path(model_path)/'generation_config.json').read_text())
    result=dict(policy=policy,max_target_positions=cfg['max_target_positions'])
    if policy=='reserve-generation-tail-v1':
        # Narrow, checked contract for this English checkpoint. Do not infer
        # multilingual/task/language prefixes from the transcript.
        start=gen['decoder_start_token_id'];no_ts=gen['no_timestamps_token_id']
        if gen.get('is_multilingual') is not False or gen.get('forced_decoder_ids')!=[[1,no_ts]]:
            raise ValueError('capacity policy requires the pinned English no-timestamps prefix')
        result['initial_decoder_ids']=[start,no_ts]
        result['previous_start_token_id']=gen['prev_sot_token_id']
    return result


def conditioning_prompt_ids(processor, history, budget, conditioning):
    raw=list(processor.get_prompt_ids(history,return_tensors='np')) if history else []
    raw=[int(x) for x in raw]
    if conditioning['policy']=='unbounded-native-v1':return raw,dict(raw_prompt_ids=raw,trimmed=0)
    if conditioning['policy']!='reserve-generation-tail-v1':raise ValueError('unknown policy')
    cap=conditioning['max_target_positions']-len(conditioning['initial_decoder_ids'])-budget
    if type(budget) is not int or budget<1 or cap<2:raise ValueError('no legal conditioning/generation capacity')
    if raw and raw[0]!=conditioning['previous_start_token_id']:raise ValueError('wrong previous-start marker')
    chosen=raw if len(raw)<=cap else [raw[0]]+raw[-(cap-1):]
    return chosen,dict(raw_prompt_ids=raw,trimmed=len(raw)-len(chosen),capacity=cap,
                      expected_initial_decoder_ids=chosen+conditioning['initial_decoder_ids'])


class TrustedWhisperRender:
    def __init__(self,processor,budget=256,conditioning=None):
        self.processor=processor;self.tokenizer=processor.tokenizer;self.budget=budget
        self.conditioning=conditioning
        self.eos={processor.tokenizer.eos_token_id}
    def __call__(self,job,Z):
        Z=list(Z)
        if not Z or len(Z)>self.budget:raise ValueError('invalid Whisper complete sequence')
        positions=[i for i,t in enumerate(Z) if t in self.eos]
        if positions and positions!=[len(Z)-1]:raise ValueError('Whisper EOS must be terminal')
        if not positions and len(Z)!=self.budget:raise ValueError('short incomplete Whisper result')
        tok=self.tokenizer
        history=tok.decode(job['prompt_tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
        if self.conditioning is not None:
            conditioning_prompt_ids(self.processor,history,self.budget,self.conditioning)
        segment=tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        text=(history+' '+segment).strip() if history else segment.strip()
        return tok.encode(text,add_special_tokens=False),text
