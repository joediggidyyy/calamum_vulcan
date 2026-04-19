# Calamum Vulcan — `0.1.0` Execution Evidence

## Purpose

This is the compact evidence surface for Sprint `0.1.0`.

It records what each frame stack actually established, what was validated, what remains stubbed, and what debt is intentionally carried forward.

## Active authority set

| Surface                                                               | Role                                                    |
| --------------------------------------------------------------------- | ------------------------------------------------------- |
| `Samsung_Android_Flashing_Platform_Research_Report_and_Build_Plan.md` | roadmap and six-sprint release ladder                   |
| `Samsung_Android_Flashing_Platform_0.1.0_Detailed_Planning.md`        | Sprint `0.1.0` execution shell and frame-stack contract |
| `Samsung_Android_Flashing_Platform_0.1.0_Execution_Evidence.md`       | compact execution evidence and validation ledger        |

## Stack register

| Stack   | Status    | Date       | Result                                                                                                                                                           |
| ------- | --------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `FS-01` | completed | 2026-04-16 | bounds, execution posture, validation ritual, evidence surface, and policy alignment pinned                                                                      |
| `FS-02` | completed | 2026-04-17 | implementation root pinned, state contract coded, fixtures added, and unit validation passed                                                                     |
| `FS-03` | completed | 2026-04-17 | Qt shell scaffold implemented, fixture-driven GUI binding added, and offscreen sandbox launch succeeded                                                          |
| `FS-04` | completed | 2026-04-17 | preflight rule engine implemented, shell gate semantics bound, and blocked/warn/ready scenarios validated                                                        |
| `FS-05` | completed | 2026-04-18 | typed manifest parsing, manifest-driven shell/preflight binding, matched/mismatched/incomplete validation, and centralized package-aware launcher flow completed |
| `FS-06` | completed | 2026-04-18 | structured session evidence contract, shell evidence binding, CLI export path, and reporting validation bundle completed                                         |
| `FS-07` | completed | 2026-04-18 | Heimdall adapter seam, normalized transport evidence, adapter-backed walkthroughs, and shell/reporting transport binding completed                               |
| `FS-08` | completed | 2026-04-18 | sprint-close integration bundle, `.venv-core` GUI validation, and release-close evidence completed                                                               |

## FS-01 — Foundation declarations and execution bounds

### Stack goal

Start Sprint `0.1.0` with clear implementation boundaries so later stacks can execute without re-litigating scope, trust surfaces, or validation cadence.

### Frame 1 — Boundaries and non-goals pinned

**Result:** completed

Confirmed for `0.1.0`:

- the release is still a **GUI-first product shell**
- Heimdall remains a **wrapped runtime dependency**, not a hidden permanent center of gravity
- the sprint must deliver the platform-owned surfaces for **state**, **preflight**, **package awareness**, **evidence**, and the **adapter seam**
- the sprint does **not** claim native Samsung transport autonomy
- the sprint does **not** expand to multi-vendor support, full repartition workflows, or a broad production device matrix

Execution order remains:

1. `FS-01` foundation declarations and bounds
2. `FS-02` platform state and orchestration contract
3. `FS-03` GUI shell skeleton and control-deck layout
4. `FS-04` preflight board and gating model
5. `FS-05` package-awareness surface and flash-plan preview
6. `FS-06` evidence, logging, and report contract
7. `FS-07` Heimdall adapter seam and event normalization
8. `FS-08` integration pass and release-close evidence

### Frame 2 — Near-term host/tool posture and logical seams pinned

**Result:** completed

Chosen `0.1.0` execution posture:

- **Qt 6 desktop shell remains the mandatory host surface**
- the first implementation passes should be **fixture-first and adapter-late**
- Heimdall interaction stays behind a **process-boundary adapter seam** until the sprint reaches `FS-07`
- package, state, preflight, and reporting contracts must be able to run against fixtures before any live-device dependence is introduced
- live-device or destructive flashing is **not required** to close `0.1.0`

Logical module map for the upcoming implementation root:

| Logical area         | Responsibility                                                     |
| -------------------- | ------------------------------------------------------------------ |
| `app/`               | desktop shell, panel layout, operator-visible state presentation   |
| `domain/state/`      | state vocabulary, transitions, guards, event model                 |
| `domain/preflight/`  | preflight checks, gating severity, readiness rules                 |
| `domain/package/`    | package summary, compatibility model, flash-plan preview inputs    |
| `domain/reporting/`  | session evidence model, export schema, decision trace              |
| `adapters/heimdall/` | command construction, invocation boundary, event normalization     |
| `fixtures/`          | package, device, state, and backend scenario fixtures              |
| `tests/unit/`        | deterministic logic tests for state, preflight, package, reporting |
| `tests/sandbox/`     | GUI/manual walkthrough scenarios and adapter sandbox notes         |

Ownership seam rule:

- GUI surfaces may consume **platform-owned state and evidence**, but may not speak raw Heimdall output directly.

### Frame 3 — Validation ritual pinned

**Result:** completed

Binding validation ritual for each remaining stack:

1. run the narrowest meaningful automated validation set for the touched surface
2. run a sandbox or manual walkthrough against fixtures or mocked scenarios
3. record what was **proven**, what was **stubbed**, and what remains **carry-forward debt**
4. do not open the next stack until the current stack has a compact evidence entry

Validation expectations by surface type:

| Surface type                       | Expected validation style                                                              |
| ---------------------------------- | -------------------------------------------------------------------------------------- |
| pure state / rules / mapping logic | targeted unit tests (`pytest`-or-equivalent for the chosen implementation root)        |
| GUI shell and panel behavior       | fixture-driven sandbox walkthrough plus narrow widget/view-model tests where available |
| adapter behavior                   | mocked invocation tests plus normalized-event assertions                               |
| sprint-close integration           | end-to-end sandbox scenarios across happy-path and blocked/failure flows               |

Safety/testing constraint:

- `0.1.0` does **not** require live destructive flashing to count as validated
- if any live-device test occurs, it must remain sacrificial-device-only and produce evidence notes

### Frame 4 — Evidence surface established

**Result:** completed

This file is now the compact evidence surface promised by the sprint shell.

Each future stack entry should record:

- date
- touched surfaces
- automated validation run
- sandbox/manual validation run
- proven behavior
- stubbed behavior
- carry-forward debt
- any policy or safety questions surfaced during the stack

### Frame 5 — Contract review against policy and roadmap

**Result:** completed

Short alignment review outcome:

| Check                                               | Result |
| --------------------------------------------------- | ------ |
| six-sprint ladder preserved                         | yes    |
| `0.1.0` still framed as wrapped Heimdall dependence | yes    |
| GUI remains mandatory primary surface               | yes    |
| safe-by-default posture preserved                   | yes    |
| active corpus kept minimal                          | yes    |
| no false autonomy claim introduced                  | yes    |

Policy-aligned reminders carried forward:

- use evidence over assertion
- preserve the adapter seam
- keep the active authority set lean
- treat destructive flows as UX and policy problems, not just backend problems
- scan test surfaces before implementation, not after

## Validation record for FS-01

| Validation type                            | Outcome |
| ------------------------------------------ | ------- |
| planning-surface review                    | passed  |
| stack-to-sprint contract consistency check | passed  |
| active-authority-surface review            | passed  |
| markdown/editor validation                 | passed  |

## Proven vs stubbed after FS-01

### Proven

- the `0.1.0` sprint now has a concrete frame-stack execution order
- the first active evidence surface exists
- the implementation posture is constrained tightly enough to begin `FS-02`
- the validation ritual is explicit rather than implied

### Stubbed / deferred

- no implementation root has been scaffolded yet
- no runtime language-specific harness has been committed yet
- no state reducer/store has been implemented yet
- no GUI shell has been scaffolded yet

## Carry-forward debt into FS-02

- pin the exact implementation-root location when execution moves from planning into code
- convert the logical module map into actual project surfaces only when `FS-02` begins
- keep fixture-first execution discipline so GUI and domain logic do not become adapter-bound too early
- ensure state vocabulary chosen in `FS-02` matches the blocked/warn/ready semantics already committed in planning

## FS-02 — Platform state model and orchestration contract

### Stack goal

Move the sprint from planning-only state language to a platform-owned, fixture-validated contract that later GUI surfaces can consume without raw backend leakage.

### Frame 1 — State vocabulary, guards, and implementation root pinned

**Result:** completed

Pinned implementation root:

- `calamum_vulcan/`

Created the first concrete implementation surfaces:

| Surface                        | Purpose                                                                            |
| ------------------------------ | ---------------------------------------------------------------------------------- |
| `calamum_vulcan/app/`          | reserved GUI shell anchor for `FS-03`                                              |
| `calamum_vulcan/domain/state/` | session phases, event vocabulary, immutable session model, and pure reducer logic  |
| `calamum_vulcan/fixtures/`     | representative happy, blocked, resume-needed, failure, and package-first scenarios |
| `tests/unit/`                  | deterministic validation for the state contract                                    |

The state contract now exists in code rather than prose through:

- `SessionPhase`
- `SessionEventType`
- `GuardState`
- `PlatformEvent`
- `PlatformSession`
- `TransitionRejected`

### Frame 2 — First immutable state contract implemented

**Result:** completed

Implemented a pure, immutable state layer in:

- `calamum_vulcan/domain/state/model.py`
- `calamum_vulcan/domain/state/reducer.py`

Contract decisions now encoded:

- the top-level session phase is operator-visible and GUI-ready
- readiness is guard-based, not inferred from ad hoc strings
- the reducer remains backend-agnostic and introduces no Heimdall coupling
- the session snapshot is immutable so fixtures and later GUI bindings stay deterministic

### Frame 3 — Transition rules for happy, blocked, failed, and pause/resume flows encoded

**Result:** completed

The reducer now enforces the main `0.1.0` transition rules:

- execution cannot start outside `ready_to_execute`
- readiness requires a device, a package, completed preflight, warning acknowledgement, and destructive acknowledgement when the package risk requires it
- blocked preflight remains first-class rather than collapsing into a generic failure
- pause/resume is modeled explicitly through `resume_needed`
- transport failure is normalized into `failed` with a captured reason
- package-first operator flow is allowed so the GUI can support early package inspection before device arrival

### Frame 4 — Fixtures and tests added

**Result:** completed

Added representative fixtures in `calamum_vulcan/fixtures/state_scenarios.py` and the first unit-test suite in `tests/unit/test_state_contract.py`.

Scenario coverage now includes:

- destructive happy path
- blocked validation path
- blocked-then-cleared recovery path
- resume-needed path
- execution failure path
- package-before-device path

Governance note:

- no new third-party dependency was introduced for `FS-02`; the stack uses the Python standard library only

### Frame 5 — Validation run and review

**Result:** completed

Automated validation run:

- `python -m unittest discover -s "tests/unit" -p "test_*.py"`
- result: `Ran 6 tests in 0.003s` / `OK`
- interpreter surface used by the workspace terminal during this historical pass: legacy development virtual environment (Vulcan now standardizes on `.venv-core`)

Fixture walkthrough evidence:

