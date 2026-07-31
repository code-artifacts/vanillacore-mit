# Step 06 — G0–G2 Decision

## Decision

**CONDITIONAL GO**：允许进入 L1 TLA+、schema/mapping 精化和 Direct harness 正确性实验；禁止进入 G3 replay/低开销主张、广泛 mutation 或生产性能主张。

机器生成的门控结果见 [`results/step-06-g0-g2-decision.json`](results/step-06-g0-g2-decision.json)，生成命令：

```console
python -m scripts.research.new_week02_gate_decision
```

## Gate Assessment

| Gate | Decision | Evidence | Qualification |
| --- | --- | --- | --- |
| G0 Build | **PASS** | Week 1 双基线 110/110；20+20 fresh processes；当前 110 项 suite 与 12 项 MIT 功能测试通过 | 仅固定 Temurin 17 环境 |
| G1 Baseline | **CONDITIONAL PASS** | PR #95 两见证差分通过；off 模式 1,500,000 请求、15 样本零残留 | 压力仅单线程 S；main 仍是 instrumented pristine；并发 worker 矩阵未做 |
| G2 Trace | **PASS, SCOPE LIMITED** | 四场景×20；五类事件 P/R=[`1.0`](results/step-06-g0-g2-decision.json#L47)；0 loss | 只验证 Direct 事件类型/数量与关键顺序；角色、快照和 abort event 未覆盖 |

## Blocking Result

最终 low 仅记录 [`GRANT/RELEASE/TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L6)，但微基准 overhead 仍为 [`57.966%`](#blocking-result)，超过 [`25%`](#blocking-result) 硬上限。该项属于 G3 前置风险，不反向篡改 G0–G2 的证据，但明确阻断低扰动 replay 主张。

## Mandatory Next Actions

1. 将 PR #95 作为独立 reference-fix patch set 激活，不与插桩 commit 混合；
2. 完成 2/4/8/16 worker、冲突混合、累计百万操作压力矩阵；
3. 降低热路径分配/记录成本，并用 [`Step 5`](step-05-trace-quality.md#overhead-method) 原协议复测到 [`≤25%`](#mandatory-next-actions)；
4. 在强 refinement verdict 前增加明确 abort/loss 语义及 owner/waiter ground truth。

## Confidence & Gaps

对 G0 为高置信；对 G1/G2 的限定范围为中高置信。最大缺口不是四个 litmus 的可重放性，而是并发压力外推、reference-fix 主基线激活和 low-mode 性能。

## Commit Summary

<a id="primary-commit-d382d20"></a>
### Primary Commit — [`d382d20`](#primary-commit-d382d20)

**完成任务。** 提交 [`d382d20`](#primary-commit-d382d20) 聚合前两周的机器结果与 Surefire 证据，对 G0–G2 作出可机器读取的阶段决策，并把准入范围、阻断项和强制后续动作同步到研究计划。

**自动化与文档改动。**

- 原始提交增加步骤专用 PowerShell 聚合器，读取 Week 1 双基线、重复运行、PR #95 witness，以及本周插桩、harness、场景和质量结果；它不启动新 Java 实验，也不修改生产或测试源码。
- 生成的 [`step-06-g0-g2-decision.json`](results/step-06-g0-g2-decision.json#L2) 固定决策 scope、门槛状态、支持证据、限定条件、风险和下一步动作，便于后续自动化直接消费。
- 本文档与 [`research/plan.md`](../../plan.md#L643) 同步记录 conditional go，避免机器结果与人工路线图产生不同结论。

**验证结果与证据。**

- G0 为 [`PASS`](results/step-06-g0-g2-decision.json#L10)：固定 JDK 17 环境下两条基线各通过 110 项测试，当前分支通过 110 项 suite 与 12 项 MIT 功能测试。
- G1 为 [`CONDITIONAL_PASS`](results/step-06-g0-g2-decision.json#L30)：PR #95 两个 witness 具备差分证据，off 模式样本无状态残留，但当前主线仍是 instrumented pristine，且缺少多 worker 压力矩阵。
- G2 为 [`PASS_SCOPE_LIMITED`](results/step-06-g0-g2-decision.json#L45)：四场景各重复 20 次，事件数量 micro precision/recall 均为 1.0 且 loss 为零；结论不覆盖 owner/waiter ground truth、abort event 或 strict replay。
- 性能风险为 [`BLOCKS_G3`](results/step-06-g0-g2-decision.json#L61)，最终 low overhead 为 [`57.966%`](results/step-06-g0-g2-decision.json#L62)；总决策因此是 [`CONDITIONAL_GO`](results/step-06-g0-g2-decision.json#L66)。

**语义影响、限制与注意事项。** 本提交只汇总既有证据，不改变 Java 行为、结果 schema 或历史实验数据。它允许推进 L1 TLA+、schema/mapping 精化与 Direct harness 正确性实验，但明确禁止 G3 replay、广泛 mutation 和生产性能主张；限定结论不能被解释为 VanillaCore 隔离机制已完成端到端验证。

### Cross-Platform Follow-up

共享提交 [`14ade02`](README.md#shared-follow-up-14ade02) 删除原始 PowerShell 聚合器，以 [`new_week02_gate_decision.py`](../../../scripts/research/new_week02_gate_decision.py#L12) 提供跨平台 CLI，并将聚合和门控实现迁入 [`new_gate_decision`](../../../scripts/research/week2.py#L374)。默认输出仍为 [`step-06-g0-g2-decision.json`](results/step-06-g0-g2-decision.json)，[`schemaVersion`](results/step-06-g0-g2-decision.json#L2)、决策字段和既有判断保持兼容。
