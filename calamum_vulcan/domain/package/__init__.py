"""Package-awareness contracts for Calamum Vulcan."""

from .contract import REQUIRED_CHECKSUM_FIELDS
from .contract import REQUIRED_COMPATIBILITY_FIELDS
from .contract import REQUIRED_FLASH_PLAN_FIELDS
from .contract import REQUIRED_IDENTITY_FIELDS
from .contract import REQUIRED_PARTITION_FIELDS
from .contract import REQUIRED_TOP_LEVEL_FIELDS
from .contract import validate_manifest_contract_shape
from .model import FRAME_1_TEST_SURFACES
from .model import ChecksumPlaceholder
from .model import PackageCompatibilityContract
from .model import PackageCompatibilityExpectation
from .model import PackageIdentity
from .model import PackageManifestAssessment
from .model import PackageRiskLevel
from .model import PackageSummaryContract
from .model import PackageTestSurface
from .model import PartitionPlanEntry
from .model import RebootPolicy
from .parser import PackageManifestContractError
from .parser import assess_package_manifest
from .parser import parse_package_summary_contract
from .parser import preflight_overrides_from_package_assessment

__all__ = [
  'ChecksumPlaceholder',
  'FRAME_1_TEST_SURFACES',
  'PackageCompatibilityContract',
  'PackageCompatibilityExpectation',
  'PackageIdentity',
  'PackageManifestAssessment',
  'PackageManifestContractError',
  'PackageRiskLevel',
  'PackageSummaryContract',
  'PackageTestSurface',
  'PartitionPlanEntry',
  'REQUIRED_CHECKSUM_FIELDS',
  'REQUIRED_COMPATIBILITY_FIELDS',
  'REQUIRED_FLASH_PLAN_FIELDS',
  'REQUIRED_IDENTITY_FIELDS',
  'REQUIRED_PARTITION_FIELDS',
  'REQUIRED_TOP_LEVEL_FIELDS',
  'RebootPolicy',
  'assess_package_manifest',
  'parse_package_summary_contract',
  'preflight_overrides_from_package_assessment',
  'validate_manifest_contract_shape',
]