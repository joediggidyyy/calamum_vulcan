"""Warning-tier Android image suspiciousness heuristics for Calamum Vulcan FS2-06."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from .model import PackageSuspiciousFinding


HEURISTIC_CONTAINER_KEYS = (
  'android_traits',
  'suspiciousness',
  'android_image_heuristics',
  'warning_indicators',
)
PAYLOAD_SCAN_MAX_BYTES = 1024 * 1024

_FINDING_DEFINITIONS = {
  'test_keys': {
    'title': 'Package signed with test-keys',
    'summary': 'Warning-tier heuristic detected test-keys signing traits in the reviewed package.',
    'operator_guidance': 'Treat the package as custom or non-production firmware and capture explicit operator acknowledgement before execution.',
  },
  'magisk': {
    'title': 'Magisk indicators detected',
    'summary': 'Warning-tier heuristic detected Magisk-related traits in the reviewed package.',
    'operator_guidance': 'Confirm the package is intentionally rooted or patched before execution.',
  },
  'su_binary': {
    'title': 'su indicators detected',
    'summary': 'Warning-tier heuristic detected `su`-style privilege-escalation markers in the reviewed package.',
    'operator_guidance': 'Confirm the package intentionally preserves elevated shell access before execution.',
  },
  'insecure_properties': {
    'title': 'Insecure Android properties detected',
    'summary': 'Warning-tier heuristic detected insecure Android property defaults in the reviewed package.',
    'operator_guidance': 'Review insecure property overrides and confirm they are intentional for the current lab workflow.',
  },
  'avb_disabled': {
    'title': 'AVB verification disablement detected',
    'summary': 'Warning-tier heuristic detected Android Verified Boot disablement in the reviewed package.',
    'operator_guidance': 'Confirm AVB disablement is required and compatible with the current recovery workflow before execution.',
  },
  'dm_verity_disabled': {
    'title': 'dm-verity disablement detected',
    'summary': 'Warning-tier heuristic detected dm-verity disablement in the reviewed package.',
    'operator_guidance': 'Confirm verity disablement is intentional and appropriate for the current device state before execution.',
  },
  'selinux_permissive': {
    'title': 'Permissive SELinux detected',
    'summary': 'Warning-tier heuristic detected permissive SELinux traits in the reviewed package.',
    'operator_guidance': 'Confirm permissive SELinux behavior is intentional and acceptable for the current lab workflow.',
  },
}


def assess_android_image_heuristics(
  manifest: Mapping[str, object],
  staged_root: Optional[Path] = None,
  payload_members: Sequence[str] = (),
) -> Tuple[PackageSuspiciousFinding, ...]:
  """Return warning-tier suspiciousness findings from manifest and payload truth."""

  findings = []  # type: List[PackageSuspiciousFinding]
  heuristic_mappings = _heuristic_mappings(manifest)
  findings.extend(_manifest_findings(heuristic_mappings))
  if staged_root is not None:
    findings.extend(_payload_findings(Path(staged_root), payload_members))
  return tuple(_dedupe_findings(findings))


def summarize_suspicious_findings(
  findings: Sequence[PackageSuspiciousFinding],
) -> str:
  """Return an operator-facing suspiciousness summary."""

  if not findings:
    return 'No suspicious Android traits detected.'
  if len(findings) == 1:
    return findings[0].summary
  labels = [finding.title for finding in findings[:3]]
  label_summary = ', '.join(labels)
  remaining = len(findings) - len(labels)
  if remaining > 0:
    label_summary += ', +{count} more'.format(count=remaining)
  return '{count} warning-tier suspicious Android traits detected: {labels}.'.format(
    count=len(findings),
    labels=label_summary,
  )


def _heuristic_mappings(
  manifest: Mapping[str, object],
) -> Tuple[Mapping[str, object], ...]:
  mappings = []  # type: List[Mapping[str, object]]
  for key in HEURISTIC_CONTAINER_KEYS:
    value = manifest.get(key)
    if isinstance(value, Mapping):
      mappings.append(value)
  mappings.append(manifest)
  return tuple(mappings)


def _manifest_findings(
  mappings: Sequence[Mapping[str, object]],
) -> List[PackageSuspiciousFinding]:
  findings = []  # type: List[PackageSuspiciousFinding]

  if _truthy(_value_for_keys(mappings, 'signed_with_test_keys', 'test_keys')):
    findings.append(_finding('test_keys', 'manifest_declared', 'signed_with_test_keys=true'))
  else:
    build_tags = _string_values(_value_for_keys(mappings, 'build_tags', 'signing_tags', 'tags'))
    if _contains_any(build_tags, ('test-keys',)):
      findings.append(
        _finding(
          'test_keys',
          'manifest_declared',
          _first_matching_value(build_tags, ('test-keys',)),
        )
      )

  magisk_values = _string_values(
    _value_for_keys(mappings, 'magisk_indicators', 'magisk_markers', 'magisk')
  )
  if _truthy(_value_for_keys(mappings, 'magisk')) or magisk_values:
    findings.append(
      _finding(
        'magisk',
        'manifest_declared',
        _evidence_or_default(magisk_values, 'magisk indicator declared'),
      )
    )

  su_values = _string_values(
    _value_for_keys(mappings, 'su_indicators', 'su_markers', 'su')
  )
  if _truthy(_value_for_keys(mappings, 'su_present')) or su_values:
    findings.append(
      _finding(
        'su_binary',
        'manifest_declared',
        _evidence_or_default(su_values, 'su indicator declared'),
      )
    )

  insecure_props = _string_values(
    _value_for_keys(mappings, 'insecure_properties', 'insecure_props', 'build_properties')
  )
  if _truthy(_value_for_keys(mappings, 'insecure_defaults')) or _contains_any(
    insecure_props,
    ('ro.secure=0', 'ro.debuggable=1', 'ro.adb.secure=0'),
  ):
    findings.append(
      _finding(
        'insecure_properties',
        'manifest_declared',
        _first_matching_value(
          insecure_props,
          ('ro.secure=0', 'ro.debuggable=1', 'ro.adb.secure=0'),
        ) or 'insecure property override declared',
      )
    )

  if _truthy(
    _value_for_keys(
      mappings,
      'avb_disabled',
      'avb_verification_disabled',
      'disable_verification',
    )
  ):
    findings.append(
      _finding('avb_disabled', 'manifest_declared', 'AVB disablement declared')
    )

  if _truthy(
    _value_for_keys(
      mappings,
      'dm_verity_disabled',
      'verity_disabled',
      'disable_verity',
    )
  ):
    findings.append(
      _finding(
        'dm_verity_disabled',
        'manifest_declared',
        'dm-verity disablement declared',
      )
    )

  selinux_value = _value_for_keys(
    mappings,
    'selinux_permissive',
    'permissive_selinux',
    'selinux_state',
  )
  if _truthy(selinux_value) or _string_contains(selinux_value, 'permissive'):
    findings.append(
      _finding(
        'selinux_permissive',
        'manifest_declared',
        _string_value(selinux_value, 'SELinux permissive declared'),
      )
    )

  return findings


def _payload_findings(
  staged_root: Path,
  payload_members: Sequence[str],
) -> List[PackageSuspiciousFinding]:
  findings = []  # type: List[PackageSuspiciousFinding]
  for member_name in _scan_member_names(staged_root, payload_members):
    lower_name = member_name.lower()
    file_path = staged_root.joinpath(*PurePosixPath(member_name).parts)

    if 'magisk' in lower_name:
      findings.append(_finding('magisk', 'payload_scan', member_name))

    if not file_path.is_file():
      continue

    data = _read_payload_window(file_path)
    if not data:
      continue

    token = _first_matching_bytes(data, (b'test-keys',))
    if token is not None:
      findings.append(_finding('test_keys', 'payload_scan', token.decode('utf-8', errors='ignore')))

    token = _first_matching_bytes(data, (b'magisk', b'init.magisk.rc', b'magiskinit'))
    if token is not None:
      findings.append(_finding('magisk', 'payload_scan', token.decode('utf-8', errors='ignore')))

    token = _first_matching_bytes(
      data,
      (b'/system/xbin/su', b'/system/bin/su', b'/sbin/su', b'busybox su', b'toybox su'),
    )
    if token is not None:
      findings.append(_finding('su_binary', 'payload_scan', token.decode('utf-8', errors='ignore')))

    token = _first_matching_bytes(
      data,
      (b'ro.secure=0', b'ro.debuggable=1', b'ro.adb.secure=0'),
    )
    if token is not None:
      findings.append(
        _finding(
          'insecure_properties',
          'payload_scan',
          token.decode('utf-8', errors='ignore'),
        )
      )

    token = _first_matching_bytes(
      data,
      (b'avbctl disable-verification', b'disable-verification', b'--disable-verification'),
    )
    if token is not None:
      findings.append(_finding('avb_disabled', 'payload_scan', token.decode('utf-8', errors='ignore')))

    token = _first_matching_bytes(
      data,
      (b'disable-verity', b'dm-verity disabled', b'androidboot.veritymode=disabled'),
    )
    if token is not None:
      findings.append(
        _finding(
          'dm_verity_disabled',
          'payload_scan',
          token.decode('utf-8', errors='ignore'),
        )
      )

    token = _first_matching_bytes(
      data,
      (b'selinux=permissive', b'androidboot.selinux=permissive', b'setenforce 0'),
    )
    if token is not None:
      findings.append(
        _finding(
          'selinux_permissive',
          'payload_scan',
          token.decode('utf-8', errors='ignore'),
        )
      )

  return findings


def _scan_member_names(
  staged_root: Path,
  payload_members: Sequence[str],
) -> Tuple[str, ...]:
  if payload_members:
    return tuple(str(member) for member in payload_members)
  members = []  # type: List[str]
  for file_path in staged_root.rglob('*'):
    if file_path.is_file():
      members.append(file_path.relative_to(staged_root).as_posix())
  return tuple(sorted(members))


def _read_payload_window(file_path: Path) -> bytes:
  with file_path.open('rb') as handle:
    return handle.read(PAYLOAD_SCAN_MAX_BYTES).lower()


def _value_for_keys(
  mappings: Sequence[Mapping[str, object]],
  *keys: str
) -> Optional[object]:
  for key in keys:
    for mapping in mappings:
      if key in mapping and mapping.get(key) is not None:
        return mapping.get(key)
  return None


def _string_values(value: object) -> Tuple[str, ...]:
  if value is None:
    return ()
  if isinstance(value, (str, bytes)):
    return (str(value),)
  if isinstance(value, Sequence):
    return tuple(str(item) for item in value)
  return (str(value),)


def _truthy(value: object) -> bool:
  if isinstance(value, bool):
    return value
  if value is None:
    return False
  if isinstance(value, str):
    return value.strip().lower() in ('1', 'true', 'yes', 'present', 'permissive')
  return bool(value)


def _string_contains(value: object, token: str) -> bool:
  if value is None:
    return False
  return token.lower() in str(value).lower()


def _contains_any(values: Sequence[str], tokens: Sequence[str]) -> bool:
  return _first_matching_value(values, tokens) is not None


def _first_matching_value(
  values: Sequence[str],
  tokens: Sequence[str],
) -> Optional[str]:
  lowered_tokens = tuple(token.lower() for token in tokens)
  for value in values:
    lowered_value = value.lower()
    for token in lowered_tokens:
      if token in lowered_value:
        return value
  return None


def _first_matching_bytes(
  data: bytes,
  tokens: Sequence[bytes],
) -> Optional[bytes]:
  for token in tokens:
    if token in data:
      return token
  return None


def _string_value(value: object, default: str) -> str:
  if value is None:
    return default
  return str(value)


def _evidence_or_default(values: Sequence[str], default: str) -> str:
  if values:
    return values[0]
  return default


def _finding(
  indicator_id: str,
  evidence_source: str,
  evidence_value: str,
) -> PackageSuspiciousFinding:
  definition = _FINDING_DEFINITIONS[indicator_id]
  return PackageSuspiciousFinding(
    indicator_id=indicator_id,
    title=definition['title'],
    summary=definition['summary'],
    operator_guidance=definition['operator_guidance'],
    evidence_source=evidence_source,
    evidence_value=evidence_value,
  )


def _dedupe_findings(
  findings: Sequence[PackageSuspiciousFinding],
) -> Tuple[PackageSuspiciousFinding, ...]:
  deduped = []  # type: List[PackageSuspiciousFinding]
  seen = set()
  for finding in findings:
    if finding.indicator_id in seen:
      continue
    seen.add(finding.indicator_id)
    deduped.append(finding)
  return tuple(deduped)