- `happy: completed`
- `blocked: validation_blocked`
- `resume: completed`

Review outcome:

- the state layer is now trustworthy enough for the GUI shell to bind against in `FS-03`
- the implementation stayed fixture-first and adapter-late as required by `FS-01`
- no false autonomy claim was introduced; Heimdall remains out of the runtime path at this stack

## Validation record for FS-02

| Validation type             | Outcome |
| --------------------------- | ------- |
| unit-test run               | passed  |
| fixture replay walkthrough  | passed  |
| static/editor validation    | passed  |
| governance alignment review | passed  |

## Proven vs stubbed after FS-02

### Proven

- `Calamum Vulcan` now has a real implementation root in the sprint workspace
- the operator-visible state vocabulary is pinned in code
- transition logic for happy, blocked, failed, and resume-needed paths is deterministic and test-backed
- fixture-driven state replay exists for later GUI binding work

### Stubbed / deferred

- no GUI shell has been scaffolded yet
- no preflight rule engine beyond the state contract has been implemented yet
- no package parsing or manifest normalization layer has been implemented yet
- no Heimdall adapter surface has been introduced yet

## Carry-forward debt into FS-03

- scaffold the Qt 6 shell against the existing immutable session snapshot rather than inventing parallel UI state
- preserve the `SessionPhase` vocabulary exactly unless a new evidence-backed change is required
- keep GUI panels bound to fixtures first before any live transport or device dependence is introduced
- create the visual control-deck, panel map, and status-pill system without leaking backend language into the operator surface

## FS-03 — GUI shell skeleton and control-deck layout

### Stack goal

Create the first real Calamum Vulcan desktop shell and bind it to the existing immutable session contract so the product is visibly its own operations console before transport or package implementation deepens.

### Frame 1 — Panel map, shell zones, and control-deck contract pinned

**Result:** completed

Pinned the initial FS-03 shell contract around five dashboard panels plus one dedicated right-side control deck:

| Surface            | Role                                                           |
| ------------------ | -------------------------------------------------------------- |
| `Device Identity`  | current hardware identity and mode surface                     |
| `Preflight Board`  | trust gate status, acknowledgements, and blocking notes        |
| `Package Summary`  | package identity, risk, and staging posture                    |
| `Transport State`  | execution/resume/failure normalization without backend leakage |
| `Session Evidence` | early report/export territory and decision-trace placeholder   |
| `Control Deck`     | operator action lane with visually separated execute surface   |

The shell now preserves the planning contract that dangerous actions must remain visually distinct and that raw backend language must not become the UI vocabulary.

### Frame 2 — Shell scaffold and runtime boundary implemented

**Result:** completed

Implemented the first GUI shell surfaces in:

- `calamum_vulcan/app/view_models.py`
- `calamum_vulcan/app/style.py`
- `calamum_vulcan/app/qt_compat.py`
- `calamum_vulcan/app/qt_shell.py`
- `calamum_vulcan/app/__main__.py`
- `calamum_vulcan/launch_shell.py`

Implementation decisions now encoded:

- the GUI shell is driven by a `ShellViewModel` derived directly from `PlatformSession`
- Qt runtime use is optional at import time, so test and CLI surfaces remain usable even when the binding is absent
- the project now declares its local GUI dependency in `calamum_vulcan/requirements.txt`
- the script-first launcher keeps the shell runnable from the standalone repo root without extra path shims

### Frame 3 — Empty-state and early-state panels rendered

**Result:** completed

The shell now renders coherent empty and early operational states rather than requiring live transport integration first.

Covered UI behaviors include:

- no-device shell still shows panel structure and operator next actions
- blocked validation shell surfaces mismatch notes visibly in the preflight board
- package-first and ready-to-execute states keep package truth visible before execution begins
- the control deck keeps `Execute flash plan` spatially and visually separated from ordinary controls
- the log pane remains console-like for technical trust without letting raw backend text drive the rest of the layout

### Frame 4 — Fixture-driven state binding completed

**Result:** completed

Bound the shell to named fixture scenarios through:

- `ready`
- `blocked`
- `happy`
- `resume`
- `failure`
- `package-first`

This gives the GUI shell stable scenario coverage before any live device or backend work begins.

The shell binding remained faithful to the state layer from `FS-02`:

- no parallel UI-only state model was introduced
- `SessionPhase` remains the operator-visible state backbone
- panel content, pills, actions, and log lines are all derived from the immutable session snapshot

### Frame 5 — Validation run and sandbox review

**Result:** completed

Automated validation run after PySide6 installation:

- `python -m unittest discover -s "tests/unit" -p "test_*.py"`
- result: `Ran 12 tests in 0.054s` / `OK`

Shell-launch validation from the release root:

- `python "calamum_vulcan/launch_shell.py" --scenario ready --describe-only`
- result: printed the expected panel map and enabled-action summary

Offscreen sandbox review:

- `QT_QPA_PLATFORM=offscreen` launch of `calamum_vulcan/launch_shell.py --scenario ready --duration-ms 250`
- result: shell launched and exited cleanly after timed review while preserving the expected panel map and control-deck summary

Packaging/runtime notes surfaced during sandbox review:

- Qt emitted a font-directory warning because the active environment does not yet bundle fonts for deployment
- the offscreen plugin emitted `This plugin does not support propagateSizeHints()` during the timed sandbox run
- neither notice blocked shell launch or test completion, but font packaging should be handled before broader distribution work

## Validation record for FS-03

| Validation type               | Outcome |
| ----------------------------- | ------- |
| view-model unit tests         | passed  |
| Qt shell contract test        | passed  |
| workspace-root launcher check | passed  |
| offscreen sandbox launch      | passed  |

## Proven vs stubbed after FS-03

### Proven

- Calamum Vulcan now has a real desktop shell scaffold rather than a placeholder app directory
- the GUI binds to the existing immutable session contract without creating parallel UI state
- the panel map, status-pill system, control deck, and operational log pane are all rendered from fixture-backed state
- the shell is runnable from the release root through a dedicated launcher script

### Stubbed / deferred

- control-deck actions are still non-operative UI surfaces rather than wired commands
- preflight board content remains state-driven rather than rule-engine-driven
- package summary remains a shell contract rather than a parsed manifest surface
- session evidence is still a visible placeholder ahead of FS-06 export/report wiring

## Carry-forward debt into FS-04

- extend the preflight board from state-only messaging into actual rule categories and severities
- preserve the current panel map while wiring genuine pass/warn/block semantics into the shell
- decide how driver, cable, battery, and product-code checks will be represented without overloading the state layer
- package the Qt runtime fonts explicitly before any broader shell distribution or screenshot-heavy review loops

## FS-04 — Preflight board and gating model

### Stack goal

Move the preflight board from placeholder state messaging to a deterministic rule engine that can explain blocked, warning, and ready states before any flash action becomes available.

### Frame 1 — Preflight categories, severities, and rule inputs pinned

**Result:** completed

Pinned the first preflight contract in `calamum_vulcan/domain/preflight/` around:

| Contract surface    | Role                                                                                     |
| ------------------- | ---------------------------------------------------------------------------------------- |
| `PreflightCategory` | host / device / package / compatibility / safety grouping                                |
| `PreflightSeverity` | `pass`, `warn`, `block` rule outcomes                                                    |
| `PreflightGate`     | operator-facing gate state: `ready`, `warn`, `blocked`                                   |
| `PreflightInput`    | deterministic rule inputs derived from session state plus placeholder host/package facts |
| `PreflightSignal`   | one rule result with title, summary, and remediation                                     |
| `PreflightReport`   | the summarized board result consumed by the shell                                        |

Rule-input coverage for this stack now includes:

- host readiness
- USB driver readiness
- device presence
- download-mode confirmation
- package selection and completeness
- checksum presence
- product-code compatibility
- battery guidance
- cable-quality posture
- destructive acknowledgement
- operator acknowledgement capture

### Frame 2 — Rule engine implemented independently of the GUI

**Result:** completed

Implemented `evaluate_preflight(...)` in `calamum_vulcan/domain/preflight/evaluator.py`.

The engine is GUI-independent and produces a pure `PreflightReport`, which means:

- rule evaluation can be unit-tested without the desktop shell
- blocked/warn/ready semantics do not depend on widget code
- the shell can consume the same rule results later when real package/environment data replaces placeholder inputs

The first evaluation model intentionally stays conservative and safe-by-default:

- missing prerequisites block execution
- warnings hold the gate until acknowledgement is captured
- destructive operations remain blocked until explicit acknowledgement exists

### Frame 3 — Preflight board rendered with pass/warn/block semantics

**Result:** completed

Bound the shell to the preflight engine in `calamum_vulcan/app/view_models.py`.

New shell behavior now includes:

- a dedicated `Gate` pill in the header
- preflight-panel summaries driven by `PreflightReport.summary`
- detail lines showing explicit `PASS`, `WARN`, and `BLOCK` findings
- count metrics for passes, warnings, and blocks
- log-pane lines that record top preflight findings instead of vague placeholder notes

This closes the earlier gap where the board only echoed coarse session state rather than rule-based trust signals.

### Frame 4 — Environment, device, and package placeholders connected to the gate

**Result:** completed

Connected the preflight engine to the existing shell and state layer through `PreflightInput.from_session(...)`.

Key integration effects:

- the preflight board now derives its initial host/device/package placeholders from the immutable session snapshot
- `Execute flash plan` is now gated by both `SessionPhase.READY_TO_EXECUTE` and `PreflightReport.ready_for_execution`
- no parallel UI-only gate model was introduced
- the state layer remains the orchestration backbone while the preflight layer owns rule semantics

### Frame 5 — Validation run and scenario review

**Result:** completed

Automated validation run:

- `python -m unittest discover -s "tests/unit" -p "test_*.py"`
- result: `Ran 17 tests in 0.446s` / `OK`

Scenario walkthrough evidence from the release root:

- no-device -> `phase="No Device" gate="Gate Blocked"`
- blocked -> `phase="Validation Blocked" gate="Gate Blocked"`
- warning -> `phase="Validation Passed" gate="Gate Warning"`
- ready -> `phase="Ready to Execute" gate="Gate Ready"`

Blocked-shell sandbox evidence:

- offscreen Qt launch of `calamum_vulcan/launch_shell.py --scenario blocked --duration-ms 250`
- result: shell launched and exited cleanly while preserving the blocked gate summary and disabled execute path

Runtime note carried forward:

- Qt still emits a font-directory warning and an offscreen-plugin `propagateSizeHints()` notice during sandbox runs; these remain packaging/runtime polish items rather than functional blockers

## Validation record for FS-04

| Validation type                                    | Outcome |
| -------------------------------------------------- | ------- |
| preflight rule tests                               | passed  |
| updated shell view-model tests                     | passed  |
| Qt shell contract tests                            | passed  |
| no-device / blocked / warning / ready walkthroughs | passed  |
| blocked-shell offscreen launch                     | passed  |

## Proven vs stubbed after FS-04

### Proven

