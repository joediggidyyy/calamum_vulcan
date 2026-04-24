# Changelog

**Document ID**: `CALAMUM_VULCAN_CHANGELOG`  
**Status**: Public change history  
**Owner**: ORACL-Prime  
**Project**: Calamum Vulcan  
**Last updated**: 2026-04-23

---

<p align="center">
  <img src="calamum_vulcan/assets/branding/calamum_vulcan_logo.png" alt="Calamum Vulcan Logo" width="200">
</p>

## 0.6.0 - 2026-04-23

Local package-only Sprint 6 autonomy boundary, sealing the first integrated-runtime Samsung flashing candidate while keeping public promotion deferred to the immediate post-`0.6.0` `1.0.0` gate.

### Added

- the deterministic `autonomy-close` integration bundle for Sprint 6 fallback-quarantine and autonomy-close proof
- the dedicated Sprint 6 readiness runner and supporting readiness docs for the package-only `0.6.0` freeze
- expanded CLI and regression coverage for the new Sprint 6 bundle surface and integrated-runtime proof lanes
- a dedicated Sprint 6 live empirical preflight runner at `scripts/run_fs6_live_empirical_review.py` that writes manual-review readiness summaries under `temp/fs6_live_empirical/`
- a Calamum-owned packaged Heimdall CLI payload under `calamum_vulcan/assets/bin/windows/heimdall/` for the Windows supported-path runtime lane

### Changed

- repository package metadata now targets the local `0.6.0` package-only Sprint 6 autonomy boundary while the latest public stable release remains `0.3.0`
- installed-artifact, scripted-simulation, empirical-review, and alignment-audit proof surfaces now treat `integrated-runtime` as the supported Sprint 6 lane and keep historical Heimdall paths explicitly quarantined
- Sprint 6 authority surfaces now separate the completed `FS6-04` quarantine cleanup from the remaining freeze/readiness and promotion-handoff work
- Windows Heimdall runtime resolution now prefers the packaged repo-owned asset before PATH/common install locations and emits explicit missing-DLL guidance when the bundled runtime cannot start

### Validated

- the `autonomy-close` bundle, CLI integration-suite surface, scripted simulation contract, and Sprint 6 audit metadata guards passed focused regression validation
- the Sprint 6 readiness archive is owned by `scripts/run_v060_readiness_stack.py`
- the Sprint 6 alignment audit remains available through `scripts/run_v060_alignment_audit.py`

### Release-boundary status

- current local package boundary: `0.6.0` package-ready autonomy candidate with validated local wheel and sdist targets
- current latest sealed repository-visible sprint tag boundary: `v0.4.0`
- latest stable GitHub/PyPI release: `0.3.0`
- renewed TestPyPI/PyPI publication remains deferred to the immediate post-`0.6.0` `1.0.0` promotion gate

### Known limitations

- Windows remains the only empirically reviewed packaged host for the local `0.6.0` boundary
- Linux packaged validation remains scripted / installed-artifact only pending broader empirical review
- Qt font packaging still emits a non-blocking warning in some environments
- the current official upstream Heimdall Windows bundle is 32-bit and can still require the Microsoft Visual C++ 2012 x86 runtime on a fresh workstation before the packaged supported-path payload can execute
- warning-tier checksum placeholder debt remains in legacy fixture manifests

## 0.5.0 - 2026-04-23

Local package-only Sprint 5 boundary for efficient integrated transport extraction, aligning the repository package metadata and package-ready evidence around the extracted Samsung transport lane while continuing to defer public promotion.

### Added

- native USB Samsung download-mode detection and remediation helpers for the supported Windows/Linux packaging lane
- packaged `libusb`, WinUSB, and `udev` remediation assets for self-resolving USB access on reviewed hosts
- regression coverage for Sprint 5 audit metadata, native USB detection, and updated live-device/session surfaces

### Changed

- repository package metadata now targets the local `0.5.0` package-only Sprint 5 boundary while the latest public stable release remains `0.3.0`
- Sprint 5 closeout surfaces now distinguish **package-ready** completion from any later repo-visible seal step
- installed-artifact validation now derives expected branding assets dynamically from the packaged source set instead of relying on a stale hardcoded subset

### Validated

- the refreshed Sprint 5 readiness archive remains the working multi-lane evidence anchor under `temp/fs5_readiness/`
- the Sprint 5 implementation audit remains available through `scripts/run_v050_timeline_audit.py`
- the Sprint 6 handoff audit remains available through `scripts/run_v060_alignment_audit.py`

