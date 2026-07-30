# References and Source Map

本索引优先链接仓库内当前源码与研究文档；外部链接只保存权威入口，不在仓库复制源码归档、Maven 制品或 PDF。

## Local Source Map

- 锁状态与等待：[`LockTable.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java)、[`LockTableTest.java`](../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTest.java)。
- 多粒度与隔离级别：[`ConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/ConcurrencyMgr.java)、[`ReadCommittedConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/ReadCommittedConcurrencyMgr.java)、[`RepeatableReadConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/RepeatableReadConcurrencyMgr.java)、[`SerializableConcurrencyMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/concurrency/SerializableConcurrencyMgr.java)。
- 事务与恢复：[`Transaction.java`](../src/main/java/org/vanilladb/core/storage/tx/Transaction.java)、[`RecoveryMgr.java`](../src/main/java/org/vanilladb/core/storage/tx/recovery/RecoveryMgr.java)。
- B-tree 并发：[`BTreeDir.java`](../src/main/java/org/vanilladb/core/storage/index/btree/BTreeDir.java)、[`BTreeLeaf.java`](../src/main/java/org/vanilladb/core/storage/index/btree/BTreeLeaf.java)、[`BTreeIndexConcurrentTest.java`](../src/test/java/org/vanilladb/core/storage/index/btree/BTreeIndexConcurrentTest.java)。
- 默认测试入口：[`FullTestSuite.java`](../src/test/java/org/vanilladb/core/FullTestSuite.java)、[`pom.xml`](../pom.xml)。

## VanillaDB Material

- [VanillaDB project](https://www.vanilladb.org/)
- [VanillaCore upstream repository](https://github.com/vanilladb/vanillacore)
- [Transaction Concurrency slides](https://www.vanilladb.org/slides/core/Transaction_Concurrency.pdf)
- [Transaction Recovery slides](https://www.vanilladb.org/slides/core/Transaction_Recovery.pdf)
- [Indexing slides](https://www.vanilladb.org/slides/core/Indexing.pdf)
- [NTHU 2026 Transaction Concurrency slides](https://nthu-datalab.github.io/db/slides/09_Transaction_Concurrency.pdf)
- [T-Part paper](https://dl.acm.org/doi/10.1145/2463676.2465302)

## Historical Evidence

- [PR #95](https://github.com/vanilladb/vanillacore/pull/95)：`lockerMap` 并发访问与 `txWaitMap` 清理；仓库保留[原始补丁](evidence/patches/pr-95-fix-locktable.patch)。
- [PR #32](https://github.com/vanilladb/vanillacore/pull/32)：rollback 与锁释放/恢复交互。
- [PR #34](https://github.com/vanilladb/vanillacore/pull/34)、[PR #37](https://github.com/vanilladb/vanillacore/pull/37)、[PR #44](https://github.com/vanilladb/vanillacore/pull/44)、[PR #50](https://github.com/vanilladb/vanillacore/pull/50)、[PR #80](https://github.com/vanilladb/vanillacore/pull/80)：索引、锁与事务回归线索。
- 本仓库 Git 历史可直接审查已合并修复，例如 `git show feb5c38`、`git show a83acf5`、`git show 3ef8dc0`、`git show 09c353f`。

历史材料用于生成假设和 regression witness，不能直接充当模型正确性的 oracle。基线解释见 [`evidence/README.md`](evidence/README.md)。

## Modeling and Testing Tools

- [TLA+](https://lamport.azurewebsites.net/tla/tla.html) 与 [TLC](https://lamport.azurewebsites.net/tla/tools.html)
- [Apalache](https://apalache-mc.org/)
- [Specula](https://github.com/specula-org/Specula)
- [Jepsen](https://jepsen.io/)（外部 history oracle 对照）

工具选型、抽象边界和迁移到 Derby/MySQL 的条件见 [`plan.md`](plan.md)。
