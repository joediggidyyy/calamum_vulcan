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
APP_ROOT = Path(__file__).resolve().parents[2]
WINDOWS_ASSET_ROOT = APP_ROOT / 'assets' / 'bin' / 'windows'
WINDOWS_PACKAGED_HEIMDALL_ROOT = WINDOWS_ASSET_ROOT / 'heimdall'
WINDOWS_PACKAGED_HEIMDALL_EXECUTABLE = (
  WINDOWS_PACKAGED_HEIMDALL_ROOT / 'heimdall.exe'
)
WINDOWS_MISSING_DLL_EXIT_CODES = frozenset((-1073741515, 3221225781))


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


@dataclass(frozen=True)
class HeimdallRuntimeProbe:
  """Bounded probe result for the packaged or resolved Heimdall runtime."""

  executable_name: str
  resolved_path: str
  resolution_source: str
  packaged_candidate: Optional[str]
  packaged_candidate_present: bool
  smoke_test_exit_code: Optional[int]
  smoke_test_summary: str
  stdout_lines: tuple[str, ...] = ()
  stderr_lines: tuple[str, ...] = ()
  available: bool = False


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


def packaged_heimdall_executable_path(
  executable: str = 'heimdall',
) -> Optional[Path]:
  """Return the packaged Heimdall executable path when it exists."""

  candidate = _packaged_executable_candidate(executable)
  if candidate is None or not candidate.exists():
    return None
  return candidate


def probe_heimdall_runtime(
  executable: str = 'heimdall',
) -> HeimdallRuntimeProbe:
  """Return a bounded readiness probe for the resolved Heimdall runtime."""

  packaged_candidate = _packaged_executable_candidate(executable)
  resolved_executable = _resolve_executable(executable)
  resolution_source = _heimdall_resolution_source(
    executable,
    resolved_executable,
    packaged_candidate,
  )
  packaged_candidate_present = (
    packaged_candidate is not None and packaged_candidate.exists()
  )
  stdout_lines = ()  # type: tuple[str, ...]
  stderr_lines = ()  # type: tuple[str, ...]
  smoke_test_exit_code = None  # type: Optional[int]

  resolved_path = Path(resolved_executable)
  if resolved_executable == executable and not resolved_path.exists():
    smoke_test_exit_code = 127
    stderr_lines = (_executable_not_available_message(),)
  else:
    try:
      completed = subprocess.run(
        [resolved_executable, 'version'],
        capture_output=True,
        check=False,
        cwd=_subprocess_cwd_for_executable(resolved_executable),
        encoding='utf-8',
        errors='replace',
        text=True,
        timeout=10,
        **_subprocess_window_suppression_kwargs(),
      )
      smoke_test_exit_code = completed.returncode
      stdout_lines = tuple(completed.stdout.splitlines())
      stderr_lines = tuple(completed.stderr.splitlines())
    except FileNotFoundError:
      smoke_test_exit_code = 127
      stderr_lines = (_executable_not_available_message(),)
    except subprocess.TimeoutExpired as error:
      smoke_test_exit_code = 124
      stdout_lines = _timeout_output_lines(getattr(error, 'output', None))
      stderr_lines = _timeout_output_lines(getattr(error, 'stderr', None))
      stderr_lines = _merged_error_lines(
        stderr_lines,
        ('Heimdall runtime probe timed out after 10 seconds.',),
      )

  if _is_windows_missing_dll_exit_code(smoke_test_exit_code):
    stderr_lines = _merged_error_lines(
      stderr_lines,
      _missing_dll_error_lines(resolution_source),
    )

  available = smoke_test_exit_code == 0
  return HeimdallRuntimeProbe(
    executable_name=executable,
    resolved_path=resolved_executable,
    resolution_source=resolution_source,
    packaged_candidate=(
      str(packaged_candidate) if packaged_candidate is not None else None
    ),
    packaged_candidate_present=packaged_candidate_present,
    smoke_test_exit_code=smoke_test_exit_code,
    smoke_test_summary=_probe_summary(
      smoke_test_exit_code,
      resolution_source,
    ),
    stdout_lines=stdout_lines,
    stderr_lines=stderr_lines,
    available=available,
  )


