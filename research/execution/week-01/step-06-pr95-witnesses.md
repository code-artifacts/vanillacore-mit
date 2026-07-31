# Step 06 — PR #95 Minimal Failing Witnesses

## Objective

为 PR #95 的两个改动各建立一个确定性最小见证，并证明它们在 pristine/reference-fix 双基线上产生预注册的相反结果。

## Method

[`invoke_pr95_witness_matrix.py`](../../../scripts/research/invoke_pr95_witness_matrix.py)：

1. 验证 manifest 固定的基线 [`src/main`](#method) tree 仍与固定上游一致；
2. 从当前 HEAD 创建两个 detached worktree；
3. 将见证测试复制到两者，只对 reference worktree 应用固定 PR #95 补丁；
4. 以 [`vanillacore.mit.pr95Witnesses=true`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTablePr95WitnessTest.java#L18) 显式激活；
5. 从 Surefire XML 验证 pristine 恰好 2 failures、reference fix 恰好 0 failures；
6. 成功后清理 worktree，raw log 保存在 Git 忽略目录。

```console
python -m scripts.research.invoke_pr95_witness_matrix
```

## Witnesses

- [`lockerRegistrySupportsUpdatesFromDistinctAnchors`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTablePr95WitnessTest.java#L24)：不同 anchor 共享的 registry 必须支持并发结构访问。
- [`reentrantGrantRemovesWaitRegistration`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTablePr95WitnessTest.java#L36)：重入早返回后不得残留 [`txWaitMap`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L105)。

详细假设与限制见 [`../../evidence/witnesses/pr-95/README.md`](../../evidence/witnesses/pr-95/README.md)。

## Result

机器可读矩阵：[`results/step-06-pr95-witness-matrix.json`](results/step-06-pr95-witness-matrix.json)。

| Variant | Tests | Failures | Expected |
| --- | ---: | ---: | --- |
| [`VC-HEAD-20230430`](results/step-06-pr95-witness-matrix.json#L25) | 2 | 2 | Yes |
| [`VC-REF-95`](results/step-06-pr95-witness-matrix.json#L39) | 2 | 0 | Yes |

两份 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) SHA-256 不同，且 [`matrixPassed=true`](results/step-06-pr95-witness-matrix.json#L53)。这关闭“见证没有实际执行补丁差分”的风险。

## Interpretation

- **Confirmed:** 两个 PR #95 改动都有确定性回归见证，现有默认 suite 未捕获。
- **Confirmed:** 参考补丁同时消除两个见证。
- **Not established:** [`ConcurrentHashMap`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html) 是唯一正确修复，或 PR #95 覆盖所有等待/清理路径。
- **Not established:** 两个内部缺陷的生产影响与触发概率。

## Confidence & Gaps

**Overall confidence:** High for the registered source-level differentials.

最强证据是同一测试源码、同一 JDK、两个隔离 worktree 的精确失败计数。外部影响、替代修复和 stress symptom 仍属于后续研究。
