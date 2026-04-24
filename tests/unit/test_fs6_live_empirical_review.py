"""Unit tests for the Sprint 0.6.0 live empirical preflight runner."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.heimdall import HeimdallRuntimeProbe
from calamum_vulcan.usb.scanner import USBProbeResult
from scripts import run_fs6_live_empirical_review as live_empirical_review


class LiveEmpiricalReviewTests(unittest.TestCase):
  """Prove the manual empirical preflight runner stays honest and actionable."""

  def test_summary_is_ready_when_runtime_and_usb_backend_are_ready(self) -> None:
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
    usb_probe = USBProbeResult(
      state='cleared',
      summary='Native USB scan did not detect a Samsung download-mode device.',
      notes=('Native USB backend resolved from bundled libusb.',),
    )

    summary = live_empirical_review.build_manual_empirical_summary(
      runtime_probe,
      usb_probe,
      Path('C:/temp/fs6_live_empirical/manual_review/20260424T010203Z'),
      'C:/Python314/python.exe',
    )

    self.assertEqual(summary['status'], 'ready')
    self.assertIn('-m', summary['gui_launch_command'])
    self.assertIn('calamum_vulcan.app', summary['gui_launch_command'])
    markdown = live_empirical_review.render_manual_empirical_markdown(summary)
    self.assertIn('`ready`', markdown)
    self.assertIn('Manual launch command', markdown)

  def test_summary_blocks_when_packaged_runtime_probe_is_not_available(self) -> None:
    runtime_probe = HeimdallRuntimeProbe(
      executable_name='heimdall',
      resolved_path='C:/repo/calamum_vulcan/assets/bin/windows/heimdall/heimdall.exe',
      resolution_source='packaged-asset',
      packaged_candidate='C:/repo/calamum_vulcan/assets/bin/windows/heimdall/heimdall.exe',
      packaged_candidate_present=True,
      smoke_test_exit_code=-1073741515,
      smoke_test_summary=(
        'Packaged Heimdall runtime resolved, but Windows could not load one or '
        'more runtime DLL dependencies.'
      ),
      stderr_lines=(
        'Packaged Heimdall runtime could not start because Windows reported a missing DLL dependency (0xC0000135).',
      ),
      available=False,
    )
    usb_probe = USBProbeResult(
      state='cleared',
      summary='Native USB scan did not detect a Samsung download-mode device.',
    )

    summary = live_empirical_review.build_manual_empirical_summary(
      runtime_probe,
      usb_probe,
      Path('C:/temp/fs6_live_empirical/manual_review/20260424T010203Z'),
      'C:/Python314/python.exe',
    )

    self.assertEqual(summary['status'], 'blocked')
    self.assertTrue(
      any('missing DLL dependency' in note for note in summary['notes'])
    )
    markdown = live_empirical_review.render_manual_empirical_markdown(summary)
    self.assertIn('`blocked`', markdown)
    self.assertIn('Resolve the blocking runtime notes', markdown)


if __name__ == '__main__':
  unittest.main()
