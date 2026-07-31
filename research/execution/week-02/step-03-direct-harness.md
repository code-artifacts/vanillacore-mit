# Step 03 — Direct [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) Harness

## Objective

实现与 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 同 package 的组件级 harness，使场景代码只表达事务、资源、模式和事件约束，不直接管理锁表反射、线程池或轮询。

## API Boundary

[`DirectLockTableHarness`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L20) 提供：

- [`lock`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L47) 与 [`submitLock`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L71)：同步或异步请求 [`IS/IX/S/SIX/X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)；
- [`awaitEvent`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L91)：基于 sink 通知等待事务、事件类型和资源，不使用 [`Thread.sleep`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Thread.html#sleep(long))；
- [`release`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L80) 与 [`end`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L85)：显式单锁释放或组件级事务结束；
- [`snapshot`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L103)：返回有 loss 元数据的不可变事件视图；
- [`close`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L108)：有限时等待 worker 停止并清理未结束事务。

Harness A 故意绕过 parent locking、SQL、recovery 和真实 commit/rollback，因此其结论只适用于 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 局部 contract。

## Validation

```console
python -m scripts.research.invoke_week02_direct_harness_validation
```

测试覆盖同步 [`S`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) 生命周期和受事件驱动的 [`X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) holder / [`S`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) waiter。结果见 [`results/step-03-direct-harness.json`](results/step-03-direct-harness.json)。

## Limits

- JVM 内 [`LockTrace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java#L5) 是单活动 sink，场景必须串行建 harness。
- [`awaitEvent`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L91) 是观测同步，不是源码 scheduler gate。
- 当前 harness 不声称复现原生 [`Transaction`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L33) lifecycle。
