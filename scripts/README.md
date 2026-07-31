# Cross-Platform Research Scripts

[`scripts.research`](research/__init__.py#L1) provides the reproducible Week 1–3 workflows on
Windows, Linux, and macOS. The implementation uses only the Python standard
library and discovers platform-specific [`java`](https://docs.oracle.com/en/java/javase/17/docs/specs/man/java.html), [`jar`](https://docs.oracle.com/en/java/javase/17/docs/specs/man/jar.html), Maven, temporary
directories, process groups, paths, and Git worktrees at runtime.

## Requirements

- Python 3.10 or newer ([`python3`](https://docs.python.org/3/using/cmdline.html) may replace [`python`](https://docs.python.org/3/using/cmdline.html) on Unix systems).
- Git and Maven available on [`PATH`](research/common/tooling.py#L238).
- Eclipse Temurin JDK [`17.0.20+8`](../research/execution/week-01/results/step-01-environment.json#L13); set [`VANILLADB_JDK17_HOME`](research/common/tooling.py#L186) when discovery is
  ambiguous. The compatibility probe additionally needs JDK 25 through
  [`VANILLADB_JDK25_HOME`](research/common/tooling.py#L186).

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
python -m scripts.research.bootstrap_tla_tools
python -m scripts.research.check_l1_model
python -m scripts.research.check_l1_mapping
python -m scripts.research.export_l1_traces
python -m scripts.research.check_l1_self_tests
python -m scripts.research.invoke_week03_g1_stress
python -m scripts.research.measure_week03_low_sink --iteration 1 --implementation early-event-type-gating
python -m scripts.research.new_week03_gate_decision
```

Use [`--help`](#requirements) on an evidence command for output and workload overrides. Evidence
schemas and default paths remain compatible with the original workflows.

[`bootstrap_tla_tools.py`](research/bootstrap_tla_tools.py) downloads the pinned
TLA+ CLI asset declared in [`tla/toolchain.json`](../tla/toolchain.json), verifies
its size and SHA-256, and runs the 2×2 and 3×3 smoke configurations. The jar is
stored under the ignored [`.tools/`](../.gitignore) directory; use the offline
option after the first verified installation.

[`check_l1_model.py`](research/check_l1_model.py) runs the pinned TLC against
the L1 S/X safety and liveness configurations and writes bounded state counts,
depth, memory boundaries, hashes, fairness assumptions, and claim limits.

[`check_l1_mapping.py`](research/check_l1_mapping.py) validates complete action
and invariant coverage in [`mapping-v0.1.json`](../tla/l1/mapping-v0.1.json),
checks every source line and trace event type, and enforces strong-contradiction
eligibility rules.

[`export_l1_traces.py`](research/export_l1_traces.py) reruns the unsymmetrized
2×2 model with a fixed seed, hashes the ignored raw action-labelled state graph,
and deterministically extracts the eight canonical L1 trace families with final
states and full provenance.

[`check_l1_self_tests.py`](research/check_l1_self_tests.py) replays all canonical
traces, requires TLC to catch injected compatibility, strictness, and cleanup
faults, and replays the four normalized Week 2 regression fixtures. Model,
mapping, scenario-source, and summary hashes make stale fixtures fail closed.

[`invoke_week03_g1_stress.py`](research/invoke_week03_g1_stress.py) creates
isolated pristine, PR #95 reference-fix, and instrumented-pristine worktrees;
runs compatible/conflict cells at 2/4/8/16 workers with at least one million
lock operations per variant; classifies every final residue and known patch
symptom; and reruns both PR #95 differential witnesses.

[`measure_week03_low_sink.py`](research/measure_week03_low_sink.py#L13) executes
one of at most two low-sink iterations with the unchanged Week 2 completeness
and 30-sample overhead protocol. [`low_sink.py`](research/low_sink.py#L76)
retains every sample, source hash, event metric, and stop decision.

[`new_week03_gate_decision.py`](research/new_week03_gate_decision.py#L12)
combines the retained L1, G1, G2, and low-overhead evidence. The fail-closed
decision logic is in [`week3_gate.py`](research/week3_gate.py#L19).

## Documentation References

Run [`check_document_links.py`](research/check_document_links.py) from the
repository root to verify that tracked documents use navigable local links for
repository files, source lines, and sections:

```console
python -m scripts.research.check_document_links
```

## Tests

```console
python -m unittest discover -s scripts/tests -v
python -m compileall -q scripts
```
