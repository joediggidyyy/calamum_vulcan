"""Heimdall adapter tests for the Calamum Vulcan FS-07 lane."""

from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallProcessResult
from calamum_vulcan.adapters.heimdall import build_detect_device_command_plan
from calamum_vulcan.adapters.heimdall import build_download_pit_command_plan
from calamum_vulcan.adapters.heimdall import build_flash_command_plan
from calamum_vulcan.adapters.heimdall import build_flash_command_plan_from_reviewed_plan
from calamum_vulcan.adapters.heimdall import build_print_pit_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.adapters.heimdall import replay_heimdall_process_result
from calamum_vulcan.adapters.heimdall import run_bounded_heimdall_flash_session
from calamum_vulcan.adapters.heimdall import runtime as heimdall_runtime
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
from calamum_vulcan.domain.state import RuntimeSessionRejected
from calamum_vulcan.domain.state import SessionEventType
from calamum_vulcan.domain.state import SessionPhase
from calamum_vulcan.domain.state import replay_events
from calamum_vulcan.fixtures import happy_path_events
from calamum_vulcan.fixtures import load_heimdall_process_fixture


class HeimdallAdapterTests(unittest.TestCase):
  """Prove the Heimdall adapter seam stays outside the shell/state contract."""

  def test_detect_plan_and_normalization_surface_device_identity(self) -> None:
    command_plan = build_detect_device_command_plan()
    process_result = load_heimdall_process_fixture('detect-ready')
    trace = normalize_heimdall_result(command_plan, process_result)

    self.assertEqual(command_plan.arguments, ('detect',))
    self.assertEqual(trace.state, HeimdallTraceState.DETECTED)
    self.assertEqual(trace.platform_events[0].event_type, SessionEventType.DEVICE_CONNECTED)
    self.assertEqual(trace.platform_events[0].payload['product_code'], 'SM-G991U')

  def test_detect_normalization_accepts_generic_heimdall_success_transcript(self) -> None:
    command_plan = build_detect_device_command_plan()
    process_result = load_heimdall_process_fixture('detect-generic-ready')

    trace = normalize_heimdall_result(command_plan, process_result)

    self.assertEqual(trace.state, HeimdallTraceState.DETECTED)
    self.assertEqual(trace.platform_events[0].event_type, SessionEventType.DEVICE_CONNECTED)
    self.assertEqual(trace.platform_events[0].payload['product_code'], 'SM-G991U')
    self.assertEqual(trace.platform_events[0].payload['mode'], 'download')

  def test_detect_normalization_preserves_presence_when_late_runtime_warning_occurs(self) -> None:
    command_plan = build_detect_device_command_plan()
    process_result = load_heimdall_process_fixture('detect-late-warning')

    trace = normalize_heimdall_result(command_plan, process_result)

    self.assertEqual(trace.state, HeimdallTraceState.DETECTED)
    self.assertIn('later transport warning interrupted the probe', trace.summary)
    self.assertTrue(any('Failed to claim interface' in note for note in trace.notes))
    self.assertEqual(trace.platform_events[0].payload['product_code'], 'SM-G991U')

  def test_detect_normalization_distinguishes_no_device_runtime_and_unparsed_failures(self) -> None:
    command_plan = build_detect_device_command_plan()

    no_device_trace = normalize_heimdall_result(
      command_plan,
      load_heimdall_process_fixture('detect-none'),
    )
    runtime_trace = normalize_heimdall_result(
      command_plan,
      load_heimdall_process_fixture('detect-runtime-failure'),
    )
    unparsed_trace = normalize_heimdall_result(
      command_plan,
      HeimdallProcessResult(
        fixture_name='detect-unparsed',
        operation=HeimdallOperation.DETECT,
        exit_code=0,
        stdout_lines=(
          'Detecting device...',
          'Device connected but product identity could not be normalized from this fixture.',
        ),
      ),
    )

    self.assertEqual(no_device_trace.state, HeimdallTraceState.FAILED)
    self.assertIn('did not detect a Samsung download-mode device', no_device_trace.summary)
    self.assertEqual(runtime_trace.state, HeimdallTraceState.FAILED)
    self.assertIn('failed before the platform could verify', runtime_trace.summary)
    self.assertEqual(unparsed_trace.state, HeimdallTraceState.FAILED)
    self.assertIn('could not normalize a trustworthy Samsung download-mode identity', unparsed_trace.summary)
    self.assertTrue(
      any('Review raw Heimdall stdout/stderr' in note for note in unparsed_trace.notes)
    )

  def test_runtime_uses_shorter_timeout_for_detect_than_flash(self) -> None:
    self.assertLess(
      heimdall_runtime._timeout_seconds_for_operation(HeimdallOperation.DETECT),
      heimdall_runtime.PROCESS_TIMEOUT_SECONDS,
    )
    self.assertEqual(
      heimdall_runtime._timeout_seconds_for_operation(HeimdallOperation.FLASH),
      heimdall_runtime.PROCESS_TIMEOUT_SECONDS,
    )

  def test_runtime_prefers_packaged_windows_heimdall_asset_when_available(self) -> None:
    candidate = heimdall_runtime.WINDOWS_PACKAGED_HEIMDALL_EXECUTABLE

    with mock.patch.object(heimdall_runtime.shutil, 'which', return_value=None):
      with mock.patch.object(heimdall_runtime, 'os') as mocked_os:
        mocked_os.name = 'nt'
        mocked_os.getenv.side_effect = lambda key: {
          'HEIMDALL_PATH': None,
          'HEIMDALL_HOME': None,
          'ChocolateyInstall': None,
          'ProgramData': None,
          'SCOOP': None,
          'USERPROFILE': None,
          'ProgramFiles': None,
          'ProgramFiles(x86)': None,
          'LOCALAPPDATA': None,
        }.get(key)
        with mock.patch.object(heimdall_runtime.Path, 'exists', autospec=True) as mocked_exists:
          mocked_exists.side_effect = lambda path: str(path) == str(candidate)
          resolved = heimdall_runtime._resolve_executable('heimdall')

    self.assertEqual(resolved, str(candidate))

  def test_runtime_resolves_common_windows_chocolatey_heimdall_path(self) -> None:
    candidate = Path('C:/ProgramData/chocolatey/bin/heimdall.exe')

    with mock.patch.object(heimdall_runtime.shutil, 'which', return_value=None):
      with mock.patch.object(heimdall_runtime, 'os') as mocked_os:
        mocked_os.name = 'nt'
        mocked_os.getenv.side_effect = lambda key: {
          'HEIMDALL_PATH': None,
          'HEIMDALL_HOME': None,
          'ChocolateyInstall': None,
          'ProgramData': 'C:/ProgramData',
          'SCOOP': None,
          'USERPROFILE': None,
          'ProgramFiles': None,
          'ProgramFiles(x86)': None,
          'LOCALAPPDATA': None,
        }.get(key)
        with mock.patch.object(heimdall_runtime.Path, 'exists', autospec=True) as mocked_exists:
          mocked_exists.side_effect = lambda path: str(path) == str(candidate)
          resolved = heimdall_runtime._resolve_executable('heimdall')

    self.assertEqual(resolved, str(candidate))

  def test_runtime_reports_missing_dll_guidance_for_packaged_asset(self) -> None:
    command_plan = build_print_pit_command_plan()

    with mock.patch.object(
      heimdall_runtime,
      '_resolve_executable',
      return_value=str(heimdall_runtime.WINDOWS_PACKAGED_HEIMDALL_EXECUTABLE),
    ):
      with mock.patch.object(
        heimdall_runtime.subprocess,
        'run',
        return_value=mock.Mock(returncode=3221225781, stdout='', stderr=''),
      ):
        result = heimdall_runtime._run_process(command_plan, 'live-process')

    self.assertEqual(result.exit_code, 3221225781)
    self.assertTrue(any('0xC0000135' in line for line in result.stderr_lines))
    self.assertTrue(
      any('Microsoft Visual C++ 2012 x86 runtime' in line for line in result.stderr_lines)
    )

  def test_flash_plan_respects_no_reboot_package_posture(self) -> None:
    base_session = build_demo_session('happy')
    package_assessment = build_demo_package_assessment(
      'happy',
      session=base_session,
      package_fixture_name='matched',
    )
    reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)
    command_plan = build_flash_command_plan_from_reviewed_plan(reviewed_flash_plan)

    self.assertTrue(reviewed_flash_plan.ready_for_transport)
    self.assertIn('--RECOVERY', command_plan.arguments)
    self.assertIn('recovery.img', command_plan.arguments)
    self.assertIn('--no-reboot', command_plan.arguments)

  def test_package_assessment_flash_builder_routes_through_reviewed_plan(self) -> None:
    base_session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=base_session)

    command_plan = build_flash_command_plan(package_assessment)

    self.assertEqual(command_plan.arguments[0], 'flash')
    self.assertIn('--RECOVERY', command_plan.arguments)
    self.assertIn('vbmeta.img', command_plan.arguments)

  def test_successful_flash_trace_replays_to_completed_session(self) -> None:
    base_session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=base_session)
    command_plan = build_flash_command_plan(package_assessment)
    process_result = load_heimdall_process_fixture('flash-success')

    session, trace = replay_heimdall_process_result(
      base_session,
      command_plan,
      process_result,
    )

    self.assertEqual(trace.state, HeimdallTraceState.COMPLETED)
    self.assertEqual(session.phase, SessionPhase.COMPLETED)
    self.assertIn('RECOVERY 42%', trace.progress_markers)

  def test_failed_flash_trace_replays_to_failed_session(self) -> None:
    base_session = replay_events(happy_path_events()[:-2])
    package_assessment = build_demo_package_assessment(
      'happy',
      session=base_session,
      package_fixture_name='matched',
    )
    command_plan = build_flash_command_plan(package_assessment)
    process_result = load_heimdall_process_fixture('flash-failure')

    session, trace = replay_heimdall_process_result(
      base_session,
      command_plan,
      process_result,
    )

    self.assertEqual(trace.state, HeimdallTraceState.FAILED)
    self.assertEqual(session.phase, SessionPhase.FAILED)
    self.assertEqual(session.failure_reason, 'USB transfer timeout during partition write')

  def test_bounded_flash_session_runs_reviewed_plan_through_explicit_runner(self) -> None:
    base_session = replay_events(happy_path_events()[:-2])
    package_assessment = build_demo_package_assessment(
      'happy',
      session=base_session,
      package_fixture_name='matched',
    )
    reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)
    process_result = load_heimdall_process_fixture('flash-success')

    runtime_result = run_bounded_heimdall_flash_session(
      base_session,
      reviewed_flash_plan,
      package_assessment=package_assessment,
      pit_inspection=build_demo_pit_inspection(
        'happy',
        session=base_session,
        package_assessment=package_assessment,
      ),
      runner=lambda command_plan: process_result,
      fixture_name='flash-success',
    )

    self.assertEqual(runtime_result.execution_source, 'explicit_runner')
    self.assertEqual(runtime_result.trace.state, HeimdallTraceState.COMPLETED)
    self.assertEqual(runtime_result.session.phase, SessionPhase.COMPLETED)
    self.assertEqual(runtime_result.reviewed_plan_id, reviewed_flash_plan.plan_id)

  def test_bounded_flash_session_rejects_non_ready_session(self) -> None:
    ready_session = replay_events(happy_path_events()[:-2])
    package_assessment = build_demo_package_assessment(
      'happy',
      session=ready_session,
      package_fixture_name='matched',
    )
    reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)

    with self.assertRaises(RuntimeSessionRejected):
      run_bounded_heimdall_flash_session(
        build_demo_session('blocked'),
        reviewed_flash_plan,
        package_assessment=package_assessment,
        pit_inspection=build_demo_pit_inspection(
          'blocked',
          session=build_demo_session('blocked'),
          package_assessment=build_demo_package_assessment(
            'blocked',
            session=build_demo_session('blocked'),
          ),
        ),
        runner=lambda command_plan: load_heimdall_process_fixture('flash-success'),
      )

  def test_bounded_flash_session_rejects_pit_mismatch_before_transport(self) -> None:
    ready_session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment(
      'ready',
      session=ready_session,
    )
    reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)
    mismatched_pit = build_demo_pit_inspection(
      'happy',
      session=ready_session,
      package_assessment=package_assessment,
    )

    with self.assertRaises(RuntimeSessionRejected):
      run_bounded_heimdall_flash_session(
        ready_session,
        reviewed_flash_plan,
        package_assessment=package_assessment,
        pit_inspection=mismatched_pit,
        runner=lambda command_plan: load_heimdall_process_fixture('flash-success'),
      )

  def test_download_pit_plan_remains_bounded_and_explicit(self) -> None:
    command_plan = build_download_pit_command_plan(output_path='artifacts/device.pit')

    self.assertEqual(command_plan.arguments[0], 'download-pit')
    self.assertIn('--output', command_plan.arguments)
    self.assertIn('artifacts', command_plan.display_command)

  def test_download_pit_runtime_creates_output_parent_before_process(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'nested' / 'device.pit'
      command_plan = build_download_pit_command_plan(output_path=str(output_path))

      def _fake_run(*args, **kwargs):
        self.assertTrue(output_path.parent.exists())
        return mock.Mock(returncode=0, stdout='', stderr='')

      with mock.patch.object(
        heimdall_runtime,
        '_resolve_executable',
        return_value='heimdall',
      ):
        with mock.patch.object(
          heimdall_runtime.subprocess,
          'run',
          side_effect=_fake_run,
        ):
          heimdall_runtime.execute_heimdall_command(command_plan)

      self.assertTrue(output_path.parent.exists())

  def test_download_pit_runtime_absolutizes_relative_output_path_before_packaged_subprocess(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      temp_root = Path(temp_dir)
      executable_path = temp_root / 'packaged' / 'heimdall.exe'
      executable_path.parent.mkdir(parents=True, exist_ok=True)
      executable_path.write_text('', encoding='utf-8')
      command_plan = build_download_pit_command_plan(output_path='artifacts/device.pit')

      def _fake_run(command, **kwargs):
        self.assertEqual(Path(kwargs['cwd']), executable_path.parent)
        output_path = Path(command[command.index('--output') + 1])
        self.assertTrue(output_path.is_absolute())
        self.assertEqual(output_path, temp_root / 'artifacts' / 'device.pit')
        self.assertTrue(output_path.parent.exists())
        return mock.Mock(returncode=0, stdout='', stderr='')

      with mock.patch.object(heimdall_runtime.Path, 'cwd', return_value=temp_root):
        with mock.patch.object(
          heimdall_runtime,
          '_resolve_executable',
          return_value=str(executable_path),
        ):
          with mock.patch.object(
            heimdall_runtime.subprocess,
            'run',
            side_effect=_fake_run,
          ):
            heimdall_runtime.execute_heimdall_command(command_plan)

      self.assertTrue((temp_root / 'artifacts').exists())

  def test_print_pit_plan_remains_bounded_and_explicit(self) -> None:
    command_plan = build_print_pit_command_plan()

    self.assertEqual(command_plan.arguments, ('print-pit',))
    self.assertEqual(command_plan.display_command, 'heimdall print-pit')


if __name__ == '__main__':
  unittest.main()
