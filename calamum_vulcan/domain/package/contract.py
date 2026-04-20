"""Manifest-shape contract helpers for the Calamum Vulcan FS-05 lane."""

from __future__ import annotations

from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple


REQUIRED_TOP_LEVEL_FIELDS = (
  'schema_version',
  'identity',
  'compatibility',
  'flash_plan',
  'checksums',
)

REQUIRED_IDENTITY_FIELDS = (
  'package_id',
  'name',
  'version',
  'manufacturer',
  'source_build',
)

REQUIRED_COMPATIBILITY_FIELDS = (
  'expectation',
  'supported_product_codes',
  'supported_device_names',
  'pit_fingerprint',
)

REQUIRED_FLASH_PLAN_FIELDS = (
  'risk_level',
  'repartition_allowed',
  'reboot_policy',
  'partitions',
  'post_flash_instructions',
)

REQUIRED_PARTITION_FIELDS = (
  'partition_name',
  'file_name',
  'checksum_id',
  'required',
)

REQUIRED_CHECKSUM_FIELDS = (
  'checksum_id',
  'file_name',
  'algorithm',
)

REQUIRED_CHECKSUM_VALUE_FIELDS = (
  'value',
  'value_placeholder',
)


def validate_manifest_contract_shape(
  manifest: Mapping[str, object],
) -> Tuple[str, ...]:
  """Return human-readable issues for a manifest-contract fixture."""

  issues = []
  issues.extend(_missing_fields(manifest, REQUIRED_TOP_LEVEL_FIELDS, 'manifest'))

  identity = _mapping_value(manifest, 'identity')
  if identity is not None:
    issues.extend(_missing_fields(identity, REQUIRED_IDENTITY_FIELDS, 'identity'))

  compatibility = _mapping_value(manifest, 'compatibility')
  if compatibility is not None:
    issues.extend(
      _missing_fields(
        compatibility,
        REQUIRED_COMPATIBILITY_FIELDS,
        'compatibility',
      )
    )

  flash_plan = _mapping_value(manifest, 'flash_plan')
  if flash_plan is not None:
    issues.extend(
      _missing_fields(
        flash_plan,
        REQUIRED_FLASH_PLAN_FIELDS,
        'flash_plan',
      )
    )
    partitions = flash_plan.get('partitions')
    if isinstance(partitions, Sequence) and not isinstance(partitions, (str, bytes)):
      if not partitions:
        issues.append('flash_plan.partitions must include at least one entry')
      for index, partition in enumerate(partitions):
        if isinstance(partition, Mapping):
          issues.extend(
            _missing_fields(
              partition,
              REQUIRED_PARTITION_FIELDS,
              'flash_plan.partitions[{index}]'.format(index=index),
            )
          )
        else:
          issues.append(
            'flash_plan.partitions[{index}] must be a mapping'.format(index=index)
          )

  checksums = manifest.get('checksums')
  if isinstance(checksums, Sequence) and not isinstance(checksums, (str, bytes)):
    if not checksums:
      issues.append('checksums must include at least one entry')
    for index, checksum in enumerate(checksums):
      if isinstance(checksum, Mapping):
        issues.extend(
          _missing_fields(
            checksum,
            REQUIRED_CHECKSUM_FIELDS,
            'checksums[{index}]'.format(index=index),
          )
        )
        if not any(field in checksum for field in REQUIRED_CHECKSUM_VALUE_FIELDS):
          issues.append(
            'checksums[{index}] must include `value` or `value_placeholder`'.format(
              index=index,
            )
          )
      else:
        issues.append('checksums[{index}] must be a mapping'.format(index=index))

  return tuple(issues)


def _missing_fields(
  mapping: Mapping[str, object],
  required_fields: Sequence[str],
  context: str,
) -> Tuple[str, ...]:
  missing = []
  for field_name in required_fields:
    if field_name not in mapping:
      missing.append('{context}.{field_name} is required'.format(
        context=context,
        field_name=field_name,
      ))
  return tuple(missing)


def _mapping_value(
  mapping: Mapping[str, object],
  key: str,
) -> Optional[Mapping[str, object]]:
  value = mapping.get(key)
  if isinstance(value, Mapping):
    return value
  return None