"""Tests for the FS-P04 scripted simulation runner."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from scripts.run_scripted_simulation_suite import FIXED_CAPTURED_AT_UTC
from scripts.run_scripted_simulation_suite import EXECUTE_MATRIX
from scripts.run_scripted_simulation_suite import SCENARIO_MATRIX


class ScriptedSimulationSuiteTests(unittest.TestCase):
  """Prove the FS-P04 scenario matrix stays explicit and deterministic."""

  def test_scenario_matrix_covers_expected_public_release_paths(self) -> None:
    self.assertEqual(
      tuple(scenario['name'] for scenario in SCENARIO_MATRIX),
      ('no-device', 'ready', 'blocked', 'mismatch', 'failure', 'resume'),
    )
    self.assertTrue(
      all('--describe-only' in scenario['cli_args'] for scenario in SCENARIO_MATRIX)
    )
    scenario_map = {scenario['name']: scenario for scenario in SCENARIO_MATRIX}
    self.assertIn('--transport-source', scenario_map['failure']['cli_args'])
    self.assertIn('integrated-runtime', scenario_map['failure']['cli_args'])
    self.assertIn('integrated-runtime', scenario_map['resume']['cli_args'])

  def test_execute_matrix_uses_integrated_runtime_for_supported_path_proof(self) -> None:
    self.assertEqual(
      tuple(case['name'] for case in EXECUTE_MATRIX),
      ('ready-execute', 'blocked-execute'),
    )
    for case in EXECUTE_MATRIX:
      with self.subTest(case=case['name']):
        self.assertIn('--execute-flash-plan', case['cli_args'])
        self.assertIn('--transport-source', case['cli_args'])
        self.assertIn('integrated-runtime', case['cli_args'])

  def test_fixed_capture_timestamp_is_pinned_for_reproducible_artifacts(self) -> None:
    self.assertEqual(FIXED_CAPTURED_AT_UTC, '2026-04-18T23:10:00Z')


if __name__ == '__main__':
  unittest.main()