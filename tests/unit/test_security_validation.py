"""Unit tests for the Calamum Vulcan shared security validation helpers."""

from __future__ import annotations

import stat
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.validation import UnsafeArchiveMemberError
from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import safe_extract_zip_archive


class SecurityValidationTests(unittest.TestCase):
  """Prove the shared security validation suite stays explicit and bounded."""

  def test_safe_extract_zip_archive_extracts_regular_members(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path = Path(temp_dir) / 'sample.zip'
      output_root = Path(temp_dir) / 'out'
      with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('pkg/data.txt', 'calamum')

      safe_extract_zip_archive(archive_path, output_root)

      self.assertEqual(
        (output_root / 'pkg' / 'data.txt').read_text(encoding='utf-8'),
        'calamum',
      )

  def test_safe_extract_zip_archive_blocks_path_traversal(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path = Path(temp_dir) / 'unsafe.zip'
      output_root = Path(temp_dir) / 'out'
      with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('../escape.txt', 'bad')

      with self.assertRaises(UnsafeArchiveMemberError):
        safe_extract_zip_archive(archive_path, output_root)

  def test_safe_extract_zip_archive_blocks_drive_qualified_member(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path = Path(temp_dir) / 'drive-qualified.zip'
      output_root = Path(temp_dir) / 'out'
      with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('C:/escape.txt', 'bad')

      with self.assertRaises(UnsafeArchiveMemberError):
        safe_extract_zip_archive(archive_path, output_root)

  def test_safe_extract_zip_archive_blocks_symbolic_link_member(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path = Path(temp_dir) / 'symlink.zip'
      output_root = Path(temp_dir) / 'out'
      link_info = zipfile.ZipInfo('pkg/link-to-secret')
      link_info.create_system = 3
      link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
      with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr(link_info, 'secret.txt')

      with self.assertRaises(UnsafeArchiveMemberError):
        safe_extract_zip_archive(archive_path, output_root)

  def test_security_validation_suite_passes_without_blocking_findings(self) -> None:
    summary = run_security_validation_suite(FINAL_EXAM_ROOT)
    checks = {check.name: check for check in summary.checks}

    self.assertNotEqual(summary.decision, 'failed')
    self.assertEqual(checks['dangerous_python_patterns'].status, 'passed')
    self.assertEqual(checks['companion_process_timeout'].status, 'passed')
    self.assertEqual(checks['heimdall_process_timeout'].status, 'passed')
    self.assertEqual(checks['live_device_read_side_truth'].status, 'passed')
    self.assertEqual(checks['pit_read_side_truth'].status, 'passed')
    self.assertEqual(checks['device_registry_truth'].status, 'passed')
    self.assertEqual(checks['flash_plan_review_surface'].status, 'passed')
    self.assertEqual(checks['android_image_heuristics'].status, 'passed')
    self.assertEqual(checks['runtime_session_loop'].status, 'passed')
    self.assertEqual(checks['inspect_only_evidence_contract'].status, 'passed')
    self.assertEqual(checks['fallback_visibility_contract'].status, 'passed')
    self.assertEqual(checks['transport_transcript_promotion'].status, 'passed')
    self.assertEqual(checks['gui_runtime_log_boundary'].status, 'passed')
    self.assertIn(checks['checksum_placeholders'].status, ('warn', 'passed'))


if __name__ == '__main__':
  unittest.main()
