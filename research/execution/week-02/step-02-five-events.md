# Step 02 — Five LockTable Events

## Objective

只在 `LockTable` 插入 `LOCK_CALL/WAIT_BEGIN/GRANT/RELEASE/TX_END`，建立组件级最小可观测流，不混入 scheduler gate、JSON I/O、owner 快照或语义修复。

## Source Sites

| Event | Placement | Meaning |
| --- | --- | --- |
| `LOCK_CALL` | 五种 lock API 入口 | 真实请求进入组件 |
| `WAIT_BEGIN` | request set 更新后、`wait` 前 | 线程即将阻塞，可能重复 |
| `GRANT` | owner 与 reverse index 更新后 | 新 owner 状态已建立 |
| `RELEASE` | owner 状态实际移除后 | no-op release 不发事件 |
| `TX_END` | `releaseAll` 清理三个事务索引后 | Direct harness 的组件级终止代理 |

source-site 使用 `locktable.<mode>.<transition>` 稳定 ID，不依赖行号。启用 sink 时只构造字符串身份和不可变事件，并以 `offer` 写入内存队列；没有磁盘 I/O。

## Validation

```powershell
.\scripts\research\Invoke-Week02InstrumentationValidation.ps1
```

测试验证无冲突 `S` 的四事件序列，以及 `X` holder 与 `S` waiter 的 `WAIT_BEGIN < holder RELEASE < waiter GRANT`。机器结果见 [`results/step-02-five-events.json`](results/step-02-five-events.json)。

## Isolation

本提交不包含 [PR #95 参考修复](../../evidence/patches/pr-95-fix-locktable.patch)，使插桩 patch 与语义 patch 保持可区分。后续决策必须把当前状态标为 instrumented pristine，而不是 `VC-REF-95`。

## Limits

- `TX_END` 只代表 `LockTable.releaseAll` 完成，不区分 commit/rollback。
- resource role、parent 和 purpose 在 v0 中保留 `UNKNOWN`。
- 重入请求不产生新的 owner 状态，因此当前不发第二个 `GRANT`。
