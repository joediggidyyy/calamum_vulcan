# Calamum Vulcan — `0.5.0` Closeout and Prepackage Checklist

## Purpose

This checklist is the working Sprint 5 / `0.5.0` pre-package shell.

For the active Sprint 5 lane, `closeout checklist` and `pre-package checklist` refer to the same working artifact, but the checklist itself completes at **package-ready**.

It should stay local and editable while the sprint is active, then harden into the exact package-ready checklist used to freeze, validate, and document the candidate before any separate repo-visible seal step.

## Sprint 5 assumptions

- `0.5.0` is the Sprint 5 / Stage III boundary defined by the roadmap as **efficient integrated transport extraction**.
- `0.3.0` remains the currently published public boundary until `0.5.0` is actually sealed and released.
- source-tree green is necessary but insufficient; installed-artifact proof, security validation, empirical review, and package-boundary validation all remain required.
- `0.5.0` now closes as a **package-only sprint boundary**; renewed TestPyPI/PyPI publication is intentionally deferred until the immediate post-`0.6.0` `1.0.0` promotion gate.

## Primary authority surfaces

Use these surfaces together when the checklist becomes active:

- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Testing_and_Readiness_Plan.md`
- `docs/Samsung_Android_Flashing_Platform_Research_Report_and_Build_Plan.md`
- `docs/Samsung_Android_Flashing_Platform_0.6.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_1.0.0_Promotion_Gate.md`
- `pyproject.toml`
- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/workflows/python-publish.yml`

## Evidence anchors that should exist before packaging begins

The exact paths may shift as implementation settles, but the pre-package boundary should expect evidence at or near the following anchors:

- deterministic `safe-path-close` bundle outputs for the candidate boundary
- installed-artifact validation outputs for help, evidence export, and closeout behavior
- shared security-validation outputs for the candidate
- aggregate readiness outputs under `temp/fs5_readiness/`
- refreshed Sprint 5 implementation audit outputs under `temp/v050_timeline_audit/`
- refreshed Sprint 6 handoff/alignment outputs under `temp/v060_alignment_audit/`
- pre-package notes tying the package-only boundary and explicit `1.0.0` publication deferral to the exact candidate being frozen
- final version, artifact-hash, and package-ready records for the candidate

## Current pre-package state

| Surface                       | Current state                                                                                                                  | Evidence anchor                                                                |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| public release baseline       | `0.3.0` is the current live release boundary                                                                                   | live GitHub release and PyPI project state                                     |
| Sprint 5 planning shell       | aligned working shell with refreshed local readiness and audit evidence                                                        | `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`            |
| Sprint 5 evidence shell       | working ledger paired with refreshed readiness and audit artifacts                                                             | `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md`           |
| current readiness archive     | refreshed and passing across `7` active lanes                                                                                  | `temp/fs5_readiness/readiness_summary.json`                                    |
| Sprint 5 implementation audit | refreshed; `15` implemented / `0` partial / `0` open                                                                           | `temp/v050_timeline_audit/v050_timeline_audit.md`                              |
| Sprint 6 handoff audit        | refreshed; remaining red items are execution gaps, not authority gaps                                                          | `temp/v060_alignment_audit/v060_alignment_audit.md`                            |
| local repo package boundary   | `pyproject.toml`, `README.md`, `CHANGELOG.md`, and `CONTRIBUTING.md` now align to a real local `0.5.0` package-ready candidate | local repo verification plus `temp/v050_timeline_audit/v050_timeline_audit.md` |
| publication workflow baseline | earlier registry-publication tooling still exists on `main`, but it is no longer active Sprint 5 pre-package work              | `.github/workflows/python-publish.yml`                                         |
| PyPI publication posture      | intentionally deferred until the immediate post-`0.6.0` `1.0.0` promotion gate                                                 | roadmap plus updated Sprint 5 execution shell                                  |

## Scheduled multi-strategy testing gate

Before the candidate can be marked package-ready, the Sprint 5 testing schedule should have current evidence for all of the following:

