"""Parser and assessment tests for the Calamum Vulcan FS-05 package lane."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind
from calamum_vulcan.domain.package import PackageCompatibilityExpectation
from calamum_vulcan.domain.package import PackageManifestContractError
from calamum_vulcan.domain.package import PackageRiskLevel
from calamum_vulcan.domain.package import assess_package_manifest
from calamum_vulcan.domain.package import parse_package_summary_contract
from calamum_vulcan.domain.package import preflight_overrides_from_package_assessment
from calamum_vulcan.fixtures import load_package_manifest_fixture


class PackageParserTests(unittest.TestCase):
  """Prove typed parsing and assessment for matched, mismatched, and incomplete manifests."""

  def test_parse_matched_manifest_into_typed_summary(self) -> None:
    manifest = load_package_manifest_fixture('matched')
    summary = parse_package_summary_contract(manifest)

    self.assertEqual(summary.identity.package_id, 'calamum-recovery-lab-001')
    self.assertEqual(summary.risk_level, PackageRiskLevel.DESTRUCTIVE)
    self.assertEqual(summary.compatibility.expectation, PackageCompatibilityExpectation.MATCHED)
    self.assertEqual(len(summary.partitions), 1)
    self.assertEqual(len(summary.checksums), 1)

  def test_assessment_detects_blocked_review_product_code_mismatch(self) -> None:
    manifest = load_package_manifest_fixture('blocked-review')
    assessment = assess_package_manifest(
      manifest,
      detected_product_code='SM-G991U',
      fixture_name='blocked-review',
    )

    self.assertTrue(assessment.contract_complete)
    self.assertFalse(assessment.matches_detected_product_code)
    self.assertEqual(
      assessment.compatibility_expectation,
      PackageCompatibilityExpectation.MISMATCH,
    )

  def test_incomplete_manifest_raises_on_typed_parse(self) -> None:
    manifest = load_package_manifest_fixture('incomplete')

    with self.assertRaises(PackageManifestContractError):
      parse_package_summary_contract(manifest)

  def test_preflight_overrides_follow_package_assessment(self) -> None:
    manifest = load_package_manifest_fixture('matched')
    assessment = assess_package_manifest(
      manifest,
      detected_product_code='SM-G973F',
      fixture_name='matched',
    )
    overrides = preflight_overrides_from_package_assessment(assessment)

    self.assertTrue(overrides['package_complete'])
    self.assertTrue(overrides['checksums_present'])
    self.assertTrue(overrides['product_code_match'])
    self.assertTrue(overrides['destructive_operation'])

  def test_assessment_resolves_alias_product_code_through_registry(self) -> None:
    manifest = load_package_manifest_fixture('ready-standard')
    assessment = assess_package_manifest(
      manifest,
      detected_product_code='g991u',
      fixture_name='ready-standard',
    )

    self.assertTrue(assessment.matches_detected_product_code)
    self.assertTrue(assessment.device_registry_known)
    self.assertEqual(
      assessment.device_registry_match_kind,
      DeviceRegistryMatchKind.ALIAS,
    )
    self.assertEqual(assessment.resolved_product_code, 'SM-G991U')
    self.assertEqual(assessment.resolved_device_name, 'Galaxy S21')

  def test_assessment_marks_unknown_device_registry_profile_as_untrusted(self) -> None:
    manifest = load_package_manifest_fixture('ready-standard')
    assessment = assess_package_manifest(
      manifest,
      detected_product_code='SM-UNKNOWN1',
      fixture_name='ready-standard',
    )

    self.assertFalse(assessment.matches_detected_product_code)
    self.assertFalse(assessment.device_registry_known)
    self.assertIn('not yet profiled', assessment.compatibility_summary)

  def test_suspicious_review_fixture_surfaces_warning_tier_traits(self) -> None:
    manifest = load_package_manifest_fixture('suspicious-review')
    assessment = assess_package_manifest(
      manifest,
      detected_product_code='SM-G991U',
      fixture_name='suspicious-review',
    )
    overrides = preflight_overrides_from_package_assessment(assessment)

    self.assertTrue(assessment.contract_complete)
    self.assertEqual(assessment.suspicious_warning_count, 7)
    self.assertIn('warning-tier suspicious Android traits', assessment.suspiciousness_summary)
    self.assertIn('test_keys', tuple(
      finding.indicator_id for finding in assessment.suspicious_findings
    ))
    self.assertEqual(overrides['suspicious_warning_count'], 7)
    self.assertIn('selinux_permissive', overrides['suspicious_indicator_ids'])


if __name__ == '__main__':
  unittest.main()