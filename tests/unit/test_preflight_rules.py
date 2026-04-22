"""Unit tests for the Calamum Vulcan FS-04 preflight rule engine."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind
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

  def test_unknown_device_registry_blocks_review_before_package_match(self) -> None:
    report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=False,
        product_code='SM-UNKNOWN1',
        package_id='regional-match-demo',
      )
    )

    self.assertEqual(report.gate, PreflightGate.BLOCKED)
    self.assertTrue(
      any(
        signal.rule_id == 'device_registry'
        and signal.severity == PreflightSeverity.BLOCK
        for signal in report.signals
      )
    )
    self.assertFalse(
      any(signal.rule_id == 'product_code_match' for signal in report.signals)
    )

  def test_alias_resolution_keeps_the_gate_open_when_other_rules_pass(self) -> None:
    report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=True,
        device_registry_match_kind=DeviceRegistryMatchKind.ALIAS,
        product_code='g991u',
        canonical_product_code='SM-G991U',
        device_marketing_name='Galaxy S21',
        product_code_match=True,
        warnings_acknowledged=True,
        battery_level=72,
        package_id='regional-match-demo',
      )
    )

    self.assertEqual(report.gate, PreflightGate.READY)
    self.assertTrue(
      any(
        signal.rule_id == 'device_registry'
        and signal.severity == PreflightSeverity.PASS
        for signal in report.signals
      )
    )

  def test_acknowledged_suspicious_warning_keeps_gate_ready(self) -> None:
    report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=True,
        product_code='SM-G991U',
        canonical_product_code='SM-G991U',
        device_marketing_name='Galaxy S21',
        product_code_match=True,
        warnings_acknowledged=True,
        battery_level=72,
        package_id='suspicious-review-demo',
        suspicious_warning_count=2,
        suspiciousness_summary='2 warning-tier suspicious Android traits detected.',
        suspicious_indicator_ids=('test_keys', 'magisk'),
      )
    )

    self.assertEqual(report.gate, PreflightGate.READY)
    self.assertTrue(report.ready_for_execution)
    self.assertGreaterEqual(report.warning_count, 1)
    self.assertTrue(
      any(
        signal.rule_id == 'package_suspiciousness'
        and signal.severity == PreflightSeverity.WARN
        for signal in report.signals
      )
    )

  def test_pit_package_mismatch_blocks_the_gate(self) -> None:
    report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=True,
        product_code='SM-G991U',
        canonical_product_code='SM-G991U',
        device_marketing_name='Galaxy S21',
        product_code_match=True,
        warnings_acknowledged=True,
        battery_level=72,
        package_id='regional-match-demo',
        pit_state='captured',
        pit_summary='Repo-owned PIT inspection captured alignment truth.',
        pit_package_alignment='mismatched',
        pit_device_alignment='matched',
        pit_observed_product_code='SM-G991U',
      )
    )

    self.assertEqual(report.gate, PreflightGate.BLOCKED)
    self.assertFalse(report.ready_for_execution)
    self.assertTrue(
      any(
        signal.rule_id == 'pit_package_alignment'
        and signal.severity == PreflightSeverity.BLOCK
        for signal in report.signals
      )
    )

  def test_acknowledged_partial_pit_truth_keeps_gate_ready(self) -> None:
    report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=True,
        product_code='SM-G991U',
        canonical_product_code='SM-G991U',
        device_marketing_name='Galaxy S21',
        product_code_match=True,
        warnings_acknowledged=True,
        battery_level=72,
        package_id='regional-match-demo',
        pit_state='partial',
        pit_summary='PIT acquisition metadata was captured, but detailed partition inspection still requires print-pit output.',
        pit_package_alignment='matched',
        pit_device_alignment='matched',
        pit_observed_product_code='SM-G991U',
      )
    )

    self.assertEqual(report.gate, PreflightGate.READY)
    self.assertTrue(report.ready_for_execution)
    self.assertTrue(
      any(
        signal.rule_id == 'pit_state'
        and signal.severity == PreflightSeverity.WARN
        for signal in report.signals
      )
    )

  def test_pit_required_blocks_safe_path_when_review_truth_is_missing(self) -> None:
    report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=True,
        product_code='SM-G991U',
        canonical_product_code='SM-G991U',
        device_marketing_name='Galaxy S21',
        product_code_match=True,
        warnings_acknowledged=True,
        battery_level=72,
        package_id='regional-match-demo',
        pit_required=True,
      )
    )

    self.assertEqual(report.gate, PreflightGate.BLOCKED)
    self.assertFalse(report.ready_for_execution)
    self.assertTrue(
      any(
        signal.rule_id == 'pit_required'
        and signal.severity == PreflightSeverity.BLOCK
        for signal in report.signals
      )
    )


if __name__ == '__main__':
  unittest.main()