"""Maximum already-available LEGAL provisional progress, never state authority.

The scan is the reference. The ordinary reverse-query index and dominance
retention use the same native compatibility relation. Proof-node multiplicity
is retained: deleting an ambiguous ancestor must not manufacture compatibility.
"""
from copy import deepcopy
import time,heapq,hashlib
from .dgft import digest_tokens
from .envelope_display import EnvelopeView
from .kernel_runtime import KernelView,KernelEnvelopeScheduler

class HistoricalEnvelopeView(EnvelopeView):
    STRATEGIES={'latest','two-register','scan','mv-index','mv-index-envelope','dominance'}
    def __init__(self,*,strategy='scan',sealed_branches=False,revocation_contract='individual',kernel_support=None,**kwargs):
        if strategy not in self.STRATEGIES:raise ValueError('undeclared selection strategy')
        if revocation_contract not in ['individual','owner-mode']:raise ValueError('undeclared revocation contract')
        super().__init__(**kwargs);self.strategy=strategy;self.sealed_branches=sealed_branches;self.revocation_contract=revocation_contract;self.kernel_support=kernel_support
    def _supports(self,s,tip):
        """Finite exact root keys under the fixed fine-aligned input contract.

        Final fractional EOF cannot have an ahead tip. The native checker is
        retained as the final authority even for indexed hits.
        """
        node=tip;seen=set();out=set()
        while node['job_id'] not in seen:
            seen.add(node['job_id']);chunk=node.get('chunk_id');inp=node.get('input_projection_sha256')
            if chunk is None or inp is None:break
            out.add((chunk*self.fine,inp))
            parents=[p for p in s['nodes'].values() if p.get('end_window')==chunk and p.get('output_projection_sha256')==inp
                and p['audio_end_sample']<node['audio_end_sample'] and p.get('branch_generation')==node.get('branch_generation')]
            if len(parents)!=1:break
            node=parents[0];out.add((node['audio_end_sample'],node.get('output_projection_sha256')))
        return out
    def _select(self,s,mode):
        if mode in ['CERTIFIED-ONLY','RECOVERY']:return None
        tips=s.setdefault('_history_tips',set());revoked=s.setdefault('_history_revoked',set())
        def retire(ids):
            tips.difference_update(ids)
            for j in ids:
                proof=dict(s['nodes'][j]);proof.pop('text',None);s['nodes'][j]=proof
        retire({j for j in tips if j in s['nodes'] and s['nodes'][j]['audio_end_sample']<=s['F']})
        eligible=[s['nodes'][j] for j in tips if j in s['nodes'] and j not in revoked and s['nodes'][j]['audio_end_sample']>s['F']
            and s['nodes'][j].get('contract_epoch')==s.get('epoch') and s['nodes'][j].get('contract_digest')==self.contract]
        indexed=self.strategy in ['mv-index','mv-index-envelope','dominance']
        supports={}
        if indexed:
            graph_signature=tuple(sorted(s['nodes']))
            if s.get('_support_graph')!=graph_signature or any(j not in s.get('_support_cache',{}) for j in tips):
                s['_support_cache']={j:self._supports(s,s['nodes'][j]) for j in tips if j in s['nodes']}
                s['_support_graph']=graph_signature
            supports=s['_support_cache']
        current=(s['F'],s.get('Psha'))
        def future_keys(n):return {r for r in supports[n['job_id']] if (r[0]>s['F'] or r==current) and r[0]<n['audio_end_sample']}
        can_retire=self.sealed_branches and self.revocation_contract=='owner-mode' and self.kernel_support is None
        if self.strategy=='mv-index-envelope' and can_retire:
            winners={}
            for n in eligible:
                rank=(n['audio_end_sample'],n.get('display_revision',0),n['job_id'])
                for r in future_keys(n):
                    if r not in winners or rank>winners[r][0]:winners[r]=(rank,n['job_id'])
            keep={item[1] for item in winners.values()};retire({n['job_id'] for n in eligible if n['job_id'] not in keep})
            eligible=[n for n in eligible if n['job_id'] in keep]
        if self.strategy=='dominance' and can_retire:
            removed=set()
            # Only remove a candidate payload, never the ancestor proof or its
            # multiplicity. Every possible future key is >= ACTUAL applied F.
            for n in eligible:
                key=n['job_id'];roots=future_keys(n)
                if not roots:removed.add(key);continue
                for other in eligible:
                    oid=other['job_id']
                    if oid==key:continue
                    superior=(other['audio_end_sample'],other.get('display_revision',0),oid)>(n['audio_end_sample'],n.get('display_revision',0),key)
                    if superior and roots<=future_keys(other):removed.add(key);break
            retire(removed)
            eligible=[n for n in eligible if n['job_id'] not in removed]
        if indexed:
            # Ordinary reverse query index, rebuilt with graph changes. This
            # first version does NOT claim a new asymptotic indexing algorithm.
            index={}
            for n in eligible:
                for r in supports[n['job_id']]:index.setdefault(r,[]).append(n)
            candidates=index.get(current,[])
        else:candidates=eligible
        legal=[n for n in candidates if self._compatible(s,n,s.get('Psha')) and
            (self.kernel_support is None or self.kernel_support(s,n))]
        return max(legal,key=lambda n:(n['audio_end_sample'],n.get('display_revision',0),n['job_id']),default=None)
    def consume(self,e,observed=None):
        sid=e.get('session_id');kind=e['kind'];previous=self.states.get(sid,{})
        if kind=='display' and hashlib.sha256(e['text'].encode()).hexdigest()!=e.get('text_sha256'):
            raise ValueError('private text binding changed')
        if kind=='display' and e['job_id'] in previous.get('nodes',{}):
            old=previous['nodes'][e['job_id']]
            for field in ['session_id','contract_epoch','contract_digest','chunk_id','end_window','audio_end_sample','branch_generation','input_projection_sha256','output_projection_sha256','text_sha256','text']:
                if old.get(field)!=e.get(field):raise ValueError('immutable private result identity changed')
        if kind=='view-mode' and e.get('revoked_job_ids') and self.revocation_contract=='owner-mode':
            raise ValueError('individual revocation outside declared owner-mode contract')
        if kind=='display' and self.sealed_branches:
            if not 0<=e['chunk_id']<e['end_window']:raise ValueError('private input not a positive causal successor')
            last=previous.get('_branch_last',{}).get(e['branch_generation'],-1)
            if e['job_id'] not in previous.get('nodes',{}) and e['end_window']<=last:
                raise ValueError('new old-window node could change a sealed ancestry proof')
        before=previous.get('visible',0);oldtext=previous.get('visible_text','')
        prior_latest=previous.get('tentative');row=super().consume(e,observed)
        if row is None:return None
        s=self.states[sid];tips=s.setdefault('_history_tips',set());revoked=s.setdefault('_history_revoked',set())
        if kind=='display' and e['job_id'] in s['nodes']:
            tips.add(e['job_id']);s.setdefault('_branch_last',{})[e['branch_generation']]=max(e['end_window'],s.get('_branch_last',{}).get(e['branch_generation'],-1))
        if kind=='view-mode':
            revoked.update(e.get('revoked_job_ids',[]))
            # Typed owner withdrawal retires the current private generation.
            # Returning to NORMAL is not permission to resurrect those tips.
            if e['mode'] in ['CERTIFIED-ONLY','RECOVERY']:revoked.update(tips)
        tips.difference_update(revoked)
        if self.strategy in ['latest','two-register']:return row
        began=time.perf_counter_ns();mode=self.modes.get(sid,'NORMAL')
        if not s['version']:s['Psha']=digest_tokens(())
        selected=self._select(s,mode)
        if selected:
            s.update(tentative=selected,visible=selected['audio_end_sample'],visible_text=selected['text'])
        else:s.update(tentative=None,visible=s['F'],visible_text=s['text'])
        common=0
        for a,b in zip(oldtext,s['visible_text']):
            if a!=b:break
            common+=1
        row.update(valid_visible_frontier=s['visible'],visible_text=s['visible_text'],
            audio_rollback_samples=max(0,before-s['visible']),erased_characters=len(oldtext)-common,
            compatible_provisional_retained=selected is not None,
            tentative_invalidated=bool(prior_latest and selected is None),
            selected_private_job_id=selected['job_id'] if selected else None,
            selected_original_publication_revision=selected.get('display_revision') if selected else None,
            selection_trigger_revision=e['display_revision'],historical_selection_strategy=self.strategy,
            selection_query_ms=(time.perf_counter_ns()-began)/1e6,
            available_candidate_payloads=len(tips),retained_proof_nodes=len(s['nodes']),
            no_new_model_call=True,no_private_canonical_permission=True)
        return row

