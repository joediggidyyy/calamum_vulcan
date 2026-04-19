# Changelog

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

### Known limitations

- the published flashing workflow remains simulation-validated rather than live-subprocess-backed
- live companion device controls remain bounded lab-review surfaces rather than broad public flashing claims
- Windows is the only empirically reviewed packaged host for `0.1.0`
- Qt font packaging remains unresolved deployment debt
- warning-tier security debt remains in package checksum placeholders, real archive import, and Android-image heuristics