# Changelog

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