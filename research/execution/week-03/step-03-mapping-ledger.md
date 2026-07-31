# Step 03 — Mapping and Refinement Ledger v0.1

## Objective

把 [`L1`](../../../tla/l1/VC_L1_SX.tla) 的动作与 invariant 逐项关联到当前 Java 源码、五类事件、资源字段和偏序证据，并明确哪些映射允许强 contradiction、哪些必须输出 [`inconclusive`](../../plan.md#52-抽象函数)。

## Artifacts

- 人工可审查说明：[`MAPPING.md`](../../../tla/l1/MAPPING.md)；
- machine-readable ledger：[`mapping-v0.1.json`](../../../tla/l1/mapping-v0.1.json)；
- 结构与源码位置校验：[`check_l1_mapping.py`](../../../scripts/research/check_l1_mapping.py)；
- 机器结果：[`step-03-mapping-ledger.json`](results/step-03-mapping-ledger.json)。

## Policy Boundary

当前 [`LOCK_CALL/WAIT_BEGIN/GRANT/RELEASE/TX_END`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/trace/LockTraceEventType.java#L4) 足以强映射普通 S/X request、wait、grant 和 complete release-all。以下情形仍阻止强 contradiction：upgrade 无 held-before、wake 无直接事件、TX_END 不区分 commit/rollback、owner/waiter snapshot 缺失，以及 role/parent/purpose 为 unknown。

全部七条 invariant 的 reviewer 仍为 unassigned，因此 ledger 状态是 provisional；本步骤 PASS 只表示覆盖完整、事件类型有效、源码位置未漂移和强判定资格规则自洽。

## Results

- [`11` 个动作与 `7` 条 invariant](results/step-03-mapping-ledger.json#L11) 均且仅映射一次；
- [`5` 个动作](results/step-03-mapping-ledger.json#L13) 只有在各自 strong conditions 满足时可参与强 contradiction；
- observation 分布为 6 observed、1 derived、2 inferred、2 unobserved；
- [`5` 项 unresolved 与 `7` 个 unassigned reviewer](results/step-03-mapping-ledger.json#L27) 使状态保持 provisional。

## Reproduction

```console
python -m scripts.research.check_l1_mapping
```

## Commit Summary

### 完成任务

- 建立 mapping/refinement ledger v0.1，逐项覆盖 L1 的 11 个动作、7 条 invariant、资源字段、顺序证据、unknown policy 和 unresolved evidence。
- 提供自动校验，防止模型 hash、Java/TLA+ 源码行、事件枚举、动作/invariant 覆盖或强判定资格静默漂移。

### 账本与文档改动

- [`mapping-v0.1.json`](../../../tla/l1/mapping-v0.1.json) 保存模型 hash、trace schema、动作规则、实现位置、required events、observation class、strong conditions、资源/偏序映射和 refinement ledger。
- [`MAPPING.md`](../../../tla/l1/MAPPING.md) 提供可审查表格，并把普通 request、upgrade、wake、commit/rollback 与 release-all 的证据强度分开。
- [`check_l1_mapping.py`](../../../scripts/research/check_l1_mapping.py) 生成机器结果；[`mapping.py`](../../../scripts/research/mapping.py) 校验完整性、唯一性、源码符号、事件类型、resource/order 位置和 reviewer/confidence 字段。

### 测试与证据

- [`test_mapping.py`](../../../scripts/tests/test_mapping.py) 覆盖完整账本、未知事件、过期源码行和缺失 strong conditions 四类行为。
- 机器校验 PASS，mapping SHA-256 固定于 [`step-03-mapping-ledger.json`](results/step-03-mapping-ledger.json#L8)。
- 完整 Python 测试 24 项、40 份文档引用、Python 编译和 Git whitespace 检查通过。

### 语义影响、限制与注意事项

- 本提交不改变 Java、TLA+ 状态机或 Week 2 trace schema，只冻结并校验二者之间的候选抽象函数。
- PASS 不表示映射已由实现行为验证；所有 invariant reviewer 仍为 unassigned，账本必须保持 provisional。
- Upgrade、wake、commit/rollback、owner/waiter snapshot 与资源角色仍不完整；任何相关判断必须输出 inconclusive，直到后续 schema/mapping 版本有直接证据。
