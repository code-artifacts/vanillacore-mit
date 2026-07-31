# Plans and Progress Records

<a id="naming"></a>
## Naming

Create one Markdown record for every implementation plan. Name it
[`YYYYMMDD-HHmm-主题.md`](#naming), using the local start time to minute precision.
Keep all progress updates for that implementation in the same file.

## Required Contents

Each record must contain:

1. the objective, scope, assumptions, and ordered implementation steps;
2. validation commands and acceptance criteria;
3. a detailed pre-commit summary written before staging each code or tooling
   commit;
4. commit identifiers, push verification, and any remaining risks recorded after
   each push.

The repository-wide requirements are defined in [`AGENTS.md`](../../AGENTS.md).

## Pre-Commit Summary Template

```markdown
## Pre-Commit Summary — <subject>

- Task completed:
- Code and document changes:
- Tests and evidence:
- Compatibility or semantic impact:
- Limitations and follow-up:
```
