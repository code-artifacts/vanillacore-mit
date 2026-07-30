# Step 04 — Four Deterministic Scenario Replays

## Objective

用 Direct harness 重放 `S/S`、`S/X`、`X/X` 与反序双资源，并保存可解析的 raw JSONL trace。每类场景执行 20 次，不使用 wall-clock sleep。

## Schedules

| Scenario | Constraint | Expected outcome |
| --- | --- | --- |
| `S/S` | holder grant 后发第二个 S | 两者 grant，无 wait |
| `S/X` | S grant 后发 X；观测 wait 后 release S | X 随后 grant |
| `X/X` | X grant 后发第二个 X；观测 wait 后 release | waiter 随后 grant |
| reverse two-resource | older `X(A)`、younger `X(B)`；older 先请求 B | older wait，younger 请求 A 时协作中止，释放 B 后 older grant |

反序场景验证当前 age-based 实现的可重复动态行为，不把它命名为标准 wait-die。由于本周只允许五类事件，abort 由 `Future` 的 `LockAbortException` 结果确认，trace 中不新增 `ABORT_MARK`。

## Reproduction

```powershell
.\scripts\research\Invoke-Week02ScenarioReplay.ps1 -Repetitions 20
```

机器汇总见 [`results/step-04-scenario-replay.json`](results/step-04-scenario-replay.json)。四份 raw JSONL 位于 Git 忽略的 `raw/step-04/`，汇总保存各文件 SHA-256 和五类事件计数。

## Evidence Boundary

这些是 event-conditioned replay：harness 等到 `WAIT_BEGIN` 后才释放 holder。它建立可重复组件 schedule，但不是源码 gate 驱动的 strict replay，也不满足后续 G3 的 low-mode 30 次标准。
