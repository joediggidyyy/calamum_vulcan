"""Unit tests for the PIT transport diagnostic runner."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.heimdall import HeimdallRuntimeProbe
from scripts import run_pit_transport_diagnostic as pit_transport_diagnostic


class PitTransportDiagnosticTests(unittest.TestCase):
  """Keep the PIT transport diagnostic broad, honest, and actionable."""

  def test_summary_highlights_gui_disconnect_heuristic_and_download_fallback(self) -> None:
    runtime_probe = HeimdallRuntimeProbe(
      executable_name='heimdall',
      resolved_path='C:/repo/calamum_vulcan/assets/bin/windows/heimdall/heimdall.exe',
      resolution_source='packaged-asset',
      packaged_candidate='C:/repo/calamum_vulcan/assets/bin/windows/heimdall/heimdall.exe',
      packaged_candidate_present=True,
      smoke_test_exit_code=0,
      smoke_test_summary='Heimdall runtime probe executed successfully.',
      available=True,
    )

    summary = pit_transport_diagnostic.build_pit_transport_summary(
      runtime_probe,
      Path('C:/temp/pit_transport_diagnostic/20260424T010203Z'),
      run_live_commands=False,
    )

    scenario_map = {
      case['scenario_id']: case for case in summary['fixture_matrix']
    }
    self.assertTrue(
      scenario_map['integrated_print_interface_loss']['gui_disconnect_detected']
    )
    self.assertEqual(
      scenario_map['integrated_print_interface_loss']['fallback_recommendation'],
      'current_gui_would_skip_download_pit_fallback',
    )
    self.assertEqual(
      scenario_map['integrated_print_interface_loss']['classification']['family'],
      'interface_loss_or_driver_rebind',
    )
    self.assertEqual(
      scenario_map['integrated_print_malformed']['fallback_recommendation'],
      'attempt_download_pit_fallback',
    )
    self.assertEqual(
      summary['live_known_issue_selector']['family'],
      'insufficient_live_evidence',
    )
    self.assertIn(
      'Current GUI PIT handling suppresses download-pit fallback whenever the failure summary is classified as interface loss.',
      summary['findings'],
    )

  def test_markdown_reports_skipped_live_suite_and_findings(self) -> None:
    runtime_probe = HeimdallRuntimeProbe(
      executable_name='heimdall',
      resolved_path='C:/repo/calamum_vulcan/assets/bin/windows/heimdall/heimdall.exe',
      resolution_source='packaged-asset',
      packaged_candidate='C:/repo/calamum_vulcan/assets/bin/windows/heimdall/heimdall.exe',
      packaged_candidate_present=True,
      smoke_test_exit_code=0,
      smoke_test_summary='Heimdall runtime probe executed successfully.',
      available=True,
    )

    summary = pit_transport_diagnostic.build_pit_transport_summary(
      runtime_probe,
      Path('C:/temp/pit_transport_diagnostic/20260424T010203Z'),
      run_live_commands=False,
    )
    markdown = pit_transport_diagnostic.render_pit_transport_markdown(summary)

    self.assertIn('# PIT transport diagnostic', markdown)
    self.assertIn('Fixture investigation matrix', markdown)
    self.assertIn('Known-issue selector', markdown)
    self.assertIn('Live PIT command suite', markdown)
    self.assertIn('`skipped`', markdown)
    self.assertIn('Current GUI PIT handling suppresses download-pit fallback', markdown)


if __name__ == '__main__':
  unittest.main()
