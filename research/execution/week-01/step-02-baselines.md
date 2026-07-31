# Step 02 — Baseline Identity

## Objective

在任何构建、补丁或测试实验前，固定研究仓库、上游源码和 PR #95 参考补丁的可机器验证身份，避免把研究基础设施变化误认为 SUT 变化。

## Method

[`new_baseline_manifest.py`](../../../scripts/research/new_baseline_manifest.py) 使用 Git object ID 与补丁内容哈希生成 [`results/step-02-baselines.json`](results/step-02-baselines.json)：

```console
python -m scripts.research.new_baseline_manifest
```

身份字段遵循以下边界：

- `repository.commit/tree`：研究基础设施所在 HEAD；
- `repository.sourceTree`：当前 [`src/`](../../../src/) 的 Git tree；
- `upstream.commit/tree/sourceTree`：固定上游 `03e1f2df49bb9664c8bdae11cf911f56b74bbc57`；
- `pomBlob`：显式记录研究 profile 使当前 POM 与上游不同；
- `patch.sha256/gitBlob/mailCommitIds`：同时覆盖文件内容、Git blob 和补丁内两个提交；
- `patch.applyCheck`：执行 `git apply --check`，只证明文本可应用，不证明修复正确。

Git object 解析与补丁 dry-run 语义分别以 [git-rev-parse](https://git-scm.com/docs/git-rev-parse) 和 [git-apply](https://git-scm.com/docs/git-apply) 为准。

## Result

| Item | Fixed value |
| --- | --- |
| Research base commit | `f34edaa1240d5f8193fc9cae64cf39ec3edcd5cd` |
| Upstream commit | `03e1f2df49bb9664c8bdae11cf911f56b74bbc57` |
| Upstream/source tree | `bbf446ad20578959e91ef2b3dd8ed72bae838940` |
| PR #95 SHA-256 | `E3C79288D13A8C8706227879DC38DB93562DAE92C4E1CBB82B0E10B8FACAD145` |
| Patch mail commits | `7b326e25508727a7f21ccbca13209dd7675d2cb0`, `e9d8174c6011750f1cd87613b5833c25ea7bf8af` |
| Patch applies | `true` |

当前 `src` tree 与上游完全一致；当前 POM 因 [`mit-research` profile](../../../pom.xml) 有意不同。后续 `VC-HEAD-20230430` 与 `VC-REF-95` 的差异只能来自记录的补丁。

## Interpretation

- **Confirmed:** 当前 SUT 源码仍是固定上游源码。
- **Confirmed:** 仓库保存的 PR #95 文件字节与此前记录哈希一致，且可应用。
- **Not established:** PR #95 是否正确、完整或无副作用；这属于步骤 3 和步骤 6。

## Confidence & Gaps

**Overall confidence:** High for identity and textual applicability.

Git tree/blob 与 SHA-256 是直接、可重复证据。尚未建立的是补丁后源码 tree、双基线构建结果和行为差分；后续步骤分别补齐。
