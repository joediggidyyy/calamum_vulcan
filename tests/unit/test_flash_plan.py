"""Unit tests for the Calamum Vulcan FS2-05 reviewed flash-plan surface."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
from calamum_vulcan.domain.package import assess_package_manifest
from calamum_vulcan.fixtures import load_package_manifest_fixture


class FlashPlanTests(unittest.TestCase):
  """Prove the reviewed flash-plan builder preserves operator truth."""

  def test_ready_standard_plan_is_review_ready(self) -> None:
    session = build_demo_session('ready')
    assessment = build_demo_package_assessment('ready', session=session)

    plan = build_reviewed_flash_plan(assessment)

    self.assertTrue(plan.ready_for_transport)
    self.assertEqual(plan.transport_backend, 'heimdall')
    self.assertEqual(plan.reboot_policy, 'standard')
    self.assertFalse(plan.repartition_allowed)
    self.assertEqual(plan.partition_targets, ('RECOVERY', 'VBMETA'))
    self.assertIn('Galaxy S21', plan.summary)

  def test_no_reboot_plan_carries_manual_recovery_guidance(self) -> None:
    session = build_demo_session('happy')
    assessment = build_demo_package_assessment(
      'happy',
      session=session,
      package_fixture_name='matched',
    )

    plan = build_reviewed_flash_plan(assessment)

    self.assertTrue(plan.ready_for_transport)
    self.assertEqual(plan.reboot_policy, 'no_reboot')
    self.assertTrue(
      any('automatic reboot' in item.lower() for item in plan.recovery_guidance)
    )
    self.assertTrue(
      any('boot directly into recovery' in item.lower() for item in plan.recovery_guidance)
    )

  def test_mismatched_device_blocks_reviewed_flash_plan(self) -> None:
    session = build_demo_session('ready')
    assessment = build_demo_package_assessment(
      'ready',
      session=session,
      package_fixture_name='matched',
    )

    plan = build_reviewed_flash_plan(assessment)

    self.assertFalse(plan.ready_for_transport)
    self.assertTrue(
      any('does not match' in reason.lower() for reason in plan.blocking_reasons)
    )

  def test_repartition_plan_requires_pit_fingerprint(self) -> None:
    manifest = load_package_manifest_fixture('ready-standard')
    manifest['flash_plan']['repartition_allowed'] = True
    manifest['compatibility']['pit_fingerprint'] = ''
    session = build_demo_session('ready')
    assessment = assess_package_manifest(
      manifest,
      fixture_name='repartition-missing-pit',
      detected_product_code=session.product_code,
    )

    plan = build_reviewed_flash_plan(assessment)

    self.assertFalse(plan.ready_for_transport)
    self.assertIn('print_pit', plan.required_capabilities)
    self.assertTrue(
      any('pit fingerprint' in reason.lower() for reason in plan.blocking_reasons)
    )

  def test_suspicious_review_plan_remains_transport_ready_but_visible(self) -> None:
    session = build_demo_session('ready')
    assessment = build_demo_package_assessment(
      'ready',
      session=session,
      package_fixture_name='suspicious-review',
    )

    plan = build_reviewed_flash_plan(assessment)

    self.assertTrue(plan.ready_for_transport)
    self.assertEqual(plan.suspicious_warning_count, 7)
    self.assertTrue(plan.requires_operator_acknowledgement)
    self.assertTrue(plan.operator_warnings)
    self.assertIn('warning-tier suspicious Android traits', plan.summary)


if __name__ == '__main__':
  unittest.main()
