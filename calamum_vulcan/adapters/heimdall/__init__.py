"""Heimdall adapter seam for Calamum Vulcan."""

from importlib import import_module

from .model import HeimdallCapability
from .model import HeimdallCommandPlan
from .model import HeimdallNormalizedTrace
from .model import HeimdallOperation
from .model import HeimdallProcessResult
from .model import HeimdallTraceState


_LAZY_EXPORTS = {
  'build_command_plan_for_operation': '.builder',
  'build_detect_device_command_plan': '.builder',
  'build_download_pit_command_plan': '.builder',
  'build_flash_command_plan': '.builder',
  'build_flash_command_plan_from_reviewed_plan': '.builder',
  'build_print_pit_command_plan': '.builder',
  'normalize_heimdall_result': '.normalizer',
  'BoundedHeimdallRuntimeResult': '.runtime',
  'HeimdallRuntimeProbe': '.runtime',
  'PROCESS_TIMEOUT_SECONDS': '.runtime',
  'apply_heimdall_trace': '.runtime',
  'execute_heimdall_command': '.runtime',
  'packaged_heimdall_executable_path': '.runtime',
  'probe_heimdall_runtime': '.runtime',
  'replay_heimdall_process_result': '.runtime',
  'run_bounded_heimdall_flash_session': '.runtime',
}


def __getattr__(name: str):
  """Lazily resolve builder, normalizer, and runtime exports."""

  module_name = _LAZY_EXPORTS.get(name)
  if module_name is None:
    raise AttributeError(
      "module '{module}' has no attribute '{name}'".format(
        module=__name__,
        name=name,
      )
    )
  module = import_module(module_name, __name__)
  value = getattr(module, name)
  globals()[name] = value
  return value

__all__ = [
  'HeimdallCapability',
  'HeimdallCommandPlan',
  'HeimdallNormalizedTrace',
  'HeimdallOperation',
  'HeimdallProcessResult',
  'HeimdallTraceState',
  'BoundedHeimdallRuntimeResult',
  'HeimdallRuntimeProbe',
  'PROCESS_TIMEOUT_SECONDS',
  'apply_heimdall_trace',
  'build_command_plan_for_operation',
  'build_detect_device_command_plan',
  'build_download_pit_command_plan',
  'build_flash_command_plan',
  'build_flash_command_plan_from_reviewed_plan',
  'build_print_pit_command_plan',
  'execute_heimdall_command',
  'normalize_heimdall_result',
  'packaged_heimdall_executable_path',
  'probe_heimdall_runtime',
  'replay_heimdall_process_result',
  'run_bounded_heimdall_flash_session',
]
