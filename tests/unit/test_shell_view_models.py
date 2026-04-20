"""Unit tests for the Calamum Vulcan FS-03 shell view models."""

from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import available_scenarios
from calamum_vulcan.app.demo import available_transport_sources
from calamum_vulcan.app.demo import build_demo_adapter_session
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.app.view_models import PANEL_TITLES
from calamum_vulcan.app.view_models import LiveCompanionDeviceViewModel
from calamum_vulcan.app.view_models import build_shell_view_model
from calamum_vulcan.app.view_models import describe_shell
from calamum_vulcan.domain.preflight import PreflightGate
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.state import replay_events
from calamum_vulcan.fixtures import load_package_manifest_fixture
from calamum_vulcan.fixtures import happy_path_events
from calamum_vulcan.fixtures import package_first_events


class ShellViewModelTests(unittest.TestCase):
  """Prove the FS-03 shell contract before Qt runtime concerns begin."""

  def test_available_scenarios_cover_the_primary_shell_states(self) -> None:
    self.assertEqual(
      available_scenarios(),
      ('no-device', 'ready', 'blocked', 'happy', 'resume', 'failure', 'package-first'),
    )
    self.assertEqual(
      available_transport_sources(),
      ('state-fixture', 'heimdall-adapter'),
    )

  def test_panel_map_is_stable_for_blocked_review(self) -> None:
    session = build_demo_session('blocked')
    package_assessment = build_demo_package_assessment('blocked', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('blocked'),
      package_assessment=package_assessment,
    )

    self.assertEqual(tuple(panel.title for panel in model.panels), PANEL_TITLES)
    self.assertEqual(model.phase_label, 'Validation Blocked')
    self.assertEqual(model.gate_label, 'Gate Blocked')
    self.assertTrue(
      any(
        'Package compatibility does not include Galaxy S21 (SM-G991U).' in line
        for line in model.panels[1].detail_lines
      )
    )
    self.assertTrue(
      any('Galaxy S21' in line for line in model.panels[0].detail_lines)
    )
    self.assertTrue(
      any('SM-G996U' in line for line in model.panels[2].detail_lines)
    )
    self.assertEqual(model.control_actions[5].label, 'Export evidence')
    self.assertTrue(model.control_actions[5].enabled)

  def test_no_device_shell_keeps_panel_map_and_blocks_export(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      package_assessment=None,
    )

    self.assertEqual(tuple(panel.title for panel in model.panels), PANEL_TITLES)
    self.assertEqual(model.phase_label, 'No Device')
    self.assertEqual(model.gate_label, 'Gate Blocked')
    self.assertFalse(model.control_actions[5].enabled)
    self.assertIn('No-device control deck', describe_shell(model))

  def test_boot_unhydrated_shell_starts_in_standby_with_blank_fields(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name='Operational startup shell',
      package_assessment=None,
      boot_unhydrated=True,
    )

    pill_map = {pill.label: pill.value for pill in model.status_pills}
    package_metrics = {metric.label: metric.value for metric in model.panels[2].metrics}

    self.assertEqual(model.phase_label, 'No Device')
    self.assertEqual(model.gate_label, 'Standby')
    self.assertEqual(pill_map['Device'], '--')
    self.assertEqual(pill_map['Package'], '--')
    self.assertEqual(pill_map['Risk'], '--')
    self.assertIn('intentionally blank at boot', model.panels[0].summary)
    self.assertIn('stay blank at boot', model.panels[2].summary)
    self.assertEqual(package_metrics['Loaded'], '--')
    self.assertEqual(package_metrics['Compatibility'], '--')

  def test_device_surface_cleared_blanks_only_live_device_surfaces(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name='Device cleared after disconnect',
      package_assessment=package_assessment,
      device_surface_cleared=True,
    )

    pill_map = {pill.label: pill.value for pill in model.status_pills}
    package_metrics = {metric.label: metric.value for metric in model.panels[2].metrics}

    self.assertEqual(pill_map['Device'], '--')
    self.assertEqual(pill_map['Package'], package_assessment.display_package_id)
    self.assertIn('No live device is currently detected.', model.panels[0].summary)
    self.assertEqual(package_metrics['Loaded'], 'yes')

  def test_live_adb_overlay_keeps_review_phase_but_marks_device_pill_ready(self) -> None:
    session = build_demo_session('no-device')
    live_device = LiveCompanionDeviceViewModel(
      backend='adb',
      serial='R58N12345AB',
      state='device',
      transport='usb',
      product_code='SM_A037U',
      model_name='SM_A037U',
      device_name='a03su',
    )
    model = build_shell_view_model(
      session,
      scenario_name='Live ADB overlay',
      live_device=live_device,
    )

    pill_map = {pill.label: pill for pill in model.status_pills}

    self.assertEqual(model.phase_label, 'No Device')
    self.assertEqual(pill_map['Device'].value, 'SM_A037U via ADB')
    self.assertEqual(pill_map['Device'].tone, 'success')
    self.assertIn('reviewed session remains No Device', model.panels[0].summary)

  def test_ready_destructive_session_enables_separated_execute_action(self) -> None:
    session = replay_events(happy_path_events()[:-2])
    package_assessment = build_demo_package_assessment(
      'happy',
      session=session,
      package_fixture_name='matched',
    )
    model = build_shell_view_model(
      session,
      scenario_name='Ready destructive lane',
      package_assessment=package_assessment,
    )

    execute_action = model.control_actions[3]
    self.assertTrue(execute_action.enabled)
    self.assertEqual(execute_action.emphasis, 'danger')
    self.assertEqual(model.phase_label, 'Ready to Execute')
    self.assertEqual(model.gate_label, 'Gate Ready')
    self.assertTrue(
      any('RECOVERY <- recovery.img' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Flash plan id:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Recovery plan:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Report id:' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('Flash plan posture:' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('Export targets:' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('Galaxy S10' in line for line in model.panels[2].detail_lines)
    )

  def test_warning_gate_keeps_execute_action_disabled(self) -> None:
    session = replay_events(package_first_events()[:-1])
    package_assessment = build_demo_package_assessment(
      'package-first',
      session=session,
    )
    report = evaluate_preflight(
      PreflightInput.from_session(
        session,
        battery_level=22,
        **{
          'package_selected': True,
          'package_complete': package_assessment.contract_complete,
          'checksums_present': package_assessment.checksum_coverage_present,
          'product_code_match': package_assessment.matches_detected_product_code,
          'destructive_operation': False,
        }
      )
    )
    model = build_shell_view_model(
      session,
      scenario_name='Warning review lane',
      preflight_report=report,
      package_assessment=package_assessment,
    )

    self.assertEqual(report.gate, PreflightGate.WARN)
    self.assertEqual(model.gate_label, 'Gate Warning')
    self.assertFalse(model.control_actions[3].enabled)
    self.assertTrue(
      any(
        'Battery level is low enough to justify operator caution.' in line
        for line in model.panels[1].detail_lines
      )
    )
    self.assertTrue(model.control_actions[5].enabled)

  def test_resume_shell_surfaces_resume_action(self) -> None:
    session = build_demo_session('resume')
    package_assessment = build_demo_package_assessment('resume', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('resume'),
      package_assessment=package_assessment,
    )

    self.assertEqual(model.phase_label, 'Completed')
    self.assertIn('Resume workflow', tuple(
      action.label for action in model.control_actions
    ))
    self.assertIn('[EVENT] execution_completed', model.log_lines)
    self.assertTrue(
      any('[PACKAGE-CTX] matched' in line for line in model.log_lines)
    )
    self.assertTrue(
      any('[EVIDENCE]' in line for line in model.log_lines)
    )

  def test_describe_shell_summarizes_layout_and_enabled_actions(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )
    summary = describe_shell(model)

    self.assertIn('Device Identity', summary)
    self.assertIn('Execute flash plan', summary)
    self.assertIn('Ready to Execute', summary)
    self.assertIn('Gate Ready', summary)

  def test_incomplete_package_fixture_surfaces_contract_issues(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment(
      'ready',
      session=session,
      package_fixture_name='incomplete',
    )
    model = build_shell_view_model(
      session,
      scenario_name='Incomplete manifest review',
      package_assessment=package_assessment,
    )

    self.assertEqual(model.gate_label, 'Gate Blocked')
    self.assertFalse(model.control_actions[3].enabled)
    self.assertTrue(
      any('Contract issue:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Flash plan blocker:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Recovery guidance:' in line for line in model.panels[4].detail_lines)
    )

  def test_adapter_backed_failure_surfaces_transport_trace(self) -> None:
    session, package_assessment, transport_trace = build_demo_adapter_session('failure')
    model = build_shell_view_model(
      session,
      scenario_name='Adapter-backed transport failure',
      package_assessment=package_assessment,
      transport_trace=transport_trace,
    )

    self.assertEqual(model.phase_label, 'Failed')
    self.assertTrue(
      any('Capability: flash_package' in line for line in model.panels[3].detail_lines)
    )
    self.assertTrue(
      any('[TRANSPORT] flash_package state=failed exit=1' in line for line in model.log_lines)
    )
    self.assertTrue(model.control_actions[5].enabled)

  def test_alias_product_code_is_resolved_in_the_device_panel(self) -> None:
    session = replace(build_demo_session('ready'), product_code='g991u')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name='Alias registry review',
      package_assessment=package_assessment,
    )

    self.assertEqual(model.gate_label, 'Gate Ready')
    self.assertTrue(
      any('Registry match: alias' in line for line in model.panels[0].detail_lines)
    )
    self.assertTrue(
      any('SM-G991U' in line or 'Galaxy S21' in line for line in model.panels[0].detail_lines)
    )

  def test_suspicious_review_surfaces_warning_details_without_hard_block(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment(
      'ready',
      session=session,
      package_fixture_name='suspicious-review',
    )
    model = build_shell_view_model(
      session,
      scenario_name='Suspicious review lane',
      package_assessment=package_assessment,
    )

    self.assertEqual(model.gate_label, 'Gate Ready')
    self.assertEqual(model.panels[2].tone, 'warning')
    self.assertTrue(model.control_actions[3].enabled)
    self.assertTrue(
      any('Suspicious trait:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Suspicious traits:' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('Flash plan warning:' in line for line in model.panels[4].detail_lines)
    )


if __name__ == '__main__':
  unittest.main()