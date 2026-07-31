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
