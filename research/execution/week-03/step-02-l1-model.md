# Step 02 — L1 S/X Model

## Objective

实现 [`research/plan.md` 定义的 L1](../../plan.md#l1单层-sx-strict-2pl)，把 S/X 请求、等待、授予、唤醒、upgrade、commit、rollback 和 release-all 编码为可由 TLC 穷举的有限状态机，并把 safety 与 fairness/liveness 分开检查。

## State and Actions

[`VC_L1_SX.tla`](../../../tla/l1/VC_L1_SX.tla) 显式保存事务状态、按事务持锁、按资源 owner、pending resource/mode、请求计数、历史 X grant 和最后动作。owner 与 held 不互相派生，使 [`OwnerHeldConsistency`](../../../tla/l1/VC_L1_SX.tla) 能发现双索引更新遗漏，而不是成为定义上的恒真式。

动作边界：

- S/X 请求和 S→X upgrade 先建立 pending；
- compatible pending 通过 grant 更新 owner/held；不兼容 pending 进入 wait，释放后先 wake 再 grant；
- commit/rollback 先进入中间状态，只有 release-all 同时清理 owner/held 并进入 terminal；
- 历史 X grant 不清除，用于检查 terminal 前不得提前释放 X。

## Checks

- [`2×2 safety`](../../../tla/l1/VC_L1_SX_2x2.cfg)：每个事务/资源最多经历 S 后 upgrade，共八次请求，完整探索该有限协议；
- [`3×3 safety`](../../../tla/l1/VC_L1_SX_3x3.cfg)：限制总请求为六，只作关键 invariant 的有界放大检查；
- [`2×2 liveness`](../../../tla/l1/VC_L1_SX_2x2_liveness.cfg)：不使用 symmetry，在 resolve、finish 和 release-all 的 weak fairness 下检查 eventual termination。

机器结果见 [`step-02-l1-model.json`](results/step-02-l1-model.json)。运行：

```console
python -m scripts.research.check_l1_model
```

## Results

- [`2×2 safety`](results/step-02-l1-model.json#L35)：8,776 generated states、3,386 distinct states、深度 22，完整覆盖八请求上界；
- [`3×3 safety`](results/step-02-l1-model.json#L54)：1,051,052 generated states、233,711 distinct states、深度 20，只覆盖六请求边界；
- [`2×2 liveness`](results/step-02-l1-model.json#L73)：33,635 generated states、12,637 distinct states、深度 22，在三项 weak-fairness 假设下通过 eventual termination；
- 第二次独立 TLC 执行得到完全相同的 generated/distinct/depth，模型和配置 hash 保持不变。

## Evidence Boundary

该模型故意不包含 age-based abort、物理 timeout、IS/IX/SIX、层次资源、SQL、recovery 或索引结构。2×2 是所定义有限协议的完整探索；3×3 只有六请求边界。两者均不是 VanillaCore 或任意规模 strict-2PL 的无界证明。

## Commit Summary

### 完成任务

- 实现可执行 L1 S/X 状态机，覆盖 pending request、wait/wake、grant、S→X upgrade、commit/rollback 中间态和 release-all cleanup。
- 将 safety/deadlock 与 fairness/liveness 分离，并对 2×2 完整有限协议和 3×3 六请求边界生成机器可读证据。

### 模型与配置改动

- [`VC_L1_SX.tla`](../../../tla/l1/VC_L1_SX.tla#L1) 独立保存 owner map 与 transaction-held map；[`OwnerHeldConsistency`](../../../tla/l1/VC_L1_SX.tla#L43) 因此能发现任一侧漏更新。
- [`RequestS`](../../../tla/l1/VC_L1_SX.tla#L110)、[`RequestX`](../../../tla/l1/VC_L1_SX.tla#L119)、[`RequestUpgrade`](../../../tla/l1/VC_L1_SX.tla#L128)、[`Grant`](../../../tla/l1/VC_L1_SX.tla#L137)、[`Wait`](../../../tla/l1/VC_L1_SX.tla#L153) 与 [`Wake`](../../../tla/l1/VC_L1_SX.tla#L164) 把请求建立、兼容判断、阻塞和授予分为可观察动作。
- [`Commit`](../../../tla/l1/VC_L1_SX.tla#L174) 与 [`Rollback`](../../../tla/l1/VC_L1_SX.tla#L182) 只进入中间态；[`ReleaseAll`](../../../tla/l1/VC_L1_SX.tla#L190) 同时清理 owner/held 并进入 terminal。
- [`StrictXRetention`](../../../tla/l1/VC_L1_SX.tla#L80) 通过持久历史集合检查 X 在 terminal 前不被释放；[`MutualExclusion`](../../../tla/l1/VC_L1_SX.tla#L47)、[`PendingWellFormed`](../../../tla/l1/VC_L1_SX.tla#L56)、[`WaiterNotOwnerOrUpgrade`](../../../tla/l1/VC_L1_SX.tla#L67) 与 [`TerminalClean`](../../../tla/l1/VC_L1_SX.tla#L74) 覆盖其余 L1 安全边界。
- 2×2/3×3 safety 配置启用 [`Symmetry`](../../../tla/l1/VC_L1_SX.tla#L235)；liveness 配置独立使用 [`FairSpec`](../../../tla/l1/VC_L1_SX.tla#L227)，避免 symmetry 与 liveness 结论混淆。

### 自动化、测试与证据

- [`check_l1_model.py`](../../../scripts/research/check_l1_model.py) 调用项目固定 TLC；[`tla.py`](../../../scripts/research/tla.py) 保存模型/config hash、状态数、深度、耗时和 JVM memory boundary。
- [`toolchain.json`](../../../tla/toolchain.json) 新增三份 L1 配置 manifest；[`test_tla.py`](../../../scripts/tests/test_tla.py) 验证配置身份、完整/有界标记、状态解析与 memory 解析。
- TLC 全部三份配置 exit code 为 0；重复执行状态计数一致。完整 Python 测试 20 项、38 份文档引用、Python 编译和 Git whitespace 检查通过。

### 语义影响、限制与注意事项

- 本提交不修改 VanillaCore Java 或 Week 2 事件语义；它新增规范与研究自动化。
- 2×2 的“完整”仅指该模块定义的最多八次请求且每个事务/资源最多 S 后 upgrade；3×3 明确只检查六请求前缀。
- liveness 结论依赖 resolve、finish 与 release-all weak fairness；它不声称 JVM monitor、timeout 或 age-based abort 具有相同进展保证。
