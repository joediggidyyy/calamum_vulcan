"""Safe-path contract vocabulary for Calamum Vulcan Sprint 0.4.0 work."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


SAFE_PATH_SCHEMA_VERSION = '0.4.0-fs4-01'
SAFE_PATH_CLOSE_SUITE_NAME = 'safe-path-close'
SAFE_PATH_EVIDENCE_REQUIREMENTS = (
  'deterministic_safe_path_close_bundle',
  'installed_artifact_validation',
  'shared_security_validation',
  'trusted_publication_rehearsal',
)


class SafePathScope(str, Enum):
  """How broad the current Sprint 0.4.0 safe-path claim is allowed to be."""

  UNDEFINED = 'undefined'
  BOUNDED = 'bounded'
  REVIEW_ONLY = 'review_only'
  OUT_OF_SCOPE = 'out_of_scope'


class SafePathOwnership(str, Enum):
  """Who currently owns the operator-visible path."""

  NATIVE = 'native'
  DELEGATED = 'delegated'
  FALLBACK = 'fallback'
  BLOCKED = 'blocked'


class SafePathReadiness(str, Enum):
  """How close a bounded path is to safe-path execution."""

  UNREVIEWED = 'unreviewed'
  READY = 'ready'
  NARROWED = 'narrowed'
  BLOCKED = 'blocked'


@dataclass(frozen=True)
class SafePathContract:
  """Foundation contract for Sprint 0.4.0 safe-path work."""

  schema_version: str = SAFE_PATH_SCHEMA_VERSION
  scope: SafePathScope = SafePathScope.BOUNDED
  ownership: SafePathOwnership = SafePathOwnership.BLOCKED
  readiness: SafePathReadiness = SafePathReadiness.UNREVIEWED
  closeout_suite_name: str = SAFE_PATH_CLOSE_SUITE_NAME
  fallback_visibility_required: bool = True
  evidence_requirements: Tuple[str, ...] = SAFE_PATH_EVIDENCE_REQUIREMENTS
  summary: str = (
    'Sprint 0.4.0 safe-path work begins as a bounded contract: native, '
    'delegated, fallback, and blocked lanes must remain explicit before '
    'any narrower execution claim is made.'
  )
  action_boundaries: Tuple[str, ...] = (
    'Do not claim default native transport in Sprint 0.4.0.',
    'Blocked or degraded alignment must stay visible instead of being flattened into generic support wording.',
    'Fallback engagement must remain explicit in UI, reporting, and closeout evidence.',
  )
