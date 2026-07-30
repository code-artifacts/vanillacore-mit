# VanillaCore 锁式并发控制模型隔离测试研究计划

> 版本：v1.0
>
> 日期：2026-07-30
>
> 研究入口：[`README.md`](README.md)
>
> 证据与基线：[`evidence/README.md`](evidence/README.md)
>
> 资料索引与本机验证：[`references.md`](references.md)、[`validation.md`](validation.md)

## 摘要

本计划把 VanillaCore 定位为本项目的**第一受控、可插桩、可变异 SUT（System Under Test）**，用于建立“TLA+ 抽象模型 → 事务与锁操作模板 → 可控并发调度 → 内部事件轨迹 → 分层 oracle → 最小反例”的完整研究闭环。它的价值不在于代表现代生产数据库的全部复杂性，而在于：

1. 提供完整而规模适中的 Java 数据库实现，而不是待补全的课程骨架；
2. 同时包含 `IS/IX/S/SIX/X`、文件/块/记录层次、事务生命周期、回滚恢复、索引并发和 phantom 路径；
3. 核心 `LockTable` 约 585 行，适合精确插桩、确定性 gate、系统 mutation 与源码级归因；
4. 存在可利用的历史缺陷、未合并修复和测试空白，可用于验证方法是否超越上游单元测试与 history-only checker；
5. 能作为 Apache Derby 和 MySQL/InnoDB 之间的模型校准起点。

但 VanillaCore 源码更新较慢，默认分支与稳定发布的工具链不同，原始基线还存在 PR #95 指出的候选并发缺陷。故本计划采用**门控可行性策略**：先用 2–4 周完成构建、稳定性、事件完整性与低扰动重放验证；只有通过量化闸门后，才进入完整模型与 mutation 实验。若失败，应快速转向 Derby，而不是为了维护教学系统重写核心。

## 1. 研究定位与决策

### 1.1 核心判断

VanillaCore 对本项目具有**高方法学价值、中等外部有效性、高工程可行性但需先修基线风险**。

| 维度 | 判断 | 依据 |
| --- | --- | --- |
| 理论适配 | 高 | 五模式多粒度锁、strict/statement release、等待与 abort 足以覆盖 L1–L3 |
| 可观察性 | 高 | Java 源码集中，可在锁表、并发管理器、事务与恢复边界发事件 |
| 可控制性 | 高 | 可在源码事件前后放置 scheduler gate，不依赖 SQL 轮询 |
| 可变异性 | 高 | 兼容、owner/waiter、upgrade、release、abort、timeout 等 fault 可局部注入 |
| 可复现性 | 中高 | Maven、Apache-2.0、0.7.0 发布物可固定；`master` 需 JDK 17 |
| 基线可信度 | 中 | 上游测试可运行，但 PR #95 和历史 patch 表明不能把原始实现当正确 oracle |
| 生产代表性 | 低至中 | 无 InnoDB 式 gap/next-key、复杂 latch/lock 分层、长历史兼容约束 |
| 论文角色 | 强校准对象 | 适合回答“方法是否工作”，不单独回答“生产系统是否普适” |

### 1.2 在总项目中的角色

```text
VanillaCore
  ├─ 建立最小且完整的模型—实现闭环
  ├─ 校准 trace schema、映射契约和三值 verdict
  ├─ 评估 schedule generation / reduction / mutation
  ├─ 发现文档、模型、观测、实现之间的差异
  └─ 输出可迁移协议
       ↓
Apache Derby（Java 完整 DBMS transfer）
       ↓
MySQL 8.4 / InnoDB（生产级 record/range lock 案例）
```

VanillaCore 上的成功只能支撑以下主张：

- 本方法能在受控完整 DBMS 中生成可行、可重放、可归因的内部锁反例；
- 带内部证据的模型 oracle 对特定 fault family 比 history-only/random/handwritten 基线更有效；
- 映射契约与三值 verdict 能区分实现 fault、模型欠拟合、观测缺失和结构锁误分类；
- 同一抽象接口具备迁移到更复杂 DBMS 的工程基础。

不能仅凭 VanillaCore 支撑：

- 方法对所有数据库或所有并发控制协议有效；
- 对 MySQL gap/next-key、MVCC、分布式 intent 或 predicate locking 有效；
- 找到了新的生产级高影响 bug；
- 模型比现有所有数据库测试方法更优。

### 1.3 Go / Conditional Go / No-Go

当前决策是 **Conditional Go**：

1. 立即执行 L0/L1 spike；
2. 原始基线、PR #95 参考修复、插桩版和 mutation 版分离；
3. 先做 Serializable + record `S/X`，再做意向锁、deadlock/abort、恢复；
4. B-tree crabbing 独立为 `P-Struct`，不和逻辑 2PL 混合；
5. 只有隐藏 mutation 与历史缺陷实验显示内部模型 oracle 有独立增益，才进入 Derby/MySQL transfer。

## 2. 研究问题、假设与可证伪条件

### 2.1 研究问题

**RQ1：抽象充分性。** 一个分层 TLA+ 锁模型能否既覆盖 VanillaCore 的关键安全/进展语义，又保持可搜索和可解释？

**RQ2：模型—实现映射。** 能否把模型中的事务、资源、模式、等待、abort、commit/rollback 与源码事件建立稳定、可审计的证据映射？

**RQ3：调度有效性。** 模型轨迹生成的 schedule 是否比随机压力和人工 litmus 更快触发独立 fault family，同时保持实现可行和可重放？

**RQ4：oracle 增益。** 内部轨迹 refinement oracle 是否能发现外部结果/history oracle 看不到的锁协议错误？

**RQ5：诊断能力。** 三值 verdict 与反例缩减能否可靠区分实现错误、模型错误、映射错误、观测缺失和插桩诱发错误？

**RQ6：外部迁移。** VanillaCore 上形成的抽象、事件模式和实验资产，有多少能不改 invariant 或仅改 mapping 地迁移到 Derby/MySQL？

### 2.2 研究假设

| 假设 | 可度量预测 | 反驳条件 |
| --- | --- | --- |
| H1 分层建模优于一次性全模型 | L1 在小时级完成探索；每升一层仍能保留旧 trace 回放 | L1 已不可搜索或层间 contract 反复破坏旧结论 |
| H2 模型调度提高 fault 检出 | 在等 CPU/运行预算下，独立 fault family 检出率或 TTF 显著优于 random/handwritten | 95% CI 覆盖零增益，或优势只来自硬编码已知 bug |
| H3 内部 oracle 有独立价值 | 检出一组 history-only 无法判定、但有完整内部证据的 fault | 所有检出都能被更简单 history checker 同等或更快发现 |
| H4 证据化三值判定减少误报 | `contradicted` 的人工复核 precision ≥ 0.95 | 大量误报来自丢事件、错误资源映射或结构锁混淆 |
| H5 schedule 可低扰动重放 | 至少 90% 反例在低插桩模式重放成功 | 反例只在 gate/高日志开销下出现 |
| H6 抽象可以 transfer | Derby 锁实验复用多数 invariant/event 字段 | 需要重写核心状态机才能表达 Derby 基本语义 |

### 2.3 首要零假设

研究必须主动尝试支持以下零假设：

