"""Safe real-package intake for Calamum Vulcan FS2-02."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Tuple
import zipfile

from calamum_vulcan.validation import UnsafeArchiveMemberError
from calamum_vulcan.validation import safe_extract_zip_archive

from .model import PackageManifestAssessment
from .parser import assess_package_manifest
from .parser import with_additional_assessment_issues
from .snapshot import AnalyzedPackageSnapshotError
from .snapshot import bind_analyzed_snapshot_verification
from .snapshot import reverify_analyzed_package_snapshot
from .snapshot import seal_analyzed_package_snapshot


PACKAGE_ARCHIVE_MANIFEST_NAMES = (
  'package_manifest.json',
  'manifest.json',
)
SUPPORTED_PACKAGE_ARCHIVE_SUFFIXES = ('.zip',)


class PackageArchiveImportError(ValueError):
  """Raised when a real package archive cannot satisfy the bounded intake contract."""


@dataclass(frozen=True)
class ImportedPackageArtifact:
  """One normalized package archive staged for later platform-owned use."""

  archive_path: Path
  manifest_member: str
  staging_root: Path
  payload_members: Tuple[str, ...]
  assessment: PackageManifestAssessment


def assess_package_archive(
  archive_path: Path,
  detected_product_code: Optional[str] = None,
) -> PackageManifestAssessment:
  """Assess one real package archive without retaining a staged extraction root."""

  with TemporaryDirectory() as temp_dir:
    artifact = import_package_archive(
      archive_path,
      Path(temp_dir),
      detected_product_code=detected_product_code,
    )
    try:
      snapshot = seal_analyzed_package_snapshot(artifact)
    except AnalyzedPackageSnapshotError as error:
      return replace(
        artifact.assessment,
        snapshot_issues=(str(error),),
      )
    verification = reverify_analyzed_package_snapshot(
      snapshot,
      artifact.archive_path,
    )
    return bind_analyzed_snapshot_verification(
      artifact.assessment,
      snapshot,
      verification,
    )


def import_package_archive(
  archive_path: Path,
  staging_root: Path,
  detected_product_code: Optional[str] = None,
) -> ImportedPackageArtifact:
  """Safely stage one package archive and return its normalized assessment."""

  archive_file = Path(archive_path)
  if not archive_file.is_file():
    raise PackageArchiveImportError(
      'Package archive does not exist: {path}'.format(path=archive_file)
    )
  if archive_file.suffix.lower() not in SUPPORTED_PACKAGE_ARCHIVE_SUFFIXES:
    raise PackageArchiveImportError(
      'Unsupported package archive type for {path}; expected one of: {suffixes}.'.format(
        path=archive_file.name,
        suffixes=', '.join(SUPPORTED_PACKAGE_ARCHIVE_SUFFIXES),
      )
    )

  member_map = _collect_archive_members(archive_file)
  manifest_member = _resolve_manifest_member(member_map)

  try:
    safe_extract_zip_archive(archive_file, staging_root)
  except UnsafeArchiveMemberError as error:
    raise PackageArchiveImportError(
      'Package archive failed the safe extraction contract: {error}'.format(
        error=error,
      )
    ) from error

  manifest_path = staging_root.joinpath(*PurePosixPath(manifest_member).parts)
  try:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
  except json.JSONDecodeError as error:
    raise PackageArchiveImportError(
      'Package archive manifest could not be decoded as JSON: {error}'.format(
        error=error,
      )
    ) from error

  normalized_manifest, payload_members, import_issues = _normalize_manifest_for_archive(
    manifest,
    member_map,
    staging_root,
  )
  assessment = assess_package_manifest(
    normalized_manifest,
    detected_product_code=detected_product_code,
    fixture_name=archive_file.name,
    source_kind='archive',
    staged_root=staging_root,
    payload_members=payload_members,
  )
  assessment = with_additional_assessment_issues(assessment, import_issues)

  return ImportedPackageArtifact(
    archive_path=archive_file,
    manifest_member=manifest_member,
    staging_root=staging_root,
    payload_members=payload_members,
    assessment=assessment,
  )


def _collect_archive_members(
  archive_path: Path,
) -> Dict[str, zipfile.ZipInfo]:
  try:
    archive = zipfile.ZipFile(archive_path)
  except zipfile.BadZipFile as error:
    raise PackageArchiveImportError(
      'Package archive is not a readable zip container: {path}'.format(
        path=archive_path.name,
      )
    ) from error

  members = {}  # type: Dict[str, zipfile.ZipInfo]
  seen_names = {}  # type: Dict[str, str]
  with archive:
    for member in archive.infolist():
      normalized_name = _normalized_archive_member_name(member.filename)
      collision_key = normalized_name.casefold()
      if collision_key in seen_names:
        raise PackageArchiveImportError(
          'Package archive contains colliding members after normalization: {left} and {right}.'.format(
            left=seen_names[collision_key],
            right=member.filename,
          )
        )
      seen_names[collision_key] = member.filename
      members[normalized_name] = member
  return members


def _resolve_manifest_member(
  member_map: Mapping[str, zipfile.ZipInfo],
) -> str:
  candidates = []
  for member_name, member in member_map.items():
    if member.is_dir():
      continue
    if member_name in PACKAGE_ARCHIVE_MANIFEST_NAMES:
      candidates.append(member_name)

  if len(candidates) != 1:
    raise PackageArchiveImportError(
      'Package archive must contain exactly one root manifest named {names}.'.format(
        names=', '.join(PACKAGE_ARCHIVE_MANIFEST_NAMES),
      )
    )
  return candidates[0]


def _normalize_manifest_for_archive(
  manifest: Mapping[str, object],
  member_map: Mapping[str, zipfile.ZipInfo],
  staging_root: Path,
) -> Tuple[Dict[str, object], Tuple[str, ...], Tuple[str, ...]]:
  normalized_manifest = json.loads(json.dumps(manifest))
  raw_checksums = normalized_manifest.get('checksums')
  if not isinstance(raw_checksums, list):
    return normalized_manifest, (), ()

  normalized_checksums = []
  payload_members = []
  import_issues = []
  for raw_entry in raw_checksums:
    if not isinstance(raw_entry, dict):
      normalized_checksums.append(raw_entry)
      continue

    entry = dict(raw_entry)
    file_name = entry.get('file_name')
    checksum_id = str(entry.get('checksum_id', 'unknown-checksum'))
    algorithm = str(entry.get('algorithm', 'unknown')).lower()
    if not isinstance(file_name, str) or not file_name:
      import_issues.append(
        'Checksum {checksum_id} does not declare a usable payload file name.'.format(
          checksum_id=checksum_id,
        )
      )
      entry['verified'] = False
      entry['source_label'] = 'archive_incomplete_digest'
      normalized_checksums.append(entry)
      continue

    try:
      normalized_payload_name = _normalized_archive_member_name(file_name)
    except PackageArchiveImportError as error:
      import_issues.append(str(error))
      entry['verified'] = False
      entry['source_label'] = 'archive_incomplete_digest'
      normalized_checksums.append(entry)
      continue

    if normalized_payload_name not in member_map or member_map[normalized_payload_name].is_dir():
      import_issues.append(
        'Checksum {checksum_id} references missing payload {file_name}.'.format(
          checksum_id=checksum_id,
          file_name=file_name,
        )
      )
      entry['verified'] = False
      entry['source_label'] = 'archive_incomplete_digest'
      normalized_checksums.append(entry)
      continue

    if algorithm != 'sha256':
      import_issues.append(
        'Checksum {checksum_id} uses unsupported algorithm {algorithm}; only sha256 is accepted in this slice.'.format(
          checksum_id=checksum_id,
          algorithm=algorithm,
        )
      )
      entry['verified'] = False
      entry['source_label'] = 'archive_incomplete_digest'
      normalized_checksums.append(entry)
      continue

    payload_members.append(normalized_payload_name)
    payload_path = staging_root.joinpath(*PurePosixPath(normalized_payload_name).parts)
    if not payload_path.is_file():
      import_issues.append(
        'Checksum {checksum_id} could not locate staged payload {file_name}.'.format(
          checksum_id=checksum_id,
          file_name=file_name,
        )
      )
      entry['verified'] = False
      entry['source_label'] = 'archive_incomplete_digest'
      normalized_checksums.append(entry)
      continue

    digest = _sha256_for_file(payload_path)
    manifest_value = entry.get('value')
    verified = True
    source_label = 'archive_computed_digest'
    if manifest_value is not None:
      verified = str(manifest_value).lower() == digest.lower()
      source_label = 'archive_verified_digest'
      if not verified:
        import_issues.append(
          'Checksum mismatch for {file_name}: manifest digest does not match the imported payload.'.format(
            file_name=file_name,
          )
        )

    entry['value'] = digest
    entry['verified'] = verified
    entry['source_label'] = source_label
    normalized_checksums.append(entry)

  normalized_manifest['checksums'] = normalized_checksums
  return normalized_manifest, tuple(payload_members), tuple(import_issues)


def _normalized_archive_member_name(raw_name: str) -> str:
  normalized_input = raw_name.replace('\\', '/')
  relative_path = PurePosixPath(normalized_input)
  if not normalized_input or normalized_input.startswith('/'):
    raise PackageArchiveImportError(
      'Archive member {name!r} uses an absolute or empty path.'.format(
        name=raw_name,
      )
    )
  if relative_path.parts and relative_path.parts[0].endswith(':'):
    raise PackageArchiveImportError(
      'Archive member {name!r} uses a drive-qualified path.'.format(
        name=raw_name,
      )
    )
  if any(part in ('', '.', '..') for part in relative_path.parts):
    raise PackageArchiveImportError(
      'Archive member {name!r} escapes the package root.'.format(
        name=raw_name,
      )
    )
  return '/'.join(relative_path.parts)


def _sha256_for_file(file_path: Path) -> str:
  digest = hashlib.sha256()
  with file_path.open('rb') as handle:
    while True:
      chunk = handle.read(1024 * 1024)
      if not chunk:
        break
      digest.update(chunk)
  return digest.hexdigest()
