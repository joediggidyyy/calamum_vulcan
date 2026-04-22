# Contributing to Calamum Vulcan

**Document ID**: `CALAMUM_VULCAN_CONTRIBUTING_040`  
**Status**: Public contributing guidelines  
**Owner**: ORACL-Prime  
**Project**: Calamum Vulcan  
**Last updated**: 2026-04-22

---

<p align="center">
  <img src="calamum_vulcan/assets/branding/polymath_global.png" alt="Polymath Global Logo" width="200">
</p>

## Working root

Treat this repository root as the canonical working root for build, test, packaging, and publication work.

Do not rely on parent-repository paths, parent-only tooling, or machine-local assumptions when changing public-facing surfaces.

## Environment

Use the validated runtime for current development and release-lane execution:

- `.venv-core`

## Baseline checks

Run these checks from the repository root before closing a change:

- `python -m unittest discover -s tests/unit -p "test_*.py"`
- `python calamum_vulcan/launch_shell.py --scenario ready --describe-only`

When touching release-lane surfaces, also run the relevant scripted simulation or evidence-export checks for the stack you are executing.

## Packaging lane checks

For packaging and publication-lane work, use repository-root commands only:

- `python -m pip install -e .[release]`
- `python scripts/build_release_artifacts.py`
- `python scripts/validate_installed_artifact.py`
- `python scripts/run_scripted_simulation_suite.py`

The build runner is the repeatable artifact-contract check for `FS-P02`.

The installed-artifact runner is the repeatable clean-environment smoke and packaged-surface check for `FS-P03`.

The scripted simulation runner is the repeatable release-root and installed-artifact scenario matrix, offscreen GUI, and deterministic evidence-export check for `FS-P04`.

## Sprint `0.4.0` package-only closeout

For the current Sprint 4 closeout lane:

- treat `0.4.0` as a **local package-only boundary**, not a public PyPI/GitHub publication boundary
- a pushed `v0.4.0` tag is acceptable as the repository-visible Sprint 4 seal, but do not treat it as a stable public promotion boundary
- keep `0.3.0` as the current public release until the later post-`0.6.0` `1.0.0` promotion gate
- run the Sprint 4 readiness and closeout proof before claiming the boundary is frozen:
	- `python scripts/run_v040_readiness_stack.py`
	- `python scripts/run_v040_timeline_audit.py --refresh-readiness`
	- `python scripts/build_release_artifacts.py`
	- `python scripts/validate_installed_artifact.py`
	- `python scripts/run_scripted_simulation_suite.py`
	- `python scripts/run_empirical_review_stack.py`
- preserve publication workflow knowledge as dormant carry-forward input, not as Sprint 4 success criteria

## Dormant publication workflow

The release-triggered GitHub Actions publisher lives at:

- `.github/workflows/python-publish.yml`

The current production workflow publishes with the `pypi` environment secret:

- `PYPI_API_TOKEN`

Release-maintainer rules:

- keep `PYPI_API_TOKEN` project-scoped to `calamum-vulcan`
- bind it to the GitHub Actions environment `pypi`
- treat the secret value as a PyPI API token, not a username/password pair
- keep `attestations: false` while the workflow is using token-backed upload instead of Trusted Publishing
- rerunning an old release job uses the workflow file frozen at that tag's commit, not the latest workflow on `main`
- use the workflow's manual dispatch from `main` with `source_ref=refs/tags/vX.Y.Z` when you need to replay publication logic against an existing release tag

Context for this decision:

- the unchanged Trusted Publishing workflow failed for both the `v0.2.0` and `v0.3.0` release runs with PyPI `invalid-publisher`
- the package itself was still publishable with the existing project-scoped PyPI token

If Trusted Publishing is reintroduced later, remove the explicit token input, restore the job-level `id-token: write` permission, and re-enable attestations only after the PyPI publisher record is confirmed to match the workflow.

## Documentation discipline

Keep public-facing docs:

- free of local absolute paths
- free of parent-repo assumptions
- aligned to the release root as the public boundary
- explicit about validated versus planned behavior

## Security reports

If you discover a potentially sensitive vulnerability, do not open a public issue first.

Use the private reporting guidance in `SECURITY.md`.

## Scope discipline

For current local `0.4.x` closeout work:

- keep the GUI-first shell contract intact
- keep `.venv-core` as the default validated runtime
- treat Qt font warnings as packaging debt, not functional test failures
- do not imply native read-side ownership beyond the reviewed Samsung subset that was actually validated
- do not imply a fully Calamum-owned integrated Samsung runtime before the later `0.6.0` autonomy boundary is actually closed
- do not imply public `0.4.0` publication; this sprint closes as a package-only boundary
