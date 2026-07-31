# Step 01 — Minimal Event Sink

## Objective

建立不依赖磁盘 I/O、默认关闭且不会阻塞锁线程的最小事件接收器，为后续 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 插桩提供稳定边界。

## Design

- schema 固定为 [`vc-locktrace-0`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L4)；
- producer 以递增 event ID 定位 [`AtomicReferenceArray`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/atomic/AtomicReferenceArray.html) 槽位，容量耗尽时不等待；
- 每条事件保存 run、全局事件、线程内事件、事务、源码点、资源和模式身份；
- snapshot 按全局事件号排序，并以 [`droppedEvents`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L16) 显式报告 loss；
- [`LockTrace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java#L5) 默认使用 no-op sink，且同一 JVM 只允许安装一个活动 sink。
- full sink 接收五类事件；low sink 仅接收 [`GRANT/RELEASE/TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6)。

本步骤不修改 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48)，因而不会改变锁语义。事件类型仅声明第二周允许的 [`LOCK_CALL/WAIT_BEGIN/GRANT/RELEASE/TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4)。

## Validation

```console
python -m scripts.research.invoke_week02_event_sink_validation
```

测试覆盖字段与序号、容量 loss、4 个并发 producer 的 400 个唯一事件。结果见 [`results/step-01-event-sink.json`](results/step-01-event-sink.json)。

## Limits

- 当前 sink 只提供内存 snapshot；JSONL 写出由 harness 在锁临界区外完成。
- [`droppedEvents`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L16) 是 run 级 loss 证据，尚未编码为事件流中的 [`TRACE_LOSS`](../../plan.md#L599)。
- schema v0 不包含 owner/waiter 快照，不能独立支持强 refinement verdict。

## Commit Summary

<a id="primary-commit-7d29383"></a>
### Primary Commit — [`7d29383`](#primary-commit-7d29383)

**完成任务。** 提交 [`7d29383`](#primary-commit-7d29383) 建立 Week 2 的最小事件边界，使后续 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 插桩可以依赖稳定事件对象和 sink API，同时保持生产锁表尚未接入、默认关闭。

**生产代码改动。**

- 新增 [`LockTraceEventType`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L3)，冻结当周允许的五类事件。
- 新增不可变 [`LockTraceEvent`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEvent.java#L3) 和 [`LockTraceSnapshot`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceSnapshot.java#L6)，记录 run、全局序号、线程序号、事务、来源、资源、模式和 loss 元数据。
- 通过 [`LockTraceSink`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceSink.java#L3) 定义 producer 边界；[`LockTrace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java#L5) 提供 no-op 默认值、单活动 sink 安装和 reset。
- 新增 [`BoundedLockTraceSink`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L10)。原始提交使用非阻塞 [`ArrayBlockingQueue.offer`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/ArrayBlockingQueue.html#offer(E))、原子全局序号、线程本地序号和显式丢弃计数；其存储结构后来由 [`Step 05`](step-05-trace-quality.md#primary-commit-b7db685) 调整。

**测试、自动化与证据。**

- [`BoundedLockTraceSinkTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSinkTest.java#L17) 验证 schema 与序号、容量耗尽的显式 loss，以及四个并发 producer 不产生重复事件 ID。
- 原始提交增加步骤专用验证入口并生成 [`step-01-event-sink.json`](results/step-01-event-sink.json)，记录 trace schema、sink 属性和测试统计。
- 本提交只声明事件和接收器；[`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 尚未调用 [`LockTrace.record`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java#L36)，因此不会改变锁授予、等待或释放行为。

**注意事项。** 单活动 sink 是进程级测试约束；容量耗尽只增加 loss 计数，不阻塞锁线程。该版本没有 owner/waiter snapshot，也没有磁盘 writer，不能单独作为完整 refinement 证据。

### Cross-Platform Follow-up

共享提交 [`14ade02`](README.md#shared-follow-up-14ade02) 删除原始 PowerShell 入口，以 [`invoke_week02_event_sink_validation.py`](../../../scripts/research/invoke_week02_event_sink_validation.py#L12) 暴露 CLI，并把结果生成迁入 [`invoke_event_sink_validation`](../../../scripts/research/week2.py#L50)。默认结果路径和 [`schemaVersion`](results/step-01-event-sink.json#L2) 保持兼容。
