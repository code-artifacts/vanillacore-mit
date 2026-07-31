"""Run Maven with the pinned Temurin JDK 17 research toolchain."""

from __future__ import annotations

import sys

from .common.cli import execute
from .common.tooling import repository_root, require_research_jdk17, run_maven


def main(arguments: list[str] | None = None) -> int:
    maven_arguments = list(arguments if arguments is not None else sys.argv[1:])
    if not maven_arguments:
        maven_arguments = ["--batch-mode", "verify"]

    def run() -> None:
        jdk = require_research_jdk17()
        print(
            f"Using {jdk['Vendor']} JDK {jdk['RuntimeVersion']} at {jdk['Home']}",
            file=sys.stderr,
        )
        result = run_maven(repository_root(), maven_arguments, jdk=jdk)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

    return execute(run)


if __name__ == "__main__":
    raise SystemExit(main())
