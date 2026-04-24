"""Tests for the Sprint 0.6.0 readiness runner."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from scripts.run_v060_readiness_stack import _render_markdown_summary
from scripts.run_v060_readiness_stack import build_default_lanes


class Sprint060ReadinessStackTests(unittest.TestCase):
  """Keep the Sprint 6 readiness schedule explicit and package-only."""

  def test_default_lane_order_covers_required_autonomy_close_strategies(self) -> None:
    lanes = build_default_lanes()

    self.assertEqual(
      tuple(lane.name for lane in lanes),
      (
        'targeted_sprint6_closure_slice',
        'pytest_baseline',
        'aggressive_penetration_pytest',
        'aggressive_penetration_suite',
        'v060_alignment_audit',
        'build_artifacts',
        'sandbox_installed_artifact',
        'scripted_simulation',
        'smoke_empirical_review',
      ),
    )
    self.assertEqual(
      tuple(lane.category for lane in lanes),
      (
        'pytest',
        'pytest',
        'penetration',
        'penetration',
        'audit',
        'sandbox',
        'sandbox',
        'scripted',
        'smoke',
      ),
    )

  def test_targeted_closure_slice_covers_sprint6_specific_seams(self) -> None:
    targeted_lane = build_default_lanes()[0]

    self.assertTrue(
      any('test_usb_scanner.py' in part for part in targeted_lane.command)
    )
    self.assertTrue(
      any('test_qt_shell_contract.py' in part for part in targeted_lane.command)
    )
    self.assertTrue(
      any('test_integration_suite.py' in part for part in targeted_lane.command)
    )
    self.assertTrue(
      any('test_sprint_audit_metadata.py' in part for part in targeted_lane.command)
    )
    self.assertTrue(
      any('test_v060_readiness_stack.py' in part for part in targeted_lane.command)
    )

  def test_markdown_summary_mentions_audit_and_publication_deferral(self) -> None:
    summary = {
      'repo_root': str(FINAL_EXAM_ROOT),
      'overall_status': 'passed',
      'ready_for_live_empirical': True,
      'lanes': [
        {
          'name': 'targeted_sprint6_closure_slice',
          'category': 'pytest',
          'status': 'passed',
          'command': ('python', '-m', 'pytest', 'tests/unit/test_usb_scanner.py', '-q'),
          'evidence_hint': 'Focused Sprint 6 closure proof.',
          'stdout_path': 'temp/fs6_readiness/targeted_sprint6_closure_slice/stdout.txt',
          'stderr_path': 'temp/fs6_readiness/targeted_sprint6_closure_slice/stderr.txt',
        },
        {
          'name': 'v060_alignment_audit',
          'category': 'audit',
          'status': 'passed',
          'command': ('python', 'scripts/run_v060_alignment_audit.py'),
          'evidence_hint': 'Sprint 6 alignment audit proof.',
          'stdout_path': 'temp/fs6_readiness/v060_alignment_audit/stdout.txt',
          'stderr_path': 'temp/fs6_readiness/v060_alignment_audit/stderr.txt',
        },
      ],
    }

    markdown = _render_markdown_summary(summary)

    self.assertIn('Sprint 0.6.0 readiness summary', markdown)
    self.assertIn('ready for live empirical', markdown)
    self.assertIn('publication rehearsal deferred', markdown)
    self.assertIn('live Sprint 6 alignment verification against the autonomy contract', markdown)
    self.assertIn('packaged GUI launch, screenshot, and evidence-readability smoke proof', markdown)
    self.assertIn('ready_for_live_empirical=True', markdown)
    self.assertIn('renewed TestPyPI/PyPI rehearsal remains intentionally deferred', markdown)


if __name__ == '__main__':
  unittest.main()
