# Calamum Vulcan

Samsung-focused open-source Android flashing platform with GUI-first workflows, preflight validation, and audit-ready evidence.

## Current status

`0.1.0` product-shell work is complete, empirical/public-doc review is now closed, and the repository is in the final publication-rehearsal lane before the first public package release.

Current release posture:

- public GitHub seed: `https://github.com/joediggidyyy/calamum_vulcan`
- release root: this repository root
- validated source-checkout runtime: Python `3.14`
- license: MIT
- current publication decision: `go` after a successful TestPyPI rehearsal and registry-delivered install validation from this repository root

## Source checkout quickstart

From the repository root:

1. activate a validated Python `3.14` environment
2. run the unit suite
3. launch a shell scenario or an integration bundle review

Representative commands:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- `python calamum_vulcan/launch_shell.py --scenario ready --describe-only`
- `python -m calamum_vulcan.app --integration-suite sprint-close --suite-format markdown --suite-output temp/fs08_sprint_close.md`

## Installed-artifact quickstart

For a release-style review from the built wheel:

1. build the artifacts from this repository root
2. install the wheel into a clean Python `3.14` environment
3. verify the public CLI, evidence export, and GUI launch surface

Representative commands:

- `python scripts/build_release_artifacts.py`
- `python -m pip install dist/calamum_vulcan-0.1.0-py3-none-any.whl`
- `calamum-vulcan --scenario ready --describe-only`
- `calamum-vulcan --scenario blocked --describe-only --export-evidence --evidence-format markdown --evidence-output blocked_review.md`
- `calamum-vulcan-gui --scenario ready`

## Packaging and build

Build and inspect release artifacts from the repository root with:

- `python -m pip install -e .[release]`
- `python scripts/build_release_artifacts.py`
- `python scripts/validate_installed_artifact.py`
- `python scripts/run_scripted_simulation_suite.py`

This produces and inspects both `sdist` and `wheel` artifacts from the nested release root.

The installed-artifact runner creates a clean temporary environment, installs the built wheel outside the source tree, verifies the public entry points, exercises evidence export and the sprint-close bundle, and audits the packaged file surface.

The scripted simulation runner executes the publication-safe scenario matrix from both the release root and an installed wheel context, checks deterministic JSON and Markdown evidence outputs, validates offscreen GUI launch behavior, and archives the resulting bundle evidence under `temp/fs_p04_scripted_simulation/`.

The empirical review runner performs the clean-install walkthrough, captures packaged GUI screenshots for human review, inspects release-facing evidence exports, and archives the resulting artifacts under `temp/fs_p05_empirical_review/`.

- `python scripts/run_empirical_review_stack.py`

The TestPyPI rehearsal runner performs the final publication gate, attempts the registry rehearsal when credentials are configured, validates registry-delivered install behavior, and records a final go/no-go summary under `temp/fs_p06_testpypi_rehearsal/`.

- `python scripts/run_testpypi_rehearsal.py`

The publication rehearsal accepts TestPyPI credentials from the release-root `.env`, the active shell environment, or the user-level `.pypirc`:

- `CALAMUM_VULCAN_TESTPYPI_TOKEN`
- optional fallback: `TWINE_USERNAME=__token__` and `TWINE_PASSWORD`
- optional shared-user profile: `[testpypi]` in `~/.pypirc`

## Installed entry points

The packaging contract for `0.1.0` defines these installed entry points:

- `calamum-vulcan` — console entry point for CLI review flows and GUI launch
- `calamum-vulcan-gui` — GUI-oriented launcher entry point

## Repository layout

| Path              | Purpose                                                  |
| ----------------- | -------------------------------------------------------- |
| `calamum_vulcan/` | package source, launcher, fixtures, and runtime surfaces |
| `tests/`          | unit and release-lane validation surfaces                |
| `docs/`           | planning, evidence, and release-lane documentation       |
| `LICENSE`         | project license                                          |

## Documentation

Primary planning surfaces live in `docs/`:

- `Samsung_Android_Flashing_Platform_Research_Report_and_Build_Plan.md`
- `Samsung_Android_Flashing_Platform_0.1.0_Detailed_Planning.md`
- `Samsung_Android_Flashing_Platform_0.1.0_Execution_Evidence.md`
- `CHANGELOG.md`

## Scope

Calamum Vulcan is currently focused on Samsung-first flashing workflows with:

- GUI-first operator flows
- package-aware preflight gating
- structured session evidence
- a bounded Heimdall adapter seam for the `0.1.0` product shell
- bounded ADB/Fastboot companion controls for detection and reboot handoffs

## Support posture for `0.1.0`

| Surface                 | `0.1.0` posture                                                   |
| ----------------------- | ----------------------------------------------------------------- |
| Windows packaged build  | empirically reviewed                                              |
| Linux packaged build    | scripted-simulation target only; empirical closeout still pending |
| macOS                   | deferred and outside the published `0.1.0` support boundary       |
| Core flashing workflow  | simulation-validated                                              |
| Live companion controls | bounded lab review only for device detection and reboot handoffs  |
| Live firmware flashing  | not part of the published `0.1.0` support boundary                |

## Known limitations

| Area                  | Current limitation                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| Transport execution   | the published flashing workflow remains fixture-backed rather than live-subprocess-backed                     |
| PIT operator controls | PIT download and print capabilities exist at the adapter seam but are not yet exposed as public shell actions |
| Host matrix           | Windows is the only empirically reviewed packaged host for `0.1.0`                                            |
| Qt deployment         | Qt font packaging still emits a warning in some review environments                                           |

## Troubleshooting

| Symptom                                       | Likely cause                                                                                    | What to do                                                                                                               |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `calamum-vulcan` will not launch              | wrong interpreter or missing runtime dependency                                                 | use Python `3.14` and reinstall the wheel so `PySide6>=6.8,<7` is present                                                |
| GUI opens without branded assets              | stale wheel built before the branding assets were packaged                                      | rebuild with `python scripts/build_release_artifacts.py` and reinstall the fresh wheel                                   |
| No device appears in the live companion panel | device is not in the expected mode, ADB is not authorized, or Windows driver state is not ready | re-enter the correct device mode, authorize ADB if applicable, and review the Windows USB/driver posture before retrying |
| Qt prints a font warning during review        | known `0.1.0` packaging debt                                                                    | treat it as a non-blocking warning for now; the shell remains usable while the font-packaging lane is hardened           |
| Evidence file was not written where expected  | output path or permissions are wrong                                                            | choose a writable output path and rerun the export command                                                               |

## Release note

The current `0.1.0` release candidate has passed the TestPyPI rehearsal gate, including registry-delivered install validation, from this repository root.