- `H0-A`：VanillaCore 太小，任何模型方法都只是在匹配手工 mutation；
- `H0-B`：随机压力或少量人工 litmus 已足以发现同样错误；
- `H0-C`：内部插桩改变了调度，所谓反例是 measurement artifact；
- `H0-D`：模型与 checker 共用同一错误假设，导致“自证正确”；
- `H0-E`：换到 Derby 后需要重写 invariant，VanillaCore 资产不可迁移；
- `H0-F`：上游原始缺陷导致基线不稳定，实验结果不可解释。

## 3. 对象身份、版本与环境

### 3.1 固定版本

| ID | VanillaCore | JDK | 用途 |
| --- | --- | --- | --- |
| `VC-REL-070` | `577c66ad369098b1676ca579a4eac7e4fcecc4f8` | Temurin JDK 17.0.20 | 历史稳定基线，仅用于跨版本比较 |
| `VC-HEAD-20230430` | 本仓库上游基线 `03e1f2df49bb9664c8bdae11cf911f56b74bbc57` | JDK 17 | 当前源码基线 |
| `VC-REF-95` | 当前源码 + 审查后的 [PR #95 补丁](evidence/patches/pr-95-fix-locktable.patch) | 同基线 | 修复参考，不称官方版本 |
| `VC-INST-*` | `VC-REF-95` + instrumentation | 同基线 | 主实验 |
| `VC-MUT-*` | `VC-INST-*` + 单 mutation | 同基线 | fault 检测实验 |

当前 VanillaCore 源码直接位于本仓库 [`src/`](../src/)，不再维护重复源码归档、Maven 发布物或 PDF 副本；历史修复证据见 [`evidence/`](evidence/)，外部资料见 [`references.md`](references.md)。每个实验结果必须记录：

```text
experiment_id
git_commit
upstream_commit
patch_set_hash
model_commit
mapping_version
trace_schema_version
scheduler_version
mutation_id
jdk_vendor_and_version
maven_version
os_or_container_digest
cpu_count
timeout_config
database_directory
seed
```

### 3.2 当前构建事实

本机在当前仓库对 `VC-HEAD-20230430` 执行默认与补充测试：

```powershell
mvn --batch-mode test
mvn --batch-mode "-Dtest=ParserTest,SpResultSetTest,ConstantRangeTest,ConstantTest,BTreeIndexConcurrentTest" test
```

在当前 Temurin JDK 17.0.20 环境中，默认 suite 为 110 项全部通过；默认 Surefire 入口遗漏的五个类共 10 项测试也单独全部通过。该结果关闭一次性 JDK 17 构建门，但尚不证明重复稳定性、容器可复现性或模型一致性。JDK 25 因旧版 JNA/JAR 兼容问题不能作为当前构建 JDK。详见 [`validation.md`](validation.md)。

### 3.3 基线隔离

每次实验使用独立 JVM 和数据库目录，原因是：

- lock table/notifier/config 中存在进程级静态状态；
- 一个测试遗留的 waiter、abort mark 或 notifier 队列可能污染下一测试；
- timeout 和线程调度受 JVM warm-up、GC、CPU oversubscription 影响；
- fork 内重复测试不能替代 fresh-process 稳定性验证。

建议目录：

```text
vanillacore-mit/
├── src/main/java/...         # VanillaCore SUT；插桩保持靠近对应实现
├── src/test/java/.../mit/    # harness、scheduler、oracle 与代码实验
├── tla/                      # TLA+ 分层模型、配置与可审查 trace
└── research/
    ├── plan.md               # 本计划
    ├── validation.md         # 当前环境与基线验证
    ├── evidence/             # 历史补丁和基线说明
    └── experiments/
        ├── manifests/        # 实验身份与参数
        ├── reducers/         # 最小反例
        └── reports/          # 人工整理的结果
```

原始、归一化、中间和自动生成结果不进 Git，约定见 [`experiments/README.md`](experiments/README.md)。以上目录按阶段创建，不在可行性结论前一次性搭空框架。

## 4. VanillaCore 语义清单与研究边界

### 4.1 逻辑锁模式

模型首先采用以下兼容矩阵：

| 请求 \ 持有 | IS | IX | S | SIX | X |
| --- | ---: | ---: | ---: | ---: | ---: |
| IS | ✓ | ✓ | ✓ | ✓ | ✗ |
| IX | ✓ | ✓ | ✗ | ✗ | ✗ |
| S | ✓ | ✗ | ✓ | ✗ | ✗ |
| SIX | ✓ | ✗ | ✗ | ✗ | ✗ |
| X | ✗ | ✗ | ✗ | ✗ | ✗ |

但“矩阵正确”不等于“多粒度协议正确”。`LockTable` 接收资源与模式，不统一检查父子层次；文件/块/记录的先后与组合主要由 `ConcurrencyMgr` 子类实现。因此必须分开测试：

1. 单资源兼容和 upgrade；
2. owner/waiter 状态维护；
3. 父子意向锁调用；
4. isolation-level release；
5. B-tree 结构锁路径。

### 4.2 资源域

VanillaCore 中可进入锁表的对象至少包括：

| 具体对象 | 模型投影 | 可能角色 |
| --- | --- | --- |
| `String` 文件名 | `File(name)` | 数据文件、索引文件、目录 |
| `BlockId` | `Block(file, number)` | 数据块、B-tree directory、B-tree leaf |
| `RecordId` | `Record(block, slot)` | 数据记录 |

事件必须保留：

```text
resource_kind
resource_id
resource_role
parent_resource_id
index_name_or_file
lock_purpose = LOGICAL_DATA | PHANTOM_GUARD | STRUCTURAL_CRAB | RECOVERY | UNKNOWN
source_method
```

若 `resource_role` 无法唯一推断，只能输出 `UNKNOWN` 并降低证据等级；不得凭 `BlockId` 就把结构锁当逻辑块锁。

### 4.3 等待与唤醒

实现特征：

- 每个资源维护请求集合；
- 资源经固定 anchor 数组散列到 monitor；
- 唤醒采用 `notifyAll`，不保证 FIFO；
- 存在全局通知队列和物理 timeout；
- 多 anchor 间没有可直接假定的全局原子快照。

模型策略：

- L1 不假定公平队列；
- 进展属性采用 bounded liveness 或实验环境假设；
- raw trace 的 `event_seq` 仅表示日志写入顺序，不代表跨 anchor 的完整 happens-before；
- 对齐器使用线程 program order、monitor 临界区、gate、事务生命周期和资源依赖构造 partial order。

### 4.4 死锁与 abort 语义

当前源码行为更接近：

1. 较小事务号代表更老事务；
2. 较老请求者遇到较年轻冲突持有者时，标记后者待中止；
3. 被标记者在后续进入锁操作时协作观察标记并抛出 `LockAbortException`；
4. 若没有及时观察，以 timeout 作为兜底。

这不同于：

- 基于 wait-for graph 的 cycle detection；
- 标准 wait-die 中“老事务等待、年轻请求者自杀”的完整定义；
- 能异步强制停止 victim 的经典 wound-wait。

本计划同时维护两个规范：

- `Spec-Impl`：忠实表达固定源码实际策略；
- `Spec-Doc`：表达课程/文档声称的策略。

若两者不同，输出 `document-semantic mismatch`，而不是自动把实现或文档判为 bug。只有外部 contract、历史修复、维护者确认或隔离性/安全性反例能升级判定。

### 4.5 strictness、语句结束与恢复

- Serializable 的逻辑 S/X 预期保持到事务结束；
- Read Committed/Repeatable Read 存在 `endStatement` 释放；
- commit/rollback 中 recovery、concurrency、buffer listener 的顺序会影响“日志/undo 完成前是否释锁”；
- lock abort 可能由调用方触发 rollback，历史 PR #32 表明双 rollback 值得单独验证。

安全属性应区分：

```text
logical_lock_held_until_commit_or_rollback
recovery_undo_completed_before_conflicting_grant
commit_record_durable_before_release_if_contract_requires
statement_lock_released_at_allowed_boundary
all_tx_state_cleaned_after_terminal_state
```

### 4.6 Phantom 与 B-tree

VanillaCore 没有 MySQL 的 record/gap/next-key/insert-intention 完整语义。其 phantom 路径主要依靠较粗粒度 file/leaf-block 保护；B-tree directory crabbing 又允许结构锁早释放。

因此：

- `L4-VC` 只研究 coarse file/leaf phantom protection；
- `L4-MySQL` 另建 interval、gap、next-key 模型；
- `P-Struct` 单独研究 B-tree crabbing、split/merge、页角色和 latch/lock 进展；
- VanillaCore 的 `L4-VC` 成功不作为 MySQL `L4-MySQL` 正确性证据。

## 5. 理论研究计划

### 5.1 状态机分层

#### L0：实验与观测契约

L0 不建业务协议，先形式化实验设施：

- worker、scheduler、event sink 的生命周期；
- gate 只能在允许的源码点阻塞；
- raw event 不丢失、不重复或明确标记 loss；
- trace schema 能表达 unknown；
- fresh-process isolation；
- replay 输入与实际 schedule 的关系。

退出条件：构建稳定、最小事件流完整、无明显插桩死锁。

#### L1：单层 `S/X` + strict 2PL

状态：

```text
TxState[t] ∈ {ACTIVE, WAITING, ABORT_MARKED, ABORTING, COMMITTED, ABORTED}
Held[t][r] ⊆ {S, X}
Wait[t] ∈ Resource ∪ {None}
Pending[t] ∈ Operation ∪ {None}
```

动作：

```text
BeginTx
RequestS
RequestX
Grant
Wait
Wake
Read
Write
Commit
Rollback
ReleaseAll
```

核心 invariant：

- 不兼容 owner 不同时存在；
- 未持所需锁不能执行逻辑读写；
- terminal 事务不再获取新锁；
- strict 模式下 X 不在 commit/rollback 完成前释放；
- waiter 不是 owner，或 conversion 状态有显式表示；
- release 后 owner map、lock-by-tx map 和 wait map 一致。

退出条件：2–3 事务、1–3 资源模型可穷举，能生成 `S/S`、`S/X`、`X/X`、upgrade、commit、rollback 轨迹。

#### L2：多粒度与 upgrade

新增：

- `IS/IX/S/SIX/X`；
- `Parent(resource)`；
- 文件—块—记录层次；
- upgrade/conversion；
- isolation-level policy。

invariant：

- 子资源锁前满足所需父意向锁；
- mode conversion 不产生瞬时双 owner 冲突；
- 同一事务重复请求幂等；
- `SIX` 与 `S+IX` 的归一化规则一致；
- release 顺序不留下孤儿子锁；
- `lockByMap` 与 owner map 双向一致。

限制：只在受控 harness 明确记录父子调用时，才把 parent invariant 用于 `contradicted`；对无法证明角色的 SQL 路径输出 `inconclusive`。

#### L3：等待、age-based abort、timeout 与恢复

新增：

- waiter/request set；
- anchor/notification 抽象；
- transaction age；
- `AbortMarked`；
- timeout clock 的有界抽象；
- rollback/undo/release 顺序。

安全属性：

- victim 或 timeout 后不会遗留 owner/waiter/abort mark；
- 同一事务不会以 ACTIVE 和 terminal 双重身份出现；
- aborted 写入不会在回滚后外部可见；
- 冲突事务不能在 undo 完成前读取被回滚状态；
- notification 不凭空授予锁；
- stale wait-map 不影响后续无关资源。

进展属性在公平性假设下检查：

- 无永久 owner 时 waiter 最终 grant 或 abort；
- abort-marked 事务最终 terminal；
- terminal 事务最终释放全部逻辑锁。

#### L4-VC：粗粒度 phantom

建模：

- data-file/leaf-block guard；
- scan、insert、delete；
- statement/transaction 边界；
- 索引路径与数据路径的配对。

不建模：

- 任意谓词；
- gap interval；
- next-key；
- insert intention；
- MySQL supremum。

#### P-Struct：B-tree 结构同步

独立状态：

- directory/leaf page role；
- safe/unsafe child；
- crab acquire/release；
- split/merge；
- page version 或结构 epoch；
- logical transaction lock 与 structural guard 的关联。

目标是防止模型把合法 crabbing 误判为 strict-2PL 违反，并为后续 LeanStore/MgCrab 类研究保留接口。

### 5.2 抽象函数

定义：

```text
α : ConcreteTrace × MappingVersion → Set(AbstractExecutions)
```

返回集合而非单一执行，因为：

- 跨 monitor 事件只有偏序；
- 某些资源角色只能推断；
- polling/日志 flush 引入 interval；
- `notifyAll` 后哪个线程先重新竞争不是确定语义。

判定：

```text
confirmed:
  ∃ abstract execution consistent with model and evidence

contradicted:
  high-confidence evidence complete
  ∧ no abstract execution satisfies model

inconclusive:
  evidence incomplete/ambiguous
  ∨ mapping admits both legal and illegal executions
```

任何 `UNKNOWN`、event loss 或 unresolved role 默认不能单独触发 `contradicted`。

### 5.3 Refinement ledger

为每条模型规则维护：

| 字段 | 含义 |
| --- | --- |
| `rule_id` | 稳定编号 |
| `layer` | L1/L2/L3/L4/P-Struct |
| `statement` | TLA+ invariant/action |
| `source_type` | protocol / official doc / source / experiment / maintainer |
| `source_uri` | 一手来源 |
| `mapping_assumption` | 具体到事件字段 |
| `counterexamples` | 受影响反例 |
| `confidence` | high/medium/low |
| `changed_at` | 模型 commit |
| `reviewer` | 非原作者复核 |

模型每次精化都必须重放旧 trace。若为解释单一失败而修改规则，同时导致多个历史 trace 从 `confirmed` 变 `inconclusive`，应视为模型过拟合警报。

### 5.4 状态空间控制

- 分层启用 feature flag；
- 先 2 个事务、2 个资源，再扩大到 3×3；
- 对资源 ID、事务 ID 做 symmetry reduction；
- timeout 只抽象为有限阶段，不建连续毫秒；
- 数据值只保留验证隔离性所需的小域；
- B-tree 结构模型不与完整 SQL/恢复笛卡尔积；
- TLC 显式模型用于最小反例，Apalache 可作为符号探索对照；
- 记录搜索边界，禁止把 bounded no-counterexample 写成证明。

## 6. 技术方案

### 6.1 三层 harness

#### Harness A：Direct LockTable

与 `LockTable` 放在同一 Java package，通过受控线程直接请求资源和模式。

用途：

- 兼容矩阵；
- owner/waiter 数据结构；
- upgrade；
- notification；
- abort mark；
- timeout；
- PR #95 回归。

优点：状态小、归因直接。

限制：绕过父子调用、SQL、恢复和真实事务生命周期，只能用于组件结论。

#### Harness B：Native Transaction / ConcurrencyMgr

通过 `TransactionMgr`、`Transaction`、`SerializableConcurrencyMgr` 等原生入口操作 file/block/record。

用途：

- 主研究 harness；
- 验证层次与 isolation-level policy；
- commit/rollback/endStatement；
- recovery 与 release 顺序；
- record/index 操作。

#### Harness C：SQL / StoredProcedure

通过 VanillaCore server/VanillaBench 兼容入口执行受控事务。

用途：

- 端到端 smoke；
- 验证 model operation 到真实 query/record/index 路径；
- 观察优化器/索引选择是否改变资源映射；
- 后期与 Derby/MySQL 使用相似 workload DSL。

SQL harness 不是第一主入口，因为查询计划会扩大不确定性；必须在 A/B 稳定后接入。

### 6.2 事件模式

raw JSONL 每条事件至少包含：

```json
{
  "schema_version": "vc-locktrace-1",
  "run_id": "uuid",
  "event_id": 42,
  "thread_id": 17,
  "thread_seq": 9,
  "tx_id": 3,
  "tx_age": 3,
  "event_type": "WAIT_BEGIN",
  "source_class": "LockTable",
  "source_method": "xLock",
  "source_site": "stable-id",
  "resource_kind": "RECORD",
  "resource_id": "tbl:blk:slot",
  "resource_role": "DATA_RECORD",
  "parent_resource_id": "tbl:blk",
  "lock_purpose": "LOGICAL_DATA",
  "requested_mode": "X",
  "held_modes_before": [],
  "owners_before": [],
  "waiters_before": [],
  "evidence": "OBSERVED",
  "scheduler_step": 12,
  "nano_time": 0
}
```

建议事件：

```text
TX_BEGIN
OP_BEGIN / OP_END
LOCK_CALL
COMPAT_CHECK
ABORT_CHECK
ABORT_MARK
WAIT_ENQUEUE
WAIT_BEGIN
WAKE_RETURN
TIMEOUT
GRANT
UPGRADE_BEGIN / UPGRADE_END
RELEASE
RELEASE_ALL_BEGIN / RELEASE_ALL_END
NOTIFY_ALL
END_STATEMENT_BEGIN / END_STATEMENT_END
COMMIT_BEGIN / COMMIT_LOGGED / COMMIT_END
ROLLBACK_BEGIN / UNDO_END / ROLLBACK_END
SNAPSHOT
TRACE_LOSS
HARNESS_BARRIER
```

事件分级：

- `OBSERVED`：直接在状态变更点读取；
- `DERIVED`：由多个 observed event 计算；
- `INFERRED`：由调用语义推断；
- `UNKNOWN`：无法可靠确定。

只有 `OBSERVED` 和经过验证规则生成的 `DERIVED` 可触发强 contradiction。

### 6.3 插桩约束

1. 在 anchor 临界区内复制最小快照；
2. JSON 序列化、磁盘 I/O、压缩在临界区外完成；
3. event sink 使用有界 ring buffer，并显式发 `TRACE_LOSS`；
4. gate 不能在持有 monitor 时等待外部 scheduler，除非该点专门用于验证 monitor 内语义且经过死锁审查；
5. instrumentation patch 与语义修复 patch 分开；
6. source site 使用稳定 ID，不依赖行号；
7. high/low/off 三档模式：
   - high：状态快照 + gate；
   - low：关键生命周期与 grant/release；
   - off：只保留 harness 外部日志。

### 6.4 确定性 scheduler

支持三种模式：

**Strict replay**

- 逐个匹配预期事件；
- 只在 gate-safe 点放行；
- 用于缩减反例与修复验证。

**Partial-order replay**

- 输入事务内顺序与必要跨线程约束；
- 未约束事件由 JVM 自由竞争；
- 用于证明反例不是单一绝对序列伪影。

**Perturbation / PCT**

- 从模型关键点选择 priority-change；
- 在 wait、grant、upgrade、abort、release、undo 周围扰动；
- 用于扩大 schedule 覆盖，避免只重放模型枚举顺序。

调度 DSL 示例：

```yaml
transactions:
  t1: [begin, x(r1), barrier(a), x(r2), commit]
  t2: [begin, x(r2), barrier(b), x(r1), commit]
constraints:
  - t1.grant(r1) < t2.request(r1)
  - t2.grant(r2) < t1.request(r2)
observe:
  - abort_mark
  - rollback_end
  - release_all_end
```

### 6.5 轨迹归一化与对齐

流水线：

```text
raw JSONL
  → schema validation
  → resource canonicalization
  → event confidence tagging
  → partial-order graph
  → abstract action candidates
  → model trace alignment
  → verdict + minimal evidence slice
```

对齐不能把 wall-clock/nanotime 当跨线程真序。优先关系来自：

1. 同线程 `thread_seq`；
2. 同一 monitor 临界区观测；
3. scheduler gate；
4. grant/release 与 owner 状态；
5. transaction lifecycle；
6. harness barrier；
7. 时间戳仅作最后的弱证据。

### 6.6 Oracle 栈

| 层 | Oracle | 典型检查 |
| --- | --- | --- |
| O1 | 内部锁语义 | compatibility、owner/waiter、upgrade、hierarchy、cleanup |
| O2 | 执行历史 | conflict/serialization graph、recoverability、dirty read/write |
| O3 | 外部结果 | 最终数据、异常、事务 outcome |
| O4 | 进展性 | timeout、永久等待、abort 后不终止 |
| O5 | 差分 | 原始/修复、版本、模型层、instrumentation mode |

报告必须说明“谁发现、谁确认”：

- O1 单独发现但 O2/O3 不可见：内部协议 fault 候选；
- O2/O3 违反：行为 bug 强证据；
- 只在 O4 超时：需排除环境和 gate artifact；
- 只在 high instrumentation 出现：measurement artifact 候选；
- 修复版消失且低插桩可重放：实现 fault 置信度上升。

### 6.7 失败缩减

分层 delta debugging：

1. 删除事务；
2. 删除事务操作；
3. 合并/删除资源；
4. 缩小锁模式集合；
5. 删除调度约束；
6. 缩短 wait/timeout；
7. 降低插桩；
8. 将 SQL workload 下沉为 native 或 direct harness；
9. 输出最小源码事件切片与对应 TLA+ state transition。

缩减器的目标不是只得到最短 SQL，而是得到最小的 `(workload, partial order, model assumptions, evidence)`。

## 7. 代码实验计划

### 7.1 L0 构建与稳定性实验

**E0.1 双版本构建**

- `VC-REL-070`：当前 Temurin JDK 17.0.20；
- `VC-HEAD-20230430`：JDK 17；
- 记录依赖、warning、测试数量、运行时长；
- 容器镜像固定 digest。

**E0.2 原始测试重复性**

- `LockTableTest`、`ConcurrencyTest` 各 fresh JVM 重复 20 次；
- 默认 suite 重复至少 10 次；
- 显式补跑默认入口遗漏的 5 个类、10 项测试；
- B-tree 并发与 Phantom 测试显式单独运行；
- 记录 pass/fail、hang、P50/P95、遗留线程。

**E0.3 PR #95 静态/动态见证**

针对两个候选问题分别写最小测试：

1. 跨 anchor 并发访问 `lockerMap`；
2. 早返回或异常路径后 `txWaitMap` 清理。

执行原始与参考修复差分，禁止先把 patch 合入主基线后忘记原始行为。

**E0.4 压力稳定性**

- 2/4/8/16 worker；
- 1、10、100 个资源；
- 兼容与冲突混合；
- 至少累计 `10^6` lock operations；
- 检查异常、hang、遗留 owner/waiter、内存增长。

### 7.2 L1 组件与事务实验

**E1.1 兼容矩阵穷举**

- 每一持有模式 × 每一请求模式；
- 单 holder、多 holder；
- 同事务重复请求；
- 请求成功、等待、timeout、release 后 grant。

**E1.2 strict-2PL litmus**

1. `S/S` 并行成功；
2. `S/X` 阻塞；
3. `X/S` 阻塞；
4. `X/X` 阻塞；
5. writer commit 后 reader grant；
6. writer rollback/undo 后 reader grant 且读不到脏值；
7. 事务结束后无 owner/waiter。

**E1.3 upgrade**

- `S→X` 单 upgrader；
- 两个 S owner 同时 upgrade；
- upgrader 与新 reader 竞争；
- conversion 失败/abort 后旧锁是否正确保留或释放；
- 重复 upgrade 幂等。

### 7.3 L2 多粒度实验

**E2.1 父子锁组合**

- record S 前 file/block IS；
- record X 前 file/block IX；
- file S 与 child IX/X 冲突；
- SIX 与 child 操作；
- 释放时 parent/child 状态一致。

**E2.2 错误调用防护**

Direct harness 故意绕过 parent；Native harness 走正常路径。比较：

- `LockTable` 是否仅执行局部 contract；
- `ConcurrencyMgr` 是否完成全局层次 contract；
- checker 是否能把“组件不负责”与“调用方违反”区分开。

**E2.3 隔离级别**

- Serializable；
- Repeatable Read；
- Read Committed；
- `endStatement` 前后锁集合；
- 同一 workload 在不同 isolation 下允许行为差异。

### 7.4 L3 deadlock/abort/timeout/恢复实验

**E3.1 两事务反序资源**

```text
T1: X(A) ... X(B)
T2: X(B) ... X(A)
```

变化：

- T1 老/T2 新；
- T2 老/T1 新；
- victim 是否在后续锁点协作中止；
- victim 无后续锁调用时 timeout 行为；
- rollback 后 survivor 是否 grant。

**E3.2 三事务 cycle 与非 cycle**

- 3-cycle；
- chain；
- shared holder + writer；
- 多资源散列到相同/不同 anchor；
- 检查 abort mark 是否只影响应受影响事务。

**E3.3 timeout 边界**

- timeout 前释放；
- timeout 竞争点释放；
- timeout 后 cleanup；
- `MAX_TIME`/`EPSILON` 参数化；
- 禁止把物理毫秒精确值写入抽象规范。

**E3.4 恢复顺序**

- commit log/flush、release、外部可见；
- rollback undo、release、survivor read；
- lock abort 触发单次 rollback；
- recovery exception 路径清理；
- `VC-REL-070` 与 `VC-HEAD-20230430` 差分。

### 7.5 L4-VC phantom 与索引实验

**E4.1 table scan / insert**

- Serializable scan 持有粗粒度 guard；
- 并发 insert 是否等待或被允许；
- commit/rollback 后结果；
- heap 与 index 访问路径差分。

**E4.2 B-tree leaf 路径**

- 读叶、写叶、split；
- logical leaf guard 与 structural crab 事件分离；
- `BTreeIndexConcurrentTest` 纳入独立 suite；
- `PhantomTest` 加强线程结果、异常传播和 barrier。

**E4.3 Read Committed 叶块回归假设**

围绕 `ReadCommittedConcurrencyMgr.readLeafBlock()` 设计动态见证：

- 是否实际调用 S lock；
- release list 是否只记录不加锁；
- statement 结束后 list 是否清空；
- 2018 `a83acf5`、2019 `feb5c38` 前后差分；
- 只有动态结果确认后才登记 bug。

### 7.6 instrumentation 自验证

**E-I1 事件完整性**

- 在可穷举 direct harness 中，以源码状态快照为 ground truth；
- 计算 grant/release/wait/abort event precision/recall；
- 目标均 ≥ 0.95；
- 丢事件必须显式标记。

**E-I2 扰动**

- off/low/high 三档运行相同 workload；
- 比较吞吐、P50/P95、schedule outcome 分布；
- 目标 low overhead ≤ 10%，hard ceiling 25%；
- high 模式允许更高开销，但不得用于最终可重放性唯一证据。

**E-I3 重放**

- 每个最小反例 high 模式重放 30 次；
- 再以 low 模式重放 30 次；
- low 成功率目标 ≥ 90%，硬停止线 80%；
- 不成功时报告 outcome 分布，不选择性展示单次成功。

## 8. Mutation 研究

### 8.1 Fault taxonomy

| Family | Mutation 示例 | 预期 oracle |
| --- | --- | --- |
| Compatibility | 允许 `S/X`、错误拒绝 `IS/S`、`SIX` 矩阵错误 | O1，部分 O2 |
| Ownership | grant 不登记、重复 owner、错误 tx ID | O1 |
| Reverse index | `lockByMap` 漏记/多记 | O1、cleanup |
| Waiter | 漏 enqueue、stale `txWaitMap`、请求集未删 | O1、O4 |
| Notify | 漏 `notifyAll`、错误资源通知 | O4 |
| Upgrade | 非原子 conversion、双 upgrader、旧锁过早释放 | O1、O2 |
| Hierarchy | 漏 parent intention、错误 parent mode | O1 |
| Age | 年龄比较反转、相等处理错误 | O1、O4 |
| Abort | 漏 abort mark、标错 victim、mark 不清理 | O1、O4 |
| Timeout | 提前/永不 timeout、异常后状态遗留 | O1、O4 |
| Lifecycle | commit/rollback 前释锁、重复 rollback | O1、O2、O3 |
| Recovery | undo 未完成即 grant、异常清理错误 | O2、O3 |
| Isolation | RC/RR statement release 错误 | O1、O2 |
| Index/leaf | read leaf 漏锁、粗 phantom guard 漏加 | O1、O2/O3 |
| Structural role | 把 crab 当 logical，或反之 | mapping/oracle robustness |

### 8.2 Mutation 独立性

- 训练集：公开 operator 与少量可见 mutation，用于调试；
- 验证集：按 semantic family 隐藏；
- 历史集：PR/commit 真实修复前版本；
- second-order 集：两个 fault 组合，只作后期鲁棒性，不进入主检测率；
- 等价 mutation 由状态覆盖和人工复核剔除；
- 同一缺陷多个代码变体只算一个独立 fault family 或一个 fault instance，防止虚增样本。

### 8.3 防共同盲点

建议分工：

- A 设计模型与 invariant；
- B 设计/冻结 hidden mutations；
- C 实现 checker 与 mapping；
- D 做独立反例复核；
- 统计分析在解盲前冻结。

若人员不足，至少按时间隔离：先冻结模型与 checker hash，再生成隐藏 mutation manifest。

## 9. 完整实验设计

### 9.1 方法组

| 组 | 方法 |
| --- | --- |
| B0 | 上游原始 tests |
| B1 | random thread stress |
| B2 | handwritten litmus |
| B3 | template/systematic interleaving，无 TLA+ |
| B4 | history-only oracle |
| B5 | model-generated workload，但无内部 trace |
| M1 | model schedule + internal trace + refinement oracle |
| M2 | M1 + PCT perturbation |
| M3 | M2 + counterexample-guided model refinement |

比较必须使用相同 CPU 时间、fresh JVM 数、seed 数和 mutation 集。不能让 M1 获得已知 fault 的专用事件，而基线只能观察最终值；对无法公平提供内部事件的基线，应明确比较的是“方法整体”而非单组件。

### 9.2 Workload family

1. 单资源 compatibility；
2. 多 holder；
3. upgrade；
4. 两资源反序；
5. 三事务 cycle；
6. parent/child intention；
7. statement release；
8. commit/rollback；
9. abort + recovery；
10. timeout race；
11. leaf/index；
12. scan/insert phantom；
13. cleanup/reuse；
14. same-anchor/cross-anchor。

### 9.3 指标

**有效性**

- 独立 fault family 检出率；
- mutation score（剔除等价 mutation）；
- 历史缺陷复现数；
- history-only 不可见但 O1 可确认的 fault 数；
- false positive / false negative。

**效率**

- time-to-first-failure；
- CPU time / JVM runs / schedules；
- 每个独立 fault 的分析成本；
- reducer 时间。

**质量**

- `confirmed/inconclusive/contradicted` 比例；
- trace alignment precision/recall；
- 低插桩重放率；
- 最小反例事务数、操作数、约束数；
- schedule/transition/lock-mode/resource-role coverage。

**扰动**

- throughput/latency overhead；
- high/low/off outcome divergence；
- event loss；
- gate-induced hang。

**迁移**

- Derby 复用的 invariant、事件字段、workload、reducer 比例；
- 必须重写的规则数量；
- transfer 中新出现的 `inconclusive` 类型。

### 9.4 统计方案

- 每个随机化配置至少 20–30 个 seed；
- 成对 fault 检出用 McNemar 或成对 bootstrap；
- TTF 有 censoring 时用 Kaplan–Meier/适当生存分析；
- 报告 effect size 和 95% CI，不只报告 p-value；
- mutation family 分层报告，避免大量 compatibility mutation 淹没 recovery；
- 多版本、多 isolation、多 instrumentation mode 预先定义比较，控制探索性分析；
- 所有排除 run 记录原因，不静默删除 timeout/hang。

### 9.5 主成功标准

满足全部条件才称 VanillaCore 阶段成功：

1. 原始和参考修复基线可重复构建；
2. trace 关键事件 precision/recall ≥ 0.95；
3. low 模式开销目标 ≤ 10%、硬上限 25%；
4. 低插桩反例重放率 ≥ 90%；
5. `inconclusive` ≤ 10%，且来源可分类；
6. 至少 30 个隐藏 mutation + 5 个历史 fault witness；
7. 对至少两个非 compatibility fault family，M1/M2 相对最强基线有 ≥ 20 个百分点检出率增益或 ≥ 2× TTF 改善，CI 不跨零增益；
8. 至少一个 fault 仅由内部轨迹 oracle 提前或独立确认；
9. 输出 Derby transfer 所需的稳定 mapping contract。

## 10. 阶段与交付物

### Phase 0：L0 可行性闸门（第 1–2 周）

任务：

- 容器化当前 JDK 17，并保留 JDK 25 依赖兼容性回归；
- 双版本 build/test；
- 20 次重复关键测试；
- PR #95 两个最小见证；
- 定义 trace schema v0；
- 五类事件最小插桩；
- X/X 与反序双资源 schedule。

交付物：

- build manifest；
- baseline stability report；
- PR #95 reproduction report；
- event schema v0；
- Go/No-Go 决策。

### Phase 1：L1 闭环（第 3–6 周）

任务：

- L1 TLA+；
- Direct + Native harness；
- strict/partial-order scheduler；
- O1/O2/O3；
- 8 类 visible mutation；
- 首版 reducer。

交付物：

- 可重放最小反例；
- 基线方法对比；
- instrumentation self-test；
- refinement ledger。

### Phase 2：L2 多粒度与隔离级别（第 7–10 周）

任务：

- `IS/IX/S/SIX/X`；
- hierarchy/upgrade；
- Serializable/RR/RC；
- hidden mutation 第一批；
- trace schema v1 冻结。

交付物：

- L2 model；
- 多粒度 mapping contract；
- mutation benchmark v1；
- 三值判定审计。

### Phase 3：L3 deadlock、timeout、恢复（第 11–16 周）

任务：

- `Spec-Impl` 与 `Spec-Doc`；
- age-based abort；
- timeout；
- commit/rollback/undo/release；
- 历史 patch 回归；
- PCT perturbation。

交付物：

- 文档—实现差异报告；
- deadlock/abort fault matrix；
- 恢复交互结果；
- 主统计实验预注册稿。

### Phase 4：L4-VC 与 P-Struct（第 17–20 周，可并行/可裁剪）

任务：

- coarse phantom；
- RC leaf 高优先级假设；
- B-tree crabbing 角色分离；
- 加强现有测试；
- 不扩展到 MySQL gap 模型。

交付物：

- L4-VC 模型；
- P-Struct 最小模型；
- index/phantom regression suite；
- 哪些结论不可迁移的边界清单。

### Phase 5：冻结、隐藏 mutation 与 Derby transfer（第 21–28 周）

任务：

- 冻结模型/checker；
- 30+ hidden mutations；
- 解盲与统计；
- Derby 10.17 最小 transfer；
- 论文 artifact 预审。

交付物：

- 主实验数据；
- reproducibility package；
- Derby transfer report；
- 继续 MySQL 或停止的决策。

## 11. 闸门与停止条件

| Gate | 目标 | 通过条件 | 失败处理 |
| --- | --- | --- | --- |
| G0 Build | 双版本可运行 | 2 天内解决环境；关键测试重复通过 | 只保留 0.7.0 或转 Derby |
| G1 Baseline | 原始状态可解释 | PR #95见证明确；`10^6` 锁操作无不可解释污染 | 建修复参考基线；仍不稳则停止 |
| G2 Trace | 事件可信 | 关键事件 P/R ≥ 0.95，无静默 loss | 调整插桩，不进入 oracle 结果 |
| G3 Replay | 反例非插桩伪影 | 30 次重放；low ≥ 90%；overhead ≤ 25% | 优化 gate/日志；低于 80% 停止 |
| G4 Verdict | 判定可用 | `inconclusive` ≤ 10%，误报 ≤ 5% | 最多两轮 mapping 修订 |
| G5 Value | 有独立增益 | hidden/historical fault 上有显著 effect | 若无增益，缩小或终止主张 |
| G6 Transfer | 不过拟合 | 6–8 周内 Derby 复用核心 invariant | 若需重写核心，停止外推 |

硬停止条件：

- baseline 经两轮修复仍随机遗留 owner/waiter；
- 无法区分 logical data lock 与 structural crab；
- 两轮 schema/mapping 修订后 `inconclusive > 20%`；
- 低插桩重放率持续 `< 80%`；
- 所有“发现”只在 high gate 模式出现；
- 相对 random/handwritten/history-only 无可重复增益；
- 只能发现已知 PR 或模型导出的手工 mutation；
- 为支持实验必须重写 VanillaCore 核心而非局部插桩；
- Derby transfer 8 周后仍不能复用核心 invariant。

## 12. 风险与应对

### 12.1 上游陈旧与工具链漂移

风险：稳定版 2022、默认分支 2023，README Java 要求可能与 POM/CI 不一致。

应对：双基线、容器固定、构建 manifest；不投入无上限的现代化改造。

### 12.2 原始基线已含缺陷

风险：checker 把已知缺陷当正常语义，或实验被不稳定状态污染。

应对：pristine/reference/instrumented/mutant 四类明确分离；PR #95 先独立复现。

### 12.3 模型与实现共谋

风险：从源码抽取模型后，模型复制同一 bug。

应对：协议规范、文档、源码、history oracle、修复差分、隐藏 mutation 多源交叉；Specula/LLM 只生成候选，不直接成为 oracle。

### 12.4 部分可观测与日志扰动

风险：日志顺序被误当真实顺序，临界区 I/O 改变 schedule。

应对：偏序对齐、证据等级、临界区只复制、low/off 重放、event-loss 明示。

### 12.5 物理 timeout 不稳定

风险：CI 负载引起假 hang/假 abort。

应对：抽象 timeout phase、参数扫描、CPU pinning、fresh JVM、wall-clock verdict 与状态 invariant 分开。

### 12.6 B-tree 结构锁误报

风险：相同 `BlockId` 和 `LockTable` API 掩盖不同目的。

应对：`resource_role`、`lock_purpose`、source-site 映射；P-Struct 独立。

### 12.7 mutation validity

风险：易检 mutation 夸大效果，等价 mutation 污染分母。

应对：语义 family 分层、隐藏集、历史 fault、第二人复核、等价性审查。

### 12.8 外部有效性不足

风险：教学系统结果不能迁移。

应对：所有 VanillaCore 结论标为 calibration；Derby 是硬 gate，MySQL 是生产主案例。

## 13. 研究治理与角色

| 角色 | 责任 | 独立性要求 |
| --- | --- | --- |
| 模型负责人 | TLA+、invariant、refinement ledger | 不看 hidden mutation 细节 |
| SUT/插桩负责人 | VanillaCore fork、event sink、gate | 不单独决定 verdict |
| 映射与 oracle 负责人 | normalization、partial-order、三值判定 | 与模型规则双人 review |
| Mutation curator | fault taxonomy、hidden manifest | 解盲前不向模型负责人披露 |
| 实验负责人 | manifest、runner、数据完整性 | 不能静默排除失败 run |
| 统计负责人 | 分析计划、CI、效果量 | 解盲前冻结主分析 |
| 外部复核者 | 最小反例、根因、许可与 artifact | 至少复核全部强 contradiction |
| 上游维护者（可选） | 澄清 contract、评审修复 | 不把未回复当作正确性证据 |

## 14. 年表与研究上下文

| 时间 | 事件 | 对本项目的意义 |
| --- | --- | --- |
| 2016 前后 | VanillaDB 家族用于教学/研究，T-Part 等工作出现 | 说明系统不只是单个课程作业 |
| 2018 | index locking / dirty-read 相关 PR 与 `a83acf5` | 提供真实 index 并发历史 |
| 2019 | `feb5c38` 修改 RC statement/leaf lock 路径 | 形成 RC 叶块高优先级回归假设 |
| 2022-04 | PR #95 提出 LockTable 并发与 cleanup 问题 | 当前最直接 baseline gate |
| 2022-09 | 0.7.0 发布到 Maven Central | 第一可复现实验基线 |
| 2023-04 | 默认分支固定 HEAD，转向 JDK 17 | 第二版本与工具链差异 |
| 2026 | NTHU 课程仍使用 VanillaCore，讲义术语与源码需核对 | 文档—实现差异研究入口 |

## 15. Devil’s Advocate

### 15.1 “这是玩具系统，容易找到的都是玩具 bug”

该批评成立一半。VanillaCore 只作为校准和 mutation ground truth。论文必须把生产外部有效性留给 MySQL，把 Derby 作为 transfer gate；若没有 transfer，结论标题和摘要不得使用普适数据库措辞。

### 15.2 “LockTable 太小，TLA+ 是过度工程”

若人工 10–20 个 litmus 与随机压力在同预算下达到相同 fault family 检出率、TTF 和诊断质量，则该批评成立。故 B2/B3 是强基线，不能只和上游测试比较。

### 15.3 “从源码建模只会把源码 bug 写进模型”

因此不采用“自动抽取结果即规范”。源码只提供一个证据源；协议、官方文档、历史 patch、外部 history 和第二系统共同约束。未来使用 Specula/LLM 时，输出仅作为 candidate spec/diff，不参与无审查 verdict。

### 15.4 “插桩制造了 bug”

任何只在 high 模式出现、low/off 无法复现的结果都不能称实现 bug。重放率和 overhead 是主指标，不是附录性能数据。

### 15.5 “PR #95 已经告诉你 bug 在哪，实验没有新意”

PR #95 只用于：

- 验证 harness 能否复现已知候选；
- 校准 trace schema；
- 检查修复差分。

主效果必须来自冻结后的 hidden mutations、其他历史 fault 和非定向 schedule。若只复现 PR #95，G5 失败。

### 15.6 “文档写 wait-die，代码不同，直接报 bug 即可”

术语差异不自动等于行为错误。必须分别建 `Spec-Doc` 和 `Spec-Impl`，确定文档的 normative 程度，并寻找安全性、进展性或维护者 contract 证据。

### 15.7 “为何不直接从 MySQL 开始”

直接从 MySQL 开始会把模型错误、资源映射、PFS 快照、Debug Sync、复杂锁类型和巨大源码同时引入。VanillaCore 用较低成本隔离方法问题；但若 G0–G5 失败，应停止，而不是把 sunk cost 当理由。

## 16. 两轮批判性复核协议

### 16.1 第一轮：证据与语义审计

逐条检查：

- 每个 invariant 是否有协议/文档/源码/实验来源；
- 实现观察是否被错误提升为规范；
- 文档术语是否与实际动作混淆；
- `BlockId` 角色是否明确；
- timeout/fairness 是否超出 contract；
- 引用是否固定到 commit；
- 未合并 PR 是否标记为候选。

输出：`evidence-audit.md` 与 refinement ledger 变更。

### 16.2 第二轮：可证伪性与过拟合审计

逐条检查：

- 最强非模型基线是否公平；
- mutation 是否只覆盖模型擅长的 fault；
- checker 是否看到基线看不到的信息；
- 反例是否可 low/off 重放；
- 是否存在同样解释力更简单的 oracle；
- VanillaCore 结果是否被不当外推；
- 失败是否会触发停止，而非继续加层。

输出：预注册更新、隐藏 mutation 冻结 hash、Go/No-Go。

## 17. 立即执行清单

### 第一周

> 执行状态：已完成。逐步方法、结果和证据见 [`execution/week-01/README.md`](execution/week-01/README.md)。

1. 固定 Temurin JDK 17 构建环境，并记录 JDK 25 兼容性限制；
2. 记录本仓库 commit、上游基线与 [PR #95 补丁](evidence/patches/pr-95-fix-locktable.patch) hash；
3. 当前源码与 PR #95 参考修复双基线 clean build；
4. 关键测试 fresh JVM ×20，并显式补跑默认 suite 遗漏的 5 个测试类；
5. 为 `LockTableTest` 的 deadlock TODO 建 issue/test skeleton；
6. 写 PR #95 两个最小失败见证。

### 第二周

1. 实现最小 event sink；
2. 只插 `LOCK_CALL/WAIT_BEGIN/GRANT/RELEASE/TX_END`；
3. 实现 Direct LockTable harness；
4. 重放 `S/S`、`S/X`、`X/X` 和反序双资源；
5. 计算事件完整性与 overhead；
6. 作 G0–G2 决策。

### 第三至四周

1. L1 TLA+；
2. 导出模型 trace；
3. strict/partial-order scheduler；
4. Native Transaction harness；
5. 三值 verdict；
6. 8 类 visible mutation；
7. reducer v0；
8. 决定是否投入完整 6 个月路线。

## 18. 预期产物

### 18.1 代码与 artifact

- 本仓库 VanillaCore 源码、固定上游身份与可审查 patch sets；
- versioned TLA+ models；
- event schema 与 instrumentation generator；
- Direct/Native/SQL harness；
- strict/partial-order/PCT scheduler；
- trace normalizer/alignment checker；
- hierarchical reducer；
- mutation operator 与 hidden corpus；
- container、manifest、分析脚本与可再生 raw trace。

### 18.2 研究结果

- VanillaCore 锁与事务语义的证据化模型；
- 文档—实现—模型差异分类；
- 内部 oracle 相对 history-only 的增益数据；
- instrumentation/replay 方法学；
- 历史 fault 与隐藏 mutation benchmark；
- VanillaCore → Derby → MySQL transfer contract。

### 18.3 可发表贡献的最低形式

即使未发现新的上游真实 bug，只要严格满足以下条件，仍可能形成方法学贡献：

1. 模型轨迹能稳定驱动真实 DBMS 组件与事务路径；
2. 内部 refinement oracle 在隐藏 fault 上显示独立增益；
3. 三值 verdict 显著降低部分可观测误报；
4. counterexample reduction 输出短小可审计见证；
5. 核心 invariant/event contract 可迁移到 Derby；
6. artifact 可由第三方复现。

## 19. 关键来源与资料深读

### 19.1 VanillaCore 源码

- [`LockTable.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java)：建立五模式、等待、notify、abort mark 和 timeout 的实现事实；不能单独建立规范正确性。
- [`ConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/ConcurrencyMgr.java) 及 [`ReadCommittedConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/ReadCommittedConcurrencyMgr.java)、[`RepeatableReadConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/RepeatableReadConcurrencyMgr.java)、[`SerializableConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/SerializableConcurrencyMgr.java)：建立父子锁调用和 release policy；不能假定所有调用路径都正确。
- [`Transaction.java`](../src/main/java/org/vanilladb/core/storage/tx/Transaction.java) 与 [`RecoveryMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/recovery/RecoveryMgr.java)：建立生命周期插桩点；最终顺序仍需动态见证。
- [`BTreeDir.java`](../src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java) 与 [`BTreeLeaf.java`](../src/main/java/org/vanilladb/core/storage/index/btree/BTreeLeaf.java)：证明结构同步与逻辑锁会共享对象/API，直接改变了事件 schema。

### 19.2 历史缺陷

- [PR #95 本地补丁](evidence/patches/pr-95-fix-locktable.patch)（[上游讨论](https://github.com/vanilladb/vanillacore/pull/95)）：指出 `lockerMap` 并发访问与 `txWaitMap` 清理候选问题，使“原始基线即正确实现”的假设不可接受。
- [PR #32](https://github.com/vanilladb/vanillacore/pull/32)：双 rollback 历史使 lock abort—recovery 交互成为 L3 必测项。
- [PR #37](https://github.com/vanilladb/vanillacore/pull/37)、[`a83acf5`](https://github.com/vanilladb/vanillacore/commit/a83acf5)、[`feb5c38`](https://github.com/vanilladb/vanillacore/commit/feb5c38)：共同构成 index/leaf/RC 的回归研究线。

### 19.3 测试与文档

- [`LockTableTest.java`](../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTest.java)：适合兼容矩阵起点，但 deadlock-avoidance TODO 表明不能依赖上游覆盖。
- [`BTreeIndexConcurrentTest.java`](../src/test/java/org/vanilladb/core/storage/index/btree/BTreeIndexConcurrentTest.java) 与 [`FullTestSuite.java`](../src/test/java/org/vanilladb/core/FullTestSuite.java)：需要核对并发测试是否进入默认回归。
- [官方 Transaction Concurrency 讲义](https://www.vanilladb.org/slides/core/Transaction_Concurrency.pdf) 与 [2026 课程讲义](https://nthu-datalab.github.io/db/slides/09_Transaction_Concurrency.pdf)：用于 contract 候选和术语比较；不能覆盖源码动态行为。

## 20. Confidence & Gaps

### 20.1 置信度

| 结论 | 置信度 | 依据 | 缺口 |
| --- | --- | --- | --- |
| VanillaCore 适合第一受控 SUT | 高 | 完整源码、五模式、事务/恢复/索引、易插桩 | 尚未完成完整 spike |
| 0.7.0 可作为历史比较基线 | 中高 | Temurin JDK 17 下 clean 默认 107 项及遗漏 10 项测试通过、Maven 发布物固定 | 不在本仓库维护重复源码 |
| 本仓库上游基线可作为主基线 | 中高 | Temurin JDK 17 下 clean 默认 110 项及遗漏 10 项测试通过 | 缺重复/容器与插桩验证 |
| 原始 LockTable 需参考修复基线 | 高 | PR #95 源码级问题陈述与 patch | 尚未动态复现 |
| age-based 策略非标准 wait-die | 中高 | 源码控制流与 abort mark | 需运行时见证、维护者 contract |
| RC leaf 路径可能回归 | 中 | 当前方法与历史 patch 差分可疑 | 尚无动态错误见证 |
| 内部模型 oracle 优于 history-only | 待验证 | 理论上能观察 owner/waiter 内部 fault | 正是主实验，不可预设 |
| 资产可迁移 Derby/MySQL | 待验证 | 抽象接口有可比锁状态 | 需 transfer gate |

### 20.2 未解决问题

1. PR #95 在固定版本上能否稳定复现；
2. `lockerMap` 跨 anchor 风险在 JDK/负载下的实际表现；
3. notifier 队列容量与 event sink 的交互；
4. `MAX_TIME`/`EPSILON` 在 CI 上的稳定区间；
5. 事务 listener 的实际 commit/rollback 事件顺序；
6. RC leaf 是否构成可观察 dirty/non-repeatable read；
7. coarse phantom 的正式 contract；
8. B-tree lock 是逻辑锁、结构锁还是混合用途的每个 source site 分类；
9. VanillaBench 兼容 commit 的端到端构建；
10. 维护者是否认可文档与实现 deadlock 术语差异；
11. 低扰动 scheduler 是否能达到 90% 重放；
12. Derby transfer 是否能在 6–8 周完成。

### 20.3 最终结论

VanillaCore 值得投入一个**有严格停止条件的 2–4 周 spike**，并有较高概率发展为本项目第一个完整案例。最重要的不是立即扩大模型，而是先证明四件事：

1. 双版本基线可构建且状态不被遗留并发结构污染；
2. 插桩能无损表达 grant/wait/release/abort/lifecycle；
3. 模型 schedule 能在低扰动模式稳定重放；
4. 内部 refinement oracle 在隐藏、非定向 fault 上优于更简单基线。

若四项成立，继续 L2/L3、历史缺陷和 mutation 主实验，并以 Derby transfer 约束外推；若不成立，应尽早停止 VanillaCore 深化，保留已形成的 trace/mapping 资产，转向 Derby，而不是把维护教学系统本身变成研究目标。
