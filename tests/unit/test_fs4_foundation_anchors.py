"""Unit tests for the Calamum Vulcan FS4-01 foundation anchors."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

import calamum_vulcan.domain as domain
from calamum_vulcan.app.integration import available_integration_suites
from calamum_vulcan.app.integration import planned_integration_suites
from calamum_vulcan.domain.safe_path import SAFE_PATH_CLOSE_SUITE_NAME
from calamum_vulcan.domain.safe_path import SAFE_PATH_EVIDENCE_REQUIREMENTS
from calamum_vulcan.domain.safe_path import SAFE_PATH_SCHEMA_VERSION
from calamum_vulcan.domain.safe_path import SafePathContract
from calamum_vulcan.domain.safe_path import SafePathOwnership
from calamum_vulcan.domain.safe_path import SafePathReadiness
from calamum_vulcan.domain.safe_path import SafePathScope
from calamum_vulcan.domain.state import SESSION_AUTHORITY_SCHEMA_VERSION
from calamum_vulcan.domain.state import SessionAuthorityContract
from calamum_vulcan.domain.state import SessionAuthorityPosture
from calamum_vulcan.domain.state import SessionTruthSurface


class FS401FoundationAnchorTests(unittest.TestCase):
  """Prove the Sprint 0.4.0 foundation anchors import cleanly."""

  def test_domain_package_exports_fs4_anchor_package(self) -> None:
    self.assertIn('safe_path', domain.__all__)

  def test_safe_path_anchor_exposes_schema_and_closeout_name(self) -> None:
    contract = SafePathContract()

    self.assertEqual(SAFE_PATH_SCHEMA_VERSION, '0.4.0-fs4-01')
    self.assertEqual(contract.closeout_suite_name, SAFE_PATH_CLOSE_SUITE_NAME)
    self.assertEqual(contract.scope, SafePathScope.BOUNDED)
    self.assertEqual(contract.ownership, SafePathOwnership.BLOCKED)
    self.assertEqual(contract.readiness, SafePathReadiness.UNREVIEWED)
    self.assertTrue(contract.fallback_visibility_required)
    self.assertIn('closeout_boundary_alignment_review', SAFE_PATH_EVIDENCE_REQUIREMENTS)
    self.assertNotIn('trusted_publication_rehearsal', SAFE_PATH_EVIDENCE_REQUIREMENTS)

  def test_session_authority_anchor_exposes_split_truth_surfaces(self) -> None:
    contract = SessionAuthorityContract()

    self.assertEqual(SESSION_AUTHORITY_SCHEMA_VERSION, '0.4.0-fs4-01')
    self.assertEqual(contract.posture, SessionAuthorityPosture.SPLIT)
    self.assertEqual(
      contract.truth_surfaces,
      (
        SessionTruthSurface.REVIEWED_SESSION,
        SessionTruthSurface.LIVE_COMPANION,
        SessionTruthSurface.INSPECTION_EVIDENCE,
        SessionTruthSurface.FALLBACK_STATUS,
      ),
    )

  def test_safe_path_close_suite_is_now_publicly_available(self) -> None:
    self.assertEqual(planned_integration_suites(), ())
    self.assertIn(SAFE_PATH_CLOSE_SUITE_NAME, available_integration_suites())


if __name__ == '__main__':
  unittest.main()
