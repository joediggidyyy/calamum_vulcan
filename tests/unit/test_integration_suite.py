"""Integrated closeout-bundle tests for Calamum Vulcan."""

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
from calamum_vulcan.app.integration import build_orchestration_close_bundle
from calamum_vulcan.app.integration import build_read_side_close_bundle
from calamum_vulcan.app.integration import build_safe_path_close_bundle
from calamum_vulcan.app.integration import render_sprint_close_bundle_markdown
from calamum_vulcan.app.integration import serialize_sprint_close_bundle_json
from calamum_vulcan.app.integration import write_sprint_close_bundle


class IntegrationSuiteTests(unittest.TestCase):
  """Prove integrated closeout bundles stay empirical and bounded."""

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

  def test_orchestration_close_bundle_promotes_bounded_runtime_transcripts(self) -> None:
    bundle = build_orchestration_close_bundle(
      captured_at_utc='2026-04-19T01:20:00Z'
    )
    scenario_map = {scenario.scenario_id: scenario for scenario in bundle.scenarios}

    self.assertEqual(bundle.release_version, '0.2.0')
    self.assertEqual(bundle.suite_name, 'orchestration-close')
    self.assertTrue(all(point.passed for point in bundle.proof_points))
    self.assertTrue(scenario_map['happy-path-review'].transcript_preserved)
    self.assertTrue(scenario_map['transport-failure-review'].transcript_preserved)
    self.assertTrue(scenario_map['resume-handoff-review'].transcript_preserved)
    self.assertFalse(scenario_map['blocked-preflight-review'].transcript_preserved)

  def test_orchestration_close_markdown_mentions_transcript_promotion(self) -> None:
    bundle = build_orchestration_close_bundle(
      captured_at_utc='2026-04-19T01:25:00Z'
    )
    markdown = render_sprint_close_bundle_markdown(bundle)

    self.assertIn('Calamum Vulcan FS2-07 orchestration-close bundle', markdown)
    self.assertIn('Sprint 0.2.0 closes with 5/5 orchestration-close proof points satisfied', markdown)
    self.assertIn('summary_only', markdown)
    self.assertIn('preserved', markdown)

  def test_read_side_close_bundle_proves_native_and_fallback_read_side_matrix(self) -> None:
    bundle = build_read_side_close_bundle(
      captured_at_utc='2026-04-20T23:10:00Z'
    )
    scenario_map = {scenario.scenario_id: scenario for scenario in bundle.scenarios}

    self.assertEqual(bundle.release_version, '0.3.0')
    self.assertEqual(bundle.suite_name, 'read-side-close')
    self.assertEqual(
      tuple(scenario_map.keys()),
      (
        'inspect-only-ready-review',
        'native-adb-package-review',
        'pit-mismatch-review',
        'fastboot-fallback-review',
        'fallback-exhausted-review',
      ),
    )
    self.assertTrue(all(point.passed for point in bundle.proof_points))
    self.assertEqual(scenario_map['inspect-only-ready-review'].inspection_posture, 'ready')
    self.assertEqual(scenario_map['native-adb-package-review'].live_source, 'adb')
    self.assertEqual(
      scenario_map['native-adb-package-review'].pit_package_alignment,
      'matched',
    )
    self.assertEqual(scenario_map['pit-mismatch-review'].pit_package_alignment, 'mismatched')
    self.assertEqual(scenario_map['fastboot-fallback-review'].live_source, 'fastboot')
    self.assertEqual(
      scenario_map['fallback-exhausted-review'].inspection_posture,
      'failed',
    )

  def test_read_side_close_markdown_mentions_fallback_visibility_and_0_4_0_debt(self) -> None:
    bundle = build_read_side_close_bundle(
      captured_at_utc='2026-04-20T23:15:00Z'
    )
    markdown = render_sprint_close_bundle_markdown(bundle)

    self.assertIn('Calamum Vulcan FS3-07 read-side-close bundle', markdown)
    self.assertIn('Sprint 0.3.0 closes with 5/5 read-side-close proof points satisfied', markdown)
    self.assertIn('Fastboot fallback review', markdown)
    self.assertIn('inspection posture:', markdown)
    self.assertIn('fallback=`engaged`', markdown)
    self.assertIn('Carry-forward debt into 0.4.0', markdown)

  def test_safe_path_close_bundle_proves_truthful_safe_path_progression(self) -> None:
    bundle = build_safe_path_close_bundle(
      captured_at_utc='2026-04-21T23:10:00Z'
    )
    scenario_map = {scenario.scenario_id: scenario for scenario in bundle.scenarios}

    self.assertEqual(bundle.release_version, '0.4.0')
    self.assertEqual(bundle.suite_name, 'safe-path-close')
    self.assertEqual(
      tuple(scenario_map.keys()),
      (
        'read-pit-required-review',
        'load-package-required-review',
        'safe-path-ready-review',
        'safe-path-runtime-complete',
        'pit-mismatch-block-review',
        'fastboot-fallback-boundary-review',
      ),
    )
    self.assertTrue(all(point.passed for point in bundle.proof_points))
    self.assertEqual(scenario_map['read-pit-required-review'].gate_label, 'Gate Blocked')
    self.assertEqual(scenario_map['safe-path-ready-review'].gate_label, 'Gate Ready')
    self.assertEqual(scenario_map['safe-path-ready-review'].live_source, 'usb')
    self.assertEqual(
      dict(scenario_map['safe-path-ready-review'].action_states)['Execute flash plan'],
      'next',
    )
    self.assertEqual(
      dict(scenario_map['safe-path-runtime-complete'].action_states)['Export evidence'],
      'next',
    )
    self.assertEqual(scenario_map['pit-mismatch-block-review'].pit_package_alignment, 'mismatched')
    self.assertEqual(scenario_map['fastboot-fallback-boundary-review'].live_source, 'fastboot')

  def test_safe_path_close_markdown_mentions_truthful_deck_and_sprint5_boundary(self) -> None:
    bundle = build_safe_path_close_bundle(
      captured_at_utc='2026-04-21T23:15:00Z'
    )
    markdown = render_sprint_close_bundle_markdown(bundle)

    self.assertIn('Calamum Vulcan FS4-07 safe-path-close bundle', markdown)
    self.assertIn('Sprint 0.4.0 closes with 5/5 safe-path-close proof points satisfied', markdown)
    self.assertIn('Read PIT required review', markdown)
    self.assertIn('Execute flash plan=next', markdown)
    self.assertIn('Carry-forward debt into 0.5.0', markdown)


if __name__ == '__main__':
  unittest.main()