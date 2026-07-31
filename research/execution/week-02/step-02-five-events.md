# Step 02 — Five [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) Events

## Objective

只在 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 插入 [`LOCK_CALL/WAIT_BEGIN/GRANT/RELEASE/TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4)，建立组件级最小可观测流，不混入 scheduler gate、JSON I/O、owner 快照或语义修复。

## Source Sites

| Event | Placement | Meaning |
| --- | --- | --- |
| [`LOCK_CALL`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4) | 五种 lock API 入口 | 真实请求进入组件 |
| [`WAIT_BEGIN`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L5) | request set 更新后、[`wait`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L196) 前 | 线程即将阻塞，可能重复 |
| [`GRANT`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6) | owner 与 reverse index 更新后 | 新 owner 状态已建立 |
| [`RELEASE`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L7) | owner 状态实际移除后 | no-op release 不发事件 |
| [`TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L8) | [`releaseAll`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L433) 清理三个事务索引后 | Direct harness 的组件级终止代理 |

source-site 使用 [`locktable.<mode>.<transition>`](#source-sites) 稳定 ID，不依赖行号。启用 sink 时只构造字符串身份和不可变事件，并写入 event ID 对应的原子槽位；没有磁盘 I/O。

## Validation

```console
python -m scripts.research.invoke_week02_instrumentation_validation
```

测试验证无冲突 [`S`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) 的四事件序列，以及 [`X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) holder 与 [`S`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) waiter 的 [`WAIT_BEGIN < holder RELEASE < waiter GRANT`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTraceInstrumentationTest.java#L57)。机器结果见 [`results/step-02-five-events.json`](results/step-02-five-events.json)。

## Isolation

本提交不包含 [PR #95 参考修复](../../evidence/patches/pr-95-fix-locktable.patch)，使插桩 patch 与语义 patch 保持可区分。后续决策必须把当前状态标为 instrumented pristine，而不是 [`VC-REF-95`](../week-01/results/step-02-baselines.json#L6)。

## Limits

- [`TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L8) 只代表 [`LockTable.releaseAll`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L433) 完成，不区分 commit/rollback。
- resource role、parent 和 purpose 在 v0 中保留 [`UNKNOWN`](../../plan.md#L235)。
- 重入请求不产生新的 owner 状态，因此当前不发第二个 [`GRANT`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6)。

## Commit Summary

<a id="primary-commit-df0bba6"></a>
### Primary Commit — [`df0bba6`](#primary-commit-df0bba6)

**完成任务。** 提交 [`df0bba6`](#primary-commit-df0bba6) 将已冻结的五类事件接入 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48)，覆盖 [`sLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L177)、[`xLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L222)、[`sixLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L267)、[`isLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L311) 和 [`ixLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L353)，且不混入 scheduler、JSON writer、owner snapshot 或 PR #95 语义修复。

**生产代码改动。**

- 五个锁入口发出 [`LOCK_CALL`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4)；request set 更新后、线程等待前发出 [`WAIT_BEGIN`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L5)；owner 与 reverse index 完成更新后发出 [`GRANT`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6)。
- [`releaseAndTrace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L472) 只在 [`releaseLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L479) 确认实际移除 owner 状态时发出 [`RELEASE`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L7)，避免 no-op release 形成伪事件。
- [`releaseAll`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L433) 清理三个事务索引后发出 [`TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L8)；[`trace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L526)、[`resourceKind`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L535) 和 [`resourceId`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L545) 集中生成稳定来源与资源身份。
- [`LockTraceEvent`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L3)、[`LockTrace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java#L5) 和 [`LockTraceSink`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceSink.java#L3) 同步扩展为生产插桩所需的事件字段与发送接口。

**测试、自动化与证据。**

- [`LockTableTraceInstrumentationTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTraceInstrumentationTest.java#L25) 验证无冲突生命周期的四事件序列，并验证冲突场景满足 [`WAIT_BEGIN < holder RELEASE < waiter GRANT`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTraceInstrumentationTest.java#L57)。
- [`BoundedLockTraceSinkTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSinkTest.java#L17) 随 schema 扩展继续检查事件序列与 loss；机器结果 [`step-02-five-events.json`](results/step-02-five-events.json#L15) 记录五项测试通过。
- 该提交保持 instrumented pristine：未应用本地 [`PR #95 patch`](../../evidence/patches/pr-95-fix-locktable.patch)，便于将观测改动与 reference-fix 的语义影响分别归因。

**语义影响、限制与注意事项。** 插桩不改变锁兼容与等待判定，但为判断实际释放而重构了释放 helper，因而仍属于需回归验证的侵入式源码改动。重入锁不产生第二个 owner 状态或 [`GRANT`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6)；[`TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L8) 也不能区分 commit 与 rollback。当前源码还包含后续 [`Step 05`](step-05-trace-quality.md#primary-commit-b7db685) 的 sink 优化，回顾本提交时不能把该优化倒推为原始实现。

### Cross-Platform Follow-up

共享提交 [`14ade02`](README.md#shared-follow-up-14ade02) 以 [`invoke_week02_instrumentation_validation.py`](../../../scripts/research/invoke_week02_instrumentation_validation.py#L12) 替换步骤专用 PowerShell 入口，并把验证与结果生成迁入 [`invoke_instrumentation_validation`](../../../scripts/research/week2.py#L75)。默认输出仍为 [`step-02-five-events.json`](results/step-02-five-events.json)，[`schemaVersion`](results/step-02-five-events.json#L2) 与实验结论保持兼容。
