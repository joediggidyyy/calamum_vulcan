"""Analyzed package snapshot sealing and re-verification for FS2-03."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from datetime import timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

from .model import PackageManifestAssessment


if TYPE_CHECKING:
  from .importer import ImportedPackageArtifact


ANALYZED_SNAPSHOT_SCHEMA_VERSION = '0.2.0-fs2-03'


class AnalyzedPackageSnapshotError(ValueError):
  """Raised when a reviewed package cannot be sealed into a snapshot."""


@dataclass(frozen=True)
class SnapshotPartitionRecord:
  """One reviewed partition row captured in the analyzed snapshot."""

  partition_name: str
  file_name: str
  checksum_id: str
  required: bool


@dataclass(frozen=True)
class SnapshotPayloadDigest:
  """One reviewed payload digest captured in the analyzed snapshot."""

  checksum_id: str
  file_name: str
  algorithm: str
  digest: str


@dataclass(frozen=True)
class AnalyzedPackageSnapshot:
  """One sealed reviewed package snapshot used to guard execution integrity."""

  schema_version: str
  snapshot_id: str
  created_at_utc: str
  source_kind: str
  source_label: str
  manifest_member: str
  payload_members: Tuple[str, ...]
  archive_sha256: str
  archive_size_bytes: int
  package_id: str
  display_name: str
  version: str
  source_build: str
  compatibility_expectation: str
  supported_product_codes: Tuple[str, ...]
  supported_device_names: Tuple[str, ...]
  pit_fingerprint: str
  risk_level: Optional[str]
  reboot_policy: Optional[str]
  repartition_allowed: bool
  partitions: Tuple[SnapshotPartitionRecord, ...]
  payload_digests: Tuple[SnapshotPayloadDigest, ...]

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable representation of the snapshot."""

    return asdict(self)


