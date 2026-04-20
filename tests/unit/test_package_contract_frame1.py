"""Frame-1 tests for the Calamum Vulcan FS-05 package contract."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.package import FRAME_1_TEST_SURFACES
from calamum_vulcan.domain.package import validate_manifest_contract_shape
from calamum_vulcan.fixtures import available_package_manifest_fixtures
from calamum_vulcan.fixtures import load_package_manifest_fixture
from calamum_vulcan.fixtures import package_manifest_fixture_path


class PackageContractFrameOneTests(unittest.TestCase):
  """Prove the package contract and fixtures exist before parsing begins."""

  def test_frame_one_test_surfaces_cover_contract_and_checksum_concerns(self) -> None:
    surface_names = tuple(surface.name for surface in FRAME_1_TEST_SURFACES)

    self.assertEqual(
      surface_names,
      (
        'manifest_identity_completeness',
        'product_code_compatibility',
        'checksum_placeholder_coverage',
        'partition_plan_preview',
        'incomplete_manifest_handling',
      ),
    )

  def test_matched_fixture_is_contract_complete(self) -> None:
    manifest = load_package_manifest_fixture('matched')
    issues = validate_manifest_contract_shape(manifest)

    self.assertEqual(issues, ())
    self.assertEqual(manifest['compatibility']['expectation'], 'matched')
    self.assertEqual(manifest['flash_plan']['risk_level'], 'destructive')

  def test_mismatched_fixture_is_complete_but_declares_mismatch(self) -> None:
    manifest = load_package_manifest_fixture('mismatched')
    issues = validate_manifest_contract_shape(manifest)

    self.assertEqual(issues, ())
    self.assertEqual(manifest['compatibility']['expectation'], 'mismatch')
    self.assertEqual(manifest['compatibility']['supported_product_codes'][0], 'SM-G991U')

  def test_incomplete_fixture_fails_contract_validation(self) -> None:
    manifest = load_package_manifest_fixture('incomplete')
    issues = validate_manifest_contract_shape(manifest)

    self.assertTrue(issues)
    self.assertIn('compatibility.pit_fingerprint is required', issues)
    self.assertIn('manifest.checksums is required', issues)
    self.assertIn('flash_plan.partitions is required', issues)

  def test_package_fixtures_and_centralized_artifacts_exist_under_root(self) -> None:
    fixture_names = available_package_manifest_fixtures()
    launcher_path = FINAL_EXAM_ROOT / 'calamum_vulcan' / 'launch_shell.py'
    requirements_path = FINAL_EXAM_ROOT / 'calamum_vulcan' / 'requirements.txt'

    self.assertEqual(
      fixture_names,
      ('matched', 'mismatched', 'incomplete', 'suspicious-review'),
    )
    for name in fixture_names:
      self.assertTrue(package_manifest_fixture_path(name).is_file())
    self.assertTrue(launcher_path.is_file())
    self.assertTrue(requirements_path.is_file())


if __name__ == '__main__':
  unittest.main()