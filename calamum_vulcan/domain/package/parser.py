"""Manifest parsing and assessment helpers for Calamum Vulcan packages."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from calamum_vulcan.domain.device_registry import resolve_package_compatibility

from .contract import validate_manifest_contract_shape
from .image_heuristics import assess_android_image_heuristics
from .image_heuristics import summarize_suspicious_findings
from .model import ChecksumPlaceholder
from .model import PackageCompatibilityContract
from .model import PackageCompatibilityExpectation
from .model import PackageIdentity
from .model import PackageManifestAssessment
from .model import PackageRiskLevel
from .model import PackageSuspiciousFinding
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
  suspicious_findings = assess_android_image_heuristics(manifest)

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
      _checksum_record_from_mapping(entry)
      for entry in checksums_aware_entries(checksums)
    ),
    post_flash_instructions=_string_tuple(
      flash_plan.get('post_flash_instructions', ())
    ),
    suspicious_findings=suspicious_findings,
  )


def assess_package_manifest(
  manifest: Mapping[str, object],
  detected_product_code: Optional[str] = None,
  fixture_name: str = 'ad_hoc_manifest',
  source_kind: str = 'fixture',
  staged_root: Optional[Path] = None,
  payload_members: Sequence[str] = (),
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
  compatibility_resolution = resolve_package_compatibility(
    supported_product_codes,
    supported_device_names,
    detected_product_code,
    expectation.value,
    issues,
  )
  matches_detected_product_code = compatibility_resolution.compatible

  if summary is not None:
    partitions = summary.partitions
    checksum_entries = summary.checksums
    post_flash_instructions = summary.post_flash_instructions

  suspicious_findings = _merged_suspicious_findings(
    manifest,
    summary.suspicious_findings if summary is not None else (),
    staged_root=staged_root,
    payload_members=payload_members,
  )

  checksum_verification_complete = bool(checksum_entries) and all(
    entry.verified for entry in checksum_entries
  )
  verified_checksum_count = sum(
    1 for entry in checksum_entries if entry.verified
  )

  return PackageManifestAssessment(
    fixture_name=fixture_name,
    source_kind=source_kind,
    contract_issues=issues,
    contract_complete=summary is not None and not issues,
    checksum_coverage_present=bool(checksum_entries),
    checksum_verification_complete=checksum_verification_complete,
    verified_checksum_count=verified_checksum_count,
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
    suspicious_findings=suspicious_findings,
    suspicious_warning_count=len(suspicious_findings),
    suspiciousness_summary=summarize_suspicious_findings(suspicious_findings),
    detected_product_code=compatibility_resolution.registry_resolution.detected_product_code,
    matches_detected_product_code=matches_detected_product_code,
    resolved_product_code=compatibility_resolution.registry_resolution.canonical_product_code,
    resolved_device_name=compatibility_resolution.registry_resolution.marketing_name,
    device_registry_known=compatibility_resolution.registry_resolution.known,
    device_registry_match_kind=compatibility_resolution.registry_resolution.match_kind,
    device_mode_entry_instructions=compatibility_resolution.registry_resolution.mode_entry_instructions,
    device_known_quirks=compatibility_resolution.registry_resolution.known_quirks,
    compatibility_summary=compatibility_resolution.summary,
    summary=summary,
  )


def preflight_overrides_from_package_assessment(
  assessment: PackageManifestAssessment,
) -> Dict[str, object]:
  """Convert assessed package truth into preflight-rule overrides."""

  destructive_operation = assessment.risk_level == PackageRiskLevel.DESTRUCTIVE
  checksums_present = assessment.checksum_coverage_present
  snapshot_required = assessment.source_kind == 'archive'
  snapshot_created = assessment.analyzed_snapshot_id is not None
  if assessment.source_kind != 'fixture':
    checksums_present = assessment.checksum_verification_complete
  return {
    'package_selected': True,
    'package_complete': assessment.contract_complete,
    'checksums_present': checksums_present,
    'snapshot_required': snapshot_required,
    'snapshot_created': snapshot_created,
    'snapshot_verified': assessment.analyzed_snapshot_verified,
    'snapshot_drift_detected': assessment.analyzed_snapshot_drift_detected,
    'snapshot_id': assessment.analyzed_snapshot_id,
    'product_code_match': assessment.matches_detected_product_code,
    'destructive_operation': destructive_operation,
    'package_id': assessment.display_package_id,
    'suspicious_warning_count': assessment.suspicious_warning_count,
    'suspiciousness_summary': assessment.suspiciousness_summary,
    'suspicious_indicator_ids': tuple(
      finding.indicator_id for finding in assessment.suspicious_findings
    ),
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
    required = ('checksum_id', 'file_name', 'algorithm')
    if all(field in entry for field in required) and _checksum_value(entry) is not None:
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
    _checksum_record_from_mapping(entry)
    for entry in checksums_aware_entries(checksums)
  )


def with_additional_assessment_issues(
  assessment: PackageManifestAssessment,
  issues: Sequence[str],
) -> PackageManifestAssessment:
  """Return one assessment with additional contract issues folded in."""

  additions = tuple(str(issue) for issue in issues if str(issue))
  if not additions:
    return assessment
  merged = assessment.contract_issues + additions
  return replace(
    assessment,
    contract_issues=merged,
    contract_complete=False,
  )


def _merged_suspicious_findings(
  manifest: Mapping[str, object],
  existing_findings: Sequence[PackageSuspiciousFinding],
  staged_root: Optional[Path],
  payload_members: Sequence[str],
) -> Tuple[PackageSuspiciousFinding, ...]:
  findings = list(existing_findings)
  if staged_root is not None:
    findings.extend(
      assess_android_image_heuristics(
        manifest,
        staged_root=staged_root,
        payload_members=payload_members,
      )
    )
  deduped = []
  seen = set()
  for finding in findings:
    if finding.indicator_id in seen:
      continue
    seen.add(finding.indicator_id)
    deduped.append(finding)
  return tuple(deduped)


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


def _checksum_record_from_mapping(
  entry: Mapping[str, object],
) -> ChecksumPlaceholder:
  value_placeholder = ''
  placeholder = entry.get('value_placeholder')
  if placeholder is not None:
    value_placeholder = str(placeholder)

  resolved_value = entry.get('value')
  source_label = _string_value(entry, 'source_label', 'manifest_placeholder')
  if resolved_value is not None and placeholder is None:
    source_label = _string_value(entry, 'source_label', 'manifest_value')

  verified_value = entry.get('verified', False)
  return ChecksumPlaceholder(
    checksum_id=str(entry['checksum_id']),
    file_name=str(entry['file_name']),
    algorithm=str(entry['algorithm']),
    value_placeholder=value_placeholder,
    resolved_value=str(resolved_value) if resolved_value is not None else None,
    verified=bool(verified_value),
    source_label=source_label,
  )


def _checksum_value(entry: Mapping[str, object]) -> Optional[str]:
  if 'value' in entry and entry.get('value') is not None:
    return str(entry['value'])
  if 'value_placeholder' in entry and entry.get('value_placeholder') is not None:
    return str(entry['value_placeholder'])
  return None