- Calamum Vulcan now has a real preflight rule engine rather than a placeholder preflight panel
- the shell can distinguish blocked, warning, and ready states from deterministic rule evaluation
- the execute action is now gated by the preflight report instead of session phase alone
- environment, device, and package placeholders are visibly connected to the trust gate in the GUI shell

### Stubbed / deferred

- host, driver, battery, and cable inputs are still placeholder facts derived from session defaults rather than live probes
- package completeness and checksum signals are still inferred until FS-05 builds a real package surface
- product-code compatibility currently rides on session-derived posture rather than parsed package metadata
- preflight exports/reporting are still deferred to FS-06

## Carry-forward debt into FS-05

- replace inferred package-completeness and checksum assumptions with real parsed package truth
- feed explicit supported product-code lists into compatibility evaluation instead of phase-based inference
- preserve the current gate semantics while introducing manifest-driven mismatch cases
- keep the shell fixture-first as the package lane expands so preflight remains testable and adapter-independent

## FS-05 — Package-awareness surface and flash-plan preview

### Stack goal

Turn package truth from a placeholder shell territory into a concrete contract with manifest fixtures the rest of the sprint can safely build against.

### Frame 1 — Package summary contract, sample manifests, and test surfaces pinned

**Result:** completed

Pinned the first package-awareness contract in `calamum_vulcan/domain/package/`.

Contract surfaces now include:

| Surface                        | Role                                                                                                 |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `PackageIdentity`              | package id, name, version, manufacturer, and source build fields                                     |
| `PackageCompatibilityContract` | supported product codes, supported device names, PIT fingerprint, and expected compatibility posture |
| `ChecksumPlaceholder`          | placeholder checksum coverage for each payload                                                       |
| `PartitionPlanEntry`           | early partition/file preview row for the flash-plan surface                                          |
| `PackageSummaryContract`       | the consolidated package summary contract for later parsing and shell binding                        |
| `FRAME_1_TEST_SURFACES`        | the specific trust surfaces this lane must preserve as it expands                                    |

Defined frame-1 test surfaces explicitly:

- manifest identity completeness
- product-code compatibility
- checksum placeholder coverage
- partition-plan preview stability
- incomplete-manifest handling

Sample manifest fixtures now live under `calamum_vulcan/fixtures/package_manifests/`:

- `matched_recovery_package.json`
- `mismatched_recovery_package.json`
- `incomplete_recovery_package.json`

Centralization change completed for downstream repo split readiness:

- active launcher moved to `calamum_vulcan/launch_shell.py`
- active local dependency file moved to `calamum_vulcan/requirements.txt`
- prior out-of-root copies were archived to `quarantine_legacy_archive/2026-04-18_calamum_vulcan_centralization/`

This keeps active application artifacts under the `calamum_vulcan/` root while preserving the archive-first repository policy.

### Validation record for FS-05 / Frame 1

| Validation type                  | Outcome |
| -------------------------------- | ------- |
| package-contract unit tests      | passed  |
| centralized launcher smoke check | passed  |
| manifest fixture walkthrough     | passed  |

Validation evidence captured:

- `python -m unittest discover -s "tests/unit" -p "test_*.py"`
- result: `Ran 22 tests in 0.403s` / `OK`
- manifest walkthrough:
	- fixtures -> `('matched', 'mismatched', 'incomplete')`
	- matched issues -> `()`
	- mismatched expectation -> `mismatch`
	- incomplete issue count -> `3`
	- centralized launcher exists -> `True`
	- legacy launcher exists -> `False`
	- centralized requirements exists -> `True`
	- legacy requirements exists -> `False`
- launcher smoke check:
	- `python "calamum_vulcan/launch_shell.py" --scenario ready --describe-only`
	- result: printed the expected ready-state shell summary through the new in-root launcher path

### Carry-forward debt into FS-05 / Frame 2

- implement the first parsing/normalization boundary from JSON manifest into package contract objects
- replace preflight package assumptions with parsed manifest facts rather than session-derived defaults
- keep launcher/dependency references rooted under `calamum_vulcan/` as new runtime surfaces appear
- decide whether package fixture helpers should remain JSON-only or gain typed normalization outputs in frame 2

### Frame 2 — Typed manifest parsing and assessment boundary implemented

**Result:** completed

Implemented the first package normalization layer in:

- `calamum_vulcan/domain/package/parser.py`
- `calamum_vulcan/domain/package/model.py`
- `calamum_vulcan/domain/package/__init__.py`

New package-owned surfaces now include:

| Surface                                            | Role                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `PackageManifestAssessment`                        | normalized package truth for shell and preflight consumption even when a manifest is incomplete |
| `PackageManifestContractError`                     | explicit parse-time failure for incomplete manifests                                            |
| `parse_package_summary_contract(...)`              | typed conversion from validated manifest mapping into `PackageSummaryContract`                  |
| `assess_package_manifest(...)`                     | contract-aware summary layer for matched, mismatched, and incomplete package states             |
| `preflight_overrides_from_package_assessment(...)` | manifest-driven preflight bridge so the trust gate no longer relies on package guesses          |

This frame also expanded fixture handling without bloating the public frame-1 manifest surface:

- public fixture discovery still returns `matched`, `mismatched`, and `incomplete`
- scenario-specific internal fixtures now support `ready`, `blocked`, and `package-first` shell states with package ids and product codes that match the fixture-driven session flows

### Frame 3 — Package identity, compatibility, and flash-plan preview bound into the shell

**Result:** completed

Bound real package truth into the shell through:

- `calamum_vulcan/app/demo.py`
- `calamum_vulcan/app/view_models.py`
- `calamum_vulcan/app/__main__.py`

The `Package Summary` panel now renders manifest-derived:

- package identity and source build
- supported product-code and device lists
- PIT fingerprint
- partition preview rows
- checksum-placeholder coverage
- post-flash instruction lines
- contract issues when the manifest is incomplete

Shell/runtime behavior now changed materially:

- scenario-default package selection is bound per shell scenario instead of relying on one generic placeholder
- the CLI now supports `--package-fixture` for explicit public manifest review
- package-context log lines are emitted into the shell evidence stream

### Frame 4 — Manifest-driven mismatch and error handling wired into the trust gate

**Result:** completed

The preflight layer now consumes manifest-driven package facts instead of session-only assumptions.

Observed effects in the shell contract:

- blocked package mismatch is visible before execution when the detected product code falls outside the supported manifest set
- incomplete package manifests keep the gate blocked and disable execute even when the session phase is otherwise ready-like
- destructive gating now reflects manifest risk level through the package assessment bridge
- no parallel package gate model was introduced; the existing `PreflightInput` contract remains the single evaluation input surface

### Frame 5 — Validation run and sandbox review

**Result:** completed

Automated validation run:

- `python -m unittest discover -s "tests/unit" -p "test_*.py"`
- result: `Ran 27 tests in 0.109s` / `OK`
- interpreter surface used by the workspace terminal during this historical pass: legacy development virtual environment (superseded for Vulcan by `.venv-core`)

Package-aware shell walkthrough evidence:

- offscreen shell launch: `python -m calamum_vulcan.app --scenario ready --duration-ms 50`
	- result: `phase="Ready to Execute" gate="Gate Ready"`
- blocked manifest review: `python -m calamum_vulcan.app --scenario blocked --describe-only`
	- result: `phase="Validation Blocked" gate="Gate Blocked"`
- public mismatched manifest review: `python -m calamum_vulcan.app --scenario ready --package-fixture mismatched --describe-only`
	- result: `phase="Ready to Execute" gate="Gate Blocked"`
- incomplete manifest review: `python -m calamum_vulcan.app --scenario ready --package-fixture incomplete --describe-only`
	- result: `phase="Ready to Execute" gate="Gate Blocked"`

Runtime note carried forward:

- offscreen Qt still emits the previously known font-directory warning and `propagateSizeHints()` notice during shell launch; these remain packaging/runtime polish items rather than functional blockers

## Validation record for FS-05

| Validation type                                                      | Outcome |
| -------------------------------------------------------------------- | ------- |
| package parser tests                                                 | passed  |
| updated shell view-model tests                                       | passed  |
| Qt shell contract tests                                              | passed  |
| full unit-test suite                                                 | passed  |
| package-aware ready / blocked / mismatched / incomplete walkthroughs | passed  |

## Proven vs stubbed after FS-05

### Proven

- Calamum Vulcan now has a typed package parsing and assessment boundary rather than JSON-only fixtures
- package identity, compatibility, partition intent, checksum placeholders, and post-flash notes now render inside the shell as first-class operator surfaces
- the preflight gate now consumes manifest-driven package truth for completeness, compatibility, checksum coverage, and destructive-risk posture
- matched, mismatched, and incomplete package states are all visible and test-backed before any adapter wiring begins

### Stubbed / deferred

- checksum values remain placeholder contracts rather than live digest verification
- package intake is still fixture-driven rather than wired to operator-selected files or real archive imports
- package evidence/export serialization is still deferred to `FS-06`
- transport execution still does not consume the flash-plan contract directly; that remains later adapter work

## Carry-forward debt into FS-06

- extend the session evidence/report contract so package assessment results serialize cleanly into logs and future export bundles
- preserve the package-context log lines as a stable reporting input rather than letting the shell own the only readable representation
- keep the package fixtures and parser contract stable while the reporting lane adds machine-readable evidence surfaces
- maintain centralized active application artifacts under `calamum_vulcan/` as logging and export surfaces expand

## FS-06 — Evidence, logging, and report contract

### Stack goal

Turn the shell’s reserved evidence lane into a real platform-owned reporting contract with structured summaries, decision traces, recovery guidance, and bounded export behavior.

### Frame 1 — Session evidence schema and export targets pinned

**Result:** completed

Pinned the first reporting contract in `calamum_vulcan/domain/reporting/`.

Contract surfaces now include:

| Surface                          | Role                                                                   |
| -------------------------------- | ---------------------------------------------------------------------- |
| `HostEnvironmentEvidence`        | runtime, platform, and execution-posture summary for one session       |
| `DeviceEvidence`                 | device identity fields carried into the report bundle                  |
| `PackageEvidence`                | package identity, compatibility, and contract-health summary           |
| `PreflightEvidence`              | gate counts, summary, and recommended-action surface                   |
| `OutcomeEvidence`                | outcome label, export readiness, next action, and recovery guidance    |
| `DecisionTraceEntry`             | one structured decision-trace row for operator review                  |
| `SessionEvidenceReport`          | consolidated session evidence schema used by shell and export surfaces |
| `REPORT_EXPORT_TARGETS`          | bounded `json` and `markdown` export targets for `0.1.0`               |
| `REQUIRED_SESSION_REPORT_FIELDS` | top-level fields that define a valid `0.1.0` report bundle             |

This frame also pinned the required/optional reporting boundary so later adapter work can extend the contract without rewriting the shell surface.

### Frame 2 — Core report, log, and serialization structures implemented

**Result:** completed

Implemented the reporting builders in:

- `calamum_vulcan/domain/reporting/builder.py`
- `calamum_vulcan/domain/reporting/model.py`
- `calamum_vulcan/domain/reporting/__init__.py`

