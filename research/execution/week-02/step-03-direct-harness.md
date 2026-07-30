# Step 03 — Direct LockTable Harness

## Objective

实现与 `LockTable` 同 package 的组件级 harness，使场景代码只表达事务、资源、模式和事件约束，不直接管理锁表反射、线程池或轮询。

## API Boundary

`DirectLockTableHarness` 提供：

- `lock` 与 `submitLock`：同步或异步请求 `IS/IX/S/SIX/X`；
- `awaitEvent`：基于 sink 通知等待事务、事件类型和资源，不使用 `Thread.sleep`；
- `release` 与 `end`：显式单锁释放或组件级事务结束；
- `snapshot`：返回有 loss 元数据的不可变事件视图；
- `close`：有限时等待 worker 停止并清理未结束事务。

Harness A 故意绕过 parent locking、SQL、recovery 和真实 commit/rollback，因此其结论只适用于 `LockTable` 局部 contract。

## Validation

```powershell
.\scripts\research\Invoke-Week02DirectHarnessValidation.ps1
```

测试覆盖同步 `S` 生命周期和受事件驱动的 `X` holder / `S` waiter。结果见 [`results/step-03-direct-harness.json`](results/step-03-direct-harness.json)。

## Limits

- JVM 内 `LockTrace` 是单活动 sink，场景必须串行建 harness。
- `awaitEvent` 是观测同步，不是源码 scheduler gate。
- 当前 harness 不声称复现原生 Transaction lifecycle。
