# Week 3 — L1 Model, Mapping, and Blocking Debt

本周按 [`research/plan.md` 第三周](../../plan.md#第三周l1-模型映射与阻断债务) 建立可生成实现测试的 L1 闭环，并关闭 [`G1/G3 前置风险`](../week-02/step-06-g0-g2-decision.md#mandatory-next-actions)。执行计划和逐次推送记录见 [`ai/plans/20260731-2218-第三周l1闭环执行.md`](../../../ai/plans/20260731-2218-第三周l1闭环执行.md)。

## Steps

| Step | Scope | Status | Evidence |
| --- | --- | --- | --- |
| [`01`](step-01-tla-toolchain.md) | 固定 TLA+ CLI、校验下载、JDK 17 与 2×2/3×3 配置 | Complete | [`step-01-tla-toolchain.json`](results/step-01-tla-toolchain.json) |
| [`02`](step-02-l1-model.md) | L1 S/X、等待、upgrade、事务结束与 safety/liveness | Complete | [`step-02-l1-model.json`](results/step-02-l1-model.json) |
| [`03`](step-03-mapping-ledger.md) | 动作映射、资源/偏序规则与 refinement ledger v0.1 | Complete | [`step-03-mapping-ledger.json`](results/step-03-mapping-ledger.json) |
| [`04`](step-04-canonical-traces.md) | 从 TLC 状态图确定性导出八类 canonical trace 与 provenance | Complete | [`step-04-canonical-traces.json`](results/step-04-canonical-traces.json) |

后续步骤在各自实现、验证并独立推送时加入本索引，避免未完成制品被文档提前声明为存在。
