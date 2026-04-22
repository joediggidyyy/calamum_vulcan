# Calamum Vulcan — Samsung-focused Android Flashing Platform `0.5.0` Execution Evidence

## Purpose

This file is the compact evidence ledger for Sprint 5 / `0.5.0`.

Unlike the fully closed `0.3.0` evidence surface, this document began in a **planned** state. It now records the completed `FS5-01` foundation closeout, the completed `FS5-02` session-authority closeout, the completed `FS5-03` alignment-hardening closeout, the completed `FS5-04` fallback-identity closeout, the completed `FS5-05` bounded safe-path transport closeout, and the 2026-04-23 package-boundary closeout updates for `FS5-06`, `FS5-07`, and `FS5-08`.

## Active authority set

The active local authority set for this evidence surface is:

- `docs/Samsung_Android_Flashing_Platform_Research_Report_and_Build_Plan.md`
- `docs/Samsung_Android_Flashing_Platform_0.3.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.3.0_Execution_Evidence.md`
- `docs/Samsung_Android_Flashing_Platform_0.3.0_Closeout_and_Prepackage_Checklist.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Closeout_and_Prepackage_Checklist.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Testing_and_Readiness_Plan.md`

For tracked/public release truth, the sprint should continue to defer to the current repo state in:

- `pyproject.toml`
- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/workflows/python-publish.yml`

## Stack register

| Stack    | Status    | Current planning anchor      | Planned closeout result                                                                                                                                                                  |
| -------- | --------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `FS5-01` | completed | 2026-04-21                   | scope, ownership surfaces, validation ritual, evidence surface, safe-path anchor, session-authority anchor, and planned `safe-path-close` contract are pinned                            |
| `FS5-02` | completed | 2026-04-21                   | authoritative session and launch-state truth now exists across state, reporting, recovery guidance, and operator-facing shell surfaces                                                   |
| `FS5-03` | completed | 2026-04-21                   | device/package/PIT alignment now hard-blocks or narrows bounded safe-path claims across preflight, authority, reporting, and shell surfaces                                              |
| `FS5-04` | completed | 2026-04-21                   | live-path fallback identity now carries explicit ownership, delegated labels, confidence, summary, and guidance across authority, reporting, shell, CLI, and packaged-context validation |
| `FS5-05` | completed | 2026-04-21                   | one narrow safe-path transport lane is platform-governed with explicit ownership boundaries while Heimdall remains visibly delegated lower transport                                     |
| `FS5-06` | completed | 2026-04-23                   | runtime hygiene, Heimdall detect taxonomy, contextual recovery continuation, disconnect-field clearing, and Qt close-thread stability now remain credible under the extracted safe-path shell |
| `FS5-07` | completed | 2026-04-23                   | `safe-path-close` evidence, security validation, empirical review, installed-artifact proof, and the multi-lane Sprint 5 readiness sweep now align for the package-only candidate         |
| `FS5-08` | completed | 2026-04-23                   | the local `0.5.0` package boundary metadata, closeout framing, and readiness proof are aligned while renewed registry publication remains deferred to `1.0.0`                            |

## Current activation note

As of 2026-04-23:

- `0.3.0` is already live on GitHub and PyPI.
- `FS5-01` is now closed locally with pinned session-authority and safe-path foundation anchors.
- `FS5-02` is now closed locally with a state-owned session-authority snapshot propagated through reporting and operator-facing shell surfaces.
- `FS5-03` is now closed locally with PIT-aware preflight hardening, narrower session-authority readiness for ambiguous alignment truth, and shell/reporting surfaces that now carry PIT/device alignment beside PIT/package alignment.
- `FS5-04` is now closed locally with repo-owned live-path identity, richer fastboot/delegated fallback labeling, CLI/reporting/shell propagation, and packaged-context proof that still preserves the warning-tier suspicious-review lane.
- `FS5-05` is now closed locally with authority-aware bounded runtime admission, a first-class CLI safe-path execute lane, explicit platform-supervised governance wording in reporting/shell/log surfaces, and installed/source parity proof for both ready and blocked execute paths.
- `FS5-06` is now closed locally with the real `Read PIT`, `Load package`, `Execute flash plan`, and `Continue after recovery` GUI workflow, explicit disconnect-field clearing, Heimdall detect diagnostic capture/taxonomy hardening, and Qt thread-lifecycle stabilization under the UNC `.venv-core` baseline.
- `FS5-07` is now closed locally with the deterministic `safe-path-close` bundle plus green source, installed-artifact, scripted-simulation, empirical-review, and aggressive-penetration readiness proof under `temp/fs5_readiness/`.
- `FS5-08` is now closed locally as a **package-only** boundary: the tracked package metadata is aligned to `0.5.0`, the readiness summary is green, and renewed TestPyPI/PyPI publication remains intentionally deferred to the immediate post-`0.6.0` `1.0.0` promotion lane.
- the repository-visible Sprint 5 seal is the pushed tag `v0.5.0`; the latest stable GitHub release object and live PyPI release intentionally remain at `0.3.0`.
- these `0.5.0` planning and evidence surfaces remain local-first even after the repo-visible tag seal because stable public promotion is intentionally deferred.

## Final Sprint 5 seal record on 2026-04-23

The Sprint 5 package-only boundary is now sealed with the following exact references:

- sealed repository-visible tag: `v0.5.0`
- repository-visible tag URL: `https://github.com/joediggidyyy/calamum_vulcan/tree/v0.5.0`
- latest stable GitHub release object remains `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.3.0`
- latest stable PyPI release remains `https://pypi.org/project/calamum-vulcan/0.3.0/`
- GitHub release-object creation remained intentionally unexercised for Sprint 5 so the boundary stays a tagged package milestone rather than a stable public promotion event
- release workflow proof remains the explicit dormant-publication posture carried in `.github/workflows/python-publish.yml`; no new Sprint 5 publication run was invoked

Final artifact hashes for the sealed candidate:

- `dist/calamum_vulcan-0.5.0.tar.gz` — `948EF2566849596C7AAB7694E108BB9C9408BC9225F2593A70519E45D7432805`
- `dist/calamum_vulcan-0.5.0-py3-none-any.whl` — `81DAA28566424D88F5A19B415151CCCA028546AE86969152A61FD4BEDFD6B52F`

Final validation references for the sealed candidate:

- `temp/fs5_readiness/readiness_summary.json`
- `temp/v040_timeline_audit/v040_timeline_audit.json`
- `temp/fs5_readiness/build_artifacts/stdout.txt`
- `temp/fs5_readiness/sandbox_installed_artifact/stdout.txt`
- `temp/fs5_readiness/scripted_simulation/stdout.txt`
- `temp/fs5_readiness/empirical_review/stdout.txt`

Carry-forward authority after the seal is now bounded to:

- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md` for efficient integrated transport extraction
- `docs/Samsung_Android_Flashing_Platform_0.6.0_Execution_Surface.md` for the fully functional no-external-Heimdall autonomy closeout target
- `docs/Samsung_Android_Flashing_Platform_1.0.0_Promotion_Gate.md` for the immediate post-`0.6.0` public-promotion gate

## Sprint 5 closeout update on 2026-04-23

The local Sprint 5 closeout proof now includes all of the following package-boundary evidence:

- `temp/fs5_readiness/readiness_summary.json` reports `overall_status="passed"` across all 7 active lanes
- `temp/v040_timeline_audit/v040_timeline_audit.json` now reports `15` implemented criteria, `0` partial items, `0` open items, and `0` notable deviations for the aligned `0.5.0` package boundary
- `tests/unit/test_qt_shell_contract.py` now passes fully under the UNC `.venv-core` baseline after stabilizing worker-thread lifetime, close-event teardown, and chained detect/info handoffs
- the `safe-path-close` JSON and Markdown bundles are now first-class integrated outputs rather than planned-only closeout targets

## Readiness-preparation work completed on 2026-04-21

The following Sprint 5 preparation work is now complete:

- a dedicated testing and readiness plan exists at `docs/Samsung_Android_Flashing_Platform_0.5.0_Testing_and_Readiness_Plan.md`
- a runnable multi-strategy readiness orchestrator now exists at `scripts/run_v040_readiness_stack.py`
- the readiness plan explicitly schedules `pytest`, sandbox, scripted simulation, empirical review, aggressive penetration-style validation, and near-end registry rehearsal

This closes the planning gap where Sprint 5 previously described validation categories but did not yet pin an implementation-facing schedule for them.

## Carry-forward inputs inherited from `0.3.0`

Sprint 5 starts with the following known carry-forward inputs:

1. **Session truth should become more authoritative.**
   `0.3.0` established meaningful read-side evidence, but session and launch-state truth still need a cleaner, more explicit authority surface.
2. **Device/package/PIT alignment needs stronger enforcement.**
   The sprint should decide how much of the current descriptive alignment truth becomes runtime or preflight gating.
3. **Fastboot and delegated fallback identity still need richer treatment.**
   If Heimdall is going to narrow to selective fallback, the remaining fallback lanes must be easier to see and reason about.
4. **Detached GUI host hygiene remains under observation.**
   Runtime clarity, transcript boundaries, and export discipline still matter as the platform absorbs more live-path responsibility.
5. **Renewed registry publication remains intentionally deferred.**
   Sprint `0.5.0` now closes as a local package-only boundary, so TestPyPI/PyPI rehearsal is preserved only as carry-forward input for the immediate post-`0.6.0` `1.0.0` promotion lane.
6. **Tag-frozen workflow history remains contextual release-admin background, not a Sprint 5 exit gate.**
   Historical reruns on old tags can still execute older workflow definitions, but that behavior is now carry-forward release infrastructure context rather than an active Sprint 5 blocker.

## Expected validation regime for Sprint 5

| Validation surface            | Planned expectation                                                                                                                    |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| targeted logic tests          | session, alignment, fallback, reporting, and integration behavior stay covered as the sprint opens                                     |
| deterministic closeout bundle | a new `safe-path-close` bundle should exist and should agree with the claimed Sprint 5 support posture                                 |
| installed-artifact validation | entry points, help output, evidence export, and closeout surfaces should keep working from an installed artifact                       |
| shared security validation    | adversarial parser and release-lane hardening remain mandatory gates rather than afterthoughts                                         |
| empirical review              | visible runtime-status, transcript, and fallback honesty should be checked whenever operator-facing surfaces change materially         |
| package-boundary validation   | the exact `0.5.0` candidate should be packaged, installed, audited, and sealed locally while renewed registry publication stays deferred |

## Scheduled readiness lane map

| Lane                                  | Primary command surface                                                                                                                                              | Current planning status             |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `pytest` baseline                     | `python -m pytest tests/unit -q`                                                                                                                                     | scheduled                           |
| aggressive penetration-style `pytest` | `python -m pytest tests/unit/test_security_validation.py tests/unit/test_package_importer.py tests/unit/test_package_snapshot.py tests/unit/test_pit_contract.py -q` | scheduled                           |
| aggressive penetration-style suite    | `python scripts/run_security_validation_suite.py`                                                                                                                    | scheduled                           |
| sandbox installed-artifact            | `python scripts/build_release_artifacts.py` + `python scripts/validate_installed_artifact.py`                                                                        | scheduled                           |
| scripted simulation                   | `python scripts/run_scripted_simulation_suite.py`                                                                                                                    | scheduled                           |
| empirical review                      | `python scripts/run_empirical_review_stack.py`                                                                                                                       | scheduled                           |
| release rehearsal                     | `python scripts/run_testpypi_rehearsal.py`                                                                                                                           | deferred to the immediate post-`0.6.0` `1.0.0` promotion lane |

The orchestration surface for these lanes is `scripts/run_v040_readiness_stack.py`, which writes the aggregate readiness summary under `temp/fs5_readiness/`.

## Expected evidence anchors

The Sprint 5 lane is expected to create or refresh evidence around at least the following anchors:

- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Closeout_and_Prepackage_Checklist.md`
- deterministic `safe-path-close` JSON/Markdown outputs
- installed-artifact validation outputs for the Sprint 5 candidate
- shared security-validation outputs for the Sprint 5 candidate
- trusted-publication rehearsal or validation notes tied to the exact release candidate and workflow route

## Planned stack closeout targets

## `FS5-01` — Foundation declarations and safe-path acceptance criteria

### Stack goal

Start Sprint `0.5.0` with clear boundaries, acceptance criteria, validation carry-forward rules, and concrete session-authority / safe-path ownership seams so later stacks can execute without re-litigating where reviewed truth ends, where live truth begins, and how bounded safe-path claims must be labeled.

### Frame 1 — Bounds, priorities, and stack ordering pinned

**Result:** completed

Confirmed for `0.5.0`:

- the release remains a **structural extraction** sprint rather than a default-native-transport sprint
- the primary ownership gains are **authoritative session truth**, **device/package/PIT alignment hardening**, **richer fallback identity**, **one bounded safe-path transport lane**, **runtime hygiene**, and **trusted-publication restoration**
- the completed `0.3.0` public boundary remains closed unless a real defect is found
- the first implementation slice should retire the three most urgent Sprint 5 debts first:
   - missing explicit session-authority vocabulary above the existing `state` package
   - missing repo-owned safe-path vocabulary for native/delegated/fallback/blocked claims
   - missing code-level naming for the planned `safe-path-close` closeout suite

Execution order for the sprint remains pinned as:

