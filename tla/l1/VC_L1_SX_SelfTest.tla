---------------------- MODULE VC_L1_SX_SelfTest ----------------------
EXTENDS VC_L1_SX

CONSTANTS FirstTx, SecondTx, TargetResource

EmptyHeld ==
    [tx \in Transactions |-> [resource \in Resources |-> NoMode]]

EmptyOwners ==
    [resource \in Resources |-> [tx \in Transactions |-> NoMode]]

ActiveTransactions == [tx \in Transactions |-> "ACTIVE"]
NoPendingResources == [tx \in Transactions |-> NoResource]
NoPendingModes == [tx \in Transactions |-> NoMode]
NoHistoricalX == [tx \in Transactions |-> {}]

FaultStutter == UNCHANGED vars

CompatibilityFaultInit ==
    /\ txState = ActiveTransactions
    /\ held = [tx \in Transactions |->
                   [resource \in Resources |->
                       IF resource = TargetResource
                       THEN IF tx = FirstTx THEN "S"
                            ELSE IF tx = SecondTx THEN "X" ELSE NoMode
                       ELSE NoMode]]
    /\ owners = [resource \in Resources |->
                     [tx \in Transactions |->
                         IF resource = TargetResource
                         THEN IF tx = FirstTx THEN "S"
                              ELSE IF tx = SecondTx THEN "X" ELSE NoMode
                         ELSE NoMode]]
    /\ pendingResource = NoPendingResources
    /\ pendingMode = NoPendingModes
    /\ requestCount = 2
    /\ xGranted = [tx \in Transactions |->
                       IF tx = SecondTx THEN {TargetResource} ELSE {}]
    /\ lastEvent = Event("GRANT", SecondTx, TargetResource, "X")

StrictnessFaultInit ==
    /\ txState = ActiveTransactions
    /\ held = EmptyHeld
    /\ owners = EmptyOwners
    /\ pendingResource = NoPendingResources
    /\ pendingMode = NoPendingModes
    /\ requestCount = 1
    /\ xGranted = [tx \in Transactions |->
                       IF tx = FirstTx THEN {TargetResource} ELSE {}]
    /\ lastEvent = Event("RELEASE_ALL", FirstTx, NoResource, NoMode)

CleanupFaultInit ==
    /\ txState = [tx \in Transactions |->
                      IF tx = FirstTx THEN "COMMITTED" ELSE "ACTIVE"]
    /\ held = [tx \in Transactions |->
                   [resource \in Resources |->
                       IF tx = FirstTx /\ resource = TargetResource
                       THEN "S" ELSE NoMode]]
    /\ owners = [resource \in Resources |->
                     [tx \in Transactions |->
                         IF tx = FirstTx /\ resource = TargetResource
                         THEN "S" ELSE NoMode]]
    /\ pendingResource = NoPendingResources
    /\ pendingMode = NoPendingModes
    /\ requestCount = 1
    /\ xGranted = NoHistoricalX
    /\ lastEvent = Event("RELEASE_ALL", FirstTx, NoResource, NoMode)

======================================================================
