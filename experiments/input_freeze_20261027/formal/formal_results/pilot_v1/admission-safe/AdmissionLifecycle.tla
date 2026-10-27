------------------------ MODULE AdmissionLifecycle ------------------------
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Jobs, Values, Nil, MaxFrontier,
 GuardParent, GuardEpoch, GuardSource, GuardContent, GuardProjection,
 GuardComplete, GuardDurability, GuardDebtRecovery

VARIABLES epoch, source, offered, accepted, durableAccepted,
 frozen, selected, returned, returnedP, complete, durable, installed,
 visible, restarted, running, replayed, receipt

vars == <<epoch, source, offered, accepted, durableAccepted,
 frozen, selected, returned, returnedP, complete, durable, installed,
 visible, restarted, running, replayed, receipt>>

Phi(p,z) == (p + z) % 3
Frontier(h) == IF Len(h)=0 THEN 0 ELSE h[Len(h)].finish
Projection(h) == IF Len(h)=0 THEN 0 ELSE h[Len(h)].outputP
CommittedJobs == {durable[i].job : i \in 1..Len(durable)}

Init == /\ epoch=1 /\ source=1 /\ offered=0 /\ accepted=0 /\ durableAccepted=0
        /\ frozen=[j \in Jobs |-> Nil]
        /\ selected=[j \in Jobs |-> Nil]
        /\ returned=[j \in Jobs |-> Nil]
        /\ returnedP=[j \in Jobs |-> Nil]
        /\ complete=[j \in Jobs |-> FALSE]
        /\ durable=<<>> /\ installed=<<>> /\ visible=0
        /\ restarted=FALSE /\ running=TRUE /\ replayed={} /\ receipt=Nil

Offer == /\ offered<MaxFrontier /\ offered'=offered+1
         /\ UNCHANGED <<epoch,source,accepted,durableAccepted,frozen,selected,
              returned,returnedP,complete,durable,installed,visible,restarted,running,replayed,receipt>>
Accept == /\ running /\ accepted<offered
          /\ accepted'=offered /\ durableAccepted'=offered
          /\ UNCHANGED <<epoch,source,offered,frozen,selected,returned,returnedP,
               complete,durable,installed,visible,restarted,running,replayed,receipt>>

Freeze(j,b) == /\ running /\ frozen[j]=Nil
              /\ Len(installed)=Len(durable)
              /\ Frontier(installed)<b /\ b<=accepted
              /\ frozen'=[frozen EXCEPT ![j]=
                    [parent |-> Len(installed), owner |-> epoch, src |-> source,
                     start |-> Frontier(installed), finish |-> b,
                     inputP |-> Projection(installed)]]
              /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,selected,
                   returned,returnedP,complete,durable,installed,visible,restarted,running,replayed,receipt>>

Select(j,z) == /\ running /\ frozen[j]#Nil /\ selected[j]=Nil
              /\ selected'=[selected EXCEPT ![j]=z]
              /\ returned'=[returned EXCEPT ![j]=z]
              /\ returnedP'=[returnedP EXCEPT ![j]=Phi(frozen[j].inputP,z)]
              /\ complete'=[complete EXCEPT ![j]=TRUE]
              /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,
                   durable,installed,visible,restarted,running,replayed,receipt>>

CoherentTamper(j,z) == /\ selected[j]#Nil /\ j\notin CommittedJobs /\ returned[j]#z
                      /\ returned'=[returned EXCEPT ![j]=z]
                      /\ returnedP'=[returnedP EXCEPT ![j]=Phi(frozen[j].inputP,z)]
                      /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                           complete,durable,installed,visible,restarted,running,replayed,receipt>>
ProjectionTamper(j,p) == /\ selected[j]#Nil /\ j\notin CommittedJobs /\ returnedP[j]#p
                        /\ returnedP'=[returnedP EXCEPT ![j]=p]
                        /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                             returned,complete,durable,installed,visible,restarted,running,replayed,receipt>>
Truncate(j) == /\ selected[j]#Nil /\ j\notin CommittedJobs /\ complete[j]
              /\ complete'=[complete EXCEPT ![j]=FALSE]
              /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                   returned,returnedP,durable,installed,visible,restarted,running,replayed,receipt>>

SyncAdmission(j) == /\ running /\ selected[j]#Nil /\ j\notin CommittedJobs
             /\ Len(installed)=Len(durable)
             /\ (~GuardParent \/ (frozen[j].parent=Len(installed)
                  /\ frozen[j].start=Frontier(installed)
                  /\ frozen[j].inputP=Projection(installed)))
             /\ (~GuardEpoch \/ frozen[j].owner=epoch)
             /\ (~GuardSource \/ frozen[j].src=source)
             /\ (~GuardContent \/ returned[j]=selected[j])
             /\ (~GuardProjection \/ returnedP[j]=Phi(frozen[j].inputP,returned[j]))
             /\ (~GuardComplete \/ complete[j])
             /\ frozen[j].finish<=durableAccepted
             /\ durable'=Append(durable,
                   [job |-> j, parent |-> frozen[j].parent, inputP |-> frozen[j].inputP,
                    start |-> frozen[j].start, finish |-> frozen[j].finish,
                    owner |-> frozen[j].owner, observedOwner |-> epoch,
                    src |-> frozen[j].src, observedSource |-> source,
                    Z |-> returned[j], selectedZ |-> selected[j],
                    outputP |-> returnedP[j], complete |-> complete[j]])
             /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                  returned,returnedP,complete,installed,visible,restarted,running,replayed,receipt>>