### Release-boundary status

- current local package boundary: `0.5.0` package-ready candidate with validated local wheel and sdist
- current latest sealed repository-visible sprint tag boundary: `v0.4.0`
- latest stable GitHub/PyPI release: `0.3.0`
- renewed TestPyPI/PyPI publication remains deferred to the immediate post-`0.6.0` `1.0.0` promotion gate

### Known limitations

- the bounded safe-path lane still relies on delegated Heimdall lower transport rather than a fully Calamum-owned integrated Samsung runtime
- Windows remains the only empirically reviewed packaged host for the local `0.5.0` boundary
- Qt font packaging still emits a non-blocking warning in some environments
- warning-tier checksum placeholder debt remains in legacy fixture manifests

## 0.4.0 - 2026-04-22

Local package-only Sprint 4 boundary, moving session authority, bounded safe-path governance, truthful operator workflow progression, and closeout proof into repo-owned surfaces while intentionally deferring public publication.

### Added

- authoritative session-authority evidence across reporting, shell, and control traces
- the deterministic `safe-path-close` integration bundle for the Sprint 4 closeout lane
- real GUI `Read PIT`, package-load, bounded execute, and contextual recovery-continuation flows
- broader Heimdall detect normalization for Samsung download-mode transcripts plus archived diagnostics for normalization misses

### Changed

- the primary control deck now follows `Detect device -> Read PIT -> Load package -> Execute flash plan -> Export evidence`
- package/PIT/device truth now narrows or blocks the safe-path lane explicitly instead of remaining descriptive only
- installed-artifact, scripted-simulation, and empirical-review validation now exercise the Sprint 4 safe-path bundle and bounded execute lane
- repository metadata now freezes the local package boundary at `0.4.0` while leaving the public boundary at `0.3.0`

### Validated

- the Sprint 4 readiness stack passed in the validated `.venv-core` environment across pytest, adversarial, build, sandbox, scripted, and empirical lanes
- installed-artifact validation preserved the bounded execute lane, safe-path-close bundle, and delegated safe-path evidence contract
- scripted simulation preserved source-vs-installed parity for review flows, execute flows, and closeout bundles
- empirical review preserved readable blocked/failure evidence and packaged GUI screenshots for the reviewed Windows host

### Release-boundary status

- local package boundary frozen at `0.4.0`
- package artifacts are built and validated locally
- repository-visible sprint tag boundary sealed at `v0.4.0`
- no new GitHub release object or PyPI publication was created for Sprint 4; the latest stable GitHub/PyPI release intentionally remains at `0.3.0`
- renewed TestPyPI/PyPI publication is deferred to the immediate post-`0.6.0` `1.0.0` promotion gate

### Known limitations

- the bounded safe-path lane still relies on delegated Heimdall lower transport rather than a fully Calamum-owned integrated Samsung runtime
- Windows remains the only empirically reviewed packaged host for the local `0.4.0` boundary
- Qt font packaging still emits a non-blocking warning in some environments
- warning-tier checksum placeholder debt remains in legacy fixture manifests

## 0.3.0 - 2026-04-21

Third public Calamum Vulcan release boundary, moving supported Samsung read-side detection, bounded info capture, PIT-aware inspection review, and closeout evidence into repo-owned platform surfaces while keeping write-side flashing out of the public support boundary.

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
- live GitHub release published at `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.3.0`
- live PyPI publication completed for `calamum-vulcan==0.3.0`

### Release-boundary status

- final public boundary sealed at tag `v0.3.0` on commit `35541cd2e91555f2c653be0a95ced560f89bcb2b`
- GitHub release object published at `https://github.com/joediggidyyy/calamum_vulcan/releases/tag/v0.3.0`
- production PyPI project page now carries `0.3.0` at `https://pypi.org/project/calamum-vulcan/0.3.0/`
- the release-triggered `Upload Python Package` workflow failed its PyPI publish leg, so the final production PyPI boundary was completed manually through the existing `pypi` profile

### Known limitations

- live firmware flashing remains outside the intended `0.3.0` public support boundary
- native read-side ownership remains limited to the reviewed Samsung subset; fallback remains explicit where ownership stops
- Windows remains the only empirically reviewed packaged host for the public `0.3.0` boundary
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