# Step 01 — Schedule DSL v0.1

## Result

[`freeze_week04_schedules.py`](../../../scripts/research/freeze_week04_schedules.py#L1) 从 [Week 3 canonical trace](../week-03/results/step-04-canonical-traces.json) 生成八个 [`vc-schedule-0.1`](schedule-v0.1.schema.json) manifest，并由 [`validate_schedule`](../../../scripts/research/week4_schedule.py#L157) fail closed 校验。

DSL 固定事务操作、事务内顺序、必要跨线程 edge、观察点、超时、期望 outcome、模型/mapping hash 与 seed。[`wallClock`](schedules/shared-shared-compatible.json#L115) 和 [`nanoTime`](schedules/shared-shared-compatible.json#L116) 明确为诊断字段，跨线程顺序只来自 [`happensBefore`](schedules/shared-shared-compatible.json#L94) 显式 edge。

## Evidence Boundary

- [`step-01-schedule-dsl.json`](results/step-01-schedule-dsl.json) 固定 corpus 路径与 SHA-256。
- corpus 是模型前缀到实现重放输入的 contract，不表示 schedule 已经在 Direct 或 Native 路径成功执行。
- gate safety 由 [Step 02](README.md#steps) 决定；manifest 中 [`gateRequested`](schedules/shared-shared-compatible.json#L52) 不是安全性证明。

## Validation

```console
python -m scripts.research.freeze_week04_schedules
python -m unittest scripts.tests.test_week4_schedule -v
```
