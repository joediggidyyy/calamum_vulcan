"""Pure transition logic for the Calamum Vulcan session contract."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Tuple

from .model import GuardState
from .model import PlatformEvent
from .model import PlatformSession
from .model import SessionEventType
from .model import SessionPhase
from .model import TransitionRejected


def apply_event(
  session: PlatformSession,
  event: PlatformEvent,
) -> PlatformSession:
  """Apply one normalized event to an immutable session snapshot."""

  event_type = event.event_type
  payload = event.payload

  if event_type == SessionEventType.DEVICE_CONNECTED:
    return _connect_device(session, payload, event_type)
  if event_type == SessionEventType.DEVICE_DISCONNECTED:
    return _disconnect_device(session, event_type)
  if event_type == SessionEventType.PACKAGE_SELECTED:
    return _select_package(session, payload, event_type)
  if event_type == SessionEventType.PREFLIGHT_REVIEW_STARTED:
    return _start_preflight(session, event_type)
  if event_type == SessionEventType.PREFLIGHT_BLOCKED:
    return _block_preflight(session, payload, event_type)
  if event_type == SessionEventType.PREFLIGHT_CLEARED:
    return _clear_preflight(session, payload, event_type)
  if event_type == SessionEventType.ACKNOWLEDGEMENTS_CAPTURED:
    return _capture_acknowledgements(session, payload, event_type)
  if event_type == SessionEventType.EXECUTION_STARTED:
    return _start_execution(session, event_type)
  if event_type == SessionEventType.EXECUTION_PAUSED:
    return _pause_execution(session, payload, event_type)
  if event_type == SessionEventType.EXECUTION_RESUMED:
    return _resume_execution(session, event_type)
  if event_type == SessionEventType.EXECUTION_COMPLETED:
    return _complete_execution(session, event_type)
  if event_type == SessionEventType.EXECUTION_FAILED:
    return _fail_execution(session, payload, event_type)
  if event_type == SessionEventType.RESET_SESSION:
    return PlatformSession(last_event=event_type)

  raise TransitionRejected(f'Unsupported event: {event_type}')


def replay_events(
  events: Iterable[PlatformEvent],
  initial: PlatformSession = PlatformSession(),
) -> PlatformSession:
  """Replay a fixture or live event stream into one final state snapshot."""

  session = initial
  for event in events:
    session = apply_event(session, event)
  return session


def _connect_device(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  guards = replace(
    session.guards,
    has_device=True,
    preflight_started=False,
    preflight_complete=False,
    warnings_acknowledged=False,
    destructive_acknowledged=False,
    validation_blocked=False,
  )
  phase = SessionPhase.PACKAGE_LOADED
  if not guards.package_loaded:
    phase = SessionPhase.DEVICE_DETECTED
  return replace(
    session,
    phase=phase,
    guards=guards,
    device_id=_string_value(payload, 'device_id'),
    product_code=_string_value(payload, 'product_code'),
    mode=_string_value(payload, 'mode'),
    failure_reason=None,
    preflight_notes=(),
    last_event=event_type,
  )


def _disconnect_device(
  session: PlatformSession,
  event_type: SessionEventType,
) -> PlatformSession:
  guards = replace(
    session.guards,
    has_device=False,
    preflight_started=False,
    preflight_complete=False,
    warnings_acknowledged=False,
    destructive_acknowledged=False,
    validation_blocked=False,
  )
  phase = SessionPhase.NO_DEVICE
  if guards.package_loaded:
    phase = SessionPhase.PACKAGE_LOADED
  return replace(
    session,
    phase=phase,
    guards=guards,
    device_id=None,
    product_code=None,
    mode=None,
    failure_reason=None,
    preflight_notes=(),
    last_event=event_type,
  )


def _select_package(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  risk = _string_value(payload, 'risk_level')
  guards = replace(
    session.guards,
    package_loaded=True,
    preflight_started=False,
    preflight_complete=False,
    warnings_acknowledged=False,
    destructive_acknowledged=False,
    validation_blocked=False,
    operation_is_destructive=risk == 'destructive',
  )
  return replace(
    session,
    phase=SessionPhase.PACKAGE_LOADED,
    guards=guards,
    package_id=_string_value(payload, 'package_id'),
    package_risk=risk,
    failure_reason=None,
    preflight_notes=(),
    last_event=event_type,
  )


def _start_preflight(
  session: PlatformSession,
  event_type: SessionEventType,
) -> PlatformSession:
  if not session.guards.has_device:
    raise TransitionRejected('Preflight cannot start without a device.')
  if not session.guards.package_loaded:
    raise TransitionRejected('Preflight cannot start without a package.')

  guards = replace(
    session.guards,
    preflight_started=True,
    preflight_complete=False,
    validation_blocked=False,
    warnings_acknowledged=False,
    destructive_acknowledged=False,
  )
  return replace(
    session,
    phase=SessionPhase.PREFLIGHT_INCOMPLETE,
    guards=guards,
    failure_reason=None,
    preflight_notes=(),
    last_event=event_type,
  )


def _block_preflight(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  _require_preflight_started(session)
  guards = replace(
    session.guards,
    preflight_complete=True,
    validation_blocked=True,
  )
  return replace(
    session,
    phase=SessionPhase.VALIDATION_BLOCKED,
    guards=guards,
    failure_reason=None,
    preflight_notes=_notes_from_payload(payload),
    last_event=event_type,
  )


def _clear_preflight(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  _require_preflight_started(session)
  guards = replace(
    session.guards,
    preflight_complete=True,
    validation_blocked=False,
  )
  return replace(
    session,
    phase=SessionPhase.VALIDATION_PASSED,
    guards=guards,
    failure_reason=None,
    preflight_notes=_notes_from_payload(payload),
    last_event=event_type,
  )


def _capture_acknowledgements(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  if session.phase not in (
    SessionPhase.VALIDATION_PASSED,
    SessionPhase.READY_TO_EXECUTE,
  ):
    raise TransitionRejected(
      'Acknowledgements can only be captured after validation passes.'
    )

  guards = replace(
    session.guards,
    warnings_acknowledged=bool(
      payload.get('warnings_acknowledged', False)
    ),
    destructive_acknowledged=bool(
      payload.get('destructive_acknowledged', False)
    ),
  )
  phase = SessionPhase.VALIDATION_PASSED
  if guards.ready():
    phase = SessionPhase.READY_TO_EXECUTE
  return replace(
    session,
    phase=phase,
    guards=guards,
    failure_reason=None,
    last_event=event_type,
  )


def _start_execution(
  session: PlatformSession,
  event_type: SessionEventType,
) -> PlatformSession:
  if session.phase != SessionPhase.READY_TO_EXECUTE:
    raise TransitionRejected('Execution can only start from ready_to_execute.')
  if not session.guards.ready():
    raise TransitionRejected('Execution cannot start while guards are open.')
  return replace(
    session,
    phase=SessionPhase.EXECUTING,
    failure_reason=None,
    last_event=event_type,
  )


def _pause_execution(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  if session.phase != SessionPhase.EXECUTING:
    raise TransitionRejected('Execution can only pause while executing.')
  return replace(
    session,
    phase=SessionPhase.RESUME_NEEDED,
    preflight_notes=_notes_from_payload(payload),
    last_event=event_type,
  )


def _resume_execution(
  session: PlatformSession,
  event_type: SessionEventType,
) -> PlatformSession:
  if session.phase != SessionPhase.RESUME_NEEDED:
    raise TransitionRejected('Execution can only resume from resume_needed.')
  return replace(
    session,
    phase=SessionPhase.EXECUTING,
    last_event=event_type,
  )


def _complete_execution(
  session: PlatformSession,
  event_type: SessionEventType,
) -> PlatformSession:
  if session.phase != SessionPhase.EXECUTING:
    raise TransitionRejected(
      'Execution can only complete after execution has started.'
    )
  return replace(
    session,
    phase=SessionPhase.COMPLETED,
    failure_reason=None,
    last_event=event_type,
  )


def _fail_execution(
  session: PlatformSession,
  payload: Mapping[str, object],
  event_type: SessionEventType,
) -> PlatformSession:
  if session.phase not in (
    SessionPhase.EXECUTING,
    SessionPhase.RESUME_NEEDED,
  ):
    raise TransitionRejected(
      'Execution failures must come from executing or resume_needed.'
    )
  return replace(
    session,
    phase=SessionPhase.FAILED,
    failure_reason=_string_value(payload, 'reason'),
    last_event=event_type,
  )


def _require_preflight_started(session: PlatformSession) -> None:
  if not session.guards.preflight_started:
    raise TransitionRejected('Preflight results require a started preflight.')


def _notes_from_payload(payload: Mapping[str, object]) -> Tuple[str, ...]:
  notes = payload.get('notes', ())
  if isinstance(notes, str):
    return (notes,)
  return tuple(str(note) for note in notes)


def _string_value(
  payload: Mapping[str, object],
  key: str,
) -> Optional[str]:
  value = payload.get(key)
  if value is None:
    return None
  return str(value)