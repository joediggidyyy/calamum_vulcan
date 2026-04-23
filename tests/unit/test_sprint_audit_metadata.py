"""Regression tests for Sprint 5 and Sprint 6 audit metadata."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))


def _load_script_module(relative_path: str, module_name: str):
  module_path = FINAL_EXAM_ROOT / relative_path
  spec = importlib.util.spec_from_file_location(module_name, module_path)
  if spec is None or spec.loader is None:
    raise RuntimeError('Unable to load script module: {path}'.format(path=module_path))
  module = importlib.util.module_from_spec(spec)
  sys.modules[module_name] = module
  spec.loader.exec_module(module)
  return module


v050_audit = _load_script_module(
  'scripts/run_v050_timeline_audit.py',
  'calamum_vulcan_tests_run_v050_timeline_audit',
)
v060_audit = _load_script_module(
  'scripts/run_v060_alignment_audit.py',
  'calamum_vulcan_tests_run_v060_alignment_audit',
)


class SprintAuditMetadataTests(unittest.TestCase):
  """Lock the reconciled sprint audit vocabulary and drift guards."""

  def test_v050_sprint_label_matches_reconciled_scope(self) -> None:
    self.assertEqual(
      v050_audit.SPRINT_LABELS['0.5.0'],
      'efficient integrated transport extraction',
    )

  def test_v050_publication_drift_guard_only_flags_stale_claims(self) -> None:
    self.assertTrue(
      v050_audit._has_stale_publication_closeout_claim(
        'the public publication route proves restored trusted publication'
      )
    )
    self.assertFalse(
      v050_audit._has_stale_publication_closeout_claim(
        'package metadata and closeout evidence agree while public promotion remains deferred'
      )
    )

  def test_v050_package_boundary_status_requires_readiness_before_alignment(self) -> None:
    self.assertEqual(
      v050_audit._build_sprint5_package_boundary_status(False, False),
      'open',
    )
    self.assertEqual(
      v050_audit._build_sprint5_package_boundary_status(False, True),
      'partial',
    )
    self.assertEqual(
      v050_audit._build_sprint5_package_boundary_status(True, True),
      'implemented',
    )

  def test_v060_release_lag_deviation_tracks_current_repo_baseline(self) -> None:
    deviation_map = {
      finding.finding_id: finding
      for finding in v060_audit._build_deviations({})
    }

    evidence_text = ' '.join(deviation_map['D-03'].evidence)
    self.assertIn('0.5.0', evidence_text)
    self.assertIn('0.3.0', evidence_text)


if __name__ == '__main__':
  unittest.main()