# Experiment Layout

实验资产按“定义可跟踪、运行可再生、大输出不入库”组织。

```text
research/experiments/
├── manifests/          # YAML/JSON 实验定义与运行身份
├── reducers/           # 缩减器配置和最小反例
├── reports/            # 人工审查的 Markdown/CSV 结果
├── raw/                # 原始事件流；Git 忽略
├── normalized/         # 归一化 trace；Git 忽略
└── work/               # 临时数据库、TLC 导出和重放状态；Git 忽略
```

目录按需要创建；[`.gitignore`](../../.gitignore) 还排除 `reports/generated/`。

## Naming

- 运行：`run-YYYYMMDD-<layer>-<workload>-<seed>`，例如 `run-20260810-l1-sx-0042`。
- mutation：`VC-MUT-<family>-NNN`，例如 `VC-MUT-COMPAT-001`。
- 模型：遵循 [`../../tla/README.md`](../../tla/README.md) 的 `VC_<layer>_<scope>` 命名。
- 最小反例：`<run-id>-min.{json,md}`，同时引用原始 run 和 reducer 版本。

## Required Manifest

至少记录：

```text
experiment_id, git_commit, upstream_commit, patch_set_hash
model_commit, mapping_version, trace_schema_version, scheduler_version
mutation_id, jdk_vendor_and_version, maven_version, os_or_container_digest
cpu_count, timeout_config, database_directory, seed
```

manifest 中的路径使用仓库相对路径。人工报告必须链接 manifest、缩减 trace、[`../../tla/`](../../tla/) 模型以及 [`../../src/`](../../src/) 源码位置。

## Reproducibility

每个变体使用 fresh JVM 和独立数据库目录。先保存 strict schedule，再尝试 partial-order 与低插桩重放；无法重放的结果标记为 `inconclusive`，不计为实现缺陷。统计、对照组和停止条件见 [`../plan.md`](../plan.md)。
