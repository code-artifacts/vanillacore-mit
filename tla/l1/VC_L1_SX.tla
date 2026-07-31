-------------------------- MODULE VC_L1_SX --------------------------
EXTENDS FiniteSets, Naturals, TLC

CONSTANTS Transactions, Resources, MaxRequests

NoTx == "NO_TX"
NoResource == "NO_RESOURCE"
NoMode == "NONE"

TxStates == {"ACTIVE", "WAITING", "COMMITTING", "ROLLING_BACK",
             "COMMITTED", "ABORTED"}
LockModes == {NoMode, "S", "X"}
PendingModes == {NoMode, "S", "X"}
TerminalStates == {"COMMITTED", "ABORTED"}
EventNames == {"INIT", "REQUEST_S", "REQUEST_X", "UPGRADE_REQUEST",
               "WAIT", "GRANT", "WAKE", "COMMIT", "ROLLBACK",
               "RELEASE_ALL", "DONE"}

VARIABLES txState, held, owners, pendingResource, pendingMode,
          requestCount, xGranted, lastEvent

vars == <<txState, held, owners, pendingResource, pendingMode,
          requestCount, xGranted, lastEvent>>

Event(name, tx, resource, mode) ==
    [action |-> name, tx |-> tx, resource |-> resource, mode |-> mode]

Terminal(tx) == txState[tx] \in TerminalStates

TypeOK ==
    /\ txState \in [Transactions -> TxStates]
    /\ held \in [Transactions -> [Resources -> LockModes]]
    /\ owners \in [Resources -> [Transactions -> LockModes]]
    /\ pendingResource \in [Transactions -> (Resources \cup {NoResource})]
    /\ pendingMode \in [Transactions -> PendingModes]
    /\ requestCount \in 0..MaxRequests
    /\ xGranted \in [Transactions -> SUBSET Resources]
    /\ lastEvent \in [action : EventNames,
                        tx : Transactions \cup {NoTx},
                        resource : Resources \cup {NoResource},
                        mode : LockModes]

OwnerHeldConsistency ==
    \A tx \in Transactions, resource \in Resources :
        owners[resource][tx] = held[tx][resource]

MutualExclusion ==
    \A resource \in Resources :
        \A first, second \in Transactions :
            /\ first # second
            /\ owners[resource][first] # NoMode
            /\ owners[resource][second] # NoMode
            => /\ owners[resource][first] = "S"
               /\ owners[resource][second] = "S"

PendingWellFormed ==
    \A tx \in Transactions :
        /\ (pendingResource[tx] = NoResource) = (pendingMode[tx] = NoMode)
        /\ txState[tx] = "WAITING" => pendingResource[tx] # NoResource
        /\ txState[tx] \notin {"ACTIVE", "WAITING"}
              => pendingResource[tx] = NoResource
        /\ pendingMode[tx] = "S"
              => held[tx][pendingResource[tx]] = NoMode
        /\ pendingMode[tx] = "X"
              => held[tx][pendingResource[tx]] \in {NoMode, "S"}

WaiterNotOwnerOrUpgrade ==
    \A tx \in Transactions :
        txState[tx] = "WAITING" =>
            \/ held[tx][pendingResource[tx]] = NoMode
            \/ /\ held[tx][pendingResource[tx]] = "S"
               /\ pendingMode[tx] = "X"

TerminalClean ==
    \A tx \in Transactions :
        Terminal(tx) =>
            /\ pendingResource[tx] = NoResource
            /\ \A resource \in Resources : held[tx][resource] = NoMode

StrictXRetention ==
    \A tx \in Transactions, resource \in Resources :
        /\ resource \in xGranted[tx]
        /\ ~Terminal(tx)
        => held[tx][resource] = "X"

Init ==
    /\ txState = [tx \in Transactions |-> "ACTIVE"]
    /\ held = [tx \in Transactions |->
                   [resource \in Resources |-> NoMode]]
    /\ owners = [resource \in Resources |->
                     [tx \in Transactions |-> NoMode]]
    /\ pendingResource = [tx \in Transactions |-> NoResource]
    /\ pendingMode = [tx \in Transactions |-> NoMode]
    /\ requestCount = 0
    /\ xGranted = [tx \in Transactions |-> {}]
    /\ lastEvent = Event("INIT", NoTx, NoResource, NoMode)

Compatible(tx, resource, mode) ==
    IF mode = "S"
    THEN \A other \in Transactions \ {tx} :
             owners[resource][other] \in {NoMode, "S"}
    ELSE \A other \in Transactions \ {tx} :
             owners[resource][other] = NoMode

CanRequest(tx) ==
    /\ txState[tx] = "ACTIVE"
    /\ pendingResource[tx] = NoResource
    /\ requestCount < MaxRequests

RequestS(tx, resource) ==
    /\ CanRequest(tx)
    /\ held[tx][resource] = NoMode
    /\ pendingResource' = [pendingResource EXCEPT ![tx] = resource]
    /\ pendingMode' = [pendingMode EXCEPT ![tx] = "S"]
    /\ requestCount' = requestCount + 1
    /\ lastEvent' = Event("REQUEST_S", tx, resource, "S")
    /\ UNCHANGED <<txState, held, owners, xGranted>>

RequestX(tx, resource) ==
    /\ CanRequest(tx)
    /\ held[tx][resource] = NoMode
    /\ pendingResource' = [pendingResource EXCEPT ![tx] = resource]
    /\ pendingMode' = [pendingMode EXCEPT ![tx] = "X"]
    /\ requestCount' = requestCount + 1
    /\ lastEvent' = Event("REQUEST_X", tx, resource, "X")
    /\ UNCHANGED <<txState, held, owners, xGranted>>

