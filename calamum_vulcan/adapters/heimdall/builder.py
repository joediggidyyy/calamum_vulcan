"""Command-plan builders for the Calamum Vulcan Heimdall adapter seam."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.package import RebootPolicy

from .model import HeimdallCapability
from .model import HeimdallCommandPlan
from .model import HeimdallOperation


def build_detect_device_command_plan() -> HeimdallCommandPlan:
  """Build the sanctioned Heimdall detect command plan."""

  arguments = ('detect',)
  return _command_plan(
    HeimdallCapability.DETECT_DEVICE,
    HeimdallOperation.DETECT,
    arguments,
  )


def build_print_pit_command_plan() -> HeimdallCommandPlan:
  """Build the sanctioned Heimdall print-pit command plan."""

  arguments = ('print-pit',)
  return _command_plan(
    HeimdallCapability.PRINT_PIT,
    HeimdallOperation.PRINT_PIT,
    arguments,
  )


def build_download_pit_command_plan(
  output_path: str = 'device.pit',
) -> HeimdallCommandPlan:
  """Build the sanctioned Heimdall download-pit command plan."""

  arguments = ('download-pit', '--output', str(Path(output_path)))
  return _command_plan(
    HeimdallCapability.DOWNLOAD_PIT,
    HeimdallOperation.DOWNLOAD_PIT,
    arguments,
  )


def build_flash_command_plan(
  package_assessment: PackageManifestAssessment,
) -> HeimdallCommandPlan:
  """Build the sanctioned Heimdall flash command plan from package truth."""

  if not package_assessment.partitions:
    raise ValueError('Flash command plan requires at least one partition entry.')

  arguments = ['flash']
  for partition in package_assessment.partitions:
    arguments.append('--' + partition.partition_name.upper())
    arguments.append(partition.file_name)
  if package_assessment.repartition_allowed:
    arguments.append('--repartition')
  if package_assessment.reboot_policy == RebootPolicy.NO_REBOOT:
    arguments.append('--no-reboot')

  return _command_plan(
    HeimdallCapability.FLASH_PACKAGE,
    HeimdallOperation.FLASH,
    tuple(arguments),
  )


def build_command_plan_for_operation(
  operation: HeimdallOperation,
  package_assessment: Optional[PackageManifestAssessment] = None,
  output_path: str = 'device.pit',
) -> HeimdallCommandPlan:
  """Build one sanctioned command plan for the requested Heimdall operation."""

  if operation == HeimdallOperation.DETECT:
    return build_detect_device_command_plan()
  if operation == HeimdallOperation.PRINT_PIT:
    return build_print_pit_command_plan()
  if operation == HeimdallOperation.DOWNLOAD_PIT:
    return build_download_pit_command_plan(output_path=output_path)
  if operation == HeimdallOperation.FLASH:
    if package_assessment is None:
      raise ValueError('Flash operation requires a package assessment.')
    return build_flash_command_plan(package_assessment)
  raise ValueError('Unsupported Heimdall operation: {operation}'.format(
    operation=operation,
  ))


def _command_plan(
  capability: HeimdallCapability,
  operation: HeimdallOperation,
  arguments: Tuple[str, ...],
) -> HeimdallCommandPlan:
  display_command = ' '.join(('heimdall',) + arguments)
  return HeimdallCommandPlan(
    capability=capability,
    operation=operation,
    executable='heimdall',
    arguments=arguments,
    display_command=display_command,
  )
