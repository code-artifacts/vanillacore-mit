# VanillaCore Model-Based Testing

本目录承载 VanillaCore 并发控制的 model-based testing 研究资产；数据库实现本身直接使用仓库中的 [`src/`](../src/)，TLA+ 模型放在 [`tla/`](../tla/)，不复制源码快照、Maven 制品或可再生输出。

## 研究入口

- [`plan.md`](plan.md)：理论问题、分层模型、harness、实验设计、闸门与停止条件。
- [`validation.md`](validation.md)：当前源码基线、JDK/Maven 环境和可重复验证命令。
- [`references.md`](references.md)：本地源码地图、上游历史与工具/论文入口。
- [`evidence/README.md`](evidence/README.md)：基线变体、已知风险与保留的 PR #95 补丁。
- [`experiments/README.md`](experiments/README.md)：实验目录、命名、manifest 和生成物管理约定。
- [`execution/README.md`](execution/README.md)：按周执行记录、自动化入口和可审计结果。
- [`../tla/README.md`](../tla/README.md)：模型分层、命名和模型—源码映射规则。

## 仓库边界

- 产品代码与最小插桩位于 [`src/main/java/`](../src/main/java/)；不维护第二份 VanillaCore fork。
- Java harness、scheduler、oracle 和代码实验位于 [`src/test/java/org/vanilladb/core/mit/`](../src/test/java/org/vanilladb/core/) 下按职责分包。
- TLA+ 规格、配置和人工筛选的反例位于 [`tla/`](../tla/)；TLC/Apalache 临时状态由 [`.gitignore`](../.gitignore) 排除。
- 实验只跟踪 manifest、缩减后的反例、分析代码和人工整理报告；raw trace 与自动生成报告不进 Git。

## 当前优先级

先完成 `L0/L1`：固定 JDK 17 基线、复现 PR #95 风险、建立 `S/X + strict 2PL` 模型、Direct `LockTable` harness、确定性调度和三值 verdict。通过 [`plan.md`](plan.md) 中 G0–G2 闸门后，再扩展意向锁、deadlock/abort、恢复与 B-tree。
