# L1 Mapping and Refinement Ledger v0.1

## Status and Policy

The machine-readable source is [`mapping-v0.1.json`](mapping-v0.1.json). Its status is **PROVISIONAL**: all model actions and invariants have source mappings, but every invariant still has an unassigned independent reviewer. Any [`UNKNOWN`](../../research/plan.md#52-抽象函数), trace loss, unresolved upgrade, absent lifecycle outcome, or ambiguous partial order yields [`inconclusive`](../../research/plan.md#52-抽象函数), never a strong contradiction.

## Action Mapping

| Model action | Implementation evidence | Observation | Strong contradiction |
| --- | --- | --- | --- |
| [`Init`](VC_L1_SX.tla#L86) | Fresh harness/process boundary | Unobserved | No |
| [`RequestS`](VC_L1_SX.tla#L110) | [`sLock`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L177) emits [`LOCK_CALL`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4) | Observed | Yes |
| [`RequestX`](VC_L1_SX.tla#L119) | [`xLock`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L222) emits [`LOCK_CALL`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4) | Observed | Yes when not an upgrade |
| [`RequestUpgrade`](VC_L1_SX.tla#L128) | Same [`xLock`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L222) entry | Observed but ambiguous | No |
| [`Grant`](VC_L1_SX.tla#L137) | [`GRANT`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L203) after owner/index update | Observed | Yes |
| [`Wait`](VC_L1_SX.tla#L153) | [`WAIT_BEGIN`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L193) after request-set insertion | Observed | Yes |
| [`Wake`](VC_L1_SX.tla#L164) | Return from [`Object.wait`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L196) between wait and grant | Derived/ambiguous | No |
| [`Commit`](VC_L1_SX.tla#L174) | [`Transaction.commit`](../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L103) plus harness outcome | Inferred | No |
| [`Rollback`](VC_L1_SX.tla#L182) | [`Transaction.rollback`](../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L116) plus harness outcome | Inferred | No |
| [`ReleaseAll`](VC_L1_SX.tla#L190) | Actual [`RELEASE`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L475) sequence followed by [`TX_END`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L468) | Observed | Yes with complete trace |
| [`DoneStutter`](VC_L1_SX.tla#L206) | Terminal implementation silence | Unobserved stutter | No |

## Resource and Ordering Mapping

- Abstract transaction is [`transactionId`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L57).
- Abstract resource key is ([`resourceKind`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L77), [`resourceId`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L81)); role, parent and purpose remain [`UNKNOWN`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L85).
- Same-thread order uses [`threadSequence`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L53). Cross-thread order uses scheduler edges and observed release→dependent-grant causality; [`eventId`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L45) and [`nanoTime`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L105) are weak evidence only.

## Refinement Ledger

| Rule | Model statement | Primary implementation source | Confidence | Reviewer |
| --- | --- | --- | --- | --- |
| L1-INV-TYPE | [`TypeOK`](VC_L1_SX.tla#L30) | Finite model configuration | High | Unassigned |
| L1-INV-OWNER-INDEX | [`OwnerHeldConsistency`](VC_L1_SX.tla#L43) | [`lockerMap`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L102), [`lockByMap`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L103) | Medium | Unassigned |
| L1-INV-COMPAT | [`MutualExclusion`](VC_L1_SX.tla#L47) | [`sLockable`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L652), [`xLockable`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L657) | Medium | Unassigned |
| L1-INV-PENDING | [`PendingWellFormed`](VC_L1_SX.tla#L56) | [`txWaitMap`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L105), [`requestSet`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L192) | Medium | Unassigned |
| L1-INV-WAITER | [`WaiterNotOwnerOrUpgrade`](VC_L1_SX.tla#L67) | [`WAIT_BEGIN`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L193) | Low | Unassigned |
| L1-INV-CLEAN | [`TerminalClean`](VC_L1_SX.tla#L74) | [`releaseAll`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L433) cleanup | Medium | Unassigned |
| L1-INV-STRICT-X | [`StrictXRetention`](VC_L1_SX.tla#L80) | [`Transaction.commit`](../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L103), [`Transaction.rollback`](../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L116), [`releaseAll`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L433) | Medium | Unassigned |

## Unresolved Evidence

1. Owner/waiter snapshots are absent.
2. Wake has no direct event.
3. [`TX_END`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L8) does not distinguish commit from rollback.
4. Upgrade lacks held-before state.
5. Resource role, parent and purpose remain unknown.

Run the structural and source-location audit with [`check_l1_mapping.py`](../../scripts/research/check_l1_mapping.py):

```console
python -m scripts.research.check_l1_mapping
```
