# Calamum Vulcan — `0.5.0` Testing and Readiness Plan

## Purpose

This document turns the Sprint 5 testing expectations into an explicit execution schedule.

It exists so `0.5.0` does not drift into the common failure mode where multiple test strategies are mentioned in passing but only one or two are actually exercised before a boundary move.

For Sprint 5, the required validation posture is intentionally multi-layered:

- **`pytest` baseline coverage** for state, reporting, GUI contract, adapters, and closeout surfaces
- **sandbox validation** from built artifacts and isolated install roots
- **scripted simulation** across supported happy and negative paths
- **empirical review** of operator-visible behavior and evidence readability
- **aggressive penetration-style validation** for archive safety, checksum drift, malformed inputs, fallback honesty, transcript boundaries, and dangerous-pattern scanning
- **package-boundary freeze validation** at the near-end boundary, with TestPyPI/PyPI rehearsal explicitly deferred to the immediate post-`0.6.0` `1.0.0` promotion lane

## Current readiness baseline as of 2026-04-22

The repo already has the core validation assets needed to open Sprint 5 with discipline:

- `pytest` is available in the permitted UNC-local `.venv-core`
- the current Sprint 5 source-tree baseline is `224 passed` under `temp/pytest_baseline_after_qt_fix.txt`
- `scripts/build_release_artifacts.py` already rebuilds `dist/` and enforces the artifact contract
- `scripts/validate_installed_artifact.py` already covers isolated installed-artifact validation in a temp root
- `scripts/run_scripted_simulation_suite.py` already proves deterministic source-vs-installed equality across the scripted matrix
- `scripts/run_empirical_review_stack.py` already captures packaged GUI screenshots and checks operator-facing evidence readability
- `scripts/run_security_validation_suite.py` plus `calamum_vulcan/validation/security.py` already provide the bounded aggressive penetration-style/security gate
- `scripts/run_testpypi_rehearsal.py` already exists as dormant promotion tooling for the later `1.0.0` lane, but it is no longer an active Sprint 5 readiness requirement

That means Sprint 5 is **operationally ready to validate**, but the package metadata boundary still needs to be landed in the repo itself before any green readiness sweep can be treated as final `0.5.0` package-ready proof.

## Working definition of the testing lanes

### 1) `pytest` baseline lane

**Goal:** catch contract regressions in the fastest repeatable source-tree lane.

**Primary command**

- `python -m pytest tests/unit -q`

**Primary proof shape**

- unit and contract regressions stay discoverable through `pytest`
- new Sprint 5 state, alignment, fallback, and closeout helpers get immediate source-tree coverage

**When this lane runs**

- every frame-stack closeout from `FS5-01` onward
- every meaningful refactor to state, reporting, adapters, or Qt shell surfaces

### 2) Sandbox lane

**Goal:** prove that the packaged artifact, not just the source tree, preserves the claimed support posture.

**Primary commands**

- `python scripts/build_release_artifacts.py`
- `python scripts/validate_installed_artifact.py`

**Primary proof shape**

- wheel/sdist contract holds
- installed entry points, evidence export, and closeout surfaces still work outside the source tree
- safe-path or fallback truth survives packaging

**When this lane runs**

- required at every stack that changes reporting, CLI, integration-bundle, package metadata, or installed-artifact behavior
- non-negotiable from `FS5-05` onward

### 3) Scripted simulation lane

**Goal:** exercise the safe-path story, blocked-path story, and installed/source parity without relying on live hardware.

**Primary command**

- `python scripts/run_scripted_simulation_suite.py`

**Primary proof shape**

- deterministic scenario coverage for no-device, ready, blocked, mismatch, failure, and resume paths
- source-root and installed-artifact results remain equal
- offscreen GUI proof and evidence export remain stable

**When this lane runs**

- required whenever Sprint 5 changes session truth, alignment gates, fallback handling, or closeout-bundle behavior
- non-negotiable from `FS5-03` onward