Core FS-06 behaviors now exist in code:

- `build_session_evidence_report(...)` produces a structured evidence bundle from session, package, and preflight truth
- report ids are generated deterministically from timestamp, phase, and scenario label
- decision traces are composed from phase, trust-gate findings, package posture, and normalized failure reasons
- log lines now flow from the reporting builder instead of being shell-only placeholders
- JSON and Markdown serialization are both available through platform-owned helpers
- bounded file export is available through `write_session_evidence_report(...)`

### Frame 3 — Live evidence panel and log-pane summary bound into the shell

**Result:** completed

Bound the reporting contract into the existing shell through:

- `calamum_vulcan/app/view_models.py`
- `calamum_vulcan/app/__main__.py`

Observed shell changes:

- `Session Evidence` now renders captured-at timestamps, recommended action, recovery guidance, export targets, and decision-trace previews
- the log pane now carries report id, export-target, recovery, and evidence-summary lines supplied by the reporting builder
- `Export evidence` is now an active operator action whenever the session has meaningful evidence, including blocked and warning review states
- no new UI panel or alternate shell surface was introduced; the original evidence lane simply became real

### Frame 4 — Bounded export path and recovery-guidance surface added

**Result:** completed

Added the first bounded reporting path to the CLI entrypoint.

New `calamum_vulcan.app` behavior now supports:

- `--export-evidence`
- `--evidence-format json|markdown`
- `--evidence-output <path>`

This keeps export behavior explicit and fixture-safe for `0.1.0` while proving that the report contract can leave the shell in both machine-readable and human-readable form.

### Frame 5 — Validation run and report walkthroughs

**Result:** completed

Automated validation run:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 31 tests in 0.426s` / `OK`
- interpreter surface used by the workspace terminal during this historical pass: legacy development virtual environment (superseded for Vulcan by `.venv-core`)

Evidence-export walkthroughs:

- ready review with Markdown export:
	- `python -m calamum_vulcan.app --scenario ready --describe-only --export-evidence --evidence-format markdown`
	- result: ready-state shell summary plus readable evidence bundle with package, preflight, recovery, and decision-trace sections
- blocked review with JSON export:
	- `python -m calamum_vulcan.app --scenario blocked --describe-only --export-evidence --evidence-format json`
	- result: blocked-state shell summary plus machine-readable evidence bundle carrying mismatch findings and decision trace
- failure review with Markdown export:
	- `python -m calamum_vulcan.app --scenario failure --describe-only --export-evidence --evidence-format markdown`
	- result: failed-state shell summary plus recovery guidance and normalized failure reason

Runtime note carried forward:

- the existing Qt font-directory warning remains visible during test runs with the Qt contract test, but it did not block the reporting validation bundle

## Validation record for FS-06

| Validation type                                        | Outcome |
| ------------------------------------------------------ | ------- |
| reporting-contract tests                               | passed  |
| updated shell view-model tests                         | passed  |
| Qt shell contract tests                                | passed  |
| full unit-test suite                                   | passed  |
| ready / blocked / failure evidence-export walkthroughs | passed  |

## Proven vs stubbed after FS-06

### Proven

- Calamum Vulcan now has a structured session evidence schema rather than a reserved reporting placeholder
- the shell evidence panel and log pane now consume platform-owned reporting data instead of future-tense placeholders
- JSON and Markdown evidence exports both exist and are exercised from the CLI
- blocked, ready, and failed scenarios now preserve package, preflight, outcome, and decision-trace context in one exportable bundle

### Stubbed / deferred

- export persistence is still manual/CLI-driven rather than attached to a dedicated GUI save flow
- report timestamps and ids are generated at runtime rather than linked to a future adapter/session ledger
- report bundles do not yet include normalized Heimdall stdout/stderr because the adapter seam is still deferred to `FS-07`
- evidence exports do not yet package external artifacts such as PIT snapshots or transport transcripts

## Carry-forward debt into FS-07

- preserve the reporting contract while adapter events start replacing fixture-only transport language
- extend the decision trace with normalized backend progress and result events once the adapter seam exists
- keep the shell log pane fed by platform-owned evidence lines rather than raw backend text when `FS-07` lands
- determine which adapter outputs belong in the session evidence bundle versus which should remain transport-internal

## FS-07 — Heimdall adapter seam and event normalization

### Stack goal

Move transport dependence behind a platform-owned seam so the shell, reporting layer, and future runtime controls consume normalized state rather than raw Heimdall text.

### Frame 1 — Adapter boundary, capability surface, and fixture-backed tests pinned

**Result:** completed

Pinned the first transport boundary in:

- `calamum_vulcan/adapters/heimdall/`
- `calamum_vulcan/fixtures/heimdall_process_fixtures.py`
- `tests/unit/test_heimdall_adapter.py`

Contract surfaces now include:

| Surface                     | Role                                                                                    |
| --------------------------- | --------------------------------------------------------------------------------------- |
| `HeimdallCapability`        | bounded transport capabilities exposed to the platform                                  |
| `HeimdallOperation`         | allowed backend operations for detect, PIT work, and flash transport                    |
| `HeimdallCommandPlan`       | executable, arguments, display command, and expected-exit contract for one backend call |
| `HeimdallProcessResult`     | raw process result boundary carrying stdout, stderr, and exit code                      |
| `HeimdallNormalizedTrace`   | platform-owned transport truth after normalization                                      |
| `HEIMDALL_PROCESS_FIXTURES` | deterministic adapter fixtures for detect, success, failure, and no-reboot resume flows |

This frame pinned the adapter contract before any shell/runtime wiring began, which keeps the backend seam explicit enough for later replacement work.

### Frame 2 — Command construction and backend invocation abstractions implemented

**Result:** completed

Implemented the command-planning boundary in `calamum_vulcan/adapters/heimdall/builder.py`.

Core FS-07 command behaviors now exist in code:

- `build_detect_device_command_plan()` produces a bounded detect invocation
- `build_print_pit_command_plan()` and `build_download_pit_command_plan(...)` expose PIT-oriented seams without leaking CLI assembly into the shell
- `build_flash_command_plan(...)` builds the package-aware flash invocation, including `--no-reboot` posture when the manifest requires it
- `build_command_plan_for_operation(...)` centralizes adapter dispatch so the CLI/demo lane does not assemble Heimdall commands ad hoc

### Frame 3 — Stdout, stderr, progress, and result states normalized into platform-owned events

**Result:** completed

Implemented normalization in `calamum_vulcan/adapters/heimdall/normalizer.py`.

The adapter now converts raw process output into product-owned transport truth:

- detect output normalizes into `DEVICE_CONNECTED` with device identity fields
- flash output normalizes progress markers such as `RECOVERY 42%` and `VBMETA 100%`
- transport failures normalize into `EXECUTION_FAILED` with a stable failure reason rather than raw stderr leakage
- no-reboot recovery flows normalize into pause/resume/completed state transitions plus operator-facing notes
- report rendering now surfaces normalized progress, transport notes, and failure reason in the evidence bundle

### Frame 4 — Normalized adapter events connected to state, reporting, and shell surfaces

**Result:** completed

Connected the new transport seam across the active product layers through:

- `calamum_vulcan/adapters/heimdall/runtime.py`
- `calamum_vulcan/app/demo.py`
- `calamum_vulcan/app/__main__.py`
- `calamum_vulcan/app/view_models.py`
- `calamum_vulcan/domain/reporting/model.py`
- `calamum_vulcan/domain/reporting/builder.py`

Observed integration changes:

- `apply_heimdall_trace(...)` and `replay_heimdall_process_result(...)` replay normalized transport events into the immutable state contract
- the demo/CLI lane now supports `--transport-source heimdall-adapter` and optional `--adapter-fixture` selection
- the reporting contract now carries `TransportEvidence` with adapter name, capability, command, normalized-event count, progress markers, notes, and exit code
- the shell `Transport State` panel now renders transport evidence instead of a future-tense placeholder
- the root package and fixtures export the new adapter seam without moving any active application artifact out of `calamum_vulcan/`

### Frame 5 — Mocked validation run and adapter-backed walkthroughs

**Result:** completed

Automated validation run:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 38 tests in 0.295s` / `OK`
- interpreter surface used by the workspace terminal during this historical pass: legacy development virtual environment (superseded for Vulcan by `.venv-core`)

Adapter-backed evidence walkthroughs:

- happy-path review with JSON export:
	- `python -m calamum_vulcan.app --scenario happy --transport-source heimdall-adapter --describe-only --export-evidence --evidence-format json --evidence-output temp/fs07_happy.json`
	- result: completed-state shell summary plus JSON evidence carrying normalized progress markers `RECOVERY 42%`, `RECOVERY 100%`, and `VBMETA 100%`
- failure review with Markdown export:
	- `python -m calamum_vulcan.app --scenario failure --transport-source heimdall-adapter --describe-only --export-evidence --evidence-format markdown --evidence-output temp/fs07_failure.md`
	- result: failed-state shell summary plus Markdown evidence carrying normalized transport progress, adapter note, and failure reason `USB transfer timeout during partition write`
- resume-needed review with JSON export:
	- `python -m calamum_vulcan.app --scenario resume --transport-source heimdall-adapter --describe-only --export-evidence --evidence-format json --evidence-output temp/fs07_resume.json`
	- result: completed-state shell summary plus JSON evidence carrying the normalized no-reboot handoff note and resume path

Runtime note carried forward:

- the existing Qt font-directory warning remains visible during the Qt contract test, but it did not block the FS-07 validation bundle

## Validation record for FS-07

| Validation type                                      | Outcome |
| ---------------------------------------------------- | ------- |
| Heimdall adapter tests                               | passed  |
| updated reporting-contract tests                     | passed  |
| updated shell view-model tests                       | passed  |
| Qt shell contract tests                              | passed  |
| full unit-test suite                                 | passed  |
| adapter-backed happy / failure / resume walkthroughs | passed  |

## Proven vs stubbed after FS-07

### Proven

- Calamum Vulcan now owns a named Heimdall adapter seam under `calamum_vulcan/adapters/heimdall/`
- transport command construction is centralized rather than scattered across the CLI or shell layers
- raw Heimdall output is normalized into platform events, progress markers, notes, and evidence-friendly summaries
- the reporting contract and shell transport panel now consume normalized transport evidence rather than placeholders
- the adapter-backed CLI/demo lane can exercise success, failure, and no-reboot resume paths without leaking raw backend text into the UI contract

### Stubbed / deferred

- transport execution is still fixture-backed rather than attached to a live subprocess/device session loop
- report bundles still carry summarized transport evidence rather than archived full transcript artifacts
- PIT acquisition and related adapter capabilities exist at the boundary but are not yet operator-driven controls in the shell
- the Qt font-packaging warning remains external deployment debt rather than a transport defect

## Carry-forward debt into FS-08

- run integrated cross-stack walkthroughs that treat the adapter-backed transport path as part of one product, not a separate demo lane
- decide which transport artifacts should remain summarized in `0.1.0` evidence versus which should be preserved as external transcript files later
- tighten any shell labels, evidence phrasing, or control affordances discovered during the integrated review pass
- keep live-device transport out of scope for `0.1.0` while documenting the next autonomy surfaces clearly enough for `0.2.0`