def _run_process(
  command_plan: HeimdallCommandPlan,
  fixture_name: str,
) -> HeimdallProcessResult:
  try:
    _prepare_command_filesystem(command_plan)
  except OSError as error:
    return HeimdallProcessResult(
      fixture_name=fixture_name,
      operation=command_plan.operation,
      exit_code=126,
      stderr_lines=(
        'Heimdall command filesystem preparation failed: {error}'.format(
          error=error,
        ),
      ),
    )
  resolved_executable = _resolve_executable(command_plan.executable)
  command = [resolved_executable] + list(_resolved_command_arguments(command_plan))
  timeout_seconds = _timeout_seconds_for_operation(command_plan.operation)
  try:
    completed = subprocess.run(
      command,
      capture_output=True,
      check=False,
      cwd=_subprocess_cwd_for_executable(resolved_executable),
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
        _executable_not_available_message(),
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

  stderr_lines = tuple(completed.stderr.splitlines())
  if _is_windows_missing_dll_exit_code(completed.returncode):
    stderr_lines = _merged_error_lines(
      stderr_lines,
      _missing_dll_error_lines(
        _heimdall_resolution_source(
          command_plan.executable,
          resolved_executable,
          _packaged_executable_candidate(command_plan.executable),
        )
      ),
    )

  return HeimdallProcessResult(
    fixture_name=fixture_name,
    operation=command_plan.operation,
    exit_code=completed.returncode,
    stdout_lines=tuple(completed.stdout.splitlines()),
    stderr_lines=stderr_lines,
  )


def _prepare_command_filesystem(command_plan: HeimdallCommandPlan) -> None:
  """Prepare any bounded filesystem destinations required by one command."""

  if command_plan.operation != HeimdallOperation.DOWNLOAD_PIT:
    return
  output_path = _resolved_download_pit_output_path(command_plan)
  if output_path is None:
    return
  output_path.parent.mkdir(parents=True, exist_ok=True)


def _resolved_command_arguments(
  command_plan: HeimdallCommandPlan,
) -> tuple[str, ...]:
  """Return subprocess arguments with live download-pit paths absolutized."""

  arguments = tuple(command_plan.arguments)
  if command_plan.operation != HeimdallOperation.DOWNLOAD_PIT:
    return arguments

  output_path = _resolved_download_pit_output_path(command_plan)
  if output_path is None:
    return arguments

  resolved_arguments = list(arguments)
  for index, argument in enumerate(arguments[:-1]):
    if argument != '--output':
      continue
    resolved_arguments[index + 1] = str(output_path)
    return tuple(resolved_arguments)
  return arguments


def _resolved_download_pit_output_path(
  command_plan: HeimdallCommandPlan,
) -> Optional[Path]:
  """Return the concrete download-pit output path used for subprocess execution."""

  output_path = _download_pit_output_path(command_plan)
  if output_path is None:
    return None
  if output_path.is_absolute():
    return output_path
  return (Path.cwd() / output_path).resolve()


def _download_pit_output_path(
  command_plan: HeimdallCommandPlan,
) -> Optional[Path]:
  """Return the output path configured for one download-pit command plan."""

  arguments = tuple(command_plan.arguments)
  for index, argument in enumerate(arguments[:-1]):
    if argument != '--output':
      continue
    return Path(arguments[index + 1])
  return None


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


def _subprocess_cwd_for_executable(resolved_executable: str) -> Optional[str]:
  """Return the executable directory when subprocesses need local DLL lookup."""

  candidate = Path(resolved_executable)
  if candidate.is_absolute() and candidate.exists():
    return str(candidate.parent)
  return None


def _resolve_executable(executable: str) -> str:
  """Resolve Heimdall from packaged assets, PATH, env vars, or install paths."""

  packaged_candidate = _packaged_executable_candidate(executable)
  if packaged_candidate is not None and packaged_candidate.exists():
    return str(packaged_candidate)

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


def _packaged_executable_candidate(executable: str) -> Optional[Path]:
  """Return the packaged Heimdall candidate path for one executable name."""

  executable_name = Path(str(executable)).name.lower()
  if executable_name not in ('heimdall', 'heimdall.exe'):
    return None
  if os.name == 'nt':
    return WINDOWS_PACKAGED_HEIMDALL_EXECUTABLE
  return None


def _heimdall_resolution_source(
  executable: str,
  resolved_executable: str,
  packaged_candidate: Optional[Path],
) -> str:
  """Return the source label for one resolved Heimdall executable path."""

  if packaged_candidate is not None and Path(resolved_executable) == packaged_candidate:
    return 'packaged-asset'
  if resolved_executable == executable:
    return 'unresolved'
  return 'path-or-env'


def _executable_not_available_message() -> str:
  """Return one consistent not-available runtime message."""

  if os.name == 'nt':
    return (
      'Heimdall executable is not available from packaged assets, PATH, or '
      'standard Windows install locations for bounded runtime execution.'
    )
  return 'Heimdall executable is not available on PATH for bounded runtime execution.'


def _missing_dll_error_lines(
  resolution_source: str,
) -> tuple[str, ...]:
  """Return operator-facing guidance for Windows missing-DLL runtime failures."""

  if resolution_source == 'packaged-asset':
    return (
      'Packaged Heimdall runtime could not start because Windows reported a missing DLL dependency (0xC0000135).',
      'Verify the bundled companion files beside the packaged executable and install the Microsoft Visual C++ 2012 x86 runtime on this host before live PIT or flash execution.',
    )
  return (
    'Heimdall executable could not start because Windows reported a missing DLL dependency (0xC0000135).',
    'Verify the resolved Heimdall installation includes its companion DLLs and install the Microsoft Visual C++ 2012 x86 runtime on this host before live PIT or flash execution.',
  )


def _merged_error_lines(
  existing: tuple[str, ...],
  additions: tuple[str, ...],
) -> tuple[str, ...]:
  """Return one deduplicated tuple of stderr guidance lines."""

  merged = list(existing)
  for line in additions:
    if line not in merged:
      merged.append(line)
  return tuple(merged)


def _probe_summary(
  exit_code: Optional[int],
  resolution_source: str,
) -> str:
  """Return one short summary for a Heimdall runtime probe result."""

  if exit_code == 0:
    return 'Heimdall runtime probe executed successfully.'
  if exit_code == 127:
    if resolution_source == 'packaged-asset':
      return 'Packaged Heimdall runtime asset was expected but could not be executed.'
    return 'Heimdall runtime probe could not resolve an executable.'
  if exit_code == 124:
    return 'Heimdall runtime probe timed out.'
  if _is_windows_missing_dll_exit_code(exit_code):
    if resolution_source == 'packaged-asset':
      return 'Packaged Heimdall runtime resolved, but Windows could not load one or more runtime DLL dependencies.'
    return 'Resolved Heimdall executable could not start because Windows reported a missing DLL dependency.'
  return 'Heimdall runtime probe failed with exit code {code}.'.format(code=exit_code)


def _is_windows_missing_dll_exit_code(exit_code: Optional[int]) -> bool:
  """Return whether the exit code matches the Windows missing-DLL failure."""

  return exit_code in WINDOWS_MISSING_DLL_EXIT_CODES


def _timeout_seconds_for_operation(operation: HeimdallOperation) -> int:
  """Return the bounded timeout for one Heimdall operation."""

  operation_key = getattr(operation, 'value', str(operation))
  return min(
    PROCESS_TIMEOUT_SECONDS,
    int(OPERATION_TIMEOUT_SECONDS.get(operation_key, PROCESS_TIMEOUT_SECONDS)),
  )
