"""Declared get_prompt_ids feedback contract, no invented suffix truncation."""
class TrustedWhisperRender:
    def __init__(self,processor,budget=256):
        self.processor=processor;self.tokenizer=processor.tokenizer;self.budget=budget
        self.eos={processor.tokenizer.eos_token_id}
    def __call__(self,job,Z):
        Z=list(Z)
        if not Z or len(Z)>self.budget:raise ValueError('invalid Whisper complete sequence')
        positions=[i for i,t in enumerate(Z) if t in self.eos]
        if positions and positions!=[len(Z)-1]:raise ValueError('Whisper EOS must be terminal')
        if not positions and len(Z)!=self.budget:raise ValueError('short incomplete Whisper result')
        tok=self.tokenizer
        history=tok.decode(job['prompt_tokens'],skip_special_tokens=True,clean_up_tokenization_spaces=False)
        segment=tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        text=(history+' '+segment).strip() if history else segment.strip()
        return tok.encode(text,add_special_tokens=False),text
