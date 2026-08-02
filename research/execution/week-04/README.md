# Week 4 — Deterministic Replay and Native Transactions

本周执行 [`research/plan.md` 第四周](../../plan.md#第四周确定性重放与-native-事务路径)。实施计划、逐次 commit summary 与 push SHA 记录在 [`ai/plans/20260802-1244-第四周确定性重放执行.md`](../../../ai/plans/20260802-1244-第四周确定性重放执行.md)。

## Steps

| Step | Scope | Status | Evidence |
| --- | --- | --- | --- |
| [`01`](step-01-schedule-dsl.md) | 冻结 schedule DSL v0.1 与八类 corpus | Complete | [`step-01-schedule-dsl.json`](results/step-01-schedule-dsl.json) |
| [`02`](step-02-gate-safe-audit.md) | gate-safe 审计 | Complete | [`step-02-gate-audit.json`](results/step-02-gate-audit.json) |
| [`03`](step-03-strict-replay.md) | strict replay | Complete | [`step-03-strict-replay.json`](results/step-03-strict-replay.json) |
| [`04`](step-04-partial-order-replay.md) | partial-order replay | Complete | [`step-04-partial-order.json`](results/step-04-partial-order.json) |
| [`05`](step-05-native-harness.md) | Native transaction harness | Complete | [`step-05-native-harness.json`](results/step-05-native-harness.json) |
| [06](#steps) | Direct/Native L1 投影差分 | Pending | Pending |
| [07](#steps) | 30 次重放、扰动与 G3 决策 | Pending | Pending |

版本化 schema 位于 [`schedule-v0.1.schema.json`](schedule-v0.1.schema.json)，生成后的 manifest 位于 [`schedules/`](schedules/)。
