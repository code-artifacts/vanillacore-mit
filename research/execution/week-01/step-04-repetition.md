# Step 04 — Fresh-JVM Repetition

## Objective

验证关键默认回归和默认 Surefire 入口遗漏的五个测试类在重复 fresh JVM 中稳定，并消除数据库目录复用与 Surefire 自动重跑对结果的混淆。

## Method

[`invoke_repetition_campaign.py`](../../../scripts/research/invoke_repetition_campaign.py) 顺序执行两个 campaign：

| Campaign | Selector | Repetitions | Expected per run |
| --- | --- | ---: | ---: |
| `default-suite` | `FullTestSuite` | 20 | 110 |
| `omitted-five` | `ParserTest,SpResultSetTest,ConstantRangeTest,ConstantTest,BTreeIndexConcurrentTest` | 20 | 10 |

每个 repetition 都启动新的 Maven 进程，使用 `forkCount=1`、`reuseForks=false`、`rerunFailingTestsCount=0`，并生成独立 VanillaCore storage root 和配置文件。Surefire 的 `test` 用户属性会选择指定类；fork 语义依据 [Surefire 2.22.2 test mojo](https://maven.apache.org/components/surefire-archives/surefire-2.22.2/maven-surefire-plugin/test-mojo.html) 与 [fork options](https://maven.apache.org/surefire-archives/surefire-2.22.2/maven-surefire-plugin/examples/fork-options-and-parallel-execution.html)。

当前 [`FileMgr.java`](../../../src/main/java/org/vanilladb/core/storage/file/FileMgr.java) 只创建 DB 目录，不单独创建 log 目录；因此同一 repetition 的 `DB_FILES_DIR` 与 `LOG_FILES_DIR` 指向同一个隔离 storage root。不同 repetition 仍完全分离，且不会回退到 `user.home`。

```console
python -m scripts.research.invoke_repetition_campaign --repetitions 20
```

每次运行后立即读取 Surefire XML；raw log、配置和数据库写入 Git 忽略目录，SHA-256 与测试计数写入跟踪的逐运行 CSV。

## Result

- 汇总：[`results/step-04-repetition-summary.json`](results/step-04-repetition-summary.json)
- 40 次逐运行证据：[`results/step-04-runs.csv`](results/step-04-runs.csv)

| Campaign | Pass | Fail/Error/Timeout |
| --- | ---: | ---: |
| Default suite | 20/20 | 0 |
| Omitted five | 20/20 | 0 |

总计 40 个 fresh Maven 进程；默认 suite 执行 2,200 tests，遗漏 bundle 执行 200 tests，无 failure、error、skip 或 timeout。

## Interpretation

- **Confirmed:** 当前主分支在固定 Temurin JDK 17 下通过第一周重复性门槛。
- **Confirmed:** `BTreeIndexConcurrentTest` 等五类确实不应依赖默认 suite 间接覆盖，现已显式重复执行。
- **Not established:** 测试通过不证明 PR #95 风险不存在；现有 suite 缺少相关内部状态 oracle。
- **Not established:** 本轮为单机顺序运行，不代表不同 CPU、Linux 或容器中的稳定性。

## Confidence & Gaps

**Overall confidence:** High for this host and exact test configuration.

证据包含每个独立进程的测试计数、退出码、耗时、配置和日志 hash。跨平台重复、随机化顺序和资源压力属于后续稳定性研究，不阻塞第一周。
