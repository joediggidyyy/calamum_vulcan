"""Runtime helpers for the Calamum Vulcan ADB/Fastboot companion seam."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable
from typing import Dict
from typing import Optional

from .model import AndroidToolsCommandPlan
from .model import AndroidToolsNormalizedTrace
from .model import AndroidToolsProcessResult
from .normalizer import normalize_android_tools_result


ProcessRunner = Callable[[AndroidToolsCommandPlan], AndroidToolsProcessResult]
PROCESS_TIMEOUT_SECONDS = 30
OPERATION_TIMEOUT_SECONDS = {
  'adb_devices': 8,
  'fastboot_devices': 8,
  'adb_getprop': 10,
  'adb_reboot': 15,
  'fastboot_reboot': 15,
}


def execute_android_tools_command(
  command_plan: AndroidToolsCommandPlan,
  runner: Optional[ProcessRunner] = None,
  fixture_name: str = 'live-process',
) -> AndroidToolsNormalizedTrace:
  """Execute one bounded companion command and normalize the result."""

  if runner is not None:
    process_result = runner(command_plan)
  else:
    process_result = _run_process(command_plan, fixture_name)
  return normalize_android_tools_result(command_plan, process_result)


def _run_process(
  command_plan: AndroidToolsCommandPlan,
  fixture_name: str,
) -> AndroidToolsProcessResult:
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
    return AndroidToolsProcessResult(
      fixture_name=fixture_name,
      operation=command_plan.operation,
      backend=command_plan.backend,
      exit_code=127,
      stderr_lines=(
        '{backend} executable is not available on PATH or in standard Android SDK locations.'.format(
          backend=command_plan.backend.value,
        ),
      ),
    )
  except subprocess.TimeoutExpired as error:
    stderr_lines = _timeout_output_lines(getattr(error, 'stderr', None))
    stdout_lines = _timeout_output_lines(getattr(error, 'output', None))
    timeout_message = (
      '{backend} command timed out after {seconds} seconds.'.format(
        backend=command_plan.backend.value,
        seconds=timeout_seconds,
      )
    )
    if stderr_lines:
      stderr_lines = stderr_lines + (timeout_message,)
    else:
      stderr_lines = (timeout_message,)
    return AndroidToolsProcessResult(
      fixture_name=fixture_name,
      operation=command_plan.operation,
      backend=command_plan.backend,
      exit_code=124,
      stdout_lines=stdout_lines,
      stderr_lines=stderr_lines,
    )

  return AndroidToolsProcessResult(
    fixture_name=fixture_name,
    operation=command_plan.operation,
    backend=command_plan.backend,
    exit_code=completed.returncode,
    stdout_lines=tuple(completed.stdout.splitlines()),
    stderr_lines=tuple(completed.stderr.splitlines()),
  )


def _timeout_seconds_for_operation(operation: AndroidToolsOperation) -> int:
  """Return the bounded timeout for one companion operation."""

  operation_key = getattr(operation, 'value', str(operation))
  return min(
    PROCESS_TIMEOUT_SECONDS,
    int(OPERATION_TIMEOUT_SECONDS.get(operation_key, PROCESS_TIMEOUT_SECONDS)),
  )


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
  """Resolve adb/fastboot from PATH or a standard Android SDK install."""

  resolved = shutil.which(executable)
  if resolved is not None:
    return resolved

  extension = '.exe' if os.name == 'nt' else ''
  candidate_name = executable + extension
  candidates = []  # type: list[Path]

  sdk_root = os.getenv('ANDROID_SDK_ROOT') or os.getenv('ANDROID_HOME')
  if sdk_root:
    candidates.append(Path(sdk_root) / 'platform-tools' / candidate_name)

  if os.name == 'nt':
    local_appdata = os.getenv('LOCALAPPDATA')
    if local_appdata:
      candidates.append(
        Path(local_appdata) / 'Android' / 'Sdk' / 'platform-tools' / candidate_name
      )
  else:
    candidates.append(Path.home() / 'Android' / 'Sdk' / 'platform-tools' / candidate_name)

  for candidate in candidates:
    if candidate.exists():
      return str(candidate)
  return executable


def _timeout_output_lines(value: object) -> tuple[str, ...]:
  if isinstance(value, bytes):
    value = value.decode('utf-8', errors='replace')
  if isinstance(value, str):
    return tuple(value.splitlines())
  return ()