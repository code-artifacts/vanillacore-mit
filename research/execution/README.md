# Research Execution

本目录记录 [`../plan.md`](../plan.md) 的实际执行过程。长期设计与结论留在 [`research/`](../README.md)，可复用自动化留在 [`../../scripts/research/`](../../scripts/research/)，每周目录只保存当周计划、人工审查结果和小型 manifest。

## Layout

```text
research/execution/
├── README.md
└── week-NN/
    ├── README.md          # 步骤、状态、验证入口
    ├── step-NN-*.md       # 方法、过程、证据、结论与缺口
    ├── results/           # 小型、可审查 JSON/CSV
    └── raw/               # 完整日志与临时输出；Git 忽略
```

每一步必须满足：单一目标、可重复命令、结果文件、文档证据、局部验证、独立 commit 和独立 push。后续步骤只能引用已推送的前置结果，不能静默改写其结论。

## Weeks

- [`week-01/README.md`](week-01/README.md)：环境、基线、双构建、重复测试、deadlock skeleton 与 PR #95 witness。
- Week 02 及以后按 [`第 17 节`](../plan.md#17-立即执行清单) 继续建立同构目录。
