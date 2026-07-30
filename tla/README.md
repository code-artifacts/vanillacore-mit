# TLA+ Models

本目录保存 VanillaCore model-based testing 的 TLA+ 规格、TLC/Apalache 配置和人工筛选的最小反例。研究目标和闸门见 [`../research/plan.md`](../research/plan.md)。

## Model Layers

| Layer | Scope | Primary source mapping |
| --- | --- | --- |
| `L0` | 事件、身份、生命周期与观测契约 | [`Transaction.java`](../src/main/java/org/vanilladb/core/storage/tx/Transaction.java) |
| `L1` | 单层 `S/X`、等待、strict 2PL | [`LockTable.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java) |
| `L2` | `IS/IX/S/SIX/X`、层次与 upgrade | [`ConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/ConcurrencyMgr.java) |
| `L3` | age-based abort、timeout、rollback/recovery | [`RecoveryMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/recovery/RecoveryMgr.java) |
| `L4_VC` | VanillaCore 粗粒度 phantom 路径 | [`SerializableConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/SerializableConcurrencyMgr.java) |
| `P_STRUCT` | B-tree 结构同步；不与逻辑 2PL 混合 | [`BTreeDir.java`](../src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java) |

## Naming and Layout

- 模块：`VC_<layer>_<scope>.tla`，例如 `VC_L1_SX.tla`。
- TLC 配置：与模块同名 `.cfg`，例如 `VC_L1_SX.cfg`。
- 可复用定义放入 `modules/`；模型 trace adapter 放入 `adapters/`。
- 人工确认并缩减的反例放入 `counterexamples/`，并链接对应 [`experiment manifest`](../research/experiments/README.md)。

TLC checkpoint、fingerprint、queue、Toolbox 状态和自动生成 trace 由 [`.gitignore`](../.gitignore) 排除，不得作为手工维护源码提交。

## Mapping Discipline

每个模型动作必须记录实现事件、资源抽象、前置条件、允许的 stutter 和不可观测字段。结构锁与逻辑锁使用不同 event kind；无法由 trace 证明的结果为 `inconclusive`，而不是 violation。映射变更需递增 `mapping_version`，并重放旧反例。

源码地图与历史证据见 [`../research/references.md`](../research/references.md) 和 [`../research/evidence/README.md`](../research/evidence/README.md)。
