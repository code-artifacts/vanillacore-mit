# Step 03 — Strict Replay

## Result

[`ScheduleControl.observeLock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/ScheduleControl.java#L29) 在 [`LockTable.trace`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L527) 的 low/full trace filter 前观察 source event；未安装 controller 时保持关闭。

[`StrictScheduleController.observe`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/StrictScheduleController.java#L31) 只让当前 enabled event 通过。提前到达的事件只有经 [`ScheduleGateAudit.requireBlockingSafe`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/ScheduleGateAudit.java#L45) 批准才可等待；monitor 内的 wait/grant/release 事件若不匹配则立即失败。

[`ScheduleDivergence.Kind`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/ScheduleDivergence.java#L10) 分离缺失、额外、事件/source、事务、资源、mode、超时与 harness exception。结果保存首次偏差时的 expected/actual 最短前缀。

## Evidence

- [`StrictScheduleControllerTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/schedule/StrictScheduleControllerTest.java#L22) 覆盖真实 Direct 争用序列、安全 gate 重排和必需错误类别。
- [`step-03-strict-replay.json`](results/step-03-strict-replay.json) 固定 JDK、测试计数、耗时和 taxonomy。
- 本步不声称八类 schedule 已达到 30/30；该 campaign 属于 [Step 07](README.md#steps)。

## Validation

```console
python -m scripts.research.check_week04_strict_replay
```