1. `FS5-01` foundation declarations and safe-path acceptance criteria
2. `FS5-02` session-layer authority and launch-state extraction
3. `FS5-03` device/package/PIT alignment hardening
4. `FS5-04` fallback identity and fastboot session extraction
5. `FS5-05` bounded safe-path transport responsibility
6. `FS5-06` runtime hygiene, transcript policy, and operator-surface honesty
7. `FS5-07` selective fallback discipline, trusted-publication rehearsal, broad security gate, empirical closure, and sprint-close evidence
8. `FS5-08` closeout checklist, prepackage freeze, trusted-publication validation, packaging boundary, and publication move

### Frame 2 — Ownership surfaces chosen and anchors pinned

**Result:** completed

Pinned the near-term `0.5.0` ownership surfaces around the existing state, reporting, GUI, validation, adapter, and integration seams plus one new domain package anchor and one new state-level authority anchor:

| Surface                                    | `0.5.0` role                                                                                                               |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `calamum_vulcan/domain/state/authority.py` | session-authority vocabulary, truth-surface naming, and split reviewed/live/fallback posture                               |
| `calamum_vulcan/domain/safe_path/`         | bounded safe-path vocabulary, ownership labels, evidence requirements, and planned closeout-suite naming                   |
| `calamum_vulcan/domain/reporting/`         | later session-authority and safe-path evidence export                                                                      |
| `calamum_vulcan/app/integration.py`        | planned `safe-path-close` naming in the app-layer closeout seam without prematurely exposing it as a public runnable suite |

The new `0.5.0` anchors are now pinned concretely at:

- `calamum_vulcan/domain/state/authority.py`
- `calamum_vulcan/domain/safe_path/__init__.py`
- `calamum_vulcan/domain/safe_path/model.py`

Touched surfaces for the anchor pass:

- `calamum_vulcan/domain/__init__.py`
- `calamum_vulcan/domain/state/__init__.py`
- `calamum_vulcan/domain/state/authority.py`
- `calamum_vulcan/domain/safe_path/__init__.py`
- `calamum_vulcan/domain/safe_path/model.py`
- `calamum_vulcan/app/integration.py`
- `tests/unit/test_fs5_foundation_anchors.py`

Concrete implementation outcomes:

- created a repo-owned `safe_path` domain package as the explicit Sprint `0.5.0` anchor for bounded safe-path work
- added `SafePathContract`, `SafePathScope`, `SafePathOwnership`, `SafePathReadiness`, `SAFE_PATH_SCHEMA_VERSION`, and `SAFE_PATH_CLOSE_SUITE_NAME`
- added `SessionAuthorityContract`, `SessionAuthorityPosture`, `SessionTruthSurface`, and `SESSION_AUTHORITY_SCHEMA_VERSION` under the existing `state` package
- extended `calamum_vulcan.domain.__all__` so the root domain surface now acknowledges the new `safe_path` package
- extended the `state` package exports so later stacks can import the new authority contract without inventing parallel state seams mid-sprint
- added a planned app-layer integration constant path so `safe-path-close` is named in code but not yet falsely advertised as a live public integration suite

### Frame 3 — Validation ritual pinned for the active sprint

**Result:** completed

The `0.5.0` validation ritual is now pinned in both planning surfaces and code-facing prep work.

Expected per-stack validation now includes:

1. the standing `pytest` / logic suite for touched state, reporting, adapter, closeout, and GUI surfaces
2. the shared security validation suite for any stack touching fallback labeling, session truth, transcripts, publication boundaries, or other trust surfaces
3. targeted adversarial / penetration-style tests for new trust surfaces such as hidden fallback drift, malformed alignment inputs, contradictory live/read-side truth, and unsafe publication-boundary assumptions
4. targeted sandbox installed-artifact validation whenever public CLI, GUI, evidence, or closeout surfaces change materially
5. targeted scripted simulation whenever session truth, fallback wording, or evidence surfaces change materially
6. empirical packaged review when operator-visible status, layout, or evidence readability changes materially
7. a near-end registry / publication rehearsal gate before the public `0.5.0` boundary moves

Validation-regime carry-forward note:

- the new readiness schedule and orchestration surface created earlier in this session now serve as the concrete Sprint 5 testing cadence rather than remaining background intent only
- trusted-publication restoration remains a later boundary concern rather than a false claim of `FS5-01`

### Frame 4 — `0.5.0` evidence surface and planned closeout-suite naming established

**Result:** completed

Concrete evidence outcomes:

- this execution evidence surface now records `FS5-01` as completed rather than planned only
- the `safe-path-close` closeout suite name is now pinned in code through the new safe-path anchor and the app integration helper
- the app layer now distinguishes between available integrated suites and planned integrated suites so Sprint 5 can name its target closeout bundle without pretending it is already implemented

### Frame 5 — Contract review against roadmap, schema rules, and release posture

**Result:** completed

Short alignment review outcome:

| Check                                                                    | Result |
| ------------------------------------------------------------------------ | ------ |
| six-sprint ladder preserved                                              | yes    |
| Sprint `0.5.0` still framed as efficient integrated transport extraction          | yes    |
| `0.3.0` public boundary remains closed by default                        | yes    |
| local `docs/` / `temp/` working-surface rule preserved                   | yes    |
| shared security validation remains mandatory for trust-boundary stacks   | yes    |
| planned `safe-path-close` suite named without false implementation claim | yes    |
| no false `0.5.0` default-native-transport claim introduced               | yes    |

## Validation record for `FS5-01`

| Validation type                             | Outcome |
| ------------------------------------------- | ------- |
| planning-surface review                     | passed  |
| stack-to-roadmap contract consistency check | passed  |
| modified-file error scan                    | passed  |
| focused FS5-01 anchor regression            | passed  |
| `.venv-core` full pytest baseline           | passed  |

Automated validation runs used for stack closeout:

