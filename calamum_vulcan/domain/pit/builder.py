"""Builders that normalize Heimdall PIT output into repo-owned inspection truth."""

from __future__ import annotations

import re
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.package import PackageManifestAssessment

from .model import PitDeviceAlignment
from .model import PitFallbackPosture
from .model import PitInspection
from .model import PitInspectionState
from .model import PitPackageAlignment
from .model import PitPartitionRecord
from .model import PitSource


PRINT_METADATA_PATTERN = re.compile(
  r'^PIT metadata: product_code=(?P<product_code>\S+) '
  r'fingerprint=(?P<fingerprint>\S+) '
  r'entry_count=(?P<entry_count>\d+)$'
)

PRINT_ENTRY_PATTERN = re.compile(
  r'^Entry: index=(?P<index>\d+) '
  r'partition=(?P<partition>[A-Z0-9_]+)'
  r'(?: file_name=(?P<file_name>\S+))?'
  r'(?: block_count=(?P<block_count>\d+))?'
  r'(?: file_offset=(?P<file_offset>\d+))?$'
)

DOWNLOAD_SUMMARY_PATTERN = re.compile(
  r'^PIT download complete: output=(?P<output>\S+) '
  r'product_code=(?P<product_code>\S+) '
  r'fingerprint=(?P<fingerprint>\S+) '
  r'entry_count=(?P<entry_count>\d+) '
  r'bytes=(?P<byte_count>\d+)$'
)


def build_pit_inspection(
  trace: HeimdallNormalizedTrace,
  detected_product_code: Optional[str] = None,
  package_assessment: Optional[PackageManifestAssessment] = None,
) -> PitInspection:
  """Normalize one Heimdall PIT trace into repo-owned inspection truth."""

  source = _pit_source_for_trace(trace)
  fallback_reason = _fallback_reason_for_source(source)
  if trace.state == HeimdallTraceState.FAILED:
    return _compose_inspection(
      state=PitInspectionState.FAILED,
      source=source,
      detected_product_code=detected_product_code,
      observed_product_code=None,
      observed_pit_fingerprint=None,
      package_assessment=package_assessment,
      fallback_reason=fallback_reason,
      summary=_pit_failure_summary(trace, source),
      download_path=_command_output_path(trace),
      entry_count=0,
      partition_names=(),
      entries=(),
      notes=tuple(trace.notes),
    )

  if source == PitSource.HEIMDALL_PRINT_PIT:
    return _build_from_print_trace(
      trace,
      source=source,
      detected_product_code=detected_product_code,
      package_assessment=package_assessment,
      fallback_reason=fallback_reason,
    )

  if source == PitSource.INTEGRATED_RUNTIME_PRINT_PIT:
    return _build_from_print_trace(
      trace,
      source=source,
      detected_product_code=detected_product_code,
      package_assessment=package_assessment,
      fallback_reason=fallback_reason,
    )

  return _build_from_download_trace(
    trace,
    source=source,
    detected_product_code=detected_product_code,
    package_assessment=package_assessment,
    fallback_reason=fallback_reason,
  )


