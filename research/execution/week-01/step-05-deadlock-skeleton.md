# Step 05 — Deadlock Issue and Test Skeleton

## Objective

把 [`LockTableTest.java`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTest.java) 中不可执行的 deadlock TODO 转换为有范围、有接受条件、有代码落点的研究 issue。

## Deliverables

- Issue：[`VCMIT-001`](../../issues/VCMIT-001-locktable-deadlock-avoidance.md)
- Test skeleton：[`LockTableDeadlockTest.java`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableDeadlockTest.java)
- 原 TODO 已从 `LockTableTest` 删除，避免两个不同事实来源继续漂移。

## Design

骨架冻结“older 持有 A、younger 持有 B、older 请求 B 标记 younger、younger 请求 A abort、释放后 older 继续”的最小双资源环。

类级 `@Ignore` 是有意的：当前唯一缺口是 `awaitOlderWaitAndYoungerAbortMark` 的确定性内部状态 probe。骨架已经包含有限 `Future.get`、victim 断言与 `finally` cleanup；启用前不得以 `sleep` 替代 probe。

## Validation

```powershell
.\scripts\research\Invoke-MavenJdk17.ps1 --batch-mode "-Dtest=LockTableDeadlockTest,LockTableTest" test
```

预期：

- `LockTableDeadlockTest`：1 skipped，证明 skeleton 被 Surefire 发现且默认禁用；
- `LockTableTest`：现有 3 tests 全部通过；
- test compile 通过，不修改生产源码。

## Interpretation

步骤 5 只完成 issue/skeleton，不宣称 deadlock policy 已验证。第二周 probe 层到位后，必须按 issue 接受条件启用并 fresh JVM ×20。

## Confidence & Gaps

**Overall confidence:** High that the missing test is now explicit and maintainable.

剩余缺口被压缩为一个可定位方法，而非模糊 TODO；行为正确性仍待启用后的动态证据。
