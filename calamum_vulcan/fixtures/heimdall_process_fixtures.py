"""Mocked Heimdall process results for deterministic FS-07 validation."""

from __future__ import annotations

from typing import Dict
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallProcessResult


HEIMDALL_PROCESS_FIXTURES = {
  'detect-ready': HeimdallProcessResult(
    fixture_name='detect-ready',
    operation=HeimdallOperation.DETECT,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Detecting device...',
      'Device detected: device_id=samsung-galaxy-lab-04 product_code=SM-G991U mode=download',
      'Interface claim successful.',
    ),
  ),
  'detect-generic-ready': HeimdallProcessResult(
    fixture_name='detect-generic-ready',
    operation=HeimdallOperation.DETECT,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Initialising connection...',
      'Detecting device...',
      'Claiming interface...',
      'Setting up interface...',
      'Initialising protocol...',
      'Protocol initialisation successful.',
      'Detected device family hint: SM-G991U',
    ),
  ),
  'detect-late-warning': HeimdallProcessResult(
    fixture_name='detect-late-warning',
    operation=HeimdallOperation.DETECT,
    exit_code=1,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Initialising connection...',
      'Detecting device...',
      'Claiming interface...',
      'Detected device family hint: SM_G991U',
    ),
    stderr_lines=(
      'ERROR: Failed to claim interface',
    ),
  ),
  'detect-none': HeimdallProcessResult(
    fixture_name='detect-none',
    operation=HeimdallOperation.DETECT,
    exit_code=1,
    stderr_lines=(
      'ERROR: Failed to detect compatible download-mode device',
    ),
  ),
  'detect-runtime-failure': HeimdallProcessResult(
    fixture_name='detect-runtime-failure',
    operation=HeimdallOperation.DETECT,
    exit_code=127,
    stderr_lines=(
      'heimdall executable not available on PATH',
    ),
  ),
  'flash-success': HeimdallProcessResult(
    fixture_name='flash-success',
    operation=HeimdallOperation.FLASH,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Beginning session for package regional-match-demo',
      'Uploading RECOVERY (42%)',
      'Uploading RECOVERY (100%)',
      'Uploading VBMETA (100%)',
      'Flash completed successfully.',
    ),
  ),
  'flash-failure': HeimdallProcessResult(
    fixture_name='flash-failure',
    operation=HeimdallOperation.FLASH,
    exit_code=1,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Beginning session for package calamum-recovery-lab-001',
      'Uploading RECOVERY (61%)',
    ),
    stderr_lines=(
      'ERROR: USB transfer timeout during partition write',
    ),
  ),
  'flash-no-reboot-resume': HeimdallProcessResult(
    fixture_name='flash-no-reboot-resume',
    operation=HeimdallOperation.FLASH,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Beginning session for package calamum-recovery-lab-001',
      'Uploading RECOVERY (100%)',
      'Upload sequence complete; manual recovery boot required.',
      'Operator resumed workflow after manual recovery boot.',
      'Session finalized successfully.',
    ),
  ),
  'flash-no-reboot-pause': HeimdallProcessResult(
    fixture_name='flash-no-reboot-pause',
    operation=HeimdallOperation.FLASH,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Beginning session for package calamum-recovery-lab-001',
      'Uploading RECOVERY (100%)',
      'Upload sequence complete; manual recovery boot required.',
    ),
  ),
}  # type: Dict[str, HeimdallProcessResult]


def available_heimdall_process_fixtures() -> Tuple[str, ...]:
  """Return supported Heimdall process fixture names."""

  return tuple(HEIMDALL_PROCESS_FIXTURES.keys())


def load_heimdall_process_fixture(name: str) -> HeimdallProcessResult:
  """Return one deterministic Heimdall process fixture."""

  if name not in HEIMDALL_PROCESS_FIXTURES:
    raise KeyError('Unknown Heimdall process fixture: {name}'.format(name=name))
  return HEIMDALL_PROCESS_FIXTURES[name]
