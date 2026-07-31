# Local Validation

## Current Baseline

| Item | Value |
| --- | --- |
| Upstream source baseline | `03e1f2df49bb9664c8bdae11cf911f56b74bbc57` |
| Project compiler release | Java 17（见 [`pom.xml`](../pom.xml)） |
| Validated JDK | Eclipse Temurin 17.0.20+8 |
| Maven | 3.9.12 |
| Host | Windows 11, x86-64 |

本机同时安装了 JDK 17 与 JDK 25。项目验证必须让 `JAVA_HOME` 和当前进程 `PATH` 明确指向 JDK 17；不要仅依据系统默认 `java`。研究脚本验证 Temurin runtime `17.0.20+8` 并自动启用 `mit-research` Maven profile；该 profile 同时限制 Java 主版本为 17、供应商为 Eclipse Adoptium，不改变普通上游构建的供应商策略。

```console
python -m scripts.research.invoke_maven_jdk17 --version
python -m scripts.research.invoke_maven_jdk17 --batch-mode clean test
```

## Validation Commands

默认 Surefire 配置只包含 [`FullTestSuite.java`](../src/test/java/org/vanilladb/core/FullTestSuite.java)：

```console
mvn --batch-mode clean test
mvn --batch-mode "-Dtest=ParserTest,SpResultSetTest,ConstantRangeTest,ConstantTest,BTreeIndexConcurrentTest" test
```

当前 JDK 17 基线结果：

- 默认 suite：110 tests，0 failures，0 errors，0 skipped。
- 默认入口遗漏的五个测试类：10 tests，0 failures，0 errors，0 skipped。
- 该结果证明一次性 clean build 和现有回归通过；不证明重复调度稳定性、插桩低扰动、容器可复现性或模型 refinement。

## JDK 25 Limitation

JDK 25.0.4 可安装并用于兼容性实验，但当前不能作为构建基线。`net.smacke:jaydio:0.1` 传递依赖 `net.java.dev.jna:jna:4.0.0`；JDK 25 的 JAR 读取器拒绝该旧 JNA 文件并报告 `Invalid CEN header (invalid zip64 extra data field size)`，生产源码编译阶段即失败。JDK 17 能读取同一制品。

在升级或替换 `jaydio`/JNA 前，所有正式实验、CI 与复现实验固定 JDK 17。依赖升级应单独评估，不能与并发控制 mutation 混入同一实验变体。

可重复运行兼容性探针：

```console
python -m scripts.research.test_jdk_compatibility
```

探针、证据来源与当前结果见 [`execution/week-01/step-01-environment.md`](execution/week-01/step-01-environment.md)。

## Repetition Gate

第一周重复性门已完成：

1. 默认 suite 与补充测试各 fresh JVM ×20；
2. 每次运行使用独立 DB/log storage root，禁用自动重跑；
3. 原始基线和 [PR #95 参考补丁](evidence/patches/pr-95-fix-locktable.patch) 已分离 clean build；
4. 结果见 [`execution/week-01/step-04-repetition.md`](execution/week-01/step-04-repetition.md)。
