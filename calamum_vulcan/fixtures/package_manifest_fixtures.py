"""Package-manifest fixture helpers for the FS-05 lane."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict
from typing import Tuple


PACKAGE_MANIFEST_FIXTURE_DIR = Path(__file__).resolve().parent / 'package_manifests'

PUBLIC_PACKAGE_MANIFEST_FIXTURES = {
  'matched': 'matched_recovery_package.json',
  'mismatched': 'mismatched_recovery_package.json',
  'incomplete': 'incomplete_recovery_package.json',
  'suspicious-review': 'suspicious_review_package.json',
}  # type: Dict[str, str]

INTERNAL_SCENARIO_PACKAGE_MANIFEST_FIXTURES = {
  'ready-standard': 'ready_standard_review_package.json',
  'package-first-standard': 'package_first_standard_review_package.json',
  'blocked-review': 'blocked_review_package.json',
}  # type: Dict[str, str]

PACKAGE_MANIFEST_FIXTURES = {}
PACKAGE_MANIFEST_FIXTURES.update(PUBLIC_PACKAGE_MANIFEST_FIXTURES)
PACKAGE_MANIFEST_FIXTURES.update(INTERNAL_SCENARIO_PACKAGE_MANIFEST_FIXTURES)


def available_package_manifest_fixtures() -> Tuple[str, ...]:
  """Return supported package-manifest fixture names."""

  return tuple(PUBLIC_PACKAGE_MANIFEST_FIXTURES.keys())


def package_manifest_fixture_path(name: str) -> Path:
  """Return the path to one package-manifest fixture."""

  if name not in PACKAGE_MANIFEST_FIXTURES:
    raise KeyError('Unknown package fixture: {name}'.format(name=name))
  return PACKAGE_MANIFEST_FIXTURE_DIR / PACKAGE_MANIFEST_FIXTURES[name]


def load_package_manifest_fixture(name: str) -> Dict[str, object]:
  """Load one manifest fixture into a Python mapping for tests."""

  fixture_path = package_manifest_fixture_path(name)
  with fixture_path.open('r', encoding='utf-8') as fixture_file:
    return json.load(fixture_file)