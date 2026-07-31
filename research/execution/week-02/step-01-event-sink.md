# Step 01 — Minimal Event Sink

## Objective

建立不依赖磁盘 I/O、默认关闭且不会阻塞锁线程的最小事件接收器，为后续 `LockTable` 插桩提供稳定边界。

## Design

- schema 固定为 `vc-locktrace-0`；
- producer 以递增 event ID 定位 `AtomicReferenceArray` 槽位，容量耗尽时不等待；
- 每条事件保存 run、全局事件、线程内事件、事务、源码点、资源和模式身份；
- snapshot 按全局事件号排序，并以 `droppedEvents` 显式报告 loss；
- `LockTrace` 默认使用 no-op sink，且同一 JVM 只允许安装一个活动 sink。
- full sink 接收五类事件；low sink 仅接收 `GRANT/RELEASE/TX_END`。

本步骤不修改 `LockTable`，因而不会改变锁语义。事件类型仅声明第二周允许的 `LOCK_CALL/WAIT_BEGIN/GRANT/RELEASE/TX_END`。

## Validation

```console
python -m scripts.research.invoke_week02_event_sink_validation
```

测试覆盖字段与序号、容量 loss、4 个并发 producer 的 400 个唯一事件。结果见 [`results/step-01-event-sink.json`](results/step-01-event-sink.json)。

## Limits

- 当前 sink 只提供内存 snapshot；JSONL 写出由 harness 在锁临界区外完成。
- `droppedEvents` 是 run 级 loss 证据，尚未编码为事件流中的 `TRACE_LOSS`。
- schema v0 不包含 owner/waiter 快照，不能独立支持强 refinement verdict。
