"""Package-awareness contracts for Calamum Vulcan."""

from .contract import REQUIRED_CHECKSUM_FIELDS
from .contract import REQUIRED_CHECKSUM_VALUE_FIELDS
from .contract import REQUIRED_COMPATIBILITY_FIELDS
from .contract import REQUIRED_FLASH_PLAN_FIELDS
from .contract import REQUIRED_IDENTITY_FIELDS
from .contract import REQUIRED_PARTITION_FIELDS
from .contract import REQUIRED_TOP_LEVEL_FIELDS
from .contract import validate_manifest_contract_shape
from .importer import ImportedPackageArtifact
from .importer import PackageArchiveImportError
from .importer import assess_package_archive
from .importer import import_package_archive
from .image_heuristics import assess_android_image_heuristics
from .image_heuristics import summarize_suspicious_findings
from .model import FRAME_1_TEST_SURFACES
from .model import ChecksumPlaceholder
from .model import PackageCompatibilityContract
from .model import PackageCompatibilityExpectation
from .model import PackageIdentity
from .model import PackageManifestAssessment
from .model import PackageRiskLevel
from .model import PackageSuspiciousFinding
from .model import PackageSummaryContract
from .model import PackageTestSurface
from .model import PartitionPlanEntry
from .model import RebootPolicy
from .parser import PackageManifestContractError
from .parser import assess_package_manifest
from .parser import parse_package_summary_contract
from .parser import preflight_overrides_from_package_assessment
from .snapshot import ANALYZED_SNAPSHOT_SCHEMA_VERSION
from .snapshot import AnalyzedPackageSnapshot
from .snapshot import AnalyzedPackageSnapshotError
from .snapshot import AnalyzedSnapshotVerification
from .snapshot import SnapshotPartitionRecord
from .snapshot import SnapshotPayloadDigest
from .snapshot import bind_analyzed_snapshot_verification
from .snapshot import reverify_analyzed_package_snapshot
from .snapshot import seal_analyzed_package_snapshot
from .parser import with_additional_assessment_issues

__all__ = [
  'ChecksumPlaceholder',
  'FRAME_1_TEST_SURFACES',
  'ImportedPackageArtifact',
  'ANALYZED_SNAPSHOT_SCHEMA_VERSION',
  'AnalyzedPackageSnapshot',
  'AnalyzedPackageSnapshotError',
  'AnalyzedSnapshotVerification',
  'PackageArchiveImportError',
  'PackageCompatibilityContract',
  'PackageCompatibilityExpectation',
  'PackageIdentity',
  'PackageManifestAssessment',
  'PackageManifestContractError',
  'PackageRiskLevel',
  'PackageSuspiciousFinding',
  'PackageSummaryContract',
  'PackageTestSurface',
  'PartitionPlanEntry',
  'REQUIRED_CHECKSUM_FIELDS',
  'REQUIRED_CHECKSUM_VALUE_FIELDS',
  'REQUIRED_COMPATIBILITY_FIELDS',
  'REQUIRED_FLASH_PLAN_FIELDS',
  'REQUIRED_IDENTITY_FIELDS',
  'REQUIRED_PARTITION_FIELDS',
  'REQUIRED_TOP_LEVEL_FIELDS',
  'RebootPolicy',
  'SnapshotPartitionRecord',
  'SnapshotPayloadDigest',
  'assess_package_archive',
  'assess_android_image_heuristics',
  'assess_package_manifest',
  'bind_analyzed_snapshot_verification',
  'import_package_archive',
  'parse_package_summary_contract',
  'preflight_overrides_from_package_assessment',
  'reverify_analyzed_package_snapshot',
  'seal_analyzed_package_snapshot',
  'summarize_suspicious_findings',
  'validate_manifest_contract_shape',
  'with_additional_assessment_issues',
]