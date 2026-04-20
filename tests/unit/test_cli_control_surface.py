"""CLI tests for the Calamum Vulcan live companion control surface."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import runpy
import sys
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.__main__ import gui_main
from calamum_vulcan.app.__main__ import main
from calamum_vulcan.app.__main__ import _render_codesentinel_status_block


class CliControlSurfaceTests(unittest.TestCase):
  """Prove the live companion CLI stays bounded and inspectable."""

  def test_version_flags_emit_application_version(self) -> None:
    for flag in ('-v', '--version'):
      with self.subTest(flag=flag):
        stream = io.StringIO()

        with redirect_stdout(stream), self.assertRaises(SystemExit) as exit_signal:
          main([flag])

        output = stream.getvalue()
        self.assertEqual(exit_signal.exception.code, 0)
        self.assertIn('Calamum Vulcan 0.1.0', output)

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

  def test_gui_main_surfaces_help_and_version_when_console_missing(self) -> None:
    for flag, expected_title, expected_text in (
      ('-h', 'help', 'usage:'),
      ('--version', 'version', 'Calamum Vulcan 0.1.0'),
    ):
      with self.subTest(flag=flag):
        with tempfile.TemporaryDirectory() as temp_dir:
          log_path = Path(temp_dir) / 'gui_startup.log'
          gui_messages: list[tuple[str, str]] = []

          def _capture_message(title: str, message: str) -> None:
            gui_messages.append((title, message))

          with patch('calamum_vulcan.app.__main__.GUI_STARTUP_LOG_PATH', log_path):
            with patch(
              'calamum_vulcan.app.__main__._show_gui_launch_information',
              side_effect=_capture_message,
            ):
              with patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
                exit_code = gui_main([flag])

          self.assertEqual(exit_code, 0)
          self.assertEqual(len(gui_messages), 1)
          title, message = gui_messages[0]
          self.assertIn(expected_title, title.lower())
          self.assertIn(expected_text, message)
          self.assertTrue(log_path.exists())
          self.assertIn(expected_text, log_path.read_text(encoding='utf-8'))

  def test_gui_main_defaults_to_unhydrated_startup_status(self) -> None:
    stream = io.StringIO()

    with patch('calamum_vulcan.app.__main__.QT_AVAILABLE', True):
      with patch('calamum_vulcan.app.__main__.launch_shell', return_value=0):
        with redirect_stdout(stream):
          exit_code = gui_main([])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('Calamum Vulcan GUI launch status', output)
    self.assertIn('status: confirm', output)
    self.assertIn('decision: gui_launch_ready', output)
    self.assertNotIn('Summary', output)
    self.assertNotIn('Review state', output)

  def test_gui_status_block_uses_blue_brand_prefix_for_interactive_terminal(self) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined]

    with patch.object(sys, 'stdout', stream):
      output = _render_codesentinel_status_block(
        title='Calamum Vulcan GUI launch status',
        status='confirm',
        decision='gui_launch_ready',
        sections=(),
      )

    self.assertIn('\x1b[96mCalamum Vulcan GUI\x1b[0m launch status', output)
    self.assertIn('status: confirm', output)
    self.assertNotIn('Summary', output)

  def test_gui_main_honors_process_argv_when_wrapper_invokes_without_explicit_args(self) -> None:
    stream = io.StringIO()

    with patch.object(sys, 'argv', ['calamum-vulcan-gui', '--version']):
      with redirect_stdout(stream):
        exit_code = gui_main(None)

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    self.assertIn('Calamum Vulcan 0.1.0', output)

  def test_gui_main_detaches_interactive_launch_without_exit_status_echo(self) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined]

    with patch('calamum_vulcan.app.__main__.QT_AVAILABLE', True):
      with patch(
        'calamum_vulcan.app.__main__._spawn_detached_gui_host',
        return_value=True,
      ) as spawn_detached:
        with patch('calamum_vulcan.app.__main__.launch_shell', return_value=0) as launch:
          with patch.object(sys, 'stdout', stream), patch.object(sys, 'stderr', stream):
            exit_code = gui_main([])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    spawn_detached.assert_called_once()
    launch.assert_not_called()
    self.assertIn('decision: gui_launch_ready', output)
    self.assertNotIn('gui_session_closed_cleanly', output)

  def test_gui_main_keeps_duration_bounded_launch_attached_for_validation(self) -> None:
    stream = io.StringIO()
    stream.isatty = lambda: True  # type: ignore[attr-defined]

    with patch('calamum_vulcan.app.__main__.QT_AVAILABLE', True):
      with patch(
        'calamum_vulcan.app.__main__._spawn_detached_gui_host',
        return_value=True,
      ) as spawn_detached:
        with patch('calamum_vulcan.app.__main__.launch_shell', return_value=0) as launch:
          with patch.object(sys, 'stdout', stream), patch.object(sys, 'stderr', stream):
            exit_code = gui_main(['--duration-ms', '1'])

    output = stream.getvalue()
    self.assertEqual(exit_code, 0)
    spawn_detached.assert_not_called()
    launch.assert_called_once()
    self.assertIn('decision: gui_session_closed_cleanly', output)

  def test_launch_shell_module_forwards_process_args_to_gui_main(self) -> None:
    captured_argv = []

    def _capture_gui_main(argv):
      captured_argv.append(tuple(argv))
      return 0

    with patch.object(
      sys,
      'argv',
      ['calamum_vulcan.launch_shell', '--scenario', 'no-device', '--gui-host-process'],
    ):
      with patch('calamum_vulcan.app.__main__.gui_main', side_effect=_capture_gui_main):
        with self.assertRaises(SystemExit) as exit_signal:
          runpy.run_module('calamum_vulcan.launch_shell', run_name='__main__')

    self.assertEqual(exit_signal.exception.code, 0)
    self.assertEqual(
      captured_argv,
      [('--scenario', 'no-device', '--gui-host-process')],
    )

  def test_pyproject_registers_gui_launcher_as_console_script(self) -> None:
    pyproject_path = FINAL_EXAM_ROOT / 'pyproject.toml'
    project = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))['project']

    self.assertEqual(
      project['scripts']['calamum-vulcan-gui'],
      'calamum_vulcan.app.__main__:gui_main',
    )
    self.assertNotIn('gui-scripts', project)


if __name__ == '__main__':
  unittest.main()