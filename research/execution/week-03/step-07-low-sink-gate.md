# Step 07 — Low-Sink Optimization and Week 3 Gate

## Objective

按 [`research/plan.md` 第三周第 7 步](../../plan.md#第三周l1-模型映射与阻断债务) 在不删除五类事件语义、不静默丢事件、不缩减 Week 2 测量工作量的前提下，对 [`BoundedLockTraceSink.low`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L31) 最多执行两轮独立优化，并据完整样本决定是否允许进入 [`G3`](../../plan.md#11-闸门与停止条件)。

## Fixed Protocol

两轮均由 [`measure_low_sink_iteration`](../../../scripts/research/low_sink.py#L76) 执行相同协议：四个 Direct 场景各 20 次完整事件重放；off/low 各 3 个 fresh JVM、每 JVM 5 个样本、每样本 100,000 次 S acquire/release、20,000 次 warmup，进程顺序交替。每轮结果保存 30 个逐样本记录、事件 P/R、loss、测试汇总、源码 hash 与 Week 2 基线 hash；没有用缩短 workload 换取开销数字。

历史 [`Week 2 基线`](../week-02/results/step-05-trace-quality.json#L95) 为 57.966%。本步骤的 fresh JVM 微基准没有 CPU pinning、频率锁定或置信区间，因此跨时段百分比只作风险门控，不解释为稳定的生产性能估计。

## Optimization Iterations

| Iteration | Independent change | Off median | Low median | Low overhead | Full P/R and loss | Decision |
| --- | --- | ---: | ---: | ---: | --- | --- |
| [`01`](results/step-07-low-sink-iteration-01.json#L5) | 前置事件类型过滤 | 93,798,100 ns | 210,466,600 ns | [`124.383%`](results/step-07-low-sink-iteration-01.json#L452) | 1.0 / 1.0 / 0 | [`OPTIMIZE_AGAIN`](results/step-07-low-sink-iteration-01.json#L458) |
| [`02`](results/step-07-low-sink-iteration-02.json#L5) | low 事件延迟物化 | 110,369,700 ns | 166,393,800 ns | [`50.760%`](results/step-07-low-sink-iteration-02.json#L452) | 1.0 / 1.0 / 0 | [`BLOCK_G3`](results/step-07-low-sink-iteration-02.json#L458) |

第一轮由 [`LockTraceSink.accepts`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceSink.java#L4)、[`LockTrace.accepts`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTrace.java#L28) 与 [`LockTable.trace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L526) 在构造资源字段前拒绝 low 不保留的 LOCK_CALL/WAIT_BEGIN；sink 内仍二次校验，直接调用不会绕过过滤。

第二轮把 low 热路径改为 [`DeferredEventBuffer`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L118)：生产者写入预分配字段数组，以原子 event-type marker 最后发布；[`snapshot`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L88) 才物化完整事件。每线程 [`ThreadState`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L109) 同时避免逐事件 Long 装箱并缓存 thread id。full 模式仍即时构造完整事件；low 仍只保留 GRANT/RELEASE/TX_END，event id、thread sequence、时间戳、字段和显式 loss 计数均保留。

[`BoundedLockTraceSinkTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSinkTest.java#L61) 验证 off/low 接受集合，并在延迟物化后逐字段验证事件。两轮 [`microPrecision=1.0`](results/step-07-week-03-gate.json#L48)、microRecall=1.0、traceLoss=0，说明 full 事件质量未低于 G2。

## Week 3 Decision

最终 [`Week 3 gate`](results/step-07-week-03-gate.json#L7) 为 **BLOCKED_FOR_G3**：L1、G1、G2 均 PASS，但第二轮 low overhead 50.760% 仍超过 25% 硬上限。两轮预算已经耗尽，不再追加第三轮或选择性重测。允许继续离线 L1 refinement、无 scheduler 性能主张的 trace validation，以及另行批准后的 low-sink profiling；禁止给出 G3、scheduler 性能或可重放性结论。

## Reproduction

```console
python -m scripts.research.measure_week03_low_sink --iteration 1 --implementation early-event-type-gating
python -m scripts.research.measure_week03_low_sink --iteration 2 --implementation deferred-low-event-materialization
python -m scripts.research.new_week03_gate_decision
python -m unittest scripts.tests.test_low_sink scripts.tests.test_week3_gate -v
```

## Evidence Boundary

逐样本结果显示第二轮降低 low 的中位耗时，但 off 中位数也在两轮间明显变化；不得把 50.760% 写成可泛化的生产开销。延迟物化把部分成本移到 snapshot，当前 benchmark 只验证 record 热路径和最终计数；后续若重新批准优化，必须单独测量 snapshot 延迟、峰值内存、多线程发布和长运行 loss，不得用本步骤结果替代这些证据。

## Commit Summary

### 完成任务

- 按第三周停止条件完成且仅完成两轮 low sink 独立优化，保留首轮超线与第二轮超线的全部 30+30 个性能样本和事件质量结果。
- 汇总 L1、G1、G2 与 low overhead 为机器可读 Week 3 gate；严格输出 BLOCKED_FOR_G3，不因 L1/G1/G2 通过而越过性能硬门槛。

### 生产代码改动

- [`LockTraceSink`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceSink.java#L4) 增加可兼容既有 sink 的默认接受查询；off sink 拒绝全部事件，bounded full/low sink 报告各自接受集合。
- [`LockTable.trace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L526) 在资源字符串和锁模式构造前做前置过滤，五类 full 事件的调用点及语义不变。
- [`BoundedLockTraceSink`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSink.java#L10) 为 low 模式引入延迟字段缓冲、原子发布与 snapshot 物化，并以可变线程状态替代逐事件装箱；容量上限、全局 event id 和显式 droppedEvents 语义不变。

### 测试、自动化与证据

- [`BoundedLockTraceSinkTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/trace/BoundedLockTraceSinkTest.java#L61) 增加接受集合与延迟事件全字段断言；既有并发唯一 id、容量 loss 和 full 顺序测试继续覆盖。
- [`low_sink.py`](../../../scripts/research/low_sink.py#L76) 固定 Week 2 完整协议、保留逐样本数据、计算两轮停止决策并固定源码 hash；[`test_low_sink.py`](../../../scripts/tests/test_low_sink.py#L9) 覆盖 10%/25% 边界和第二轮阻断。
- [`week3_gate.py`](../../../scripts/research/week3_gate.py#L39) fail-closed 汇总七步证据；[`test_week3_gate.py`](../../../scripts/tests/test_week3_gate.py#L8) 覆盖 ready、性能阻断和基础门控失败优先级。
- 两轮证据分别保存在 [`iteration-01`](results/step-07-low-sink-iteration-01.json#L116) 与 [`iteration-02`](results/step-07-low-sink-iteration-02.json#L116)，最终判定保存在 [`step-07-week-03-gate.json`](results/step-07-week-03-gate.json#L7)。

### 语义影响、限制与注意事项

- full 五类事件语义和 trace schema 不变；low 仍明确只保留三类 lifecycle state change，未静默丢事件，且两轮 full P/R=1.0、loss=0。
- low snapshot 的对象分配从 record 路径后移，不能把热路径改善等同端到端成本降低；内存、snapshot 和并发长期运行仍是开放风险。
- 第二轮 50.760% 超过 25% 硬上限，因此本提交明确阻断 G3。任何后续第三轮优化都必须先更新研究计划和预算，不能覆盖本步骤失败证据。
