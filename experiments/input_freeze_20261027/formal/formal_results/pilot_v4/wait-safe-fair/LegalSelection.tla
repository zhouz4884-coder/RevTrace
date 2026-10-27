--------------------------- MODULE LegalSelection ---------------------------
EXTENDS Naturals, Sequences, FiniteSets
CONSTANTS Mode, Scenario, Nil
VARIABLES arrived, decided, chosen, waitBudget
vars == <<arrived,decided,chosen,waitBudget>>
IDs == {"root","older","latest"}
Canonical == [sid |-> "s", epoch |-> 2, frontier |-> 2, projection |-> "P2"]

(* Older full preview descends through an actual completed boundary node. *)
Nodes == [id\in IDs |-> CASE
 id="root" -> [sid |-> "s", epoch |-> 2, generation |-> 1,
    start |-> 1, finish |-> 2, inputP |-> "P1", outputP |-> "P2", predecessor |-> Nil,
    complete |-> TRUE, registered |-> TRUE, authorized |-> TRUE, sequence |-> 1]
 [] id="older" -> [sid |-> "s", epoch |-> 2, generation |-> 1,
    start |-> 2, finish |-> 3, inputP |-> "P2", outputP |-> "P3", predecessor |-> "root",
    complete |-> TRUE, registered |-> TRUE, authorized |-> Scenario#"revoked", sequence |-> 2]
 [] OTHER -> [sid |-> IF Scenario="wrong-session" THEN "other" ELSE "s",
    epoch |-> IF Scenario="old-epoch" THEN 1 ELSE 2, generation |-> 1,
    start |-> 2, finish |-> 4,
    inputP |-> IF Scenario="wrong-root" THEN "BAD" ELSE "P2", outputP |-> "P4",
    predecessor |-> IF Scenario="broken-edge" THEN "older" ELSE "root",
    complete |-> Scenario#"incomplete", registered |-> TRUE,
    authorized |-> Scenario#"revoked", sequence |-> 3]]

IdentityOK(c) == /\ Nodes[c].sid=Canonical.sid /\ Nodes[c].epoch=Canonical.epoch
                /\ Nodes[c].registered /\ Nodes[c].authorized /\ Nodes[c].complete
BoundaryRoot(c) == /\ Nodes[c].finish=Canonical.frontier
                  /\ Nodes[c].outputP=Canonical.projection
                  /\ IdentityOK(c) /\ c\in arrived
Edge(p,c) == /\ Nodes[c].predecessor=p
             /\ Nodes[p].finish=Nodes[c].start
             /\ Nodes[p].outputP=Nodes[c].inputP
             /\ Nodes[p].generation=Nodes[c].generation
             /\ Nodes[c].finish>Nodes[c].start
Paths(c) == {q\in UNION { [1..k -> IDs] : k\in1..3 }:
              /\ q[Len(q)]=c /\ BoundaryRoot(q[1])
              /\ \A i\in1..Len(q): IdentityOK(q[i]) /\ q[i]\in arrived
              /\ \A i\in1..(Len(q)-1): Edge(q[i],q[i+1])}
Eligible(c) == /\ c\in arrived /\ IdentityOK(c)
               /\ Nodes[c].finish>Canonical.frontier /\ Paths(c) # {}
Available == {c\in IDs: Eligible(c)}
Latest == CHOOSE c\in arrived: \A d\in arrived: Nodes[d].sequence<=Nodes[c].sequence
MaxLegal == CHOOSE c\in Available: \A d\in Available: Nodes[d].finish<=Nodes[c].finish

Init == /\ arrived={} /\ decided=FALSE /\ chosen=Nil /\ waitBudget=2
Arrive(c) == /\ ~decided /\ c\notin arrived /\ arrived'=arrived\cup{c}
             /\ UNCHANGED <<decided,chosen,waitBudget>>
Tick == /\ ~decided /\ waitBudget>0 /\ waitBudget'=waitBudget-1
        /\ UNCHANGED <<arrived,decided,chosen>>
Choose == /\ ~decided /\ arrived=IDs /\ waitBudget=0 /\ decided'=TRUE
          /\ chosen'=CASE Mode="unsafe-latest" -> Latest
                       [] Mode="latest-safe" -> IF Eligible(Latest) THEN Latest ELSE Nil
                       [] OTHER -> IF Available={} THEN Nil ELSE MaxLegal
          /\ UNCHANGED <<arrived,waitBudget>>
Next == (\E c\in IDs: Arrive(c)) \/ Tick \/ Choose
Spec == Init /\ [][Next]_vars
FairSpec == Spec /\ (\A c\in IDs: WF_vars(Arrive(c))) /\ WF_vars(Tick) /\ WF_vars(Choose)
TypeOK == /\ arrived\subseteq IDs /\ chosen\in IDs\cup{Nil} /\ waitBudget\in0..2
SafeChoice == chosen=Nil \/ Eligible(chosen)
SelectionCompleteness == (decided /\ Available#{}) => chosen#Nil
MaximumLegalProgress == (decided /\ chosen#Nil) => \A c\in Available: Nodes[c].finish<=Nodes[chosen].finish
EventualDecision == <>decided
=============================================================================
