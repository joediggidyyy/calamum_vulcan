"""Reviewed flash-plan contracts for Calamum Vulcan FS2-06."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from typing import Tuple


FLASH_PLAN_SCHEMA_VERSION = '0.2.0-fs2-06'


@dataclass(frozen=True)
class ReviewedFlashPlanPartition:
  """One partition row in the reviewed flash plan."""

  partition_name: str
  file_name: str
  checksum_id: str
  digest_value: Optional[str]
  digest_verified: bool
  required: bool


@dataclass(frozen=True)
class ReviewedFlashPlan:
  """Platform-owned reviewed flash plan derived from package truth."""

  schema_version: str
  plan_id: str
  summary: str
  package_id: str
  display_name: str
  source_build: str
  source_kind: str
  snapshot_id: Optional[str]
  canonical_product_code: Optional[str]
  device_marketing_name: Optional[str]
  compatibility_summary: str
  risk_level: str
  reboot_policy: str
  repartition_allowed: bool
  pit_fingerprint: str
  transport_backend: str
  required_capabilities: Tuple[str, ...]
  advanced_requirements: Tuple[str, ...]
  suspicious_warning_count: int
  operator_warnings: Tuple[str, ...]
  requires_operator_acknowledgement: bool
  partitions: Tuple[ReviewedFlashPlanPartition, ...]
  verified_partition_count: int
  blocking_reasons: Tuple[str, ...]
  recovery_guidance: Tuple[str, ...]
  ready_for_transport: bool

  @property
  def partition_targets(self) -> Tuple[str, ...]:
    """Return the partition targets in reviewed execution order."""

    return tuple(partition.partition_name for partition in self.partitions)

  @property
  def required_partition_count(self) -> int:
    """Return the number of required partition rows in the reviewed plan."""

    return sum(1 for partition in self.partitions if partition.required)

  @property
  def optional_partition_count(self) -> int:
    """Return the number of optional partition rows in the reviewed plan."""

    return sum(1 for partition in self.partitions if not partition.required)
