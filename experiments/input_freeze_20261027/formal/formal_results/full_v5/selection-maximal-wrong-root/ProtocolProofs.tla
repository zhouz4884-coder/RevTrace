---------------------------- MODULE ProtocolProofs ----------------------------
EXTENDS Naturals, TLAPS
CONSTANTS InitialP, Phi(_,_), Nil, Eligible(_), Frontier(_)

PrevF(n,h) == IF n=0 THEN 0 ELSE h[n].finish
PrevP(n,h) == IF n=0 THEN InitialP ELSE h[n].outputP
EntryOK(e,i,f,p) ==
 /\ e.parent=i-1 /\ e.start=f /\ e.finish>f /\ e.inputP=p
 /\ e.Z=e.selectedZ /\ e.outputP=Phi(e.inputP,e.Z) /\ e.complete
 /\ e.owner=e.observedOwner /\ e.src=e.observedSource
HistOK(n,h) == /\ n\in Nat /\ DOMAIN h=1..n
 /\ \A i\in1..n: EntryOK(h[i],i,PrevF(i-1,h),PrevP(i-1,h))
 /\ \A i,j\in1..n: h[i].id=h[j].id => i=j
AppendH(n,h,e) == [i\in1..(n+1) |-> IF i=n+1 THEN e ELSE h[i]]
Guard(n,h,e,epoch,src) ==
 /\ e.parent=n /\ e.start=PrevF(n,h) /\ e.finish>e.start /\ e.inputP=PrevP(n,h)
 /\ e.Z=e.selectedZ /\ e.outputP=Phi(e.inputP,e.Z) /\ e.complete
 /\ e.owner=epoch /\ e.observedOwner=epoch /\ e.src=src /\ e.observedSource=src
 /\ \A i\in1..n: e.id#h[i].id

THEOREM GenesisSafe == HistOK(0,[i\in{} |-> Nil])
BY SMT DEF HistOK

THEOREM AppendFrame ==
 ASSUME NEW n\in Nat, NEW h, NEW e
 PROVE \A i\in1..n: AppendH(n,h,e)[i]=h[i]
BY SMT DEF AppendH

THEOREM GuardSuppliesNewEntry ==
 ASSUME NEW n\in Nat, NEW h, NEW e, NEW epoch, NEW src, Guard(n,h,e,epoch,src)
 PROVE EntryOK(e,n+1,PrevF(n,h),PrevP(n,h))
BY SMT DEF Guard, EntryOK

THEOREM GuardedAppendPreservesHistory ==
 ASSUME NEW n\in Nat, NEW h, NEW e, NEW epoch, NEW src,
        HistOK(n,h), Guard(n,h,e,epoch,src)
 PROVE HistOK(n+1,AppendH(n,h,e))
BY SMT DEF HistOK, Guard, EntryOK, PrevF, PrevP, AppendH

THEOREM OldWriterCannotAppend ==
 ASSUME NEW n, NEW h, NEW e, NEW oldEpoch, NEW nextEpoch, NEW src,
        e.owner=oldEpoch, oldEpoch#nextEpoch
 PROVE ~Guard(n,h,e,nextEpoch,src)
BY SMT DEF Guard

Receipt(n,h,id) == h[CHOOSE i\in1..n: h[i].id=id]
THEOREM HistoricalReceiptReturnsUniqueOriginal ==
 ASSUME NEW n\in Nat, NEW h, NEW id, NEW k\in1..n, HistOK(n,h), h[k].id=id
 PROVE Receipt(n,h,id)=h[k]
BY SMT DEF Receipt, HistOK

(* Prefix equality is the recovery frame: a validated durable history is not
   re-created under today's owner.  A current epoch is absent from HistOK. *)
THEOREM RecoveredPrefixPreservesOriginalFields ==
 ASSUME NEW n\in Nat, NEW h, NEW installed,
        HistOK(n,h), DOMAIN installed=1..n, \A i\in1..n: installed[i]=h[i]
 PROVE HistOK(n,installed)
BY SMT DEF HistOK, EntryOK, PrevF, PrevP

Best(S,b) == /\ (b=Nil <=> ~\E c\in S: Eligible(c))
             /\ (b#Nil => b\in S /\ Eligible(b) /\ \A c\in S: Eligible(c) => Frontier(c)<=Frontier(b))
Insert(b,c) == IF Eligible(c) /\ (b=Nil \/ Frontier(c)>Frontier(b)) THEN c ELSE b
THEOREM EmptyScan == Best({},Nil)
BY SMT DEF Best
THEOREM MaximumLegalScanStep ==
 ASSUME NEW S, NEW b, NEW c, Best(S,b), c#Nil,
        \A x\in S\cup{c}: Frontier(x)\in Nat
 PROVE Best(S\cup{c},Insert(b,c))
BY SMT DEF Best, Insert

WaitFrame(b,C,D,I) == [budget |-> b-1, canonical |-> C, durable |-> D, input |-> I]
THEOREM BoundedWaitPreservesTrustedStateAndDecreasesBudget ==
 ASSUME NEW b\in Nat, NEW C, NEW D, NEW I, b>0
 PROVE /\ WaitFrame(b,C,D,I).canonical=C
       /\ WaitFrame(b,C,D,I).durable=D
       /\ WaitFrame(b,C,D,I).input=I
       /\ WaitFrame(b,C,D,I).budget\in Nat
       /\ WaitFrame(b,C,D,I).budget<b
BY SMT DEF WaitFrame
=============================================================================
