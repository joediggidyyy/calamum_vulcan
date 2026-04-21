"""Helpers that derive inspect-only read-side workflow posture."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional
from typing import Sequence
from typing import Tuple

from calamum_vulcan.domain.live_device.model import LiveDetectionSession
from calamum_vulcan.domain.live_device.model import LiveDetectionState
from calamum_vulcan.domain.live_device.model import LiveDeviceInfoState

from .model import InspectionWorkflow
from .model import InspectionWorkflowPosture


if TYPE_CHECKING:
  from calamum_vulcan.domain.pit.model import PitInspection


READ_SIDE_ACTION_BOUNDARIES = (
  'Inspect-only workflow remains read-side only and does not open a write path.',
  'Successful detection or PIT review must not be treated as transport readiness.',
)


def inspection_in_progress(
  summary: str = 'Inspect-only workflow is running.',
  captured_at_utc: Optional[str] = None,
  notes: Sequence[str] = (),
) -> InspectionWorkflow:
  """Return an in-progress inspect-only posture."""

  combined_notes = ('Inspect-only workflow is currently in progress.',) + tuple(notes)
  return InspectionWorkflow(
    posture=InspectionWorkflowPosture.INSPECTING,
    summary=summary,
    next_action='Wait for the inspect-only workflow to finish before exporting evidence.',
    action_boundaries=READ_SIDE_ACTION_BOUNDARIES,
    notes=_dedupe_strings(combined_notes),
    captured_at_utc=captured_at_utc,
  )


def build_inspection_workflow(
  live_detection: LiveDetectionSession,
  pit_inspection: Optional[PitInspection] = None,
  captured_at_utc: Optional[str] = None,
  notes: Sequence[str] = (),
) -> InspectionWorkflow:
  """Build one inspect-only read-side posture from live and PIT truth."""

  if pit_inspection is None:
    from calamum_vulcan.domain.pit.model import PitInspection

    resolved_pit = PitInspection.not_collected()
  else:
    resolved_pit = pit_inspection
  detect_ran = live_detection.state != LiveDetectionState.UNHYDRATED
  info_ran = bool(
    live_detection.snapshot is not None
    and live_detection.snapshot.info_state
    not in (
      LiveDeviceInfoState.NOT_COLLECTED,
      LiveDeviceInfoState.UNAVAILABLE,
    )
  )
  pit_state = resolved_pit.state.value
  pit_ran = pit_state != 'not_collected'
  useful_live_evidence = live_detection.device_present
  useful_pit_evidence = pit_state in ('captured', 'partial')

  posture = InspectionWorkflowPosture.UNINSPECTED
  summary = 'No inspect-only workflow has run yet.'
  next_action = 'Run the inspect-only workflow to capture read-side evidence.'

  if pit_state == 'captured':
    posture = InspectionWorkflowPosture.READY
    if useful_live_evidence:
      summary = (
        'Inspect-only workflow captured live device evidence and PIT review '
        'without opening a write path.'
      )
    else:
      summary = (
        'Inspect-only workflow captured PIT review evidence without opening a '
        'write path, even though ADB/Fastboot detection did not establish a '
        'live companion.'
      )
    next_action = (
      'Export evidence or continue reviewed package comparison; inspect-only '
      'results do not open the write path.'
    )
  elif useful_live_evidence or useful_pit_evidence:
    posture = InspectionWorkflowPosture.PARTIAL
    if useful_live_evidence and not pit_ran:
      summary = (
        'Inspect-only workflow captured live device evidence, but PIT review '
        'has not run yet.'
      )
      next_action = _missing_pit_guidance(live_detection)
    elif useful_live_evidence and pit_state == 'partial':
      summary = (
        'Inspect-only workflow captured live device evidence, but PIT review '
        'remains partial.'
      )
      next_action = _pit_guidance(resolved_pit)
    elif useful_pit_evidence:
      summary = (
        'Inspect-only workflow captured bounded PIT evidence, but live device '
        'detection remains incomplete.'
      )
      next_action = _pit_guidance(resolved_pit)
  elif detect_ran or pit_ran:
    posture = InspectionWorkflowPosture.FAILED
    summary = (
      'Inspect-only workflow ran, but it did not establish trustworthy '
      'read-side evidence.'
    )
    next_action = _failure_guidance(live_detection, resolved_pit)

  combined_notes = (
    tuple(notes)
    + tuple(live_detection.notes[:2])
    + tuple(resolved_pit.notes[:2])
  )
  return InspectionWorkflow(
    posture=posture,
    summary=summary,
    detect_ran=detect_ran,
    info_ran=info_ran,
    pit_ran=pit_ran,
    evidence_ready=detect_ran or pit_ran,
    next_action=next_action,
    action_boundaries=READ_SIDE_ACTION_BOUNDARIES,
    notes=_dedupe_strings(combined_notes),
    captured_at_utc=captured_at_utc,
  )


def _missing_pit_guidance(live_detection: LiveDetectionSession) -> str:
  if live_detection.snapshot is not None and live_detection.snapshot.source.value == 'adb':
    return (
      'PIT review usually requires a Heimdall-capable download-mode path; keep '
      'write claims closed until PIT evidence is available.'
    )
  return 'Capture PIT evidence before treating inspect-only review as complete.'


def _pit_guidance(pit_inspection: PitInspection) -> str:
  if pit_inspection.operator_guidance:
    return pit_inspection.operator_guidance[0]
  return 'Re-run PIT review only after the read-side path is stable enough to preserve bounded evidence.'


def _failure_guidance(
  live_detection: LiveDetectionSession,
  pit_inspection: PitInspection,
) -> str:
  if pit_inspection.operator_guidance:
    return pit_inspection.operator_guidance[0]
  if live_detection.state == LiveDetectionState.FAILED:
    return 'Reconnect the device and rerun inspect-only review before making support claims.'
  return 'Rerun inspect-only review only after the read-side path is stable enough to preserve bounded evidence.'


def _dedupe_strings(values: Sequence[str]) -> Tuple[str, ...]:
  deduped = []
  for value in values:
    normalized = str(value).strip()
    if not normalized or normalized in deduped:
      continue
    deduped.append(normalized)
  return tuple(deduped)