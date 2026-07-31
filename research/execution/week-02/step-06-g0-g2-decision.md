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