def _build_from_print_trace(
  trace: HeimdallNormalizedTrace,
  source: PitSource,
  detected_product_code: Optional[str],
  package_assessment: Optional[PackageManifestAssessment],
  fallback_reason: str,
) -> PitInspection:
  metadata_match = None
  raw_entry_lines = 0
  entries = []  # type: List[PitPartitionRecord]
  notes = list(trace.notes)

  for line in trace.stdout_lines:
    metadata = PRINT_METADATA_PATTERN.search(line)
    if metadata is not None:
      metadata_match = metadata
      continue
    if line.startswith('Entry:'):
      raw_entry_lines += 1
      entry_match = PRINT_ENTRY_PATTERN.search(line)
      if entry_match is None:
        notes.append('One or more PIT partition rows did not satisfy the parser contract.')
        continue
      entries.append(
        PitPartitionRecord(
          index=int(entry_match.group('index')),
          partition_name=entry_match.group('partition'),
          file_name=entry_match.group('file_name'),
          block_count=_optional_int(entry_match.group('block_count')),
          file_offset=_optional_int(entry_match.group('file_offset')),
        )
      )

  if metadata_match is None or not entries:
    if metadata_match is None:
      notes.append('PIT metadata did not satisfy the repo-owned parser contract.')
    if not entries:
      notes.append('No PIT partition rows could be parsed from Heimdall print-pit output.')
    return _compose_inspection(
      state=PitInspectionState.MALFORMED,
      source=source,
      detected_product_code=detected_product_code,
      observed_product_code=(
        metadata_match.group('product_code') if metadata_match is not None else None
      ),
      observed_pit_fingerprint=(
        metadata_match.group('fingerprint') if metadata_match is not None else None
      ),
      package_assessment=package_assessment,
      fallback_reason=fallback_reason,
      summary=(
        'PIT output was captured through {path}, but '
        'it did not satisfy the repo-owned parser contract.'
      ).format(path=_source_path_label(source)),
      download_path=None,
      entry_count=len(entries),
      partition_names=tuple(entry.partition_name for entry in entries),
      entries=tuple(entries),
      notes=tuple(_dedupe_strings(notes)),
    )

  expected_entry_count = int(metadata_match.group('entry_count'))
  state = PitInspectionState.CAPTURED
  if raw_entry_lines != len(entries) or expected_entry_count != len(entries):
    state = PitInspectionState.PARTIAL
    notes.append(
      'PIT metadata and parsed partition-row counts do not fully agree yet.'
    )
  notes.append(
    'Parsed {count} PIT partition rows through the repo-owned print-pit parser.'.format(
      count=len(entries),
    )
  )
  return _compose_inspection(
    state=state,
    source=source,
    detected_product_code=detected_product_code,
    observed_product_code=metadata_match.group('product_code'),
    observed_pit_fingerprint=metadata_match.group('fingerprint'),
    package_assessment=package_assessment,
    fallback_reason=fallback_reason,
    summary=_summary_for_print_capture(
      source=source,
      state=state,
      observed_product_code=metadata_match.group('product_code'),
      observed_pit_fingerprint=metadata_match.group('fingerprint'),
      detected_product_code=detected_product_code,
      package_assessment=package_assessment,
      entry_count=len(entries),
    ),
    download_path=None,
    entry_count=len(entries),
    partition_names=tuple(entry.partition_name for entry in entries),
    entries=tuple(entries),
    notes=tuple(_dedupe_strings(notes)),
  )


def _pit_failure_summary(
  trace: HeimdallNormalizedTrace,
  source: PitSource,
) -> str:
  """Return one operator-facing PIT failure summary with the best reason."""

  summary = (
    '{source_label} PIT acquisition failed before repo-owned PIT inspection '
    'could begin.'
  ).format(source_label=_pit_failure_source_label(source))
  detail = _pit_failure_detail(trace)
  if detail is None:
    return summary
  return '{summary} Reason: {detail}'.format(
    summary=summary,
    detail=_terminal_sentence(detail),
  )


def _pit_failure_source_label(source: PitSource) -> str:
  """Return the operator label for one failed PIT acquisition source."""

  if source in (
    PitSource.INTEGRATED_RUNTIME_PRINT_PIT,
    PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT,
  ):
    return 'Supported-path'
  return 'Heimdall'


def _pit_failure_detail(trace: HeimdallNormalizedTrace) -> Optional[str]:
  """Return the most specific failure detail carried by one normalized trace."""

  ignored_prefixes = (
    'Calamum integrated runtime owns',
    'Delegated lower-transport internals remain packaged',
    'Delegated lower-transport command:',
  )
  for note in trace.notes:
    candidate = str(note).strip()
    if not candidate:
      continue
    if any(candidate.startswith(prefix) for prefix in ignored_prefixes):
      continue
    return _normalized_failure_detail(candidate)
  for line in trace.stderr_lines:
    candidate = str(line).strip()
    if candidate:
      return _normalized_failure_detail(candidate)
  for line in trace.stdout_lines:
    candidate = str(line).strip()
    if candidate and 'error' in candidate.lower():
      return _normalized_failure_detail(candidate)
  return None


def _normalized_failure_detail(value: str) -> str:
  """Return one operator-facing PIT failure detail without raw transport noise."""

  candidate = value.strip()
  lowered = candidate.lower()
  disconnect_markers = (
    'no longer connected',
    'device disconnected',
    'device has been disconnected',
    'failed to open usb device',
  )
  if any(marker in lowered for marker in disconnect_markers):
    return 'The supported-path transport lost access to the Samsung download-mode interface during PIT acquisition'
  return candidate


def _terminal_sentence(value: str) -> str:
  """Return one sentence-like value with terminal punctuation."""

  trimmed = value.strip()
  if not trimmed:
    return ''
  if trimmed.endswith(('.', '!', '?')):
    return trimmed
  return trimmed + '.'


