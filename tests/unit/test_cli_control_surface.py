"""CLI tests for the Calamum Vulcan live companion control surface."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import runpy
import sys
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

PROJECT_VERSION = tomllib.loads(
  (FINAL_EXAM_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
)['project']['version']

from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_fastboot_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
from calamum_vulcan.adapters.heimdall import build_print_pit_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.app.__main__ import gui_main
from calamum_vulcan.app.__main__ import main
from calamum_vulcan.app.__main__ import _render_control_trace
from calamum_vulcan.app.__main__ import _render_codesentinel_status_block
from calamum_vulcan.domain.live_device import LiveFallbackPosture
from calamum_vulcan.domain.live_device import apply_live_device_info_trace
from calamum_vulcan.domain.live_device import build_live_detection_session
from calamum_vulcan.fixtures import load_heimdall_pit_fixture
from calamum_vulcan.usb import USBDeviceDescriptor
from calamum_vulcan.usb import USBProbeResult


def _ready_adb_info_trace():
  return normalize_android_tools_result(
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


def _ready_print_pit_trace():
  return normalize_heimdall_result(
    build_print_pit_command_plan(),
    load_heimdall_pit_fixture('pit-print-ready-g991u'),
  )


def _no_device_adb_detection_trace():
  return normalize_android_tools_result(
    build_adb_detect_command_plan(),
    AndroidToolsProcessResult(
      fixture_name='adb-none',
      operation=AndroidToolsOperation.ADB_DEVICES,
      backend=AndroidToolsBackend.ADB,
      exit_code=0,
      stdout_lines=('List of devices attached',),
    ),
  )


def _no_device_fastboot_detection_trace():
  return normalize_android_tools_result(
    build_fastboot_detect_command_plan(),
    AndroidToolsProcessResult(
      fixture_name='fastboot-none',
      operation=AndroidToolsOperation.FASTBOOT_DEVICES,
      backend=AndroidToolsBackend.FASTBOOT,
      exit_code=0,
      stdout_lines=(),
    ),
  )


def _ready_usb_probe_result():
  return USBProbeResult(
    state='detected',
    summary='Native USB scan detected a Samsung download-mode device.',
    devices=(
      USBDeviceDescriptor(
        vendor_id=0x04E8,
        product_id=0x685D,
        bus=1,
        address=5,
        serial_number='usb-g991u-lab-01',
        manufacturer='Samsung',
        product_name='Samsung Galaxy S21 (SM-G991U)',
        product_code='SM-G991U',
      ),
    ),
    notes=('Native USB backend resolved from bundled libusb.',),
  )


def _attention_usb_probe_result():
  return USBProbeResult(
    state='attention',
    summary=(
      'Native USB scan detected a Samsung download-mode device, but richer '
      'USB identity strings still need operator attention.'
    ),
    devices=(
      USBDeviceDescriptor(
        vendor_id=0x04E8,
        product_id=0x685D,
        bus=1,
        address=5,
        serial_number='usb-g991u-lab-02',
        manufacturer='Samsung',
        product_name='Samsung Galaxy S21 (SM-G991U)',
        product_code='SM-G991U',
        command_ready=False,
      ),
    ),
    notes=('Native USB backend resolved from bundled libusb.',),
  )


def _failed_usb_probe_result():
  return USBProbeResult(
    state='failed',
    summary='Native USB detection failed before a trustworthy Samsung download-mode identity could be built.',
    notes=(
      'Bundled libusb backend could not be resolved on Windows.',
    ),
    remediation_command='powershell.exe -NoProfile -ExecutionPolicy Bypass',
  )


class CliControlSurfaceTests(unittest.TestCase):
  """Prove the live companion CLI stays bounded and inspectable."""

  def test_version_flags_emit_application_version(self) -> None:
    for flag in ('-v', '--version'):
      with self.subTest(flag=flag):
        stream = io.StringIO()

        with redirect_stdout(stream), self.assertRaises(SystemExit) as exit_signal:
          main([flag])

        output = stream.getvalue()
        self.assertEqual(exit_signal.exception.code, 0)
        self.assertIn('Calamum Vulcan {version}'.format(version=PROJECT_VERSION), output)

  def test_describe_only_adb_download_reboot_surfaces_vendor_specific_note(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--adb-reboot',
          'download',
          '--device-serial',
          'R58N12345AB',
          '--describe-only',
        ]
      )

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('adb -s R58N12345AB reboot download', output)
    self.assertIn('vendor_specific="yes"', output)
    self.assertIn('vendor-specific', output)

  def test_describe_only_adb_detect_surfaces_live_command_plan(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(['--adb-detect', '--describe-only'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('adb devices -l', output)
    self.assertIn('detect_adb_devices', output)

  def test_render_control_trace_includes_repo_owned_live_detection_summary(self) -> None:
    trace = normalize_android_tools_result(
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

    live_detection = apply_live_device_info_trace(
      build_live_detection_session(trace),
      _ready_adb_info_trace(),
    )

    output = _render_control_trace(trace, 'text', live_detection=live_detection)

    self.assertIn('live_detection state="detected"', output)
    self.assertIn('source="adb"', output)
    self.assertIn('live_identity serial="R58N12345AB"', output)
    self.assertIn('marketing_name="Galaxy S21"', output)
    self.assertIn('live_info posture="captured"', output)
    self.assertIn('live_capability="bounded_info_snapshot_ready"', output)
    self.assertIn('live_path ownership="native"', output)

  def test_render_control_trace_surfaces_fastboot_fallback_path_identity(self) -> None:
    trace = normalize_android_tools_result(
      build_fastboot_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='fastboot-ready',
        operation=AndroidToolsOperation.FASTBOOT_DEVICES,
        backend=AndroidToolsBackend.FASTBOOT,
        exit_code=0,
        stdout_lines=('FASTBOOT123\tfastboot',),
      ),
    )

    live_detection = build_live_detection_session(
      trace,
      fallback_posture=LiveFallbackPosture.ENGAGED,
      fallback_reason='ADB did not establish a live device; fastboot captured the active companion.',
      source_labels=('adb', 'fastboot'),
    )

    output = _render_control_trace(trace, 'text', live_detection=live_detection)

    self.assertIn('live_path ownership="fallback"', output)
    self.assertIn('path_label="Fastboot Fallback Session"', output)
    self.assertIn('identity_confidence="serial_only"', output)
    self.assertIn('live_path_guidance="Treat the current fastboot lane as serial-only identity until richer product truth is available."', output)

  def test_adb_detect_runs_bounded_info_enrichment_before_rendering_trace(self) -> None:
    stream = io.StringIO()

    with patch(
      'calamum_vulcan.app.__main__.execute_android_tools_command',
      side_effect=(
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
        ),
        _ready_adb_info_trace(),
      ),
    ) as mocked_execute:
      with redirect_stdout(stream):
        exit_code = main(['--adb-detect'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertEqual(mocked_execute.call_count, 2)
    self.assertIn('live_info posture="captured"', output)
    self.assertIn('live_guidance=', output)

  def test_inspect_device_runs_read_side_lane_without_write_ready_theater(self) -> None:
    stream = io.StringIO()

    with patch(
      'calamum_vulcan.app.__main__.execute_android_tools_command',
      side_effect=(
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
        ),
        _ready_adb_info_trace(),
      ),
    ) as mocked_android, patch(
      'calamum_vulcan.app.__main__.execute_heimdall_command',
      return_value=_ready_print_pit_trace(),
    ) as mocked_heimdall:
      with redirect_stdout(stream):
        exit_code = main(['--inspect-device'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertEqual(mocked_android.call_count, 2)
    mocked_heimdall.assert_called_once()
    self.assertIn('inspection_result posture="ready"', output)
    self.assertIn('write_ready="no"', output)
    self.assertIn('inspection_boundary=', output)
    self.assertIn('inspection_pit state="captured"', output)

  def test_inspect_device_can_fall_through_to_native_usb_download_mode_detection(self) -> None:
    stream = io.StringIO()

    with patch(
      'calamum_vulcan.app.__main__.execute_android_tools_command',
      side_effect=(
        _no_device_adb_detection_trace(),
        _no_device_fastboot_detection_trace(),
      ),
    ) as mocked_android, patch(
      'calamum_vulcan.app.__main__.VulcanUSBScanner.probe_download_mode_devices',
      return_value=_ready_usb_probe_result(),
    ) as mocked_usb, patch(
      'calamum_vulcan.app.__main__.execute_heimdall_command',
      return_value=_ready_print_pit_trace(),
    ) as mocked_heimdall:
      with redirect_stdout(stream):
        exit_code = main(['--inspect-device'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertEqual(mocked_android.call_count, 2)
    mocked_usb.assert_called_once()
    mocked_heimdall.assert_called_once()
    self.assertIn('inspection_live state="detected" source="usb"', output)
    self.assertIn('inspection_live state="detected" source="usb" info_state="unavailable"', output)
    self.assertIn('inspection_pit state="captured"', output)
    self.assertIn('SM-G991U', output)

  def test_inspect_device_preserves_native_usb_attention_state(self) -> None:
    stream = io.StringIO()

    with patch(
      'calamum_vulcan.app.__main__.execute_android_tools_command',
      side_effect=(
        _no_device_adb_detection_trace(),
        _no_device_fastboot_detection_trace(),
      ),
    ) as mocked_android, patch(
      'calamum_vulcan.app.__main__.VulcanUSBScanner.probe_download_mode_devices',
      return_value=_attention_usb_probe_result(),
    ) as mocked_usb, patch(
      'calamum_vulcan.app.__main__.execute_heimdall_command',
      return_value=_ready_print_pit_trace(),
    ) as mocked_heimdall:
      with redirect_stdout(stream):
        exit_code = main(['--inspect-device'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertEqual(mocked_android.call_count, 2)
    mocked_usb.assert_called_once()
    mocked_heimdall.assert_called_once()
    self.assertIn('inspection_live state="attention" source="usb"', output)
    self.assertIn('inspection_pit state="captured"', output)

  def test_inspect_device_surfaces_native_usb_failure_honestly(self) -> None:
    stream = io.StringIO()

    with patch(
      'calamum_vulcan.app.__main__.execute_android_tools_command',
      side_effect=(
        _no_device_adb_detection_trace(),
        _no_device_fastboot_detection_trace(),
      ),
    ) as mocked_android, patch(
      'calamum_vulcan.app.__main__.VulcanUSBScanner.probe_download_mode_devices',
      return_value=_failed_usb_probe_result(),
    ) as mocked_usb, patch(
      'calamum_vulcan.app.__main__.execute_heimdall_command',
      return_value=_ready_print_pit_trace(),
    ) as mocked_heimdall:
      with redirect_stdout(stream):
        exit_code = main(['--inspect-device'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertEqual(mocked_android.call_count, 2)
    mocked_usb.assert_called_once()
    mocked_heimdall.assert_called_once()
    self.assertIn('inspection_live state="failed" source="usb"', output)
    self.assertIn('inspection_pit state="captured"', output)

  def test_inspect_device_can_export_json_evidence_with_inspection_block(self) -> None:
    stream = io.StringIO()

    with tempfile.TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'inspection-evidence.json'

      with patch(
        'calamum_vulcan.app.__main__.execute_android_tools_command',
        side_effect=(
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
          ),
          _ready_adb_info_trace(),
        ),
      ), patch(
        'calamum_vulcan.app.__main__.execute_heimdall_command',
        return_value=_ready_print_pit_trace(),
      ):
        with redirect_stdout(stream):
          exit_code = main(
            [
              '--inspect-device',
              '--evidence-output',
              str(output_path),
              '--evidence-format',
              'json',
            ]
          )

      payload = json.loads(output_path.read_text(encoding='utf-8'))
      self.assertEqual(exit_code, 0)
      self.assertTrue(output_path.exists())
      self.assertEqual(payload['inspection']['posture'], 'ready')
      self.assertTrue(payload['inspection']['read_side_only'])
      self.assertTrue(payload['inspection']['pit_ran'])
      self.assertTrue(payload['outcome']['export_ready'])

  def test_execute_flash_plan_runs_platform_supervised_safe_path_lane(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--execute-flash-plan',
          '--transport-source', 'heimdall-adapter',
          '--scenario', 'ready',
        ]
      )

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('safe_path_result execution_allowed="yes"', output)
    self.assertIn('ownership="delegated"', output)
    self.assertIn('transport_state="completed"', output)
    self.assertIn('safe_path_boundary=', output)
    self.assertIn('safe_path_command="heimdall flash', output)

  def test_execute_flash_plan_reports_blocked_lane_without_transport(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--execute-flash-plan',
          '--transport-source', 'heimdall-adapter',
          '--scenario', 'blocked',
        ]
      )

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('safe_path_result execution_allowed="no"', output)
    self.assertIn('transport_state="not_invoked"', output)
    self.assertIn('safe_path_rejected=', output)

  def test_execute_flash_plan_rejects_state_fixture_transport_source(self) -> None:
    with self.assertRaises(SystemExit) as exit_signal:
      main(['--execute-flash-plan'])

    self.assertIn('requires --transport-source heimdall-adapter', str(exit_signal.exception))

  def test_reserved_integrated_runtime_transport_source_is_rejected_honestly(self) -> None:
    with self.assertRaises(SystemExit) as exit_signal:
      main(['--transport-source', 'integrated-runtime', '--describe-only'])

    self.assertIn('reserved for the Calamum-owned runtime', str(exit_signal.exception))

  def test_execute_flash_plan_can_render_json_result(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--execute-flash-plan',
          '--transport-source', 'heimdall-adapter',
          '--scenario', 'ready',
          '--control-format', 'json',
        ]
      )

    payload = json.loads(stream.getvalue())
    self.assertEqual(exit_code, 0)
    self.assertTrue(payload['execution_allowed'])
    self.assertEqual(payload['authority']['ownership'], 'delegated')
    self.assertEqual(payload['transport']['state'], 'completed')

  def test_read_side_close_bundle_serializes_from_cli(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--integration-suite', 'read-side-close',
          '--suite-format', 'json',
          '--captured-at-utc', '2026-04-20T23:20:00Z',
        ]
      )

    payload = json.loads(stream.getvalue())
    scenario_map = {scenario['scenario_id']: scenario for scenario in payload['scenarios']}

    self.assertEqual(exit_code, 0)
    self.assertEqual(payload['suite_name'], 'read-side-close')
    self.assertEqual(payload['release_version'], '0.3.0')
    self.assertEqual(scenario_map['inspect-only-ready-review']['inspection_posture'], 'ready')
    self.assertEqual(scenario_map['fastboot-fallback-review']['live_source'], 'fastboot')
    self.assertEqual(
      scenario_map['fallback-exhausted-review']['inspection_posture'],
      'failed',
    )

  def test_safe_path_close_bundle_serializes_from_cli(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--integration-suite', 'safe-path-close',
          '--suite-format', 'json',
          '--captured-at-utc', '2026-04-21T23:20:00Z',
        ]
      )

    payload = json.loads(stream.getvalue())
    scenario_map = {scenario['scenario_id']: scenario for scenario in payload['scenarios']}

    self.assertEqual(exit_code, 0)
    self.assertEqual(payload['suite_name'], 'safe-path-close')
    self.assertEqual(payload['release_version'], '0.4.0')
    self.assertEqual(scenario_map['read-pit-required-review']['gate_label'], 'Gate Blocked')
    self.assertEqual(scenario_map['safe-path-ready-review']['live_source'], 'usb')
    self.assertEqual(
      dict(scenario_map['safe-path-ready-review']['action_states'])['Execute flash plan'],
      'next',
    )
    self.assertEqual(
      dict(scenario_map['safe-path-runtime-complete']['action_states'])['Export evidence'],
      'next',
    )

  def test_gui_main_survives_missing_console_streams(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      log_path = Path(temp_dir) / 'gui_startup.log'
      with patch('calamum_vulcan.app.__main__.GUI_STARTUP_LOG_PATH', log_path):
        with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
          exit_code = gui_main(['--scenario', 'ready', '--describe-only'])

      self.assertEqual(exit_code, 0)
      self.assertTrue(log_path.exists())
      self.assertIn('phase="Ready to Execute"', log_path.read_text(encoding='utf-8'))

  def test_gui_main_surfaces_help_and_version_when_console_missing(self) -> None:
    for flag, expected_title, expected_text in (
      ('-h', 'help', 'usage:'),
      ('--version', 'version', 'Calamum Vulcan {version}'.format(version=PROJECT_VERSION)),
    ):
      with self.subTest(flag=flag):
        with tempfile.TemporaryDirectory() as temp_dir:
          log_path = Path(temp_dir) / 'gui_startup.log'
          gui_messages: list[tuple[str, str]] = []

          def _capture_message(title: str, message: str) -> None:
            gui_messages.append((title, message))

          with patch('calamum_vulcan.app.__main__.GUI_STARTUP_LOG_PATH', log_path):
            with patch(
              'calamum_vulcan.app.__main__._show_gui_launch_information',
              side_effect=_capture_message,
            ):
              with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
                exit_code = gui_main([flag])

          self.assertEqual(exit_code, 0)
          self.assertEqual(len(gui_messages), 1)
          title, message = gui_messages[0]
          self.assertIn(expected_title, title.lower())
          self.assertIn(expected_text, message)
          self.assertTrue(log_path.exists())
          self.assertIn(expected_text, log_path.read_text(encoding='utf-8'))

  def test_gui_main_defaults_to_unhydrated_startup_status(self) -> None:
    stream = io.StringIO()

    with patch('calamum_vulcan.app.__main__.QT_AVAILABLE', True):
      with patch('calamum_vulcan.app.__main__.launch_shell', return_value=0):
        with redirect_stdout(stream):
          exit_code = gui_main([])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('Calamum Vulcan GUI launch status', output)
    self.assertIn('\n\ngenerated_at_utc:', output)
    self.assertIn('status:           confirm', output)
    self.assertIn('decision:         gui_launch_ready', output)
    self.assertIn('decision:         gui_launch_ready\n\nCalamum Vulcan GUI exit status', output)
    self.assertNotIn('Summary', output)
    self.assertNotIn('Review state', output)

  def test_gui_status_block_uses_blue_brand_prefix_for_interactive_terminal(self) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined]

    with patch.object(sys, 'stdout', stream):
      output = _render_codesentinel_status_block(
        title='Calamum Vulcan GUI launch status',
        status='confirm',
        decision='gui_launch_ready',
        sections=(),
      )

    self.assertIn('\x1b[96mCalamum Vulcan GUI\x1b[0m launch status', output)
    self.assertIn('\n\ngenerated_at_utc:', output)
    self.assertIn('status:           confirm', output)
    self.assertNotIn('Summary', output)

  def test_gui_main_honors_process_argv_when_wrapper_invokes_without_explicit_args(self) -> None:
    stream = io.StringIO()

    with patch.object(sys, 'argv', ['calamum-vulcan-gui', '--version']):
      with redirect_stdout(stream):
        exit_code = gui_main(None)

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('Calamum Vulcan {version}'.format(version=PROJECT_VERSION), output)

  def test_gui_main_detaches_interactive_launch_without_exit_status_echo(self) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined]

    with patch('calamum_vulcan.app.__main__.QT_AVAILABLE', True):
      with patch(
        'calamum_vulcan.app.__main__._spawn_detached_gui_host',
        return_value=True,
      ) as spawn_detached:
        with patch('calamum_vulcan.app.__main__.launch_shell', return_value=0) as launch:
          with patch.object(sys, 'stdout', stream), patch.object(sys, 'stderr', stream):
            exit_code = gui_main([])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    spawn_detached.assert_called_once()
    launch.assert_not_called()
    self.assertIn('decision:         gui_launch_ready', output)
    self.assertTrue(output.endswith('\n\n'))
    self.assertNotIn('gui_session_closed_cleanly', output)

  def test_gui_main_keeps_duration_bounded_launch_attached_for_validation(self) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined]

    with patch('calamum_vulcan.app.__main__.QT_AVAILABLE', True):
      with patch(
        'calamum_vulcan.app.__main__._spawn_detached_gui_host',
        return_value=True,
      ) as spawn_detached:
        with patch('calamum_vulcan.app.__main__.launch_shell', return_value=0) as launch:
          with patch.object(sys, 'stdout', stream), patch.object(sys, 'stderr', stream):
            exit_code = gui_main(['--duration-ms', '1'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    spawn_detached.assert_not_called()
    launch.assert_called_once()
    self.assertIn('decision:         gui_session_closed_cleanly', output)

  def test_launch_shell_module_forwards_process_args_to_gui_main(self) -> None:
    captured_argv = []

    def _capture_gui_main(argv):
      captured_argv.append(tuple(argv))
      return 0

    with patch.object(
      sys,
      'argv',
      ['calamum_vulcan.launch_shell', '--scenario', 'no-device', '--gui-host-process'],
    ):
      with patch('calamum_vulcan.app.__main__.gui_main', side_effect=_capture_gui_main):
        with self.assertRaises(SystemExit) as exit_signal:
          runpy.run_module('calamum_vulcan.launch_shell', run_name='__main__')

    self.assertEqual(exit_signal.exception.code, 0)
    self.assertEqual(
      captured_argv,
      [('--scenario', 'no-device', '--gui-host-process')],
    )

  def test_pyproject_registers_gui_launcher_as_console_script(self) -> None:
    pyproject_path = FINAL_EXAM_ROOT / 'pyproject.toml'
    project = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))['project']

    self.assertEqual(
      project['scripts']['calamum-vulcan-gui'],
      'calamum_vulcan.app.__main__:gui_main',
    )
    self.assertNotIn('gui-scripts', project)


if __name__ == '__main__':
  unittest.main()