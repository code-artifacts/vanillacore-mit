# Step 07 — Replay Campaign and G3 Decision

## Protocol

[`run_week04_campaign`](../../../scripts/research/week4_campaign.py#L262) 先编译一次，再为八个 schedule 的 high/low 每次 repetition 启动独立 JDK 17 JVM，共 480 次 replay。随后以 3 个 fresh process/模式、每进程 5 个样本执行 off/low benchmark。每次 replay 都记录 strict outcome、dropped event、owner/waiter/map residue 与 harness worker thread。

## Results

- [`step-07-g3-decision.json`](results/step-07-g3-decision.json#L8) 的机器决策为 **G3_FAIL**。
- 除双升级外，七类 schedule 在 high 与 low 均分别 30/30；[`double-upgrader`](results/step-07-g3-decision.json#L32) 两模式均 0/30，所以 high/low 总成功率都为 87.5%。
- 60 个失败 outcome 全部为第二个 WAIT 未出现；全部 480 次的 dropped event、owner/waiter/map residue 和 worker leak 均为零。
- 当前 low overhead 为 [`29.657%`](results/step-07-g3-decision.json#L189)，仍高于 25% hard ceiling；继承的 [`Week 3 prerequisite`](../week-03/results/step-07-week-03-gate.json) 也仍是 BLOCKED_FOR_G3。

## Double-Upgrade Divergence

冻结 schedule 要求第一个 upgrader WAIT 后，第二个 upgrader 也产生 [`WAIT_BEGIN`](schedules/double-upgrader.json#L139)。实际 [`avoidDeadlock`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L126) 在较老事务升级时遍历 S owners，并把较年轻事务加入 abort set；较年轻事务随后在 [`txnsToBeAborted.contains`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L127) 处抛出 [`LockAbortException`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockAbortException.java#L23)，因而不会到达第二个 WAIT。

这是可重复的 refinement/model-granularity 缺口：L1 模型包含双等待 lock semantics，却没有 VanillaCore 的 wound-wait abort action。它不是 high gate 独有、不是 sink loss，也不是 scheduler 在 anchor monitor 内等待造成的 instrumentation deadlock。后续只能扩展模型/映射的 abort 语义，或把该 trace 标为不具实现 refinement 资格；不能删除失败后宣称 30/30。

## Decision Boundary

G3 同时因 high 30/30、low ≥90%、overhead ≤25% 和继承 prerequisite 未满足而失败。[`blockedWeek5MethodEvidence`](results/step-07-g3-decision.json#L10435) 为 true；在重新通过 G3 前，第五周不得把 mutation detection 写成方法有效性证据。七个 Week 4 步骤均已执行，执行完成不等于 gate 通过。

## Validation

```console
python -m scripts.research.run_week04_campaign --repetitions 30
python -m unittest scripts.tests.test_week4_gate -v
```
