# Week 01 Execution

目标：关闭 [`../../plan.md`](../../plan.md) 第 17 节第一周的六项可行性前置条件。每项完成后独立提交并推送。

| Step | Deliverable | Status |
| --- | --- | --- |
| 1 | 固定 Temurin JDK 17；记录 JDK 25 限制 | Complete |
| 2 | 固定仓库、上游与 PR #95 身份 | Complete |
| 3 | 原始/PR #95 双基线 clean build | Pending |
| 4 | fresh JVM ×20 与遗漏测试 | Pending |
| 5 | deadlock TODO issue/test skeleton | Pending |
| 6 | PR #95 两个最小失败见证 | Pending |

## Step Records

- [`step-01-environment.md`](step-01-environment.md)
- [`step-02-baselines.md`](step-02-baselines.md)
- Step 03–06 文档在对应步骤实施时创建，避免预先搭建无内容文件。

## Shared Commands

```powershell
.\scripts\research\Invoke-MavenJdk17.ps1 --version
.\scripts\research\Test-JdkCompatibility.ps1
```

原始运行日志写入 `raw/`，不进入 Git；经过人工核对的小型结果写入 [`results/`](results/)。
