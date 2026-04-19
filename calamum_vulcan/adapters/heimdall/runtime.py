"""Runtime helpers that apply normalized Heimdall traces to platform state."""

from __future__ import annotations

from typing import Tuple

from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import replay_events

from .model import HeimdallCommandPlan
from .model import HeimdallNormalizedTrace
from .model import HeimdallProcessResult
from .normalizer import normalize_heimdall_result


def apply_heimdall_trace(
  session: PlatformSession,
  trace: HeimdallNormalizedTrace,
) -> PlatformSession:
  """Apply one normalized Heimdall trace to the immutable platform session."""

  if not trace.platform_events:
    return session
  return replay_events(trace.platform_events, initial=session)


def replay_heimdall_process_result(
  session: PlatformSession,
  command_plan: HeimdallCommandPlan,
  process_result: HeimdallProcessResult,
) -> Tuple[PlatformSession, HeimdallNormalizedTrace]:
  """Normalize one process result and replay its platform events into session state."""

  trace = normalize_heimdall_result(command_plan, process_result)
  return apply_heimdall_trace(session, trace), trace
