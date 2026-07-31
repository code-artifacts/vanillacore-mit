# Step 01 — Pinned TLA+ Toolchain

## Objective

固定第三周使用的 TLA+ CLI 身份、下载校验、JDK 17 命令和两档有界配置，使后续 [`L1`](../../plan.md#l1单层-sx-strict-2pl) 模型检查不依赖开发者机器上的隐式 Toolbox 状态。

## Fixed Identity

- 官方发布：[TLA+ Tools v1.7.4](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4)；
- CLI：TLC 2.19 of 08 August 2024；
- jar：2,274,532 字节，SHA-256 为 936A262061C914694DFD669A543BE24573C45D5AA0FF20A8B96B23D01E050E88；
- Java：[`Week 1` 固定的 Temurin 17.0.20+8](../week-01/results/step-01-environment.json#L13)；TLA+ 官方要求 Java 11 或更高版本；
- 完整 machine-readable pin 见 [`tla/toolchain.json`](../../../tla/toolchain.json)。

VS Code 已安装 [TLA+ 扩展](https://marketplace.visualstudio.com/items?itemName=alygin.vscode-tlaplus)，但本研究只以可脚本化 CLI 结果作为证据，插件不进入验收依赖。

## Reproduction

[`bootstrap_tla_tools.py`](../../../scripts/research/bootstrap_tla_tools.py) 只依赖 Python 标准库，下载到被忽略的 [`.tools/`](../../../.gitignore) 目录，并在使用前核对 size 与 SHA-256：

```console
python -m scripts.research.bootstrap_tla_tools
python -m scripts.research.bootstrap_tla_tools --offline
```

命令运行 [`VC_L1_ToolchainSmoke.tla`](../../../tla/l1/VC_L1_ToolchainSmoke.tla)，分别加载 [`2×2`](../../../tla/l1/VC_L1_ToolchainSmoke_2x2.cfg) 和 [`3×3`](../../../tla/l1/VC_L1_ToolchainSmoke_3x3.cfg) 配置。两档均固定单 worker、fingerprint polynomial 0 和独立 metadata 目录，以减少本步骤证据的非必要漂移。

## Result and Boundary

机器结果见 [`step-01-tla-toolchain.json`](results/step-01-tla-toolchain.json)。本步骤只证明官方 jar 在固定 JDK 17 上可校验、可启动，并能完整探索两档 smoke 状态空间；它不证明 [`LockTable`](../../../src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L48) 或尚未实现的 L1 协议正确。

- [`2×2`](results/step-01-tla-toolchain.json#L24)：34 个 generated states、16 个 distinct states、深度 5；
- [`3×3`](results/step-01-tla-toolchain.json#L36)：2,306 个 generated states、512 个 distinct states、深度 10；
- 两档 exit code 均为 0，refresh 下载与 offline 复用路径均通过校验。

## Commit Summary

### 完成任务

- 固定官方 TLA+ Tools v1.7.4、TLC 2.19、jar size/SHA-256、Temurin JDK 17 运行边界与本地安装位置。
- 提供跨平台、可重复、可离线复验的 CLI，并用 2×2/3×3 有界 smoke 配置证明工具与配置兼容。

### 工具、配置与文档改动

- [`tla/toolchain.json`](../../../tla/toolchain.json) 保存发布身份、下载 URL、SHA-256、Java 边界、安装路径和两档配置 manifest。
- [`tla.py`](../../../scripts/research/tla.py) 实现 manifest 校验、标准库下载、原子替换、size/SHA-256 验证、固定 JDK 发现、TLC 调用和状态指标解析；[`bootstrap_tla_tools.py`](../../../scripts/research/bootstrap_tla_tools.py) 提供 refresh/offline CLI。
- [`VC_L1_ToolchainSmoke.tla`](../../../tla/l1/VC_L1_ToolchainSmoke.tla) 与两份配置验证 2×2/3×3 常量、状态探索和 invariant 检查；它们不是 L1 锁协议模型。
- [`.gitignore`](../../../.gitignore) 排除下载 jar、嵌套 TLC metadata 和自动 trace；[`scripts/README.md`](../../../scripts/README.md) 与 [`tla/README.md`](../../../tla/README.md) 记录跨平台命令和证据边界。

### 测试与证据

- [`test_tla.py`](../../../scripts/tests/test_tla.py) 覆盖 manifest pin、TLC 指标解析和错误 jar 拒绝；[`test_cli.py`](../../../scripts/tests/test_cli.py#L10) 将新 CLI 纳入导入/help 矩阵。
- refresh 成功下载并验证 [`tla2tools.jar`](results/step-01-tla-toolchain.json#L9)，offline 模式复用同一制品后再次运行两档模型。
- 完整 Python 测试 19 项通过，37 份 Git 管理文档引用审计通过，Python 编译与 Git whitespace 检查通过。

### 语义影响、限制与注意事项

- 本提交不修改 VanillaCore Java、事件 schema、历史结果或锁语义；下载 jar 位于忽略目录，不进入 Git。
- 官方发布页只提供 release asset；本仓库记录的 SHA-256 是本次从官方 URL 下载后计算并固定的项目校验值，不声称是上游签名。
- smoke 状态数只证明工具链和有限配置可执行；下一步骤仍必须实现并独立验证 [`L1`](../../plan.md#l1单层-sx-strict-2pl) 状态机与 invariant。
