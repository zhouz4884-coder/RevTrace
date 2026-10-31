"""Bounded fail-stop cleanup with PID-generation and session ownership proofs.

No neural path is changed. A failed CUDA query is unverified release, never PASS.
"""
from __future__ import annotations
import os,pathlib,signal,subprocess,time
from common import GateError,need,lines

class CleanupError(GateError):pass
def require(ok,message):
    if not ok:raise CleanupError(message)
def process_identity(pid):
    path=pathlib.Path('/proc')/str(pid)/'stat'
    try:fields=path.read_text().rsplit(')',1)[1].split()
    except FileNotFoundError:return None
    return dict(pid=int(pid),state=fields[0],ppid=int(fields[1]),pgid=int(fields[2]),session=int(fields[3]),start_ticks=int(fields[19]))
def process_group_members(group):
    rows=[]
    for path in pathlib.Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:row=process_identity(int(path.name))
        except (OSError,ValueError,IndexError):continue
        if row is not None and row['pgid']==group:rows.append(row)
    return rows
def owned_worker_identities(out,epoch):
    result=[];path=pathlib.Path(out)/f'owner_e{epoch}'/'owner_events.jsonl'
    if not path.exists():return result
    fragments=path.read_bytes().splitlines()
    for index,fragment in enumerate(fragments):
        try:
            import json
            row=json.loads(fragment)
        except (ValueError,UnicodeDecodeError):
            require(index==len(fragments)-1,'non-tail ownership metadata corruption')
            break
        if row.get('kind')=='worker_started' and isinstance(row.get('start_ticks'),int):
            result.append(dict(pid=row['pid'],start_ticks=row['start_ticks']))
    return result
def descendant_session_proofs(pid,expected_start_ticks):
    """Failure-time snapshot rooted in an exact live Popen generation."""
    root=process_identity(pid)
    if root is None:return []
    require(root['start_ticks']==expected_start_ticks,'outer child PID generation changed before descendant snapshot')
    rows={}
    for path in pathlib.Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:row=process_identity(int(path.name))
        except (OSError,ValueError,IndexError):continue
        if row is not None:rows[row['pid']]=row
    descendants={pid};changed=True
    while changed:
        before=len(descendants);descendants.update(r['pid'] for r in rows.values() if r['ppid'] in descendants);changed=len(descendants)!=before
    result=[]
    for member in rows.values():
        if member['pid'] in descendants and member['pid']!=pid and member['pgid']==member['session']==member['pid']:
            known=[r for r in rows.values() if r['pgid']==member['pid']]
            result.append(group_proof(member['pid'],member['start_ticks'],known_members=known))
    return result
def group_proof(pid,expected_start_ticks,*,bound_event=False,known_members=()):
    """Use a live launched leader or exact recorded descendant generation."""
    require(isinstance(expected_start_ticks,int) and expected_start_ticks>0,'missing launched Owner PID generation')
    leader=process_identity(pid);members=process_group_members(pid);known={(r['pid'],r['start_ticks']) for r in known_members}
    if leader is not None:
        require(leader['start_ticks']==expected_start_ticks,'Owner PID was reused; refuse unrelated group signal')
        if leader['pgid']==leader['session']==pid:route='live launched Owner PID/startticks/PGID/session'
        else:
            require(leader['state'] in ('Z','X') and not members,'Owner has not established its own registered session')
            route='exact launched PID already dead before its own session; no group signal inferred'
    elif members:
        require(any((r['pid'],r['start_ticks']) in known for r in members),'dead leader group lacks an exact known worker generation')
        route='dead launched Owner plus exact same-run recorded worker PID/startticks/session'
    else:
        # No group signal will be issued. CUDA emptiness still needs observation.
        route='no group members observed; no group signal authority inferred'
    for member in members:
        require(member['pgid']==member['session']==pid and member['start_ticks']>=expected_start_ticks,'group/session/generation ownership differs')
    if leader is not None:known.update((r['pid'],r['start_ticks']) for r in members)
    return dict(pid=pid,pgid=pid,session=pid,start_ticks=expected_start_ticks,bound_Owner_registration=bool(bound_event),ownership_route=route,known_members=[dict(pid=p,start_ticks=t) for p,t in sorted(known)])
def refresh_proof(proof,known_members=()):
    require(isinstance(proof,dict),'registered Owner proof must include PID generation, not a boolean')
    return group_proof(proof['pid'],proof['start_ticks'],bound_event=proof.get('bound_Owner_registration',False),known_members=[*proof.get('known_members',[]),*known_members])
def cuda_owners(*,timeout):
    require(timeout>0,'CUDA release deadline exhausted')
    try:raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=timeout)
    except subprocess.TimeoutExpired as exc:raise CleanupError('CUDA ownership CLI timed out; physical release is unverified') from exc
    except (OSError,subprocess.CalledProcessError) as exc:raise CleanupError('CUDA ownership query failed; physical release is unverified') from exc
    try:return [int(row.strip()) for row in raw.splitlines() if row.strip()]
    except ValueError as exc:raise CleanupError('invalid CUDA ownership response; physical release is unverified') from exc
def signal_group(proof):
    proof=refresh_proof(proof);group=proof['pgid'];members=process_group_members(group);signalled=False
    if any(r['state'] not in ('Z','X') for r in members):
        try:os.killpg(group,signal.SIGKILL);signalled=True
        except ProcessLookupError:pass
    return proof,signalled
def terminate_group(owner,proof,*,timeout=30.,query_timeout=2.):
    begun=time.perf_counter();deadline=begun+timeout;proof,signalled=signal_group(proof);group=proof['pgid']
    if owner is not None:owner.join(max(0.,min(5.,deadline-time.perf_counter())))
    while True:
        remaining=deadline-time.perf_counter();require(remaining>0,'Owner group/CUDA release deadline exceeded; release remains unverified')
        checked=refresh_proof(proof);members=process_group_members(group);active=[r for r in members if r['state'] not in ('Z','X')]
        pids=cuda_owners(timeout=min(query_timeout,remaining))
        if not active and not pids:
            return dict(owner_pid=group,owner_start_ticks=proof['start_ticks'],owner_exitcode=getattr(owner,'exitcode',None),ownership_proof=checked,group_SIGKILL_sent=signalled,confirmed_no_executing_members=True,retired_process_members=members,all_CUDA_owners_released=True,observed=time.perf_counter(),cleanup_seconds=time.perf_counter()-begun)
        time.sleep(min(.05,max(0.,deadline-time.perf_counter())))
def cleanup_owner(owner,registered_proof,launch_ticks,out,epoch):
    """Works after leader death; never hide release failure with leader-only kill."""
    known=owned_worker_identities(out,epoch)
    if registered_proof:
        proof=refresh_proof(registered_proof,known);return terminate_group(owner,proof)
    leader=process_identity(owner.pid)
    if leader is not None and leader['start_ticks']==launch_ticks and (leader['pgid']!=owner.pid or leader['session']!=owner.pid):
        # Failure before setsid(): this exact launched PID is ours, its inherited
        # process group is not. The frozen Owner starts no worker before setsid.
        owner.kill();owner.join(5);require(process_identity(owner.pid) is None or process_identity(owner.pid)['state'] in ('Z','X'),'unregistered exact Owner PID did not exit')
        proof=group_proof(owner.pid,launch_ticks,known_members=known)
        return terminate_group(owner,proof)
    proof=group_proof(owner.pid,launch_ticks,known_members=known)
    return terminate_group(owner,proof)