def kernel_private_support(kernel,s,tip):
    """Same stricter J-graph relation as final kernel, without mutating it.

    Native view checks branch-local ancestry; the generic core counts all
    matching actual parents. A cross-branch ambiguity must not make a maximum
    query choose a tip which the final unchanged core will reject.
    """
    sid=tip['session_id'];node=kernel.state.J.get(tip['job_id']);seen=set()
    if not node or node['sid']!=sid or not node.get('result'):return False
    if node['end']!=tip['audio_end_sample'] or node['result']['textsha']!=tip['text_sha256']:return False
    while not ((node['rootF']==s['F'] and node['inputP']==s['Psha']) or
               (node['end']==s['F'] and node['result']['P']==s['Psha'])):
        if node['id'] in seen:return False
        seen.add(node['id'])
        parents=[j for j in kernel.state.J.values() if j['sid']==sid and j['role']=='proposal' and j.get('result') and
            j['end']==node['rootF'] and j['result']['P']==node['inputP'] and j['end']<node['end']]
        if len(parents)!=1:return False
        node=parents[0]
    return True

class KernelHistoricalView(KernelView):
    def __init__(self,kernel,fine_samples=32000,*,strategy='scan',sealed_branches=False,revocation_contract='individual'):
        self.preview_factory=lambda **kw:HistoricalEnvelopeView(strategy=strategy,sealed_branches=sealed_branches,revocation_contract=revocation_contract,
            kernel_support=lambda s,n:kernel_private_support(kernel,s,n),**kw)
        super().__init__(kernel,fine_samples)

class HistoricalKernelScheduler(KernelEnvelopeScheduler):
    def __init__(self,*,history_strategy='scan',sealed_branches=False,revocation_contract='individual',**kwargs):
        self.consumer_view_factory=lambda kernel,fine:KernelHistoricalView(kernel,fine,strategy=history_strategy,sealed_branches=sealed_branches,revocation_contract=revocation_contract)
        super().__init__(**kwargs)
