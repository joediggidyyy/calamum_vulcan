"""Runtime-readiness helpers for bounded execution sessions."""

from __future__ import annotations

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