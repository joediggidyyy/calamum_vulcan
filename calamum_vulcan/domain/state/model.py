"""State vocabulary and event contracts for Calamum Vulcan."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional
from typing import TYPE_CHECKING
from typing import Tuple


if TYPE_CHECKING:
  from calamum_vulcan.domain.live_device.model import LiveDetectionSession


class SessionPhase(str, Enum):
  """Operator-visible top-level phases for Sprint 0.1.0."""

  NO_DEVICE = 'no_device'
  DEVICE_DETECTED = 'device_detected'
  PREFLIGHT_INCOMPLETE = 'preflight_incomplete'
  PACKAGE_LOADED = 'package_loaded'
  VALIDATION_BLOCKED = 'validation_blocked'
  VALIDATION_PASSED = 'validation_passed'
  READY_TO_EXECUTE = 'ready_to_execute'
  EXECUTING = 'executing'
  RESUME_NEEDED = 'resume_needed'
  COMPLETED = 'completed'
  FAILED = 'failed'


class SessionEventType(str, Enum):
  """Normalized event vocabulary owned by the platform shell."""

  DEVICE_CONNECTED = 'device_connected'
  DEVICE_DISCONNECTED = 'device_disconnected'
  PACKAGE_SELECTED = 'package_selected'
  PREFLIGHT_REVIEW_STARTED = 'preflight_review_started'
  PREFLIGHT_BLOCKED = 'preflight_blocked'
  PREFLIGHT_CLEARED = 'preflight_cleared'
  ACKNOWLEDGEMENTS_CAPTURED = 'acknowledgements_captured'
  EXECUTION_STARTED = 'execution_started'
  EXECUTION_PAUSED = 'execution_paused'
  EXECUTION_RESUMED = 'execution_resumed'
  EXECUTION_COMPLETED = 'execution_completed'
  EXECUTION_FAILED = 'execution_failed'
  RESET_SESSION = 'reset_session'


class InspectionWorkflowPosture(str, Enum):
  """Operator-facing posture for the inspect-only read-side workflow."""

  UNINSPECTED = 'uninspected'
  INSPECTING = 'inspecting'
  READY = 'ready'
  PARTIAL = 'partial'
  FAILED = 'failed'


class TransitionRejected(ValueError):
  """Raised when an event violates the sprint state contract."""


@dataclass(frozen=True)
class GuardState:
  """Boolean gating facts that sit underneath the visible session phase."""

  has_device: bool = False
  package_loaded: bool = False
  preflight_started: bool = False
  preflight_complete: bool = False
  warnings_acknowledged: bool = False
  destructive_acknowledged: bool = False
  validation_blocked: bool = False
  operation_is_destructive: bool = False

  def ready(self) -> bool:
    """Return True when execution can safely begin."""

    destructive_clear = (
      not self.operation_is_destructive or self.destructive_acknowledged
    )
    return (
      self.has_device
      and self.package_loaded
      and self.preflight_complete
      and not self.validation_blocked
      and self.warnings_acknowledged
      and destructive_clear
    )


@dataclass(frozen=True)
class PlatformEvent:
  """A state transition request emitted by platform-owned surfaces."""

  event_type: SessionEventType
  payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InspectionWorkflow:
  """Repo-owned inspect-only posture carried alongside the reviewed session."""

  posture: InspectionWorkflowPosture = InspectionWorkflowPosture.UNINSPECTED
  summary: str = 'No inspect-only workflow has run yet.'
  detect_ran: bool = False
  info_ran: bool = False
  pit_ran: bool = False
  evidence_ready: bool = False
  next_action: str = 'Run the inspect-only workflow to capture read-side evidence.'
  action_boundaries: Tuple[str, ...] = (
    'Inspect-only workflow remains read-side only and does not open a write path.',
    'Successful detection or PIT review must not be treated as transport readiness.',
  )
  notes: Tuple[str, ...] = ()
  captured_at_utc: Optional[str] = None


def _default_live_detection_session() -> 'LiveDetectionSession':
  """Lazily build the default unhydrated live-detection session."""

  from calamum_vulcan.domain.live_device.model import LiveDetectionSession

  return LiveDetectionSession.unhydrated()


@dataclass(frozen=True)
class PlatformSession:
  """The immutable session snapshot consumed by the future GUI shell."""

  phase: SessionPhase = SessionPhase.NO_DEVICE
  guards: GuardState = field(default_factory=GuardState)
  device_id: Optional[str] = None
  product_code: Optional[str] = None
  package_id: Optional[str] = None
  package_risk: Optional[str] = None
  mode: Optional[str] = None
  live_detection: 'LiveDetectionSession' = field(
    default_factory=_default_live_detection_session
  )
  inspection: InspectionWorkflow = field(default_factory=InspectionWorkflow)
  failure_reason: Optional[str] = None
  last_event: Optional[SessionEventType] = None
  preflight_notes: Tuple[str, ...] = ()