### 4) Empirical review lane

**Goal:** ensure the operator-facing surfaces remain understandable, readable, and honest in packaged form.

**Primary command**

- `python scripts/run_empirical_review_stack.py`

**Primary proof shape**

- packaged GUI screenshots for selected scenarios
- visible operator guidance remains readable
- blocked and failure evidence exports remain recovery-oriented
- public support posture can still be stated honestly

**When this lane runs**

- required whenever Qt shell layout, phase/gate wording, evidence readability, or operator-visible fallback/native status changes materially
- non-negotiable from `FS5-06` onward

### 5) Aggressive penetration-style lane

**Goal:** push hard on the boundaries that should fail safely or stay explicit under hostile or malformed input.

**Primary commands**

- `python -m pytest tests/unit/test_security_validation.py tests/unit/test_package_importer.py tests/unit/test_package_snapshot.py tests/unit/test_pit_contract.py -q`
- `python scripts/run_security_validation_suite.py`

**Why this is called penetration-style rather than generic security smoke**

Because this lane intentionally attacks or stress-checks the highest-risk trust boundaries:

- archive traversal
- drive-qualified paths
- symlink abuse
- checksum mismatch
- analyzed-snapshot drift
- malformed PIT traces
- dangerous Python patterns
- hidden fallback dependence
- transcript and GUI runtime-log boundary regressions

This is still a **bounded repo-owned penetration-style gate**, not a live exploit campaign against external services or hardware.

**When this lane runs**

- every stack closeout
- every time a new import, parsing, fallback, transcript, or publication boundary surface is introduced
- mandatory again in `FS5-07` and `FS5-08`

### 6) Promotion-prep lane (deferred until `1.0.0`)

**Goal:** preserve the future registry-publication rehearsal tooling without pretending that Sprint 5 must reopen TestPyPI/PyPI publication.

**Primary command**

- `python scripts/run_testpypi_rehearsal.py`

**Primary proof shape**

- dormant rehearsal template for later `1.0.0` promotion work
- reminder that registry-delivered install validation resumes only after the `0.6.0` autonomy boundary
- no effect on Sprint 5 go/no-go decisions unless the roadmap is changed again

**When this lane runs**

- not part of the active Sprint 5 readiness cadence
- reactivated in the immediate post-`0.6.0` `1.0.0` promotion lane

## Scheduled cadence by stack

| Stack    | Required test lanes                                                                    | Why                                                                                       |
| -------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `FS5-01` | `pytest`, aggressive penetration-style                                                 | foundation declarations must keep the security and contract posture explicit from day one |
| `FS5-02` | `pytest`, aggressive penetration-style, scripted simulation (targeted if needed)       | session authority changes can silently break blocked/ready semantics and fallback truth   |
| `FS5-03` | `pytest`, aggressive penetration-style, scripted simulation                            | alignment hardening must be proven on both happy and negative paths                       |
| `FS5-04` | `pytest`, aggressive penetration-style, scripted simulation                            | richer fallback identity has to remain honest under degraded or malformed adapter output  |
| `FS5-05` | `pytest`, sandbox, scripted simulation, aggressive penetration-style                   | the first bounded safe-path lane must survive packaging and adversarial review            |
| `FS5-06` | `pytest`, sandbox, scripted simulation, empirical review, aggressive penetration-style | runtime-hygiene and operator-surface changes require visible review, not just contracts   |
| `FS5-07` | all active Sprint 5 lanes, excluding the dormant registry-publication rehearsal        | candidate-level proof must be coherent before freeze                                      |
| `FS5-08` | all active Sprint 5 lanes plus final package-boundary freeze validation                | the sprint package boundary only moves when the entire active stack agrees                |

## Sprint 5 readiness orchestration surface

To keep the schedule executable, the repo now uses:

- `scripts/run_v050_readiness_stack.py`

