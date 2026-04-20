"""Unit tests for the Calamum Vulcan FS2-04 device registry."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.device_registry import DeviceCompatibilityStatus
from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind
from calamum_vulcan.domain.device_registry import available_device_profiles
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.device_registry import resolve_package_compatibility


class DeviceRegistryTests(unittest.TestCase):
  """Prove repo-owned device truth resolves deterministically for FS2-04."""

  def test_exact_product_code_resolution_returns_known_profile(self) -> None:
    resolution = resolve_device_profile('SM-G991U')

    self.assertTrue(resolution.known)
    self.assertEqual(resolution.match_kind, DeviceRegistryMatchKind.EXACT)
    self.assertEqual(resolution.canonical_product_code, 'SM-G991U')
    self.assertEqual(resolution.marketing_name, 'Galaxy S21')

  def test_alias_product_code_resolution_maps_to_canonical_profile(self) -> None:
    resolution = resolve_device_profile('g991u')

    self.assertTrue(resolution.known)
    self.assertEqual(resolution.match_kind, DeviceRegistryMatchKind.ALIAS)
    self.assertEqual(resolution.canonical_product_code, 'SM-G991U')
    self.assertEqual(resolution.marketing_name, 'Galaxy S21')

  def test_unknown_product_code_stays_unresolved(self) -> None:
    resolution = resolve_device_profile('SM-UNKNOWN1')

    self.assertFalse(resolution.known)
    self.assertEqual(resolution.match_kind, DeviceRegistryMatchKind.UNKNOWN)
    self.assertIsNone(resolution.canonical_product_code)
    self.assertIsNone(resolution.marketing_name)

  def test_package_compatibility_uses_canonical_alias_match(self) -> None:
    resolution = resolve_package_compatibility(
      supported_product_codes=('SM-G991U',),
      supported_device_names=('Galaxy S21',),
      detected_product_code='g991u',
      expectation='matched',
      issues=(),
    )

    self.assertTrue(resolution.compatible)
    self.assertEqual(
      resolution.status,
      DeviceCompatibilityStatus.ALIAS_MATCHED,
    )
    self.assertIn('matches the package support list', resolution.summary)

  def test_available_profiles_cover_current_fixture_codes(self) -> None:
    product_codes = tuple(
      profile.canonical_product_code for profile in available_device_profiles()
    )

    self.assertIn('SM-G973F', product_codes)
    self.assertIn('SM-G991U', product_codes)
    self.assertIn('SM-G996U', product_codes)
    self.assertIn('SM-N975F', product_codes)


if __name__ == '__main__':
  unittest.main()