- `functions.get_errors` against the touched domain, integration, and test files
   - result: no errors found in any edited code or test file
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_fs5_foundation_anchors.py -q`
   - result: `4 passed in 0.40s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit -q`
   - result: `175 passed, 4 subtests passed in 8.68s`

### Proven behavior

- Sprint `0.5.0` now has a repo-owned `safe_path` domain package instead of leaving bounded safe-path vocabulary as prose-only planning debt
- the `state` package now exports a dedicated session-authority contract so reviewed, live, inspection, and fallback truth can be named explicitly in later implementation stacks
- the app integration layer now distinguishes between available closeout suites and planned closeout suites, so `safe-path-close` is pinned in code without falsely reading as already implemented

### Stubbed / intentionally deferred behavior

- the deterministic `safe-path-close` bundle is still planned rather than implemented; it is named, not yet runnable
- session-authority vocabulary was pinned here first, and fuller reporting / operator-surface propagation was intentionally deferred to `FS5-02`
- trusted-publication restoration is still future Sprint 5 work rather than a false closeout claim of `FS5-01`

### Carry-forward debt

- decide which device/package/PIT mismatch shapes hard-block or narrow any future safe-path lane in `FS5-03`
- keep the new session-authority snapshot as the single source of launch-state truth while `FS5-03` and `FS5-04` deepen alignment and fallback semantics
- implement the real `safe-path-close` integrated bundle before Sprint `0.5.0` closeout evidence claims bundle-level support

## `FS5-02` — Session-layer authority and launch-state extraction

### Stack goal

Make session and launch-state truth authoritative rather than reconstructed so the same reviewed/live/fallback story is visible in state, exported evidence, recovery guidance, and operator-facing shell surfaces.

### Frame 1 — Session and launch-state vocabulary pinned

**Result:** completed

Pinned the Sprint `0.5.0` session-authority vocabulary around these explicit surfaces:

- reviewed phase versus live phase remain separate on purpose
- selected launch path is explicit (`standby`, `review_only`, `safe_path_candidate`, `fallback_review`, `blocked`)
- current ownership is explicit (`native`, `delegated`, `fallback`, `blocked`)
- safe-path readiness is explicit (`unreviewed`, `ready`, `narrowed`, `blocked`)
- clear/refresh semantics are explicit instead of being implied by scattered shell heuristics

### Frame 2 — State-owned authority snapshot implemented

**Result:** completed

Touched state surfaces:

- `calamum_vulcan/domain/state/authority.py`
- `calamum_vulcan/domain/state/__init__.py`
- `tests/unit/test_session_authority_contract.py`

Concrete implementation outcomes:

- added `SessionAuthoritySnapshot` with schema version `0.5.0-fs5-02`
- added `SessionLaunchPath` and `SessionRefreshState`
- implemented `build_session_authority_snapshot(...)` as the state-owned launch-state authority helper
- preserved the explicit reviewed-target label `No Download-Mode Target` so live phase overrides do not collapse the reviewed/live split back into ambiguous status wording

### Frame 3 — Reporting, summaries, and shell surfaces now consume the same authority truth

**Result:** completed

Touched propagation surfaces:

- `calamum_vulcan/domain/reporting/model.py`
- `calamum_vulcan/domain/reporting/__init__.py`
- `calamum_vulcan/domain/reporting/builder.py`
- `calamum_vulcan/app/view_models.py`
- `tests/unit/test_reporting_contract.py`
- `tests/unit/test_shell_view_models.py`

Concrete implementation outcomes:

- added first-class `authority` evidence to the session-report contract
- session evidence JSON and Markdown now export launch path, ownership, readiness, fallback-active posture, block reason, refresh posture, and an authority summary
- recovery guidance, decision trace, and log lines now carry the same authority surface instead of relying only on preflight or phase fragments
- the shell now binds its operator-facing phase label from the state-owned authority snapshot and surfaces authority details in the transport and evidence panels

### Frame 4 — Clear, refresh, and transition semantics pinned

**Result:** completed

Concrete lifecycle outcomes:

- `LiveDetectionState.CLEARED` with prior source labels now maps to `SessionRefreshState.CLEAR_REQUIRED` so stale live-path surfaces can be cleared explicitly
- degraded live detection, partial/failed inspection posture, and resume-needed states now map to `SessionRefreshState.REFRESH_RECOMMENDED`
- fallback-engaged lanes now keep fallback review explicit instead of falling back to generic blocked/standby wording

### Frame 5 — Boundary-case validation closed the stack

**Result:** completed

Touched validation surfaces:

- `tests/unit/test_session_authority_contract.py`
- `tests/unit/test_reporting_contract.py`
- `tests/unit/test_shell_view_models.py`

Concrete validation outcomes:

- added focused FS5-02 authority coverage for no-device, ready, blocked alignment, fallback review, and degraded live-output cases
- extended reporting tests to prove the new authority evidence is serialized and rendered
- extended shell-view-model tests to prove the operator-facing phase, launch-path details, and reviewed-target wording remain aligned to the new state-owned authority surface

## Validation record for `FS5-02`

| Validation type                   | Outcome |
| --------------------------------- | ------- |
| modified-file error scan          | passed  |
| focused FS5-02 pytest slice       | passed  |
| `.venv-core` full pytest baseline | passed  |

Automated validation runs used for stack closeout:

- `functions.get_errors` against the touched state, reporting, view-model, and test files
   - result: no errors found in any edited file
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_session_authority_contract.py tests/unit/test_reporting_contract.py tests/unit/test_shell_view_models.py -q`
   - result: `33 passed in 0.56s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit -q`
   - result: `180 passed, 4 subtests passed in 9.75s`

### Proven behavior

- the platform now has one state-owned authority snapshot for launch-path truth instead of reconstructing that story independently in reporting and shell helpers
- exported evidence, recovery guidance, decision traces, and shell panels now all carry the same launch-path, readiness, fallback, block, and refresh posture
- the shell still preserves the reviewed/live split honestly: a live phase such as `ADB Device Detected` can coexist with the explicit reviewed-target posture `No Download-Mode Target`

### Stubbed / intentionally deferred behavior

- stronger device/package/PIT alignment enforcement still belongs to `FS5-03`; `FS5-02` names and exports the authority surface but does not yet harden every narrowing rule
- richer fastboot/delegated identity remains `FS5-04` work even though fallback review is now named more explicitly
- the deterministic `safe-path-close` bundle remains planned rather than implemented

### Carry-forward debt

- bind the upcoming alignment-hardening outcomes directly into `SessionAuthoritySnapshot` narrowing/block rules in `FS5-03`
- enrich fallback/delegated identity inputs so the authority snapshot can describe those lanes with more than current bounded labels in `FS5-04`
- decide whether the immediate CLI inspect/control text output should surface the new authority snapshot directly or continue relying on the richer exported evidence lane first

## `FS5-03` — Device/package/PIT alignment hardening

### Stack goal

Turn reviewed device/package/PIT alignment truth into stronger preflight and session-authority gating so mismatched or under-specified alignment can block or narrow bounded safe-path claims instead of remaining descriptive evidence only.

### Frame 1 — Alignment grammar pinned for Sprint 5 gating

**Result:** completed

Pinned the active FS5-03 alignment grammar around these concrete states:

- PIT/package mismatch is now a first-class block rather than an evidence-only warning
- PIT/device mismatch is now a first-class block rather than an operator-inferred drift hint
- malformed or failed PIT truth is treated as untrustworthy for safe-path claims
- partial or under-specified PIT comparison truth now narrows readiness rather than silently passing as a full safe-path candidate

### Frame 2 — Preflight inputs now carry package and PIT review truth together

**Result:** completed

Touched gating surfaces:

- `calamum_vulcan/domain/preflight/model.py`
- `calamum_vulcan/domain/preflight/evaluator.py`
- `calamum_vulcan/domain/pit/builder.py`
- `calamum_vulcan/domain/pit/__init__.py`

Concrete implementation outcomes:

- added PIT-aware preflight fields for PIT state, package alignment, device alignment, and observed PIT product code
- added shared review-context helpers so package and PIT truth can be merged into one `PreflightInput` snapshot without duplicating override logic across layers
- added PIT-aware preflight rules for captured/partial/malformed/failed PIT posture plus PIT/package and PIT/device alignment outcomes

