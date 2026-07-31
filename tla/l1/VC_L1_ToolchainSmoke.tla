-------------------- MODULE VC_L1_ToolchainSmoke --------------------
EXTENDS FiniteSets, Naturals

CONSTANTS Transactions, Resources

VARIABLE seen

vars == <<seen>>

TypeOK ==
    /\ seen \subseteq (Transactions \X Resources)
    /\ Cardinality(Transactions) >= 2
    /\ Cardinality(Resources) >= 2

Init == seen = {}

Observe(tx, resource) ==
    /\ <<tx, resource>> \notin seen
    /\ seen' = seen \cup {<<tx, resource>>}

Next ==
    \/ \E tx \in Transactions, resource \in Resources : Observe(tx, resource)
    \/ /\ seen = Transactions \X Resources
       /\ UNCHANGED seen

=====================================================================
