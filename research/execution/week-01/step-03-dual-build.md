# Step 03 — Dual-Baseline Clean Build

## Objective

在完全隔离的目录中验证 `VC-HEAD-20230430` 与 `VC-REF-95` 均能使用同一 Temurin JDK 17 clean build，并证明主工作树未被补丁污染。

## Method

[`invoke_dual_baseline_build.py`](../../../scripts/research/invoke_dual_baseline_build.py) 读取步骤 2 manifest，并执行：

1. 从固定上游 commit 创建两个 detached Git worktree；
2. 只对 `VC-REF-95` worktree 执行 `git apply --check` 和 `git apply`；
3. 在两者中顺序运行 `mvn --batch-mode clean test`；
4. 汇总 Surefire XML，而不是仅搜索控制台 `BUILD SUCCESS`；
5. 成功后删除临时 worktree；raw stdout/stderr 留在 Git 忽略目录。

```console
python -m scripts.research.invoke_dual_baseline_build
```

两个变体共享 JDK、Maven 本地仓库、主机和 timeout。顺序执行避免并行构建竞争 CPU、磁盘和 Maven cache。

## Result

机器可读结果：[`results/step-03-build-matrix.json`](results/step-03-build-matrix.json)。

| Variant | Patch | Clean build | Default suite |
| --- | --- | --- | --- |
| `VC-HEAD-20230430` | None | Pass | 110/110 pass |
| `VC-REF-95` | PR #95 exact SHA-256 | Pass | 110/110 pass |

两者 `LockTable.java` SHA-256 不同，证明参考变体实际包含补丁；两者均从相同上游 commit 创建。

## Interpretation

- **Confirmed:** PR #95 能应用、编译并保持现有默认回归通过。
- **Not established:** 默认 suite 没有覆盖补丁指出的内部状态泄漏和跨-anchor map 并发契约。
- **Not established:** 单次成功不证明 flake-free；步骤 4 使用 fresh JVM 重复测试。

## Confidence & Gaps

**Overall confidence:** High for one clean build per variant.

证据直接来自隔离 worktree、进程退出码和 Surefire XML。主要缺口是重复性和补丁行为见证，分别由步骤 4、6 关闭。