def _build_from_download_trace(
  trace: HeimdallNormalizedTrace,
  source: PitSource,
  detected_product_code: Optional[str],
  package_assessment: Optional[PackageManifestAssessment],
  fallback_reason: str,
) -> PitInspection:
  metadata_match = None
  for line in trace.stdout_lines:
    metadata = DOWNLOAD_SUMMARY_PATTERN.search(line)
    if metadata is not None:
      metadata_match = metadata
      break

  notes = list(trace.notes)
  output_path = _command_output_path(trace)
  if metadata_match is None:
    notes.append('PIT download output did not satisfy the repo-owned metadata parser.')
    return _compose_inspection(
      state=PitInspectionState.MALFORMED,
      source=source,
      detected_product_code=detected_product_code,
      observed_product_code=None,
      observed_pit_fingerprint=None,
      package_assessment=package_assessment,
      fallback_reason=fallback_reason,
      summary=(
        'PIT download output completed through {path}, but the repo-owned metadata parser '
        'could not extract trustworthy PIT facts.'
      ).format(path=_source_path_label(source)),
      download_path=output_path,
      entry_count=0,
      partition_names=(),
      entries=(),
      notes=tuple(_dedupe_strings(notes)),
    )

  notes.append(
    'Download-pit captured bounded PIT metadata; detailed partition rows still require print-pit.'
  )
  return _compose_inspection(
    state=PitInspectionState.PARTIAL,
    source=source,
    detected_product_code=detected_product_code,
    observed_product_code=metadata_match.group('product_code'),
    observed_pit_fingerprint=metadata_match.group('fingerprint'),
    package_assessment=package_assessment,
    fallback_reason=fallback_reason,
    summary=(
      'PIT acquisition metadata was captured through {path}, but '
      'path, but detailed partition inspection still requires print-pit output.'
    ).format(path=_source_path_label(source)),
    download_path=metadata_match.group('output') or output_path,
    entry_count=int(metadata_match.group('entry_count')),
    partition_names=(),
    entries=(),
    notes=tuple(_dedupe_strings(notes)),
  )


def _compose_inspection(
  state: PitInspectionState,
  source: PitSource,
  detected_product_code: Optional[str],
  observed_product_code: Optional[str],
  observed_pit_fingerprint: Optional[str],
  package_assessment: Optional[PackageManifestAssessment],
  fallback_reason: str,
  summary: str,
  download_path: Optional[str],
  entry_count: int,
  partition_names: Tuple[str, ...],
  entries: Tuple[PitPartitionRecord, ...],
  notes: Tuple[str, ...],
) -> PitInspection:
  resolution = resolve_device_profile(observed_product_code or detected_product_code)
  reviewed_pit_fingerprint = None
  package_alignment = PitPackageAlignment.NOT_REVIEWED
  if package_assessment is not None:
    reviewed_pit_fingerprint = package_assessment.pit_fingerprint
    package_alignment = _package_alignment(
      reviewed_pit_fingerprint,
      observed_pit_fingerprint,
    )

  device_alignment = _device_alignment(
    observed_product_code,
    detected_product_code,
  )
  operator_guidance = _operator_guidance(
    state=state,
    source=source,
    package_alignment=package_alignment,
    device_alignment=device_alignment,
    registry_match_kind=resolution.match_kind.value,
  )
  return PitInspection(
    state=state,
    source=source,
    summary=summary,
    fallback_posture=PitFallbackPosture.ENGAGED,
    fallback_reason=fallback_reason,
    observed_product_code=observed_product_code,
    canonical_product_code=resolution.canonical_product_code,
    marketing_name=resolution.marketing_name,
    registry_match_kind=resolution.match_kind.value,
    observed_pit_fingerprint=observed_pit_fingerprint,
    reviewed_pit_fingerprint=reviewed_pit_fingerprint,
    package_alignment=package_alignment,
    device_alignment=device_alignment,
    download_path=download_path,
    entry_count=entry_count,
    partition_names=partition_names,
    entries=entries,
    notes=notes,
    operator_guidance=operator_guidance,
  )


