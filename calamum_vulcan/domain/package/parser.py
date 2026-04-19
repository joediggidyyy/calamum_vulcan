"""Manifest parsing and assessment helpers for Calamum Vulcan packages."""

from __future__ import annotations

from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from .contract import validate_manifest_contract_shape
from .model import ChecksumPlaceholder
from .model import PackageCompatibilityContract
from .model import PackageCompatibilityExpectation
from .model import PackageIdentity
from .model import PackageManifestAssessment
from .model import PackageRiskLevel
from .model import PackageSummaryContract
from .model import PartitionPlanEntry
from .model import RebootPolicy


class PackageManifestContractError(ValueError):
  """Raised when a manifest cannot satisfy the package contract."""

  def __init__(self, issues: Tuple[str, ...]) -> None:
    self.issues = issues
    super().__init__('Package manifest is incomplete: {issues}'.format(
      issues='; '.join(issues),
    ))


def parse_package_summary_contract(
  manifest: Mapping[str, object],
) -> PackageSummaryContract:
  """Parse a validated manifest mapping into a typed package summary."""

  issues = validate_manifest_contract_shape(manifest)
  if issues:
    raise PackageManifestContractError(issues)

  identity = _mapping_value(manifest, 'identity')
  compatibility = _mapping_value(manifest, 'compatibility')
  flash_plan = _mapping_value(manifest, 'flash_plan')
  checksums = manifest.get('checksums')

  return PackageSummaryContract(
    schema_version=str(manifest['schema_version']),
    identity=PackageIdentity(
      package_id=str(identity['package_id']),
      name=str(identity['name']),
      version=str(identity['version']),
      manufacturer=str(identity['manufacturer']),
      source_build=str(identity['source_build']),
    ),
    compatibility=PackageCompatibilityContract(
      expectation=PackageCompatibilityExpectation(
        str(compatibility['expectation'])
      ),
      supported_product_codes=_string_tuple(
        compatibility.get('supported_product_codes', ())
      ),
      supported_device_names=_string_tuple(
        compatibility.get('supported_device_names', ())
      ),
      pit_fingerprint=str(compatibility['pit_fingerprint']),
    ),
    risk_level=PackageRiskLevel(str(flash_plan['risk_level'])),
    reboot_policy=RebootPolicy(str(flash_plan['reboot_policy'])),
    repartition_allowed=bool(flash_plan['repartition_allowed']),
    partitions=tuple(
      PartitionPlanEntry(
        partition_name=str(entry['partition_name']),
        file_name=str(entry['file_name']),
        checksum_id=str(entry['checksum_id']),
        required=bool(entry['required']),
      )
      for entry in checksums_aware_partitions(flash_plan.get('partitions', ()))
    ),
    checksums=tuple(
      ChecksumPlaceholder(
        checksum_id=str(entry['checksum_id']),
        file_name=str(entry['file_name']),
        algorithm=str(entry['algorithm']),
        value_placeholder=str(entry['value_placeholder']),
      )
      for entry in checksums_aware_entries(checksums)
    ),
    post_flash_instructions=_string_tuple(
      flash_plan.get('post_flash_instructions', ())
    ),
  )


def assess_package_manifest(
  manifest: Mapping[str, object],
  detected_product_code: Optional[str] = None,
  fixture_name: str = 'ad_hoc_manifest',
) -> PackageManifestAssessment:
  """Assess one manifest for shell display and preflight integration."""

  issues = validate_manifest_contract_shape(manifest)
  summary = None  # type: Optional[PackageSummaryContract]
  if not issues:
    summary = parse_package_summary_contract(manifest)

  identity = _mapping_value_or_empty(manifest, 'identity')
  compatibility = _mapping_value_or_empty(manifest, 'compatibility')
  flash_plan = _mapping_value_or_empty(manifest, 'flash_plan')
  checksums = manifest.get('checksums')

  expectation = _enum_or_default(
    PackageCompatibilityExpectation,
    compatibility.get('expectation'),
    PackageCompatibilityExpectation.INCOMPLETE,
  )
  supported_product_codes = _string_tuple(
    compatibility.get('supported_product_codes', ())
  )
  supported_device_names = _string_tuple(
    compatibility.get('supported_device_names', ())
  )
  risk_level = _enum_or_default(
    PackageRiskLevel,
    flash_plan.get('risk_level'),
    None,
  )
  reboot_policy = _enum_or_default(
    RebootPolicy,
    flash_plan.get('reboot_policy'),
    None,
  )
  partitions = _preview_partitions(flash_plan.get('partitions', ()))
  checksum_entries = _preview_checksums(checksums)
  post_flash_instructions = _string_tuple(
    flash_plan.get('post_flash_instructions', ())
  )
  matches_detected_product_code = _matches_detected_product_code(
    supported_product_codes,
    detected_product_code,
    expectation,
    issues,
  )

  if summary is not None:
    partitions = summary.partitions
    checksum_entries = summary.checksums
    post_flash_instructions = summary.post_flash_instructions

  return PackageManifestAssessment(
    fixture_name=fixture_name,
    contract_issues=issues,
    contract_complete=summary is not None and not issues,
    checksum_coverage_present=bool(checksum_entries),
    display_package_id=_string_value(identity, 'package_id', 'unknown-package'),
    display_name=_string_value(identity, 'name', 'Unresolved package'),
    version=_string_value(identity, 'version', 'unknown'),
    source_build=_string_value(identity, 'source_build', 'unknown'),
    compatibility_expectation=expectation,
    supported_product_codes=supported_product_codes,
    supported_device_names=supported_device_names,
    pit_fingerprint=_string_value(
      compatibility,
      'pit_fingerprint',
      'missing pit fingerprint',
    ),
    risk_level=risk_level,
    reboot_policy=reboot_policy,
    repartition_allowed=bool(flash_plan.get('repartition_allowed', False)),
    partitions=partitions,
    checksums=checksum_entries,
    post_flash_instructions=post_flash_instructions,
    detected_product_code=detected_product_code,
    matches_detected_product_code=matches_detected_product_code,
    summary=summary,
  )


