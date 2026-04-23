"""Tests for the shared readiness aggregate reporting helpers."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from scripts.readiness_reporting import render_readiness_aggregate_report
from scripts.readiness_reporting import write_readiness_aggregate_report


class ReadinessReportingTests(unittest.TestCase):
  """Keep aggregate readiness reporting disk-backed and summary-first."""

  def _build_sample_archive(self) -> tuple[Path, dict[str, object]]:
    temp_dir = tempfile.TemporaryDirectory()
    self.addCleanup(temp_dir.cleanup)
    repo_root = Path(temp_dir.name)
    archive_root = repo_root / 'temp' / 'fs5_readiness'
    passing_root = archive_root / 'aggressive_penetration_suite'
    failing_root = archive_root / 'pytest_baseline'
    passing_root.mkdir(parents=True)
    failing_root.mkdir(parents=True)
    (archive_root / 'readiness_summary.md').write_text('summary', encoding='utf-8')
    (archive_root / 'readiness_summary.json').write_text('{}', encoding='utf-8')
    (passing_root / 'stdout.txt').write_text(
      'security_decision="passed_with_warnings"\nblocking_findings="0"\nwarnings="8"\n',
      encoding='utf-8',
    )
    (passing_root / 'stderr.txt').write_text('', encoding='utf-8')
    (failing_root / 'stdout.txt').write_text(
      '\n'.join(
        (
          'FAILED tests/unit/test_qt_shell_contract.py::test_alpha',
          'FAILED tests/unit/test_qt_shell_contract.py::test_beta',
          '4 failed, 239 passed, 4 subtests passed in 43.29s',
        )
      )
      + '\n',
      encoding='utf-8',
    )
    (failing_root / 'stderr.txt').write_text('', encoding='utf-8')
    summary = {
      'repo_root': str(repo_root),
      'archive_root': str(archive_root),
      'include_testpypi_rehearsal': False,
      'overall_status': 'failed',
      'lanes': [
        {
          'name': 'pytest_baseline',
          'category': 'pytest',
          'status': 'failed',
          'returncode': 1,
          'command': ('python', '-m', 'pytest', 'tests/unit', '-q'),
          'evidence_hint': 'Source-tree contract and unit proof.',
          'stdout_path': str(failing_root / 'stdout.txt'),
          'stderr_path': str(failing_root / 'stderr.txt'),
        },
        {
          'name': 'aggressive_penetration_suite',
          'category': 'penetration',
          'status': 'passed',
          'returncode': 0,
          'command': ('python', 'scripts/run_security_validation_suite.py'),
          'evidence_hint': 'Security validation artifacts under temp/security_validation/.',
          'stdout_path': str(passing_root / 'stdout.txt'),
          'stderr_path': str(passing_root / 'stderr.txt'),
        },
      ],
    }
    return archive_root, summary

  def test_rendered_aggregate_report_is_summary_first(self) -> None:
    archive_root, summary = self._build_sample_archive()

    markdown = render_readiness_aggregate_report(
      summary,
      archive_root=archive_root,
      repo_root=Path(summary['repo_root']),
      sprint_label='0.5.0',
      generated_on='2026-04-23',
    )

    self.assertIn('# Sprint 0.5.0 readiness aggregate report', markdown)
    self.assertLess(markdown.index('## Summary'), markdown.index('## Lane result summary'))
    self.assertIn('verified report artifacts on disk', markdown)
    self.assertIn('`temp/fs5_readiness/pytest_baseline/stdout.txt`', markdown)
    self.assertIn('4 failed, 239 passed, 4 subtests passed in 43.29s', markdown)
    self.assertIn('## Verified report artifacts on disk', markdown)

  def test_write_aggregate_report_persists_to_archive(self) -> None:
    archive_root, summary = self._build_sample_archive()

    report_path = write_readiness_aggregate_report(
      summary,
      archive_root=archive_root,
      repo_root=Path(summary['repo_root']),
      sprint_label='0.5.0',
      generated_on='2026-04-23',
    )

    self.assertTrue(report_path.exists())
    report_text = report_path.read_text(encoding='utf-8')
    self.assertIn('## Lane output highlights', report_text)
    self.assertIn('## Aggregate conclusion', report_text)


if __name__ == '__main__':
  unittest.main()