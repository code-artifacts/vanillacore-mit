# Step 06 — Direct/Native L1 Projection

## Result

版本化 ledger [`direct-native-projection-v0.1.json`](direct-native-projection-v0.1.json) 把选定逻辑资源的 LOCK_CALL/WAIT_BEGIN/GRANT/TX_END 投影为 L1 request/wait/grant/lifecycle/release/wake action。Native 的父级 intention locks 与 raw release order 不进入 L1 equality，但保留为 context。

[`L1TraceProjection.project`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/L1TraceProjection.java#L43) 是 stateful projection：识别 upgrade、等待后的 wake 和 terminal release。Terminal action 锚定首个真实 RELEASE，TX_END 仅作无 RELEASE 时的兜底，因为 waiter 合法地可能在 holder 记录 TX_END 前获得 monitor 并 grant。[`DirectNativeProjectionTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/DirectNativeProjectionTest.java#L20) 对相同 logical resource 比较允许 action sequence，而非 raw event 数量。

## Recovery Boundary

[`Transaction`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L83) 的 listener 顺序先 recovery、后 concurrency；因此 rollback fixture 的含义是 undo lifecycle 完成后才 release/grant。当前 schema 保留该上下文但没有新增 recovery event，不能据此声称逐条观察了 undo 日志。

## Evidence

- [`step-06-direct-native-projection.json`](results/step-06-direct-native-projection.json) 固定 ledger hash、规则数、context 类别与五类 differential fixture。
- Direct/Native 在 S/S、S/X、X/X、commit→release→wake→grant、rollback→release→wake→grant 上投影相等。
- Native context 必须非空，从而避免“过滤后相等”掩盖层级锁事实。

## Validation

```console
python -m scripts.research.check_week04_direct_native_projection
```
