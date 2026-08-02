# Step 02 — Gate-Safe Audit

## Result

机器台账 [`gate-audit-v0.1.json`](gate-audit-v0.1.json) 覆盖 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 的 acquisition、wait、grant、release、release-all 与 terminal trace site，以及 [`Transaction.commit`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L103)、[`Transaction.rollback`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L116) 和 [`Transaction.endStatement`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L129) 的 harness boundary。

[`ScheduleGateAudit.requireBlockingSafe`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/ScheduleGateAudit.java#L45) 对未知点和 observe-only 点 fail closed。只有 acquisition call 前、terminal cleanup 后、transaction method 调用前与 harness barrier 可等待控制器。

## Safety Boundary

- [`WAIT_BEGIN`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L193)、[`GRANT`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L203) 和 [`RELEASE`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L407) 均位于 anchor monitor 内，只允许无阻塞观察。
- [Java 17 Object.wait contract](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Object.html#wait()) 要求当前线程持有 monitor，并在等待时释放；若在调用它之前等待外部 scheduler，会阻止 owner release/notify，形成插桩死锁。
- [`step-02-gate-audit.json`](results/step-02-gate-audit.json) 只证明台账完整和规则自洽，不证明 [Step 03 scheduler](README.md#steps) 已正确使用台账。

## Validation

```console
python -m scripts.research.check_week04_gate_audit
python -m unittest scripts.tests.test_gate_audit -v
python -m scripts.research.invoke_maven_jdk17 --batch-mode -Dtest=ScheduleGateAuditTest test
```
