# Week 01 Execution

目标：关闭 [`第 17 节`](../../plan.md#17-立即执行清单) 第一周的六项可行性前置条件。每项完成后独立提交并推送。

| Step | Deliverable | Status |
| --- | --- | --- |
| 1 | 固定 Temurin JDK 17；记录 JDK 25 限制 | Complete |
| 2 | 固定仓库、上游与 PR #95 身份 | Complete |
| 3 | 原始/PR #95 双基线 clean build | Complete |
| 4 | fresh JVM ×20 与遗漏测试 | Complete |
| 5 | deadlock TODO issue/test skeleton | Complete |
| 6 | PR #95 两个最小失败见证 | Complete |

## Step Records

- [`step-01-environment.md`](step-01-environment.md)
- [`step-02-baselines.md`](step-02-baselines.md)
- [`step-03-dual-build.md`](step-03-dual-build.md)
- [`step-04-repetition.md`](step-04-repetition.md)
- [`step-05-deadlock-skeleton.md`](step-05-deadlock-skeleton.md)
- [`step-06-pr95-witnesses.md`](step-06-pr95-witnesses.md)

## Shared Commands

```console
python -m scripts.research.invoke_maven_jdk17 --version
python -m scripts.research.test_jdk_compatibility
```

原始运行日志写入 [`.gitignore` 所定义的 `raw/`](../../../.gitignore#L44)，不进入 Git；经过人工核对的小型结果写入 [`results/`](results/)。
