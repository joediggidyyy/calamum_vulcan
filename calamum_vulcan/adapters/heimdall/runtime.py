"""Runtime helpers that apply bounded Heimdall traces to platform state."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.flash_plan import ReviewedFlashPlan
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import RuntimeSessionRejected
from calamum_vulcan.domain.state import ensure_safe_path_runtime_ready
from calamum_vulcan.domain.state import ensure_runtime_ready
from calamum_vulcan.domain.state import replay_events

from .builder import build_flash_command_plan_from_reviewed_plan
from .model import HeimdallCommandPlan
from .model import HeimdallOperation
from .model import HeimdallNormalizedTrace
from .model import HeimdallProcessResult
from .normalizer import normalize_heimdall_result


ProcessRunner = Callable[[HeimdallCommandPlan], HeimdallProcessResult]
PROCESS_TIMEOUT_SECONDS = 120
OPERATION_TIMEOUT_SECONDS = {
  'detect': 15,
  'print_pit': 30,
  'download_pit': 45,
  'flash': PROCESS_TIMEOUT_SECONDS,
}


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
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
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
  ensure_safe_path_runtime_ready(
    session,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
  )
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
  command = [_resolve_executable(command_plan.executable)] + list(command_plan.arguments)
  timeout_seconds = _timeout_seconds_for_operation(command_plan.operation)
  try:
    completed = subprocess.run(
      command,
      capture_output=True,
      check=False,
      encoding='utf-8',
      errors='replace',
      text=True,
      timeout=timeout_seconds,
      **_subprocess_window_suppression_kwargs(),
    )
  except FileNotFoundError:
    return HeimdallProcessResult(
      fixture_name=fixture_name,
      operation=command_plan.operation,
      exit_code=127,
      stderr_lines=(
        'Heimdall executable is not available on PATH or in standard Windows install locations for bounded runtime execution.',
      ),
    )
  except subprocess.TimeoutExpired as error:
    stderr_lines = _timeout_output_lines(getattr(error, 'stderr', None))
    stdout_lines = _timeout_output_lines(getattr(error, 'output', None))
    timeout_message = (
      'Heimdall command timed out after {seconds} seconds.'.format(
        seconds=timeout_seconds,
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


def _subprocess_window_suppression_kwargs() -> Dict[str, object]:
  """Return platform-specific subprocess options that avoid terminal ghosts."""

  if os.name != 'nt':
    return {}

  kwargs = {}  # type: Dict[str, object]
  creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
  if creationflags:
    kwargs['creationflags'] = creationflags

  startupinfo_factory = getattr(subprocess, 'STARTUPINFO', None)
  use_show_window = getattr(subprocess, 'STARTF_USESHOWWINDOW', 0)
  hide_window = getattr(subprocess, 'SW_HIDE', 0)
  if startupinfo_factory is not None and use_show_window:
    startupinfo = startupinfo_factory()
    startupinfo.dwFlags |= use_show_window
    startupinfo.wShowWindow = hide_window
    kwargs['startupinfo'] = startupinfo
  return kwargs


def _resolve_executable(executable: str) -> str:
  """Resolve Heimdall from PATH, optional env vars, or common install locations."""

  resolved = shutil.which(executable)
  if resolved is not None:
    return resolved

  extension = '.exe' if os.name == 'nt' else ''
  candidate_name = executable + extension
  candidates = []  # type: list[Path]

  heimdall_path = os.getenv('HEIMDALL_PATH')
  if heimdall_path:
    candidates.append(Path(heimdall_path))

  heimdall_home = os.getenv('HEIMDALL_HOME')
  if heimdall_home:
    candidates.append(Path(heimdall_home) / candidate_name)
    candidates.append(Path(heimdall_home) / 'bin' / candidate_name)

  if os.name == 'nt':
    chocolatey_install = os.getenv('ChocolateyInstall')
    if chocolatey_install:
      candidates.append(Path(chocolatey_install) / 'bin' / candidate_name)
    program_data = os.getenv('ProgramData')
    if program_data:
      candidates.append(Path(program_data) / 'chocolatey' / 'bin' / candidate_name)
    scoop_root = os.getenv('SCOOP')
    if scoop_root:
      candidates.append(Path(scoop_root) / 'shims' / candidate_name)
    user_profile = os.getenv('USERPROFILE')
    if user_profile:
      candidates.append(Path(user_profile) / 'scoop' / 'shims' / candidate_name)
    for env_var in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
      base = os.getenv(env_var)
      if not base:
        continue
      base_path = Path(base)
      candidates.extend(
        (
          base_path / 'Heimdall' / candidate_name,
          base_path / 'Heimdall Suite' / candidate_name,
          base_path / 'Programs' / 'Heimdall' / candidate_name,
          base_path / 'Programs' / 'Heimdall Suite' / candidate_name,
        )
      )
  else:
    candidates.extend(
      (
        Path('/usr/bin') / executable,
        Path('/usr/local/bin') / executable,
        Path('/opt/homebrew/bin') / executable,
      )
    )

  for candidate in candidates:
    if candidate.exists():
      return str(candidate)
  return executable


def _timeout_seconds_for_operation(operation: HeimdallOperation) -> int:
  """Return the bounded timeout for one Heimdall operation."""

  operation_key = getattr(operation, 'value', str(operation))
  return min(
    PROCESS_TIMEOUT_SECONDS,
    int(OPERATION_TIMEOUT_SECONDS.get(operation_key, PROCESS_TIMEOUT_SECONDS)),
  )
