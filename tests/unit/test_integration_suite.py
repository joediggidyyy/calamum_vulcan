"""FS-08 sprint-close integration tests for Calamum Vulcan."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.integration import build_sprint_close_bundle
from calamum_vulcan.app.integration import render_sprint_close_bundle_markdown
from calamum_vulcan.app.integration import serialize_sprint_close_bundle_json
from calamum_vulcan.app.integration import write_sprint_close_bundle


class IntegrationSuiteTests(unittest.TestCase):
  """Prove the FS-08 sprint-close bundle stays empirical and bounded."""

  def test_sprint_close_bundle_covers_expected_scenarios(self) -> None:
    bundle = build_sprint_close_bundle(captured_at_utc='2026-04-18T21:10:00Z')
    scenario_ids = tuple(scenario.scenario_id for scenario in bundle.scenarios)

    self.assertEqual(bundle.release_version, '0.1.0')
    self.assertEqual(bundle.suite_name, 'sprint-close')
    self.assertEqual(
      scenario_ids,
      (
        'no-device-review',
        'happy-path-review',
        'blocked-preflight-review',
        'incompatible-package-review',
        'transport-failure-review',
        'resume-handoff-review',
      ),
    )
    self.assertEqual(len(bundle.proof_points), 5)
    self.assertTrue(all(point.passed for point in bundle.proof_points))

  def test_sprint_close_bundle_captures_happy_and_negative_paths(self) -> None:
    bundle = build_sprint_close_bundle(captured_at_utc='2026-04-18T21:15:00Z')
    scenario_map = {scenario.scenario_id: scenario for scenario in bundle.scenarios}

    self.assertEqual(scenario_map['happy-path-review'].transport_state, 'completed')
    self.assertEqual(scenario_map['happy-path-review'].outcome, 'completed')
    self.assertEqual(scenario_map['no-device-review'].gate_label, 'Gate Blocked')
    self.assertFalse(scenario_map['no-device-review'].export_ready)
    self.assertEqual(
      scenario_map['incompatible-package-review'].gate_label,
      'Gate Blocked',
    )
    self.assertEqual(scenario_map['transport-failure-review'].outcome, 'failed')

  def test_markdown_render_includes_summary_and_debt(self) -> None:
    bundle = build_sprint_close_bundle(captured_at_utc='2026-04-18T21:20:00Z')
    markdown = render_sprint_close_bundle_markdown(bundle)

    self.assertIn('Calamum Vulcan FS-08 sprint-close bundle', markdown)
    self.assertIn('Sprint 0.1.0 closes with 5/5 sprint-close proof points satisfied', markdown)
    self.assertIn('Incompatible package review', markdown)
    self.assertIn('Carry-forward debt into 0.2.0', markdown)

  def test_writer_persists_json_bundle_to_disk(self) -> None:
    bundle = build_sprint_close_bundle(captured_at_utc='2026-04-18T21:25:00Z')

    with TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'fs08_bundle.json'
      written_path = write_sprint_close_bundle(bundle, output_path)
      payload = json.loads(written_path.read_text(encoding='utf-8'))

    self.assertEqual(written_path, output_path)
    self.assertEqual(payload['suite_name'], 'sprint-close')
    self.assertEqual(payload['release_version'], '0.1.0')
    self.assertEqual(len(payload['scenarios']), 6)


if __name__ == '__main__':
  unittest.main()