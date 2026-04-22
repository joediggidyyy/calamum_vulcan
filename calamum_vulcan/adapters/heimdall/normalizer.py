"""Normalize Heimdall process output into platform-owned events."""

from __future__ import annotations

import re
from typing import Dict
from typing import List
from typing import Optional

from calamum_vulcan.domain.state.model import PlatformEvent
from calamum_vulcan.domain.state.model import SessionEventType

from .model import HeimdallCommandPlan
from .model import HeimdallNormalizedTrace
from .model import HeimdallOperation
from .model import HeimdallProcessResult
from .model import HeimdallTraceState


DEVICE_PATTERN = re.compile(
  r'Device detected: device_id=(?P<device_id>\S+) '
  r'product_code=(?P<product_code>\S+) mode=(?P<mode>\S+)'
)

DETECTING_DEVICE_PATTERN = re.compile(r'\bdetecting device\b', re.IGNORECASE)
GENERIC_DEVICE_DETECTED_PATTERN = re.compile(r'\bdevice detected\b', re.IGNORECASE)
DEVICE_ID_PATTERN = re.compile(r'device_id=(?P<device_id>\S+)', re.IGNORECASE)
PRODUCT_CODE_PATTERN = re.compile(r'product_code=(?P<product_code>\S+)', re.IGNORECASE)
MODE_PATTERN = re.compile(r'mode=(?P<mode>\S+)', re.IGNORECASE)
PRODUCT_HINT_PATTERN = re.compile(r'\bSM[-_][A-Z0-9]+\b', re.IGNORECASE)

DETECT_PRESENCE_PATTERNS = (
  re.compile(r'\bclaim(?:ing)? interface\b', re.IGNORECASE),
  re.compile(r'\binterface claim successful\b', re.IGNORECASE),
  re.compile(r'\bsetting up interface\b', re.IGNORECASE),
  re.compile(r'\binitialising protocol\b', re.IGNORECASE),
  re.compile(r'\bprotocol initialisation successful\b', re.IGNORECASE),
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

  payload = _detect_payload(process_result)
  if payload is not None:
    events.append(PlatformEvent(SessionEventType.DEVICE_CONNECTED, payload))
    later_runtime_warning = process_result.exit_code not in command_plan.expected_exit_codes
    if payload.get('product_code'):
      if later_runtime_warning:
        notes.append(
          'Samsung download-mode presence was verified through Heimdall before a later transport warning interrupted the detect command.'
        )
        summary = (
          'Heimdall verified Samsung download-mode presence and normalized device identity before a later transport warning interrupted the probe.'
        )
      else:
        notes.append('Samsung download-mode device detected through Heimdall.')
        summary = 'Heimdall detected a Samsung device and normalized it into platform identity.'
    else:
      if later_runtime_warning:
        notes.append(
          'Samsung download-mode presence was verified through Heimdall from transport handshake output, but product identity remained incomplete and the probe later reported a transport warning.'
        )
        summary = (
          'Heimdall verified Samsung download-mode presence from transport handshake output, but product identity remained incomplete and the probe later reported a transport warning.'
        )
      else:
        notes.append(
          'Samsung download-mode device detected through Heimdall, but product identity remained incomplete.'
        )
        summary = 'Heimdall detected a Samsung download-mode device, but product identity remained incomplete.'
    if later_runtime_warning:
      notes.append(_failure_reason(process_result))
    return HeimdallNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=HeimdallTraceState.DETECTED,
      summary=summary,
      exit_code=process_result.exit_code,
      platform_events=tuple(events),
      notes=tuple(notes),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  classification = _detect_failure_classification(process_result)
  reason = _failure_reason(process_result)
  summary = 'Heimdall device detection did not produce a trustworthy identity result.'
  if classification == 'no_device':
    summary = 'Heimdall did not detect a Samsung download-mode device.'
  elif classification == 'runtime_failure':
    summary = 'Heimdall device detection failed before the platform could verify Samsung download-mode presence.'
  elif classification == 'unparsed_output':
    summary = 'Heimdall reached detect output but the platform could not normalize a trustworthy Samsung download-mode identity.'
    notes.append(
      'Review raw Heimdall stdout/stderr because detect output did not match a trusted parser shape.'
    )
  notes.append(reason)
  return HeimdallNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=HeimdallTraceState.FAILED,
    summary=summary,
    exit_code=process_result.exit_code,
    platform_events=(),
    notes=tuple(notes),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _detect_payload(
  process_result: HeimdallProcessResult,
) -> Optional[Dict[str, str]]:
  """Return a normalized detect payload when Heimdall clearly reached a device."""

  combined_lines = process_result.stdout_lines + process_result.stderr_lines
  combined_text = '\n'.join(combined_lines)

  for line in combined_lines:
    match = DEVICE_PATTERN.search(line)
    if match is None:
      continue
    return {
      'device_id': match.group('device_id'),
      'product_code': _normalized_product_code(match.group('product_code')),
      'mode': match.group('mode').lower(),
    }

  if not _detect_output_implies_presence(combined_text):
    return None

  device_id_match = DEVICE_ID_PATTERN.search(combined_text)
  product_code_match = PRODUCT_CODE_PATTERN.search(combined_text)
  mode_match = MODE_PATTERN.search(combined_text)
  hinted_product_code = _hinted_product_code(combined_text)
  payload = {
    'device_id': (
      device_id_match.group('device_id')
      if device_id_match is not None
      else 'download-mode-device'
    ),
    'mode': (
      mode_match.group('mode').lower()
      if mode_match is not None
      else 'download'
    ),
  }
  if product_code_match is not None:
    payload['product_code'] = _normalized_product_code(
      product_code_match.group('product_code')
    )
  elif hinted_product_code is not None:
    payload['product_code'] = hinted_product_code
  return payload


def _detect_output_implies_presence(combined_text: str) -> bool:
  """Return whether detect output shows Samsung download-mode presence."""

  if GENERIC_DEVICE_DETECTED_PATTERN.search(combined_text) is not None:
    return True
  if DETECTING_DEVICE_PATTERN.search(combined_text) is None:
    return False
  return any(pattern.search(combined_text) is not None for pattern in DETECT_PRESENCE_PATTERNS)


def _hinted_product_code(combined_text: str) -> Optional[str]:
  """Return one best-effort Samsung product code hinted in raw detect output."""

  product_code_match = PRODUCT_HINT_PATTERN.search(combined_text)
  if product_code_match is None:
    return None
  return _normalized_product_code(product_code_match.group(0))


def _normalized_product_code(value: str) -> str:
  """Normalize one hinted product code into the canonical display form."""

  return value.strip().replace('_', '-').upper()


def _detect_failure_classification(
  process_result: HeimdallProcessResult,
) -> str:
  """Classify detect failures into no-device, runtime, or unparsed output."""

  combined = ' '.join(process_result.stdout_lines + process_result.stderr_lines).lower()
  if any(
    token in combined
    for token in (
      'failed to detect compatible download-mode device',
      'no download-mode device',
      'no compatible download-mode device',
      'no device detected',
    )
  ):
    return 'no_device'
  if process_result.exit_code in (124, 127):
    return 'runtime_failure'
  if any(
    token in combined
    for token in (
      'not available on path',
      'executable',
      'timed out',
      'timeout',
      'access denied',
      'permission denied',
      'driver',
      'unable to open usb device',
      'usb transfer',
      'failed to claim interface',
    )
  ):
    return 'runtime_failure'
  if combined.strip():
    return 'unparsed_output'
  return 'runtime_failure'


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
