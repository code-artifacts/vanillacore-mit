# Step 01 — Temurin JDK 17 Baseline

## Objective

让研究构建不受调用者默认 `PATH` 影响：所有正式构建固定 Eclipse Temurin JDK 17，并把 JDK 25 仅作为显式兼容性探针。

## Methodology

**Research period:** July 2026

**Mode:** Standard

**Queries used:**

- `site:bugs.openjdk.org "Invalid CEN header (invalid zip64 extra data field size)"`
- `site:maven.apache.org enforcer requireJavaVersion`
- `site:maven.apache.org enforcer requireJavaVendor`
- `repo.maven.apache.org net.smacke jaydio 0.1`

**Filters applied:**

- Java/Maven 行为只使用 OpenJDK、Apache Maven 和 Maven Central 一手资料。
- 本机结论必须由可重复命令和 [`results/step-01-environment.json`](results/step-01-environment.json) 支撑。
- 不把“JDK 25 构建失败”外推为 VanillaCore 源码不兼容；先隔离到具体制品。

**Known limitations before synthesis:**

- 当前只验证 Windows 11 x86-64。
- 没有评估升级 `jaydio`、排除 JNA 或重打包旧 JAR 的兼容性。

## Implementation

1. [`pom.xml`](../../../pom.xml) 的 `mit-research` profile 使用 Maven Enforcer 3.6.3，要求 Java `[17,18)` 且 `java.vendor` 精确为 `Eclipse Adoptium`；普通上游构建不被供应商规则污染。
2. [`Invoke-MavenJdk17.ps1`](../../../scripts/research/Invoke-MavenJdk17.ps1) 从显式环境变量、注册表或标准安装目录解析 JDK 17，验证 runtime 精确为 `17.0.20+8`，在子进程范围设置 `JAVA_HOME/PATH` 并强制启用研究 profile。
3. [`Test-JdkCompatibility.ps1`](../../../scripts/research/Test-JdkCompatibility.ps1) 让 JDK 17/25 分别读取同一 JNA 4.0.0 JAR，并让 JDK 25 执行一次跳过 Enforcer 的 compile probe。

```powershell
.\scripts\research\Invoke-MavenJdk17.ps1 --version
.\scripts\research\Test-JdkCompatibility.ps1
```

## Evidence

| Claim | Status | Evidence | Quality / limitation |
| --- | --- | --- | --- |
| Compiler `release` 约束不是 JDK 选择器 | Confirmed | [Compiler Plugin: set release](https://maven.apache.org/plugins/maven-compiler-plugin/examples/set-compiler-release.html) | Apache Maven 官方文档 |
| Maven 可强制 Java 版本范围 | Confirmed | [Require Java Version](https://maven.apache.org/enforcer/enforcer-rules/requireJavaVersion.html) | Apache Maven 官方文档 |
| Maven 可按完整 vendor 名强制供应商 | Confirmed | [Require Java Vendor](https://maven.apache.org/enforcer/enforcer-rules/requireJavaVendor.html) | Apache Maven 官方文档 |
| JDK 22+ 增加 ZIP64 extra-header 校验 | Confirmed | [JDK-8314891](https://bugs.openjdk.org/browse/JDK-8314891) | OpenJDK issue；解释机制，不替代本机复现 |
| 旧 JAR 可触发相同 javac 错误，禁用一个 ZipFile 检查仍可能不足 | Confirmed | [JDK-8363985](https://bugs.openjdk.org/browse/JDK-8363985) | OpenJDK issue；对象不是 JNA |
| `jaydio:0.1` 是 2014 年制品 | Confirmed | [Maven Central directory](https://repo1.maven.org/maven2/net/smacke/jaydio/0.1/) | Maven Central 元数据 |
| 本项目传递解析到 `jna:4.0.0` | Confirmed | `mvn dependency:tree` 与 [`pom.xml`](../../../pom.xml) | 当前仓库/解析环境 |
| 同一 JNA JAR：JDK 17 可读、JDK 25 拒绝 | Confirmed | [`results/step-01-environment.json`](results/step-01-environment.json) | 当前主机，可重复 |

## Findings

- 正式基线固定 Temurin 17.0.20+8；Maven 3.9.12。
- JNA 文件 SHA-256 固定为结果 JSON 中的值，JDK 17 `jar tf` 成功。
- JDK 25.0.4 对同一文件报告 `Invalid CEN header (invalid zip64 extra data field size)`；跳过 Enforcer 后 Maven compile 同样失败。
- 因此 JDK 25 限制属于当前依赖制品/ZIP64 校验边界，而不是并发控制实验结果。依赖升级必须成为独立变体。
- `jdk.util.zip.disableZip64ExtraFieldValidation` 只适合作为诊断；[JDK-8328267](https://bugs.openjdk.org/browse/JDK-8328267) 与 [JDK-8363985](https://bugs.openjdk.org/browse/JDK-8363985) 显示 ZipFS/javac 路径仍可能拒绝旧制品。

## Source Inventory

除上表来源外，本轮还审查了：

- [Maven Toolchains guide](https://maven.apache.org/guides/mini/guide-using-toolchains)：说明 toolchain 可让 compiler、Surefire 等插件使用不同于 Maven 进程的 JDK；本步骤不提交机器相关 `toolchains.xml`。
- [Maven Wrapper](https://maven.apache.org/tools/wrapper/index.html)：后续若需固定 Maven 分发版可采用；第一周只记录本机 Maven 3.9.12。
- [JDK-8314677](https://bugs.openjdk.org/browse/JDK-8314677)：旧 ZIP64 校验曾影响部分 17.0.8 版本，支持记录完整 runtime build，而非只记主版本。
- [JDK-8313765](https://bugs.openjdk.org/browse/JDK-8313765)：列出可触发 CEN ZIP64 错误的历史制品生成问题。
- [Oracle JDK 20 release notes](https://www.oracle.com/java/technologies/javase/20all-relnotes.html)：记录 ZipFile 校验开关及其边界。
- [JNA 4.0.0 Maven Central directory](https://repo1.maven.org/maven2/net/java/dev/jna/jna/4.0.0/)：固定被测制品版本和发布时间。
- [JEP 472](https://openjdk.org/jeps/472) 与 [JDK 25 migration guide](https://docs.oracle.com/en/java/javase/25/migrate/migrating-jdk-8-later-jdk-releases.html)：说明即使修复 JAR 格式，旧 JNA 在更高 JDK 上仍需独立评估 native-access 行为。

## Confidence & Gaps

**Overall confidence:** High for this machine and dependency graph.

最强证据是同一 JAR 的双 JDK 对照和 Maven compile probe。缺口是 Linux/container 重放及替代依赖评估；它们不阻塞第一周 JDK 17 基线，但进入跨平台 artifact 前必须补齐。