def _summary_for_print_capture(
  source: PitSource,
  state: PitInspectionState,
  observed_product_code: Optional[str],
  observed_pit_fingerprint: Optional[str],
  detected_product_code: Optional[str],
  package_assessment: Optional[PackageManifestAssessment],
  entry_count: int,
) -> str:
  resolution = resolve_device_profile(observed_product_code or detected_product_code)
  device_label = _device_label(
    observed_product_code,
    resolution.canonical_product_code,
    resolution.marketing_name,
  )
  summary = (
    'Repo-owned PIT inspection captured {count} partition rows for {device} '
    'through {path}.'.format(
      count=entry_count,
      device=device_label,
      path=_source_path_label(source),
    )
  )
  if state == PitInspectionState.PARTIAL:
    summary = (
      'Repo-owned PIT inspection partially parsed {count} partition rows for '
      '{device} through {path}.'.format(
        count=entry_count,
        device=device_label,
        path=_source_path_label(source),
      )
    )
  package_alignment = PitPackageAlignment.NOT_REVIEWED
  if package_assessment is not None:
    package_alignment = _package_alignment(
      package_assessment.pit_fingerprint,
      observed_pit_fingerprint,
    )
  if package_alignment == PitPackageAlignment.MATCHED:
    summary += ' Observed PIT fingerprint matches the reviewed package fingerprint.'
  elif package_alignment == PitPackageAlignment.MISMATCHED:
    summary += ' Observed PIT fingerprint does not match the reviewed package fingerprint.'
  elif package_alignment == PitPackageAlignment.MISSING_REVIEWED:
    summary += ' Reviewed package truth does not yet provide a usable PIT fingerprint for comparison.'
  elif package_alignment == PitPackageAlignment.MISSING_OBSERVED:
    summary += ' Observed PIT output did not provide a usable PIT fingerprint for comparison.'
  if _device_alignment(observed_product_code, detected_product_code) == PitDeviceAlignment.MISMATCHED:
    summary += ' Observed PIT product code does not match the current session device identity.'
  return summary


def _device_label(
  observed_product_code: Optional[str],
  canonical_product_code: Optional[str],
  marketing_name: Optional[str],
) -> str:
  if marketing_name and (canonical_product_code or observed_product_code):
    return '{name} ({product})'.format(
      name=marketing_name,
      product=canonical_product_code or observed_product_code,
    )
  if canonical_product_code:
    return canonical_product_code
  if observed_product_code:
    return observed_product_code
  return 'the active device'


def _package_alignment(
  reviewed_pit_fingerprint: Optional[str],
  observed_pit_fingerprint: Optional[str],
) -> PitPackageAlignment:
  reviewed = _normalized_truth_value(reviewed_pit_fingerprint)
  observed = _normalized_truth_value(observed_pit_fingerprint)
  if reviewed is None:
    return PitPackageAlignment.MISSING_REVIEWED
  if observed is None:
    return PitPackageAlignment.MISSING_OBSERVED
  if reviewed == observed:
    return PitPackageAlignment.MATCHED
  return PitPackageAlignment.MISMATCHED


def _device_alignment(
  observed_product_code: Optional[str],
  detected_product_code: Optional[str],
) -> PitDeviceAlignment:
  observed = _normalized_product_code(observed_product_code)
  detected = _normalized_product_code(detected_product_code)
  if observed is None or detected is None:
    return PitDeviceAlignment.NOT_PROVIDED
  if observed == detected:
    return PitDeviceAlignment.MATCHED
  return PitDeviceAlignment.MISMATCHED


def _operator_guidance(
  state: PitInspectionState,
  source: PitSource,
  package_alignment: PitPackageAlignment,
  device_alignment: PitDeviceAlignment,
  registry_match_kind: str,
) -> Tuple[str, ...]:
  integrated_source = source in (
    PitSource.INTEGRATED_RUNTIME_PRINT_PIT,
    PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT,
  )
  guidance = [
    'Treat observed PIT truth as read-side inspection only; it does not imply flash readiness.',
    (
      'PIT acquisition runs through the supported path while repo-owned PIT parsing and inspection remain authoritative.'
      if integrated_source
      else 'PIT acquisition currently depends on the Heimdall adapter while repo-owned PIT parsing and inspection mature.'
    ),
  ]
  if source in (
    PitSource.HEIMDALL_DOWNLOAD_PIT,
    PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT,
  ):
    guidance.append('Detailed partition inspection currently requires print-pit; download-pit is metadata-only in this slice.')
  if state == PitInspectionState.MALFORMED:
    guidance.append('Do not rely on this PIT result until malformed PIT output is resolved.')
  elif state == PitInspectionState.FAILED:
    guidance.append(
      'Re-run PIT acquisition only after the supported-path PIT failure is understood and bounded.'
      if integrated_source
      else 'Re-run PIT acquisition only after the Heimdall adapter failure is understood and bounded.'
    )
  elif state == PitInspectionState.PARTIAL:
    guidance.append('Keep PIT review bounded until metadata and partition rows agree fully.')

  if package_alignment == PitPackageAlignment.MATCHED:
    guidance.append('Observed PIT fingerprint matches the reviewed package fingerprint.')
  elif package_alignment == PitPackageAlignment.MISMATCHED:
    guidance.append('Observed PIT fingerprint does not match the reviewed package fingerprint; keep write-side claims closed.')
  elif package_alignment == PitPackageAlignment.MISSING_REVIEWED:
    guidance.append('Reviewed package truth does not yet provide a usable PIT fingerprint for comparison.')
  elif package_alignment == PitPackageAlignment.MISSING_OBSERVED:
    guidance.append('Observed PIT output did not provide a usable PIT fingerprint for comparison.')

  if device_alignment == PitDeviceAlignment.MISMATCHED:
    guidance.append('Observed PIT product code does not match the current session device identity.')
  if registry_match_kind == 'not_provided':
    guidance.append('Resolve a concrete product code before treating this PIT review as support evidence.')
  elif registry_match_kind == 'unknown':
    guidance.append('Add a repo-owned device profile before treating this PIT review as support evidence.')
  return tuple(_dedupe_strings(guidance))


