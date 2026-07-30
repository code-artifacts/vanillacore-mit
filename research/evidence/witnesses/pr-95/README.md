# PR #95 Minimal Witnesses

这两个测试是 [PR #95](https://github.com/vanilladb/vanillacore/pull/95) 的**差分回归见证**，不是一般化 LockTable 正确性 oracle。测试源码位于 [`LockTablePr95WitnessTest.java`](../../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTablePr95WitnessTest.java)，反射集中在 [`LockTableTestProbe.java`](../../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTestProbe.java)。

## Witness 1 — Shared Registry Contract

`lockerMap` 由多个不同资源 anchor 保护，但 map 本身跨 anchor 共享。见证先证明两个资源映射到不同 monitor，再要求 registry 实现 `ConcurrentMap`：

- pristine：`HashMap`，断言失败；
- PR #95：`ConcurrentHashMap`，断言通过。

Java 17 [`HashMap`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/HashMap.html) 明确要求并发结构修改使用外部同步；当前不同 anchor 不构成统一外部同步。该断言与 PR #95 的具体修复绑定；若未来改为全局锁或其他安全 registry，必须更新见证而不是误报行为回归。

## Witness 2 — Reentrant Cleanup

同一事务第二次请求已持有的 S lock 时，原始方法在 `hasSLock` 分支提前返回，跳过方法末尾的 `txWaitMap.remove`：

- pristine：重入后残留 `txNum -> anchor`，断言失败；
- PR #95：外层 `finally` 清理，断言通过。

该见证不依赖线程时序、timeout 或异常注入。

## Activation

见证默认通过 JUnit assumption 跳过，避免普通全量测试故意失败。只由矩阵 runner 显式激活：

```powershell
.\scripts\research\Invoke-Pr95WitnessMatrix.ps1
```

预期矩阵和实测结果见 [`../../../execution/week-01/results/step-06-pr95-witness-matrix.json`](../../../execution/week-01/results/step-06-pr95-witness-matrix.json)。

## Limits

- Witness 1 证明违反并发 collection contract 的可达结构，不证明某次运行必然产生用户可见 HashMap corruption。
- Witness 2 证明内部 stale registration，不单独证明内存增长或错误通知的外部后果。
- PR #95 未合并、未上游认可，`VC-REF-95` 仍只是研究参考修复。
