"""Unit tests for the Calamum Vulcan ADB/Fastboot companion adapter."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import unittest
from unittest import mock


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsTraceState
from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_reboot_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_fastboot_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_fastboot_reboot_command_plan
from calamum_vulcan.adapters.adb_fastboot import execute_android_tools_command
from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
from calamum_vulcan.adapters.adb_fastboot import runtime as adb_fastboot_runtime


class AdbFastbootAdapterTests(unittest.TestCase):
  """Prove the bounded ADB/Fastboot companion seam stays explicit."""

  def test_adb_detect_plan_uses_devices_long_output(self) -> None:
    command_plan = build_adb_detect_command_plan(device_serial='R58N12345AB')

    self.assertEqual(command_plan.backend, AndroidToolsBackend.ADB)
    self.assertEqual(command_plan.arguments, ('-s', 'R58N12345AB', 'devices', '-l'))
    self.assertEqual(command_plan.display_command, 'adb -s R58N12345AB devices -l')

  def test_adb_detection_normalizes_ready_and_unauthorized_devices(self) -> None:
    command_plan = build_adb_detect_command_plan()
    process_result = AndroidToolsProcessResult(
      fixture_name='adb-mixed',
      operation=AndroidToolsOperation.ADB_DEVICES,
      backend=AndroidToolsBackend.ADB,
      exit_code=0,
      stdout_lines=(
        'List of devices attached',
        'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
        '192.168.0.10:5555\tunauthorized model:SM_G991U device:dm3q',
      ),
    )

    trace = normalize_android_tools_result(command_plan, process_result)

    self.assertEqual(trace.state, AndroidToolsTraceState.DETECTED)
    self.assertEqual(len(trace.detected_devices), 2)
    self.assertEqual(trace.detected_devices[0].transport, 'usb')
    self.assertEqual(trace.detected_devices[1].transport, 'tcpip')
    self.assertIn('command-ready', trace.summary)
    self.assertTrue(
      any('unauthorized' in note for note in trace.notes)
    )

  def test_fastboot_detection_normalizes_connected_device(self) -> None:
    command_plan = build_fastboot_detect_command_plan()
    process_result = AndroidToolsProcessResult(
      fixture_name='fastboot-ready',
      operation=AndroidToolsOperation.FASTBOOT_DEVICES,
      backend=AndroidToolsBackend.FASTBOOT,
      exit_code=0,
      stdout_lines=('R58N12345AB\tfastboot',),
    )

    trace = normalize_android_tools_result(command_plan, process_result)

    self.assertEqual(trace.state, AndroidToolsTraceState.DETECTED)
    self.assertEqual(trace.detected_devices[0].serial, 'R58N12345AB')
    self.assertEqual(trace.detected_devices[0].state, 'fastboot')

  def test_fastboot_detection_parses_optional_identity_tokens(self) -> None:
    command_plan = build_fastboot_detect_command_plan()
    process_result = AndroidToolsProcessResult(
      fixture_name='fastboot-identity',
      operation=AndroidToolsOperation.FASTBOOT_DEVICES,
      backend=AndroidToolsBackend.FASTBOOT,
      exit_code=0,
      stdout_lines=(
        'FASTBOOT123\tfastboot product:dm3q model:SM_G991U device:dm3q',
      ),
    )

    trace = normalize_android_tools_result(command_plan, process_result)

    self.assertEqual(trace.state, AndroidToolsTraceState.DETECTED)
    self.assertEqual(trace.detected_devices[0].product, 'dm3q')
    self.assertEqual(trace.detected_devices[0].model, 'SM_G991U')
    self.assertEqual(trace.detected_devices[0].device, 'dm3q')

  def test_adb_device_info_plan_and_normalization_surface_structured_properties(self) -> None:
    command_plan = build_adb_device_info_command_plan(device_serial='R58N12345AB')
    process_result = AndroidToolsProcessResult(
      fixture_name='adb-info-ready',
      operation=AndroidToolsOperation.ADB_GETPROP,
      backend=AndroidToolsBackend.ADB,
      exit_code=0,
      stdout_lines=(
        '[ro.product.manufacturer]: [samsung]',
        '[ro.product.brand]: [samsung]',
        '[ro.product.model]: [SM-G991U]',
        '[ro.build.version.release]: [14]',
        '[ro.build.version.security_patch]: [2026-04-05]',
      ),
    )

    trace = normalize_android_tools_result(command_plan, process_result)

    self.assertEqual(command_plan.arguments, ('-s', 'R58N12345AB', 'shell', 'getprop'))
    self.assertEqual(trace.state, AndroidToolsTraceState.COMPLETED)
    self.assertEqual(trace.observed_properties['ro.product.manufacturer'], 'samsung')
    self.assertEqual(trace.observed_properties['ro.build.version.release'], '14')
    self.assertTrue(any('read-side only' in note for note in trace.notes))

  def test_vendor_specific_download_reboot_plan_is_flagged(self) -> None:
    command_plan = build_adb_reboot_command_plan(
      'download',
      device_serial='R58N12345AB',
    )

    self.assertTrue(command_plan.vendor_specific)
    self.assertEqual(command_plan.reboot_target, 'download')
    self.assertEqual(
      command_plan.display_command,
      'adb -s R58N12345AB reboot download',
    )
    self.assertTrue(command_plan.notes)

  def test_runtime_runner_normalizes_successful_reboot(self) -> None:
    command_plan = build_fastboot_reboot_command_plan('bootloader')

    def fake_runner(_command_plan):
      return AndroidToolsProcessResult(
        fixture_name='live-fastboot-reboot',
        operation=AndroidToolsOperation.FASTBOOT_REBOOT,
        backend=AndroidToolsBackend.FASTBOOT,
        exit_code=0,
      )

    trace = execute_android_tools_command(command_plan, runner=fake_runner)

    self.assertEqual(trace.state, AndroidToolsTraceState.COMPLETED)
    self.assertEqual(trace.summary, 'FASTBOOT reboot command accepted for target bootloader.')

  def test_runtime_resolves_default_windows_sdk_platform_tools_path(self) -> None:
    candidate = Path('C:/Users/tester/AppData/Local/Android/Sdk/platform-tools/adb.exe')

    with mock.patch.object(adb_fastboot_runtime.shutil, 'which', return_value=None):
      with mock.patch.object(adb_fastboot_runtime, 'os') as mocked_os:
        mocked_os.name = 'nt'
        mocked_os.getenv.side_effect = lambda key: {
          'ANDROID_SDK_ROOT': None,
          'ANDROID_HOME': None,
          'LOCALAPPDATA': 'C:/Users/tester/AppData/Local',
        }.get(key)
        with mock.patch.object(adb_fastboot_runtime.Path, 'exists', autospec=True) as mocked_exists:
          mocked_exists.side_effect = lambda path: str(path) == str(candidate)
          resolved = adb_fastboot_runtime._resolve_executable('adb')

    self.assertEqual(resolved, str(candidate))

  def test_runtime_returns_timeout_result_for_hung_command(self) -> None:
    command_plan = build_adb_detect_command_plan()
    timeout_error = subprocess.TimeoutExpired(
      cmd=['adb', 'devices', '-l'],
      timeout=adb_fastboot_runtime.PROCESS_TIMEOUT_SECONDS,
      output='List of devices attached\n',
      stderr='device query stalled',
    )

    with mock.patch.object(adb_fastboot_runtime, '_resolve_executable', return_value='adb'):
      with mock.patch.object(
        adb_fastboot_runtime.subprocess,
        'run',
        side_effect=timeout_error,
      ):
        process_result = adb_fastboot_runtime._run_process(
          command_plan,
          fixture_name='live-process',
        )

    self.assertEqual(process_result.exit_code, 124)
    self.assertEqual(process_result.stdout_lines, ('List of devices attached',))
    self.assertIn('timed out after', process_result.stderr_lines[-1])

  def test_runtime_uses_shorter_timeout_for_detect_and_info_than_global_bound(self) -> None:
    self.assertLess(
      adb_fastboot_runtime._timeout_seconds_for_operation(
        AndroidToolsOperation.ADB_DEVICES,
      ),
      adb_fastboot_runtime.PROCESS_TIMEOUT_SECONDS,
    )
    self.assertLess(
      adb_fastboot_runtime._timeout_seconds_for_operation(
        AndroidToolsOperation.ADB_GETPROP,
      ),
      adb_fastboot_runtime.PROCESS_TIMEOUT_SECONDS,
    )
    self.assertEqual(
      adb_fastboot_runtime._timeout_seconds_for_operation(
        AndroidToolsOperation.ADB_REBOOT,
      ),
      15,
    )

  def test_runtime_suppresses_windows_console_window_for_live_commands(self) -> None:
    command_plan = build_adb_detect_command_plan()
    completed = mock.Mock(returncode=0, stdout='', stderr='')

    with mock.patch.object(adb_fastboot_runtime, '_resolve_executable', return_value='adb.exe'):
      with mock.patch.object(adb_fastboot_runtime.os, 'name', 'nt'):
        with mock.patch.object(
          adb_fastboot_runtime.subprocess,
          'run',
          return_value=completed,
        ) as mocked_run:
          adb_fastboot_runtime._run_process(
            command_plan,
            fixture_name='live-process',
          )

    kwargs = mocked_run.call_args.kwargs
    create_no_window = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    if create_no_window:
      self.assertEqual(kwargs.get('creationflags'), create_no_window)
    startupinfo_factory = getattr(subprocess, 'STARTUPINFO', None)
    use_show_window = getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
    hide_window = getattr(subprocess, 'SW_HIDE', 0)
    if startupinfo_factory is not None and use_show_window:
      startupinfo = kwargs.get('startupinfo')
      self.assertIsNotNone(startupinfo)
      self.assertEqual(startupinfo.wShowWindow, hide_window)
      self.assertTrue(startupinfo.dwFlags & use_show_window)
    else:
      self.assertNotIn('startupinfo', kwargs)


if __name__ == '__main__':
  unittest.main()