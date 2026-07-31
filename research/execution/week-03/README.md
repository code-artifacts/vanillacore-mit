# Week 3 — L1 Model, Mapping, and Blocking Debt

本周按 [`research/plan.md` 第三周](../../plan.md#第三周l1-模型映射与阻断债务) 建立可生成实现测试的 L1 闭环，并关闭 [`G1/G3 前置风险`](../week-02/step-06-g0-g2-decision.md#mandatory-next-actions)。执行计划和逐次推送记录见 [`ai/plans/20260731-2218-第三周l1闭环执行.md`](../../../ai/plans/20260731-2218-第三周l1闭环执行.md)。

## Steps

| Step | Scope | Status | Evidence |
| --- | --- | --- | --- |
| [`01`](step-01-tla-toolchain.md) | 固定 TLA+ CLI、校验下载、JDK 17 与 2×2/3×3 配置 | Complete | [`step-01-tla-toolchain.json`](results/step-01-tla-toolchain.json) |
| [`02`](step-02-l1-model.md) | L1 S/X、等待、upgrade、事务结束与 safety/liveness | Complete | [`step-02-l1-model.json`](results/step-02-l1-model.json) |
| [`03`](step-03-mapping-ledger.md) | 动作映射、资源/偏序规则与 refinement ledger v0.1 | Complete | [`step-03-mapping-ledger.json`](results/step-03-mapping-ledger.json) |
| [`04`](step-04-canonical-traces.md) | 从 TLC 状态图确定性导出八类 canonical trace 与 provenance | Complete | [`step-04-canonical-traces.json`](results/step-04-canonical-traces.json) |
| [`05`](step-05-model-self-tests.md) | 合法/负例模型自测试与 Week 2 四场景归一化回归 | Complete | [`step-05-model-self-tests.json`](results/step-05-model-self-tests.json) |
| [`06`](step-06-g1-stress.md) | 三变体百万操作压力、残留分类与 PR #95 witness 差分 | Complete | [`step-06-g1-stress.json`](results/step-06-g1-stress.json) |
| [`07`](step-07-low-sink-gate.md) | 两轮 low sink 优化、完整基准与 Week 3 门控 | Blocked for G3 | [`step-07-week-03-gate.json`](results/step-07-week-03-gate.json) |

七个步骤均已执行；[`G3`](../../plan.md#11-闸门与停止条件) 因 low overhead 超过硬上限而阻断，允许范围与禁止主张以 [`Step 07`](step-07-low-sink-gate.md#week-3-decision) 为准。
