"""Unit tests for the Calamum Vulcan FS-02 state contract."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.state import PlatformEvent
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import SessionEventType
from calamum_vulcan.domain.state import SessionPhase
from calamum_vulcan.domain.state import TransitionRejected
from calamum_vulcan.domain.state import apply_event
from calamum_vulcan.domain.state import replay_events
from calamum_vulcan.fixtures import blocked_then_cleared_events
from calamum_vulcan.fixtures import blocked_validation_events
from calamum_vulcan.fixtures import execution_failure_events
from calamum_vulcan.fixtures import happy_path_events
from calamum_vulcan.fixtures import package_first_events
from calamum_vulcan.fixtures import resume_needed_events


class StateContractTests(unittest.TestCase):
  """Prove the FS-02 orchestration contract before any GUI work begins."""

  def test_happy_path_reaches_completed(self) -> None:
    session = replay_events(happy_path_events())

    self.assertEqual(session.phase, SessionPhase.COMPLETED)
    self.assertEqual(session.product_code, 'SM-G973F')
    self.assertTrue(session.guards.ready())

  def test_blocked_preflight_rejects_execution_until_cleared(self) -> None:
    blocked_session = replay_events(blocked_validation_events())

    self.assertEqual(blocked_session.phase, SessionPhase.VALIDATION_BLOCKED)
    self.assertIn('Product code mismatch', blocked_session.preflight_notes)

    with self.assertRaises(TransitionRejected):
      apply_event(
        blocked_session,
        PlatformEvent(SessionEventType.EXECUTION_STARTED),
      )

    recovered_session = replay_events(blocked_then_cleared_events())
    self.assertEqual(recovered_session.phase, SessionPhase.READY_TO_EXECUTE)

  def test_resume_needed_flow_returns_to_completed(self) -> None:
    session = replay_events(resume_needed_events())

    self.assertEqual(session.phase, SessionPhase.COMPLETED)
    self.assertEqual(session.last_event, SessionEventType.EXECUTION_COMPLETED)

  def test_execution_start_requires_ready_state(self) -> None:
    with self.assertRaises(TransitionRejected):
      apply_event(
        PlatformSession(),
        PlatformEvent(SessionEventType.EXECUTION_STARTED),
      )

  def test_failure_flow_captures_reason(self) -> None:
    session = replay_events(execution_failure_events())

    self.assertEqual(session.phase, SessionPhase.FAILED)
    self.assertEqual(
      session.failure_reason,
      'USB transfer timeout during partition write',
    )

  def test_package_can_be_loaded_before_device(self) -> None:
    session = replay_events(package_first_events())

    self.assertEqual(session.phase, SessionPhase.READY_TO_EXECUTE)
    self.assertEqual(session.package_id, 'package-first-demo')
    self.assertTrue(session.guards.has_device)


if __name__ == '__main__':
  unittest.main()