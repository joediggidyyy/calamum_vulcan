"""Shared security-validation helpers for Calamum Vulcan stack closures."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import stat
from typing import Iterable
from typing import List
from typing import Sequence
from typing import Tuple
import zipfile

from calamum_vulcan.adapters.adb_fastboot import runtime as adb_fastboot_runtime


CODE_ROOT_NAMES = ('calamum_vulcan', 'scripts', 'tests')
IGNORED_PATH_PARTS = {
  '__pycache__',
  '.git',
  '.pytest_cache',
  'build',
  'dist',
  'temp',
}
PACKAGE_FIXTURE_DIR = (
  Path(__file__).resolve().parents[1] / 'fixtures' / 'package_manifests'
)
PACKAGE_IMPORTER_PATH = (
  Path(__file__).resolve().parents[1] / 'domain' / 'package' / 'importer.py'
)
IMAGE_HEURISTICS_PATH = (
  Path(__file__).resolve().parents[1] / 'domain' / 'package' / 'image_heuristics.py'
)


class UnsafeArchiveMemberError(ValueError):
  """Raised when a zip archive contains a member outside the safe extraction contract."""


@dataclass(frozen=True)
class SecurityCheckResult:
  """One security validation result."""

  name: str
  status: str
  summary: str
  details: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SecurityValidationSummary:
  """Consolidated security validation summary for one stack closure."""

  decision: str
  checks: Tuple[SecurityCheckResult, ...]
  blocking_findings: Tuple[str, ...]
  warnings: Tuple[str, ...]

  def to_dict(self) -> dict:
    """Return a JSON-serializable representation of the summary."""

    return asdict(self)


class _SecurityPatternVisitor(ast.NodeVisitor):
  """AST visitor that records dangerous code patterns."""

  def __init__(self, file_path: Path) -> None:
    self.file_path = file_path
    self.findings = []  # type: List[str]

  def visit_Call(self, node: ast.Call) -> None:
    callable_name = _callable_name(node.func)
    if callable_name in ('eval', 'exec', 'os.system'):
      self.findings.append(
        '{path}:{line} uses dangerous callable `{name}`.'.format(
          path=self.file_path.as_posix(),
          line=node.lineno,
          name=callable_name,
        )
      )
    if callable_name in (
      'subprocess.run',
      'subprocess.Popen',
      'subprocess.call',
      'subprocess.check_call',
      'subprocess.check_output',
    ):
      for keyword in node.keywords:
        if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant):
          if keyword.value.value is True:
            self.findings.append(
              '{path}:{line} enables `shell=True` for subprocess execution.'.format(
                path=self.file_path.as_posix(),
                line=node.lineno,
              )
            )
    if callable_name == 'extractall' or callable_name.endswith('.extractall'):
      self.findings.append(
        '{path}:{line} uses archive `extractall`, which bypasses the safe extraction contract.'.format(
          path=self.file_path.as_posix(),
          line=node.lineno,
        )
      )
    self.generic_visit(node)


def safe_extract_zip_archive(archive_path: Path, target_root: Path) -> None:
  """Extract a zip archive only when every member stays inside the target root."""

  target_root.mkdir(parents=True, exist_ok=True)
  resolved_root = target_root.resolve()
  with zipfile.ZipFile(archive_path) as archive:
    for member in archive.infolist():
      destination = _safe_zip_destination(resolved_root, member)
      if member.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        continue
      destination.parent.mkdir(parents=True, exist_ok=True)
      with archive.open(member, 'r') as source_handle:
        with destination.open('wb') as destination_handle:
          shutil.copyfileobj(source_handle, destination_handle)


def run_security_validation_suite(repo_root: Path) -> SecurityValidationSummary:
  """Run the current stack-closing security validation suite."""

  checks = (
    _dangerous_python_pattern_check(repo_root),
    _companion_process_timeout_check(),
    _checksum_placeholder_check(),
    _package_importer_check(),
    _image_heuristics_check(),
  )
  blocking_findings = tuple(
    detail
    for check in checks
    if check.status == 'failed'
    for detail in (check.details or (check.summary,))
  )
  warnings = tuple(
    detail
    for check in checks
    if check.status == 'warn'
    for detail in (check.details or (check.summary,))
  )
  if blocking_findings:
    decision = 'failed'
  elif warnings:
    decision = 'passed_with_warnings'
  else:
    decision = 'passed'
  return SecurityValidationSummary(
    decision=decision,
    checks=checks,
    blocking_findings=blocking_findings,
    warnings=warnings,
  )


def write_security_validation_artifacts(
  output_root: Path,
  summary: SecurityValidationSummary,
) -> Tuple[Path, Path]:
  """Write JSON and Markdown security-validation artifacts."""

  output_root.mkdir(parents=True, exist_ok=True)
  json_path = output_root / 'security_validation_summary.json'
  markdown_path = output_root / 'security_validation_summary.md'
  json_path.write_text(
    json.dumps(summary.to_dict(), indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
  )
  markdown_path.write_text(
    _render_markdown_summary(summary),
    encoding='utf-8',
  )
  return json_path, markdown_path


def _dangerous_python_pattern_check(repo_root: Path) -> SecurityCheckResult:
  findings = []  # type: List[str]
  for file_path in _iter_code_files(repo_root):
    try:
      tree = ast.parse(file_path.read_text(encoding='utf-8'))
    except UnicodeDecodeError:
      findings.append(
        '{path} could not be decoded for security scanning.'.format(
          path=file_path.as_posix(),
        )
      )
      continue
    visitor = _SecurityPatternVisitor(file_path.relative_to(repo_root))
    visitor.visit(tree)
    findings.extend(visitor.findings)
  if findings:
    return SecurityCheckResult(
      name='dangerous_python_patterns',
      status='failed',
      summary='Dangerous code patterns were detected in the repo-owned Python surfaces.',
      details=tuple(findings),
    )
  return SecurityCheckResult(
    name='dangerous_python_patterns',
    status='passed',
    summary='No `shell=True`, `os.system`, `eval`, `exec`, or unsafe `extractall` usage was detected in the repo-owned Python surfaces.',
  )


def _companion_process_timeout_check() -> SecurityCheckResult:
  timeout_seconds = getattr(adb_fastboot_runtime, 'PROCESS_TIMEOUT_SECONDS', 0)
  if isinstance(timeout_seconds, int) and timeout_seconds >= 1:
    return SecurityCheckResult(
      name='companion_process_timeout',
      status='passed',
      summary='ADB/Fastboot companion subprocesses are bounded by an explicit timeout.',
      details=('PROCESS_TIMEOUT_SECONDS={value}'.format(value=timeout_seconds),),
    )
  return SecurityCheckResult(
    name='companion_process_timeout',
    status='failed',
    summary='ADB/Fastboot companion subprocesses do not have an explicit timeout bound.',
  )


def _checksum_placeholder_check() -> SecurityCheckResult:
  findings = []  # type: List[str]
  for manifest_path in sorted(PACKAGE_FIXTURE_DIR.glob('*.json')):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for entry in manifest.get('checksums', ()):  # type: ignore[assignment]
      placeholder = entry.get('value_placeholder')
      if isinstance(placeholder, str) and placeholder.startswith('PLACEHOLDER_'):
        findings.append(
          '{name} still uses placeholder checksum coverage for {file_name}.'.format(
            name=manifest_path.name,
            file_name=entry.get('file_name', 'unknown payload'),
          )
        )
  if findings:
    return SecurityCheckResult(
      name='checksum_placeholders',
      status='warn',
      summary='Package fixtures still rely on checksum placeholders instead of verified payload digests.',
      details=tuple(findings),
    )
  return SecurityCheckResult(
    name='checksum_placeholders',
    status='passed',
    summary='Package fixtures no longer rely on checksum placeholders.',
  )


def _package_importer_check() -> SecurityCheckResult:
  if PACKAGE_IMPORTER_PATH.exists():
    return SecurityCheckResult(
      name='package_archive_importer',
      status='passed',
      summary='A package archive importer exists for safe real-package intake.',
      details=(PACKAGE_IMPORTER_PATH.as_posix(),),
    )
  return SecurityCheckResult(
    name='package_archive_importer',
    status='warn',
    summary='Package intake remains fixture-driven; no real package archive importer exists yet.',
  )


def _image_heuristics_check() -> SecurityCheckResult:
  if IMAGE_HEURISTICS_PATH.exists():
    return SecurityCheckResult(
      name='android_image_heuristics',
      status='passed',
      summary='Android-image suspiciousness heuristics exist in the package domain.',
      details=(IMAGE_HEURISTICS_PATH.as_posix(),),
    )
  return SecurityCheckResult(
    name='android_image_heuristics',
    status='warn',
    summary='No Android-image suspiciousness heuristics are implemented yet for rooted or tampered package traits.',
  )


def _iter_code_files(repo_root: Path) -> Iterable[Path]:
  for root_name in CODE_ROOT_NAMES:
    root_path = repo_root / root_name
    if not root_path.exists():
      continue
    for file_path in root_path.rglob('*.py'):
      if any(part in IGNORED_PATH_PARTS for part in file_path.parts):
        continue
      yield file_path


def _callable_name(node: ast.AST) -> str:
  if isinstance(node, ast.Name):
    return node.id
  if isinstance(node, ast.Attribute):
    parent = _callable_name(node.value)
    if parent:
      return parent + '.' + node.attr
    return node.attr
  return ''


def _safe_zip_destination(target_root: Path, member: zipfile.ZipInfo) -> Path:
  raw_name = member.filename.replace('\\', '/')
  relative_path = PurePosixPath(raw_name)
  if not raw_name or raw_name.startswith('/'):
    raise UnsafeArchiveMemberError(
      'Archive member {name!r} uses an absolute or empty path.'.format(
        name=member.filename,
      )
    )
  if relative_path.parts and relative_path.parts[0].endswith(':'):
    raise UnsafeArchiveMemberError(
      'Archive member {name!r} uses a drive-qualified path.'.format(
        name=member.filename,
      )
    )
  if any(part in ('', '.', '..') for part in relative_path.parts):
    raise UnsafeArchiveMemberError(
      'Archive member {name!r} escapes the target root.'.format(
        name=member.filename,
      )
    )
  if _zip_info_is_symlink(member):
    raise UnsafeArchiveMemberError(
      'Archive member {name!r} is a symbolic link.'.format(
        name=member.filename,
      )
    )
  destination = (target_root / Path(*relative_path.parts)).resolve()
  if target_root not in destination.parents and destination != target_root:
    raise UnsafeArchiveMemberError(
      'Archive member {name!r} resolves outside the target root.'.format(
        name=member.filename,
      )
    )
  return destination


def _zip_info_is_symlink(member: zipfile.ZipInfo) -> bool:
  unix_mode = member.external_attr >> 16
  if unix_mode == 0:
    return False
  return stat.S_IFMT(unix_mode) == stat.S_IFLNK


def _render_markdown_summary(summary: SecurityValidationSummary) -> str:
  lines = [
    '## Security validation summary',
    '',
    '- decision: `{decision}`'.format(decision=summary.decision),
    '- blocking findings: `{count}`'.format(count=len(summary.blocking_findings)),
    '- warnings: `{count}`'.format(count=len(summary.warnings)),
    '',
    '### Checks',
    '',
  ]
  for check in summary.checks:
    lines.append(
      '- `{name}`: `{status}` - {summary}'.format(
        name=check.name,
        status=check.status,
        summary=check.summary,
      )
    )
    for detail in check.details:
      lines.append('  - ' + detail)
  return '\n'.join(lines) + '\n'
