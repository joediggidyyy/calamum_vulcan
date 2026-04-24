"""Builders that normalize adapter traces into repo-owned live-device truth."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.adb_fastboot import AndroidDeviceRecord
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsNormalizedTrace
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsTraceState
from calamum_vulcan.adapters.heimdall.model import HeimdallNormalizedTrace
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.usb import USBProbeResult

from .model import LiveDetectionSession
from .model import LiveDetectionState
from .model import LiveDeviceInfoState
from .model import LiveIdentityConfidence
from .model import LivePathIdentity
from .model import LivePathOwnership
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
      path_identity=_build_path_identity(
        source,
        fallback_posture,
        fallback_reason,
        detection_state=LiveDetectionState.FAILED,
      ),
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
      path_identity=_build_path_identity(
        source,
        fallback_posture,
        fallback_reason,
        detection_state=LiveDetectionState.CLEARED,
      ),
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
    path_identity=_build_path_identity(
      source,
      fallback_posture,
      fallback_reason,
      snapshot=snapshot,
      detection_state=detection_state,
    ),
    notes=_detection_notes(
      trace.notes,
      fallback_posture,
      fallback_reason,
      snapshot,
      detection_state,
    ),
  )


def build_heimdall_live_detection_session(
  trace: HeimdallNormalizedTrace,
  source_labels: Optional[Tuple[str, ...]] = None,
  treat_missing_device_as_cleared: bool = False,
) -> LiveDetectionSession:
  """Normalize one Heimdall detect trace into repo-owned live-detection truth."""

  source = LiveDeviceSource.HEIMDALL
  considered_sources = source_labels or (source.value,)
  payload = _first_heimdall_device_payload(trace)
  detect_classification = _heimdall_detect_classification(trace)

  if payload is None:
    detection_state = LiveDetectionState.FAILED
    summary = trace.summary
    if treat_missing_device_as_cleared and detect_classification == 'no_device':
      detection_state = LiveDetectionState.CLEARED
      summary = _heimdall_cleared_summary(considered_sources)
    return LiveDetectionSession(
      state=detection_state,
      summary=summary,
      source=source,
      source_labels=considered_sources,
      path_identity=_build_path_identity(
        source,
        LiveFallbackPosture.NOT_NEEDED,
        None,
        detection_state=detection_state,
      ),
      notes=_detection_notes(
        trace.notes,
        LiveFallbackPosture.NOT_NEEDED,
        None,
        detection_state=detection_state,
      ),
    )

  snapshot = _build_heimdall_snapshot(payload)
  detection_state = LiveDetectionState.DETECTED
  if not snapshot.command_ready or _heimdall_runtime_failure(trace):
    detection_state = LiveDetectionState.ATTENTION

  return LiveDetectionSession(
    state=detection_state,
    summary=_compose_summary(
      trace.summary,
      LiveFallbackPosture.NOT_NEEDED,
      None,
      snapshot,
      detection_state,
    ),
    source=source,
    source_labels=considered_sources,
    snapshot=snapshot,
    path_identity=_build_path_identity(
      source,
      LiveFallbackPosture.NOT_NEEDED,
      None,
      snapshot=snapshot,
      detection_state=detection_state,
    ),
    notes=_detection_notes(
      trace.notes,
      LiveFallbackPosture.NOT_NEEDED,
      None,
      snapshot,
      detection_state,
    ),
  )


def build_usb_live_detection_session(
  probe_result: USBProbeResult,
  source_labels: Optional[Tuple[str, ...]] = None,
) -> LiveDetectionSession:
  """Normalize one native USB probe result into live-device truth."""

  source = LiveDeviceSource.USB
  considered_sources = source_labels or (source.value,)

  if not probe_result.devices:
    detection_state = LiveDetectionState.FAILED
    if probe_result.state == 'cleared':
      detection_state = LiveDetectionState.CLEARED
    next_operator_action = _usb_probe_next_action(
      probe_result,
      detection_state,
    )
    return LiveDetectionSession(
      state=detection_state,
      summary=probe_result.summary,
      source=source,
      source_labels=considered_sources,
      path_identity=_build_path_identity(
        source,
        LiveFallbackPosture.NOT_NEEDED,
        None,
        detection_state=detection_state,
      ),
      notes=_detection_notes(
        probe_result.notes,
        LiveFallbackPosture.NOT_NEEDED,
        None,
        detection_state=detection_state,
        extra_notes=_usb_probe_extra_notes(
          probe_result,
          next_operator_action,
        ),
      ),
    )

  snapshot = _build_usb_snapshot(probe_result.devices[0])
  detection_state = LiveDetectionState.DETECTED
  if probe_result.state == 'attention' or not snapshot.command_ready:
    detection_state = LiveDetectionState.ATTENTION
  next_operator_action = _usb_probe_next_action(
    probe_result,
    detection_state,
    snapshot=snapshot,
  )

  return LiveDetectionSession(
    state=detection_state,
    summary=_compose_summary(
      probe_result.summary,
      LiveFallbackPosture.NOT_NEEDED,
      None,
      snapshot,
      detection_state,
    ),
    source=source,
    source_labels=considered_sources,
    snapshot=snapshot,
    path_identity=_build_path_identity(
      source,
      LiveFallbackPosture.NOT_NEEDED,
      None,
      snapshot=snapshot,
      detection_state=detection_state,
    ),
    notes=_detection_notes(
      probe_result.notes,
      LiveFallbackPosture.NOT_NEEDED,
      None,
      snapshot,
      detection_state,
      extra_notes=_usb_probe_extra_notes(
        probe_result,
        next_operator_action,
      ),
    ),
  )


def _usb_probe_next_action(
  probe_result: USBProbeResult,
  detection_state: LiveDetectionState,
  snapshot: Optional[LiveDeviceSnapshot] = None,
) -> Optional[str]:
  """Return the primary operator next step for one native USB probe."""

  if probe_result.remediation_command is not None:
    return 'Allow the packaged USB remediation helper to finish, then rerun Detect device.'
  if (
    detection_state == LiveDetectionState.DETECTED
    and snapshot is not None
    and snapshot.support_posture == LiveDeviceSupportPosture.IDENTITY_INCOMPLETE
  ):
    return 'Run Read PIT next to gather bounded partition truth and narrow the active device identity.'
  if detection_state == LiveDetectionState.ATTENTION:
    if snapshot is not None and snapshot.support_posture == LiveDeviceSupportPosture.IDENTITY_INCOMPLETE:
      return 'Confirm the direct USB access path so product identity can be read, then rerun Detect device.'
    return 'Confirm the USB access path, then rerun Detect device so the download-mode session can become command-ready.'
  if detection_state == LiveDetectionState.FAILED:
    return 'Confirm the native USB backend and access path, then rerun Detect device.'
  if detection_state == LiveDetectionState.CLEARED:
    return 'Reconnect the device in Samsung download mode, then rerun Detect device.'
  return None


def _usb_probe_extra_notes(
  probe_result: USBProbeResult,
  next_operator_action: Optional[str],
) -> Tuple[str, ...]:
  """Return remediation-first notes for one native USB probe result."""

  notes = []  # type: list[str]
  if probe_result.remediation_command is not None:
    notes.append(
      'Self-heal attempted: {command}'.format(
        command=probe_result.remediation_command,
      )
    )
  if next_operator_action is not None:
    notes.append('Next step: {action}'.format(action=next_operator_action))
  return tuple(notes)


def _first_heimdall_device_payload(
  trace: HeimdallNormalizedTrace,
) -> Optional[dict[str, object]]:
  for event in trace.platform_events:
    event_type = getattr(event.event_type, 'value', str(event.event_type))
    if event_type != 'device_connected':
      continue
    payload = getattr(event, 'payload', None)
    if isinstance(payload, dict):
      return payload
    if payload is not None and hasattr(payload, 'items'):
      return dict(payload)
  return None


def _build_heimdall_snapshot(
  payload: dict[str, object],
) -> LiveDeviceSnapshot:
  source = LiveDeviceSource.HEIMDALL
  serial = _string_payload_value(payload, 'device_id') or 'download-mode-device'
  connection_state = _string_payload_value(payload, 'mode') or 'download'
  product_code = _string_payload_value(payload, 'product_code')
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

  command_ready = connection_state == 'download'
  info_state = LiveDeviceInfoState.UNAVAILABLE
  return LiveDeviceSnapshot(
    source=source,
    serial=serial,
    connection_state=connection_state,
    transport='download-mode',
    mode='{source}/{state}'.format(
      source=source.value,
      state=connection_state,
    ),
    command_ready=command_ready,
    product_code=product_code,
    canonical_product_code=canonical_product_code,
    marketing_name=marketing_name,
    registry_match_kind=registry_match_kind,
    support_posture=support_posture,
    info_state=info_state,
    capability_hints=_capability_hints(
      source,
      command_ready,
      support_posture,
      info_state,
    ),
    operator_guidance=_operator_guidance(
      source,
      command_ready,
      support_posture,
      info_state,
    ),
  )


def _build_usb_snapshot(device) -> LiveDeviceSnapshot:
  source = LiveDeviceSource.USB
  product_code = getattr(device, 'product_code', None)
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

  info_state = LiveDeviceInfoState.UNAVAILABLE
  return LiveDeviceSnapshot(
    source=source,
    serial=getattr(device, 'serial_number', 'download-mode-device'),
    connection_state='download',
    transport='download-mode',
    mode='usb/download',
    command_ready=bool(getattr(device, 'command_ready', True)),
    product_code=product_code,
    model_name=(getattr(device, 'product_name', None) if product_code is not None else None),
    canonical_product_code=canonical_product_code,
    marketing_name=marketing_name,
    registry_match_kind=registry_match_kind,
    support_posture=support_posture,
    info_state=info_state,
    manufacturer=getattr(device, 'manufacturer', None),
    brand=getattr(device, 'manufacturer', None),
    capability_hints=_capability_hints(
      source,
      bool(getattr(device, 'command_ready', True)),
      support_posture,
      info_state,
    ),
    operator_guidance=_operator_guidance(
      source,
      bool(getattr(device, 'command_ready', True)),
      support_posture,
      info_state,
    ),
  )


def _heimdall_runtime_failure(trace: HeimdallNormalizedTrace) -> bool:
  classification = _heimdall_detect_classification(trace)
  if classification == 'runtime_failure':
    return True
  if classification == 'no_device':
    return False
  if trace.exit_code in (124, 127):
    return True
  combined = ' '.join(trace.notes + trace.stderr_lines).lower()
  for token in (
    'executable',
    'not available on path',
    'timed out',
    'timeout',
    'access denied',
    'permission denied',
    'driver',
    'failed to claim interface',
    'failed to receive handshake response',
    'protocol initialisation failed',
    'transport warning',
  ):
    if token in combined:
      return True
  return False


def _heimdall_detect_classification(trace: HeimdallNormalizedTrace) -> str:
  """Return the detect classification inferred from the normalized trace summary."""

  summary = trace.summary.lower()
  if summary.startswith('heimdall did not detect a samsung download-mode device'):
    return 'no_device'
  if 'could not normalize a trustworthy samsung download-mode identity' in summary:
    return 'unparsed_output'
  if 'failed before the platform could verify samsung download-mode presence' in summary:
    return 'runtime_failure'
  return 'detected'


def _heimdall_cleared_summary(source_labels: Tuple[str, ...]) -> str:
  normalized_labels = tuple(label.lower() for label in source_labels)
  if normalized_labels == ('adb', 'fastboot', 'heimdall'):
    return 'No live device detected after checking ADB, fastboot, and Heimdall.'
  if len(normalized_labels) > 1:
    return (
      'Heimdall did not capture a Samsung download-mode device after the '
      'earlier live probes completed.'
    )
  return 'Heimdall did not capture a Samsung download-mode device.'


def _string_payload_value(
  payload: dict[str, object],
  key: str,
) -> Optional[str]:
  value = payload.get(key)
  if value is None:
    return None
  normalized = str(value).strip()
  if not normalized:
    return None
  return normalized


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
    path_identity=_build_path_identity(
      updated_snapshot.source,
      detection.fallback_posture,
      detection.fallback_reason,
      snapshot=updated_snapshot,
      detection_state=detection.state,
    ),
    notes=_merge_detection_notes(detection.notes, trace.notes, updated_snapshot, info_state),
  )


def _build_path_identity(
  source: LiveDeviceSource,
  fallback_posture: LiveFallbackPosture,
  fallback_reason: Optional[str],
  snapshot: Optional[LiveDeviceSnapshot] = None,
  detection_state: Optional[LiveDetectionState] = None,
) -> LivePathIdentity:
  """Build one explicit live-path identity surface for this detection state."""

  ownership = _path_ownership(source, fallback_posture)
  identity_confidence = _identity_confidence(snapshot)
  return LivePathIdentity(
    ownership=ownership,
    path_label=_path_label(
      source,
      fallback_posture,
      snapshot,
      detection_state,
    ),
    delegated_path_label=_delegated_path_label(
      source,
      fallback_posture,
      snapshot,
      detection_state,
    ),
    mode_label=_path_mode_label(
      source,
      snapshot,
      fallback_posture,
      detection_state,
    ),
    identity_confidence=identity_confidence,
    summary=_path_summary(
      source,
      fallback_posture,
      fallback_reason,
      snapshot,
      detection_state,
      identity_confidence,
    ),
    operator_guidance=_path_guidance(
      source,
      fallback_posture,
      fallback_reason,
      snapshot,
      detection_state,
      identity_confidence,
    ),
  )


def _path_ownership(
  source: LiveDeviceSource,
  fallback_posture: LiveFallbackPosture,
) -> LivePathOwnership:
  """Return the explicit ownership label for one live path."""

  if source == LiveDeviceSource.ADB:
    if fallback_posture == LiveFallbackPosture.NEEDED:
      return LivePathOwnership.DELEGATED
    return LivePathOwnership.NATIVE
  if source == LiveDeviceSource.USB:
    return LivePathOwnership.NATIVE
  if source == LiveDeviceSource.HEIMDALL:
    return LivePathOwnership.DELEGATED
  if fallback_posture == LiveFallbackPosture.ENGAGED:
    return LivePathOwnership.FALLBACK
  return LivePathOwnership.DELEGATED


def _identity_confidence(
  snapshot: Optional[LiveDeviceSnapshot],
) -> LiveIdentityConfidence:
  """Return how much repo-owned identity is available for this path."""

  if snapshot is None:
    return LiveIdentityConfidence.UNAVAILABLE
  if snapshot.support_posture == LiveDeviceSupportPosture.SUPPORTED:
    return LiveIdentityConfidence.PROFILED
  if (
    snapshot.canonical_product_code is not None
    or snapshot.product_code is not None
    or snapshot.model_name is not None
  ):
    return LiveIdentityConfidence.PRODUCT_RESOLVED
  return LiveIdentityConfidence.SERIAL_ONLY


def _path_label(
  source: LiveDeviceSource,
  fallback_posture: LiveFallbackPosture,
  snapshot: Optional[LiveDeviceSnapshot],
  detection_state: Optional[LiveDetectionState],
) -> str:
  """Return one operator-facing label for the current live path."""

  if snapshot is None:
    if fallback_posture == LiveFallbackPosture.NEEDED:
      return 'Fallback Check Pending'
    if fallback_posture == LiveFallbackPosture.ENGAGED:
      if detection_state == LiveDetectionState.FAILED:
        return 'Fallback Probe Failed'
      return 'Fallback Exhausted'
    if detection_state == LiveDetectionState.FAILED:
      if source == LiveDeviceSource.ADB:
        return 'ADB Probe Failed'
      if source == LiveDeviceSource.USB:
        return 'Native Download-Mode Probe Failed'
      if source == LiveDeviceSource.HEIMDALL:
        return 'Heimdall Probe Failed'
      return 'Fastboot Probe Failed'
    if source == LiveDeviceSource.USB:
      return 'No Download-Mode Device'
    if source == LiveDeviceSource.HEIMDALL:
      return 'No Download-Mode Device'
    return 'No Live Path'
  if snapshot.source == LiveDeviceSource.ADB:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return 'ADB Session Attention'
    return 'ADB Native Session'
  if snapshot.source == LiveDeviceSource.USB:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return 'Native Download-Mode Attention'
    return 'Native Download-Mode Session'
  if snapshot.source == LiveDeviceSource.HEIMDALL:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return 'Heimdall Download-Mode Attention'
    return 'Heimdall Download-Mode Session'
  if fallback_posture == LiveFallbackPosture.ENGAGED:
    return 'Fastboot Fallback Session'
  return 'Delegated Fastboot Session'


def _delegated_path_label(
  source: LiveDeviceSource,
  fallback_posture: LiveFallbackPosture,
  snapshot: Optional[LiveDeviceSnapshot],
  detection_state: Optional[LiveDetectionState],
) -> str:
  """Return one compact delegated-path label for evidence surfaces."""

  if snapshot is None:
    if fallback_posture == LiveFallbackPosture.NEEDED:
      return 'adb -> fastboot handoff'
    if fallback_posture == LiveFallbackPosture.ENGAGED:
      if detection_state == LiveDetectionState.FAILED:
        return 'adb -> fastboot probe failed'
      return 'adb -> fastboot exhausted'
    if source == LiveDeviceSource.ADB:
      return 'adb probe'
    if source == LiveDeviceSource.HEIMDALL:
      return 'heimdall download-mode probe'
    return 'fastboot probe'
  if snapshot.source == LiveDeviceSource.ADB:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return 'adb attention lane'
    return 'native adb session'
  if snapshot.source == LiveDeviceSource.USB:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return 'native usb attention lane'
    return 'native usb download-mode session'
  if snapshot.source == LiveDeviceSource.HEIMDALL:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return 'heimdall download-mode attention lane'
    return 'heimdall download-mode session'
  if fallback_posture == LiveFallbackPosture.ENGAGED:
    return 'adb -> fastboot fallback'
  return 'fastboot delegated session'


def _path_mode_label(
  source: LiveDeviceSource,
  snapshot: Optional[LiveDeviceSnapshot],
  fallback_posture: LiveFallbackPosture,
  detection_state: Optional[LiveDetectionState],
) -> str:
  """Return one human-readable mode-truth label for the current path."""

  if snapshot is not None:
    return snapshot.mode.replace('/', ' / ')
  if fallback_posture == LiveFallbackPosture.NEEDED:
    return 'awaiting fastboot identity'
  if detection_state == LiveDetectionState.FAILED:
    if source == LiveDeviceSource.ADB:
      return 'adb probe failed'
    if source == LiveDeviceSource.USB:
      return 'native usb probe failed'
    if source == LiveDeviceSource.HEIMDALL:
      return 'heimdall probe failed'
    return 'fastboot probe failed'
  if source == LiveDeviceSource.USB:
    return 'download-mode not detected'
  if source == LiveDeviceSource.HEIMDALL:
    return 'download-mode not detected'
  return 'no live mode'


def _path_summary(
  source: LiveDeviceSource,
  fallback_posture: LiveFallbackPosture,
  fallback_reason: Optional[str],
  snapshot: Optional[LiveDeviceSnapshot],
  detection_state: Optional[LiveDetectionState],
  identity_confidence: LiveIdentityConfidence,
) -> str:
  """Return one summary sentence for the current live-path identity."""

  if snapshot is None:
    if fallback_posture == LiveFallbackPosture.NEEDED:
      return (
        'ADB did not establish a live device yet; the next supported delegated '
        'path is the fastboot handoff.'
      )
    if fallback_posture == LiveFallbackPosture.ENGAGED:
      if detection_state == LiveDetectionState.FAILED:
        return (
          'The delegated fastboot fallback lane failed before a live companion '
          'could be identified.'
        )
      return (
        'Fallback review stayed explicit, but fastboot did not capture a live '
        'companion after ADB failed to establish one.'
      )
    if detection_state == LiveDetectionState.FAILED:
      if source == LiveDeviceSource.USB:
        return (
          'Native USB detection failed before a trustworthy Samsung '
          'download-mode identity could be built.'
        )
      if source == LiveDeviceSource.HEIMDALL:
        return 'Heimdall detection failed before a trustworthy Samsung download-mode identity could be built.'
      return '{source} detection failed before a trustworthy live identity could be built.'.format(
        source=source.value.upper(),
      )
    if source == LiveDeviceSource.USB:
      return 'Native USB scan did not capture a Samsung download-mode companion.'
    if source == LiveDeviceSource.HEIMDALL:
      return 'Heimdall did not capture a Samsung download-mode companion.'
    return 'No live or delegated path is currently active.'

  identity = _identity_label(snapshot)
  if snapshot.source == LiveDeviceSource.ADB:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return (
        'ADB identified {identity}, but the live session still needs operator '
        'attention before it should be treated as command-ready.'
      ).format(identity=identity)
    if snapshot.info_state == LiveDeviceInfoState.CAPTURED:
      return (
        'ADB native session resolved {identity}, and bounded ADB device info is '
        'captured for reviewed guidance.'
      ).format(identity=identity)
    if snapshot.info_state == LiveDeviceInfoState.PARTIAL:
      return (
        'ADB native session resolved {identity}, but bounded ADB device info is '
        'only partial.'
      ).format(identity=identity)
    if snapshot.info_state == LiveDeviceInfoState.FAILED:
      return (
        'ADB native session resolved {identity}, but bounded ADB device info '
        'could not be captured.'
      ).format(identity=identity)
    return 'ADB native session resolved {identity} for repo-owned live guidance.'.format(
      identity=identity,
    )

  if snapshot.source == LiveDeviceSource.HEIMDALL:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return (
        'Heimdall identified {identity}, but the download-mode session still '
        'needs operator attention before it should be treated as command-ready.'
      ).format(identity=identity)
    if identity_confidence == LiveIdentityConfidence.SERIAL_ONLY:
      return (
        'Heimdall download-mode session captured serial {serial}, but current '
        'identity is still serial-only because Heimdall did not provide a '
        'product code.'
      ).format(serial=snapshot.serial)
    return (
      'Heimdall download-mode session resolved {identity} for PIT-oriented '
      'review while keeping the delegated Samsung download-mode lane explicit.'
    ).format(identity=identity)

  if snapshot.source == LiveDeviceSource.USB:
    if detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
      return (
        'Native USB detection identified {identity}, but the download-mode '
        'session still needs operator attention before it should be treated '
        'as command-ready.'
      ).format(identity=identity)
    if identity_confidence == LiveIdentityConfidence.SERIAL_ONLY:
      return (
        'Native USB download-mode session captured serial {serial}, but '
        'current identity is still serial-only because the USB descriptors '
        'did not expose a Samsung product code.'
      ).format(serial=snapshot.serial)
    return (
      'Native USB download-mode session resolved {identity} for repo-owned '
      'Samsung detection while PIT and flash ownership remain explicitly bounded.'
    ).format(identity=identity)

  if fallback_posture == LiveFallbackPosture.ENGAGED:
    if identity_confidence == LiveIdentityConfidence.SERIAL_ONLY:
      return (
        'Fastboot fallback captured serial {serial}, but current fallback '
        'identity is still serial-only because fastboot did not provide a '
        'product code.'
      ).format(serial=snapshot.serial)
    return (
      'Fastboot fallback resolved {identity}, but the lane remains explicit '
      'fallback guidance rather than a native-ready claim.'
    ).format(identity=identity)

  if identity_confidence == LiveIdentityConfidence.SERIAL_ONLY:
    return (
      'Delegated fastboot session captured serial {serial}, but current '
      'identity is still serial-only because fastboot did not provide a '
      'product code.'
    ).format(serial=snapshot.serial)
  return (
    'Delegated fastboot session resolved {identity} while staying narrower '
    'than a native ADB session.'
  ).format(identity=identity)


def _path_guidance(
  source: LiveDeviceSource,
  fallback_posture: LiveFallbackPosture,
  fallback_reason: Optional[str],
  snapshot: Optional[LiveDeviceSnapshot],
  detection_state: Optional[LiveDetectionState],
  identity_confidence: LiveIdentityConfidence,
) -> Tuple[str, ...]:
  """Return operator guidance for the current live-path identity."""

  guidance = []  # type: list[str]
  if snapshot is None:
    if source == LiveDeviceSource.USB:
      if detection_state == LiveDetectionState.FAILED:
        guidance.append(
          'Resolve the native USB access or bundled libusb backend before trusting Samsung download-mode identity.'
        )
      else:
        guidance.append(
          'If the device should already be in Samsung download mode, confirm the USB path and rerun Detect device.'
        )
    if source == LiveDeviceSource.HEIMDALL:
      if detection_state == LiveDetectionState.FAILED:
        guidance.append(
          'Resolve the Heimdall/download-mode detection failure before trusting Samsung download-mode identity.'
        )
      else:
        guidance.append(
          'If the device should already be in Samsung download mode, confirm the cable/driver path and rerun Detect device.'
        )
    elif fallback_posture == LiveFallbackPosture.NEEDED:
      guidance.append(
        'Treat the current lane as an ADB -> fastboot handoff only; do not infer device support until a live companion is identified.'
      )
    elif fallback_posture == LiveFallbackPosture.ENGAGED:
      guidance.append(
        'Keep fallback status explicit; do not widen the path until fastboot or ADB captures a live companion.'
      )
    elif detection_state == LiveDetectionState.FAILED:
      guidance.append(
        'Resolve the live companion tool failure before trusting any launch-path identity.'
      )
  elif snapshot.source == LiveDeviceSource.HEIMDALL:
    guidance.append(
      'Samsung download mode is present; use PIT review to gather bounded evidence before widening any safe-path claim.'
    )
    guidance.append(
      'Heimdall detection does not provide the richer bounded Android property snapshot that a command-ready ADB session can capture.'
    )
  elif snapshot.source == LiveDeviceSource.USB:
    guidance.append(
      'Samsung download mode is present through the native USB lane; use Read PIT to gather bounded partition truth before widening any safe-path claim.'
    )
    guidance.append(
      'Native USB detection owns presence and identity, but richer Android property snapshots still require a command-ready ADB session.'
    )
  elif snapshot.source == LiveDeviceSource.FASTBOOT:
    if identity_confidence == LiveIdentityConfidence.SERIAL_ONLY:
      guidance.append(
        'Treat the current fastboot lane as serial-only identity until richer product truth is available.'
      )
    else:
      guidance.append(
        'Keep the current fastboot lane labeled delegated or fallback; do not flatten it into a native-ready claim.'
      )
  elif detection_state == LiveDetectionState.ATTENTION or not snapshot.command_ready:
    guidance.append(
      'Keep the current live lane narrowed until ADB becomes command-ready again.'
    )

  if snapshot is not None:
    guidance.extend(snapshot.operator_guidance[:2])
  if fallback_reason:
    guidance.append(fallback_reason)
  return _dedupe_preserve_order(guidance)


def _identity_label(snapshot: LiveDeviceSnapshot) -> str:
  """Return one readable identity label for path-summary output."""

  if snapshot.marketing_name is not None:
    return '{name} ({product})'.format(
      name=snapshot.marketing_name,
      product=(
        snapshot.canonical_product_code
        or snapshot.product_code
        or snapshot.serial
      ),
    )
  if snapshot.product_code is not None:
    return '{product} [{serial}]'.format(
      product=snapshot.product_code,
      serial=snapshot.serial,
    )
  if snapshot.model_name is not None:
    return '{model} [{serial}]'.format(
      model=snapshot.model_name,
      serial=snapshot.serial,
    )
  return snapshot.serial


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
  extra_notes: Tuple[str, ...] = (),
) -> Tuple[str, ...]:
  collected = list(extra_notes)
  collected.extend(notes)
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
  elif source == LiveDeviceSource.USB:
    hints.append('usb_download_detect')
    if command_ready:
      hints.extend(
        (
          'heimdall_print_pit',
          'heimdall_download_pit',
          'download_mode_detected',
          'adb_required_for_richer_info',
        )
      )
    else:
      hints.append('usb_access_attention_required')
  elif source == LiveDeviceSource.HEIMDALL:
    hints.append('heimdall_detect')
    if command_ready:
      hints.extend(
        (
          'heimdall_print_pit',
          'heimdall_download_pit',
          'download_mode_detected',
          'adb_required_for_richer_info',
        )
      )
    else:
      hints.append('heimdall_attention_required')
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
  if source == LiveDeviceSource.USB:
    guidance.append('Native USB detection confirms Samsung download mode without relying on an external Heimdall detect subprocess.')
    guidance.append('Use Read PIT to continue the bounded download-mode review path after native detection succeeds.')
  if source == LiveDeviceSource.HEIMDALL:
    guidance.append('Samsung download mode is present; use PIT review to gather bounded evidence before widening any safe-path claim.')
    guidance.append('Heimdall does not expose the richer bounded Android property snapshot that a command-ready ADB session can capture.')
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
