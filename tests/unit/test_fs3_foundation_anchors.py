"""Unit tests for the Calamum Vulcan FS3-01 foundation anchors."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

import calamum_vulcan.domain as domain
from calamum_vulcan.domain.live_device import LIVE_DEVICE_SCHEMA_VERSION
from calamum_vulcan.domain.pit import PIT_SCHEMA_VERSION


class FS301FoundationAnchorTests(unittest.TestCase):
  """Prove the Sprint 0.3.0 anchor packages import cleanly."""

  def test_domain_package_exports_fs3_anchor_packages(self) -> None:
    self.assertIn('live_device', domain.__all__)
    self.assertIn('pit', domain.__all__)

  def test_live_device_anchor_exposes_schema_version(self) -> None:
    self.assertEqual(LIVE_DEVICE_SCHEMA_VERSION, '0.3.0-fs3-03')

  def test_pit_anchor_exposes_schema_version(self) -> None:
    self.assertEqual(PIT_SCHEMA_VERSION, '0.3.0-fs3-04')


if __name__ == '__main__':
  unittest.main()