## FS-08 — Integration pass, sandbox scenarios, and release-close evidence

### Stack goal

Close Sprint `0.1.0` as one coherent product by proving the integrated shell, trust gate, package surface, adapter boundary, and reporting contract all hold together under one release-close walkthrough bundle.

### Frame 1 — Sprint-close proof set and review bundle pinned

**Result:** completed

Pinned the FS-08 integration surface in:

- `calamum_vulcan/app/integration.py`
- `calamum_vulcan/app/__main__.py`
- `tests/unit/test_integration_suite.py`

The new sprint-close bundle now owns:

| Surface                           | Role                                                       |
| --------------------------------- | ---------------------------------------------------------- |
| `SprintCloseProofPoint`           | one release-close requirement with pass/fail status        |
| `SprintCloseScenarioResult`       | one integrated scenario result with shell/evidence summary |
| `SprintCloseBundle`               | the structured FS-08 release-close bundle                  |
| `SPRINT_CLOSE_SCENARIOS`          | the frozen integrated scenario matrix for `0.1.0` closeout |
| `SPRINT_CLOSE_CARRY_FORWARD_DEBT` | the bounded debt list carried into `0.2.0`                 |

The frozen sprint-close suite now covers six integrated scenarios:

- no-device shell review
- happy-path adapter review
- blocked preflight review
- incompatible package review
- transport failure review
- resume-handoff adapter review

### Frame 2 — Cross-stack happy-path walkthrough executed through one product shell

**Result:** completed

The new FS-08 bundle proves the happy path through the integrated product surface rather than through separate lane-specific checks.

Observed integrated happy-path proof:

- the shell remains on the five-panel contract (`Device Identity`, `Preflight Board`, `Package Summary`, `Transport State`, `Session Evidence`)
- the adapter-backed happy path reaches `Completed` with `Gate Ready`
- transport stays normalized as `completed` rather than surfacing raw Heimdall text
- the integrated report remains export-ready in both JSON and Markdown formats

CLI surface added for this frame:

- `--integration-suite sprint-close`
- `--suite-format json|markdown`
- `--suite-output <path>`

### Frame 3 — Negative-path walkthroughs executed and captured in the release-close bundle

**Result:** completed

The FS-08 suite now closes the negative-path gap that remained after the earlier lane-by-lane stacks.

Integrated negative-path coverage now includes:

- no-device shell review with `Gate Blocked` and intentionally non-exportable evidence posture
- blocked preflight review with preserved blocked gate and export-ready evidence bundle
- incompatible package review where the shell phase remains `Ready to Execute` but the trust gate correctly stays `Gate Blocked`
- adapter-backed transport failure review with normalized failed transport state and recovery evidence
- adapter-backed resume-handoff review that stays normalized and export-ready without falling back to backend-text language

### Frame 4 — Highest-value shell and evidence gap tightened

**Result:** completed

Tightened one high-value review gap discovered during the integrated walkthrough pass:

- the `Session Evidence` panel now surfaces the report id directly in the shell, which makes cross-checking exported artifacts against the visible operator surface much easier during closeout review

This kept the polish bounded and useful instead of drifting into broad UI restyling.

### Frame 5 — Sprint-close validation bundle executed and artifacts captured

**Result:** completed

Automated validation run in the approved Calamum Vulcan environment:

- interpreter: `.venv-core`
- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 42 tests in 0.612s` / `OK`

Sprint-close bundle exports:

- Markdown bundle:
	- `python -m calamum_vulcan.app --integration-suite sprint-close --suite-format markdown --suite-output temp/fs08_sprint_close.md`
	- result: exported a human-readable sprint-close bundle proving `5/5` proof points across `6` integrated scenarios
- JSON bundle:
	- `python -m calamum_vulcan.app --integration-suite sprint-close --suite-format json --suite-output temp/fs08_sprint_close.json`
	- result: exported the machine-readable sprint-close bundle with the same scenario matrix and carry-forward debt list

Integrated walkthrough validation:

- offscreen happy-path launch:
	- `python -m calamum_vulcan.app --scenario happy --transport-source heimdall-adapter --duration-ms 50`
	- result: shell launched offscreen, held the completed / gate-ready happy path, and exited cleanly
- mismatched package review:
	- `python -m calamum_vulcan.app --scenario ready --package-fixture mismatched --describe-only`
	- result: shell summary preserved `phase="Ready to Execute" gate="Gate Blocked"`

Environment note resolved during this frame:

- `.venv-core` was confirmed as the approved Calamum Vulcan runtime for future work
- `PySide6>=6.8,<7` was installed into `.venv-core` from `calamum_vulcan/requirements.txt` so GUI validation no longer falls back to a skipped runtime surface there

Known runtime note carried forward:

- Qt still emits the known font-directory warning plus the offscreen-plugin `propagateSizeHints()` notice; these remain packaging/deployment debt rather than functional blockers

## Validation record for FS-08

| Validation type                                     | Outcome |
| --------------------------------------------------- | ------- |
| integration-suite tests                             | passed  |
| updated shell view-model tests                      | passed  |
| full unit-test suite in `.venv-core`                | passed  |
| sprint-close bundle Markdown export                 | passed  |
| sprint-close bundle JSON export                     | passed  |
| offscreen happy-path adapter launch in `.venv-core` | passed  |
| mismatched package integrated review                | passed  |

## Proven vs stubbed after FS-08

### Proven

- Sprint `0.1.0` now has a structured release-close bundle rather than only lane-local validation notes
- the integrated suite proves the five-panel shell stays stable across happy, blocked, mismatch, failure, resume, and no-device reviews
- the adapter-backed happy and failure lanes behave like product-owned flows rather than isolated backend demos
- the reporting/export contract remains intact at sprint close in both Markdown and JSON forms
- `.venv-core` now supports both the unit suite and the offscreen GUI validation path for Calamum Vulcan

### Stubbed / deferred

- transport execution remains fixture-backed rather than attached to a live subprocess/device loop
- release-close bundles summarize transport evidence instead of preserving full transcript artifacts
- PIT-oriented transport capabilities remain adapter-level surfaces rather than exposed shell actions
- Qt deployment/font packaging remains an environment-preparation concern rather than a solved distribution surface

## Carry-forward debt into 0.2.0

- keep live-device subprocess transport out of `0.1.0`; the next release should define the first bounded runtime session loop explicitly
- decide which transport artifacts should graduate from summarized evidence into preserved transcript files in `0.2.0`
- promote PIT-oriented adapter capabilities into operator-driven shell controls only after the current shell contract stays stable under live transport
- close the Qt deployment/font-packaging debt before broader distribution or screenshot-heavy release review

## Publication lane activation after Sprint `0.1.0`

With the product-shell sprint complete, the next active lane moved to the nested-repo publication sequence.

### `FS-P01` — Subordinate-repo boundary and release-root contract

**Execution note (2026-04-18):** completed.

### Stack goal

Treat the nested repo as the authoritative public boundary for `0.1.0` and prove that it can stand on its own for public-facing build, test, documentation, and release preparation work.

### Frame 1 — Boundary contract and public seed pinned

**Result:** completed

Pinned the publication boundary around the live public seed:

- public repo: `https://github.com/joediggidyyy/calamum_vulcan`
- default branch: `main`
- release root: nested repo root
- seed state at activation: MIT `LICENSE`, no releases published yet

### Frame 2 — Required public surfaces inventoried

**Result:** completed

Observed release-root surfaces at the start of the stack:

- `LICENSE`
- `calamum_vulcan/`
- `docs/`
- `tests/`

Missing public-root scaffolding identified before closeout:

- `README.md`
- contributor quickstart guidance
- release-root-local ignore rules

### Frame 3 — Nested release root attached to the public seed

**Result:** completed

Prepared the release root as its own git repository and attached it to the live public seed.

Observed git boundary state after attachment:

- `.git/` initialized at the release root
- `origin` points to `https://github.com/joediggidyyy/calamum_vulcan.git`
- local `main` tracks `origin/main`
- seed `LICENSE` is present in the nested repo working tree

### Frame 4 — Public-facing boundary surfaces tightened

**Result:** completed

Boundary hardening completed in this stack:

- added release-root `.gitignore`
- added `README.md` with public quickstart and release-root usage
- added `CONTRIBUTING.md` with contributor quickstart and boundary rules
- replaced parent-path-heavy publication wording in planning docs with release-root language
- removed remaining workspace-root phrasing and absolute interpreter path leakage from the execution evidence surface

### Frame 5 — Release-root audit and validation

**Result:** completed

Release-root audit outcome:

- release-root public scaffolding exists
- nested git boundary exists and is wired to the public seed
- planning docs now point to the live seed and the release-root publication lane
- parent-path leakage was reduced to planning-only boundary language, not public quickstart commands

Validation evidence used for stack closeout:

- release-root file inventory review: passed
- markdown/editor validation for touched docs: passed
- `.venv-core` unit suite at the release root: `Ran 42 tests in 0.322s` / `OK`
- release-root shell smoke: ready scenario summary printed successfully
- nested repo audit: public seed `origin` wired, local `main` tracking `origin/main`, and working tree contains the expected uncommitted FS-P01 boundary files

### Proven vs stubbed after `FS-P01`

#### Proven

- the public seed exists and the nested repo is attached to it
- the release root now has baseline public scaffolding (`README.md`, `CONTRIBUTING.md`, `.gitignore`, `LICENSE`)
- the publication lane now has a real root boundary rather than only a planning assumption
- the nested repo can serve as the authoritative location for upcoming packaging and validation work

#### Stubbed / deferred

- packaging metadata is still deferred to `FS-P02`
- installed-artifact checks are still deferred to `FS-P03`
- scripted simulation bundle automation for publication is still deferred to `FS-P04`
- empirical review and TestPyPI rehearsal remain deferred to `FS-P05` and `FS-P06`

### Carry-forward debt into `FS-P02`

- add subordinate-repo-local packaging metadata and build configuration
- make the public README align with the exact packaging commands once `pyproject.toml` exists
- preserve release-root-only commands and avoid reintroducing parent-path assumptions
- keep the evidence surface updated as the publication lane advances

### `FS-P02` — Packaging metadata and build artifact contract

**Execution note (2026-04-18):** completed.

### Stack goal

Give the nested release root a real packaging contract so it can build correct `sdist` and `wheel` artifacts with coherent metadata directly from the release root.

### Frame 1 — Build metadata, version, and entry points pinned

**Result:** completed

Added a subordinate-repo-local packaging contract in `pyproject.toml`.

Pinned packaging metadata now includes:

- package name: `calamum_vulcan`
- version: `0.1.0`
- requires-python: `>=3.14,<3.15`
- runtime dependency: `PySide6>=6.8,<7`
- release extras: `build`, `twine`
- repository URLs pointing at `https://github.com/joediggidyyy/calamum_vulcan`
- installed entry points:
	- `calamum-vulcan`
	- `calamum-vulcan-gui`