Install == /\ running /\ Len(installed)<Len(durable)
           /\ installed'=durable
           /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                returned,returnedP,complete,durable,visible,restarted,running,replayed,receipt>>
Publish == /\ running /\ visible<Len(installed)
           /\ visible'=Len(installed)
           /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                returned,returnedP,complete,durable,installed,restarted,running,replayed,receipt>>
PublishUnsynced == /\ running /\ ~GuardDurability /\ Len(durable)=0
                   /\ \E j\in Jobs: selected[j]#Nil
                   /\ visible'=1
                   /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                        returned,returnedP,complete,durable,installed,restarted,running,replayed,receipt>>

ChangeSource == /\ running /\ source=1 /\ source'=2
                /\ UNCHANGED <<epoch,offered,accepted,durableAccepted,frozen,selected,
                     returned,returnedP,complete,durable,installed,visible,restarted,running,replayed,receipt>>
Crash == /\ running /\ ~restarted /\ running'=FALSE /\ restarted'=TRUE
         /\ epoch'=epoch+1 /\ installed'=<<>> /\ visible'=0 /\ accepted'=0
         /\ UNCHANGED <<source,offered,durableAccepted,frozen,selected,returned,returnedP,
              complete,durable,replayed,receipt>>
Recover == /\ ~running /\ installed'=durable /\ running'=TRUE
           /\ accepted'=IF GuardDebtRecovery THEN durableAccepted ELSE Frontier(durable)
           /\ UNCHANGED <<epoch,source,offered,durableAccepted,frozen,selected,returned,
                returnedP,complete,durable,visible,restarted,replayed,receipt>>

Replay(j) == /\ running /\ j\in CommittedJobs /\ j\notin replayed
             /\ replayed'=replayed\cup{j}
             /\ receipt'=durable[CHOOSE i\in1..Len(durable): durable[i].job=j]
             /\ UNCHANGED <<epoch,source,offered,accepted,durableAccepted,frozen,selected,
                  returned,returnedP,complete,durable,installed,visible,restarted,running>>

Next == Offer \/ Accept \/ Install \/ Publish \/ PublishUnsynced \/ ChangeSource \/ Crash \/ Recover
        \/ (\E j\in Jobs, b\in1..MaxFrontier: Freeze(j,b))
        \/ (\E j\in Jobs,z\in Values: Select(j,z) \/ CoherentTamper(j,z))
        \/ (\E j\in Jobs,p\in0..2: ProjectionTamper(j,p))
        \/ (\E j\in Jobs: Truncate(j) \/ SyncAdmission(j) \/ Replay(j))
Spec == Init /\ [][Next]_vars
FairSpec == Spec /\ WF_vars(Recover) /\ WF_vars(Install) /\ WF_vars(Publish)

TypeOK == /\ epoch\in1..2 /\ source\in1..2 /\ offered\in0..MaxFrontier
          /\ accepted\in0..offered /\ durableAccepted\in0..offered
          /\ selected\in[Jobs -> Values\cup{Nil}]
          /\ returned\in[Jobs -> Values\cup{Nil}]
          /\ returnedP\in[Jobs -> (0..2)\cup{Nil}]
          /\ complete\in[Jobs -> BOOLEAN]
          /\ Len(durable)<=Cardinality(Jobs) /\ visible\in0..Cardinality(Jobs)
AuthorizedContent == \A i\in1..Len(durable): durable[i].Z=durable[i].selectedZ
TrustedProjection == \A i\in1..Len(durable): durable[i].outputP=Phi(durable[i].inputP,durable[i].Z)
CompleteSelection == \A i\in1..Len(durable): durable[i].complete
Ancestry == \A i\in1..Len(durable):
              /\ durable[i].parent=i-1
              /\ durable[i].inputP=IF i=1 THEN 0 ELSE durable[i-1].outputP
NoGap == \A i\in1..Len(durable):
           /\ durable[i].start=IF i=1 THEN 0 ELSE durable[i-1].finish
           /\ durable[i].finish>durable[i].start
WriterFence == \A i\in1..Len(durable): durable[i].owner=durable[i].observedOwner
SourceEligibility == \A i\in1..Len(durable): durable[i].src=durable[i].observedSource
AtMostOnce == Cardinality(CommittedJobs)=Len(durable)
DurableInstalled == /\ Len(installed)<=Len(durable)
                    /\ \A i\in1..Len(installed): installed[i]=durable[i]
VisibleDurable == visible<=Len(installed)
InputDebtPreserved == running => accepted=durableAccepted
InputCoverage == Frontier(durable)<=durableAccepted
ReceiptIsHistorical == receipt=Nil \/ \E i\in1..Len(durable): receipt=durable[i]
Safety == /\ AuthorizedContent /\ TrustedProjection /\ CompleteSelection
          /\ Ancestry /\ NoGap /\ WriterFence /\ SourceEligibility /\ AtMostOnce
          /\ DurableInstalled /\ VisibleDurable /\ InputDebtPreserved /\ InputCoverage
          /\ ReceiptIsHistorical
RecoveryProgress == (~running) ~> running
DurableVisibility == \A k\in1..Cardinality(Jobs): (Len(durable)>=k) ~> (running /\ visible>=k)
=============================================================================