RequestUpgrade(tx, resource) ==
    /\ CanRequest(tx)
    /\ held[tx][resource] = "S"
    /\ pendingResource' = [pendingResource EXCEPT ![tx] = resource]
    /\ pendingMode' = [pendingMode EXCEPT ![tx] = "X"]
    /\ requestCount' = requestCount + 1
    /\ lastEvent' = Event("UPGRADE_REQUEST", tx, resource, "X")
    /\ UNCHANGED <<txState, held, owners, xGranted>>

Grant(tx) ==
    LET resource == pendingResource[tx]
        mode == pendingMode[tx]
    IN  /\ txState[tx] = "ACTIVE"
        /\ resource # NoResource
        /\ Compatible(tx, resource, mode)
        /\ held' = [held EXCEPT ![tx][resource] = mode]
        /\ owners' = [owners EXCEPT ![resource][tx] = mode]
        /\ pendingResource' = [pendingResource EXCEPT ![tx] = NoResource]
        /\ pendingMode' = [pendingMode EXCEPT ![tx] = NoMode]
        /\ xGranted' = IF mode = "X"
                        THEN [xGranted EXCEPT ![tx] = @ \cup {resource}]
                        ELSE xGranted
        /\ lastEvent' = Event("GRANT", tx, resource, mode)
        /\ UNCHANGED <<txState, requestCount>>

Wait(tx) ==
    LET resource == pendingResource[tx]
        mode == pendingMode[tx]
    IN  /\ txState[tx] = "ACTIVE"
        /\ resource # NoResource
        /\ ~Compatible(tx, resource, mode)
        /\ txState' = [txState EXCEPT ![tx] = "WAITING"]
        /\ lastEvent' = Event("WAIT", tx, resource, mode)
        /\ UNCHANGED <<held, owners, pendingResource, pendingMode,
                        requestCount, xGranted>>

Wake(tx) ==
    LET resource == pendingResource[tx]
        mode == pendingMode[tx]
    IN  /\ txState[tx] = "WAITING"
        /\ Compatible(tx, resource, mode)
        /\ txState' = [txState EXCEPT ![tx] = "ACTIVE"]
        /\ lastEvent' = Event("WAKE", tx, resource, mode)
        /\ UNCHANGED <<held, owners, pendingResource, pendingMode,
                        requestCount, xGranted>>

Commit(tx) ==
    /\ txState[tx] = "ACTIVE"
    /\ pendingResource[tx] = NoResource
    /\ txState' = [txState EXCEPT ![tx] = "COMMITTING"]
    /\ lastEvent' = Event("COMMIT", tx, NoResource, NoMode)
    /\ UNCHANGED <<held, owners, pendingResource, pendingMode,
                    requestCount, xGranted>>

Rollback(tx) ==
    /\ txState[tx] \in {"ACTIVE", "WAITING"}
    /\ txState' = [txState EXCEPT ![tx] = "ROLLING_BACK"]
    /\ pendingResource' = [pendingResource EXCEPT ![tx] = NoResource]
    /\ pendingMode' = [pendingMode EXCEPT ![tx] = NoMode]
    /\ lastEvent' = Event("ROLLBACK", tx, NoResource, NoMode)
    /\ UNCHANGED <<held, owners, requestCount, xGranted>>

ReleaseAll(tx) ==
    /\ txState[tx] \in {"COMMITTING", "ROLLING_BACK"}
    /\ txState' = [txState EXCEPT
                       ![tx] = IF @ = "COMMITTING" THEN "COMMITTED"
                               ELSE "ABORTED"]
    /\ held' = [owner \in Transactions |->
                    IF owner = tx
                    THEN [resource \in Resources |-> NoMode]
                    ELSE held[owner]]
    /\ owners' = [resource \in Resources |->
                      [owner \in Transactions |->
                          IF owner = tx THEN NoMode
                          ELSE owners[resource][owner]]]
    /\ lastEvent' = Event("RELEASE_ALL", tx, NoResource, NoMode)
    /\ UNCHANGED <<pendingResource, pendingMode, requestCount, xGranted>>

DoneStutter ==
    /\ \A tx \in Transactions : Terminal(tx)
    /\ lastEvent' = Event("DONE", NoTx, NoResource, NoMode)
    /\ UNCHANGED <<txState, held, owners, pendingResource, pendingMode,
                    requestCount, xGranted>>

Resolve(tx) == Grant(tx) \/ Wait(tx) \/ Wake(tx)
Finish(tx) == Commit(tx) \/ Rollback(tx)

Next ==
    \/ \E tx \in Transactions, resource \in Resources : RequestS(tx, resource)
    \/ \E tx \in Transactions, resource \in Resources : RequestX(tx, resource)
    \/ \E tx \in Transactions, resource \in Resources :
           RequestUpgrade(tx, resource)
    \/ \E tx \in Transactions : Resolve(tx)
    \/ \E tx \in Transactions : Finish(tx)
    \/ \E tx \in Transactions : ReleaseAll(tx)
    \/ DoneStutter

Spec == Init /\ [][Next]_vars

FairSpec ==
    /\ Spec
    /\ \A tx \in Transactions : WF_vars(Resolve(tx))
    /\ \A tx \in Transactions : WF_vars(Finish(tx))
    /\ \A tx \in Transactions : WF_vars(ReleaseAll(tx))

EventualTermination == <> (\A tx \in Transactions : Terminal(tx))

Symmetry ==
    { [value \in Transactions \cup Resources |->
          IF value \in Transactions THEN txPermutation[value]
          ELSE resourcePermutation[value]] :
        txPermutation \in Permutations(Transactions),
        resourcePermutation \in Permutations(Resources) }

=====================================================================