- `pytest` baseline coverage
- sandbox installed-artifact validation
- scripted simulation
- empirical packaged review
- aggressive penetration-style validation
- package-boundary freeze validation at the near-end boundary

The standard orchestration surface for that aggregate proof is:

- `scripts/run_v050_readiness_stack.py`

Current refreshed aggregate proof:

- `temp/fs5_readiness/readiness_summary.json` (`overall_status="passed"`)

## Pre-package checklist

### 1) Candidate-boundary identity and Sprint 5 scope lock

- [x] Confirm the exact `0.5.0` sprint claims still match the roadmap wording: efficient integrated transport extraction, not default native transport.
- [x] Confirm the final docs/evidence still describe Heimdall as delegated lower transport for the standard Sprint 5 write lane and Samsung download-mode detect lane, rather than drifting into Sprint 5 `optional fallback only` wording early.
- [x] Confirm the final support posture clearly distinguishes native, delegated, fallback, and blocked paths.
- [x] Confirm the public docs and pre-package evidence do not overclaim broader flashing autonomy than Sprint 5 actually proves.
- [x] Confirm the `0.5.0` version string, release notes, changelog language, and support posture all point to the same candidate boundary.

### 2) Session and alignment closeout gate

- [x] Confirm authoritative session and launch-state truth exists across state, reporting, and operator-facing surfaces.
- [x] Confirm device/package/PIT alignment now produces stronger blocking or narrowing behavior for claimed safe-path lanes.
- [x] Confirm blocked-path guidance is as clear as happy-path guidance for mismatched, incomplete, or unsupported inputs.
- [x] Confirm fallback identity remains visible wherever the platform still relies on delegated or external transport paths.

### 3) Safe-path extraction and runtime-hygiene gate

- [x] Confirm the bounded safe-path lane claimed by Sprint 5 is explicitly defined and honestly labeled.
- [x] Confirm higher-risk or unsupported actions remain visibly outside the extracted boundary.
- [x] Confirm reviewed-host Samsung download-mode detection is trustworthy: either a normalized Samsung identity is captured or the operator gets an explicit distinction between `no device`, Heimdall runtime/tool failure, and unparsed detect output.
- [x] Confirm transcript integrity, detached-host runtime behavior, and evidence export stay coherent after the extraction work.
- [x] Confirm operator-visible status and recovery guidance remain readable and accurate during ready, blocked, degraded, and fallback states.

### 4) Deterministic proof and installed-artifact gate

- [x] Run the Sprint 5 readiness orchestrator or produce equivalent per-lane evidence under `temp/fs5_readiness/`.
- [x] Confirm the `pytest` baseline remains green for the candidate boundary.
- [x] Generate the deterministic `safe-path-close` bundle from the candidate boundary.
- [x] Confirm the closeout bundle agrees with the claimed Sprint 5 support posture.
- [x] Run installed-artifact validation for help output, evidence export, closeout behavior, uninstall, and reinstall as appropriate for the candidate.
- [x] Confirm the installed-artifact surface does not drift from the source-tree support posture.
- [x] Run the scripted simulation suite and confirm the source-tree and installed-artifact stories still match.
- [x] Confirm the sandbox installed-artifact lane still preserves safe-path, fallback, and evidence-export truth after packaging.

### 5) Security and adversarial validation gate

- [x] Run the aggressive penetration-style `pytest` slice for archive safety, checksum drift, malformed PIT, and related hostile-input boundaries.
- [x] Run the shared security-validation suite against the candidate boundary.
- [x] Confirm parser hardening, transcript integrity, and execution-path integrity checks produce no blocking findings.
- [x] Review any warning-tier findings and decide whether they are acceptable Sprint 5 carry-forward debt or real release blockers.
- [x] Record the final security-validation result alongside the package-ready evidence.

### 6) Package-only boundary gate

- [x] Freeze `pyproject.toml`, `README.md`, `CHANGELOG.md`, and `CONTRIBUTING.md` so the public package boundary matches the Sprint 5 reality.
- [x] Confirm the final package metadata, long description, and support posture render correctly for publication.
- [x] Build the final candidate artifacts and record their hashes.
- [x] Run the candidate install-smoke and entry-point checks from the built artifacts.

