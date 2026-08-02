# Step 05 — Native Harness

## Result

[`NativeTransactionHarness.newTransaction`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/NativeTransactionHarness.java#L91) 通过 [`TransactionMgr.newTransaction`](../../../src/main/java/org/vanilladb/core/storage/tx/TransactionMgr.java#L173) 创建固定事务号的 Serializable transaction。资源 dispatch 调用真实 [`ConcurrencyMgr`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/ConcurrencyMgr.java#L30) file/block/record API。

[`NativeTransactionHarness.lifecycle`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/NativeTransactionHarness.java#L146) 在 harness-safe boundary 观察 commit、rollback 与 endStatement，然后调用 [`Transaction`](../../../src/main/java/org/vanilladb/core/storage/tx/Transaction.java#L33) lifecycle。所有 worker throwable 由 [`WorkerOutcome`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/NativeTransactionHarness.java#L35) 返回，不依赖未捕获线程异常。

## Evidence

- [`NativeTransactionHarnessTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/NativeTransactionHarnessTest.java#L24) 覆盖 parent intention locks、S/S、S/X、X/X、commit release、rollback 后 grant、statement boundary、terminal residue 与线程清理。
- [`step-05-native-harness.json`](results/step-05-native-harness.json) 固定测试计数与覆盖能力。
- Native 的 parent file/block locks 是预期层级语义，不能与 Direct 原始事件逐条比较；投影在 [Step 06](README.md#steps) 定义。

## Validation

```console
python -m scripts.research.check_week04_native_harness
```
