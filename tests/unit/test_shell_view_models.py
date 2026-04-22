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
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_fastboot_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
from calamum_vulcan.app.view_models import LiveCompanionDeviceViewModel
from calamum_vulcan.app.view_models import PANEL_TITLES
from calamum_vulcan.app.view_models import build_shell_view_model
from calamum_vulcan.app.view_models import describe_shell
from calamum_vulcan.domain.live_device import LiveFallbackPosture
from calamum_vulcan.domain.live_device import apply_live_device_info_trace
from calamum_vulcan.domain.live_device import build_live_detection_session
from calamum_vulcan.domain.pit import PitDeviceAlignment
from calamum_vulcan.domain.pit import PitPackageAlignment
from calamum_vulcan.domain.preflight import PreflightGate
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.state import PlatformEvent
from calamum_vulcan.domain.state import SessionEventType
from calamum_vulcan.domain.state import SessionLaunchPath
from calamum_vulcan.domain.state import build_inspection_workflow
from calamum_vulcan.domain.state import replay_events
from calamum_vulcan.fixtures import happy_path_events
from calamum_vulcan.fixtures import package_first_events


def _actions_by_label(model):
  """Return the current control actions keyed by operator label."""

  return {action.label: action for action in model.control_actions}


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
    self.assertEqual(
      model.session_authority.selected_launch_path,
      SessionLaunchPath.BLOCKED,
    )
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
    actions = _actions_by_label(model)
    self.assertIn('Export evidence', actions)
    self.assertTrue(actions['Export evidence'].enabled)

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
    self.assertEqual(
      model.session_authority.selected_launch_path,
      SessionLaunchPath.STANDBY,
    )
    self.assertFalse(_actions_by_label(model)['Export evidence'].enabled)
    self.assertIn('enabled_actions=[Detect device]', describe_shell(model))

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

  def test_live_adb_overlay_promotes_phase_display_and_keeps_review_target_explicit(self) -> None:
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
    transport_metrics = {
      metric.label: metric.value for metric in model.panels[3].metrics
    }

    self.assertEqual(model.phase_label, 'ADB Device Detected')
    self.assertEqual(model.session_authority.live_phase_label, 'ADB Device Detected')
    self.assertEqual(pill_map['Device'].value, 'SM_A037U via ADB')
    self.assertEqual(pill_map['Device'].tone, 'success')
    self.assertEqual(pill_map['Phase'].value, 'ADB Device Detected')
    self.assertEqual(transport_metrics['Phase'], 'ADB Device Detected')
    self.assertIn(
      'reviewed target posture remains No Download-Mode Target',
      model.panels[0].summary,
    )
    self.assertTrue(
      any(
        'Reviewed target posture: No Download-Mode Target' in line
        for line in model.panels[0].detail_lines
      )
    )

  def test_live_heimdall_overlay_promotes_download_mode_phase_display(self) -> None:
    session = build_demo_session('no-device')
    live_device = LiveCompanionDeviceViewModel(
      backend='heimdall',
      serial='samsung-galaxy-lab-04',
      state='download',
      transport='download-mode',
      product_code='SM-G991U',
    )
    model = build_shell_view_model(
      session,
      scenario_name='Live Heimdall overlay',
      live_device=live_device,
    )

    pill_map = {pill.label: pill for pill in model.status_pills}

    self.assertEqual(model.phase_label, 'Download-Mode Device Detected')
    self.assertEqual(
      model.session_authority.live_phase_label,
      'Download-Mode Device Detected',
    )
    self.assertEqual(pill_map['Phase'].value, 'Download-Mode Device Detected')
    self.assertEqual(pill_map['Device'].value, 'SM-G991U via HEIMDALL')
    self.assertIn('via HEIMDALL', model.panels[0].summary)
    self.assertTrue(
      any(
        'Live companion backend: HEIMDALL' in line
        for line in model.panels[0].detail_lines
      )
    )

  def test_repo_owned_live_info_snapshot_surfaces_capability_and_guidance_lines(self) -> None:
    session = build_demo_session('no-device')
    live_detection = build_live_detection_session(
      normalize_android_tools_result(
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
    )
    live_detection = apply_live_device_info_trace(
      live_detection,
      normalize_android_tools_result(
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
      ),
    )

    model = build_shell_view_model(
      replace(session, live_detection=live_detection),
      scenario_name='Live info overlay',
      package_assessment=None,
    )

    self.assertIn('bounded read-side device info is now captured', model.panels[0].summary)
    self.assertTrue(
      any('Android version: 14' in line for line in model.panels[0].detail_lines)
    )
    self.assertTrue(
      any('Capability hint: bounded info snapshot ready' in line for line in model.panels[0].detail_lines)
    )
    self.assertTrue(
      any('Next step:' in line for line in model.panels[0].detail_lines)
    )

  def test_read_pit_action_and_evidence_panel_surface_bounded_pit_lane(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    live_detection = build_live_detection_session(
      normalize_android_tools_result(
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
    )
    live_detection = apply_live_device_info_trace(
      live_detection,
      normalize_android_tools_result(
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
      ),
    )
    session = replace(
      session,
      live_detection=live_detection,
      inspection=build_inspection_workflow(
        live_detection,
        pit_inspection=pit_inspection,
        captured_at_utc='2026-04-20T22:30:00Z',
      ),
    )

    model = build_shell_view_model(
      session,
      scenario_name='Inspect-only ready lane',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    actions = _actions_by_label(model)

    self.assertEqual(actions['Read PIT'].state.value, 'completed')
    self.assertFalse(actions['Read PIT'].enabled)
    self.assertEqual(model.session_report.inspection.posture, 'ready')
    self.assertTrue(
      any('Authority summary:' in line for line in model.panels[4].detail_lines)
    )
    self.assertIn('Inspect-only workflow captured', model.panels[4].summary)
    self.assertTrue(
      any('Inspection posture: ready' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('Inspection next action:' in line for line in model.panels[4].detail_lines)
    )

  def test_ready_destructive_session_enables_separated_execute_action(self) -> None:
    session = replay_events(happy_path_events()[:-2])
    package_assessment = build_demo_package_assessment(
      'happy',
      session=session,
      package_fixture_name='matched',
    )
    pit_inspection = build_demo_pit_inspection(
      'happy',
      session=session,
      package_assessment=package_assessment,
    )
    model = build_shell_view_model(
      session,
      scenario_name='Ready destructive lane',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    execute_action = _actions_by_label(model)['Execute flash plan']

    self.assertTrue(execute_action.enabled)
    self.assertEqual(execute_action.emphasis, 'danger')
    self.assertEqual(
      model.session_authority.selected_launch_path,
      SessionLaunchPath.SAFE_PATH_CANDIDATE,
    )
    self.assertEqual(model.phase_label, 'Ready to Execute')
    self.assertEqual(model.gate_label, 'Gate Ready')
    self.assertTrue(
      any('Launch path: Safe-Path Candidate' in line for line in model.panels[3].detail_lines)
    )
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
      any('Observed PIT fingerprint:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Report id:' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('PIT posture:' in line for line in model.panels[4].detail_lines)
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
    self.assertFalse(_actions_by_label(model)['Execute flash plan'].enabled)
    self.assertTrue(
      any(
        'Battery level is low enough to justify operator caution.' in line
        for line in model.panels[1].detail_lines
      )
    )
    self.assertTrue(_actions_by_label(model)['Export evidence'].enabled)

  def test_resume_shell_surfaces_contextual_continue_action(self) -> None:
    session = replay_events(
      happy_path_events()[:-1] + [
        PlatformEvent(
          SessionEventType.EXECUTION_PAUSED,
          {'notes': ('Manual recovery boot required',)},
        )
      ]
    )
    package_assessment = build_demo_package_assessment('resume', session=session)
    pit_inspection = build_demo_pit_inspection(
      'resume',
      session=session,
      package_assessment=package_assessment,
    )
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('resume'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      pit_required_for_safe_path=True,
    )

    action_map = _actions_by_label(model)
    visible_labels = tuple(
      action.label for action in model.control_actions if action.visible
    )

    self.assertIn('Continue after recovery', visible_labels)
    self.assertNotIn('Resume workflow', visible_labels)
    self.assertEqual(action_map['Continue after recovery'].state.value, 'next')
    self.assertTrue(action_map['Continue after recovery'].enabled)
    self.assertEqual(model.phase_label, 'Resume Needed')
    self.assertIn('[EVENT] execution_paused', model.log_lines)
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
    self.assertFalse(_actions_by_label(model)['Execute flash plan'].enabled)
    self.assertTrue(
      any('Contract issue:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Flash plan blocker:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Recovery guidance:' in line for line in model.panels[4].detail_lines)
    )

  def test_pit_mismatch_surfaces_in_package_and_evidence_panels(self) -> None:
    session = build_demo_session('blocked')
    package_assessment = build_demo_package_assessment('blocked', session=session)
    pit_inspection = build_demo_pit_inspection(
      'blocked',
      session=session,
      package_assessment=package_assessment,
    )

    model = build_shell_view_model(
      session,
      scenario_name='Blocked PIT review lane',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    self.assertEqual(model.panels[2].tone, 'danger')
    self.assertTrue(
      any('PIT/package alignment: mismatched' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Observed PIT fingerprint:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('PIT posture:' in line for line in model.panels[4].detail_lines)
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
      any('Safe-path governance:' in line for line in model.panels[3].detail_lines)
    )
    self.assertTrue(
      any('[TRANSPORT] flash_package state=failed exit=1' in line for line in model.log_lines)
    )
    self.assertTrue(
      any('[SAFE-PATH] governance=platform_supervised' in line for line in model.log_lines)
    )
    self.assertTrue(_actions_by_label(model)['Export evidence'].enabled)

  def test_fastboot_fallback_identity_surfaces_path_label_and_confidence(self) -> None:
    session = build_demo_session('no-device')
    live_detection = build_live_detection_session(
      normalize_android_tools_result(
        build_fastboot_detect_command_plan(),
        AndroidToolsProcessResult(
          fixture_name='fastboot-ready',
          operation=AndroidToolsOperation.FASTBOOT_DEVICES,
          backend=AndroidToolsBackend.FASTBOOT,
          exit_code=0,
          stdout_lines=('FASTBOOT123\tfastboot',),
        ),
      ),
      fallback_posture=LiveFallbackPosture.ENGAGED,
      fallback_reason='ADB did not establish a live device; fastboot captured the active companion.',
      source_labels=('adb', 'fastboot'),
    )

    model = build_shell_view_model(
      replace(session, live_detection=live_detection),
      scenario_name='Fastboot fallback review',
    )

    self.assertEqual(
      model.session_authority.selected_launch_path,
      SessionLaunchPath.FALLBACK_REVIEW,
    )
    self.assertTrue(
      any('Live path: Fastboot Fallback Session' in line for line in model.panels[0].detail_lines)
    )
    self.assertTrue(
      any('Identity confidence: serial only' in line for line in model.panels[0].detail_lines)
    )
    self.assertTrue(
      any('Live path identity: Fastboot Fallback Session' in line for line in model.panels[3].detail_lines)
    )
    self.assertTrue(
      any('Live path identity: Fastboot Fallback Session / fallback / serial_only' in line for line in model.panels[4].detail_lines)
    )

  def test_pit_device_mismatch_blocks_safe_path_shell_and_surfaces_alignment(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = replace(
      build_demo_pit_inspection(
        'ready',
        session=session,
        package_assessment=package_assessment,
      ),
      device_alignment=PitDeviceAlignment.MISMATCHED,
      observed_product_code='SM-G996U',
      canonical_product_code='SM-G996U',
      marketing_name='Galaxy S21+',
    )

    model = build_shell_view_model(
      session,
      scenario_name='PIT device mismatch review',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    self.assertEqual(model.gate_label, 'Gate Blocked')
    self.assertEqual(model.session_authority.selected_launch_path, SessionLaunchPath.BLOCKED)
    self.assertTrue(
      any('PIT/device alignment: mismatched' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any(
        'Observed PIT product code does not match the current session device identity.' in line
        for line in model.panels[3].detail_lines
      )
    )
    self.assertTrue(
      any('PIT/device alignment: mismatched' in line for line in model.panels[4].detail_lines)
    )

  def test_missing_pit_fingerprint_comparison_narrows_ready_shell(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = replace(
      build_demo_pit_inspection(
        'ready',
        session=session,
        package_assessment=package_assessment,
      ),
      package_alignment=PitPackageAlignment.MISSING_OBSERVED,
      observed_pit_fingerprint=None,
    )

    model = build_shell_view_model(
      session,
      scenario_name='Narrowed PIT fingerprint review',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    self.assertEqual(model.gate_label, 'Gate Ready')
    self.assertEqual(
      model.session_authority.selected_launch_path,
      SessionLaunchPath.SAFE_PATH_CANDIDATE,
    )
    self.assertEqual(model.session_authority.readiness.value, 'narrowed')
    self.assertEqual(model.panels[2].tone, 'warning')
    self.assertIn('usable PIT fingerprint', model.session_authority.block_reason)

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
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    model = build_shell_view_model(
      session,
      scenario_name='Suspicious review lane',
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    self.assertIsNotNone(pit_inspection)
    self.assertEqual(pit_inspection.reviewed_pit_fingerprint, 'PIT-G991U-SUSPICIOUS-001')
    self.assertEqual(pit_inspection.package_alignment.value, 'matched')
    self.assertEqual(model.gate_label, 'Gate Ready')
    self.assertEqual(model.panels[2].tone, 'warning')
    self.assertTrue(_actions_by_label(model)['Execute flash plan'].enabled)
    self.assertTrue(
      any('Suspicious trait:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Suspicious traits:' in line for line in model.panels[4].detail_lines)
    )
    self.assertTrue(
      any('Flash plan warning:' in line for line in model.panels[4].detail_lines)
    )

  def test_missing_pit_truth_keeps_safe_path_pinned_on_read_pit(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    live_device = LiveCompanionDeviceViewModel(
      backend='heimdall',
      serial='samsung-galaxy-lab-04',
      state='download',
      transport='download-mode',
      product_code='SM-G991U',
    )

    model = build_shell_view_model(
      session,
      scenario_name='Missing PIT safe-path review',
      package_assessment=package_assessment,
      pit_inspection=None,
      live_device=live_device,
      pit_required_for_safe_path=True,
    )

    actions = _actions_by_label(model)

    self.assertEqual(model.gate_label, 'Gate Blocked')
    self.assertEqual(actions['Read PIT'].state.value, 'next')
    self.assertFalse(actions['Execute flash plan'].enabled)
    self.assertEqual(actions['Export evidence'].state.value, 'available')
    self.assertIn(
      'Run Read PIT before continuing the bounded safe-path workflow.',
      model.session_authority.block_reason,
    )


if __name__ == '__main__':
  unittest.main()