This runner is intended to provide one repeatable local readiness slice that sequences the core Sprint 5 lanes and writes a summary under:

- `temp/fs5_readiness/`

Default readiness slice:

1. `pytest` baseline
2. aggressive penetration-style `pytest` slice
3. aggressive penetration-style shared security suite
4. build/artifact contract refresh
5. sandbox installed-artifact validation
6. scripted simulation
7. empirical review

Registry rehearsal is intentionally **not** part of the active Sprint 5 readiness slice. That lane resumes only in the immediate post-`0.6.0` `1.0.0` promotion gate.

## Expected archive roots and evidence anchors

| Lane                                  | Primary archive / proof anchor                                                                      |
| ------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `pytest` baseline                     | terminal output and readiness summary in `temp/fs5_readiness/pytest_baseline/`                      |
| aggressive penetration-style `pytest` | `temp/fs5_readiness/aggressive_penetration_pytest/`                                                 |
| aggressive penetration-style suite    | `temp/security_validation/` plus `temp/fs5_readiness/aggressive_penetration_suite/`                 |
| build/artifact contract               | `temp/fs_p02_build_artifacts/`                                                                      |
| sandbox installed-artifact            | `%TEMP%/calamum_vulcan_fs_p03_installed_artifact/` and readiness summary                            |
| scripted simulation                   | `temp/fs_p04_scripted_simulation/`                                                                  |
| empirical review                      | `temp/fs_p05_empirical_review/`                                                                     |
| TestPyPI rehearsal                    | dormant until the `1.0.0` promotion gate; existing anchor remains `temp/fs_p06_testpypi_rehearsal/` |
| Sprint 5 aggregate view               | `temp/fs5_readiness/readiness_summary.json` and `.md`                                               |

## Current status and near-term readiness call

### Ready now

- Sprint 5 can open with explicit multi-strategy testing already scheduled
- the repo has runnable lanes for `pytest`, sandbox, scripted, empirical, and aggressive penetration-style validation
- the new readiness orchestrator can be used as the standard pre-package sweep for early and mid-sprint frame stacks
- any existing `temp/fs5_readiness/readiness_summary.json` output can be used as working-reference candidate evidence
- any existing `safe-path-close` output should be treated as candidate package-ready evidence until version and package metadata align to a real `0.5.0` candidate

### Not fully ready yet

- the local authority docs and checklist must stay aligned with the now-green readiness proof so audits do not report stale planning drift
- the local repo state still does not match a real `0.5.0` boundary: `pyproject.toml` remains at `0.4.0`, and a local `v0.5.0` tag is not present
- git/tag/release-object seal-boundary actions remain intentionally separate from the local package-boundary proof and still require explicit maintainer timing and approval
- renewed TestPyPI/PyPI publication remains deferred to the immediate post-`0.6.0` `1.0.0` promotion lane

## Readiness rule for implementation start

Sprint 5 implementation should proceed only if:

- the permitted `.venv-core` runtime is active
- the `pytest` baseline and aggressive penetration-style lane are runnable on demand
- artifact rebuild plus sandbox validation can be refreshed whenever packaging-sensitive surfaces change
- scripted simulation and empirical review remain scheduled, not deferred to the very end

That condition is currently satisfied.

## Readiness rule for package-boundary movement

Sprint 5 should **not** move the `0.5.0` package boundary unless:

- the readiness orchestrator has gone green for the candidate or the equivalent per-lane evidence exists
- the `safe-path-close` bundle is implemented and validated
- the package-only closeout wording, versioning, hashes, and carry-forward notes all agree on the exact candidate boundary

Renewed TestPyPI/PyPI publication is intentionally deferred and is therefore **not** a Sprint 5 readiness blocker. The package-boundary condition above is **not yet satisfied for the actual local repo state** because `pyproject.toml` still reports `0.4.0`. Any green readiness outputs should therefore be treated as pre-package candidate evidence until the repo lands the matching Sprint 5 package metadata boundary.
