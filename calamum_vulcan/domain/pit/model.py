"""Repo-owned PIT acquisition, parsing, and inspection contracts."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple


PIT_SCHEMA_VERSION = '0.3.0-fs3-04'


class PitSource(str, Enum):
  """Supported PIT acquisition sources for the current read-side slice."""

  HEIMDALL_PRINT_PIT = 'heimdall_print_pit'
  HEIMDALL_DOWNLOAD_PIT = 'heimdall_download_pit'


class PitInspectionState(str, Enum):
  """Normalized inspection states exposed above raw PIT adapter output."""

  NOT_COLLECTED = 'not_collected'
  CAPTURED = 'captured'
  PARTIAL = 'partial'
  MALFORMED = 'malformed'
  FAILED = 'failed'


class PitFallbackPosture(str, Enum):
  """Fallback posture recorded for the current PIT inspection path."""

  NOT_NEEDED = 'not_needed'
  NEEDED = 'needed'
  ENGAGED = 'engaged'


class PitPackageAlignment(str, Enum):
  """Alignment between observed PIT truth and reviewed package truth."""

  NOT_REVIEWED = 'not_reviewed'
  MATCHED = 'matched'
  MISMATCHED = 'mismatched'
  MISSING_REVIEWED = 'missing_reviewed'
  MISSING_OBSERVED = 'missing_observed'


class PitDeviceAlignment(str, Enum):
  """Alignment between observed PIT truth and session device identity."""

  NOT_PROVIDED = 'not_provided'
  MATCHED = 'matched'
  MISMATCHED = 'mismatched'


@dataclass(frozen=True)
class PitPartitionRecord:
  """One repo-owned partition row parsed from PIT inspection output."""

  index: int
  partition_name: str
  file_name: Optional[str] = None
  block_count: Optional[int] = None
  file_offset: Optional[int] = None


@dataclass(frozen=True)
class PitInspection:
  """Repo-owned PIT acquisition and inspection truth for one review path."""

  schema_version: str = PIT_SCHEMA_VERSION
  state: PitInspectionState = PitInspectionState.NOT_COLLECTED
  source: Optional[PitSource] = None
  summary: str = 'No PIT inspection has been captured yet.'
  fallback_posture: PitFallbackPosture = PitFallbackPosture.NOT_NEEDED
  fallback_reason: Optional[str] = None
  observed_product_code: Optional[str] = None
  canonical_product_code: Optional[str] = None
  marketing_name: Optional[str] = None
  registry_match_kind: str = 'unknown'
  observed_pit_fingerprint: Optional[str] = None
  reviewed_pit_fingerprint: Optional[str] = None
  package_alignment: PitPackageAlignment = PitPackageAlignment.NOT_REVIEWED
  device_alignment: PitDeviceAlignment = PitDeviceAlignment.NOT_PROVIDED
  download_path: Optional[str] = None
  entry_count: int = 0
  partition_names: Tuple[str, ...] = ()
  entries: Tuple[PitPartitionRecord, ...] = ()
  notes: Tuple[str, ...] = ()
  operator_guidance: Tuple[str, ...] = ()

  @classmethod
  def not_collected(cls) -> 'PitInspection':
    """Return the default pre-inspection state."""

    return cls()

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this PIT inspection."""

    return asdict(self)
