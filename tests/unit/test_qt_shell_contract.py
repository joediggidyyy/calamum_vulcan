"""Qt-shell contract tests for Calamum Vulcan FS-03."""

from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.app.qt_compat import QT_AVAILABLE
from calamum_vulcan.app.view_models import PANEL_TITLES
from calamum_vulcan.app.view_models import build_shell_view_model

if QT_AVAILABLE:
  os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
  from calamum_vulcan.app.qt_compat import QtWidgets
  from calamum_vulcan.app.qt_shell import ShellWindow
  from calamum_vulcan.app.qt_shell import BrandMark
  from calamum_vulcan.app.qt_shell import get_or_create_application


@unittest.skipUnless(QT_AVAILABLE, 'Qt runtime not installed in test environment.')
class QtShellContractTests(unittest.TestCase):
  """Verify the Qt shell can instantiate from the view-model contract."""

  @classmethod
  def setUpClass(cls) -> None:
    cls.application = get_or_create_application()

  def test_window_builds_expected_panel_titles(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )
    window = ShellWindow(model)
    brand_mark = window.findChild(BrandMark)
    self.assertIsNotNone(brand_mark)
    label_text = tuple(widget.text() for widget in brand_mark.findChildren(QtWidgets.QLabel))

    self.assertEqual(window.panel_titles(), PANEL_TITLES)
    self.assertIn('Calamum Vulcan', window.windowTitle())
    self.assertIn('Execute flash plan', window.action_labels())
    self.assertFalse(window.windowIcon().isNull())
    self.assertGreaterEqual(window.minimumWidth(), 1080)
    self.assertGreaterEqual(window.minimumHeight(), 720)
    self.assertNotIn('CALAMUM SYSTEMS', label_text)
    self.assertFalse(any('Samsung' in text for text in label_text))
    self.assertIn('VULCAN', label_text)
    window.close()

  def test_window_supports_runtime_zoom_controls(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )
    window = ShellWindow(model)

    self.assertEqual(window.zoom_percent(), 90)
    window.increase_zoom()
    self.assertEqual(window.zoom_percent(), 95)
    window.decrease_zoom()
    self.assertEqual(window.zoom_percent(), 90)
    for _ in range(20):
      window.decrease_zoom()
    self.assertEqual(window.zoom_percent(), 55)
    window.reset_zoom()
    self.assertEqual(window.zoom_percent(), 90)
    window.close()

  def test_window_exposes_live_companion_controls(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )
    window = ShellWindow(model)

    adb_combo = window.findChild(QtWidgets.QComboBox, 'live-adb-mode')
    fastboot_combo = window.findChild(QtWidgets.QComboBox, 'live-fastboot-mode')
    status_label = window.findChild(QtWidgets.QLabel, 'live-companion-status')

    self.assertIsNotNone(adb_combo)
    self.assertIsNotNone(fastboot_combo)
    self.assertIsNotNone(status_label)
    self.assertIn('download', window.live_adb_reboot_targets())
    self.assertIn('bootloader', window.live_fastboot_reboot_targets())
    self.assertIn('Awaiting live ADB probe', window.live_status_text())
    window.close()


if __name__ == '__main__':
  unittest.main()