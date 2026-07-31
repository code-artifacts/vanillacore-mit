# Week 02 Execution

本目录对应 [`第 17 节`](../../plan.md#17-立即执行清单)“第二周”六项立即执行清单。每一步都有独立实现、机器可读证据、研究记录和 Git 推送。

| Step | Scope | Status | Evidence |
| --- | --- | --- | --- |
| 01 | Minimal event sink | Complete | [`step-01-event-sink.md`](step-01-event-sink.md) |
| 02 | Five [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) events | Complete | [`step-02-five-events.md`](step-02-five-events.md) |
| 03 | Direct [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) harness | Complete | [`step-03-direct-harness.md`](step-03-direct-harness.md) |
| 04 | Four deterministic scenarios | Complete | [`step-04-scenario-replay.md`](step-04-scenario-replay.md) |
| 05 | Completeness and overhead | Complete | [`step-05-trace-quality.md`](step-05-trace-quality.md) |
| 06 | G0–G2 decision | Complete | [`step-06-g0-g2-decision.md`](step-06-g0-g2-decision.md) |

生成的原始 trace 与运行日志位于 [`.gitignore` 所定义的 `raw/`](../../../.gitignore#L44)，由 Git 忽略；提交的 [`results/`](results) 只保存小型机器可读汇总。

## Commit Summary Map

| Step | Primary commit | Detailed summary |
| --- | --- | --- |
| 01 | [`7d29383`](step-01-event-sink.md#primary-commit-7d29383) | [`Minimal Event Sink`](step-01-event-sink.md#commit-summary) |
| 02 | [`df0bba6`](step-02-five-events.md#primary-commit-df0bba6) | [`Five LockTable Events`](step-02-five-events.md#commit-summary) |
| 03 | [`fc79bb7`](step-03-direct-harness.md#primary-commit-fc79bb7) | [`Direct LockTable Harness`](step-03-direct-harness.md#commit-summary) |
| 04 | [`82ba3be`](step-04-scenario-replay.md#primary-commit-82ba3be) | [`Scenario Replay`](step-04-scenario-replay.md#commit-summary) |
| 05 | [`b7db685`](step-05-trace-quality.md#primary-commit-b7db685) | [`Trace Quality`](step-05-trace-quality.md#commit-summary) |
| 06 | [`d382d20`](step-06-g0-g2-decision.md#primary-commit-d382d20) | [`G0–G2 Decision`](step-06-g0-g2-decision.md#commit-summary) |

<a id="shared-follow-up-14ade02"></a>
## Shared Follow-up — [`14ade02`](#shared-follow-up-14ade02)

提交 [`14ade02`](#shared-follow-up-14ade02) 在六个步骤完成后，将研究自动化从 Windows PowerShell 迁移到只依赖 Python 标准库的跨平台实现：

- 六个 CLI 分别位于 [`invoke_week02_event_sink_validation.py`](../../../scripts/research/invoke_week02_event_sink_validation.py#L12)、[`invoke_week02_instrumentation_validation.py`](../../../scripts/research/invoke_week02_instrumentation_validation.py#L12)、[`invoke_week02_direct_harness_validation.py`](../../../scripts/research/invoke_week02_direct_harness_validation.py#L12)、[`invoke_week02_scenario_replay.py`](../../../scripts/research/invoke_week02_scenario_replay.py#L12)、[`measure_week02_trace_quality.py`](../../../scripts/research/measure_week02_trace_quality.py#L12) 和 [`new_week02_gate_decision.py`](../../../scripts/research/new_week02_gate_decision.py#L12)。
- 共享实现集中到 [`week2.py`](../../../scripts/research/week2.py#L50)，并复用 [`tooling.py`](../../../scripts/research/common/tooling.py#L1) 的 JDK 发现、进程、Git worktree、Surefire 和文件处理能力。
- [`test_cli.py`](../../../scripts/tests/test_cli.py#L10) 验证模块导入、帮助命令、旧 PowerShell 清理和文档命令迁移；[`test_tooling.py`](../../../scripts/tests/test_tooling.py#L13) 验证跨平台共享原语。
- 迁移保留各步骤结果文件中的 [`schemaVersion`](results/step-01-event-sink.json#L2)、默认输出路径和既有实验结论；它改变自动化实现与调用方式，不改变 Java 事件语义或重新生成历史实验数字。
