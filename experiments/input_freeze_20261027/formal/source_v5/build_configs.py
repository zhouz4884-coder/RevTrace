"""Frozen finite study cuts; no runtime result selection."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
guards=['GuardParent','GuardEpoch','GuardSource','GuardContent','GuardProjection','GuardComplete','GuardDurability','GuardDebtRecovery']
base='CONSTANTS\n Jobs = {j0,j1}\n Values = {0,1}\n Nil = nil\n MaxFrontier = 2\n'
runs=[]
def write(name,module,text,expected,target=None):
    text='CHECK_DEADLOCK FALSE\n'+text
    (P/name).write_text(text,encoding='utf8',newline='\n')
    runs.append(dict(id=name.removesuffix('.cfg'),module=module,config=name,expected=expected,target=target))
def adm(name,bad=None,target=None,fair=False):
    text=base+''.join(f' {g} = {str(g!=bad).upper()}\n' for g in guards)
    text+='SPECIFICATION '+('FairSpec' if fair else 'Spec')+'\n'
    text+='INVARIANT '+(target or 'Safety')+'\nINVARIANT TypeOK\n'
    if fair:text+='PROPERTY RecoveryProgress\nPROPERTY DurableVisibility\n'
    write(name,'AdmissionLifecycle.tla',text,'VIOLATION' if bad else 'PASS',target)
adm('admission-safe.cfg')
adm('admission-fair.cfg',fair=True)
for bad,target in [('GuardParent','Ancestry'),('GuardEpoch','WriterFence'),('GuardSource','SourceEligibility'),
                   ('GuardContent','AuthorizedContent'),('GuardProjection','TrustedProjection'),
                   ('GuardComplete','CompleteSelection'),('GuardDurability','VisibleDurable'),('GuardDebtRecovery','InputDebtPreserved')]:
    adm('admission-without-'+bad+'.cfg',bad,target)
for scenario in ['wrong-root','incomplete','wrong-session','old-epoch','broken-edge','revoked','complete']:
    text=f'CONSTANTS Mode = "maximal"\n Scenario = "{scenario}"\n Nil = nil\nSPECIFICATION FairSpec\nINVARIANT TypeOK\nINVARIANT SafeChoice\nINVARIANT SelectionCompleteness\nINVARIANT MaximumLegalProgress\nPROPERTY EventualDecision\n'
    write('selection-maximal-'+scenario+'.cfg','LegalSelection.tla',text,'PASS')
for mode,target in [('latest-safe','SelectionCompleteness'),('unsafe-latest','SafeChoice')]:
    text=f'CONSTANTS Mode = "{mode}"\n Scenario = "wrong-root"\n Nil = nil\nSPECIFICATION Spec\nINVARIANT {target}\n'
    write('selection-'+mode+'-negative.cfg','LegalSelection.tla',text,'VIOLATION',target)
text='CONSTANTS Budget = 2\n Deadline = 1\n MaxClock = 3\nSPECIFICATION FairSpec\nINVARIANT TypeOK\nINVARIANT NoAdmissionByWaiting\nINVARIANT NoFrozenJobWhileWaiting\nPROPERTY EventuallyDispatch\n'
write('wait-safe-fair.cfg','BoundedWait.tla',text,'PASS')
write('wait-timing-not-guaranteed.cfg','BoundedWait.tla',text+'INVARIANT DeadlineAlwaysMet\n','VIOLATION','DeadlineAlwaysMet')
(P/'RUNS.json').write_text(json.dumps(dict(schema='revtrace-formal-cuts-v1',runs=runs,
 proof_modules=['ProtocolProofs.tla'],scope='Finite TLC cuts and separate parameterized TLAPS lemmas; not complete Python/CUDA/OS refinement'),indent=2)+'\n')
print(len(runs),'TLC configurations frozen')
