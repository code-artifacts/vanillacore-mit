# VCMIT-001 — Deterministic LockTable Deadlock Avoidance

## Status

**Skeleton.** 测试场景和接受条件已冻结；等待确定性 waiter/abort-state probe 后启用。

## Problem

[`LockTableTest.java`](../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTest.java) 原有 TODO 没有验证 [`LockTable.avoidDeadlock`](../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java)。

当前实现不是标准 wait-die：较小 `txNum` 的请求者遇到较大 `txNum` holder 时，会把 holder 加入 `txnsToBeAborted` 并通知；被标记者下一次进入 `avoidDeadlock` 时 abort。事务级 [`TxTest.java`](../../src/test/java/org/vanilladb/core/storage/tx/TxTest.java) 有 sleep 驱动的环路案例，但不能作为确定性 LockTable 单元 oracle。

## Frozen Scenario

1. `older=40` 持有资源 A 的 X lock；
2. `younger=41` 持有资源 B 的 X lock；
3. older 异步请求 B，进入 wait 并标记 younger；
4. probe 证明 older 已在 B 的 waiter state，且 younger 已被标记；
5. younger 请求 A，必须在有限时间内抛出 `LockAbortException`；
6. younger `releaseAll` 后，older 必须取得 B；
7. 两个事务释放后，owner、waiter、`txWaitMap` 与 abort marker 均清空。

## Acceptance Criteria

- 启用 [`LockTableDeadlockTest.java`](../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableDeadlockTest.java)，删除类级 `@Ignore`。
- 只使用 `Future.get(timeout)` 和显式状态 probe；禁止裸 `sleep`、无期限 `join` 或依赖默认 `MAX_TIME`。
- 连续 fresh JVM ×20 全部通过。
- 失败信息区分：未进入 wait、victim 错误、未及时 abort、未唤醒 older、状态未清理。
- 原始和 PR #95 参考基线均运行；若行为不同，必须单独归因。

## Non-Goals

- 五模式完整兼容矩阵；
- 公平性、饥饿、多事务环；
- timeout/interruption 竞态；
- recovery、B-tree latch 或完整 wound-wait 证明。

## Activation Dependency

第二周最小 event/probe 层需提供只读测试能力：判断事务是否在指定资源等待、是否被标记 abort，以及终态是否清理。生产 API 不暴露这些内部集合；probe 留在同 package 测试代码。
