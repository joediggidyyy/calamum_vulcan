"""Reporting-contract tests for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_adapter_session
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.domain.reporting import REPORT_EXPORT_TARGETS
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.reporting import render_session_evidence_markdown
from calamum_vulcan.domain.reporting import serialize_session_evidence_json
from calamum_vulcan.domain.reporting import write_session_evidence_report


class ReportingContractTests(unittest.TestCase):
  """Prove the FS-06 evidence contract for ready, failure, and incomplete states."""

  def test_ready_report_serializes_with_package_and_preflight_context(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
      captured_at_utc='2026-04-18T20:15:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    self.assertEqual(payload['preflight']['gate'], 'ready')
    self.assertEqual(payload['package']['package_id'], 'regional-match-demo')
    self.assertEqual(payload['captured_at_utc'], '2026-04-18T20:15:00Z')
    self.assertGreaterEqual(len(payload['decision_trace']), 3)
    self.assertEqual(payload['transport']['state'], 'not_invoked')

  def test_failure_report_carries_recovery_guidance_into_markdown(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('failure')
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('failure'),
      package_assessment=package_assessment,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-18T20:20:00Z',
    )

    markdown = render_session_evidence_markdown(report)
    self.assertEqual(report.outcome.outcome, 'failed')
    self.assertIn('Recovery guidance', markdown)
    self.assertIn('Stabilize the direct USB path', markdown)
    self.assertIn('USB transfer timeout during partition write', markdown)
    self.assertIn('### Transport', markdown)
    self.assertIn('heimdall flash', markdown)

  def test_incomplete_manifest_report_marks_contract_gap(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment(
      'ready',
      session=session,
      package_fixture_name='incomplete',
    )
    report = build_session_evidence_report(
      session,
      scenario_name='Incomplete manifest review',
      package_assessment=package_assessment,
      captured_at_utc='2026-04-18T20:25:00Z',
    )

    self.assertFalse(report.package.contract_complete)
    self.assertEqual(report.preflight.gate, 'blocked')
    self.assertTrue(report.package.contract_issues)

  def test_adapter_backed_report_carries_transport_trace(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('happy')
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('happy'),
      package_assessment=package_assessment,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-18T20:27:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    self.assertEqual(payload['transport']['adapter_name'], 'heimdall')
    self.assertEqual(payload['transport']['state'], 'completed')
    self.assertEqual(payload['transport']['normalized_event_count'], 2)

  def test_writer_persists_markdown_report_to_disk(self) -> None:
    session = build_demo_session('blocked')
    package_assessment = build_demo_package_assessment('blocked', session=session)
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('blocked'),
      package_assessment=package_assessment,
      captured_at_utc='2026-04-18T20:30:00Z',
    )

    with TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'blocked_evidence.md'
      written_path = write_session_evidence_report(
        report,
        output_path,
        format_name='markdown',
      )
      contents = written_path.read_text(encoding='utf-8')

    self.assertEqual(tuple(REPORT_EXPORT_TARGETS), ('json', 'markdown'))
    self.assertEqual(written_path, output_path)
    self.assertIn('Calamum Vulcan session evidence', contents)
    self.assertIn('Blocked preflight review', contents)


if __name__ == '__main__':
  unittest.main()