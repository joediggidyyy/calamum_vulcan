"""Unit tests for the Calamum Vulcan FS2-02 package archive importer."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.__main__ import main
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.app.view_models import build_shell_view_model
from calamum_vulcan.domain.package import PackageArchiveImportError
from calamum_vulcan.domain.package import assess_package_archive
from calamum_vulcan.domain.package import import_package_archive
from calamum_vulcan.domain.package import preflight_overrides_from_package_assessment
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.fixtures import load_package_manifest_fixture


class PackageArchiveImporterTests(unittest.TestCase):
  """Prove the FS2-02 real package importer stays bounded and useful."""

  def test_assess_package_archive_computes_verified_sha256_digests(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path, expected_digest = _write_package_archive(Path(temp_dir))
      assessment = assess_package_archive(
        archive_path,
        detected_product_code='SM-G973F',
      )

    self.assertTrue(assessment.contract_complete)
    self.assertEqual(assessment.source_kind, 'archive')
    self.assertTrue(assessment.checksum_coverage_present)
    self.assertTrue(assessment.checksum_verification_complete)
    self.assertEqual(assessment.verified_checksum_count, 1)
    self.assertEqual(assessment.checksums[0].resolved_value, expected_digest)
    self.assertTrue(assessment.checksums[0].verified)
    self.assertIsNotNone(assessment.analyzed_snapshot_id)
    self.assertTrue(assessment.analyzed_snapshot_verified)
    self.assertFalse(assessment.analyzed_snapshot_drift_detected)
    self.assertTrue(assessment.matches_detected_product_code)
    self.assertTrue(
      preflight_overrides_from_package_assessment(assessment)['checksums_present']
    )

  def test_assess_package_archive_marks_digest_mismatch_as_untrusted(self) -> None:
    manifest = load_package_manifest_fixture('matched')
    manifest['checksums'][0]['value'] = '0' * 64

    with TemporaryDirectory() as temp_dir:
      archive_path, _ = _write_package_archive(Path(temp_dir), manifest=manifest)
      assessment = assess_package_archive(
        archive_path,
        detected_product_code='SM-G973F',
      )

    self.assertFalse(assessment.contract_complete)
    self.assertFalse(assessment.checksum_verification_complete)
    self.assertEqual(assessment.verified_checksum_count, 0)
    self.assertTrue(
      any('Checksum mismatch for recovery.img' in issue for issue in assessment.contract_issues)
    )

  def test_import_package_archive_rejects_casefold_member_collisions(self) -> None:
    manifest = load_package_manifest_fixture('matched')

    with TemporaryDirectory() as temp_dir:
      archive_path = Path(temp_dir) / 'collision_package.zip'
      with zipfile.ZipFile(archive_path, 'w') as archive:
        archive.writestr('package_manifest.json', json.dumps(manifest))
        archive.writestr('recovery.img', b'first')
        archive.writestr('RECOVERY.IMG', b'second')

      with self.assertRaises(PackageArchiveImportError):
        import_package_archive(archive_path, Path(temp_dir) / 'stage')

  def test_archive_assessment_surfaces_verified_digests_in_shell_and_report(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path, _ = _write_package_archive(Path(temp_dir))
      assessment = assess_package_archive(
        archive_path,
        detected_product_code='SM-G973F',
      )

    session = build_demo_session('ready')
    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=assessment,
      captured_at_utc='2026-04-19T14:00:00Z',
    )
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=assessment,
      session_report=report,
    )

    self.assertTrue(
      any(
        'Checksum digests verified: 1/1' in line
        for line in model.panels[2].detail_lines
      )
    )
    self.assertTrue(
      any('Digest preview:' in line for line in model.panels[2].detail_lines)
    )
    self.assertEqual(report.package.source_kind, 'archive')
    self.assertTrue(report.package.checksum_verification_complete)
    self.assertEqual(report.package.verified_checksum_count, 1)
    self.assertIsNotNone(report.package.snapshot_id)
    self.assertTrue(report.package.snapshot_verified)
    self.assertTrue(
      any('[PACKAGE-CTX]' in line and 'source=archive' in line for line in report.log_lines)
    )

  def test_cli_describe_only_accepts_real_package_archive(self) -> None:
    with TemporaryDirectory() as temp_dir:
      archive_path, _ = _write_package_archive(Path(temp_dir))
      stream = io.StringIO()
      with redirect_stdout(stream):
        exit_code = main(
          [
            '--scenario',
            'ready',
            '--package-archive',
            str(archive_path),
            '--describe-only',
            '--export-evidence',
            '--evidence-format',
            'json',
            '--captured-at-utc',
            '2026-04-19T14:05:00Z',
          ]
        )

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('"source_kind": "archive"', output)
    self.assertIn('"checksum_verification_complete": true', output)
    self.assertIn('"verified_checksum_count": 1', output)
    self.assertIn('"snapshot_verified": true', output)


def _write_package_archive(
  temp_root: Path,
  manifest: dict | None = None,
) -> tuple[Path, str]:
  payload_bytes = b'calamum-vulcan-recovery-image'
  digest = hashlib.sha256(payload_bytes).hexdigest()
  archive_path = temp_root / 'matched_recovery_package.zip'
  manifest_payload = manifest or load_package_manifest_fixture('matched')

  with zipfile.ZipFile(archive_path, 'w') as archive:
    archive.writestr('package_manifest.json', json.dumps(manifest_payload))
    archive.writestr('recovery.img', payload_bytes)

  return archive_path, digest


if __name__ == '__main__':
  unittest.main()
