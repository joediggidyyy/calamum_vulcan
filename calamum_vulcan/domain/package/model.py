"""Package summary contracts for the Calamum Vulcan FS-05 lane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind


class PackageRiskLevel(str, Enum):
  """Risk posture declared by a package manifest."""

  STANDARD = 'standard'
  ADVANCED = 'advanced'
  DESTRUCTIVE = 'destructive'


class RebootPolicy(str, Enum):
  """Reboot handling expected after the flash plan."""

  STANDARD = 'standard'
  NO_REBOOT = 'no_reboot'


class PackageCompatibilityExpectation(str, Enum):
  """Expected compatibility posture for a package fixture."""

  MATCHED = 'matched'
  MISMATCH = 'mismatch'
  INCOMPLETE = 'incomplete'


@dataclass(frozen=True)
class PackageIdentity:
  """Top-level package identity shown in the GUI and reports."""

  package_id: str
  name: str
  version: str
  manufacturer: str
  source_build: str


@dataclass(frozen=True)
class PackageCompatibilityContract:
  """Compatibility posture and supported Samsung matrix hints."""

  expectation: PackageCompatibilityExpectation
  supported_product_codes: Tuple[str, ...]
  supported_device_names: Tuple[str, ...]
  pit_fingerprint: str


@dataclass(frozen=True)
class ChecksumPlaceholder:
  """Checksum coverage record for one package payload."""

  checksum_id: str
  file_name: str
  algorithm: str
  value_placeholder: str
  resolved_value: Optional[str] = None
  verified: bool = False
  source_label: str = 'manifest_placeholder'

  @property
  def display_value(self) -> str:
    """Return the most useful checksum value for operator-facing surfaces."""

    if self.resolved_value:
      return self.resolved_value
    return self.value_placeholder

  @property
  def placeholder_only(self) -> bool:
    """Return whether this checksum still relies on a placeholder surface."""

    return not self.resolved_value and bool(self.value_placeholder)


@dataclass(frozen=True)
class PackageSuspiciousFinding:
  """One warning-tier suspicious Android trait surfaced during package review."""

  indicator_id: str
  title: str
  summary: str
  operator_guidance: str
  evidence_source: str
  evidence_value: str


@dataclass(frozen=True)
class PartitionPlanEntry:
  """One partition entry in the early flash-plan preview contract."""

  partition_name: str
  file_name: str
  checksum_id: str
  required: bool


@dataclass(frozen=True)
class PackageSummaryContract:
  """The package summary contract planned for FS-05 implementation."""

  schema_version: str
  identity: PackageIdentity
  compatibility: PackageCompatibilityContract
  risk_level: PackageRiskLevel
  reboot_policy: RebootPolicy
  repartition_allowed: bool
  partitions: Tuple[PartitionPlanEntry, ...]
  checksums: Tuple[ChecksumPlaceholder, ...]
  post_flash_instructions: Tuple[str, ...] = ()
  suspicious_findings: Tuple[PackageSuspiciousFinding, ...] = ()


@dataclass(frozen=True)
class PackageManifestAssessment:
  """Normalized package manifest context, even when the contract is incomplete."""

  fixture_name: str
  source_kind: str
  contract_issues: Tuple[str, ...]
  contract_complete: bool
  checksum_coverage_present: bool
  checksum_verification_complete: bool
  verified_checksum_count: int
  display_package_id: str
  display_name: str
  version: str
  source_build: str
  compatibility_expectation: PackageCompatibilityExpectation
  supported_product_codes: Tuple[str, ...]
  supported_device_names: Tuple[str, ...]
  pit_fingerprint: str
  risk_level: Optional[PackageRiskLevel] = None
  reboot_policy: Optional[RebootPolicy] = None
  repartition_allowed: bool = False
  partitions: Tuple[PartitionPlanEntry, ...] = ()
  checksums: Tuple[ChecksumPlaceholder, ...] = ()
  post_flash_instructions: Tuple[str, ...] = ()
  suspicious_findings: Tuple[PackageSuspiciousFinding, ...] = ()
  suspicious_warning_count: int = 0
  suspiciousness_summary: str = 'No suspicious Android traits detected.'
  detected_product_code: Optional[str] = None
  matches_detected_product_code: bool = False
  resolved_product_code: Optional[str] = None
  resolved_device_name: Optional[str] = None
  device_registry_known: bool = False
  device_registry_match_kind: DeviceRegistryMatchKind = DeviceRegistryMatchKind.NOT_PROVIDED
  device_mode_entry_instructions: Tuple[str, ...] = ()
  device_known_quirks: Tuple[str, ...] = ()
  compatibility_summary: str = 'Compatibility unresolved.'
  analyzed_snapshot_id: Optional[str] = None
  analyzed_snapshot_created_at_utc: Optional[str] = None
  analyzed_snapshot_verified: bool = False
  analyzed_snapshot_drift_detected: bool = False
  snapshot_issues: Tuple[str, ...] = ()
  summary: Optional[PackageSummaryContract] = None


@dataclass(frozen=True)
class PackageTestSurface:
  """One test surface the package lane must preserve as it deepens."""

  name: str
  purpose: str


FRAME_1_TEST_SURFACES = (
  PackageTestSurface(
    name='manifest_identity_completeness',
    purpose='Package fixtures must carry enough identity to drive the shell and later reports.',
  ),
  PackageTestSurface(
    name='product_code_compatibility',
    purpose='Matched and mismatched Samsung product-code cases must be representable before execution.',
  ),
  PackageTestSurface(
    name='checksum_placeholder_coverage',
    purpose='Each planned payload must have checksum placeholder coverage in the manifest contract.',
  ),
  PackageTestSurface(
    name='partition_plan_preview',
    purpose='The manifest must expose a stable partition/file preview surface for the GUI.',
  ),
  PackageTestSurface(
    name='incomplete_manifest_handling',
    purpose='Intentionally incomplete fixtures must be detectable by contract validation before parsing deepens.',
  ),
)