### Frame 3 — Session authority, reporting, and shell surfaces now enforce the same alignment truth

**Result:** completed

Touched propagation surfaces:

- `calamum_vulcan/domain/state/authority.py`
- `calamum_vulcan/domain/reporting/builder.py`
- `calamum_vulcan/app/view_models.py`

Concrete implementation outcomes:

- `SessionAuthoritySnapshot` now blocks on PIT/package mismatch, PIT/device mismatch, and untrustworthy PIT state even when a caller provides separate preflight and PIT objects
- `SessionAuthoritySnapshot` now narrows readiness when PIT truth is partial or when PIT/package or PIT/device comparison remains under-specified
- reporting and shell evidence now surface PIT/device alignment beside PIT/package alignment so operator-facing recovery guidance, evidence lines, and package detail rows all read from the same alignment truth

### Frame 4 — Ambiguous alignment no longer widens safe-path claims silently

**Result:** completed

Concrete narrowing outcomes:

- under-specified observed or reviewed PIT fingerprints now keep the safe-path lane visibly narrowed instead of looking fully clear
- package and evidence panels now reflect the narrower PIT posture with warning-tone summaries and explicit alignment detail lines
- authority block reasons now explain why a bounded safe-path lane stayed narrowed or blocked instead of falling back to generic support wording

### Frame 5 — Targeted and adversarial validation closed the stack

**Result:** completed

Touched validation surfaces:

- `tests/unit/test_preflight_rules.py`
- `tests/unit/test_pit_contract.py`
- `tests/unit/test_session_authority_contract.py`
- `tests/unit/test_reporting_contract.py`
- `tests/unit/test_shell_view_models.py`

Concrete validation outcomes:

- added focused regression coverage for PIT-aware preflight blocks and PIT-partial warning behavior
- added PIT override coverage so PIT inspection truth is proven to flow into preflight inputs deterministically
- added session-authority, reporting, and shell regressions for PIT/device mismatch and under-specified PIT fingerprint comparison

## Validation record for `FS5-03`

| Validation type                           | Outcome                                                                |
| ----------------------------------------- | ---------------------------------------------------------------------- |
| modified-file error scan                  | passed                                                                 |
| focused FS5-03 pytest slice               | passed                                                                 |
| `.venv-core` full pytest baseline         | passed                                                                 |
| aggressive penetration-style pytest slice | passed                                                                 |
| aggressive penetration-style suite        | passed_with_warnings                                                   |
| scripted simulation lane                  | materially passed after `dist/` refresh and direct artifact comparison |

Automated validation runs used for stack closeout:

- `functions.get_errors` against the touched preflight, PIT, authority, reporting, shell, and test files
   - result: no errors found in any edited file
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_preflight_rules.py tests/unit/test_session_authority_contract.py tests/unit/test_reporting_contract.py tests/unit/test_shell_view_models.py tests/unit/test_pit_contract.py -q`
   - result: `52 passed in 1.34s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit -q`
   - result: passed with exit code `0`; terminal summary was clipped before the final count
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_security_validation.py tests/unit/test_package_importer.py tests/unit/test_package_snapshot.py tests/unit/test_pit_contract.py -q`
   - result: `19 passed in 2.33s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/run_security_validation_suite.py`
   - result: `passed_with_warnings`, `0` blockers, `8` warnings
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/build_release_artifacts.py`
   - result: refreshed `dist/` artifacts so installed-context scripted validation used current FS5-03 code instead of a stale wheel
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/run_scripted_simulation_suite.py`
   - result: `progress.log` reached all source-root and installed-artifact scenarios plus both sprint-close bundles; direct comparison of generated artifacts confirmed exact parity for `describe.txt`, `evidence.json`, `evidence.md`, `gui_stderr.txt`, and both sprint-close bundles between source-root and installed-artifact contexts, with only timestamp-only drift in `gui_stdout.txt`

### Proven behavior

- preflight now blocks on PIT/package mismatch, PIT/device mismatch, and failed or malformed PIT truth instead of leaving those states as descriptive evidence only
- partial or under-specified PIT comparison truth now narrows session-authority readiness instead of silently preserving full safe-path confidence
- reporting and shell surfaces now propagate PIT/device alignment beside PIT/package alignment and use the same authority block reasons for recovery guidance and operator-visible detail lines

### Stubbed / intentionally deferred behavior

- richer fastboot or delegated fallback identity still belongs to `FS5-04`
- the deterministic `safe-path-close` bundle remains planned rather than implemented
- trusted-publication restoration remains later Sprint 5 boundary work rather than a claim of FS5-03 closeout

### Carry-forward debt

- keep the new PIT-aware authority rules aligned with upcoming richer fallback identity inputs in `FS5-04`
- decide whether later safe-path transport extraction should consume PIT narrowing state directly or only through the authority snapshot once `FS5-05` opens
- preserve the current evidence-based distinction between real alignment blocks and timestamp-only scripted GUI-output drift when Sprint 5 closeout evidence is consolidated

## `FS5-04` — Fallback identity and fastboot session extraction

### Stack goal

Make delegated and fallback live-path lanes explicit, evidence-bearing, and honest enough that operators can see exactly what kind of session truth they have without flattening those lanes into native-ready claims.

### Frame 1 — Repo-owned live-path identity schema pinned

**Result:** completed

Touched live-path contract surfaces:

- `calamum_vulcan/domain/live_device/model.py`
- `calamum_vulcan/domain/live_device/__init__.py`

Concrete implementation outcomes:

- added `LIVE_PATH_IDENTITY_SCHEMA_VERSION = '0.5.0-fs5-04'`
- added `LivePathOwnership` with explicit `none`, `native`, `delegated`, and `fallback` labels
- added `LiveIdentityConfidence` with explicit `unavailable`, `serial_only`, `product_resolved`, and `profiled` tiers
- added `LivePathIdentity` so live detection can carry path label, delegated label, mode truth, summary, and operator guidance as first-class repo-owned session truth
- extended `LiveDetectionSession` so fallback identity is part of the live-detection contract rather than a reporting-only reconstruction

### Frame 2 — Fastboot and delegated-session evidence enriched

**Result:** completed

Touched live-detection and reporting surfaces:

- `calamum_vulcan/domain/live_device/builder.py`
- `calamum_vulcan/adapters/adb_fastboot/normalizer.py`
- `calamum_vulcan/domain/reporting/model.py`
- `calamum_vulcan/domain/reporting/__init__.py`
- `calamum_vulcan/domain/reporting/builder.py`

Concrete implementation outcomes:

- live detection now derives a repo-owned `path_identity` from source, fallback posture, detection state, and any available snapshot truth
- fastboot normalization now preserves optional `product:`, `model:`, and `device:` tokens when the backend provides them, and distinguishes USB from TCP/IP transport in the normalized record
- reporting now exports `device.live.path_identity` with ownership, delegated label, confidence, summary, and operator guidance
- decision traces, log lines, recovery guidance, and Markdown evidence now include the delegated/fallback live-path story explicitly instead of leaving that truth implicit in fallback posture alone

