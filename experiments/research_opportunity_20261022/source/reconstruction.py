"""Pure logical job reconstruction from ledger + pinned session/audio/contract."""
import hashlib,math
def reconstruct_next(state,spec,audio,contract,contract_digest,runtime_digest):
 from revtrace.dgft import digest_tokens
 if spec['session_id']!=state.session_id:raise ValueError('fixed session mapping mismatch')
 if hashlib.sha256(audio).hexdigest()!=spec['audio_sha256']:raise ValueError('manifest audio mismatch')
 fine=int(contract['fine_seconds']*contract['sample_rate']);F=state.audio_frontier_window;total=len(audio)//4
 if F>=total:raise ValueError('no further audio')
 if F%fine:raise ValueError('unfinished non-window frontier')
 end=min(total,F+contract['rho']*fine);chunk=F//fine;endwin=math.ceil(end/fine)
 return {'session_id':state.session_id,'role':'authority','source_id':spec['source_id'],'language':spec['language'],'parent':state.checkpoint_id,'parent_prompt_digest':digest_tokens(state.prompt_tokens),'prompt_tokens':list(state.prompt_tokens),'chunk_id':chunk,'chunk_advance':endwin-chunk,'end_window':endwin,'audio_start_sample':F,'audio_end_sample':end,'contract_digest':contract_digest,'runtime_digest':runtime_digest,'prefix_audio_sha256':hashlib.sha256(audio[:end*4]).hexdigest(),'interval_audio_sha256':hashlib.sha256(audio[F*4:end*4]).hexdigest()}
