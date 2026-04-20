"""Reviewed flash-plan builder for Calamum Vulcan FS2-05."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.package import RebootPolicy

from .model import FLASH_PLAN_SCHEMA_VERSION
from .model import ReviewedFlashPlan
from .model import ReviewedFlashPlanPartition


def build_reviewed_flash_plan(
  package_assessment: PackageManifestAssessment,
  transport_backend: str = 'heimdall',
) -> ReviewedFlashPlan:
  """Build one platform-owned reviewed flash plan from package truth."""

  reviewed_partitions = _reviewed_partitions(package_assessment)
  blocking_reasons = tuple(
    _blocking_reasons(package_assessment, reviewed_partitions)
  )
  operator_warnings = tuple(
    finding.summary for finding in package_assessment.suspicious_findings
  )
  advanced_requirements = tuple(
    _advanced_requirements(package_assessment)
  )
  recovery_guidance = tuple(build_recovery_guidance(package_assessment))
  material = {
    'schema_version': FLASH_PLAN_SCHEMA_VERSION,
    'package_id': package_assessment.display_package_id,
    'source_kind': package_assessment.source_kind,
    'snapshot_id': package_assessment.analyzed_snapshot_id,
    'canonical_product_code': _canonical_product_code(package_assessment),
    'risk_level': _risk_level(package_assessment),
    'reboot_policy': _reboot_policy(package_assessment),
    'repartition_allowed': package_assessment.repartition_allowed,
    'pit_fingerprint': package_assessment.pit_fingerprint,
    'transport_backend': transport_backend,
    'required_capabilities': _required_capabilities(package_assessment),
    'advanced_requirements': advanced_requirements,
    'operator_warnings': operator_warnings,
    'blocking_reasons': blocking_reasons,
    'partitions': [asdict(partition) for partition in reviewed_partitions],
    'recovery_guidance': recovery_guidance,
  }
  ready_for_transport = not blocking_reasons
  return ReviewedFlashPlan(
    schema_version=FLASH_PLAN_SCHEMA_VERSION,
    plan_id=_stable_hash(material),
    summary=_summary(
      package_assessment,
      ready_for_transport=ready_for_transport,
    ),
    package_id=package_assessment.display_package_id,
    display_name=package_assessment.display_name,
    source_build=package_assessment.source_build,
    source_kind=package_assessment.source_kind,
    snapshot_id=package_assessment.analyzed_snapshot_id,
    canonical_product_code=_canonical_product_code(package_assessment),
    device_marketing_name=package_assessment.resolved_device_name,
    compatibility_summary=package_assessment.compatibility_summary,
    risk_level=_risk_level(package_assessment),
    reboot_policy=_reboot_policy(package_assessment),
    repartition_allowed=package_assessment.repartition_allowed,
    pit_fingerprint=package_assessment.pit_fingerprint,
    transport_backend=transport_backend,
    required_capabilities=_required_capabilities(package_assessment),
    advanced_requirements=advanced_requirements,
    suspicious_warning_count=package_assessment.suspicious_warning_count,
    operator_warnings=operator_warnings,
    requires_operator_acknowledgement=bool(operator_warnings),
    partitions=tuple(reviewed_partitions),
    verified_partition_count=sum(
      1 for partition in reviewed_partitions if partition.digest_verified
    ),
    blocking_reasons=blocking_reasons,
    recovery_guidance=recovery_guidance,
    ready_for_transport=ready_for_transport,
  )


def build_recovery_guidance(
  package_assessment: PackageManifestAssessment,
) -> List[str]:
  """Build reviewed recovery guidance from package truth."""

  guidance = []  # type: List[str]
  reboot_policy = package_assessment.reboot_policy
  if reboot_policy == RebootPolicy.NO_REBOOT:
    guidance.append(
      'Do not allow automatic reboot after flash completion; preserve the manual recovery handoff immediately.'
    )
  elif reboot_policy == RebootPolicy.STANDARD:
    guidance.append(
      'Allow a standard reboot after flash completion and confirm the device reaches the expected boot state.'
    )
  else:
    guidance.append(
      'Confirm the reviewed reboot posture before issuing any transport command.'
    )

  device_name = package_assessment.resolved_device_name
  product_code = _canonical_product_code(package_assessment)
  if device_name is not None or product_code is not None:
    guidance.append(
      'Recovery target: {device}{product}.'.format(
        device=device_name or 'Samsung device',
        product=(
          ' ({product_code})'.format(product_code=product_code)
          if product_code is not None
          else ''
        ),
      )
    )

  if package_assessment.repartition_allowed:
    guidance.append(
      'Confirm PIT fingerprint {pit} against the active device before any repartition-capable flash.'.format(
        pit=package_assessment.pit_fingerprint or 'missing'
      )
    )

  if package_assessment.suspicious_warning_count:
    guidance.append(
      'Warning-tier suspicious Android traits were detected; preserve explicit operator acknowledgement before execution.'
    )

  guidance.extend(package_assessment.post_flash_instructions)

  if package_assessment.device_known_quirks:
    guidance.append(
      'Quirk watch: {quirk}'.format(
        quirk=package_assessment.device_known_quirks[0]
      )
    )

  return _dedupe(guidance)


def _reviewed_partitions(
  package_assessment: PackageManifestAssessment,
) -> List[ReviewedFlashPlanPartition]:
  checksum_lookup = {
    checksum.checksum_id: checksum for checksum in package_assessment.checksums
  }  # type: Dict[str, object]
  partitions = []  # type: List[ReviewedFlashPlanPartition]
  for partition in package_assessment.partitions:
    checksum = checksum_lookup.get(partition.checksum_id)
    partitions.append(
      ReviewedFlashPlanPartition(
        partition_name=partition.partition_name,
        file_name=partition.file_name,
        checksum_id=partition.checksum_id,
        digest_value=(
          None if checksum is None else getattr(checksum, 'display_value', None)
        ),
        digest_verified=(
          False if checksum is None else bool(getattr(checksum, 'verified', False))
        ),
        required=partition.required,
      )
    )
  return partitions


def _blocking_reasons(
  package_assessment: PackageManifestAssessment,
  reviewed_partitions: List[ReviewedFlashPlanPartition],
) -> List[str]:
  reasons = list(package_assessment.contract_issues)

  if not reviewed_partitions:
    reasons.append('Reviewed flash plan requires at least one partition row.')

  missing_coverage = [
    partition.partition_name
    for partition in reviewed_partitions
    if partition.digest_value is None
  ]
  if missing_coverage:
    reasons.append(
      'Reviewed digest coverage is missing for: {targets}.'.format(
        targets=', '.join(missing_coverage)
      )
    )

  if package_assessment.source_kind != 'fixture':
    unverified = [
      partition.partition_name
      for partition in reviewed_partitions
      if not partition.digest_verified
    ]
    if unverified:
      reasons.append(
        'Reviewed payload digests are not verified for: {targets}.'.format(
          targets=', '.join(unverified)
        )
      )

  if package_assessment.source_kind == 'archive':
    if package_assessment.analyzed_snapshot_id is None:
      reasons.append(
        'Archive-backed flash plans require an analyzed snapshot before transport review.'
      )
    elif package_assessment.analyzed_snapshot_drift_detected:
      reasons.append(
        'Archive-backed flash plan is blocked because analyzed snapshot drift was detected.'
      )
    elif not package_assessment.analyzed_snapshot_verified:
      reasons.append(
        'Archive-backed flash plan is blocked because the analyzed snapshot is not verified.'
      )

  if package_assessment.detected_product_code is not None:
    if not package_assessment.device_registry_known:
      reasons.append(
        'Detected product code {product} is not recognized by the reviewed device registry.'.format(
          product=package_assessment.detected_product_code
        )
      )
    elif not package_assessment.matches_detected_product_code:
      reasons.append(
        'Detected product code {product} does not match the reviewed package compatibility envelope.'.format(
          product=package_assessment.detected_product_code
        )
      )

  if package_assessment.repartition_allowed and not _pit_fingerprint_present(
    package_assessment.pit_fingerprint
  ):
    reasons.append(
      'Repartition-capable flash plans require a reviewed PIT fingerprint.'
    )

  return _dedupe(reasons)


def _advanced_requirements(
  package_assessment: PackageManifestAssessment,
) -> List[str]:
  requirements = []  # type: List[str]
  if package_assessment.repartition_allowed:
    requirements.append(
      'Confirm the reviewed PIT fingerprint before any repartition-capable transport action.'
    )
  if package_assessment.reboot_policy == RebootPolicy.NO_REBOOT:
    requirements.append(
      'Manual recovery sequencing is required because the reviewed reboot policy is no_reboot.'
    )
  if package_assessment.suspicious_warning_count:
    requirements.append(
      'Operator acknowledgement is required for the warning-tier suspicious Android traits surfaced during package review.'
    )
  if package_assessment.device_registry_match_kind is not None:
    requirements.append(
      'Device compatibility resolution used registry match kind {kind}.'.format(
        kind=package_assessment.device_registry_match_kind.value
      )
    )
  return _dedupe(requirements)


def _required_capabilities(
  package_assessment: PackageManifestAssessment,
) -> Tuple[str, ...]:
  capabilities = ['flash_package']
  if package_assessment.repartition_allowed:
    capabilities.append('print_pit')
  return tuple(capabilities)


def _summary(
  package_assessment: PackageManifestAssessment,
  ready_for_transport: bool,
) -> str:
  device_label = (
    package_assessment.resolved_device_name
    or _canonical_product_code(package_assessment)
    or 'the reviewed Samsung target'
  )
  if not ready_for_transport:
    return (
      '{name} reviewed flash plan is blocked until trust prerequisites are cleared.'
    ).format(name=package_assessment.display_name)
  if package_assessment.suspicious_warning_count:
    return (
      '{name} reviewed flash plan is ready for {device} with warning-tier suspicious Android traits surfaced for operator review.'
    ).format(
      name=package_assessment.display_name,
      device=device_label,
    )
  if package_assessment.reboot_policy == RebootPolicy.NO_REBOOT:
    return (
      '{name} reviewed flash plan is ready for {device} with a manual no-reboot recovery handoff.'
    ).format(
      name=package_assessment.display_name,
      device=device_label,
    )
  if package_assessment.repartition_allowed:
    return (
      '{name} reviewed flash plan is ready for {device} and requires PIT-confirmed repartition review.'
    ).format(
      name=package_assessment.display_name,
      device=device_label,
    )
  return (
    '{name} reviewed flash plan is ready for {device}.'.format(
      name=package_assessment.display_name,
      device=device_label,
    )
  )


def _canonical_product_code(
  package_assessment: PackageManifestAssessment,
) -> Optional[str]:
  return (
    package_assessment.resolved_product_code
    or package_assessment.detected_product_code
  )


def _risk_level(package_assessment: PackageManifestAssessment) -> str:
  if package_assessment.risk_level is None:
    return 'unclassified'
  return package_assessment.risk_level.value


def _reboot_policy(package_assessment: PackageManifestAssessment) -> str:
  if package_assessment.reboot_policy is None:
    return 'unspecified'
  return package_assessment.reboot_policy.value


def _pit_fingerprint_present(pit_fingerprint: str) -> bool:
  fingerprint = pit_fingerprint.strip().lower()
  if not fingerprint:
    return False
  return not fingerprint.startswith('missing')


def _stable_hash(payload: Dict[str, object]) -> str:
  return hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
  ).hexdigest()


def _dedupe(values: List[str]) -> List[str]:
  deduped = []  # type: List[str]
  for value in values:
    if value not in deduped:
      deduped.append(value)
  return deduped
