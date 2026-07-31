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

## Commit Summary

<a id="primary-commit-fc79bb7"></a>
### Primary Commit — [`fc79bb7`](#primary-commit-fc79bb7)

**完成任务。** 提交 [`fc79bb7`](#primary-commit-fc79bb7) 建立 package-local Direct harness，将 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48)、worker 生命周期和事件同步封装为可复用测试 API，使后续场景只表达事务、资源、锁模式与事件约束。

**测试基础设施改动。**

- [`DirectLockTableHarness`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L20) 封装同步 [`lock`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L47)、异步 [`submitLock`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L71)、单锁 [`release`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L80) 与事务级 [`end`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L85)。
- [`awaitEvent`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L91) 通过 harness 内的 awaitable sink 等待事件条件；[`record`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L160) 发布通知，[`await`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L170) 使用条件等待，避免 wall-clock sleep 和轮询。
- [`snapshot`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L103) 暴露带 loss 元数据的不可变视图；[`close`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarness.java#L108) 有限时关闭 worker，并清理未显式结束的事务和全局 sink。

**测试、自动化与证据。**

- [`DirectLockTableHarnessTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarnessTest.java#L19) 覆盖同步共享锁生命周期，以及由事件驱动的独占锁 holder / 共享锁 waiter 解阻序列。
- 冲突测试在观测到 [`WAIT_BEGIN`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectLockTableHarnessTest.java#L41) 后才释放 holder，证明 harness 能以事件而非延时协调线程。
- 机器结果 [`step-03-direct-harness.json`](results/step-03-direct-harness.json#L15) 记录两项测试及固定运行环境，作为后续场景重放的 harness 基线。

**语义影响、限制与注意事项。** 本提交只增加测试源码、文档和自动化，不修改生产 Java 行为。Direct harness 绕过 parent locking、SQL、recovery 和真实 [`Transaction`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L33) commit/rollback，因此证据只适用于组件级 contract。事件等待是观测同步而非 scheduler gate；进程级单 sink 也要求场景串行创建 harness。

### Cross-Platform Follow-up

共享提交 [`14ade02`](README.md#shared-follow-up-14ade02) 以 [`invoke_week02_direct_harness_validation.py`](../../../scripts/research/invoke_week02_direct_harness_validation.py#L12) 替换原始 PowerShell 入口，并将步骤实现迁入 [`invoke_direct_harness_validation`](../../../scripts/research/week2.py#L100)。默认输出仍为 [`step-03-direct-harness.json`](results/step-03-direct-harness.json)，[`schemaVersion`](results/step-03-direct-harness.json#L2) 和结果结构保持兼容。
