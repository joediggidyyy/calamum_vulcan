"""Heimdall adapter tests for the Calamum Vulcan FS-07 lane."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.adapters.heimdall import build_detect_device_command_plan
from calamum_vulcan.adapters.heimdall import build_download_pit_command_plan
from calamum_vulcan.adapters.heimdall import build_flash_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.adapters.heimdall import replay_heimdall_process_result
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_session
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

  def test_flash_plan_respects_no_reboot_package_posture(self) -> None:
    base_session = build_demo_session('happy')
    package_assessment = build_demo_package_assessment(
      'happy',
      session=base_session,
      package_fixture_name='matched',
    )
    command_plan = build_flash_command_plan(package_assessment)

    self.assertIn('--RECOVERY', command_plan.arguments)
    self.assertIn('recovery.img', command_plan.arguments)
    self.assertIn('--no-reboot', command_plan.arguments)

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

  def test_download_pit_plan_remains_bounded_and_explicit(self) -> None:
    command_plan = build_download_pit_command_plan(output_path='artifacts/device.pit')

    self.assertEqual(command_plan.arguments[0], 'download-pit')
    self.assertIn('--output', command_plan.arguments)
    self.assertIn('artifacts', command_plan.display_command)


if __name__ == '__main__':
  unittest.main()
