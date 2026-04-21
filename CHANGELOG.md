# Changelog

## 0.3.0 - 2026-04-20

Third Calamum Vulcan candidate boundary, moving supported Samsung read-side detection, bounded info capture, PIT-aware inspection review, and closeout evidence into repo-owned platform surfaces while keeping write-side flashing out of the public support boundary.

### Added

- repo-owned live-device detection sessions with bounded ADB info capture for the reviewed Samsung subset
- PIT acquisition / inspection evidence surfaces and inspect-only CLI/GUI export paths
- the deterministic `read-side-close` integration bundle plus installed-artifact proof that the packaged wheel preserves it
- adversarial transcript-path and archive-abuse regression coverage for release-boundary hardening
- a reusable `0.3.0` closeout and prepackage checklist for package / publish decisions

### Changed

- the GUI now uses a denser independent-scroll layout and promotes successful bounded ADB detection to `ADB Device Detected`
- reporting and evidence exports now carry inspect-only posture, fallback posture, PIT alignment truth, and read-side-close bundle metadata explicitly
- installed-artifact validation now asserts the packaged `read-side-close` bundle and the bounded inspect-only non-transport posture
- release metadata is now frozen at the `0.3.0` candidate boundary instead of the previous `0.2.0` public baseline

### Validated

- targeted adversarial regression passed for reporting transcript sanitization and unsafe archive members
- broader regression passed for CLI control surfaces, integrated closeout bundles, and Qt shell contracts
- the standalone security validation gate passed with warning-tier checksum-placeholder debt only

### Release-boundary status

- `0.2.0` remains the latest public PyPI/GitHub release until the sealed `v0.3.0` boundary moves
- the `0.3.0` candidate is intended to publish only when the exact version strings, artifacts, hashes, tag, release notes, and install proof all point to the same sealed boundary

### Known limitations

- live firmware flashing remains outside the intended `0.3.0` public support boundary
- native read-side ownership remains limited to the reviewed Samsung subset; fallback remains explicit where ownership stops
- Windows remains the only empirically reviewed packaged host for the `0.3.0` candidate
- Qt font packaging still emits a non-blocking warning in some environments
- warning-tier checksum placeholder debt remains in legacy fixture manifests

## 0.2.0 - 2026-04-20

Second packaged Calamum Vulcan release boundary, extending the public shell with reviewed package intake, reviewed flash-plan/runtime evidence, and cleaner packaged GUI behavior.

### Added

- archive-backed package intake with manifest, path-shape, and checksum verification
- analyzed package snapshots plus drift-aware preflight enforcement for archive-backed reviews
- Samsung device-registry lookups and reviewed flash-plan evidence surfaces
- warning-tier Android image heuristics and transcript-aware runtime evidence retention
- the `orchestration-close` integration bundle for the `0.2.0` runtime/transcript lane

### Changed

- the GUI now boots into an explicit standby/unhydrated review state and hydrates the main device surfaces from unified live detection
- interactive `calamum-vulcan-gui` launches now emit compact status output, detach cleanly on Windows, and suppress duplicate exit confirmations
- reporting/evidence exports now advance to the `0.2.0` schema boundary
- installed-artifact and empirical-review validation scripts now resolve current package-version metadata instead of pinning `0.1.0` artifact names

### Validated

- `.venv-core` package validation reran successfully for build, Twine metadata, installed-artifact, scripted-simulation, and empirical-review gates
- the packaged launcher behavior was revalidated after the detached-launch/no-duplicate-echo fix
- live PyPI publication completed for `calamum-vulcan==0.2.0`
- live GitHub release published at `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.2.0`

### Known limitations

- live firmware flashing remains outside the public `0.2.0` support boundary
- Windows remains the only empirically reviewed packaged host for `0.2.0`
- Qt font packaging still emits a non-blocking warning in some environments
- warning-tier checksum placeholder debt remains in legacy fixture manifests

## 0.1.0 - 2026-04-18

Initial public packaging target for the Calamum Vulcan product shell.

### Added

- GUI-first product shell with deterministic scenario fixtures
- package-aware preflight gating and reporting surfaces
- Heimdall adapter seam with normalized transport evidence
- sprint-close integration bundle in JSON and Markdown formats

### Packaging preparation

- nested release-root publication lane activated
- public repo seed attached at `https://github.com/joediggidyyy/calamum_vulcan`
- packaging metadata, manifest rules, and artifact-build runner added for `FS-P02`
- packaged branding assets are now carried in both the wheel and the source distribution
- empirical release review runner added for `FS-P05`
- TestPyPI rehearsal and final publication-gate runner added for `FS-P06`
- TestPyPI upload, registry-delivered install validation, uninstall/reinstall validation, and final `go` publication decision completed for `FS-P06`
- live PyPI publication completed for `calamum-vulcan==0.1.0`
- live GitHub release published at `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.1.0`

### Known limitations

- the published flashing workflow remains simulation-validated rather than live-subprocess-backed
- live companion device controls remain bounded lab-review surfaces rather than broad public flashing claims
- Windows is the only empirically reviewed packaged host for `0.1.0`
- Qt font packaging remains unresolved deployment debt
- warning-tier security debt remains in package checksum placeholders, real archive import, and Android-image heuristics