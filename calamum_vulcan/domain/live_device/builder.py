"""Builders that normalize adapter traces into repo-owned live-device truth."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.adb_fastboot import AndroidDeviceRecord
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsNormalizedTrace
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsTraceState
from calamum_vulcan.domain.device_registry import resolve_device_profile

from .model import LiveDetectionSession
from .model import LiveDetectionState
from .model import LiveDeviceInfoState
from .model import LiveDeviceSnapshot
from .model import LiveDeviceSource
from .model import LiveDeviceSupportPosture
from .model import LiveFallbackPosture


def build_live_detection_session(
  trace: AndroidToolsNormalizedTrace,
  fallback_posture: LiveFallbackPosture = LiveFallbackPosture.NOT_NEEDED,
  fallback_reason: Optional[str] = None,
  source_labels: Optional[Tuple[str, ...]] = None,
) -> LiveDetectionSession:
  """Normalize one adapter trace into repo-owned live-detection truth."""

  source = LiveDeviceSource(trace.command_plan.backend.value)
  considered_sources = source_labels or (source.value,)

  if trace.state == AndroidToolsTraceState.FAILED:
    return LiveDetectionSession(
      state=LiveDetectionState.FAILED,
      summary=_compose_summary(
        trace.summary,
        fallback_posture,
        fallback_reason,
      ),
      source=source,
      source_labels=considered_sources,
      fallback_posture=fallback_posture,
      fallback_reason=fallback_reason,
      notes=_detection_notes(
        trace.notes,
        fallback_posture,
        fallback_reason,
      ),
    )

  if not trace.detected_devices:
    return LiveDetectionSession(
      state=LiveDetectionState.CLEARED,
      summary=_compose_summary(
        trace.summary,
        fallback_posture,
        fallback_reason,
      ),
      source=source,
      source_labels=considered_sources,
      fallback_posture=fallback_posture,
      fallback_reason=fallback_reason,
      notes=_detection_notes(
        trace.notes,
        fallback_posture,
        fallback_reason,
      ),
    )

  selected_device = _select_active_device(trace.detected_devices, source)
  snapshot = _build_snapshot(selected_device, source)
  detection_state = LiveDetectionState.DETECTED
  if not snapshot.command_ready:
    detection_state = LiveDetectionState.ATTENTION

  return LiveDetectionSession(
    state=detection_state,
    summary=_compose_summary(
      trace.summary,
      fallback_posture,
      fallback_reason,
      snapshot,
      detection_state,
    ),
    source=source,
    source_labels=considered_sources,
    fallback_posture=fallback_posture,
    fallback_reason=fallback_reason,
    snapshot=snapshot,
    notes=_detection_notes(
      trace.notes,
      fallback_posture,
      fallback_reason,
      snapshot,
      detection_state,
    ),
  )


def _select_active_device(
  devices: Tuple[AndroidDeviceRecord, ...],
  source: LiveDeviceSource,
) -> AndroidDeviceRecord:
  for device in devices:
    if _command_ready(device, source):
      return device
  return devices[0]


def _build_snapshot(
  device: AndroidDeviceRecord,
  source: LiveDeviceSource,
) -> LiveDeviceSnapshot:
  product_code = device.model or device.product
  resolution = resolve_device_profile(product_code)
  support_posture = LiveDeviceSupportPosture.IDENTITY_INCOMPLETE
  registry_match_kind = 'unknown'
  canonical_product_code = None
  marketing_name = None

  if product_code is not None:
    registry_match_kind = resolution.match_kind.value
    canonical_product_code = resolution.canonical_product_code
    marketing_name = resolution.marketing_name
    if resolution.known:
      support_posture = LiveDeviceSupportPosture.SUPPORTED
    else:
      support_posture = LiveDeviceSupportPosture.UNPROFILED

  info_state = _initial_info_state(source, device.state)

  return LiveDeviceSnapshot(
    source=source,
    serial=device.serial,
    connection_state=device.state,
    transport=device.transport,
    mode='{source}/{state}'.format(
      source=source.value,
      state=device.state,
    ),
    command_ready=_command_ready(device, source),
    product_code=product_code,
    model_name=device.model,
    device_name=device.device,
    canonical_product_code=canonical_product_code,
    marketing_name=marketing_name,
    registry_match_kind=registry_match_kind,
    support_posture=support_posture,
    info_state=info_state,
    capability_hints=_capability_hints(
      source,
      _command_ready(device, source),
      support_posture,
      info_state,
    ),
    operator_guidance=_operator_guidance(
      source,
      _command_ready(device, source),
      support_posture,
      info_state,
    ),
  )


def apply_live_device_info_trace(
  detection: LiveDetectionSession,
  trace: AndroidToolsNormalizedTrace,
) -> LiveDetectionSession:
  """Apply one bounded info-gather trace to an existing live-detection session."""

  snapshot = detection.snapshot
  if snapshot is None:
    return detection
  if trace.command_plan.operation != AndroidToolsOperation.ADB_GETPROP:
    raise ValueError('Live device info traces must come from the bounded ADB getprop command.')

  info_state = LiveDeviceInfoState.CAPTURED
  observed_properties = trace.observed_properties
  if trace.state == AndroidToolsTraceState.FAILED:
    info_state = LiveDeviceInfoState.FAILED
  elif not observed_properties:
    info_state = LiveDeviceInfoState.PARTIAL

  manufacturer = _first_nonblank(
    observed_properties,
    'ro.product.manufacturer',
    'ro.product.vendor.manufacturer',
  )
  brand = _first_nonblank(
    observed_properties,
    'ro.product.brand',
    'ro.product.vendor.brand',
  )
  model_name = _first_nonblank(observed_properties, 'ro.product.model') or snapshot.model_name
  device_name = _first_nonblank(
    observed_properties,
    'ro.product.device',
    'ro.product.vendor.device',
  ) or snapshot.device_name
  android_version = _first_nonblank(observed_properties, 'ro.build.version.release')
  build_id = _first_nonblank(observed_properties, 'ro.build.id')
  security_patch = _first_nonblank(observed_properties, 'ro.build.version.security_patch')
  build_fingerprint = _first_nonblank(observed_properties, 'ro.build.fingerprint')
  bootloader_version = _first_nonblank(observed_properties, 'ro.bootloader')
  build_tags = _first_nonblank(observed_properties, 'ro.build.tags')

  if trace.state != AndroidToolsTraceState.FAILED:
    populated_core_fields = sum(
      1
      for value in (
        manufacturer,
        brand,
        android_version,
        build_id,
        build_fingerprint,
      )
      if value is not None
    )
    if populated_core_fields < 3:
      info_state = LiveDeviceInfoState.PARTIAL

  updated_snapshot = replace(
    snapshot,
    model_name=model_name,
    device_name=device_name,
    info_state=info_state,
    info_source_label='adb_getprop',
    manufacturer=manufacturer,
    brand=brand,
    android_version=android_version,
    build_id=build_id,
    security_patch=security_patch,
    build_fingerprint=build_fingerprint,
    bootloader_version=bootloader_version,
    build_tags=build_tags,
    capability_hints=_capability_hints(
      snapshot.source,
      snapshot.command_ready,
      snapshot.support_posture,
      info_state,
    ),
    operator_guidance=_operator_guidance(
      snapshot.source,
      snapshot.command_ready,
      snapshot.support_posture,
      info_state,
    ),
  )
  return replace(
    detection,
    snapshot=updated_snapshot,
    notes=_merge_detection_notes(detection.notes, trace.notes, updated_snapshot, info_state),
  )


def _command_ready(
  device: AndroidDeviceRecord,
  source: LiveDeviceSource,
) -> bool:
  if source == LiveDeviceSource.ADB:
    return device.state == 'device'
  return device.state == 'fastboot'


def _initial_info_state(
  source: LiveDeviceSource,
  connection_state: str,
) -> LiveDeviceInfoState:
  if source == LiveDeviceSource.ADB and connection_state == 'device':
    return LiveDeviceInfoState.NOT_COLLECTED
  return LiveDeviceInfoState.UNAVAILABLE


def _compose_summary(
  summary: str,
  fallback_posture: LiveFallbackPosture,
  fallback_reason: Optional[str],
  snapshot: Optional[LiveDeviceSnapshot] = None,
  detection_state: Optional[LiveDetectionState] = None,
) -> str:
  parts = [summary]
  if detection_state == LiveDetectionState.ATTENTION:
    parts.append(
      'Operator attention is still required before the live device can be treated as command-ready.'
    )
  if snapshot is not None:
    if snapshot.support_posture == LiveDeviceSupportPosture.UNPROFILED:
      parts.append(
        'The detected product code is not yet represented in the repo-owned device registry.'
      )
    elif snapshot.support_posture == LiveDeviceSupportPosture.IDENTITY_INCOMPLETE:
      parts.append(
        'The active source did not provide enough identity to resolve a repo-owned device profile.'
      )
  if fallback_posture == LiveFallbackPosture.NEEDED:
    parts.append('Fastboot fallback is recommended.')
  elif fallback_posture == LiveFallbackPosture.ENGAGED:
    parts.append('Fallback detection was engaged.')
  if fallback_reason:
    parts.append(fallback_reason)
  return ' '.join(parts)


def _detection_notes(
  notes: Tuple[str, ...],
  fallback_posture: LiveFallbackPosture,
  fallback_reason: Optional[str],
  snapshot: Optional[LiveDeviceSnapshot] = None,
  detection_state: Optional[LiveDetectionState] = None,
) -> Tuple[str, ...]:
  collected = list(notes)
  if detection_state == LiveDetectionState.ATTENTION:
    collected.append(
      'Live device presence is real, but command-ready control is not yet established.'
    )
  if snapshot is not None:
    if snapshot.support_posture == LiveDeviceSupportPosture.UNPROFILED:
      collected.append(
        'Add a repo-owned device profile before trusting compatibility resolution.'
      )
    elif snapshot.support_posture == LiveDeviceSupportPosture.IDENTITY_INCOMPLETE:
      collected.append(
        'Live identity is incomplete because the current source did not provide a product code.'
      )
  if fallback_posture == LiveFallbackPosture.NEEDED:
    collected.append('Fallback posture: fastboot should be checked next.')
  elif fallback_posture == LiveFallbackPosture.ENGAGED:
    collected.append('Fallback posture: fastboot was used after the first source did not establish a device.')
  if fallback_reason:
    collected.append(fallback_reason)
  return tuple(_dedupe_preserve_order(collected))


def _dedupe_preserve_order(values: Tuple[str, ...] | list[str]) -> Tuple[str, ...]:
  ordered = []
  for value in values:
    if value not in ordered:
      ordered.append(value)
  return tuple(ordered)


def _first_nonblank(
  values: dict[str, str],
  *keys: str,
) -> Optional[str]:
  for key in keys:
    value = values.get(key)
    if value is not None and str(value).strip():
      return str(value).strip()
  return None


def _capability_hints(
  source: LiveDeviceSource,
  command_ready: bool,
  support_posture: LiveDeviceSupportPosture,
  info_state: LiveDeviceInfoState,
) -> Tuple[str, ...]:
  hints = []  # type: list[str]
  if source == LiveDeviceSource.ADB:
    hints.append('adb_detect')
    if command_ready:
      hints.extend(
        (
          'adb_reboot',
          'adb_read_props',
          'vendor_download_reboot',
        )
      )
    else:
      hints.append('adb_authorization_required')
  else:
    hints.extend(
      (
        'fastboot_detect',
        'fastboot_reboot',
        'adb_required_for_richer_info',
      )
    )

  if support_posture == LiveDeviceSupportPosture.SUPPORTED:
    hints.append('repo_profile_available')
  elif support_posture == LiveDeviceSupportPosture.UNPROFILED:
    hints.append('repo_profile_missing')
  else:
    hints.append('identity_incomplete')

  if info_state == LiveDeviceInfoState.CAPTURED:
    hints.append('bounded_info_snapshot_ready')
  elif info_state == LiveDeviceInfoState.PARTIAL:
    hints.append('bounded_info_snapshot_partial')
  elif info_state == LiveDeviceInfoState.FAILED:
    hints.append('bounded_info_snapshot_failed')
  elif info_state == LiveDeviceInfoState.UNAVAILABLE:
    hints.append('bounded_info_snapshot_unavailable')
  return _dedupe_preserve_order(hints)


def _operator_guidance(
  source: LiveDeviceSource,
  command_ready: bool,
  support_posture: LiveDeviceSupportPosture,
  info_state: LiveDeviceInfoState,
) -> Tuple[str, ...]:
  guidance = [
    'Treat live device info and capability hints as read-side guidance only; they do not imply flash readiness.',
  ]
  if source == LiveDeviceSource.ADB and not command_ready:
    guidance.append('Authorize the ADB session before expecting shell-derived device info or reboot controls.')
  if source == LiveDeviceSource.FASTBOOT:
    guidance.append('Fastboot currently exposes only limited read-side identity; richer device info still requires a command-ready ADB session.')
  if info_state == LiveDeviceInfoState.CAPTURED:
    guidance.append('Bounded ADB properties were captured successfully for the active live device.')
  elif info_state == LiveDeviceInfoState.PARTIAL:
    guidance.append('Some bounded device-info fields are missing; keep support and compatibility claims narrow.')
  elif info_state == LiveDeviceInfoState.FAILED:
    guidance.append('The bounded ADB property probe failed; re-run detection after confirming adb access and device stability.')
  elif info_state == LiveDeviceInfoState.UNAVAILABLE:
    guidance.append('A richer info snapshot is not available from the current live source/state yet.')
  elif info_state == LiveDeviceInfoState.NOT_COLLECTED:
    guidance.append('A command-ready ADB session can be enriched with a bounded property probe for additional device facts.')

  if support_posture == LiveDeviceSupportPosture.UNPROFILED:
    guidance.append('Add a repo-owned device profile before trusting compatibility conclusions for this product code.')
  elif support_posture == LiveDeviceSupportPosture.IDENTITY_INCOMPLETE:
    guidance.append('Resolve product identity before treating this live session as a profiled supported device.')
  return _dedupe_preserve_order(guidance)


def _merge_detection_notes(
  existing_notes: Tuple[str, ...],
  trace_notes: Tuple[str, ...],
  snapshot: LiveDeviceSnapshot,
  info_state: LiveDeviceInfoState,
) -> Tuple[str, ...]:
  notes = list(existing_notes)
  notes.extend(trace_notes)
  if info_state == LiveDeviceInfoState.CAPTURED:
    notes.append('Bounded live device info was captured successfully through ADB getprop.')
  elif info_state == LiveDeviceInfoState.PARTIAL:
    notes.append('Bounded live device info was only partially captured through ADB getprop.')
  elif info_state == LiveDeviceInfoState.FAILED:
    notes.append('Bounded live device info collection failed after the device was detected.')
  if snapshot.manufacturer is not None:
    notes.append('Manufacturer: {manufacturer}'.format(manufacturer=snapshot.manufacturer))
  if snapshot.android_version is not None:
    notes.append('Android version: {version}'.format(version=snapshot.android_version))
  return _dedupe_preserve_order(notes)