### Frame 3 — Authority, shell, and CLI surfaces now read from the same fallback truth

**Result:** completed

Touched propagation surfaces:

- `calamum_vulcan/app/view_models.py`
- `calamum_vulcan/app/__main__.py`
- `calamum_vulcan/domain/state/authority.py`
- `calamum_vulcan/validation/security.py`

Concrete implementation outcomes:

- shell device, transport, and evidence panels now surface explicit delegated/fallback path labels, confidence, summaries, and guidance
- CLI control-trace output now emits `live_path ...` and `live_path_guidance ...` lines beside the existing live-detection identity output
- session authority no longer risks labeling direct fastboot review as `native`; delegated and fallback ownership now stay explicit when the live path is not command-ready ADB
- the shared security suite now requires both fallback posture visibility and delegated path identity visibility as part of the exported trust contract

### Frame 4 — Degraded and packaged fallback paths stay explicit instead of widening silently

**Result:** completed

Concrete narrowing outcomes:

- no-device and failed fallback lanes now produce explicit labels such as `Fallback Check Pending`, `Fallback Exhausted`, and `Fallback Probe Failed` instead of collapsing back into generic live-session wording
- serial-only fastboot detections now remain explicitly `serial_only` rather than overclaiming richer device identity than the adapter actually provided
- packaged-context validation exposed that the `ready` demo scenario was still pairing `suspicious-review` packages with the default ready PIT fixture, which falsely blocked the warning-tier lane with a PIT mismatch; the stack therefore added a matching suspicious PIT fixture plus package-aware demo PIT selection so the reviewed package and observed PIT stay aligned when the operator intentionally selects the warning-tier suspicious-review path

Touched repair surfaces for the packaged-context lane:

- `calamum_vulcan/fixtures/heimdall_pit_fixtures.py`
- `calamum_vulcan/app/demo.py`
- `tests/unit/test_shell_view_models.py`

### Frame 5 — Focused, packaged, and deterministic validation closed the stack

**Result:** completed

Touched validation surfaces:

- `tests/unit/test_adb_fastboot_adapter.py`
- `tests/unit/test_live_device_contract.py`
- `tests/unit/test_session_authority_contract.py`
- `tests/unit/test_reporting_contract.py`
- `tests/unit/test_shell_view_models.py`
- `tests/unit/test_cli_control_surface.py`
- `tests/unit/test_security_validation.py`

Concrete validation outcomes:

- added parser coverage for richer fastboot identity tokens
- added live-path identity coverage for fallback-needed, delegated fastboot, fallback fastboot, and direct-fastboot authority lanes
- added reporting, shell, CLI, and security regressions for the new path-identity surface
- proved the packaged suspicious-review lane stays `Gate Ready` after the PIT-fixture repair instead of silently drifting into a false PIT mismatch block

## Validation record for `FS5-04`

| Validation type                         | Outcome              |
| --------------------------------------- | -------------------- |
| modified-file error scan                | passed               |
| focused FS5-04 pytest slice             | passed               |
| targeted suspicious-review repair slice | passed               |
| `.venv-core` full pytest baseline       | passed               |
| standalone security validation          | passed_with_warnings |
| installed-artifact validation           | passed               |
| scripted simulation / reproducibility   | passed               |

Automated validation runs used for stack closeout:

- `functions.get_errors` against the touched live-device, reporting, shell, authority, security, demo, fixture, and test files
   - result: no errors found in any edited file
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_adb_fastboot_adapter.py tests/unit/test_live_device_contract.py tests/unit/test_session_authority_contract.py tests/unit/test_reporting_contract.py tests/unit/test_shell_view_models.py tests/unit/test_cli_control_surface.py tests/unit/test_security_validation.py -q`
   - result: `81 passed, 4 subtests passed in 1.84s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_shell_view_models.py -q`
   - result: `20 passed in 0.41s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit -q`
   - result: `196 passed, 4 subtests passed in 11.18s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/run_security_validation_suite.py`
   - result: `passed_with_warnings`, `0` blockers, `8` warnings
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m build --wheel --outdir dist .`
   - result: refreshed the candidate wheel used for packaged-context FS5-04 validation
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/validate_installed_artifact.py`
   - result: `installed_artifact_contract="passed"`; help, describe-only review, GUI entrypoint, archive-backed review, suspicious-review, evidence export, integration bundle, read-side-close bundle, and distribution-file checks all passed from the installed artifact
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/run_scripted_simulation_suite.py`
   - result: `progress.log` reached all source-root and installed-artifact scenarios plus both sprint-close bundles, and the suite recorded `source and installed contexts matched exactly`

### Proven behavior

- live detection now carries explicit path identity with ownership, delegated label, confidence, summary, and operator guidance instead of leaving fallback meaning implicit in a thinner summary string
- delegated fastboot and fastboot fallback lanes remain visibly delegated or fallback across authority, reporting, shell, and CLI surfaces rather than being flattened into native-ready wording
- fastboot identity can now remain honestly `serial_only` when product truth is thin or rise to richer `product_resolved` / `profiled` confidence when optional tokens provide more evidence
- installed-artifact and scripted simulation proof still hold after the new fallback identity surface was threaded through source-root and packaged contexts

### Stubbed / intentionally deferred behavior

- the sanctioned fastboot detect command plan remains `fastboot devices`; the stack deliberately widened parsing without escalating the command grammar to `devices -l`
- default native transport autonomy still belongs to later Sprint 5 / Sprint 5 work rather than FS5-04
- the deterministic `safe-path-close` bundle and trusted-publication restoration remain later Sprint 5 boundary work

### Carry-forward debt

- decide whether the extracted safe-path lane in `FS5-05` should consume `path_identity` directly or only through the state-owned authority snapshot
- extend later closeout or integration suites with a first-class fallback-identity scenario if the eventual `safe-path-close` proof needs direct delegated/fallback matrix coverage rather than relying only on current targeted tests and scripted parity
- keep source-tree and installed-artifact parity under observation whenever later stacks materially change operator-visible safe-path wording, evidence exports, or closeout-bundle content

## `FS5-05` — Bounded safe-path transport responsibility

### Stack goal

Promote one reviewed flash lane from adapter-helper status into a platform-supervised bounded safe-path execute surface while keeping delegated lower transport, blocked-path behavior, and higher-risk claims explicit.

### Frame 1 — Exact owned lane and refusal boundary pinned

**Result:** completed

Pinned the concrete FS5-05 lane as:

- reviewed flash-plan execution only
- gated by state-owned session authority plus reviewed package/PIT truth
- surfaced first through the CLI execute path rather than the Qt write surface
- still explicitly delegated at the lower transport layer because Heimdall remains the actual flash subprocess boundary

Explicitly refused in this stack:

