# TLA+ Models

本目录保存 VanillaCore model-based testing 的 TLA+ 规格、TLC/Apalache 配置和人工筛选的最小反例。研究目标和闸门见 [`../research/plan.md`](../research/plan.md)。

## Model Layers

| Layer | Scope | Primary source mapping |
| --- | --- | --- |
| [`L0`](#model-layers) | 事件、身份、生命周期与观测契约 | [`Transaction.java`](../src/main/java/org/vanilladb/core/storage/tx/Transaction.java) |
| [`L1`](../research/plan.md#l1单层-sx-strict-2pl) | 单层 [`S/X`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)、等待、strict 2PL | [`LockTable.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java) |
| [`L2`](#model-layers) | [`IS/IX/S/SIX/X`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L51)、层次与 upgrade | [`ConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/ConcurrencyMgr.java) |
| [`L3`](#model-layers) | age-based abort、timeout、rollback/recovery | [`RecoveryMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/recovery/RecoveryMgr.java) |
| [`L4_VC`](#model-layers) | VanillaCore 粗粒度 phantom 路径 | [`SerializableConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/SerializableConcurrencyMgr.java) |
| [`P_STRUCT`](#model-layers) | B-tree 结构同步；不与逻辑 2PL 混合 | [`BTreeDir.java`](../src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java) |

## Naming and Layout

- 模块：[`VC_<layer>_<scope>.tla`](#naming-and-layout)，例如 [`VC_L1_SX.tla`](#naming-and-layout)。
- TLC 配置：与模块同名 [`.cfg`](#naming-and-layout)，例如 [`VC_L1_SX.cfg`](#naming-and-layout)。
- 可复用定义放入 [`modules/`](#naming-and-layout)；模型 trace adapter 放入 [`adapters/`](#naming-and-layout)。
- 人工确认并缩减的反例放入 [`counterexamples/`](#naming-and-layout)，并链接对应 [`experiment manifest`](../research/experiments/README.md)。

TLC checkpoint、fingerprint、queue、Toolbox 状态和自动生成 trace 由 [`.gitignore`](../.gitignore) 排除，不得作为手工维护源码提交。

## Pinned Toolchain

[`toolchain.json`](toolchain.json) pins the official [TLA+ Tools v1.7.4 release](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4), the CLI jar size and SHA-256, TLC 2.19, and the required JDK boundary. Install and validate it from the repository root:

```console
python -m scripts.research.bootstrap_tla_tools
python -m scripts.research.bootstrap_tla_tools --offline
```

The cross-platform [`bootstrap_tla_tools.py`](../scripts/research/bootstrap_tla_tools.py) command stores the verified jar below the ignored [`.tools/`](../.gitignore) directory and runs [`VC_L1_ToolchainSmoke.tla`](l1/VC_L1_ToolchainSmoke.tla) with the bounded [`2×2`](l1/VC_L1_ToolchainSmoke_2x2.cfg) and [`3×3`](l1/VC_L1_ToolchainSmoke_3x3.cfg) configurations. These smoke models validate tool/config compatibility only; [`L1`](../research/plan.md#l1单层-sx-strict-2pl) protocol claims require the separate model and checks implemented in the next step.

## L1 S/X Model

[`VC_L1_SX.tla`](l1/VC_L1_SX.tla) models separate owner and transaction indexes, pending requests, wait/wake, S→X upgrade, commit/rollback stages, release-all cleanup, and X-lock history. Run all bounded checks with [`check_l1_model.py`](../scripts/research/check_l1_model.py):

```console
python -m scripts.research.check_l1_model
```

[`VC_L1_SX_2x2.cfg`](l1/VC_L1_SX_2x2.cfg) explores the complete finite protocol for two transactions and two resources with the maximum eight requests. [`VC_L1_SX_3x3.cfg`](l1/VC_L1_SX_3x3.cfg) limits three transactions and three resources to six requests and therefore provides bounded invariant evidence only. [`VC_L1_SX_2x2_liveness.cfg`](l1/VC_L1_SX_2x2_liveness.cfg) checks eventual termination separately under documented weak-fairness assumptions and without symmetry reduction.

The provisional [`L1 mapping/refinement ledger`](l1/MAPPING.md) links every model action and invariant to current Java events and source locations. Its machine source is [`mapping-v0.1.json`](l1/mapping-v0.1.json); unresolved or unknown evidence cannot produce a strong contradiction.

## Mapping Discipline

每个模型动作必须记录实现事件、资源抽象、前置条件、允许的 stutter 和不可观测字段。结构锁与逻辑锁使用不同 event kind；无法由 trace 证明的结果为 [`inconclusive`](../research/plan.md#L378)，而不是 violation。映射变更需递增 [`mapping_version`](#mapping-discipline)，并重放旧反例。

源码地图与历史证据见 [`../research/references.md`](../research/references.md) 和 [`../research/evidence/README.md`](../research/evidence/README.md)。
