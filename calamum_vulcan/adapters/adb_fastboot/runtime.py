"""Runtime helpers for the Calamum Vulcan ADB/Fastboot companion seam."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable
from typing import Optional

from .model import AndroidToolsCommandPlan
from .model import AndroidToolsNormalizedTrace
from .model import AndroidToolsProcessResult
from .normalizer import normalize_android_tools_result


ProcessRunner = Callable[[AndroidToolsCommandPlan], AndroidToolsProcessResult]
PROCESS_TIMEOUT_SECONDS = 30


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
        seconds=PROCESS_TIMEOUT_SECONDS,
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