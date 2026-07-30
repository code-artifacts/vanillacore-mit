# Step 05 — Event Completeness and Overhead

## Objective

量化 v0 五类事件在四个可穷举 Direct 场景中的完整性，并以 fresh JVM、交替顺序比较 instrumentation `off` 与内存 sink `low`。

## Completeness Method

每个场景重放 20 次，按预注册事件类型多重集计算 TP/FP/FN：

- 每次四场景合计预期 `LOCK_CALL=10`、`WAIT_BEGIN=3`、`GRANT=9`、`RELEASE=9`、`TX_END=8`；
- 场景测试同时验证关键跨线程顺序、模式、资源和 abort outcome；
- 任一 sink 容量 loss 会使 JUnit 失败，而不是静默排除。

该 P/R 是**五类事件类型与数量**的自验证，不是 owner/waiter 字段的完整语义 precision。

## Overhead Method

- 每个模式 3 个 fresh JVM，每个 JVM 预热后取 5 个样本；
- 每样本 100,000 次单线程 `S acquire + release`，100 个资源；
- 模式顺序交替，比较 15 个样本的 duration median；
- 每模式累计 1,500,000 个 lock request；
- 每样本检查 `lockerMap/lockByMap/txWaitMap` 均无残留。

运行：

```powershell
.\scripts\research\Measure-Week02TraceQuality.ps1
```

机器结果见 [`results/step-05-trace-quality.json`](results/step-05-trace-quality.json)。

首次使用 `ArrayBlockingQueue.offer` 的 15+15 样本测得 `99.274%` overhead，见 [`results/step-05-overhead-iteration-01.json`](results/step-05-overhead-iteration-01.json)。改为 event ID 定位的 `AtomicReferenceArray`、但仍接收五类事件后测得 `107.814%`，见 [`results/step-05-overhead-iteration-02.json`](results/step-05-overhead-iteration-02.json)。最终按计划把 low 明确定义为只接收 `GRANT/RELEASE/TX_END` 并第三次复测；三次结果均保留，禁止只展示最优数字。

## Results

- full trace 在 20×4 个场景中得到 micro precision=`1.0`、recall=`1.0`、trace loss=`0`；
- off 与最终 low 各运行 3 个 fresh JVM、15 个测量样本、1,500,000 个锁请求；
- 所有 30 个样本的三个内部 map 均为零残留；
- off median 为 `146,569,500 ns/100k`，low median 为 `231,530,000 ns/100k`；
- final low overhead=`57.966%`，未达到 `10%` 目标并越过 `25%` 硬上限。

完整性门槛在本周受控场景范围内通过，但当前 low sink 不能进入 G3 重放/性能主张。下一步只能先减少热路径分配或异步消费成本，再以相同协议复测；不得把本次超线结果解释为可接受。

## Interpretation Boundary

这是组件热循环微基准，不包含 SQL、I/O、JSON 序列化或 scheduler gate。它对插桩自身成本敏感，但不能外推数据库事务吞吐。目标 `≤10%` 与硬上限 `25%` 仍按计划原样报告，不因结果调整。
