"""Unit tests for Calamum Vulcan FS2-06 Android-image heuristics."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.domain.package import assess_android_image_heuristics
from calamum_vulcan.fixtures import load_package_manifest_fixture


class ImageHeuristicsTests(unittest.TestCase):
  """Prove the first warning-tier suspiciousness heuristics stay deterministic."""

  def test_manifest_declared_traits_surface_expected_indicator_ids(self) -> None:
    manifest = load_package_manifest_fixture('suspicious-review')

    findings = assess_android_image_heuristics(manifest)
    indicator_ids = {finding.indicator_id for finding in findings}

    self.assertEqual(
      indicator_ids,
      {
        'test_keys',
        'magisk',
        'su_binary',
        'insecure_properties',
        'avb_disabled',
        'dm_verity_disabled',
        'selinux_permissive',
      },
    )

  def test_payload_scan_detects_text_backed_warning_markers(self) -> None:
    manifest = load_package_manifest_fixture('ready-standard')

    with TemporaryDirectory() as temp_dir:
      payload_root = Path(temp_dir)
      payload_file = payload_root / 'system.prop'
      payload_file.write_text(
        '\n'.join(
          (
            'ro.secure=0',
            'ro.debuggable=1',
            'androidboot.selinux=permissive',
            'init.magisk.rc',
            '/system/xbin/su',
            'disable-verification',
            'disable-verity',
            'test-keys',
          )
        ),
        encoding='utf-8',
      )

      findings = assess_android_image_heuristics(
        manifest,
        staged_root=payload_root,
        payload_members=('system.prop',),
      )

    indicator_ids = {finding.indicator_id for finding in findings}
    self.assertIn('test_keys', indicator_ids)
    self.assertIn('magisk', indicator_ids)
    self.assertIn('su_binary', indicator_ids)
    self.assertIn('insecure_properties', indicator_ids)
    self.assertIn('avb_disabled', indicator_ids)
    self.assertIn('dm_verity_disabled', indicator_ids)
    self.assertIn('selinux_permissive', indicator_ids)


if __name__ == '__main__':
  unittest.main()
