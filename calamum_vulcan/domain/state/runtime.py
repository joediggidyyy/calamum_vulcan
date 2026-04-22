"""Runtime-readiness helpers for bounded execution sessions."""

from __future__ import annotations

from typing import Optional

from calamum_vulcan.domain.safe_path import SafePathOwnership
from calamum_vulcan.domain.safe_path import SafePathReadiness

from .authority import SessionLaunchPath
from .authority import build_session_authority_snapshot
from .model import PlatformSession
from .model import SessionPhase


class RuntimeSessionRejected(ValueError):
  """Raised when a bounded runtime session violates platform guardrails."""


def ensure_runtime_ready(session: PlatformSession) -> None:
  """Reject bounded runtime execution unless the reviewed session is ready."""

  if session.phase != SessionPhase.READY_TO_EXECUTE:
    raise RuntimeSessionRejected(
      'Bounded runtime execution can only start from ready_to_execute.'
    )
  if not session.guards.ready():
    raise RuntimeSessionRejected(
      'Bounded runtime execution cannot start while session guards remain open.'
    )


def ensure_safe_path_runtime_ready(
  session: PlatformSession,
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
):
  """Reject bounded runtime execution unless authority selects a ready safe-path lane."""

  ensure_runtime_ready(session)
  authority = build_session_authority_snapshot(
    session,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    pit_required_for_safe_path=True,
  )
  if authority.selected_launch_path != SessionLaunchPath.SAFE_PATH_CANDIDATE:
    raise RuntimeSessionRejected(
      'Bounded safe-path runtime requires session authority to select a safe-path candidate before transport.'
    )
  if authority.ownership not in (
    SafePathOwnership.DELEGATED,
    SafePathOwnership.NATIVE,
  ):
    raise RuntimeSessionRejected(
      'Bounded safe-path runtime requires delegated or native path ownership, not {ownership}.'.format(
        ownership=authority.ownership.value,
      )
    )
  if authority.readiness != SafePathReadiness.READY:
    if authority.block_reason is not None:
      raise RuntimeSessionRejected(
        'Bounded safe-path runtime is not ready: {reason}'.format(
          reason=authority.block_reason,
        )
      )
    raise RuntimeSessionRejected(
      'Bounded safe-path runtime requires ready authority before transport.'
    )
  return authority