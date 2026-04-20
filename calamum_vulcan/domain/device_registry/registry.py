"""Repo-owned device registry and compatibility resolvers for Calamum Vulcan."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import Optional
from typing import Tuple


DEVICE_REGISTRY_SCHEMA_VERSION = '0.2.0-fs2-04'


class DeviceRegistryMatchKind(str, Enum):
  """How one product code matched the repo-owned device registry."""

  NOT_PROVIDED = 'not_provided'
  EXACT = 'exact'
  ALIAS = 'alias'
  UNKNOWN = 'unknown'


class DeviceCompatibilityStatus(str, Enum):
  """Compatibility outcome after registry-backed resolution."""

  AWAITING_DEVICE = 'awaiting_device'
  MATCHED = 'matched'
  ALIAS_MATCHED = 'alias_matched'
  MISMATCH = 'mismatch'
  UNKNOWN_DEVICE = 'unknown_device'
  INCOMPLETE = 'incomplete'


@dataclass(frozen=True)
class DeviceProfile:
  """One repo-owned Samsung device profile."""

  canonical_product_code: str
  marketing_name: str
  product_code_aliases: Tuple[str, ...] = ()
  mode_entry_instructions: Tuple[str, ...] = ()
  known_quirks: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DeviceRegistryResolution:
  """Resolved device identity for one detected product code."""

  detected_product_code: Optional[str]
  canonical_product_code: Optional[str]
  marketing_name: Optional[str]
  match_kind: DeviceRegistryMatchKind
  mode_entry_instructions: Tuple[str, ...] = ()
  known_quirks: Tuple[str, ...] = ()

  @property
  def known(self) -> bool:
    """Return whether the detected code resolved to a registry profile."""

    return self.match_kind in (
      DeviceRegistryMatchKind.EXACT,
      DeviceRegistryMatchKind.ALIAS,
    )

  @property
  def alias_matched(self) -> bool:
    """Return whether resolution happened through an alias path."""

    return self.match_kind == DeviceRegistryMatchKind.ALIAS


@dataclass(frozen=True)
class DeviceCompatibilityResolution:
  """Compatibility result after combining device registry and package support data."""

  status: DeviceCompatibilityStatus
  registry_resolution: DeviceRegistryResolution
  matched_supported_product_code: Optional[str] = None
  summary: str = 'Compatibility unresolved.'

  @property
  def compatible(self) -> bool:
    """Return whether the resolved device is allowed for the package."""

    return self.status in (
      DeviceCompatibilityStatus.MATCHED,
      DeviceCompatibilityStatus.ALIAS_MATCHED,
    )


DEVICE_PROFILES = (
  DeviceProfile(
    canonical_product_code='SM-G973F',
    marketing_name='Galaxy S10',
    product_code_aliases=('SMG973F', 'G973F'),
    mode_entry_instructions=(
      'Power the device off completely before entering Download Mode.',
      'Use the device-family Samsung hardware-key flow, then confirm Download Mode on-device before USB transport begins.',
    ),
    known_quirks=(
      'Recovery-first lab flows should boot directly into recovery after flashing.',
    ),
  ),
  DeviceProfile(
    canonical_product_code='SM-G991U',
    marketing_name='Galaxy S21',
    product_code_aliases=('SMG991U', 'G991U'),
    mode_entry_instructions=(
      'Power the device off completely before entering Download Mode.',
      'Use the device-family Samsung hardware-key flow, then confirm Download Mode on-device before USB transport begins.',
    ),
    known_quirks=(
      'Regional review packages should keep recovery and vbmeta alignment visible before release validation.',
    ),
  ),
  DeviceProfile(
    canonical_product_code='SM-G996U',
    marketing_name='Galaxy S21+',
    product_code_aliases=('SMG996U', 'G996U'),
    mode_entry_instructions=(
      'Power the device off completely before entering Download Mode.',
      'Use the device-family Samsung hardware-key flow, then confirm Download Mode on-device before USB transport begins.',
    ),
    known_quirks=(
      'Blocked-review fixtures should remain mismatched against the ready review lane until registry-backed compatibility is explicit.',
    ),
  ),
  DeviceProfile(
    canonical_product_code='SM-N975F',
    marketing_name='Galaxy Note10+',
    product_code_aliases=('SMN975F', 'N975F'),
    mode_entry_instructions=(
      'Power the device off completely before entering Download Mode.',
      'Use the device-family Samsung hardware-key flow, then confirm Download Mode on-device before USB transport begins.',
    ),
    known_quirks=(
      'Package-first review remains valid before hardware arrives, but execution still waits on a detected device profile.',
    ),
  ),
)

def available_device_profiles() -> Tuple[DeviceProfile, ...]:
  """Return the current repo-owned device profiles."""

  return DEVICE_PROFILES


def normalize_product_code(product_code: str) -> str:
  """Normalize one product-code string for registry lookup."""

  return ''.join(
    character
    for character in str(product_code).strip().upper()
    if character.isalnum()
  )


def resolve_device_profile(
  product_code: Optional[str],
) -> DeviceRegistryResolution:
  """Resolve one detected product code through the repo-owned device registry."""

  if product_code is None or not str(product_code).strip():
    return DeviceRegistryResolution(
      detected_product_code=None,
      canonical_product_code=None,
      marketing_name=None,
      match_kind=DeviceRegistryMatchKind.NOT_PROVIDED,
    )

  detected_code = _display_product_code(product_code)
  profile = _DEVICE_PROFILE_LOOKUP.get(normalize_product_code(detected_code))
  if profile is None:
    return DeviceRegistryResolution(
      detected_product_code=detected_code,
      canonical_product_code=None,
      marketing_name=None,
      match_kind=DeviceRegistryMatchKind.UNKNOWN,
    )

  match_kind = DeviceRegistryMatchKind.EXACT
  if normalize_product_code(detected_code) != normalize_product_code(
    profile.canonical_product_code
  ):
    match_kind = DeviceRegistryMatchKind.ALIAS

  return DeviceRegistryResolution(
    detected_product_code=detected_code,
    canonical_product_code=profile.canonical_product_code,
    marketing_name=profile.marketing_name,
    match_kind=match_kind,
    mode_entry_instructions=profile.mode_entry_instructions,
    known_quirks=profile.known_quirks,
  )


def resolve_package_compatibility(
  supported_product_codes: Tuple[str, ...],
  supported_device_names: Tuple[str, ...],
  detected_product_code: Optional[str],
  expectation: str,
  issues: Tuple[str, ...],
) -> DeviceCompatibilityResolution:
  """Resolve package compatibility using repo-owned device-registry truth."""

  registry_resolution = resolve_device_profile(detected_product_code)
  if issues:
    return DeviceCompatibilityResolution(
      status=DeviceCompatibilityStatus.INCOMPLETE,
      registry_resolution=registry_resolution,
      summary='Package manifest issues prevent trusted registry-backed compatibility review.',
    )

  if registry_resolution.match_kind == DeviceRegistryMatchKind.NOT_PROVIDED:
    return DeviceCompatibilityResolution(
      status=DeviceCompatibilityStatus.AWAITING_DEVICE,
      registry_resolution=registry_resolution,
      summary='No detected Samsung device is available for registry-backed compatibility review.',
    )

  if not registry_resolution.known:
    return DeviceCompatibilityResolution(
      status=DeviceCompatibilityStatus.UNKNOWN_DEVICE,
      registry_resolution=registry_resolution,
      summary='The detected product code {product_code} is not yet profiled in the repo-owned device registry.'.format(
        product_code=registry_resolution.detected_product_code,
      ),
    )

  if expectation == 'mismatch':
    return DeviceCompatibilityResolution(
      status=DeviceCompatibilityStatus.MISMATCH,
      registry_resolution=registry_resolution,
      summary='{name} ({product_code}) is intentionally marked mismatched for this package review lane.'.format(
        name=registry_resolution.marketing_name or 'Detected Samsung device',
        product_code=registry_resolution.canonical_product_code,
      ),
    )

  supported_codes = _canonicalize_supported_codes(supported_product_codes)
  supported_names = _normalize_device_names(supported_device_names)
  matched_supported_code = None  # type: Optional[str]
  detected_canonical = registry_resolution.canonical_product_code
  if detected_canonical in supported_codes:
    matched_supported_code = detected_canonical
  elif (
    registry_resolution.marketing_name is not None
    and _normalize_device_name(registry_resolution.marketing_name) in supported_names
  ):
    matched_supported_code = detected_canonical

  if matched_supported_code is not None:
    if registry_resolution.alias_matched:
      return DeviceCompatibilityResolution(
        status=DeviceCompatibilityStatus.ALIAS_MATCHED,
        registry_resolution=registry_resolution,
        matched_supported_product_code=matched_supported_code,
        summary='Detected product code {detected} resolves to {canonical} ({name}) and matches the package support list.'.format(
          detected=registry_resolution.detected_product_code,
          canonical=registry_resolution.canonical_product_code,
          name=registry_resolution.marketing_name,
        ),
      )
    return DeviceCompatibilityResolution(
      status=DeviceCompatibilityStatus.MATCHED,
      registry_resolution=registry_resolution,
      matched_supported_product_code=matched_supported_code,
      summary='{name} ({product_code}) matches the package support list.'.format(
        name=registry_resolution.marketing_name,
        product_code=registry_resolution.canonical_product_code,
      ),
    )

  return DeviceCompatibilityResolution(
    status=DeviceCompatibilityStatus.MISMATCH,
    registry_resolution=registry_resolution,
    summary='{name} ({product_code}) is not in the package support list.'.format(
      name=registry_resolution.marketing_name or 'Detected Samsung device',
      product_code=registry_resolution.canonical_product_code,
    ),
  )


def _build_device_profile_lookup(
  profiles: Tuple[DeviceProfile, ...],
) -> Dict[str, DeviceProfile]:
  lookup = {}  # type: Dict[str, DeviceProfile]
  for profile in profiles:
    lookup[normalize_product_code(profile.canonical_product_code)] = profile
    for alias in profile.product_code_aliases:
      lookup[normalize_product_code(alias)] = profile
  return lookup


def _canonicalize_supported_codes(
  supported_product_codes: Tuple[str, ...],
) -> Tuple[str, ...]:
  canonical = []
  for product_code in supported_product_codes:
    resolution = resolve_device_profile(product_code)
    if resolution.canonical_product_code is not None:
      canonical.append(resolution.canonical_product_code)
    else:
      canonical.append(_display_product_code(product_code))
  return tuple(canonical)


def _normalize_device_names(
  supported_device_names: Tuple[str, ...],
) -> Tuple[str, ...]:
  return tuple(_normalize_device_name(name) for name in supported_device_names)


def _normalize_device_name(device_name: str) -> str:
  return ' '.join(str(device_name).strip().lower().split())


def _display_product_code(product_code: str) -> str:
  return str(product_code).strip().upper()


_DEVICE_PROFILE_LOOKUP = _build_device_profile_lookup(DEVICE_PROFILES)
