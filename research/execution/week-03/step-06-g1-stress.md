# Step 06 — G1 Differential [LockTable](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) Stress

## Objective

在固定 [`VC-HEAD-20230430`](../week-01/results/step-02-baselines.json#L5)、[`VC-REF-95`](../week-01/results/step-02-baselines.json#L6) 和 instrumented-pristine 三个变体上执行 2/4/8/16 workers 的 compatible/conflict 压力矩阵；每个变体累计至少一百万 lock operations，分类 owner、request、locker map、transaction-lock map、wait map 和 abort registry 残留，并复跑两个 PR #95 witness。

## Methodology

- **基线：** 原始与参考修复 worktree 均来自固定研究 commit；只对参考修复应用 hash-pinned [`PR #95 patch`](../../evidence/patches/pr-95-fix-locktable.patch)。instrumented-pristine 来自当前生产源码，不混入参考修复。
- **矩阵：** [`LockTableStressMatrixTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableStressMatrixTest.java#L44) 对每个 worker 数执行 S/S-compatible 与 X/X-conflict cell；每 cell 62,500 iterations，每 iteration 包含首次 acquire、reentrant acquire 和 release-all，实际每变体 [`1,500,000` lock operations](results/step-06-g1-stress.json#L69)。
- **残留：** [`residueSnapshot`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTestProbe.java#L43) 反射读取 owner/request 引用和三个事务级 map；[`classify_stress_cell`](../../../scripts/research/stress.py#L93) 只把补丁明确针对的原始/instrumented locker-map 与 reentrant wait-registration 症状标为 known，worker failure、terminal residue 或参考修复上的同类症状均为 unexplained。
- **provenance：** [`harness`](results/step-06-g1-stress.json#L37) 固定 Java harness、probe、witness、Python automation 源码 SHA-256；Maven stdout/stderr、CSV 留在 [`.gitignore` 排除的 raw 目录](../../../.gitignore#L44)，tracked result 保存各自 hash。

## Retained Attempt 01

第一次 multi-anchor 设计没有删除或覆盖为“成功”：[`attempt-01`](results/step-06-g1-stress-attempt-01.json#L6) 保存为 gate-ineligible evidence。

- 原始基线和参考修复均完成 1,500,000 operations；原始基线出现 499,284 次 reentrant wait-registration、7 个非零 locker-map cell、一个 cell 的 3 个 terminal owner references，而参考修复 8/8 cell clean；
- instrumented-pristine 未产生 CSV，原因无法在 SUT stall 与 harness termination defect 之间区分；原 harness 对每个 Future 依次等待 120 秒且使用 non-daemon worker，可能成倍放大超时；
- [`correctiveAction`](results/step-06-g1-stress-attempt-01.json#L50) 将 worker 改为 daemon、每 cell 单一全局 deadline，并以单 anchor bounded workload 作正式门控；distinct-anchor 风险由保留的 attempt 与两个 witness 支持，不把失败运行选择性丢弃。

## Formal Results

| Variant | Lock operations | Cell classification | Reentrant wait observations | Final unexplained residue |
| --- | ---: | --- | ---: | ---: |
| [`VC-HEAD-20230430`](results/step-06-g1-stress.json#L69) | 1,500,000 | 8 known PR #95 symptom | 500,000 | 0 |
| [`VC-REF-95`](results/step-06-g1-stress.json#L302) | 1,500,000 | 8 clean | 0 | 0 |
| [`VC-INST-PRISTINE`](results/step-06-g1-stress.json#L519) | 1,500,000 | 8 known PR #95 symptom | 500,000 | 0 |

正式矩阵 24 个 cell 均无 abort、worker error、timeout 或 terminal owner/request/map residue。原始与 instrumented 变体的 wait registration 在 reentrant return 时可观察，但本次每 iteration 的 release-all 最终清理该条目；参考修复在中间点和终态均为零。

[`PR #95 witness rerun`](results/step-06-g1-stress.json#L752) 再次得到原始基线 2 tests/2 failures、参考修复 2 tests/0 failures，与 [`Week 1`](../week-01/step-06-pr95-witnesses.md#L31) 独立运行一致。最终 [`G1 PASS`](results/step-06-g1-stress.json#L785) 表示参考修复在本预算内无 unexplained pollution，且补丁两项差分可复现。

## Reproduction

```console
python -m scripts.research.invoke_week03_g1_stress
python -m unittest scripts.tests.test_stress -v
```

## Evidence Boundary

正式 cell 使用单 anchor 保证有界终止，因此不把它写成 distinct-anchor [`HashMap`](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/HashMap.html) race 的穷尽验证；multi-anchor attempt 的异常只作为支持证据。PR #95 仍是未合并的研究参考修复。G1 PASS 不证明补丁在本矩阵之外完整，也不批准后续 G3；low sink 必须单独达到第三周硬上限。

## Commit Summary

### 完成任务

- 完成三变体、2/4/8/16 workers、compatible/conflict、每变体 150 万 lock operations 的 G1 压力差分，并逐 cell 分类 known、clean 与 unexplained。
- 在同一批隔离 worktree 中复跑两个 PR #95 witness，证明原始 2/2 failure 与参考修复 0/2 failure 的差异仍可重复。
- 保留首轮 inconclusive harness 尝试及 corrective action，不删除不利或失败结果。

### 测试与 harness 改动

- [`LockTableStressMatrixTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableStressMatrixTest.java#L27) 添加固定 worker/workload 矩阵、event-free start gate、daemon workers、单 cell global deadline、reentrant symptom sampling 和 CSV evidence。
- [`LockTableTestProbe.ResidueSnapshot`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/LockTableTestProbe.java#L99) 增加 locker-map entry、owner/request references、lockBy/wait/abort map 的终态快照。
- [`stress.py`](../../../scripts/research/stress.py#L268) 创建并清理三类 detached worktree、应用固定补丁、运行压力和 witness、解析 CSV/Surefire、固定源码与日志 hash，并实施百万操作和 G1 gate。

### 自动化、测试与证据

- [`invoke_week03_g1_stress.py`](../../../scripts/research/invoke_week03_g1_stress.py#L12) 提供跨平台入口；[`test_stress.py`](../../../scripts/tests/test_stress.py#L33) 覆盖 known/unexplained 分类、terminal owner residue 和完整矩阵要求。
- [`step-06-g1-stress.json`](results/step-06-g1-stress.json#L6) 保存 24 个 cell、三变体各 150 万 operations、源码/CSV/log hashes、witness 结果和门控判定。
- [`step-06-g1-stress-attempt-01.json`](results/step-06-g1-stress-attempt-01.json#L6) 保存首轮两变体结果、instrumented 不完整状态、raw hashes、无效原因和修订措施。

### 语义影响、限制与注意事项

- 本提交不修改生产代码或锁语义，只增加 test probe、stress harness、Python orchestration 与证据。
- 原始和 instrumented 变体的中间 wait-registration 是已知 PR #95 symptom，不等同 terminal leak；正式 24 个 cell 的终态 residue 均为零。
- 单 anchor 正式 workload 与 multi-anchor attempt 的证据强度不同；不得用 G1 PASS 宣称所有 distinct-anchor race 已消失，或把未合并 PR #95 描述为官方修复。