- default native transport claims
- broad live write-path expansion through the GUI
- any wording that would flatten delegated lower transport into native ownership

### Frame 2 — Platform-owned gating and supervision implemented

**Result:** completed

Touched runtime and adapter surfaces:

- `calamum_vulcan/domain/state/runtime.py`
- `calamum_vulcan/domain/state/__init__.py`
- `calamum_vulcan/adapters/heimdall/runtime.py`
- `calamum_vulcan/app/demo.py`

Concrete implementation outcomes:

- added `ensure_safe_path_runtime_ready(...)` so bounded runtime admission now requires a state-owned safe-path candidate with ready authority posture instead of trusting phase alone
- tightened `run_bounded_heimdall_flash_session(...)` so package assessment and PIT inspection truth can participate in runtime admission before any flash command is generated
- repaired the demo/runtime seam so the bounded execute lane can be assembled deterministically from a pre-transport ready session, a reviewed package, and a reviewed PIT posture instead of only from already-completed scenario snapshots
- made the ready review lane a valid bounded runtime fixture path by adding an explicit adapter fixture mapping for `ready`

### Frame 3 — CLI, evidence, and operator surfaces now expose the lane honestly

**Result:** completed

Touched app/reporting/operator surfaces:

- `calamum_vulcan/app/__main__.py`
- `calamum_vulcan/app/view_models.py`
- `calamum_vulcan/domain/reporting/builder.py`

Concrete implementation outcomes:

- added `--execute-flash-plan` as a first-class CLI lane for bounded safe-path execution
- restricted the lane to `--transport-source heimdall-adapter` so the current delegated lower transport stays explicit instead of pretending to be default-native execution
- added text and JSON execute-result rendering so the CLI can report both ready execution and blocked-path rejection without requiring GUI launch or ad-hoc log inspection
- added explicit safe-path governance wording to shell transport/evidence detail lines and report log lines so the operator can see that the platform supervised the lane while Heimdall remained delegated lower transport

### Frame 4 — Blocked-path and delegated-boundary honesty preserved

**Result:** completed

Concrete honesty outcomes:

- blocked execute attempts now remain visible as `execution_allowed=false` with explicit rejection text and `transport_state="not_invoked"`
- ready execute attempts now preserve `ownership="delegated"` rather than widening into a false native claim
- installed-artifact and source-root evidence now preserve the `[SAFE-PATH] governance=platform_supervised ...` log line so the lower transport boundary remains auditable after export

### Frame 5 — Deterministic, installed, and parity validation closed the stack

**Result:** completed

Touched validation and regression surfaces:

- `tests/unit/test_heimdall_adapter.py`
- `tests/unit/test_cli_control_surface.py`
- `tests/unit/test_shell_view_models.py`
- `tests/unit/test_reporting_contract.py`
- `scripts/validate_installed_artifact.py`
- `scripts/run_scripted_simulation_suite.py`

Concrete validation outcomes:

- added focused runtime coverage for PIT-mismatch rejection before transport
- added CLI coverage for ready execute, blocked execute, and JSON result rendering
- added shell/reporting coverage for the explicit safe-path governance wording/log lines
- extended installed-artifact validation so the packaged wheel now exercises the ready execute lane, the blocked execute lane, and exported execute evidence
- extended scripted simulation so both source-root and installed-artifact contexts now compare `ready-execute` and `blocked-execute` outputs/evidence in addition to the existing review matrix

## Validation record for `FS5-05`

| Validation type                           | Outcome              |
| ----------------------------------------- | -------------------- |
| modified-file error scan                  | passed               |
| focused FS5-05 pytest slice               | passed               |
| execute-lane JSON rendering regression    | passed               |
| `.venv-core` full pytest baseline         | passed               |
| aggressive penetration-style pytest slice | passed               |
| standalone security validation            | passed_with_warnings |
| installed-artifact validation             | passed               |
| scripted simulation / reproducibility     | passed               |

Automated validation runs used for stack closeout:

- `functions.get_errors` against the touched runtime, adapter, CLI, reporting, shell, script, and test files
   - result: no errors found in any edited file
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_heimdall_adapter.py tests/unit/test_cli_control_surface.py tests/unit/test_shell_view_models.py tests/unit/test_reporting_contract.py`
   - result: `64 passed in 1.36s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_cli_control_surface.py -q`
   - result: `22 passed, 4 subtests passed in 0.72s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit -q`
   - result: `200 passed, 4 subtests passed in 12.34s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe -m pytest tests/unit/test_security_validation.py tests/unit/test_package_importer.py tests/unit/test_package_snapshot.py tests/unit/test_pit_contract.py -q`
   - result: `19 passed in 1.13s`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/run_security_validation_suite.py`
   - result: `passed_with_warnings`, `0` blockers, `8` warnings
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/build_release_artifacts.py`
   - result: refreshed `dist/` quietly for the updated FS5-05 candidate
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/validate_installed_artifact.py`
   - result: completed quietly; packaged outputs now include `execute_safe_path_evidence.json` plus the completed execute transcript `cv-20260421-195333-completed-ready-to-execute-control-deck.transport.log`
- `c:/Users/joedi/Documents/edu/UNC/.venv-core/Scripts/python.exe scripts/run_scripted_simulation_suite.py`
   - result: completed quietly; `temp/fs_p04_scripted_simulation/progress.log` now records `ready-execute`, `blocked-execute`, both sprint-close bundles, and `source and installed contexts matched exactly`, while `simulation_summary.json` now records `execute_names=["ready-execute", "blocked-execute"]`

### Proven behavior

- bounded runtime execution now requires a state-owned safe-path candidate with ready authority posture instead of trusting only `phase == ready_to_execute`
- the CLI now exposes a real `--execute-flash-plan` lane that can report both successful bounded execution and blocked-path refusal without leaving the operator to infer state from raw transport logs
- reporting, shell detail lines, and exported log lines now state explicitly that the platform supervised the bounded reviewed flash session while Heimdall remained delegated lower transport
- installed-artifact and scripted-simulation proof now exercise and compare both ready and blocked execute lanes instead of validating only the older review-only surfaces

### Stubbed / intentionally deferred behavior

- the Qt `Execute flash plan` control remains placeholder-only in this stack; FS5-05 promoted the CLI execute lane first so the bounded write-adjacent surface could stay explicit and deterministic
- the lane still requires `--transport-source heimdall-adapter`; FS5-05 does **not** claim default native transport or a general live write path
- the deterministic `safe-path-close` bundle remains later Sprint 5 work rather than an FS5-05 claim

### Carry-forward debt

- decide whether the Qt execute control should graduate from placeholder status in `FS5-06` or later once runtime-hygiene follow-through is complete
- thread the new safe-path governance wording and execute-lane proof into the later deterministic `safe-path-close` bundle
- keep installed/source execute-lane parity under observation whenever later stacks change transcript policy, operator-visible safe-path wording, or bundled closeout evidence

