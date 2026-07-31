# Step 05 — L1 Model Self-Tests and Week 2 Fixtures

## Objective

建立模型或 mapping 变更后必须全量重放的 fail-closed 自测试：合法 canonical trace 必须保持可执行，compatibility、strictness、cleanup 三类故障必须被目标 invariant 捕获，[`Week 2 四场景`](../week-02/step-04-scenario-replay.md#schedules) 必须在当前证据边界内保持可解释。

## Test Layers

1. [`validate_canonical_corpus`](../../../scripts/research/model_selftest.py#L254) 校验当前模型、trace config 和 mapping hash，逐动作重放八条 [`canonical trace`](results/step-04-canonical-traces.json#L52)，并逐字段比较 TLC 最终状态。
2. [`VC_L1_SX_SelfTest.tla`](../../../tla/l1/VC_L1_SX_SelfTest.tla) 构造只破坏一个目标性质的三个初态：[`CompatibilityFaultInit`](../../../tla/l1/VC_L1_SX_SelfTest.tla#L19)、[`StrictnessFaultInit`](../../../tla/l1/VC_L1_SX_SelfTest.tla#L40) 和 [`CleanupFaultInit`](../../../tla/l1/VC_L1_SX_SelfTest.tla#L51)。TLC 必须以预期错误码报告对应 invariant，而不是任意失败。
3. [`week2-v0.1.json`](../../../tla/l1/fixtures/week2-v0.1.json) 固定原始 summary、Java 场景源码、模型和 mapping hash；[`validate_week2_fixtures`](../../../scripts/research/model_selftest.py#L283) 重放四个归一化 fixture 并检查终态。

## Week 2 Normalization

| Fixture | Verdict boundary | Normalization |
| --- | --- | --- |
| [`week2-s-s`](../../../tla/l1/fixtures/week2-v0.1.json#L32) | Confirmed | 两个 S request/grant 后依次 commit/release-all |
| [`week2-s-x`](../../../tla/l1/fixtures/week2-v0.1.json#L53) | Confirmed | S holder、X wait、holder release、wake/grant |
| [`week2-x-x`](../../../tla/l1/fixtures/week2-v0.1.json#L76) | Confirmed | X holder、X wait、holder release、wake/grant |
| [`week2-reverse-two-resource`](../../../tla/l1/fixtures/week2-v0.1.json#L99) | Inconclusive | 保留 age-based abort 的一个合法 L1 projection，但不把外部 Future outcome 提升为强 trace mapping |

反序双资源 fixture 的合法性只防止模型无依据收紧；由于 [`TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L8) 不区分 commit/rollback 且 v0 schema 无 abort event，它必须稳定保持 inconclusive。

## Results

- 八条 canonical trace 均由 [`replay`](../../../scripts/research/model_selftest.py#L234) 执行，并与 TLC 最终状态一致；
- 三个负例分别只命中 [`MutualExclusion`](results/step-05-model-self-tests.json#L68)、[`StrictXRetention`](results/step-05-model-self-tests.json#L82) 与 [`TerminalClean`](results/step-05-model-self-tests.json#L96)，TLC exit code 均为 12；
- 四个 Week 2 fixture 全部可重放，其中 [`3` 个 confirmed、`1` 个 inconclusive](results/step-05-model-self-tests.json#L110)；
- 汇总状态为 [`PASS`](results/step-05-model-self-tests.json#L6)。

## Reproduction

```console
python -m scripts.research.check_l1_self_tests
python -m unittest scripts.tests.test_model_selftest -v
```

## Evidence Boundary

Python [`apply_event`](../../../scripts/research/model_selftest.py#L150) 是用于 fixture 重放和最终状态交叉检查的 executable oracle，不替代 TLC。其合法 corpus 输入来自 TLC state graph，负例检测仍由实际 TLA+ invariant 执行。任何模型、mapping、Week 2 summary 或 Java 场景源码 hash 漂移都会失败并要求人工审查、重新归一化，而不会静默接受旧 fixture。

## Commit Summary

### 完成任务

- 建立第三周第五步的合法轨迹、三类负例和 Week 2 四场景回归自测试，确保模型/mapping 修改后完整 corpus fail-closed 重放。
- 显式保留 reverse-two-resource 的 inconclusive 边界，避免把不可观测 abort 与 commit/rollback 区分伪装成 confirmed refinement。

### 模型、代码与 fixture 改动

- [`VC_L1_SX_SelfTest.tla`](../../../tla/l1/VC_L1_SX_SelfTest.tla#L19) 添加三个单故障初态；三个专用配置分别只检查目标 invariant，并由 [`toolchain.json`](../../../tla/toolchain.json#L80) 固定预期错误码和故障说明。
- [`model_selftest.py`](../../../scripts/research/model_selftest.py#L38) 添加 L1 初态、兼容性、六条语义 invariant、11 个动作的 executable replay、canonical/hash 校验、Week 2 fixture 校验和负例 TLC runner。
- [`week2-v0.1.json`](../../../tla/l1/fixtures/week2-v0.1.json#L1) 保存四个归一化 action sequence、raw trace hash、预期终态与三值 verdict 边界。
- [`check_l1_self_tests.py`](../../../scripts/research/check_l1_self_tests.py#L12) 提供跨平台单入口，并输出 [`step-05-model-self-tests.json`](results/step-05-model-self-tests.json)。

### 测试、自动化与证据

- [`test_model_selftest.py`](../../../scripts/tests/test_model_selftest.py#L14) 独立检查 Python invariant oracle 能拒绝 compatibility、strictness、cleanup 故障，并重放八条 canonical trace 与四个 Week 2 fixture。
- CLI import/help 与 toolchain manifest 测试同步覆盖新入口和三个目标 invariant。
- 机器结果记录每个 TLA module/config/output hash、预期/实际 invariant、exit code、合法 trace 与 fixture 计数，便于定位模型或工具漂移。

### 语义影响、限制与注意事项

- 本提交不修改 Java 或主 L1 转移关系；新增 TLA 故障模块仅用于预期失败的自测试。
- Python oracle 与 TLA 语义存在双实现风险，因此 canonical 终态逐字段对照 TLC，且三类负例必须由 TLC 本身捕获；未来动作变更需同步审查两侧。
- PASS 不改变 provisional mapping 状态，也不证明 Week 2 实现 trace 完全 conformant；反序双资源 fixture 仍是显式 inconclusive。
