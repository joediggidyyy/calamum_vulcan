"""CLI tests for the Calamum Vulcan live companion control surface."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.__main__ import gui_main
from calamum_vulcan.app.__main__ import main


class CliControlSurfaceTests(unittest.TestCase):
  """Prove the live companion CLI stays bounded and inspectable."""

  def test_describe_only_adb_download_reboot_surfaces_vendor_specific_note(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(
        [
          '--adb-reboot',
          'download',
          '--device-serial',
          'R58N12345AB',
          '--describe-only',
        ]
      )

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('adb -s R58N12345AB reboot download', output)
    self.assertIn('vendor_specific="yes"', output)
    self.assertIn('vendor-specific', output)

  def test_describe_only_adb_detect_surfaces_live_command_plan(self) -> None:
    stream = io.StringIO()

    with redirect_stdout(stream):
      exit_code = main(['--adb-detect', '--describe-only'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('adb devices -l', output)
    self.assertIn('detect_adb_devices', output)

  def test_gui_main_survives_missing_console_streams(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      log_path = Path(temp_dir) / 'gui_startup.log'
      with patch('calamum_vulcan.app.__main__.GUI_STARTUP_LOG_PATH', log_path):
        with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
          exit_code = gui_main(['--scenario', 'ready', '--describe-only'])

      self.assertEqual(exit_code, 0)
      self.assertTrue(log_path.exists())
      self.assertIn('phase="Ready to Execute"', log_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
  unittest.main()