### 7) Deferred-publication discipline gate

- [x] Confirm the near-end package-boundary rehearsal lane has current evidence before the final sprint-boundary move.
- [x] Confirm no Sprint 5 closeout item claims renewed TestPyPI/PyPI publication or restored trusted-publication status as a success condition.
- [x] Preserve any registry-publication workflow notes only as dormant inputs for the later `1.0.0` promotion gate.
- [x] Record the explicit defer-to-`1.0.0` publication posture in the closeout evidence and release/admin notes.
- [x] If any GitHub-release or repository-visible packaging surface is used for `0.5.0`, confirm it is framed as a pre-`1.0.0` sprint package boundary rather than the final polished public promotion.

### 8) Package-ready capture

- [x] Record the exact `0.5.0` candidate version, artifact hashes, and validation references in the execution evidence surface.
- [x] Confirm the package metadata, readiness sweep, and this checklist all point to the same package-ready candidate.
- [x] Mark the active Sprint 5 execution evidence surface as package-ready for the exact candidate while preserving honest Sprint 6 / `1.0.0` carry-forward notes.
- [x] Carry any remaining post-`0.5.0` debt into the `0.5.0`, `0.6.0`, and `1.0.0` authority surfaces once the candidate is marked package-ready.

## Boundary execution after package-ready

The following actions may follow a green pre-package checklist, but they are **not** required for the checklist itself to be complete:

- create or confirm the sealed release commit for the final `0.5.0` candidate
- create the annotated tag `v0.5.0`
- push the release commit and tag if a repo-visible Sprint 5 package-boundary seal is desired
- keep any GitHub release-object step intentionally out of Sprint 5 unless it is framed only as a pre-`1.0.0` sprint package boundary
- Do **not** publish `0.5.0` to PyPI as part of Sprint 5

Current pre-package notes:

- latest stable GitHub release remains `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.3.0`
- latest stable PyPI release remains `https://pypi.org/project/calamum-vulcan/0.3.0/`
- current Sprint 5 readiness archive is green across `7` active lanes under `temp/fs5_readiness/readiness_summary.json`
- current Sprint 5 implementation audit reports `15` implemented, `0` partial, `0` open under `temp/v050_timeline_audit/v050_timeline_audit.md`
- current Sprint 6 handoff audit reports `7` implemented, `3` partial, `2` open under `temp/v060_alignment_audit/v060_alignment_audit.md`
- current security validation result is `passed_with_warnings` with `0` blocking findings; the remaining `8` warnings are fixture checksum placeholders and are accepted as pre-package carry-forward debt for now
- final package metadata rendering passes `python -m twine check dist/*`
- current `0.5.0` artifact hashes are:
	- `calamum_vulcan-0.5.0-py3-none-any.whl` — `SHA256 D0AFCC168E0507AB7ACA93D3F2D67C781525D2B2FC328E78346732B1D95E61A3`
	- `calamum_vulcan-0.5.0.tar.gz` — `SHA256 5F6C71B25D3A4FE2FAB009F22114483F61011C33924F1188F8C1D2B4B8C61A43`
- the current local `0.5.0` candidate is package-ready; any later repo-visible Sprint 5 seal remains a separate optional step
- no Sprint 5 PyPI publication should occur; registry publication remains deferred to the immediate post-`0.6.0` `1.0.0` promotion gate

## Package-ready decision rule

The `0.5.0` candidate should be treated as package-ready only when all of the following are simultaneously true:

- Sprint 5 runtime claims are supported by deterministic package-ready evidence.
- installed-artifact and security-validation proof agree with the same candidate boundary.
- public documentation and package metadata honestly match the real support posture.
- the closeout evidence explicitly records that renewed TestPyPI/PyPI publication is deferred until the immediate post-`0.6.0` `1.0.0` promotion gate.

If the package-ready candidate is still ambiguous, the release should be treated as **hold**. A later repo-visible seal step should wait until this checklist is already green. The absence of a new PyPI publication is **not** a Sprint 5 failure; it is the intended roadmap posture.
