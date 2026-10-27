"""Independent local task judgments; never called during model generation."""
from itertools import combinations


def prefix(family,source,prior):
    values=prior.get('completed' if family=='runbook' else 'reserved',[])
    kept=[];cost=0
    for x in values:
        if x in kept:break
        if family=='runbook':
            if x not in source['dependencies'] or not set(source['dependencies'][x])<=set(kept):break
        else:
            if x not in source['jobs'] or cost+source['jobs'][x]['cost']>source['capacity']:break
            cost+=source['jobs'][x]['cost']
        kept.append(x)
    return kept


def prior_valid(family,source,prior):
    kept=prefix(family,source,prior)
    if family=='runbook':
        return kept==prior['completed'] and (prior['last_action'] is None or bool(kept) and prior['last_action']==kept[-1])
    return kept==prior['reserved'] and prior['remaining']==source['capacity']-sum(source['jobs'][x]['cost'] for x in kept)


def judge(family,source,prior,request,value):
    if not isinstance(value,dict):return dict(schema_valid=False,current_output_valid=False,transition_valid=False,current_step_success=False)
    if family=='runbook':
        schema=(set(value)=={'completed','last_action'} and isinstance(value['completed'],list) and all(type(x) is str for x in value['completed']) and (value['last_action'] is None or type(value['last_action']) is str))
    else:
        schema=(set(value)=={'reserved','remaining'} and isinstance(value['reserved'],list) and all(type(x) is str for x in value['reserved']) and type(value['remaining']) is int)
    if not schema:return dict(schema_valid=False,current_output_valid=False,transition_valid=False,current_step_success=False)
    kept=prefix(family,source,prior)
    if family=='runbook':
        after=value['completed'];action=value['last_action'];ready=[x for x,d in source['dependencies'].items() if x not in kept and set(d)<=set(kept)]
        valid=prefix(family,source,value)==after and (action is None or bool(after) and action==after[-1])
        transition=(action in ready and after==kept+[action] and request['action_budget']>=1) if ready else after==kept and action is None
        return dict(schema_valid=True,current_output_valid=valid,transition_valid=transition,current_step_success=valid and transition)
    jobs=source['jobs'];capacity=source['capacity'];before_cost=sum(jobs[x]['cost'] for x in kept)
    after=value['reserved'];subset=len(after)==len(set(after)) and all(x in jobs for x in after) and after[:len(kept)]==kept
    new=after[len(kept):] if subset else [];used=sum(jobs[x]['cost'] for x in after) if subset else capacity+1
    feasible=subset and len(new)<=request['max_new_jobs'] and used<=capacity
    valid=prefix(family,source,value)==after and value['remaining']==capacity-sum(jobs[x]['cost'] for x in after)
    options=[];available=sorted(set(jobs)-set(kept))
    for n in range(request['max_new_jobs']+1):
        for xs in combinations(available,n):
            if before_cost+sum(jobs[x]['cost'] for x in xs)<=capacity:options.append(sum(jobs[x]['value'] for x in xs))
    objective=sum(jobs[x]['value'] for x in new) if feasible else None
    transition=feasible and value['remaining']==capacity-used
    return dict(schema_valid=True,current_output_valid=valid,transition_valid=transition,current_step_success=bool(transition and valid and objective==max(options,default=0)))
