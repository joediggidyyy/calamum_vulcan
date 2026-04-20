"""Runtime helpers that apply bounded Heimdall traces to platform state."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Callable
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import RuntimeSessionRejected
from calamum_vulcan.domain.state import ensure_runtime_ready
from calamum_vulcan.domain.state import replay_events

from .builder import build_flash_command_plan_from_reviewed_plan
from .model import HeimdallCommandPlan
from .model import HeimdallNormalizedTrace
from .model import HeimdallProcessResult
from .normalizer import normalize_heimdall_result


ProcessRunner = Callable[[HeimdallCommandPlan], HeimdallProcessResult]
PROCESS_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class BoundedHeimdallRuntimeResult:
  """One bounded runtime-session result over the Heimdall adapter seam."""

  session: PlatformSession
  trace: HeimdallNormalizedTrace
  command_plan: HeimdallCommandPlan
  reviewed_plan_id: str
  snapshot_id: Optional[str]
  execution_source: str
  runtime_policy: str = 'bounded_reviewed_flash_session'
  transcript_policy: str = 'preserve_bounded_transport_transcript'

  @property
  def summary(self) -> str:
    """Return an operator-facing runtime summary."""

    return (
      'Bounded Heimdall runtime session executed through {source} and '
      'normalized into platform-owned state.'.format(
        source=self.execution_source.replace('_', ' '),
      )
    )


def execute_heimdall_command(
  command_plan: HeimdallCommandPlan,
  runner: Optional[ProcessRunner] = None,
  fixture_name: str = 'live-process',
) -> HeimdallNormalizedTrace:
  """Execute one bounded Heimdall command and normalize the result."""

  if runner is not None:
    process_result = runner(command_plan)
  else:
    process_result = _run_process(command_plan, fixture_name)
  return normalize_heimdall_result(command_plan, process_result)


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


def run_bounded_heimdall_flash_session(
  session: PlatformSession,
  reviewed_flash_plan: ReviewedFlashPlan,
  runner: Optional[ProcessRunner] = None,
  fixture_name: str = 'live-process',
) -> BoundedHeimdallRuntimeResult:
  """Run one bounded reviewed flash session over the Heimdall adapter seam."""

  if reviewed_flash_plan.transport_backend != 'heimdall':
    raise RuntimeSessionRejected(
      'Bounded Heimdall runtime requires a reviewed flash plan for the Heimdall backend.'
    )
  if not reviewed_flash_plan.ready_for_transport:
    raise RuntimeSessionRejected(
      'Bounded Heimdall runtime requires a transport-ready reviewed flash plan.'
    )
  if (
    reviewed_flash_plan.source_kind != 'fixture'
    and reviewed_flash_plan.snapshot_id is None
  ):
    raise RuntimeSessionRejected(
      'Bounded Heimdall runtime requires a reviewed snapshot identity.'
    )

  ensure_runtime_ready(session)
  command_plan = build_flash_command_plan_from_reviewed_plan(reviewed_flash_plan)
  trace = execute_heimdall_command(
    command_plan,
    runner=runner,
    fixture_name=fixture_name,
  )
  execution_source = 'explicit_runner' if runner is not None else 'bounded_subprocess'
  return BoundedHeimdallRuntimeResult(
    session=apply_heimdall_trace(session, trace),
    trace=trace,
    command_plan=command_plan,
    reviewed_plan_id=reviewed_flash_plan.plan_id,
    snapshot_id=reviewed_flash_plan.snapshot_id,
    execution_source=execution_source,
  )


def _run_process(
  command_plan: HeimdallCommandPlan,
  fixture_name: str,
) -> HeimdallProcessResult:
  command = [command_plan.executable] + list(command_plan.arguments)
  try:
    completed = subprocess.run(
      command,
      capture_output=True,
      check=False,
      encoding='utf-8',
      errors='replace',
      text=True,
      timeout=PROCESS_TIMEOUT_SECONDS,
    )
  except FileNotFoundError:
    return HeimdallProcessResult(
      fixture_name=fixture_name,
      operation=command_plan.operation,
      exit_code=127,
      stderr_lines=(
        'Heimdall executable is not available on PATH for bounded runtime execution.',
      ),
    )
  except subprocess.TimeoutExpired as error:
    stderr_lines = _timeout_output_lines(getattr(error, 'stderr', None))
    stdout_lines = _timeout_output_lines(getattr(error, 'output', None))
    timeout_message = (
      'Heimdall command timed out after {seconds} seconds.'.format(
        seconds=PROCESS_TIMEOUT_SECONDS,
      )
    )
    if stderr_lines:
      stderr_lines = stderr_lines + (timeout_message,)
    else:
      stderr_lines = (timeout_message,)
    return HeimdallProcessResult(
      fixture_name=fixture_name,
      operation=command_plan.operation,
      exit_code=124,
      stdout_lines=stdout_lines,
      stderr_lines=stderr_lines,
    )

  return HeimdallProcessResult(
    fixture_name=fixture_name,
    operation=command_plan.operation,
    exit_code=completed.returncode,
    stdout_lines=tuple(completed.stdout.splitlines()),
    stderr_lines=tuple(completed.stderr.splitlines()),
  )


def _timeout_output_lines(value: object) -> tuple[str, ...]:
  if isinstance(value, bytes):
    value = value.decode('utf-8', errors='replace')
  if isinstance(value, str):
    return tuple(value.splitlines())
  return ()
