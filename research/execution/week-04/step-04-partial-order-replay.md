# Step 04 — Partial-Order Replay

## Result

[`PartialOrderScheduleController`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/PartialOrderScheduleController.java#L20) 以 node ID 区分重复事件，只在全部 predecessor 完成后放行；constructor 对未知 edge 和 cycle fail closed。实际 node linearization 与 seed 可由 [`actualLinearization`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/schedule/PartialOrderScheduleController.java#L99) 读取。

[`validate_dag`](../../../scripts/research/partial_order.py#L7) 验证全部八个 schedule manifest。同一独立动作 fixture 保留 A→B→C 与 B→A→C 两种顺序，二者都满足汇合点 C 的 barrier predecessor。

## Evidence Boundary

- [`step-04-partial-order.json`](results/step-04-partial-order.json) 记录 seed、八个 DAG 大小、两种合法 linearization 与 Java 测试结果。
- [`PartialOrderScheduleControllerTest`](../../../src/test/java/org/vanilladb/core/storage/tx/concurrency/schedule/PartialOrderScheduleControllerTest.java#L14) 实际执行两种顺序，并验证提前到达的安全 gate 等待 predecessor。
- 该实现采用 [DPOR 原论文](https://doi.org/10.1145/1040305.1040315) 的因果等价思想，但只重放给定 DAG，不实现动态 backtracking 或完备搜索。

## Validation

```console
python -m scripts.research.check_week04_partial_order
python -m unittest scripts.tests.test_partial_order -v
```