def _command_output_path(trace: HeimdallNormalizedTrace) -> Optional[str]:
  arguments = trace.command_plan.arguments
  if '--output' not in arguments:
    return None
  output_index = arguments.index('--output')
  if output_index + 1 >= len(arguments):
    return None
  return arguments[output_index + 1]


def _pit_source_for_trace(trace: HeimdallNormalizedTrace) -> PitSource:
  """Return the PIT source semantics that match the current trace boundary."""

  operation = trace.command_plan.operation
  adapter_name = getattr(trace, 'adapter_name', 'heimdall')
  if operation == HeimdallOperation.PRINT_PIT:
    if adapter_name == 'integrated-runtime':
      return PitSource.INTEGRATED_RUNTIME_PRINT_PIT
    return PitSource.HEIMDALL_PRINT_PIT
  if operation == HeimdallOperation.DOWNLOAD_PIT:
    if adapter_name == 'integrated-runtime':
      return PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT
    return PitSource.HEIMDALL_DOWNLOAD_PIT
  raise ValueError(
    'PIT inspection requires Heimdall print-pit or download-pit output.'
  )


def _fallback_reason_for_source(source: PitSource) -> str:
  """Return the boundary note for the current PIT acquisition source."""

  if source in (
    PitSource.INTEGRATED_RUNTIME_PRINT_PIT,
    PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT,
  ):
    return (
      'PIT acquisition is running through the supported path; '
      'delegated lower-transport details stay packaged behind the supported path.'
    )
  return (
    'PIT acquisition currently depends on the Heimdall adapter while '
    'repo-owned PIT parsing and inspection mature.'
  )


def _source_path_label(source: PitSource) -> str:
  """Return one operator-facing label for the PIT source boundary."""

  if source == PitSource.INTEGRATED_RUNTIME_PRINT_PIT:
    return 'the supported-path print-pit lane'
  if source == PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT:
    return 'the supported-path download-pit lane'
  if source == PitSource.HEIMDALL_PRINT_PIT:
    return 'the Heimdall print-pit path'
  return 'the Heimdall download-pit path'


def _normalized_truth_value(value: Optional[str]) -> Optional[str]:
  if value is None:
    return None
  normalized = value.strip()
  if not normalized:
    return None
  if normalized.lower().startswith('missing'):
    return None
  return normalized.upper()


def _normalized_product_code(value: Optional[str]) -> Optional[str]:
  if value is None:
    return None
  normalized = value.strip().replace('_', '-')
  if not normalized:
    return None
  return normalized.upper()


def _optional_int(value: Optional[str]) -> Optional[int]:
  if value is None:
    return None
  return int(value)


def _dedupe_strings(values: List[str]) -> Tuple[str, ...]:
  deduped = []  # type: List[str]
  for value in values:
    if value not in deduped:
      deduped.append(value)
  return tuple(deduped)


def preflight_overrides_from_pit_inspection(
  inspection: PitInspection,
) -> Dict[str, object]:
  """Convert PIT inspection truth into preflight-rule overrides."""

  return {
    'pit_state': inspection.state.value,
    'pit_summary': inspection.summary,
    'pit_package_alignment': inspection.package_alignment.value,
    'pit_device_alignment': inspection.device_alignment.value,
    'pit_observed_product_code': (
      inspection.canonical_product_code or inspection.observed_product_code
    ),
  }
