"""Normalize Heimdall process output into platform-owned events."""

from __future__ import annotations

import re
from typing import List

from calamum_vulcan.domain.state import PlatformEvent
from calamum_vulcan.domain.state import SessionEventType

from .model import HeimdallCommandPlan
from .model import HeimdallNormalizedTrace
from .model import HeimdallOperation
from .model import HeimdallProcessResult
from .model import HeimdallTraceState


DEVICE_PATTERN = re.compile(
  r'Device detected: device_id=(?P<device_id>\S+) '
  r'product_code=(?P<product_code>\S+) mode=(?P<mode>\S+)'
)

PROGRESS_PATTERN = re.compile(
  r'Uploading (?P<partition>[A-Z0-9_]+) \((?P<percent>\d+)%\)'
)


def normalize_heimdall_result(
  command_plan: HeimdallCommandPlan,
  process_result: HeimdallProcessResult,
) -> HeimdallNormalizedTrace:
  """Normalize one Heimdall process result into platform-owned transport truth."""

  if process_result.operation == HeimdallOperation.DETECT:
    return _normalize_detect_result(command_plan, process_result)
  if process_result.operation == HeimdallOperation.FLASH:
    return _normalize_flash_result(command_plan, process_result)
  return _normalize_non_stateful_result(command_plan, process_result)


def _normalize_detect_result(
  command_plan: HeimdallCommandPlan,
  process_result: HeimdallProcessResult,
) -> HeimdallNormalizedTrace:
  events = []  # type: List[PlatformEvent]
  notes = []  # type: List[str]

  for line in process_result.stdout_lines:
    match = DEVICE_PATTERN.search(line)
    if match is None:
      continue
    payload = {
      'device_id': match.group('device_id'),
      'product_code': match.group('product_code'),
      'mode': match.group('mode'),
    }
    events.append(PlatformEvent(SessionEventType.DEVICE_CONNECTED, payload))
    notes.append('Samsung download-mode device detected through Heimdall.')
    break

  if events:
    return HeimdallNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=HeimdallTraceState.DETECTED,
      summary='Heimdall detected a Samsung device and normalized it into platform identity.',
      exit_code=process_result.exit_code,
      platform_events=tuple(events),
      notes=tuple(notes),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  reason = _failure_reason(process_result)
  return HeimdallNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=HeimdallTraceState.FAILED,
    summary='Heimdall device detection did not produce a trustworthy identity result.',
    exit_code=process_result.exit_code,
    platform_events=(),
    notes=(reason,),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _normalize_flash_result(
  command_plan: HeimdallCommandPlan,
  process_result: HeimdallProcessResult,
) -> HeimdallNormalizedTrace:
  events = []  # type: List[PlatformEvent]
  progress_markers = []  # type: List[str]
  notes = []  # type: List[str]
  started = False
  paused = False
  resumed = False
  completed = False

  for line in process_result.stdout_lines:
    lower_line = line.lower()
    if 'beginning session' in lower_line and not started:
      events.append(PlatformEvent(SessionEventType.EXECUTION_STARTED))
      started = True

    progress_match = PROGRESS_PATTERN.search(line)
    if progress_match is not None:
      progress_markers.append(
        '{partition} {percent}%'.format(
          partition=progress_match.group('partition'),
          percent=progress_match.group('percent'),
        )
      )

    if 'manual recovery boot required' in lower_line and not paused:
      note = 'Manual recovery boot required before transport can continue.'
      notes.append(note)
      events.append(
        PlatformEvent(
          SessionEventType.EXECUTION_PAUSED,
          {'notes': (note,)},
        )
      )
      paused = True

    if 'operator resumed workflow' in lower_line and not resumed:
      events.append(PlatformEvent(SessionEventType.EXECUTION_RESUMED))
      resumed = True

    if (
      'flash completed successfully' in lower_line
      or 'session finalized successfully' in lower_line
    ) and not completed:
      events.append(PlatformEvent(SessionEventType.EXECUTION_COMPLETED))
      completed = True

  if process_result.exit_code not in command_plan.expected_exit_codes:
    if not started:
      events.append(PlatformEvent(SessionEventType.EXECUTION_STARTED))
    failure_reason = _failure_reason(process_result)
    events.append(
      PlatformEvent(
        SessionEventType.EXECUTION_FAILED,
        {'reason': failure_reason},
      )
    )
    notes.append(failure_reason)
    return HeimdallNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=HeimdallTraceState.FAILED,
      summary='Heimdall flash output was normalized into a transport failure event.',
      exit_code=process_result.exit_code,
      platform_events=tuple(events),
      progress_markers=tuple(progress_markers),
      notes=tuple(notes),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  if completed:
    summary = 'Heimdall flash output completed and remained behind the platform-owned adapter seam.'
    if paused and resumed:
      summary = 'Heimdall flash output included a no-reboot recovery handoff and a normalized resume path.'
    return HeimdallNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=HeimdallTraceState.COMPLETED,
      summary=summary,
      exit_code=process_result.exit_code,
      platform_events=tuple(events),
      progress_markers=tuple(progress_markers),
      notes=tuple(notes),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  if paused:
    return HeimdallNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=HeimdallTraceState.RESUME_NEEDED,
      summary='Heimdall flash output requires a manual recovery step before transport can continue.',
      exit_code=process_result.exit_code,
      platform_events=tuple(events),
      progress_markers=tuple(progress_markers),
      notes=tuple(notes),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  return HeimdallNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=HeimdallTraceState.EXECUTING if started else HeimdallTraceState.NOT_INVOKED,
    summary='Heimdall flash output was normalized but did not reach a terminal state.',
    exit_code=process_result.exit_code,
    platform_events=tuple(events),
    progress_markers=tuple(progress_markers),
    notes=tuple(notes),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _normalize_non_stateful_result(
  command_plan: HeimdallCommandPlan,
  process_result: HeimdallProcessResult,
) -> HeimdallNormalizedTrace:
  if process_result.exit_code in command_plan.expected_exit_codes:
    return HeimdallNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=HeimdallTraceState.COMPLETED,
      summary='Heimdall {operation} completed and remained adapter-contained.'.format(
        operation=process_result.operation.value,
      ),
      exit_code=process_result.exit_code,
      platform_events=(),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  failure_reason = _failure_reason(process_result)
  return HeimdallNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=HeimdallTraceState.FAILED,
    summary='Heimdall {operation} failed before any platform state change was allowed.'.format(
      operation=process_result.operation.value,
    ),
    exit_code=process_result.exit_code,
    platform_events=(),
    notes=(failure_reason,),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _failure_reason(process_result: HeimdallProcessResult) -> str:
  if process_result.stderr_lines:
    first_error = process_result.stderr_lines[0]
    if first_error.lower().startswith('error:'):
      return first_error.split(':', 1)[1].strip()
    return first_error
  for line in process_result.stdout_lines:
    if 'error:' in line.lower():
      return line.split(':', 1)[1].strip()
  return 'Heimdall process exited unexpectedly without a normalized reason.'
