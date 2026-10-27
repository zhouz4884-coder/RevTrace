----------------------------- MODULE BoundedWait -----------------------------
EXTENDS Naturals
CONSTANTS Budget, Deadline, MaxClock
VARIABLES budget, clock, dispatched, canonical, debt, frozen
vars == <<budget,clock,dispatched,canonical,debt,frozen>>
Init == /\ budget=Budget /\ clock=0 /\ dispatched=FALSE
        /\ canonical=0 /\ debt=1 /\ frozen=FALSE
Wait == /\ ~dispatched /\ budget>0 /\ budget'=budget-1
        /\ UNCHANGED <<clock,dispatched,canonical,debt,frozen>>
ClockTick == /\ clock<MaxClock /\ clock'=clock+1
             /\ UNCHANGED <<budget,dispatched,canonical,debt,frozen>>
Dispatch == /\ ~dispatched /\ budget=0 /\ dispatched'=TRUE /\ frozen'=TRUE
            /\ UNCHANGED <<budget,clock,canonical,debt>>
Spec == Init /\ [][Wait \/ ClockTick \/ Dispatch]_vars
FairSpec == Spec /\ WF_vars(Wait) /\ WF_vars(Dispatch)
TypeOK == /\ budget\in0..Budget /\ clock\in0..MaxClock
NoAdmissionByWaiting == canonical=0 /\ debt=1
NoFrozenJobWhileWaiting == ~dispatched => ~frozen
EventuallyDispatch == <>dispatched
DeadlineAlwaysMet == ~dispatched => clock<=Deadline
=============================================================================
