"""Normalize ADB/Fastboot process output into platform-owned companion traces."""

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Tuple

from .model import AndroidDeviceRecord
from .model import AndroidToolsBackend
from .model import AndroidToolsCommandPlan
from .model import AndroidToolsNormalizedTrace
from .model import AndroidToolsOperation
from .model import AndroidToolsProcessResult
from .model import AndroidToolsTraceState


def normalize_android_tools_result(
  command_plan: AndroidToolsCommandPlan,
  process_result: AndroidToolsProcessResult,
) -> AndroidToolsNormalizedTrace:
  """Normalize one live or mocked platform-tools result."""

  operation = process_result.operation
  if operation == AndroidToolsOperation.ADB_DEVICES:
    return _normalize_adb_devices_result(command_plan, process_result)
  if operation == AndroidToolsOperation.FASTBOOT_DEVICES:
    return _normalize_fastboot_devices_result(command_plan, process_result)
  return _normalize_reboot_result(command_plan, process_result)


def _normalize_adb_devices_result(
  command_plan: AndroidToolsCommandPlan,
  process_result: AndroidToolsProcessResult,
) -> AndroidToolsNormalizedTrace:
  if process_result.exit_code not in command_plan.expected_exit_codes:
    return _failed_trace(
      command_plan,
      process_result,
      'ADB device detection failed before a trustworthy device list was produced.',
    )

  devices = _parse_adb_devices(process_result.stdout_lines)
  if not devices:
    return AndroidToolsNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=AndroidToolsTraceState.NO_DEVICES,
      summary='ADB did not report any connected devices.',
      exit_code=process_result.exit_code,
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  ready_count = sum(1 for device in devices if device.state == 'device')
  notes = []  # type: List[str]
  if ready_count == 0:
    notes.append('ADB reported devices, but none are command-ready yet.')
  for device in devices:
    if device.state != 'device':
      notes.append(
        'Device {serial} is present in adb with state={state}.'.format(
          serial=device.serial,
          state=device.state,
        )
      )
  summary = 'ADB detected {count} device(s); {ready} command-ready.'.format(
    count=len(devices),
    ready=ready_count,
  )
  return AndroidToolsNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=AndroidToolsTraceState.DETECTED,
    summary=summary,
    exit_code=process_result.exit_code,
    detected_devices=tuple(devices),
    notes=tuple(notes),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _normalize_fastboot_devices_result(
  command_plan: AndroidToolsCommandPlan,
  process_result: AndroidToolsProcessResult,
) -> AndroidToolsNormalizedTrace:
  if process_result.exit_code not in command_plan.expected_exit_codes:
    return _failed_trace(
      command_plan,
      process_result,
      'Fastboot detection failed before a trustworthy device list was produced.',
    )

  devices = _parse_fastboot_devices(process_result.stdout_lines)
  if not devices:
    return AndroidToolsNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=AndroidToolsTraceState.NO_DEVICES,
      summary='Fastboot did not report any connected devices.',
      exit_code=process_result.exit_code,
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  return AndroidToolsNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=AndroidToolsTraceState.DETECTED,
    summary='Fastboot detected {count} device(s).'.format(count=len(devices)),
    exit_code=process_result.exit_code,
    detected_devices=tuple(devices),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _normalize_reboot_result(
  command_plan: AndroidToolsCommandPlan,
  process_result: AndroidToolsProcessResult,
) -> AndroidToolsNormalizedTrace:
  target = command_plan.reboot_target or 'system'
  notes = list(command_plan.notes)
  if process_result.exit_code in command_plan.expected_exit_codes:
    summary = '{backend} reboot command accepted for target {target}.'.format(
      backend=command_plan.backend.value.upper(),
      target=target,
    )
    return AndroidToolsNormalizedTrace(
      fixture_name=process_result.fixture_name,
      command_plan=command_plan,
      state=AndroidToolsTraceState.COMPLETED,
      summary=summary,
      exit_code=process_result.exit_code,
      notes=tuple(notes),
      stdout_lines=process_result.stdout_lines,
      stderr_lines=process_result.stderr_lines,
    )

  failure_reason = _failure_reason(process_result)
  notes.append(failure_reason)
  return AndroidToolsNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=AndroidToolsTraceState.FAILED,
    summary='{backend} reboot command failed for target {target}.'.format(
      backend=command_plan.backend.value.upper(),
      target=target,
    ),
    exit_code=process_result.exit_code,
    notes=tuple(notes),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _failed_trace(
  command_plan: AndroidToolsCommandPlan,
  process_result: AndroidToolsProcessResult,
  summary: str,
) -> AndroidToolsNormalizedTrace:
  return AndroidToolsNormalizedTrace(
    fixture_name=process_result.fixture_name,
    command_plan=command_plan,
    state=AndroidToolsTraceState.FAILED,
    summary=summary,
    exit_code=process_result.exit_code,
    notes=(_failure_reason(process_result),),
    stdout_lines=process_result.stdout_lines,
    stderr_lines=process_result.stderr_lines,
  )


def _parse_adb_devices(stdout_lines: tuple[str, ...]) -> Tuple[AndroidDeviceRecord, ...]:
  devices = []  # type: List[AndroidDeviceRecord]
  for line in stdout_lines:
    stripped = line.strip()
    if not stripped:
      continue
    if stripped.startswith('List of devices attached'):
      continue
    if stripped.startswith('* daemon '):
      continue
    parts = stripped.split()
    if len(parts) < 2:
      continue
    serial = parts[0]
    state = parts[1]
    detail_map = _parse_key_value_tokens(parts[2:])
    transport = 'usb'
    if ':' in serial:
      transport = 'tcpip'
    elif 'usb' not in detail_map:
      transport = 'unknown'
    devices.append(
      AndroidDeviceRecord(
        serial=serial,
        state=state,
        transport=transport,
        product=detail_map.get('product'),
        model=detail_map.get('model'),
        device=detail_map.get('device'),
      )
    )
  return tuple(devices)


def _parse_fastboot_devices(
  stdout_lines: tuple[str, ...],
) -> Tuple[AndroidDeviceRecord, ...]:
  devices = []  # type: List[AndroidDeviceRecord]
  for line in stdout_lines:
    stripped = line.strip()
    if not stripped:
      continue
    parts = stripped.split()
    if len(parts) < 2:
      continue
    devices.append(
      AndroidDeviceRecord(
        serial=parts[0],
        state=parts[1],
        transport='usb',
      )
    )
  return tuple(devices)


def _parse_key_value_tokens(tokens: List[str]) -> Dict[str, str]:
  details = {}  # type: Dict[str, str]
  for token in tokens:
    if ':' not in token:
      continue
    key, value = token.split(':', 1)
    details[key] = value
  return details


def _failure_reason(process_result: AndroidToolsProcessResult) -> str:
  if process_result.stderr_lines:
    return process_result.stderr_lines[0]
  for line in process_result.stdout_lines:
    if 'error' in line.lower() or 'failed' in line.lower():
      return line
  if process_result.backend == AndroidToolsBackend.ADB:
    return 'ADB process exited unexpectedly without a normalized reason.'
  return 'Fastboot process exited unexpectedly without a normalized reason.'