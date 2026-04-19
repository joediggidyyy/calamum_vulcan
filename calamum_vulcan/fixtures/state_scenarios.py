"""Representative state scenarios for FS-02 validation."""

from __future__ import annotations

from typing import List

from calamum_vulcan.domain.state import PlatformEvent
from calamum_vulcan.domain.state import SessionEventType


def happy_path_events() -> List[PlatformEvent]:
  """Return a standard destructive-flow happy path."""

  return [
    PlatformEvent(
      SessionEventType.DEVICE_CONNECTED,
      {
        'device_id': 'samsung-galaxy-lab-01',
        'product_code': 'SM-G973F',
        'mode': 'download',
      },
    ),
    PlatformEvent(
      SessionEventType.PACKAGE_SELECTED,
      {
        'package_id': 'calamum-recovery-lab-001',
        'risk_level': 'destructive',
      },
    ),
    PlatformEvent(SessionEventType.PREFLIGHT_REVIEW_STARTED),
    PlatformEvent(
      SessionEventType.PREFLIGHT_CLEARED,
      {'notes': ('Driver validated', 'Product code matched')},
    ),
    PlatformEvent(
      SessionEventType.ACKNOWLEDGEMENTS_CAPTURED,
      {
        'warnings_acknowledged': True,
        'destructive_acknowledged': True,
      },
    ),
    PlatformEvent(SessionEventType.EXECUTION_STARTED),
    PlatformEvent(SessionEventType.EXECUTION_COMPLETED),
  ]


def blocked_validation_events() -> List[PlatformEvent]:
  """Return a preflight-blocked scenario."""

  return [
    PlatformEvent(
      SessionEventType.DEVICE_CONNECTED,
      {
        'device_id': 'samsung-galaxy-lab-02',
        'product_code': 'SM-G991U',
        'mode': 'download',
      },
    ),
    PlatformEvent(
      SessionEventType.PACKAGE_SELECTED,
      {
        'package_id': 'regional-mismatch-demo',
        'risk_level': 'standard',
      },
    ),
    PlatformEvent(SessionEventType.PREFLIGHT_REVIEW_STARTED),
    PlatformEvent(
      SessionEventType.PREFLIGHT_BLOCKED,
      {'notes': ('Product code mismatch',)},
    ),
  ]


def blocked_then_cleared_events() -> List[PlatformEvent]:
  """Return a blocked scenario that is corrected and approved."""

  return blocked_validation_events() + [
    PlatformEvent(
      SessionEventType.PACKAGE_SELECTED,
      {
        'package_id': 'regional-match-demo',
        'risk_level': 'standard',
      },
    ),
    PlatformEvent(SessionEventType.PREFLIGHT_REVIEW_STARTED),
    PlatformEvent(
      SessionEventType.PREFLIGHT_CLEARED,
      {'notes': ('Product code matched', 'Checksums present')},
    ),
    PlatformEvent(
      SessionEventType.ACKNOWLEDGEMENTS_CAPTURED,
      {'warnings_acknowledged': True},
    ),
  ]


def resume_needed_events() -> List[PlatformEvent]:
  """Return a no-reboot style execution path with resume handling."""

  return happy_path_events()[:-1] + [
    PlatformEvent(
      SessionEventType.EXECUTION_PAUSED,
      {'notes': ('Manual recovery boot required',)},
    ),
    PlatformEvent(SessionEventType.EXECUTION_RESUMED),
    PlatformEvent(SessionEventType.EXECUTION_COMPLETED),
  ]


def execution_failure_events() -> List[PlatformEvent]:
  """Return a transport failure after execution begins."""

  return happy_path_events()[:-1] + [
    PlatformEvent(
      SessionEventType.EXECUTION_FAILED,
      {'reason': 'USB transfer timeout during partition write'},
    )
  ]


def package_first_events() -> List[PlatformEvent]:
  """Return a scenario where the operator loads a package before the device."""

  return [
    PlatformEvent(
      SessionEventType.PACKAGE_SELECTED,
      {
        'package_id': 'package-first-demo',
        'risk_level': 'standard',
      },
    ),
    PlatformEvent(
      SessionEventType.DEVICE_CONNECTED,
      {
        'device_id': 'samsung-galaxy-lab-03',
        'product_code': 'SM-N975F',
        'mode': 'download',
      },
    ),
    PlatformEvent(SessionEventType.PREFLIGHT_REVIEW_STARTED),
    PlatformEvent(
      SessionEventType.PREFLIGHT_CLEARED,
      {'notes': ('Deferred package load respected',)},
    ),
    PlatformEvent(
      SessionEventType.ACKNOWLEDGEMENTS_CAPTURED,
      {'warnings_acknowledged': True},
    ),
  ]