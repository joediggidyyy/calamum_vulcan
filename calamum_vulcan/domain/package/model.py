"""Package summary contracts for the Calamum Vulcan FS-05 lane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from typing import Tuple


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
  """Checksum coverage placeholder for one package payload."""

  checksum_id: str
  file_name: str
  algorithm: str
  value_placeholder: str


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


@dataclass(frozen=True)
class PackageManifestAssessment:
  """Normalized package manifest context, even when the contract is incomplete."""

  fixture_name: str
  contract_issues: Tuple[str, ...]
  contract_complete: bool
  checksum_coverage_present: bool
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
  detected_product_code: Optional[str] = None
  matches_detected_product_code: bool = False
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