# Step 04 — Canonical TLC Trace Families

## Objective

从 [`VC_L1_SX.tla`](../../../tla/l1/VC_L1_SX.tla) 的完整 2×2 bounded state graph 中自动导出八类规范轨迹，保留工具、模型、配置、映射、原始图和选择规则的 provenance，避免把手写示例误当作模型生成证据。

## Methodology

- **研究时间与模式：** 2026 年 7 月，Standard；本步骤实现并复核既定第三周轨迹要求。
- **查询与一手来源：** 查阅官方 [TLC current tools](https://github.com/tlaplus/tlaplus/blob/master/general/docs/current-tools.md) 与 [TLA+ Tools v1.7.4 release](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4)，确认 action-labelled DOT dump、固定版本和 CLI 参数。
- **证据策略：** 使用无 symmetry 的 [`VC_L1_SX_2x2_trace.cfg`](../../../tla/l1/VC_L1_SX_2x2_trace.cfg)，固定 [`seed`](results/step-04-canonical-traces.json#L34) 和单 worker 穷举状态图；[`parse_dot_graph`](../../../scripts/research/traces.py#L169) 解析 TLC 节点/边并去重，[`extract_trace`](../../../scripts/research/traces.py#L259) 按完整事件模式匹配，以最小数值 state-id 作唯一 tie-break。
- **限制：** 未尝试付费或不可访问来源；结论仅覆盖固定的 2×2、八请求边界。当前 [`mapping-v0.1.json`](../../../tla/l1/mapping-v0.1.json) 仍为 provisional，规范轨迹不是实现轨迹。

## Artifacts

- 跨平台入口：[`export_l1_traces.py`](../../../scripts/research/export_l1_traces.py)；
- 图解析、状态结构化和八类模式：[`traces.py`](../../../scripts/research/traces.py#L57)；
- 固定 trace 配置：[`VC_L1_SX_2x2_trace.cfg`](../../../tla/l1/VC_L1_SX_2x2_trace.cfg)；
- machine-readable evidence：[`step-04-canonical-traces.json`](results/step-04-canonical-traces.json)；
- parser、去重、结构化最终状态与 catalog 测试：[`test_traces.py`](../../../scripts/tests/test_traces.py#L15)。

原始 DOT 图保存在 [`.gitignore` 排除的工具目录](../../../.gitignore)，不进入 Git；其路径、字节数和 SHA-256 固定在 [`provenance`](results/step-04-canonical-traces.json#L7)，可由入口命令重新生成和核对。

## Results

TLC 以固定配置穷举 [`12,637` 个 distinct states、`33,634` 条去重边](results/step-04-canonical-traces.json#L42)。导出结果包含以下八类 exact-pattern witness：

| Family | Canonical witness | Final observation |
| --- | --- | --- |
| S/S | [`shared-shared-compatible`](results/step-04-canonical-traces.json#L55) | 两个 reader 均持有 S |
| S/X | [`shared-exclusive-conflict`](results/step-04-canonical-traces.json#L157) | writer 进入 WAITING |
| X/S | [`exclusive-shared-conflict`](results/step-04-canonical-traces.json#L259) | reader 进入 WAITING |
| X/X | [`exclusive-exclusive-conflict`](results/step-04-canonical-traces.json#L363) | 第二个 writer 进入 WAITING |
| Single upgrader | [`single-upgrader`](results/step-04-canonical-traces.json#L467) | S→X 成功 |
| Double upgrader | [`double-upgrader`](results/step-04-canonical-traces.json#L571) | 两个 upgrader 均 WAITING |
| Commit release | [`writer-commit-reader-grant`](results/step-04-canonical-traces.json#L721) | writer COMMITTED 后 reader 获 S |
| Rollback release | [`writer-rollback-reader-grant`](results/step-04-canonical-traces.json#L873) | writer ABORTED 后 reader 获 S |

每条 witness 保存 action sequence、源/目标 state-id、TLA+ action、规范事件和结构化最终状态。相同固定 seed 的第二次完整导出得到相同 DOT SHA-256、状态计数和八条轨迹。

## Reproduction

```console
python -m scripts.research.export_l1_traces
python -m unittest scripts.tests.test_traces -v
```

## Confidence & Gaps

- **置信度：高（bounded export correctness）。** 固定工具 hash、配置、seed、完整状态图、重复运行和 parser 单测共同支持导出可复现。
- **最强证据：** [`PASS 结果与完整 provenance`](results/step-04-canonical-traces.json#L6) 直接来自 TLC graph，不依赖人工编排 action sequence。
- **主要缺口：** 有界 witness 不构成无界证明；provisional mapping 尚不能证明 Java execution 与规范路径一致；double-upgrader 只展示等待状态，不在本步骤引入 age-based victim policy。

## Commit Summary

### 完成任务

- 为第三周第四步建立 TLC 原始 action-labelled state graph 到八类 canonical trace 的可复现导出链路。
- 用固定 seed、无 symmetry 配置和确定性 tie-break 消除手写轨迹与运行顺序造成的证据歧义。

### 代码与配置改动

- [`traces.py`](../../../scripts/research/traces.py#L169) 新增 DOT parser、重复边去重、完整状态解析、exact-pattern 路径抽取、TLC 执行与 provenance 输出。
- [`SCENARIOS`](../../../scripts/research/traces.py#L57) 精确定义 S/S、S/X、X/S、X/X、单/双 upgrader、commit/rollback 后 reader grant 八类模式。
- [`export_l1_traces.py`](../../../scripts/research/export_l1_traces.py#L12) 提供跨平台 CLI；[`toolchain.json`](../../../tla/toolchain.json#L70) 固定模型、配置、常量、seed 与忽略的原始图位置。
- [`VC_L1_SX_2x2_trace.cfg`](../../../tla/l1/VC_L1_SX_2x2_trace.cfg#L1) 保留全部七条 invariant 并明确禁用 symmetry reduction，以保持事务和资源身份稳定。

### 测试、自动化与证据

- [`test_traces.py`](../../../scripts/tests/test_traces.py#L15) 覆盖 DOT 重复边、跨行 record、结构化最终状态和八类 catalog 完整性；CLI import/help 与 manifest 测试同步扩展。
- [`step-04-canonical-traces.json`](results/step-04-canonical-traces.json#L6) 记录 PASS、工具/模型/config/mapping/raw graph hashes、常量、seed、TLC metrics、action sequence 与最终状态。
- 两次完整 TLC 执行均得到 12,637 distinct states、33,634 条去重边和相同 raw graph SHA-256；八条轨迹逐字段一致。

### 语义影响、限制与注意事项

- 本提交不改变 Java 或 L1 状态转移，只增加专用无 symmetry 配置、导出工具、测试和证据。
- 原始 10 MB DOT 图按仓库策略保持忽略；tracked JSON 保存其 hash/size，审查者必须通过固定入口重建原始图。
- 结果只证明八类模式在 2×2、MaxRequests=8 状态空间可达；不得解释为无界 safety/liveness 证明或实现 conformant 结论。
