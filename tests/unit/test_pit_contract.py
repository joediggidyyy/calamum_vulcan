"""Unit tests for the Calamum Vulcan FS3-04 PIT domain."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.heimdall import build_download_pit_command_plan
from calamum_vulcan.adapters.heimdall import build_print_pit_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.domain.pit import PitInspectionState
from calamum_vulcan.domain.pit import PitPackageAlignment
from calamum_vulcan.domain.pit import build_pit_inspection
from calamum_vulcan.fixtures import load_heimdall_pit_fixture


class PitContractTests(unittest.TestCase):
  """Prove the repo-owned PIT parser and inspection surface for FS3-04."""

  def test_print_pit_trace_builds_captured_inspection_with_package_match(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    trace = normalize_heimdall_result(
      build_print_pit_command_plan(),
      load_heimdall_pit_fixture('pit-print-ready-g991u'),
    )

    inspection = build_pit_inspection(
      trace,
      detected_product_code=session.product_code,
      package_assessment=package_assessment,
    )

    self.assertEqual(inspection.state, PitInspectionState.CAPTURED)
    self.assertEqual(inspection.entry_count, 3)
    self.assertEqual(inspection.partition_names, ('BOOT', 'RECOVERY', 'VBMETA'))
    self.assertEqual(inspection.package_alignment, PitPackageAlignment.MATCHED)
    self.assertEqual(inspection.observed_pit_fingerprint, 'PIT-G991U-READY-001')
    self.assertEqual(inspection.marketing_name, 'Galaxy S21')

  def test_print_pit_trace_detects_package_fingerprint_mismatch(self) -> None:
    session = build_demo_session('blocked')
    package_assessment = build_demo_package_assessment('blocked', session=session)
    trace = normalize_heimdall_result(
      build_print_pit_command_plan(),
      load_heimdall_pit_fixture('pit-print-ready-g991u'),
    )

    inspection = build_pit_inspection(
      trace,
      detected_product_code=session.product_code,
      package_assessment=package_assessment,
    )

    self.assertEqual(inspection.state, PitInspectionState.CAPTURED)
    self.assertEqual(inspection.package_alignment, PitPackageAlignment.MISMATCHED)
    self.assertIn('does not match the reviewed package fingerprint', inspection.summary)

  def test_download_pit_trace_records_metadata_only_partial_state(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    trace = normalize_heimdall_result(
      build_download_pit_command_plan(output_path='artifacts/device-ready.pit'),
      load_heimdall_pit_fixture('pit-download-ready-g991u'),
    )

    inspection = build_pit_inspection(
      trace,
      detected_product_code=session.product_code,
      package_assessment=package_assessment,
    )

    self.assertEqual(inspection.state, PitInspectionState.PARTIAL)
    self.assertEqual(inspection.download_path, 'artifacts/device-ready.pit')
    self.assertEqual(inspection.entry_count, 3)
    self.assertEqual(inspection.partition_names, ())
    self.assertTrue(
      any('Detailed partition inspection currently requires print-pit' in line for line in inspection.operator_guidance)
    )

  def test_malformed_print_pit_trace_is_flagged(self) -> None:
    trace = normalize_heimdall_result(
      build_print_pit_command_plan(),
      load_heimdall_pit_fixture('pit-print-malformed'),
    )

    inspection = build_pit_inspection(trace)

    self.assertEqual(inspection.state, PitInspectionState.MALFORMED)
    self.assertTrue(inspection.notes)
    self.assertIn('did not satisfy the repo-owned parser contract', inspection.summary)


if __name__ == '__main__':
  unittest.main()