## Preserved operator-flow design conversation (2026-04-21)

This note captures a still-ongoing local design decision so the rationale survives beyond chat history and remains available as a hard-copy memory substrate during later Sprint 5 stacks.

Settled items preserved here:

- the current control-deck problem is now preserved as three separate but related issues with three separate fixes:
   1. functional collision -> narrow the current inspect action so it stops silently duplicating detect/info and becomes a true PIT-read action
   2. semantic collision -> rename the control from `Inspect device` to `Read PIT`
   3. workflow clarity -> reorder the deck to emphasize the intended flashing sequence
- the preferred control-deck order is now explicitly preserved as `Detect device -> Read PIT -> Load package -> Execute flash plan -> Export evidence`
- within that settled order, `Read PIT` is a required workflow step: `Load package` and `Execute flash plan` should not advance as next-step-eligible actions until PIT truth has been captured successfully enough to count as a completed PIT step
- greyed-out buttons remain the correct unavailable cue
- one green button at a time is now the settled visual preference; green means the single next required or strongest recommended action, not generic availability
- the deck should move away from explanatory helper prose where equivalent workflow meaning can be conveyed through stronger non-verbal state cues

Current collision preserved here:

- `Inspect device` is doing more semantic work than its operator-facing label earns
- `Detect device` already performs most quick live detect/info hydration
- the current inspect lane still reruns detect/info before it reaches the PIT read, so relabeling alone would leave the operator-facing action misleading

Current preferred direction preserved here:

- reorder the control deck as `Detect device -> Read PIT -> Load package -> Execute flash plan -> Export evidence`
- make `Detect device` the authoritative live-state hydrator
- replace the `Inspect device` label with `Read PIT`
- narrow the current inspect lane into a real `Read PIT` action that consumes the current live snapshot instead of silently duplicating detect/info by default
- keep `Read PIT` disabled until detect has run and the current path is PIT-capable
- keep `Load package` unavailable until PIT truth is good enough to count as a completed step, then advance the next-step cue to `Load package`
- preserve package alignment as explicitly unreviewed / pending until package truth exists
- keep inspection/posture/evidence preparation implicit in updated GUI evidence fields and exported reports rather than exposing report-preparation as its own operator verb
- make missing PIT truth an explicit execution prerequisite for the bounded execute lane rather than treating it as absent optional context
- make `Export evidence` available as soon as `Detect device` has executed and the session carries exportable evidence, while still keeping it out of the green next-step role until the flash-plan workflow has been executed and resolved
- treat resume as a specialized execution-handoff concept rather than as part of the default ordered deck flow
- if a real recovery continuation action is later surfaced to the operator, the accepted label is `Continue after recovery`
- `Continue after recovery` should be contextual only: hidden during the normal deck flow and visible only when a real `resume_needed` handoff is active and resumable

Open items preserved here:

- how to represent workflow progress visually so the user can infer `done`, `available`, and `do this next` without leaning on helper paragraphs
- how much of the current control-deck small writing can be removed once the button/state model becomes richer
- how the deck should guide the operator when detect succeeds but the current live path is not yet PIT-capable, especially if the strongest next-step cue needs to move from the deck into one of the live-companion reboot controls
- how to land the mandatory-PIT rule in code, because the current preflight/authority/runtime stack still treats missing PIT as non-blocking unless bad PIT truth is already present
- what exact PIT result counts as “step complete” for advancing to `Load package`: fully captured only, or a narrower subset of partially resolved PIT truth
- how a future contextual `Continue after recovery` action should validate resumability before it becomes clickable, because the current code still has no operator-driven continuation path yet
- the latest real GUI repro proves the unified detect flow now reaches Heimdall after the reboot-to-download handoff, but the operator surface can still end at `Heimdall device detection did not produce a trustworthy identity result.`; that makes download-mode detect normalization hardening and clearer failure taxonomy explicit `FS5-06` carry-forward work rather than a solved detail
- full ladder alignment still requires explicit honesty that the current repo remains a Sprint 5 delegated-lower-transport boundary rather than a Sprint 5 default-native or Heimdall-optional boundary

Current recommendation preserved here:

- reserve green for the single next required or strongest recommended step
- do not let green also mean generic availability, because that collapses `valid` and `next` into the same cue
- completed-but-still-valid actions should remain enabled without staying green; use a softer completion cue instead
- make `Read PIT` mandatory inside the settled control-deck workflow chain, with `Load package` and `Execute flash plan` both gated behind a completed PIT step
- keep `Export evidence` available early once evidence exists, but do not make it green until execute has run and resolved
- keep any future `Continue after recovery` action out of the primary ordered workflow and surface it only as a contextual recovery control when a real resumable execution path exists
- the likely code-level follow-through for `FS5-06` is a richer control-action state model than the current `enabled + emphasis` pair so the UI can express at least `unavailable`, `available`, `next`, and `completed`
- capture the real Heimdall detect stdout/stderr shapes that currently fail normalization and widen the detect parser / operator guidance so standard Samsung download-mode detection becomes trustworthy on reviewed hardware rather than merely reaching the delegated backend
- keep the Sprint 5 wording explicit in code/docs/evidence while carrying true native-default transport extraction and Heimdall demotion criteria into the future `0.5.0` lane instead of quietly redefining the current sprint

Planned owning stack: `FS5-06` for operator-surface honesty and runtime-behavior cleanup, with any resulting execute-lane prerequisite tightening carrying forward into later Sprint 5 closeout work as needed.

### `FS5-06` — Runtime hygiene, transcript policy, and operator-surface honesty

**Stack goal:** preserve trust as safe-path responsibility expands.

**Planned closeout signal:** logs, transcripts, detached-host behavior, and exported evidence stay coherent, readable, and honest about native, delegated, blocked, and fallback status.

### `FS5-07` — Selective fallback discipline, trusted-publication rehearsal, broad security gate, empirical closure, and sprint-close evidence

**Stack goal:** consolidate the real Sprint 5 candidate before freeze.

**Planned closeout signal:** the `safe-path-close` bundle, installed-artifact outputs, security validation, empirical review, and trusted-publication rehearsal all agree on the same candidate story.

### `FS5-08` — Closeout checklist, prepackage freeze, trusted-publication validation, packaging boundary, and publication move

**Stack goal:** move from local planning shell to real public release boundary.

**Planned closeout signal:** the exact `0.5.0` candidate is sealed, release notes and package metadata agree, and the public publication route proves restored trusted publication instead of depending on the interim token-backed/manual workaround.

## Expected record shape for each completed stack

When a Sprint 5 stack is actually closed, the evidence update should record:

- closeout date
- code/doc surfaces touched
- validation commands or suites run
- bundle, report, or workflow outputs created
- carry-forward debt that remains for later Sprint 5 stacks or `0.5.0`

Except for stacks explicitly marked completed in the register above, the remaining entries should be treated as the authoritative planned shape rather than as proof that the work is already complete.
