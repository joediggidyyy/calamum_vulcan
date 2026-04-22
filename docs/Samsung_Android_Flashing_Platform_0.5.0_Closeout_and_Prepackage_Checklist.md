# Calamum Vulcan — `0.5.0` Closeout and Prepackage Checklist

## Purpose

This checklist is the release-close shell for Sprint 5 / `0.5.0`.

It should stay local and editable while the sprint is active, then harden into the exact boundary checklist used to freeze, package, tag, and publish the final `0.5.0` candidate.

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
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.6.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_1.0.0_Promotion_Gate.md`
- `pyproject.toml`
- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `.github/workflows/python-publish.yml`

## Evidence anchors that should exist before packaging begins

The exact paths may shift as implementation settles, but the release-close boundary should expect evidence at or near the following anchors:

- deterministic `safe-path-close` bundle outputs for the candidate boundary
- installed-artifact validation outputs for help, evidence export, and closeout behavior
- shared security-validation outputs for the candidate
- aggregate readiness outputs under `temp/fs5_readiness/`
- closeout notes tying the package-only boundary and explicit `1.0.0` publication deferral to the exact candidate being sealed
- final version, tag, and artifact-hash records for the candidate

## Current closeout state

| Surface                         | Current state                                                    | Evidence anchor                                                              |
| ------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| public release baseline         | `0.3.0` is the current live release boundary                     | live GitHub release and PyPI project state                                   |
| Sprint 5 planning shell         | generated locally                                                | `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`          |
| Sprint 5 evidence shell         | generated locally                                                | `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md`         |
| publication workflow baseline   | earlier registry-publication tooling still exists on `main`, but it is no longer active Sprint 5 closeout work | `.github/workflows/python-publish.yml` |
| PyPI publication posture        | intentionally deferred until the immediate post-`0.6.0` `1.0.0` promotion gate | roadmap plus updated Sprint 5 execution shell |

## Scheduled multi-strategy testing gate

Before the candidate boundary can move, the Sprint 5 testing schedule should have current evidence for all of the following:

- `pytest` baseline coverage
- sandbox installed-artifact validation
- scripted simulation
- empirical packaged review
- aggressive penetration-style validation
- package-boundary freeze validation at the near-end boundary

The standard orchestration surface for that aggregate proof is:

- `scripts/run_v040_readiness_stack.py`

## Closeout checklist

### 1) Candidate-boundary identity and Sprint 5 scope lock

- [x] Confirm the exact `0.5.0` sprint claims still match the roadmap wording: efficient integrated transport extraction, not default native transport.
- [x] Confirm the final docs/evidence still describe Heimdall as delegated lower transport for the standard Sprint 5 write lane and Samsung download-mode detect lane, rather than drifting into Sprint 5 `optional fallback only` wording early.
- [x] Confirm the final support posture clearly distinguishes native, delegated, fallback, and blocked paths.
- [x] Confirm the public docs and closeout evidence do not overclaim broader flashing autonomy than Sprint 5 actually proves.
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
- [x] Record the final security-validation result alongside the closeout evidence.

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

### 8) Seal boundary gate

Maintainer authorization for the sealed-boundary move has now been exercised, and the Sprint 5 candidate is closed against the checked items below.

- [x] Create or confirm the sealed release commit for the final `0.5.0` candidate.
- [x] Create the annotated tag `v0.5.0` at the sealed release boundary.
- [x] Push the release commit and tag to the public repository as the repository-visible Sprint 5 package-boundary seal.
- [x] Keep the GitHub release-object step intentionally unexercised for Sprint 5; the pushed `v0.5.0` tag is the repo-visible seal while the latest stable GitHub/PyPI release remains `0.3.0`.
- [x] Do **not** publish `0.5.0` to PyPI as part of Sprint 5 closeout.
- [x] Install the final built artifact from the sealed package boundary into a clean environment and rerun the critical installed-artifact checks.
- [x] Record the final artifact hashes, boundary URLs (if any), and validation references in the closeout evidence.

### 9) Final closeout and carry-forward capture

- [x] Mark the `0.5.0` execution evidence surface as closed with the final stack results.
- [x] Confirm the final artifact hashes, version strings, release notes, workflow proof, and public URLs all point to the same `0.5.0` boundary.
- [x] Carry any remaining post-`0.5.0` debt into the `0.5.0`, `0.6.0`, and `1.0.0` authority surfaces only after the `0.5.0` boundary is truly sealed.

Final Sprint 5 seal notes:

- artifact hashes are recorded in `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md`
- repository-visible tag URL: `https://github.com/joediggidyyy/calamum_vulcan/tree/v0.5.0`
- latest stable GitHub release remains `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.3.0`
- latest stable PyPI release remains `https://pypi.org/project/calamum-vulcan/0.3.0/`
- workflow proof for Sprint 5 remains the explicit dormant-publication posture carried in `.github/workflows/python-publish.yml`; no new Sprint 5 publication run was invoked
- validation references: `temp/fs5_readiness/readiness_summary.json`, `temp/v040_timeline_audit/v040_timeline_audit.json`, `temp/fs5_readiness/sandbox_installed_artifact/stdout.txt`, `temp/fs5_readiness/scripted_simulation/stdout.txt`, and `temp/fs5_readiness/empirical_review/stdout.txt`

## Package-boundary decision rule

The `0.5.0` candidate should move only when all of the following are simultaneously true:

- Sprint 5 runtime claims are supported by deterministic closeout evidence.
- installed-artifact and security-validation proof agree with the same candidate boundary.
- public documentation and package metadata honestly match the real support posture.
- the closeout evidence explicitly records that renewed TestPyPI/PyPI publication is deferred until the immediate post-`0.6.0` `1.0.0` promotion gate.

If the package-only boundary is still ambiguous, the release should be treated as **hold**. The absence of a new PyPI publication is **not** a Sprint 5 failure; it is the intended roadmap posture.
