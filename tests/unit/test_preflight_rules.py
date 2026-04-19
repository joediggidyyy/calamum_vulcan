"""Unit tests for the Calamum Vulcan FS-04 preflight rule engine."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.preflight import PreflightGate
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import PreflightSeverity
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.state import replay_events
from calamum_vulcan.fixtures import blocked_then_cleared_events
from calamum_vulcan.fixtures import blocked_validation_events
from calamum_vulcan.fixtures import happy_path_events
from calamum_vulcan.fixtures import package_first_events


class PreflightRuleTests(unittest.TestCase):
  """Prove blocked, warning, and ready semantics for FS-04."""

  def test_ready_session_opens_the_preflight_gate(self) -> None:
    session = replay_events(blocked_then_cleared_events())
    report = evaluate_preflight(PreflightInput.from_session(session))

    self.assertEqual(report.gate, PreflightGate.READY)
    self.assertTrue(report.ready_for_execution)
    self.assertEqual(report.block_count, 0)

  def test_product_code_mismatch_blocks_the_gate(self) -> None:
    session = replay_events(blocked_validation_events())
    report = evaluate_preflight(PreflightInput.from_session(session))

    self.assertEqual(report.gate, PreflightGate.BLOCKED)
    self.assertFalse(report.ready_for_execution)
    self.assertTrue(
      any(
        signal.rule_id == 'product_code_match'
        and signal.severity == PreflightSeverity.BLOCK
        for signal in report.signals
      )
    )

  def test_warning_state_requires_operator_acknowledgement(self) -> None:
    session = replay_events(package_first_events()[:-1])
    report = evaluate_preflight(
      PreflightInput.from_session(session, battery_level=22)
    )

    self.assertEqual(report.gate, PreflightGate.WARN)
    self.assertFalse(report.ready_for_execution)
    self.assertGreaterEqual(report.warning_count, 1)

  def test_destructive_ack_is_required_before_ready(self) -> None:
    session = replay_events(happy_path_events()[:4])
    report = evaluate_preflight(PreflightInput.from_session(session))

    self.assertEqual(report.gate, PreflightGate.BLOCKED)
    self.assertTrue(
      any(
        signal.rule_id == 'destructive_ack'
        and signal.severity == PreflightSeverity.BLOCK
        for signal in report.signals
      )
    )


if __name__ == '__main__':
  unittest.main()