@dataclass(frozen=True)
class AnalyzedSnapshotVerification:
  """Re-verification result for one sealed analyzed snapshot."""

  snapshot_id: Optional[str]
  checked_at_utc: str
  verified: bool
  drift_detected: bool
  summary: str
  issues: Tuple[str, ...] = ()
  current_snapshot_id: Optional[str] = None
  current_archive_sha256: Optional[str] = None

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable representation of the verification."""

    return asdict(self)


def seal_analyzed_package_snapshot(
  artifact: 'ImportedPackageArtifact',
  captured_at_utc: Optional[str] = None,
) -> AnalyzedPackageSnapshot:
  """Seal one reviewed archive-backed package into a deterministic snapshot."""

  assessment = artifact.assessment
  if assessment.source_kind != 'archive':
    raise AnalyzedPackageSnapshotError(
      'Analyzed snapshots can only be sealed from archive-backed package reviews.'
    )
  if not assessment.contract_complete:
    raise AnalyzedPackageSnapshotError(
      'Analyzed snapshot sealing requires a contract-complete package review.'
    )
  if not assessment.checksum_verification_complete:
    raise AnalyzedPackageSnapshotError(
      'Analyzed snapshot sealing requires verified payload digests.'
    )
  if not assessment.checksums:
    raise AnalyzedPackageSnapshotError(
      'Analyzed snapshot sealing requires at least one reviewed payload digest.'
    )
  if not artifact.archive_path.is_file():
    raise AnalyzedPackageSnapshotError(
      'Analyzed snapshot sealing requires the reviewed archive to remain available.'
    )

  archive_sha256 = _sha256_for_file(artifact.archive_path)
  archive_size_bytes = artifact.archive_path.stat().st_size
  created = captured_at_utc or _utc_now()
  payload_members = tuple(sorted(set(artifact.payload_members)))
  partitions = tuple(
    SnapshotPartitionRecord(
      partition_name=partition.partition_name,
      file_name=partition.file_name,
      checksum_id=partition.checksum_id,
      required=partition.required,
    )
    for partition in assessment.partitions
  )
  payload_digests = tuple(
    SnapshotPayloadDigest(
      checksum_id=checksum.checksum_id,
      file_name=checksum.file_name,
      algorithm=checksum.algorithm,
      digest=checksum.display_value,
    )
    for checksum in assessment.checksums
  )

  material = {
    'schema_version': ANALYZED_SNAPSHOT_SCHEMA_VERSION,
    'source_kind': assessment.source_kind,
    'manifest_member': artifact.manifest_member,
    'payload_members': payload_members,
    'archive_sha256': archive_sha256,
    'archive_size_bytes': archive_size_bytes,
    'package_id': assessment.display_package_id,
    'display_name': assessment.display_name,
    'version': assessment.version,
    'source_build': assessment.source_build,
    'compatibility_expectation': assessment.compatibility_expectation.value,
    'supported_product_codes': assessment.supported_product_codes,
    'supported_device_names': assessment.supported_device_names,
    'pit_fingerprint': assessment.pit_fingerprint,
    'risk_level': (
      assessment.risk_level.value if assessment.risk_level is not None else None
    ),
    'reboot_policy': (
      assessment.reboot_policy.value
      if assessment.reboot_policy is not None
      else None
    ),
    'repartition_allowed': assessment.repartition_allowed,
    'partitions': [asdict(partition) for partition in partitions],
    'payload_digests': [asdict(digest) for digest in payload_digests],
  }
  snapshot_id = _stable_hash(material)
  return AnalyzedPackageSnapshot(
    schema_version=ANALYZED_SNAPSHOT_SCHEMA_VERSION,
    snapshot_id=snapshot_id,
    created_at_utc=created,
    source_kind=assessment.source_kind,
    source_label=artifact.archive_path.name,
    manifest_member=artifact.manifest_member,
    payload_members=payload_members,
    archive_sha256=archive_sha256,
    archive_size_bytes=archive_size_bytes,
    package_id=assessment.display_package_id,
    display_name=assessment.display_name,
    version=assessment.version,
    source_build=assessment.source_build,
    compatibility_expectation=assessment.compatibility_expectation.value,
    supported_product_codes=assessment.supported_product_codes,
    supported_device_names=assessment.supported_device_names,
    pit_fingerprint=assessment.pit_fingerprint,
    risk_level=(
      assessment.risk_level.value if assessment.risk_level is not None else None
    ),
    reboot_policy=(
      assessment.reboot_policy.value
      if assessment.reboot_policy is not None
      else None
    ),
    repartition_allowed=assessment.repartition_allowed,
    partitions=partitions,
    payload_digests=payload_digests,
  )


def reverify_analyzed_package_snapshot(
  snapshot: AnalyzedPackageSnapshot,
  archive_path: Path,
  checked_at_utc: Optional[str] = None,
) -> AnalyzedSnapshotVerification:
  """Re-import and re-seal one reviewed archive to detect execution-path drift."""

  checked = checked_at_utc or _utc_now()
  current_archive_path = Path(archive_path)
  if not current_archive_path.is_file():
    return AnalyzedSnapshotVerification(
      snapshot_id=snapshot.snapshot_id,
      checked_at_utc=checked,
      verified=False,
      drift_detected=True,
      summary='Analyzed snapshot re-verification failed because the reviewed archive is missing.',
      issues=(
        'Reviewed archive is missing at re-verification time: {path}'.format(
          path=current_archive_path,
        ),
      ),
    )

  try:
    from .importer import PackageArchiveImportError
    from .importer import import_package_archive

    with TemporaryDirectory() as temp_dir:
      current_artifact = import_package_archive(
        current_archive_path,
        Path(temp_dir),
      )
      current_snapshot = seal_analyzed_package_snapshot(current_artifact)
  except (AnalyzedPackageSnapshotError, PackageArchiveImportError) as error:
    return AnalyzedSnapshotVerification(
      snapshot_id=snapshot.snapshot_id,
      checked_at_utc=checked,
      verified=False,
      drift_detected=True,
      summary='Analyzed snapshot re-verification failed because the reviewed archive can no longer be trusted.',
      issues=(str(error),),
    )

  issues = []
  if current_snapshot.archive_sha256 != snapshot.archive_sha256:
    issues.append('Source archive bytes changed after snapshot review.')
  if current_snapshot.snapshot_id != snapshot.snapshot_id:
    issues.append('Analyzed snapshot identity drift detected before execution.')

  verified = not issues
  summary = 'Analyzed snapshot re-verification passed for the reviewed package.'
  if not verified:
    summary = 'Analyzed snapshot re-verification detected reviewed-input drift.'
  return AnalyzedSnapshotVerification(
    snapshot_id=snapshot.snapshot_id,
    checked_at_utc=checked,
    verified=verified,
    drift_detected=not verified,
    summary=summary,
    issues=tuple(issues),
    current_snapshot_id=current_snapshot.snapshot_id,
    current_archive_sha256=current_snapshot.archive_sha256,
  )


def bind_analyzed_snapshot_verification(
  assessment: PackageManifestAssessment,
  snapshot: AnalyzedPackageSnapshot,
  verification: AnalyzedSnapshotVerification,
) -> PackageManifestAssessment:
  """Attach snapshot identity and re-verification status to one package assessment."""

  return replace(
    assessment,
    analyzed_snapshot_id=snapshot.snapshot_id,
    analyzed_snapshot_created_at_utc=snapshot.created_at_utc,
    analyzed_snapshot_verified=verification.verified,
    analyzed_snapshot_drift_detected=verification.drift_detected,
    snapshot_issues=verification.issues,
  )


def _stable_hash(payload: Dict[str, Any]) -> str:
  return hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
  ).hexdigest()


def _sha256_for_file(file_path: Path) -> str:
  digest = hashlib.sha256()
  with file_path.open('rb') as handle:
    while True:
      chunk = handle.read(1024 * 1024)
      if not chunk:
        break
      digest.update(chunk)
  return digest.hexdigest()


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    '+00:00',
    'Z',
  )