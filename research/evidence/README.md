# Evidence and Baselines

本目录只保存目标源码中不存在、且对实验解释必要的证据。当前 VanillaCore 实现直接使用 [`src/`](../../src/)，不复制 upstream checkout、发布包、Maven 缓存或 PDF。

## Baseline Variants

| Variant | Definition | Purpose |
| --- | --- | --- |
| `VC-HEAD-20230430` | 上游 commit `03e1f2df49bb9664c8bdae11cf911f56b74bbc57` | 原始源码基线 |
| `VC-REF-95` | 原始基线 + [`pr-95-fix-locktable.patch`](patches/pr-95-fix-locktable.patch) | 经审查的参考修复，不宣称官方版本 |
| `VC-INST-*` | `VC-REF-95` + 最小事件插桩 | 主实验 SUT |
| `VC-MUT-*` | 单个 `VC-INST-*` + 单 mutation | 检出率与诊断实验 |

保留补丁的 SHA-256 为 `E3C79288D13A8C8706227879DC38DB93562DAE92C4E1CBB82B0E10B8FACAD145`；[`.gitattributes`](../../.gitattributes) 禁止 Git 改写其行尾。

每次实验必须保存目标仓库 commit、上游 commit、补丁 hash、模型/映射/schema 版本、JDK/Maven/OS、timeout、数据库目录和 seed；格式见 [`../experiments/README.md`](../experiments/README.md)。

第一周固定身份及 Git object 证据见 [`../execution/week-01/results/step-02-baselines.json`](../execution/week-01/results/step-02-baselines.json)。

## Known Research Leads

- [`LockTable.java`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java) 的 `lockerMap` 由不同资源 anchor 上的 monitor 访问，PR #95 将其改为并发 map；需构造跨 anchor 并发见证。
- 同一补丁在 unlock 路径清理 `txWaitMap`；需区分内存/状态泄漏、错误 abort 标记和可观察事务失败。
- [`LockTableTest.java`](../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTest.java) 留有 deadlock-avoidance 测试空白，不能将现有 suite 当完整 oracle。
- [`ReadCommittedConcurrencyMgr.java`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/ReadCommittedConcurrencyMgr.java) 与历史 index/leaf 修复形成 RC 回归假设；必须用动态 witness 证实或否证。
- [`BTreeDir.java`](../../src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java) 和 [`BTreeLeaf.java`](../../src/main/java/org/vanilladb/core/storage/index/btree/BTreeLeaf.java) 同时涉及结构同步与逻辑锁，事件 schema 必须显式区分二者。

PR #95 的两个确定性差分见证已实现，见 [`witnesses/pr-95/README.md`](witnesses/pr-95/README.md)；外部影响仍未建立。

## Evidence Rules

1. 历史 PR 只用于预注册 fault hypothesis，不作为隐藏 mutation。
2. 原始、参考修复、插桩和 mutation 变体必须分开构建和报告。
3. 补丁应用前执行 `git apply --check`，并记录 SHA-256。
4. 所有失败先按实现矛盾、模型欠拟合、映射错误、观测缺失或插桩扰动分类。
5. 结论必须链接最小 trace、manifest、模型状态和对应本地源码。

完整研究闸门见 [`../plan.md`](../plan.md)，当前构建事实见 [`../validation.md`](../validation.md)。
