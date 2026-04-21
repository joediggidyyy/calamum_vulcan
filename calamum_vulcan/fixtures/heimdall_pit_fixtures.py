"""Deterministic Heimdall PIT process fixtures for Sprint 0.3.0 FS3-04."""

from __future__ import annotations

from typing import Dict
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallProcessResult


HEIMDALL_PIT_FIXTURES = {
  'pit-print-ready-g991u': HeimdallProcessResult(
    fixture_name='pit-print-ready-g991u',
    operation=HeimdallOperation.PRINT_PIT,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Printing PIT...',
      'PIT metadata: product_code=SM-G991U fingerprint=PIT-G991U-READY-001 entry_count=3',
      'Entry: index=7 partition=BOOT file_name=boot.img.lz4 block_count=32768 file_offset=0',
      'Entry: index=20 partition=RECOVERY file_name=recovery.img block_count=131072 file_offset=32768',
      'Entry: index=21 partition=VBMETA file_name=vbmeta.img block_count=4096 file_offset=163840',
      'PIT print completed successfully.',
    ),
  ),
  'pit-print-ready-g973f': HeimdallProcessResult(
    fixture_name='pit-print-ready-g973f',
    operation=HeimdallOperation.PRINT_PIT,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Printing PIT...',
      'PIT metadata: product_code=SM-G973F fingerprint=PIT-G973F-LAB-001 entry_count=3',
      'Entry: index=3 partition=BOOT file_name=boot.img.lz4 block_count=32768 file_offset=0',
      'Entry: index=12 partition=RECOVERY file_name=recovery.img block_count=98304 file_offset=32768',
      'Entry: index=13 partition=SYSTEM file_name=system.img block_count=524288 file_offset=131072',
      'PIT print completed successfully.',
    ),
  ),
  'pit-print-malformed': HeimdallProcessResult(
    fixture_name='pit-print-malformed',
    operation=HeimdallOperation.PRINT_PIT,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Printing PIT...',
      'PIT metadata: product_code=SM-G991U entry_count=two',
      'Entry: partition=RECOVERY file_name=recovery.img block_count=131072 file_offset=32768',
      'PIT print completed successfully.',
    ),
  ),
  'pit-download-ready-g991u': HeimdallProcessResult(
    fixture_name='pit-download-ready-g991u',
    operation=HeimdallOperation.DOWNLOAD_PIT,
    exit_code=0,
    stdout_lines=(
      'Heimdall v1.4.2',
      'Downloading PIT...',
      'PIT download complete: output=artifacts/device-ready.pit product_code=SM-G991U fingerprint=PIT-G991U-READY-001 entry_count=3 bytes=4096',
    ),
  ),
}  # type: Dict[str, HeimdallProcessResult]


def available_heimdall_pit_fixtures() -> Tuple[str, ...]:
  """Return supported Heimdall PIT fixture names."""

  return tuple(HEIMDALL_PIT_FIXTURES.keys())


def load_heimdall_pit_fixture(name: str) -> HeimdallProcessResult:
  """Return one deterministic Heimdall PIT fixture."""

  if name not in HEIMDALL_PIT_FIXTURES:
    raise KeyError('Unknown Heimdall PIT fixture: {name}'.format(name=name))
  return HEIMDALL_PIT_FIXTURES[name]
