# Cross-Platform Research Scripts

`scripts.research` provides the reproducible Week 1 and Week 2 workflows on
Windows, Linux, and macOS. The implementation uses only the Python standard
library and discovers platform-specific `java`, `jar`, Maven, temporary
directories, process groups, paths, and Git worktrees at runtime.

## Requirements

- Python 3.10 or newer (`python3` may replace `python` on Unix systems).
- Git and Maven available on `PATH`.
- Eclipse Temurin JDK `17.0.20+8`; set `VANILLADB_JDK17_HOME` when discovery is
  ambiguous. The compatibility probe additionally needs JDK 25 through
  `VANILLADB_JDK25_HOME`.

Run modules from the repository root:

```console
python -m scripts.research.invoke_maven_jdk17 --batch-mode clean test
python -m scripts.research.test_jdk_compatibility
python -m scripts.research.new_baseline_manifest
python -m scripts.research.invoke_dual_baseline_build
python -m scripts.research.invoke_repetition_campaign --repetitions 20
python -m scripts.research.invoke_pr95_witness_matrix
python -m scripts.research.invoke_week02_event_sink_validation
python -m scripts.research.invoke_week02_instrumentation_validation
python -m scripts.research.invoke_week02_direct_harness_validation
python -m scripts.research.invoke_week02_scenario_replay --repetitions 20
python -m scripts.research.measure_week02_trace_quality
python -m scripts.research.new_week02_gate_decision
```

Use `--help` on an evidence command for output and workload overrides. Evidence
schemas and default paths remain compatible with the original workflows.

## Tests

```console
python -m unittest discover -s scripts/tests -v
python -m compileall -q scripts
```
