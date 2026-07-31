# Step 04 — Four Deterministic Scenario Replays

## Objective

用 Direct harness 重放 [`S/S`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)、[`S/X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)、[`X/X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) 与反序双资源，并保存可解析的 raw JSONL trace。每类场景执行 20 次，不使用 wall-clock sleep。

## Schedules

| Scenario | Constraint | Expected outcome |
| --- | --- | --- |
| [`S/S`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) | holder grant 后发第二个 S | 两者 grant，无 wait |
| [`S/X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) | S grant 后发 X；观测 wait 后 release S | X 随后 grant |
| [`X/X`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51) | X grant 后发第二个 X；观测 wait 后 release | waiter 随后 grant |
| reverse two-resource | older [`X(A)`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)、younger [`X(B)`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)；older 先请求 B | older wait，younger 请求 A 时协作中止，释放 B 后 older grant |

反序场景验证当前 age-based 实现的可重复动态行为，不把它命名为标准 wait-die。由于本周只允许五类事件，abort 由 [`Future`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/Future.html) 的 [`LockAbortException`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockAbortException.java#L23) 结果确认，trace 中不新增 [`ABORT_MARK`](../../plan.md#L585)。

## Reproduction

```console
python -m scripts.research.invoke_week02_scenario_replay --repetitions 20
```

机器汇总见 [`results/step-04-scenario-replay.json`](results/step-04-scenario-replay.json)。四份 raw JSONL 位于 [`.gitignore` 所定义的 `raw/step-04/`](../../../.gitignore#L44)，汇总保存各文件 SHA-256 和五类事件计数。

## Evidence Boundary

这些是 event-conditioned replay：harness 等到 [`WAIT_BEGIN`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L5) 后才释放 holder。它建立可重复组件 schedule，但不是源码 gate 驱动的 strict replay，也不满足后续 G3 的 low-mode 30 次标准。

## Commit Summary

<a id="primary-commit-82ba3be"></a>
### Primary Commit — [`82ba3be`](#primary-commit-82ba3be)

**完成任务。** 提交 [`82ba3be`](#primary-commit-82ba3be) 将 Direct harness 扩展为四类确定性重放，并把每次运行的事件流写为 JSONL，同时生成可追溯的重复执行摘要。

**测试与 harness 改动。**

- [`LockTableReplayScenarioTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L22) 实现共享锁/共享锁、共享锁/独占锁、独占锁/独占锁和反序双资源四个场景，对应入口分别位于 [`#L34`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L34)、[`#L58`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L58)、[`#L84`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L84) 和 [`#L110`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L110)。
- 调度只依赖 holder [`GRANT`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6)、waiter [`WAIT_BEGIN`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L5) 等事件条件，不使用 wall-clock sleep；反序场景通过 [`assertAborted`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L142) 检查异步结果中的 [`LockAbortException`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockAbortException.java#L23)。
- [`LockTraceJsonlWriter.write`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTraceJsonlWriter.java#L18) 在锁临界区外输出 snapshot；[`toJson`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTraceJsonlWriter.java#L30) 固定逐事件 JSON schema，避免测试依赖额外序列化库。

**自动化、验证与证据。**

- 自动化以每场景 20 次的协议启动 fresh 测试运行，收集 Surefire 结果、五类事件计数、trace loss、原始文件路径和 SHA-256。
- 机器汇总 [`step-04-scenario-replay.json`](results/step-04-scenario-replay.json#L2) 记录四个场景均完成 20 次且 loss 为零；原始 JSONL 属于可再生成证据，按 [`.gitignore`](../../../.gitignore#L44) 排除而不提交。
- [`writeTrace`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableReplayScenarioTest.java#L165) 将单次场景结果交给 writer，确保测试断言与证据落盘使用同一 snapshot。

**语义影响、限制与注意事项。** 本提交不修改生产代码；它验证当前 age-based 动态行为，不将其重新命名为标准 wait-die。由于 schema 只允许五类事件，中止依据来自异步结果而非 trace 内专用 abort event。重放是 event-conditioned schedule，不是源码 gate 控制的 strict replay，也不满足 G3 的低扰动与重复次数门槛。

### Cross-Platform Follow-up

共享提交 [`14ade02`](README.md#shared-follow-up-14ade02) 以 [`invoke_week02_scenario_replay.py`](../../../scripts/research/invoke_week02_scenario_replay.py#L12) 替换原始 PowerShell 入口，并将重复执行、JSONL 汇总与哈希逻辑迁入 [`invoke_scenario_replay`](../../../scripts/research/week2.py#L129)。默认结果仍为 [`step-04-scenario-replay.json`](results/step-04-scenario-replay.json)，[`schemaVersion`](results/step-04-scenario-replay.json#L2)、默认 raw 路径和摘要字段保持兼容。
