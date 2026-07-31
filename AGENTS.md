# Repository Guidelines

## Repository Areas

- [`src/main/java/`](src/main/java/) contains VanillaCore production code.
- [`src/test/java/`](src/test/java/) contains upstream and model-isolation test harnesses.
- [`research/`](research/README.md) contains plans, evidence, experiments, and execution records.
- [`scripts/`](scripts/README.md) contains cross-platform research automation.
- [`tla/`](tla/README.md) contains the TLA+ model hierarchy.

## Documentation Links

Every internal reference in repository documentation must be a repository-relative,
locally navigable Markdown link. This includes files, directories, source classes,
methods, fields, variables, code lines, scripts, evidence files, other documents,
and document sections. Source-symbol links should use a precise line fragment such
as [`LockTable`](src/main/java/org/vanilladb/core/storage/tx/concurrency/LockTable.java#L35).
External papers, official documentation, and issue trackers may link directly to
their authoritative URLs.

Run the documented link audit before every documentation commit:

```console
python -m scripts.research.check_document_links
```

## Plans and Progress

Store every implementation plan and progress record under [`ai/plans/`](ai/plans/README.md).
Use the timestamped naming convention defined there and update the active record
before each commit and after each push.

## Commit Summaries

Before staging any code, test, script, workflow, or configuration commit, write a
detailed pre-commit summary. If the work belongs to an execution step, keep the
summary in that step document; otherwise keep it in the active
[`ai/plans/`](ai/plans/README.md) progress record. Include the completed task,
specific code changes, validation, compatibility or semantic impact, limitations,
and follow-up concerns.

## Validation

Run the narrowest relevant tests, then:

```console
python -m unittest discover -s scripts/tests -v
python -m compileall -q scripts
git diff --check
```

Do not commit generated [`target/`](.gitignore), raw traces, caches, temporary
worktrees, credentials, or unlicensed artifacts.
