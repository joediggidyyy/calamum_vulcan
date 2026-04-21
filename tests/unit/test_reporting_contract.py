"""Reporting-contract tests for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

from dataclasses import replace
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
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
from calamum_vulcan.domain.live_device import apply_live_device_info_trace
from calamum_vulcan.domain.live_device import build_live_detection_session
from calamum_vulcan.domain.reporting import REPORT_EXPORT_TARGETS
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.reporting import render_session_evidence_markdown
from calamum_vulcan.domain.reporting import serialize_session_evidence_json
from calamum_vulcan.domain.reporting import write_session_evidence_report
from calamum_vulcan.domain.state import build_inspection_workflow


class ReportingContractTests(unittest.TestCase):
  """Prove the FS-06 evidence contract for ready, failure, and incomplete states."""

  def test_ready_report_serializes_with_package_and_preflight_context(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      captured_at_utc='2026-04-18T20:15:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    self.assertEqual(payload['preflight']['gate'], 'ready')
    self.assertEqual(payload['package']['package_id'], 'regional-match-demo')
    self.assertEqual(payload['captured_at_utc'], '2026-04-18T20:15:00Z')
    self.assertEqual(payload['device']['marketing_name'], 'Galaxy S21')
    self.assertEqual(payload['device']['registry_match_kind'], 'exact')
    self.assertIn('Galaxy S21', payload['package']['compatibility_summary'])
    self.assertTrue(payload['flash_plan']['ready_for_transport'])
    self.assertEqual(payload['flash_plan']['reboot_policy'], 'standard')
    self.assertIn('RECOVERY', payload['flash_plan']['partition_targets'])
    self.assertEqual(payload['pit']['state'], 'captured')
    self.assertEqual(payload['pit']['package_alignment'], 'matched')
    self.assertEqual(payload['pit']['observed_pit_fingerprint'], 'PIT-G991U-READY-001')
    self.assertGreaterEqual(len(payload['decision_trace']), 3)
    self.assertEqual(payload['transport']['state'], 'not_invoked')
    self.assertIn('live', payload['device'])
    self.assertEqual(payload['device']['live']['state'], 'unhydrated')

  def test_report_exports_live_detection_identity_when_present(self) -> None:
    session = build_demo_session('ready')
    live_trace = normalize_android_tools_result(
      build_adb_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='adb-ready',
        operation=AndroidToolsOperation.ADB_DEVICES,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          'List of devices attached',
          'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
        ),
      ),
    )
    live_detection = build_live_detection_session(live_trace)
    live_info_trace = normalize_android_tools_result(
      build_adb_device_info_command_plan(device_serial='R58N12345AB'),
      AndroidToolsProcessResult(
        fixture_name='adb-info-ready',
        operation=AndroidToolsOperation.ADB_GETPROP,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          '[ro.product.manufacturer]: [samsung]',
          '[ro.product.brand]: [samsung]',
          '[ro.build.version.release]: [14]',
          '[ro.build.version.security_patch]: [2026-04-05]',
          '[ro.bootloader]: [G991USQS9HYD1]',
        ),
      ),
    )
    session = replace(
      session,
      live_detection=apply_live_device_info_trace(live_detection, live_info_trace),
    )
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )

    report = build_session_evidence_report(
      session,
      scenario_name='Ready report with live detection',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      captured_at_utc='2026-04-18T20:16:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    markdown = render_session_evidence_markdown(report)

    self.assertEqual(payload['device']['live']['state'], 'detected')
    self.assertEqual(payload['device']['live']['source'], 'adb')
    self.assertTrue(payload['device']['live']['device_present'])
    self.assertEqual(payload['device']['live']['marketing_name'], 'Galaxy S21')
    self.assertEqual(payload['device']['live']['info_state'], 'captured')
    self.assertEqual(payload['device']['live']['android_version'], '14')
    self.assertIn('bounded_info_snapshot_ready', payload['device']['live']['capability_hints'])
    self.assertEqual(payload['pit']['state'], 'captured')
    self.assertIn('live detection state', markdown)
    self.assertIn('### PIT inspection', markdown)
    self.assertIn('live marketing name', markdown)
    self.assertIn('live android version', markdown)

  def test_report_exports_inspection_workflow_when_present(self) -> None:
    session = build_demo_session('ready')
    live_trace = normalize_android_tools_result(
      build_adb_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='adb-ready',
        operation=AndroidToolsOperation.ADB_DEVICES,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          'List of devices attached',
          'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
        ),
      ),
    )
    live_detection = build_live_detection_session(live_trace)
    live_info_trace = normalize_android_tools_result(
      build_adb_device_info_command_plan(device_serial='R58N12345AB'),
      AndroidToolsProcessResult(
        fixture_name='adb-info-ready',
        operation=AndroidToolsOperation.ADB_GETPROP,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          '[ro.product.manufacturer]: [samsung]',
          '[ro.product.brand]: [samsung]',
          '[ro.build.version.release]: [14]',
          '[ro.build.version.security_patch]: [2026-04-05]',
          '[ro.bootloader]: [G991USQS9HYD1]',
        ),
      ),
    )
    session = replace(
      session,
      live_detection=apply_live_device_info_trace(live_detection, live_info_trace),
    )
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    session = replace(
      session,
      inspection=build_inspection_workflow(
        session.live_detection,
        pit_inspection=pit_inspection,
        captured_at_utc='2026-04-20T22:35:00Z',
      ),
    )

    report = build_session_evidence_report(
      session,
      scenario_name='Ready report with inspection workflow',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      captured_at_utc='2026-04-20T22:35:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    markdown = render_session_evidence_markdown(report)

    self.assertEqual(payload['inspection']['posture'], 'ready')
    self.assertTrue(payload['inspection']['pit_ran'])
    self.assertTrue(payload['inspection']['evidence_ready'])
    self.assertIn('### Inspection workflow', markdown)
    self.assertIn('Inspect-only workflow captured', markdown)

  def test_failure_report_carries_recovery_guidance_into_markdown(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('failure')
    pit_inspection = build_demo_pit_inspection(
      'failure',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('failure'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-18T20:20:00Z',
    )

    markdown = render_session_evidence_markdown(report)
    self.assertEqual(report.outcome.outcome, 'failed')
    self.assertIn('Recovery guidance', markdown)
    self.assertIn('### Flash plan', markdown)
    self.assertIn('### PIT inspection', markdown)
    self.assertIn('### Transcript', markdown)
    self.assertIn('Stabilize the direct USB path', markdown)
    self.assertIn('manual no-reboot recovery handoff', markdown)
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
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name='Incomplete manifest review',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      captured_at_utc='2026-04-18T20:25:00Z',
    )

    self.assertFalse(report.package.contract_complete)
    self.assertFalse(report.flash_plan.ready_for_transport)
    self.assertEqual(report.preflight.gate, 'blocked')
    self.assertTrue(report.package.contract_issues)
    self.assertTrue(report.flash_plan.blocking_reasons)

  def test_adapter_backed_report_carries_transport_trace(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('happy')
    pit_inspection = build_demo_pit_inspection(
      'happy',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('happy'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-18T20:27:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    self.assertEqual(payload['transport']['adapter_name'], 'heimdall')
    self.assertEqual(payload['transport']['state'], 'completed')
    self.assertEqual(payload['transport']['normalized_event_count'], 2)
    self.assertTrue(payload['transcript']['preserved'])
    self.assertEqual(
      payload['transcript']['policy'],
      'preserve_bounded_transport_transcript',
    )
    self.assertTrue(payload['transcript']['reference_file_name'])

  def test_suspicious_review_report_exports_warning_tier_traits(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment(
      'ready',
      session=session,
      package_fixture_name='suspicious-review',
    )
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name='Suspicious review lane',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      captured_at_utc='2026-04-18T20:28:00Z',
    )

    payload = json.loads(serialize_session_evidence_json(report))
    markdown = render_session_evidence_markdown(report)
    self.assertEqual(payload['preflight']['gate'], 'ready')
    self.assertEqual(payload['package']['suspicious_warning_count'], 7)
    self.assertIn('test_keys', payload['package']['suspicious_indicator_ids'])
    self.assertEqual(payload['flash_plan']['suspicious_warning_count'], 7)
    self.assertTrue(payload['flash_plan']['operator_warnings'])
    self.assertIn('flash-plan warning', markdown)

  def test_writer_persists_markdown_report_to_disk(self) -> None:
    session = build_demo_session('blocked')
    package_assessment = build_demo_package_assessment('blocked', session=session)
    pit_inspection = build_demo_pit_inspection(
      'blocked',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('blocked'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
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
    self.assertIn('### Flash plan', contents)
    self.assertIn('### PIT inspection', contents)

  def test_writer_persists_transport_transcript_for_adapter_backed_report(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('failure')
    pit_inspection = build_demo_pit_inspection(
      'failure',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('failure'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-19T01:10:00Z',
    )

    with TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'failure_evidence.json'
      written_path = write_session_evidence_report(
        report,
        output_path,
        transport_trace=transport_trace,
      )
      payload = json.loads(written_path.read_text(encoding='utf-8'))
      transcript_path = Path(temp_dir) / payload['transcript']['reference_file_name']
      transcript_exists = transcript_path.exists()
      transcript_contents = transcript_path.read_text(encoding='utf-8')

    self.assertTrue(payload['transcript']['preserved'])
    self.assertTrue(transcript_exists)
    self.assertIn('Calamum Vulcan transport transcript', transcript_contents)
    self.assertIn('USB transfer timeout during partition write', transcript_contents)

  def test_transcript_reference_file_name_sanitizes_malicious_scenario_name(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('failure')
    pit_inspection = build_demo_pit_inspection(
      'failure',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=r'..\rogue\evidence:lane/../../still-bad',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-19T01:15:00Z',
    )

    reference_name = report.transcript.reference_file_name

    self.assertIsNotNone(reference_name)
    self.assertNotIn('..', reference_name)
    self.assertNotIn('/', reference_name)
    self.assertNotIn('\\', reference_name)
    self.assertNotIn(':', reference_name)

    with TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'evidence.json'
      write_session_evidence_report(
        report,
        output_path,
        transport_trace=transport_trace,
      )

      transcript_path = Path(temp_dir) / reference_name
      file_names = {path.name for path in Path(temp_dir).iterdir() if path.is_file()}
      transcript_exists = transcript_path.exists()

    self.assertTrue(transcript_exists)
    self.assertIn('evidence.json', file_names)
    self.assertIn(reference_name, file_names)

  def test_writer_sanitizes_malicious_transcript_reference_file_name(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('failure')
    pit_inspection = build_demo_pit_inspection(
      'failure',
      session=session,
      package_assessment=package_assessment,
    )
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('failure'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      transport_trace=transport_trace,
      captured_at_utc='2026-04-19T01:20:00Z',
    )
    report = replace(
      report,
      transcript=replace(
        report.transcript,
        reference_file_name=r'..\escape\rogue:transcript.log',
      ),
    )

    with TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'failure_evidence.json'
      write_session_evidence_report(
        report,
        output_path,
        transport_trace=transport_trace,
      )

      file_names = {path.name for path in Path(temp_dir).iterdir() if path.is_file()}

    self.assertIn('failure_evidence.json', file_names)
    self.assertIn('rogue-transcript.log', file_names)


if __name__ == '__main__':
  unittest.main()