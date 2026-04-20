"""Unit tests for the Calamum Vulcan FS2-03 analyzed snapshot surface."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Tuple
import unittest
import zipfile


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.app.view_models import build_shell_view_model
from calamum_vulcan.domain.package import bind_analyzed_snapshot_verification
from calamum_vulcan.domain.package import import_package_archive
from calamum_vulcan.domain.package import preflight_overrides_from_package_assessment
from calamum_vulcan.domain.package import reverify_analyzed_package_snapshot
from calamum_vulcan.domain.package import seal_analyzed_package_snapshot
from calamum_vulcan.domain.preflight import PreflightGate
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import PreflightSeverity
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.reporting import render_session_evidence_markdown
from calamum_vulcan.fixtures import load_package_manifest_fixture


class PackageSnapshotTests(unittest.TestCase):
  """Prove the FS2-03 analyzed snapshot stays deterministic and blocking."""

  def test_seal_analyzed_snapshot_from_reviewed_archive(self) -> None:
    manifest = load_package_manifest_fixture('matched')

    with TemporaryDirectory() as temp_dir:
      archive_path, digests = _write_package_archive(
        Path(temp_dir),
        manifest=manifest,
      )
      archive_sha256 = _sha256_for_file(archive_path)
      artifact = import_package_archive(
        archive_path,
        Path(temp_dir) / 'stage',
        detected_product_code='SM-G973F',
      )
      snapshot = seal_analyzed_package_snapshot(artifact)
      verification = reverify_analyzed_package_snapshot(snapshot, archive_path)
      bound_assessment = bind_analyzed_snapshot_verification(
        artifact.assessment,
        snapshot,
        verification,
      )

    self.assertEqual(snapshot.package_id, 'calamum-recovery-lab-001')
    self.assertEqual(snapshot.archive_sha256, archive_sha256)
    self.assertEqual(snapshot.payload_digests[0].digest, digests['recovery.img'])
    self.assertTrue(verification.verified)
    self.assertFalse(verification.drift_detected)
    self.assertEqual(bound_assessment.analyzed_snapshot_id, snapshot.snapshot_id)
    self.assertTrue(bound_assessment.analyzed_snapshot_verified)
    self.assertFalse(bound_assessment.analyzed_snapshot_drift_detected)

  def test_reverify_analyzed_snapshot_detects_payload_drift(self) -> None:
    manifest = load_package_manifest_fixture('matched')

    with TemporaryDirectory() as temp_dir:
      temp_root = Path(temp_dir)
      archive_path, _ = _write_package_archive(temp_root, manifest=manifest)
      artifact = import_package_archive(
        archive_path,
        temp_root / 'stage',
        detected_product_code='SM-G973F',
      )
      snapshot = seal_analyzed_package_snapshot(artifact)
      _write_package_archive(
        temp_root,
        manifest=manifest,
        payload_bytes_by_name={'recovery.img': b'mutated-reviewed-payload'},
        archive_name=archive_path.name,
      )
      verification = reverify_analyzed_package_snapshot(snapshot, archive_path)

    self.assertFalse(verification.verified)
    self.assertTrue(verification.drift_detected)
    self.assertTrue(
      any('changed after snapshot review' in issue or 'identity drift' in issue for issue in verification.issues)
    )

  def test_snapshot_drift_blocks_preflight_execution_gate(self) -> None:
    manifest = load_package_manifest_fixture('ready-standard')
    session = build_demo_session('ready')

    with TemporaryDirectory() as temp_dir:
      temp_root = Path(temp_dir)
      archive_path, _ = _write_package_archive(temp_root, manifest=manifest)
      artifact = import_package_archive(
        archive_path,
        temp_root / 'stage',
        detected_product_code=session.product_code,
      )
      snapshot = seal_analyzed_package_snapshot(artifact)
      _write_package_archive(
        temp_root,
        manifest=manifest,
        payload_bytes_by_name={
          'recovery.img': b'drift-recovery',
          'vbmeta.img': b'drift-vbmeta',
        },
        archive_name=archive_path.name,
      )
      verification = reverify_analyzed_package_snapshot(snapshot, archive_path)
      bound_assessment = bind_analyzed_snapshot_verification(
        artifact.assessment,
        snapshot,
        verification,
      )

    report = evaluate_preflight(
      PreflightInput.from_session(
        session,
        **preflight_overrides_from_package_assessment(bound_assessment)
      )
    )

    self.assertEqual(report.gate, PreflightGate.BLOCKED)
    self.assertTrue(
      any(
        signal.rule_id == 'analyzed_snapshot'
        and signal.severity == PreflightSeverity.BLOCK
        for signal in report.signals
      )
    )

  def test_report_and_shell_surface_analyzed_snapshot_identity(self) -> None:
    manifest = load_package_manifest_fixture('ready-standard')
    session = build_demo_session('ready')

    with TemporaryDirectory() as temp_dir:
      archive_path, _ = _write_package_archive(
        Path(temp_dir),
        manifest=manifest,
      )
      from calamum_vulcan.domain.package import assess_package_archive

      assessment = assess_package_archive(
        archive_path,
        detected_product_code=session.product_code,
      )

    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=assessment,
      captured_at_utc='2026-04-19T16:00:00Z',
    )
    markdown = render_session_evidence_markdown(report)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=assessment,
      session_report=report,
    )

    self.assertIsNotNone(report.package.snapshot_id)
    self.assertTrue(report.package.snapshot_verified)
    self.assertFalse(report.package.snapshot_drift_detected)
    self.assertIn('analyzed snapshot', markdown.lower())
    self.assertTrue(
      any('Analyzed snapshot:' in line for line in model.panels[2].detail_lines)
    )
    self.assertTrue(
      any('Snapshot verification:' in line for line in model.panels[4].detail_lines)
    )


def _write_package_archive(
  temp_root: Path,
  manifest: Optional[Mapping[str, object]] = None,
  payload_bytes_by_name: Optional[Mapping[str, bytes]] = None,
  archive_name: str = 'package_under_review.zip',
) -> Tuple[Path, Dict[str, str]]:
  archive_path = temp_root / archive_name
  manifest_payload = dict(manifest or load_package_manifest_fixture('matched'))
  payload_map = {}  # type: Dict[str, bytes]

  if payload_bytes_by_name is not None:
    payload_map.update(dict(payload_bytes_by_name))
  else:
    for entry in manifest_payload.get('checksums', ()):  # type: ignore[assignment]
      if isinstance(entry, dict) and 'file_name' in entry:
        file_name = str(entry['file_name'])
        payload_map[file_name] = ('calamum-review:' + file_name).encode('utf-8')

  digests = {
    file_name: hashlib.sha256(payload).hexdigest()
    for file_name, payload in payload_map.items()
  }

  with zipfile.ZipFile(archive_path, 'w') as archive:
    archive.writestr('package_manifest.json', json.dumps(manifest_payload))
    for file_name, payload in payload_map.items():
      archive.writestr(file_name, payload)

  return archive_path, digests


def _sha256_for_file(file_path: Path) -> str:
  digest = hashlib.sha256()
  with file_path.open('rb') as handle:
    while True:
      chunk = handle.read(1024 * 1024)
      if not chunk:
        break
      digest.update(chunk)
  return digest.hexdigest()


if __name__ == '__main__':
  unittest.main()
