"""Repo-owned live-device detection and identity contracts."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple


LIVE_DEVICE_SCHEMA_VERSION = '0.3.0-fs3-03'
LIVE_PATH_IDENTITY_SCHEMA_VERSION = '0.4.0-fs4-04'


class LiveDeviceSource(str, Enum):
  """Supported live-device sources owned by the platform."""

  ADB = 'adb'
  FASTBOOT = 'fastboot'
  USB = 'usb'
  HEIMDALL = 'heimdall'


class LiveDetectionState(str, Enum):
  """Normalized live-detection states exposed above raw adapter traces."""

  UNHYDRATED = 'unhydrated'
  DETECTED = 'detected'
  ATTENTION = 'attention'
  CLEARED = 'cleared'
  FAILED = 'failed'


class LiveFallbackPosture(str, Enum):
  """Fallback posture recorded for one live-detection attempt."""

  NOT_NEEDED = 'not_needed'
  NEEDED = 'needed'
  ENGAGED = 'engaged'


class LiveDeviceSupportPosture(str, Enum):
  """Support posture for one live device identity snapshot."""

  SUPPORTED = 'supported'
  UNPROFILED = 'unprofiled'
  IDENTITY_INCOMPLETE = 'identity_incomplete'


class LiveDeviceInfoState(str, Enum):
  """Collection posture for bounded live device info snapshots."""

  NOT_COLLECTED = 'not_collected'
  CAPTURED = 'captured'
  PARTIAL = 'partial'
  UNAVAILABLE = 'unavailable'
  FAILED = 'failed'


class LivePathOwnership(str, Enum):
  """Ownership label for the current live or delegated path."""

  NONE = 'none'
  NATIVE = 'native'
  DELEGATED = 'delegated'
  FALLBACK = 'fallback'


class LiveIdentityConfidence(str, Enum):
  """How much repo-owned identity is currently available for one live path."""

  UNAVAILABLE = 'unavailable'
  SERIAL_ONLY = 'serial_only'
  PRODUCT_RESOLVED = 'product_resolved'
  PROFILED = 'profiled'


@dataclass(frozen=True)
class LivePathIdentity:
  """Repo-owned identity surface for one native, delegated, or fallback lane."""

  schema_version: str = LIVE_PATH_IDENTITY_SCHEMA_VERSION
  ownership: LivePathOwnership = LivePathOwnership.NONE
  path_label: str = 'No Live Path'
  delegated_path_label: str = 'none'
  mode_label: str = 'No Live Mode'
  identity_confidence: LiveIdentityConfidence = LiveIdentityConfidence.UNAVAILABLE
  summary: str = 'No live or fallback identity is currently active.'
  operator_guidance: Tuple[str, ...] = ()

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this path identity."""

    return asdict(self)


@dataclass(frozen=True)
class LiveDeviceSnapshot:
  """One repo-owned snapshot of a live device identity."""

  source: LiveDeviceSource
  serial: str
  connection_state: str
  transport: str
  mode: str
  command_ready: bool
  product_code: Optional[str] = None
  model_name: Optional[str] = None
  device_name: Optional[str] = None
  canonical_product_code: Optional[str] = None
  marketing_name: Optional[str] = None
  registry_match_kind: str = 'unknown'
  support_posture: LiveDeviceSupportPosture = (
    LiveDeviceSupportPosture.IDENTITY_INCOMPLETE
  )
  info_state: LiveDeviceInfoState = LiveDeviceInfoState.NOT_COLLECTED
  info_source_label: Optional[str] = None
  manufacturer: Optional[str] = None
  brand: Optional[str] = None
  android_version: Optional[str] = None
  build_id: Optional[str] = None
  security_patch: Optional[str] = None
  build_fingerprint: Optional[str] = None
  bootloader_version: Optional[str] = None
  build_tags: Optional[str] = None
  capability_hints: Tuple[str, ...] = ()
  operator_guidance: Tuple[str, ...] = ()

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this snapshot."""

    return asdict(self)


@dataclass(frozen=True)
class LiveDetectionSession:
  """Repo-owned live-detection truth carried through session and shell layers."""

  schema_version: str = LIVE_DEVICE_SCHEMA_VERSION
  state: LiveDetectionState = LiveDetectionState.UNHYDRATED
  summary: str = 'No live device probe has run yet.'
  source: Optional[LiveDeviceSource] = None
  source_labels: Tuple[str, ...] = ()
  fallback_posture: LiveFallbackPosture = LiveFallbackPosture.NOT_NEEDED
  fallback_reason: Optional[str] = None
  snapshot: Optional[LiveDeviceSnapshot] = None
  path_identity: LivePathIdentity = field(default_factory=LivePathIdentity)
  notes: Tuple[str, ...] = ()

  @classmethod
  def unhydrated(cls) -> 'LiveDetectionSession':
    """Return the default pre-probe live-detection state."""

    return cls()

  @classmethod
  def cleared(
    cls,
    summary: str = 'No live device is currently detected.',
    source: Optional[LiveDeviceSource] = None,
    source_labels: Tuple[str, ...] = (),
    fallback_posture: LiveFallbackPosture = LiveFallbackPosture.NOT_NEEDED,
    fallback_reason: Optional[str] = None,
    notes: Tuple[str, ...] = (),
  ) -> 'LiveDetectionSession':
    """Return a cleared live-detection state after a completed probe."""

    return cls(
      state=LiveDetectionState.CLEARED,
      summary=summary,
      source=source,
      source_labels=source_labels,
      fallback_posture=fallback_posture,
      fallback_reason=fallback_reason,
      notes=notes,
    )

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this detection session."""

    return asdict(self)

  @property
  def device_present(self) -> bool:
    """Return whether a live device snapshot is currently available."""

    return self.snapshot is not None

  @property
  def command_ready(self) -> bool:
    """Return whether the active live device can accept command traffic."""

    return bool(self.snapshot is not None and self.snapshot.command_ready)
