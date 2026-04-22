"""Tests for the Sprint 0.4.0 readiness runner."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from scripts.run_v040_readiness_stack import build_default_lanes
from scripts.run_v040_readiness_stack import _render_markdown_summary


class Sprint040ReadinessStackTests(unittest.TestCase):
  """Keep the Sprint 4 readiness schedule explicit and multi-strategy."""

  def test_default_lane_order_covers_all_required_strategies(self) -> None:
    lanes = build_default_lanes()

    self.assertEqual(
      tuple(lane.name for lane in lanes),
      (
        'pytest_baseline',
        'aggressive_penetration_pytest',
        'aggressive_penetration_suite',
        'build_artifacts',
        'sandbox_installed_artifact',
        'scripted_simulation',
        'empirical_review',
      ),
    )
    self.assertEqual(
      tuple(lane.category for lane in lanes),
      (
        'pytest',
        'penetration',
        'penetration',
        'sandbox',
        'sandbox',
        'scripted',
        'empirical',
      ),
    )

  def test_testpypi_lane_is_opt_in(self) -> None:
    lanes = build_default_lanes(include_testpypi=True)

    self.assertEqual(lanes[-1].name, 'testpypi_rehearsal')
    self.assertEqual(lanes[-1].category, 'release')
    self.assertIn('run_testpypi_rehearsal.py', lanes[-1].command[-1])

  def test_penetration_lane_targets_security_and_adversarial_surfaces(self) -> None:
    lanes = build_default_lanes()
    penetration_pytest = lanes[1]
    penetration_suite = lanes[2]

    self.assertTrue(
      any('test_security_validation.py' in part for part in penetration_pytest.command)
    )
    self.assertTrue(
      any('test_package_importer.py' in part for part in penetration_pytest.command)
    )
    self.assertTrue(
      any('test_package_snapshot.py' in part for part in penetration_pytest.command)
    )
    self.assertTrue(
      any('test_pit_contract.py' in part for part in penetration_pytest.command)
    )
    self.assertEqual(
      penetration_suite.command[-1],
      'scripts/run_security_validation_suite.py',
    )

  def test_markdown_summary_mentions_strategy_coverage(self) -> None:
    summary = {
      'repo_root': str(FINAL_EXAM_ROOT),
      'overall_status': 'passed',
      'include_testpypi_rehearsal': False,
      'lanes': [
        {
          'name': 'pytest_baseline',
          'category': 'pytest',
          'status': 'passed',
          'command': ('python', '-m', 'pytest', 'tests/unit', '-q'),
          'evidence_hint': 'Source-tree contract and unit proof.',
          'stdout_path': 'temp/fs4_readiness/pytest_baseline/stdout.txt',
          'stderr_path': 'temp/fs4_readiness/pytest_baseline/stderr.txt',
        },
        {
          'name': 'empirical_review',
          'category': 'empirical',
          'status': 'passed',
          'command': ('python', 'scripts/run_empirical_review_stack.py'),
          'evidence_hint': 'Empirical review proof.',
          'stdout_path': 'temp/fs4_readiness/empirical_review/stdout.txt',
          'stderr_path': 'temp/fs4_readiness/empirical_review/stderr.txt',
        },
      ],
    }

    markdown = _render_markdown_summary(summary)

    self.assertIn('Sprint 0.4.0 readiness summary', markdown)
    self.assertIn('Strategy coverage', markdown)
    self.assertIn('aggressive penetration-style archive, drift, malformed-input, and security-boundary checks', markdown)
    self.assertIn('packaged GUI and evidence readability review', markdown)


if __name__ == '__main__':
  unittest.main()