def preflight_overrides_from_package_assessment(
  assessment: PackageManifestAssessment,
) -> Dict[str, object]:
  """Convert assessed package truth into preflight-rule overrides."""

  destructive_operation = assessment.risk_level == PackageRiskLevel.DESTRUCTIVE
  return {
    'package_selected': True,
    'package_complete': assessment.contract_complete,
    'checksums_present': assessment.checksum_coverage_present,
    'product_code_match': assessment.matches_detected_product_code,
    'destructive_operation': destructive_operation,
    'package_id': assessment.display_package_id,
  }


def checksums_aware_partitions(
  partitions: object,
) -> Tuple[Mapping[str, object], ...]:
  """Return partition entries that are complete enough for normalization."""

  if not isinstance(partitions, Sequence) or isinstance(partitions, (str, bytes)):
    return ()
  normalized = []
  for entry in partitions:
    if not isinstance(entry, Mapping):
      continue
    required = ('partition_name', 'file_name', 'checksum_id', 'required')
    if all(field in entry for field in required):
      normalized.append(entry)
  return tuple(normalized)


def checksums_aware_entries(
  checksums: object,
) -> Tuple[Mapping[str, object], ...]:
  """Return checksum entries that are complete enough for normalization."""

  if not isinstance(checksums, Sequence) or isinstance(checksums, (str, bytes)):
    return ()
  normalized = []
  for entry in checksums:
    if not isinstance(entry, Mapping):
      continue
    required = ('checksum_id', 'file_name', 'algorithm', 'value_placeholder')
    if all(field in entry for field in required):
      normalized.append(entry)
  return tuple(normalized)


def _preview_partitions(
  partitions: object,
) -> Tuple[PartitionPlanEntry, ...]:
  return tuple(
    PartitionPlanEntry(
      partition_name=str(entry['partition_name']),
      file_name=str(entry['file_name']),
      checksum_id=str(entry['checksum_id']),
      required=bool(entry['required']),
    )
    for entry in checksums_aware_partitions(partitions)
  )


def _preview_checksums(
  checksums: object,
) -> Tuple[ChecksumPlaceholder, ...]:
  return tuple(
    ChecksumPlaceholder(
      checksum_id=str(entry['checksum_id']),
      file_name=str(entry['file_name']),
      algorithm=str(entry['algorithm']),
      value_placeholder=str(entry['value_placeholder']),
    )
    for entry in checksums_aware_entries(checksums)
  )


def _matches_detected_product_code(
  supported_product_codes: Tuple[str, ...],
  detected_product_code: Optional[str],
  expectation: PackageCompatibilityExpectation,
  issues: Tuple[str, ...],
) -> bool:
  if issues:
    return False
  if expectation == PackageCompatibilityExpectation.MISMATCH:
    return False
  if detected_product_code is not None and supported_product_codes:
    return detected_product_code in supported_product_codes
  return expectation == PackageCompatibilityExpectation.MATCHED


def _mapping_value_or_empty(
  mapping: Mapping[str, object],
  key: str,
) -> Mapping[str, object]:
  value = mapping.get(key)
  if isinstance(value, Mapping):
    return value
  return {}


def _mapping_value(
  mapping: Mapping[str, object],
  key: str,
) -> Mapping[str, object]:
  value = _mapping_value_or_empty(mapping, key)
  if not value:
    raise KeyError('Missing mapping value for {key}'.format(key=key))
  return value


def _string_tuple(values: object) -> Tuple[str, ...]:
  if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
    return ()
  return tuple(str(value) for value in values)


def _string_value(
  mapping: Mapping[str, object],
  key: str,
  default: str,
) -> str:
  value = mapping.get(key)
  if value is None:
    return default
  return str(value)


def _enum_or_default(enum_type, value: object, default):
  if value is None:
    return default
  try:
    return enum_type(str(value))
  except ValueError:
    return default