### Frame 2 — Package-data and artifact-boundary rules encoded

**Result:** completed

Encoded packaging boundaries through:

- `MANIFEST.in`
- `tool.setuptools.package-data` in `pyproject.toml`

Observed artifact-boundary decisions:

- package manifest fixtures are included in the built distribution
- `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, and `LICENSE` are included as release-root documentation surfaces
- `docs/` and `tests/` are included in the source distribution for publication-context traceability
- local caches, build outputs, and temporary release artifacts remain excluded from the release-root ignore rules

### Frame 3 — Repeatable build runner added

**Result:** completed

Added `scripts/build_release_artifacts.py` as the repeatable FS-P02 build runner.

The runner now:

- builds both `sdist` and `wheel`
- verifies that exactly one wheel and one source tarball are produced
- inspects both artifacts for required files and fixture content
- emits a compact artifact summary suitable for release-lane evidence

### Frame 4 — Public metadata and README rendering reviewed

**Result:** completed

Updated release-root documentation surfaces to match the packaging contract:

- `README.md` now documents source-checkout quickstart, packaging commands, and installed entry points
- `CONTRIBUTING.md` now includes the packaging-lane checks and release-root command discipline
- `CHANGELOG.md` now records the `0.1.0` packaging-preparation posture

Rendering and metadata validation:

- `twine check dist/*`
- result: wheel `PASSED`, sdist `PASSED`

### Frame 5 — Build artifacts created and inspected

**Result:** completed

Release-root validation bundle executed in the approved environment:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 42 tests in 0.224s` / `OK`

Artifact build and inspection:

- `python scripts/build_release_artifacts.py`
- result:
	- `sdist="calamum_vulcan-0.1.0.tar.gz"`
	- `wheel="calamum_vulcan-0.1.0-py3-none-any.whl"`
	- `artifact_contract="passed"`

Observed `dist/` contents after the stack:

- `calamum_vulcan-0.1.0.tar.gz`
- `calamum_vulcan-0.1.0-py3-none-any.whl`

## Validation record for `FS-P02`

| Validation type                      | Outcome |
| ------------------------------------ | ------- |
| packaging metadata/editor validation | passed  |
| `.venv-core` full unit-test suite    | passed  |
| release artifact runner              | passed  |
| wheel content inspection             | passed  |
| sdist content inspection             | passed  |
| `twine check` for wheel and sdist    | passed  |

### Proven vs stubbed after `FS-P02`

#### Proven

- the nested repo now has a real packaging contract rooted in `pyproject.toml`
- both `sdist` and `wheel` build successfully from the release root
- public metadata, entry points, and distribution URLs now point to the live public seed
- manifest fixtures and required documentation surfaces are included in the release artifacts
- long-description rendering passes for both artifact types

#### Stubbed / deferred

- installed-artifact import and CLI smoke checks remain deferred to `FS-P03`
- publication-context scenario automation remains deferred to `FS-P04`
- empirical review and registry rehearsal remain deferred to `FS-P05` and `FS-P06`

### Carry-forward debt into `FS-P03`

- validate installed-artifact imports outside the source tree
- exercise the installed console entry points and CLI evidence flows
- inspect the built wheel in a clean environment rather than only at build time
- keep release-root commands and docs aligned with the installed-artifact experience

### `FS-P03` — Installed-artifact and public API smoke lane

**Execution note (2026-04-18):** completed.

### Stack goal

Prove that the built `0.1.0` wheel behaves correctly outside the source tree, preserves the intended public surface, and can still drive the main evidence and integration flows from an installed-artifact context.

### Frame 1 — Installed-artifact validation matrix pinned

**Result:** completed

Pinned the release-root installed-artifact contract around these proof targets:

- one built wheel in `dist/`
- install target outside the source tree
- import resolution that does not fall back into the checkout
- installed public entry points for:
	- `calamum-vulcan`
	- `calamum-vulcan-gui`
- installed CLI smoke for help, describe-only, evidence export, and sprint-close bundle generation
- packaged fixture and metadata integrity review
- forbidden-content check to ensure `tests/`, `docs/`, and `temp/` do not leak into the installed wheel surface

### Frame 2 — Clean-environment install and import runner added

**Result:** completed

Added `scripts/validate_installed_artifact.py` as the repeatable FS-P03 installed-artifact runner.

The runner now:

- locates the single built wheel in `dist/`
- stages validation work under the system temp directory at `C:\Users\joedi\AppData\Local\Temp\calamum_vulcan_fs_p03_installed_artifact`
- installs the wheel into a dedicated target root outside the repository
- verifies that `import calamum_vulcan` resolves from the installed target rather than the source checkout
- inspects distribution metadata, entry points, dependency metadata, and packaged fixture visibility

### Frame 3 — Installed CLI, evidence, and integration flows exercised

**Result:** completed

The installed-artifact runner now exercises the public command surface from the installed target.

Validated installed behaviors include:

- `--help` output includes expected public flags:
	- `--integration-suite`
	- `--export-evidence`
	- `--package-fixture`
- ready-state `--describe-only` preserves the expected shell summary
- blocked-state JSON evidence export preserves the blocked preflight gate
- `--integration-suite sprint-close` preserves the expected suite name and six-scenario bundle shape
- the GUI entry-point contract remains aligned with the same ready-state describe-only surface

### Frame 4 — Packaged file surface and public metadata audited

**Result:** completed

Installed-artifact inspection now proves that the wheel ships the intended release surface.

Observed installed-package checks:

- required package files are present, including:
	- `calamum_vulcan/__init__.py`
	- `calamum_vulcan/app/__main__.py`
	- `calamum_vulcan/launch_shell.py`
	- package-manifest fixtures under `calamum_vulcan/fixtures/package_manifests/`
- distribution metadata includes the `PySide6` runtime requirement
- installed entry points include both public launchers
- expected fixture set is present in the installed artifact:
	- `blocked_review_package.json`
	- `incomplete_recovery_package.json`
	- `matched_recovery_package.json`
	- `mismatched_recovery_package.json`
	- `package_first_standard_review_package.json`
	- `ready_standard_review_package.json`
- forbidden content under `tests/`, `docs/`, and `temp/` does not leak into the installed wheel

### Frame 5 — Release-root validation bundle executed and corrected to true outside-tree proof

**Result:** completed

Release-root validation executed in the approved environment:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 42 tests in 0.418s` / `OK`

Artifact rebuild confirmation:

- direct execution of `scripts/build_release_artifacts.py`
- result:
	- `sdist="calamum_vulcan-0.1.0.tar.gz"`
	- `wheel="calamum_vulcan-0.1.0-py3-none-any.whl"`
	- `artifact_contract="passed"`

Installed-artifact validation confirmation after moving the validation root fully outside the repo:

- direct execution of `scripts/validate_installed_artifact.py`
- result:
	- `validation_root="C:\Users\joedi\AppData\Local\Temp\calamum_vulcan_fs_p03_installed_artifact"`
	- `wheel="calamum_vulcan-0.1.0-py3-none-any.whl"`
	- `installed_root="C:\Users\joedi\AppData\Local\Temp\calamum_vulcan_fs_p03_installed_artifact\install_root\calamum_vulcan"`
	- `import_contract="passed"`
	- `entrypoint_help="passed"`
	- `entrypoint_describe="passed"`
	- `gui_entrypoint="passed"`
	- `evidence_export="passed"`
	- `integration_bundle="passed"`
	- `distribution_files="passed"`
	- `installed_artifact_contract="passed"`

## Validation record for `FS-P03`

| Validation type                             | Outcome |
| ------------------------------------------- | ------- |
| `.venv-core` full unit-test suite           | passed  |
| release artifact rebuild confirmation       | passed  |
| installed import isolation check            | passed  |
| installed entry-point help smoke            | passed  |
| installed ready-state describe-only smoke   | passed  |
| installed blocked evidence export           | passed  |
| installed sprint-close bundle generation    | passed  |
| installed distribution-file integrity audit | passed  |

### Proven vs stubbed after `FS-P03`

#### Proven

- the built wheel installs and runs outside the source tree from a clean target root
- installed imports do not fall back into the repository checkout
- the public command surface still exposes help, ready-state describe-only review, evidence export, and sprint-close bundle generation after installation
- the packaged fixture and metadata surface is complete and intentional
- the installed wheel does not leak `tests/`, `docs/`, or repo-local temp artifacts into the runtime surface

#### Stubbed / deferred

- cross-platform installed-artifact validation beyond the current Windows host remains deferred to `FS-P04` and later empirical review
- visible packaged-GUI review remains deferred to `FS-P05`
- registry-delivered artifact rehearsal remains deferred to `FS-P06`

### Carry-forward debt into `FS-P04`

- extend the installed-artifact lane into the full scripted simulation matrix rather than only smoke checks
- add reproducible offscreen GUI and report-output assertions for publication-safe scenario coverage
- preserve the outside-source-tree install proof while broadening host and scenario coverage
- keep public docs aligned with the installed-artifact command experience as the simulation lane expands

### `FS-P04` — Scripted simulation and reproducibility lane

**Execution note (2026-04-18):** completed.

### Stack goal

Prove that the packaged `0.1.0` product can run its non-live operational scenario matrix reproducibly from both the release root and an installed wheel context, with deterministic evidence and bundle outputs.

### Frame 1 — Scripted scenario matrix and deterministic capture posture pinned

**Result:** completed

Pinned the FS-P04 scenario matrix in `scripts/run_scripted_simulation_suite.py` around six publication-safe scenarios:

- `no-device`
- `ready`
- `blocked`
- `mismatch`
- `failure`
- `resume`

Supporting contract changes added in this stack:

- `calamum_vulcan.app` now accepts `--captured-at-utc` so evidence and sprint-close bundle outputs can be reproduced deterministically
- the shell demo lane now includes a real `no-device` CLI scenario instead of relying only on the FS-08 integration bundle for that state

### Frame 2 — Release-root and installed-artifact runners wired to the same matrix

**Result:** completed

Added `scripts/run_scripted_simulation_suite.py` as the repeatable FS-P04 publication-lane runner.

The runner now:

- executes the same scripted scenario matrix from the source checkout and from an extracted installed wheel context
- archives evidence under:
	- `temp/fs_p04_scripted_simulation/source_root/`
	- `temp/fs_p04_scripted_simulation/installed_artifact/`
- writes a compact summary manifest to `temp/fs_p04_scripted_simulation/simulation_summary.json`
- records execution progress to `temp/fs_p04_scripted_simulation/progress.log`

### Frame 3 — Offscreen GUI validation plus JSON and Markdown evidence-export checks added

**Result:** completed

The FS-P04 runner now exercises these surfaces for every scenario in both execution contexts:

- `--describe-only` shell summary
- JSON evidence export
- Markdown evidence export
- offscreen GUI launch with `QT_QPA_PLATFORM=offscreen` and timed auto-close

Observed scenario coverage now includes:

- no-device shell summary and blocked gate without package context
- ready-state execute posture
- blocked mismatch review
- mismatched package override review
- adapter-backed failure review
- adapter-backed resume-handoff review

### Frame 4 — Deterministic report and bundle assertions tightened

**Result:** completed

Reproducibility checks now enforce:

- fixed capture timestamp for the sprint-close bundle: `2026-04-18T23:10:00Z`
- deterministic per-scenario evidence captures across the six-scenario matrix
- exact equality of source-root and installed-artifact:
	- describe-only outputs
	- JSON evidence bundles
	- Markdown evidence bundles
	- sprint-close JSON bundle
	- sprint-close Markdown bundle

This turns reproducibility from a narrative claim into an executable contract.

### Frame 5 — Full scripted simulation suite executed and archived

**Result:** completed

Release-root validation in the approved environment:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 45 tests in 0.883s` / `OK`

Artifact rebuild confirmation before the simulation lane:

- `python scripts/build_release_artifacts.py`
- result:
	- `sdist="calamum_vulcan-0.1.0.tar.gz"`
	- `wheel="calamum_vulcan-0.1.0-py3-none-any.whl"`
	- `artifact_contract="passed"`

FS-P04 simulation runner confirmation:

- `python scripts/run_scripted_simulation_suite.py`
- result:
	- `archive_root="C:\Users\joedi\Documents\edu\UNC\calamum_vulcan\temp\fs_p04_scripted_simulation"`
	- `wheel="calamum_vulcan-0.1.0-py3-none-any.whl"`
	- `scenario_matrix="passed"`
	- `source_root_runner="passed"`
	- `installed_artifact_runner="passed"`
	- `offscreen_gui="passed"`
	- `evidence_exports="passed"`
	- `integration_bundle="passed"`
	- `reproducibility_contract="passed"`
	- `scripted_simulation_contract="passed"`

Archived bundle evidence now includes:

- source-root scenario evidence for all six scenarios
- installed-artifact scenario evidence for all six scenarios
- source-root sprint-close bundle in JSON and Markdown
- installed-artifact sprint-close bundle in JSON and Markdown
- summary manifest:
	- `bundle_id="cv-fs08-20260418-231000-sprint-close"`

## Validation record for `FS-P04`

| Validation type                                  | Outcome |
| ------------------------------------------------ | ------- |
| `.venv-core` full unit-test suite                | passed  |
| release artifact rebuild confirmation            | passed  |
| source-root six-scenario matrix                  | passed  |
| installed-artifact six-scenario matrix           | passed  |
| JSON evidence export checks                      | passed  |
| Markdown evidence export checks                  | passed  |
| offscreen GUI validation                         | passed  |
| source vs installed exact-output reproducibility | passed  |
| sprint-close JSON and Markdown bundle generation | passed  |

### Proven vs stubbed after `FS-P04`

#### Proven

- the publication-safe scenario matrix now runs reproducibly from both the release root and an installed wheel context
- the package can generate identical JSON and Markdown evidence outputs across source and installed contexts when capture timestamps are pinned
- offscreen GUI validation now covers the full six-scenario matrix instead of only isolated smoke checks
- the sprint-close bundle is reproducible and archived in both execution contexts

#### Stubbed / deferred

- visible human-operated GUI review remains deferred to `FS-P05`
- public quickstart and troubleshooting alignment review remains deferred to `FS-P05`
- registry-delivered artifact rehearsal remains deferred to `FS-P06`

### Carry-forward debt into `FS-P05`

- review quickstart and troubleshooting material against the actual FS-P04 archived artifacts
- perform visible packaged-GUI review rather than only offscreen validation
- inspect exported evidence bundles for human readability and public-safe wording
- pin the exact public support posture between simulation-validated and live-device-validated claims

## `FS-P05` - empirical review and public-doc readiness

Completed from the nested release root after the scripted simulation archive from `FS-P04` was already available for comparison.

Release-lane changes completed for this stack:

- packaged branding assets now ship in both the wheel and source distribution through `pyproject.toml` and `MANIFEST.in`
- `scripts/build_release_artifacts.py` and `scripts/validate_installed_artifact.py` now assert that the packaged GUI branding assets are present in release artifacts
- added `scripts/run_empirical_review_stack.py` to perform the clean-install walkthrough, packaged GUI screenshot capture, and release-evidence readability checks
- tightened `README.md` with installed-artifact quickstart guidance, support posture, known limitations, and troubleshooting
- updated `CHANGELOG.md` with the packaged-GUI and support-boundary posture for the public `0.1.0` release candidate

Release-root validation in the approved environment:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 55 tests in 1.322s` / `OK`

Fresh artifact and installed-package validation:

- `python scripts/build_release_artifacts.py`
- result: `artifact_contract="passed"`
- `python scripts/validate_installed_artifact.py`
- result:
	- `import_contract="passed"`
	- `entrypoint_help="passed"`
	- `entrypoint_describe="passed"`
	- `gui_entrypoint="passed"`
	- `evidence_export="passed"`
	- `integration_bundle="passed"`
	- `distribution_files="passed"`
	- `installed_artifact_contract="passed"`

Empirical review runner confirmation:

- `python scripts/run_empirical_review_stack.py`
- archived artifacts:
	- `temp/fs_p05_empirical_review/empirical_review_summary.md`
	- `temp/fs_p05_empirical_review/empirical_review_summary.json`
	- `temp/fs_p05_empirical_review/sprint_close_bundle.md`
	- `temp/fs_p05_empirical_review/evidence/blocked_review.md`
	- `temp/fs_p05_empirical_review/evidence/failure_review.md`
	- `temp/fs_p05_empirical_review/screenshots/ready.png`
	- `temp/fs_p05_empirical_review/screenshots/blocked.png`
	- `temp/fs_p05_empirical_review/screenshots/failure.png`

Human-visible GUI review notes from the packaged screenshots:

- `ready.png` shows the branded header, readable control deck, and the expected ready-state summaries across the five dashboard panels
- `blocked.png` shows the blocked gate state with readable red-accent preflight findings and the expected package mismatch posture
- `failure.png` shows the failed transport state with readable normalized failure details and recovery-oriented evidence framing
- the screenshot runner now sanitizes stale `QT_QPA_PLATFORM=offscreen` shell state before capture so Windows empirical review uses the real Qt backend rather than the headless plugin

Evidence readability notes from the archived Markdown exports:

- `blocked_review.md` keeps the recovery guidance explicit and keeps the blocking trust findings readable in the decision trace
- `failure_review.md` preserves the normalized failure reason `USB transfer timeout during partition write` and the expected recovery guidance to stabilize the USB path before retry

## Validation record for `FS-P05`

| Validation type                      | Outcome |
| ------------------------------------ | ------- |
| `.venv-core` full unit-test suite    | passed  |
| fresh release artifact build         | passed  |
| installed-artifact validation        | passed  |
| clean-install quickstart walkthrough | passed  |
| packaged GUI screenshot review       | passed  |
| evidence readability review          | passed  |
| support posture pinning              | passed  |

### Proven vs stubbed after `FS-P05`

#### Proven

- the built wheel and source distribution now carry the packaged branding assets required by the public GUI shell
- a clean installed-wheel walkthrough succeeded for installed help, ready describe-only usage, and sprint-close bundle generation
- packaged GUI review now includes readable, branded screenshots for the ready, blocked, and failed scenarios rather than only offscreen smoke confirmation
- exported Markdown evidence remained readable and recovery-oriented for both blocked and failed review paths
- the public `0.1.0` support posture is now pinned explicitly: Windows packaged build empirically reviewed, core flashing workflow simulation-validated, and live companion controls limited to bounded lab/device-control review

#### Stubbed / deferred

- registry-delivered artifact rehearsal remains deferred to `FS-P06`
- live firmware flashing runtime remains outside the published `0.1.0` support boundary
- non-Windows packaged-host empirical review remains outside the `FS-P05` closeout scope

### Carry-forward debt into `FS-P06`

- perform the TestPyPI rehearsal from the nested release root
- confirm install, entry-point, and metadata behavior from registry-delivered artifacts
- execute the final publication gate and go/no-go note for `0.1.0`

## `FS-P06` - TestPyPI rehearsal and publication gate

Executed from the nested release root to make the final `0.1.0` publication decision boundary explicit.

Release-lane changes completed for this stack:

- added `scripts/run_testpypi_rehearsal.py` to perform the TestPyPI rehearsal gate, artifact hash capture, metadata audit, uninstall/reinstall verification, and final go/no-go decision recording
- added release-root `.env` placeholder guidance for TestPyPI and PyPI token configuration and ignored it in `.gitignore`
- updated `README.md` and `CHANGELOG.md` so the public release surfaces point at the `FS-P06` rehearsal runner and the current publication state

Release-root validation in the approved environment:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 60 tests in 1.423s` / `OK`

Artifact and metadata rehearsal evidence:

- `python scripts/build_release_artifacts.py`
- current artifact set inspected by the `FS-P06` runner:
	- wheel: `calamum_vulcan-0.1.0-py3-none-any.whl`
	- sdist: `calamum_vulcan-0.1.0.tar.gz`
	- wheel sha256: `400fa06e688d8a41a5c348b759e5fa449edde4f45ce2ccdb364cd00e54d3d405`
	- sdist sha256: `d521b3c9ea90aeb6e5bbc76840e7881209f2aa15a9a891b1b924b3ef8909b779`

TestPyPI rehearsal runner confirmation:

- `python scripts/run_testpypi_rehearsal.py`
- archived artifacts:
	- `temp/fs_p06_testpypi_rehearsal/testpypi_rehearsal_summary.md`
	- `temp/fs_p06_testpypi_rehearsal/testpypi_rehearsal_summary.json`
	- `temp/fs_p06_testpypi_rehearsal/twine_check_stdout.txt`
	- `temp/fs_p06_testpypi_rehearsal/twine_check_stderr.txt`

Runner outcome:

- `twine check` passed for both release artifacts
- wheel tag audit recorded `py3-none-any`
- project metadata remained aligned to `name="calamum_vulcan"`, `version="0.1.0"`, and `requires-python=">=3.14,<3.15"`
- TestPyPI upload passed and published the candidate to `https://test.pypi.org/project/calamum-vulcan/0.1.0/`
- registry-delivered install validation passed
- uninstall and reinstall validation passed
- publication decision: `go`

Credential and registry surface recorded by the rehearsal runner:

- user-level `.pypirc` now exposes `[distutils]`, `[pypi]`, and `[testpypi]`
- upload readiness was satisfied through the shared user-level TestPyPI profile rather than a repo-local env token
- registry-delivered help, describe-only, sprint-close bundle, metadata, uninstall, reinstall, and GUI-entrypoint presence checks all passed in the clean validation environment

## Validation record for `FS-P06`

| Validation type                            | Outcome |
| ------------------------------------------ | ------- |
| `.venv-core` full unit-test suite          | passed  |
| release artifact presence and hash capture | passed  |
| local `twine check` for wheel and sdist    | passed  |
| credential surface audit                   | passed  |
| TestPyPI upload                            | passed  |
| registry-delivered install validation      | passed  |
| final publication decision                 | go      |

### Proven vs carry-forward after `FS-P06`

#### Proven

- the final publication-gate runner now records artifact hashes, wheel tags, credential readiness, and a durable go/no-go summary under `temp/fs_p06_testpypi_rehearsal/`
- the current wheel and sdist pass `twine check`, so the local distribution metadata and README rendering remain structurally valid before upload
- the TestPyPI upload path now succeeds from the nested release root and produces a registry-visible candidate at `https://test.pypi.org/project/calamum-vulcan/0.1.0/`
- registry-delivered install, uninstall, reinstall, integration-bundle, and metadata checks all pass in the clean validation environment
- the `0.1.0` publication boundary is now explicit and satisfied at the rehearsal level: the final gate returns `go`

#### Carry-forward

- warning-tier security debt remains in checksum placeholders, the real package archive importer, and Android-image suspiciousness heuristics
- non-Windows packaged-host empirical review remains outside the current `0.1.0` closeout evidence

### Re-entry conditions for `FS-P06`

- rerun `python scripts/run_testpypi_rehearsal.py` after any packaging, metadata, or dependency-surface change that materially affects the published artifact set
- keep the shared user-level `[testpypi]` profile or an equivalent env-token path available for future rehearsal uploads
- require the rehearsal summary to stay at `publication_decision="go"` before any follow-on public-release action

## Planning-capture audit and security backfill

**Backfill date:** 2026-04-18

### Coverage check

- the sprint and publication stacks were recorded in the active authority surfaces as execution progressed
- the later security and threat-model discussion after `FS-P06` lived in chat longer than it should have, which fell short of the same-day planning-capture rule used to prevent drift and data loss
- this section backfills that discussion into the evidence ledger and aligns the master roadmap document with the resulting decisions

### Backfilled planning decisions from the conversation

| Topic               | Decision captured                                                                                                                                                                                          |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| operator visibility | device identity, product code, mode, and package truth remain visible by default because they are operational necessities                                                                                  |
| security focus      | the primary security concern is the incoming package plus execution-path integrity, not hiding phone data from the operator                                                                                |
| override philosophy | structurally unsafe intake remains blocked; suspicious but intentional custom-package traits surface as bypassable warnings                                                                                |
| feasibility posture | the platform can provide strong integrity and suspiciousness signals, but final judgment on novel custom images remains operator-informed                                                                  |
| current strengths   | the state reducer, guard model, preflight gate, and execute-action gating already resist casual path skipping                                                                                              |
| current gaps        | package intake is still fixture-driven, checksum values are placeholders, no safe archive importer exists, no sealed analyzed-package snapshot exists, and no Android-image heuristics are implemented yet |

### Current code-backed posture after the audit

| Surface                                           | Current posture                                                                                                                                                                     |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `calamum_vulcan/domain/state/reducer.py`          | execution only starts from `READY_TO_EXECUTE` and rejects out-of-order transitions                                                                                                  |
| `calamum_vulcan/domain/state/model.py`            | guard readiness requires device, package, preflight completion, and acknowledgements                                                                                                |
| `calamum_vulcan/domain/preflight/evaluator.py`    | destructive and warning-gated flows stay blocked until the operator closes them                                                                                                     |
| `calamum_vulcan/domain/package/parser.py`         | package truth is typed and test-backed, but still limited to manifest structure and fixture data                                                                                    |
| `calamum_vulcan/adapters/heimdall/normalizer.py`  | transport normalization is bounded, but still needs adversarial hardening for hostile output cases                                                                                  |
| `calamum_vulcan/validation/security.py`           | release-lane security validation now scans for dangerous Python patterns, unsafe `extractall` usage, and missing companion timeouts while recording warning-tier carry-forward debt |
| `calamum_vulcan/adapters/adb_fastboot/runtime.py` | ADB/Fastboot companion subprocesses now time out after `30` seconds and emit a deterministic timeout result instead of hanging indefinitely                                         |

### Carry-forward security requirements now pinned for future work

- add a real package importer that uses the now-pinned safe archive extraction and path normalization boundary
- replace checksum placeholders with real SHA-256 verification over the analyzed payload set
- seal the analyzed package snapshot and re-verify it immediately before execution
- add Android-image heuristics that surface root, tamper, and integrity-disablement traits as explicit warnings
- add adversarial tests for package import, manifest parsing, and backend-output normalization

This backfill began as a planning and evidence correction. The first shared hardening slice is now implemented, but the deferred importer, checksum, snapshot, and heuristics work above remains open.

## Security validation integration and publication-lane rerun

**Execution date:** 2026-04-18

Implemented security-hardened release-lane changes:

- added `calamum_vulcan/validation/security.py` and `scripts/run_security_validation_suite.py` as the shared security-validation boundary for publication-lane closure
- wired the shared suite into `scripts/build_release_artifacts.py`, `scripts/validate_installed_artifact.py`, `scripts/run_scripted_simulation_suite.py`, `scripts/run_empirical_review_stack.py`, and `scripts/run_testpypi_rehearsal.py`
- replaced the FS-P04 wheel extraction path with `safe_extract_zip_archive(...)` so the simulation runner no longer relies on raw `extractall(...)`
- bounded ADB/Fastboot live companion subprocesses with `PROCESS_TIMEOUT_SECONDS = 30` and added timeout-path unit coverage

Validation rerun in the approved environment:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- result: `Ran 60 tests in 1.423s` / `OK`

Standalone security suite confirmation:

- `python scripts/run_security_validation_suite.py`
- decision: `passed_with_warnings`
- blocking findings: `0`
- warnings: `8`

Publication-lane rerun summary after wiring the shared security gate:

| Stack    | Runner                                            | Result                                  | Security result        |
| -------- | ------------------------------------------------- | --------------------------------------- | ---------------------- |
| `FS-P02` | `python scripts/build_release_artifacts.py`       | `artifact_contract="passed"`            | `passed_with_warnings` |
| `FS-P03` | `python scripts/validate_installed_artifact.py`   | `installed_artifact_contract="passed"`  | `passed_with_warnings` |
| `FS-P04` | `python scripts/run_scripted_simulation_suite.py` | `scripted_simulation_contract="passed"` | `passed_with_warnings` |
| `FS-P05` | `python scripts/run_empirical_review_stack.py`    | `empirical_review_contract="passed"`    | `passed_with_warnings` |
| `FS-P06` | `python scripts/run_testpypi_rehearsal.py`        | `publication_decision="go"`             | `passed_with_warnings` |

Current warning-tier carry-forward debt reported by the shared suite:

- package fixtures still rely on placeholder checksum coverage for selected images
- package intake remains fixture-driven; no real package archive importer exists yet
- Android-image suspiciousness heuristics are still unimplemented

Current publication-gate status after the rerun:

- local build, installed-artifact validation, scripted simulation, and empirical review all remain green with no blocking security findings
- `FS-P06` now passes with a successful TestPyPI upload and registry-delivered validation from the nested release root
- the publication lane now has an explicit per-stack security closure rule rather than treating security as a separate late-stage discussion

## Release-admin follow-up after the green rehearsal gate

**Execution date:** 2026-04-19

The release-admin lane resumed after the green `FS-P06` rehearsal to convert the candidate boundary into the real public `0.1.0` release boundary.

### Final validation rerun before sealing

Release-root validation was rerun from the current tree in the approved environment before the git boundary was sealed.

Observed results:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
	- result: `Ran 62 tests in 4.087s` / `OK`
- `python scripts/build_release_artifacts.py`
	- result: `artifact_contract="passed"`
	- security result: `passed_with_warnings`
- `python scripts/validate_installed_artifact.py`
	- result: `installed_artifact_contract="passed"`
	- security result: `passed_with_warnings`
- `python scripts/run_scripted_simulation_suite.py`
	- result: `scripted_simulation_contract="passed"`
	- security result: `passed_with_warnings`
- `python scripts/run_empirical_review_stack.py`
	- result: `empirical_review_contract="passed"`
	- security result: `passed_with_warnings`
- `python scripts/run_testpypi_rehearsal.py`
	- result: `publication_decision="go"`
	- security result: `passed_with_warnings`

Artifact hashes from the final rerun before sealing:

- wheel `calamum_vulcan-0.1.0-py3-none-any.whl`: `5b54aa69d3fdba5ca654b7b4e79a2c760e00aaa01fa0a675252789b2ef7617e2`
- sdist `calamum_vulcan-0.1.0.tar.gz`: `47e04409730546dc728bc8c92d4458a2c6cc6d76549f33917fdb1a25268e52ff`

### Git boundary closure

The sealed closeout boundary was created successfully from the nested release root.

Observed git outcomes:

- final release commit created:
	- short SHA: `d11a4ac`
	- full SHA: `d11a4ace26027aba944f03e61c63c3350477a0f7`
	- message: `feat(release): finalize 0.1.0 release tree`
- `main` pushed successfully to `origin`
- annotated tag `v0.1.0` created and pushed successfully to `origin`

This closes the git-boundary portion of the `0.1.0` closeout checklist.

### GitHub release attempt

The GitHub release object could not be created from the current workstation because the local authentication surface failed.

Observed blockers:

- `gh auth status` reported the active `github.com` account token in keyring as invalid
- browser navigation to the GitHub release-creation page redirected to the GitHub sign-in screen instead of an authenticated release form

Current consequence:

- the sealed tag exists publicly on GitHub
- the repository does **not** yet have a published GitHub release object for `v0.1.0`

### Real PyPI publication attempt

The first production upload attempt to the real PyPI index did **not** complete.

Observed production upload result:

- `python -m twine upload --repository pypi --non-interactive dist/*`
	- result: `403 Forbidden`
- verbose retry showed the server-side rejection reason:
	- `Invalid API Token: project-scoped token is not valid for project: 'calamum-vulcan'`

Follow-up verification from the consumer side:

- `python -m pip index versions calamum-vulcan`
	- result: `ERROR: No matching distribution found for calamum-vulcan`

Current consequence:

- the production PyPI project page for `calamum-vulcan` is still not populated by this release attempt
- the real-PyPI install-validation step remains blocked until a valid production token for `calamum-vulcan` is supplied

### Closeout posture after the admin follow-up

| Surface | Status | Evidence |
| ------- | ------ | -------- |
| git release commit | completed | `d11a4ace26027aba944f03e61c63c3350477a0f7` |
| `origin/main` push | completed | push result from 2026-04-19 |
| annotated tag `v0.1.0` | completed | tag push result from 2026-04-19 |
| GitHub release object | blocked by auth | invalid `gh` keyring token and unauthenticated browser session |
| real PyPI publication | blocked by auth | invalid project-scoped token for `calamum-vulcan` |
| real PyPI install validation | blocked by missing publication | package not visible via `pip index versions` |

## Next active surface

The `0.1.0` rehearsal gate is satisfied and the git release boundary is now sealed publicly through `origin/main` plus tag `v0.1.0`. The next active surface is still the `0.1.0` closeout lane, not `0.2.0`: repair the GitHub authentication surface, replace the invalid production PyPI token with one authorized for `calamum-vulcan`, complete the GitHub release and real PyPI publication, verify the live install path, and only then promote `0.2.0` planning to the active lane.
