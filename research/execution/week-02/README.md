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
