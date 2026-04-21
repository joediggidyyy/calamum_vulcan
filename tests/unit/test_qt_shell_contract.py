"""Qt-shell contract tests for Calamum Vulcan FS-03."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path
import time
import unittest
from unittest import mock


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import scenario_label
from calamum_vulcan.app.qt_compat import QT_AVAILABLE
from calamum_vulcan.app.view_models import PANEL_TITLES
from calamum_vulcan.app.view_models import build_shell_view_model

if QT_AVAILABLE:
  from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
  from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
  from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
  from calamum_vulcan.adapters.adb_fastboot import build_adb_reboot_command_plan
  from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
  from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
  from calamum_vulcan.adapters.adb_fastboot import build_fastboot_detect_command_plan
  from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
  from calamum_vulcan.adapters.heimdall import build_print_pit_command_plan
  from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
  os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
  import calamum_vulcan.app.qt_shell as qt_shell_module
  from calamum_vulcan.app.qt_compat import QtWidgets
  from calamum_vulcan.app.qt_shell import ShellWindow
  from calamum_vulcan.app.qt_shell import BrandMark
  from calamum_vulcan.app.qt_shell import DashboardPanel
  from calamum_vulcan.app.qt_shell import DetailRow
  from calamum_vulcan.app.qt_shell import MetricBlock
  from calamum_vulcan.app.qt_shell import get_or_create_application
  from calamum_vulcan.fixtures import load_heimdall_pit_fixture


def _ready_adb_detection_trace():
  command_plan = build_adb_detect_command_plan()
  process_result = AndroidToolsProcessResult(
    fixture_name='adb-ready',
    operation=AndroidToolsOperation.ADB_DEVICES,
    backend=AndroidToolsBackend.ADB,
    exit_code=0,
    stdout_lines=(
      'List of devices attached',
      'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
    ),
  )
  return normalize_android_tools_result(command_plan, process_result)


def _no_device_adb_detection_trace():
  command_plan = build_adb_detect_command_plan()
  process_result = AndroidToolsProcessResult(
    fixture_name='adb-none',
    operation=AndroidToolsOperation.ADB_DEVICES,
    backend=AndroidToolsBackend.ADB,
    exit_code=0,
    stdout_lines=('List of devices attached',),
  )
  return normalize_android_tools_result(command_plan, process_result)


def _ready_adb_info_trace():
  command_plan = build_adb_device_info_command_plan(device_serial='R58N12345AB')
  process_result = AndroidToolsProcessResult(
    fixture_name='adb-info-ready',
    operation=AndroidToolsOperation.ADB_GETPROP,
    backend=AndroidToolsBackend.ADB,
    exit_code=0,
    stdout_lines=(
      '[ro.product.manufacturer]: [samsung]',
      '[ro.product.brand]: [samsung]',
      '[ro.build.version.release]: [14]',
      '[ro.build.version.security_patch]: [2026-04-05]',
      '[ro.bootloader]: [G991USQS9HYD1]',
    ),
  )
  return normalize_android_tools_result(command_plan, process_result)


def _ready_fastboot_detection_trace():
  command_plan = build_fastboot_detect_command_plan()
  process_result = AndroidToolsProcessResult(
    fixture_name='fastboot-ready',
    operation=AndroidToolsOperation.FASTBOOT_DEVICES,
    backend=AndroidToolsBackend.FASTBOOT,
    exit_code=0,
    stdout_lines=('FASTBOOT123\tfastboot',),
  )
  return normalize_android_tools_result(command_plan, process_result)


def _successful_adb_reboot_trace(target: str = 'system'):
  command_plan = build_adb_reboot_command_plan(target, device_serial='R58N12345AB')
  process_result = AndroidToolsProcessResult(
    fixture_name='adb-reboot-ok',
    operation=AndroidToolsOperation.ADB_REBOOT,
    backend=AndroidToolsBackend.ADB,
    exit_code=0,
  )
  return normalize_android_tools_result(command_plan, process_result)


def _ready_print_pit_trace():
  return normalize_heimdall_result(
    build_print_pit_command_plan(),
    load_heimdall_pit_fixture('pit-print-ready-g991u'),
  )


@unittest.skipUnless(QT_AVAILABLE, 'Qt runtime not installed in test environment.')
class QtShellContractTests(unittest.TestCase):
  """Verify the Qt shell can instantiate from the view-model contract."""

  @classmethod
  def setUpClass(cls) -> None:
    cls.application = get_or_create_application()

  def _process_events_until(self, predicate, timeout_seconds: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
      self.application.processEvents()
      if predicate():
        return True
      time.sleep(0.01)
    self.application.processEvents()
    return predicate()

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

    detect_button = window.findChild(
      QtWidgets.QPushButton,
      'control-action-detect-device',
    )
    adb_combo = window.findChild(QtWidgets.QComboBox, 'live-adb-mode')
    fastboot_combo = window.findChild(QtWidgets.QComboBox, 'live-fastboot-mode')
    status_label = window.findChild(QtWidgets.QLabel, 'live-companion-status')
    load_package_button = window.findChild(
      QtWidgets.QPushButton,
      'control-action-load-package',
    )

    self.assertIsNotNone(detect_button)
    self.assertIsNotNone(adb_combo)
    self.assertIsNotNone(fastboot_combo)
    self.assertIsNotNone(status_label)
    self.assertIsNotNone(load_package_button)
    self.assertIsNone(window.findChild(QtWidgets.QPushButton, 'live-adb-detect'))
    self.assertIsNone(window.findChild(QtWidgets.QPushButton, 'live-fastboot-detect'))
    self.assertIn('download', window.live_adb_reboot_targets())
    self.assertIn('bootloader', window.live_fastboot_reboot_targets())
    self.assertEqual(detect_button.toolTip(), '')
    self.assertEqual(load_package_button.toolTip(), '')
    self.assertIn('Standby. No live device probe has run since startup.', window.live_status_text())
    window.close()

  def test_window_uses_hidden_independent_scroll_regions(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )
    window = ShellWindow(model)
    window.resize(960, 420)
    window.show()

    main_scroll = window.findChild(QtWidgets.QScrollArea, 'main-pane-scroll')
    control_scroll = window.findChild(QtWidgets.QScrollArea, 'control-deck-scroll')

    self.assertIsNotNone(main_scroll)
    self.assertIsNotNone(control_scroll)
    self.assertEqual(
      main_scroll.verticalScrollBarPolicy(),
      qt_shell_module.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
    )
    self.assertEqual(
      control_scroll.verticalScrollBarPolicy(),
      qt_shell_module.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
    )
    self.assertTrue(
      self._process_events_until(
        lambda: (
          main_scroll.verticalScrollBar().maximum() > 0
          and control_scroll.verticalScrollBar().maximum() > 0
        ),
        timeout_seconds=1.5,
      )
    )

    main_value = min(80, main_scroll.verticalScrollBar().maximum())
    control_value = min(120, control_scroll.verticalScrollBar().maximum())
    main_scroll.verticalScrollBar().setValue(main_value)
    control_scroll.verticalScrollBar().setValue(control_value)

    self.assertEqual(main_scroll.verticalScrollBar().value(), main_value)
    self.assertEqual(control_scroll.verticalScrollBar().value(), control_value)
    window.close()

  def test_dashboard_stacks_preflight_and_package_without_leaving_a_blank_left_cell(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )
    window = ShellWindow(model)
    window.resize(1400, 1000)
    window.show()

    dashboard = window.findChild(QtWidgets.QWidget, 'dashboard-surface')
    top_band = window.findChild(QtWidgets.QWidget, 'dashboard-top-band')
    left_column = window.findChild(QtWidgets.QWidget, 'dashboard-left-column')
    right_column = window.findChild(QtWidgets.QWidget, 'dashboard-right-column')
    device_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-device-identity',
    )
    preflight_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-preflight-board',
    )
    package_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-package-summary',
    )
    transport_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-transport-state',
    )
    evidence_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-session-evidence',
    )

    self.assertIsNotNone(dashboard)
    self.assertIsNotNone(top_band)
    self.assertIsNotNone(left_column)
    self.assertIsNotNone(right_column)
    self.assertIsNotNone(device_panel)
    self.assertIsNotNone(preflight_panel)
    self.assertIsNotNone(package_panel)
    self.assertIsNotNone(transport_panel)
    self.assertIsNotNone(evidence_panel)
    self.assertTrue(self._process_events_until(lambda: dashboard.isVisible()))

    self.assertIs(device_panel.parentWidget(), left_column)
    self.assertIs(transport_panel.parentWidget(), left_column)
    self.assertIs(preflight_panel.parentWidget(), right_column)
    self.assertIs(package_panel.parentWidget(), right_column)
    self.assertIs(evidence_panel.parentWidget(), dashboard)
    self.assertGreater(right_column.x(), left_column.x())
    self.assertGreater(evidence_panel.y(), top_band.y() + top_band.height())
    self.assertGreaterEqual(package_panel.y(), preflight_panel.y() + preflight_panel.height())
    self.assertGreaterEqual(transport_panel.y(), device_panel.y() + device_panel.height())
    window.close()

  def test_live_adb_probe_hydrates_main_device_panel_from_no_device_review(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=(
        _ready_adb_detection_trace(),
        _ready_adb_info_trace(),
      ),
    ) as mocked_execute:
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(detect_button)
      self.assertEqual(window.phase_label(), 'No Device')
      self.assertIn(
        'Device identity is intentionally blank at boot.',
        window.panel_summary('Device Identity'),
      )

      detect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 2)
      )

      self.assertTrue(
        self._process_events_until(
          lambda: 'Live companion detected' in window.panel_summary('Device Identity')
        )
      )
      self.assertTrue(
        self._process_events_until(
          lambda: (
            window.findChild(QtWidgets.QPushButton, 'control-action-detect-device') is not None
            and window.findChild(QtWidgets.QPushButton, 'control-action-detect-device').isEnabled()
          )
        )
      )
      self.assertEqual(mocked_execute.call_count, 2)
      self.assertEqual(window.phase_label(), 'ADB Device Detected')
      self.assertIn('Galaxy S21', window.panel_summary('Device Identity'))
      self.assertTrue(
        any(
          'Live companion backend: ADB' in line
          for line in window.panel_detail_lines('Device Identity')
        )
      )
      self.assertTrue(
        any(
          'Registry match: exact' in line
          for line in window.panel_detail_lines('Device Identity')
        )
      )
      self.assertTrue(
        any(
          'Android version: 14' in line
          for line in window.panel_detail_lines('Device Identity')
        )
      )
      device_pills = dict(window.status_pill_values())
      control_deck_title = window.findChild(QtWidgets.QLabel, 'control-deck-title')
      self.assertIsNotNone(control_deck_title)
      self.assertEqual(control_deck_title.text(), 'ADB Device Detected')
      self.assertEqual(device_pills['Phase'], 'ADB Device Detected')
      self.assertIn('SM_G991U via ADB', device_pills['Device'])
      window.close()

  def test_boot_unhydrated_shell_starts_with_blank_header_fields(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name='Operational startup shell',
      boot_unhydrated=True,
    )
    window = ShellWindow(model)

    device_pills = dict(window.status_pill_values())

    self.assertEqual(window.phase_label(), 'No Device')
    self.assertIn('intentionally blank at boot', window.panel_summary('Device Identity'))
    self.assertIn('stay blank at boot', window.panel_summary('Package Summary'))
    self.assertEqual(device_pills['Device'], '--')
    self.assertEqual(device_pills['Package'], '--')
    window.close()

  def test_detect_device_button_runs_adb_probe_when_clicked(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )

    allow_probe_completion = threading.Event()

    call_counter = {'count': 0}

    def _delayed_ready_trace(*_args, **_kwargs):
      call_counter['count'] += 1
      if call_counter['count'] == 1:
        allow_probe_completion.wait(timeout=1.0)
        return _ready_adb_detection_trace()
      return _ready_adb_info_trace()

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=_delayed_ready_trace,
    ) as mocked_execute:
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )
      adb_identity = window.findChild(QtWidgets.QLabel, 'live-adb-serial')
      adb_reboot_button = window.findChild(QtWidgets.QPushButton, 'live-adb-reboot')

      self.assertIsNotNone(detect_button)
      self.assertIsNotNone(adb_identity)
      self.assertIsNotNone(adb_reboot_button)
      self.assertEqual(mocked_execute.call_count, 0)
      self.assertFalse(adb_reboot_button.isEnabled())

      detect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 1)
      )
      self.assertIn('Detecting live device via ADB', window.live_status_text())
      self.assertFalse(detect_button.isEnabled())

      allow_probe_completion.set()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 2)
      )

      self.assertTrue(
        self._process_events_until(
          lambda: (
            window.findChild(QtWidgets.QLabel, 'live-adb-serial') is not None
            and 'R58N12345AB'
            in window.findChild(QtWidgets.QLabel, 'live-adb-serial').text()
          )
        )
      )
      current_adb_identity = window.findChild(QtWidgets.QLabel, 'live-adb-serial')
      current_adb_reboot_button = window.findChild(
        QtWidgets.QPushButton,
        'live-adb-reboot',
      )
      current_detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(current_adb_identity)
      self.assertIsNotNone(current_adb_reboot_button)
      self.assertIsNotNone(current_detect_button)
      self.assertIn('R58N12345AB', current_adb_identity.text())
      self.assertTrue(current_adb_reboot_button.isEnabled())
      self.assertTrue(current_detect_button.isEnabled())
      self.assertIn('captured', window.live_status_text().lower())
      window.close()

  def test_detect_device_completion_handler_runs_on_gui_thread(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      return_value=_ready_adb_detection_trace(),
    ):
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(detect_button)
      detect_button.click()

      self.assertTrue(
        self._process_events_until(
          lambda: window._last_live_command_result_on_gui_thread is not None
        )
      )
      self.assertTrue(window._last_live_command_result_on_gui_thread)
      window.close()

  def test_close_request_is_ignored_while_live_command_is_still_running(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )

    allow_probe_completion = threading.Event()
    call_counter = {'count': 0}

    def _delayed_ready_trace(*_args, **_kwargs):
      call_counter['count'] += 1
      if call_counter['count'] == 1:
        allow_probe_completion.wait(timeout=1.0)
        return _ready_adb_detection_trace()
      return _ready_adb_info_trace()

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=_delayed_ready_trace,
    ) as mocked_execute:
      window = ShellWindow(model)
      window.show()

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(detect_button)
      detect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 1)
      )

      window.close()
      self.application.processEvents()

      self.assertTrue(window.isVisible())
      self.assertIn(
        'Wait for the current live companion action to finish before closing the GUI.',
        window.live_status_text(),
      )

      allow_probe_completion.set()

      self.assertTrue(
        self._process_events_until(
          lambda: (
            window.findChild(QtWidgets.QPushButton, 'control-action-detect-device') is not None
            and window.findChild(QtWidgets.QPushButton, 'control-action-detect-device').isEnabled()
          )
        )
      )

      window.close()
      self.application.processEvents()
      self.assertFalse(window.isVisible())

  def test_close_request_is_ignored_while_retained_live_thread_is_still_running(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )

    class _FakeRunningThread:
      def __init__(self) -> None:
        self.running = True

      def isRunning(self) -> bool:
        return self.running

    window = ShellWindow(model)
    window.show()
    fake_thread = _FakeRunningThread()
    window._retained_live_command_objects.append((fake_thread, object(), 1))

    window.close()
    self.application.processEvents()

    self.assertTrue(window.isVisible())
    self.assertIn(
      'Wait for the current live companion action to finish before closing the GUI.',
      window.live_status_text(),
    )

    fake_thread.running = False
    window.close()
    self.application.processEvents()
    self.assertFalse(window.isVisible())

  def test_adb_reboot_requires_confirmation_and_runs_when_approved(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=(
        _ready_adb_detection_trace(),
        _ready_adb_info_trace(),
        _successful_adb_reboot_trace('system'),
      ),
    ) as mocked_execute:
      with mock.patch.object(
        QtWidgets.QMessageBox,
        'question',
        return_value=QtWidgets.QMessageBox.StandardButton.Yes,
      ) as mocked_question:
        with mock.patch.object(
          QtWidgets.QMessageBox,
          'warning',
          return_value=QtWidgets.QMessageBox.StandardButton.No,
        ) as mocked_warning:
          window = ShellWindow(model)

          detect_button = window.findChild(
            QtWidgets.QPushButton,
            'control-action-detect-device',
          )

          self.assertIsNotNone(detect_button)
          detect_button.click()

          self.assertTrue(
            self._process_events_until(lambda: mocked_execute.call_count == 2)
          )
          self.assertTrue(
            self._process_events_until(
              lambda: (
                window.findChild(QtWidgets.QPushButton, 'live-adb-reboot') is not None
                and window.findChild(QtWidgets.QPushButton, 'live-adb-reboot').isEnabled()
              )
            )
          )

          adb_mode_combo = window.findChild(QtWidgets.QComboBox, 'live-adb-mode')
          reboot_button = window.findChild(QtWidgets.QPushButton, 'live-adb-reboot')

          self.assertIsNotNone(adb_mode_combo)
          self.assertIsNotNone(reboot_button)
          adb_mode_combo.setCurrentText('system')
          reboot_button.click()

          self.assertTrue(
            self._process_events_until(lambda: mocked_execute.call_count == 3)
          )
          self.assertTrue(
            self._process_events_until(
              lambda: 'ADB reboot accepted for system' in window.live_status_text()
            )
          )
          self.assertEqual(mocked_question.call_count, 1)
          self.assertEqual(mocked_warning.call_count, 0)
          window.close()

  def test_detect_device_handler_exception_surfaces_status_instead_of_crashing(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      return_value=_ready_adb_detection_trace(),
    ):
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(detect_button)

      def _raise_after_trace(_trace):
        raise RuntimeError('synthetic detect handler failure')

      window._apply_unified_adb_detection_trace = _raise_after_trace
      detect_button.click()

      self.assertTrue(
        self._process_events_until(
          lambda: 'synthetic detect handler failure' in window.live_status_text()
        )
      )
      self.assertIsNotNone(
        window.findChild(
          QtWidgets.QPushButton,
          'control-action-detect-device',
        )
      )
      self.assertIn(
        'Live companion processing failed after command completion',
        window.live_status_text(),
      )
      window.close()

  def test_detect_device_ignores_stale_non_getprop_info_trace(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=(
        _ready_adb_detection_trace(),
        _ready_adb_detection_trace(),
      ),
    ) as mocked_execute:
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(detect_button)
      detect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 2)
      )
      self.assertTrue(
        self._process_events_until(
          lambda: 'Ignored one stale detect result' in window.live_status_text()
        )
      )

      current_detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )
      self.assertIsNotNone(current_detect_button)
      self.assertTrue(current_detect_button.isEnabled())
      self.assertIn(
        'Ignored one stale detect result',
        window.live_status_text(),
      )
      window.close()

  def test_detect_device_start_failure_writes_runtime_log_and_surfaces_status(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
      log_path = Path(temp_dir) / 'gui_runtime.log'
      with mock.patch.object(qt_shell_module, 'GUI_RUNTIME_LOG_PATH', log_path):
        window = ShellWindow(model)
        detect_button = window.findChild(
          QtWidgets.QPushButton,
          'control-action-detect-device',
        )

        self.assertIsNotNone(detect_button)
        with mock.patch.object(
          window,
          '_start_live_command',
          side_effect=RuntimeError('synthetic detect start failure'),
        ):
          detect_button.click()

        self.assertTrue(
          self._process_events_until(
            lambda: 'synthetic detect start failure' in window.live_status_text()
          )
        )
        self.assertIn('Detect device failed before command completion', window.live_status_text())
        self.assertIn(str(log_path), window.live_status_text())
        self.assertTrue(log_path.exists())
        self.assertIn('Detect device', log_path.read_text(encoding='utf-8'))
        window.close()

  def test_gui_hang_watchdog_reports_one_stall_with_last_heartbeat_note(self) -> None:
    events = []
    watchdog = qt_shell_module._GuiHangWatchdog(
      scenario_name='No-device control deck',
      phase_label='No Device',
      stall_seconds=0.10,
      poll_seconds=0.01,
      diagnostic_writer=lambda **payload: events.append(payload),
    )
    try:
      watchdog.mark('window_shown')
      self.assertTrue(
        self._process_events_until(lambda: len(events) == 1, timeout_seconds=0.5)
      )
    finally:
      watchdog.stop()

    self.assertEqual(events[0]['scenario_name'], 'No-device control deck')
    self.assertEqual(events[0]['phase_label'], 'No Device')
    self.assertEqual(events[0]['last_heartbeat_note'], 'window_shown')
    self.assertGreaterEqual(events[0]['stall_seconds'], 0.10)

  def test_detail_row_height_expands_for_wrapped_value_text(self) -> None:
    row = DetailRow(
      (
        'NEXT STEP: Treat live device info and capability hints as read-side '
        'guidance only; they do not imply flash readiness.'
      ),
      1.0,
    )

    narrow_height = row.heightForWidth(420)
    wide_height = row.heightForWidth(760)

    self.assertGreater(narrow_height, wide_height)
    self.assertGreaterEqual(narrow_height, 70)
    row.close()

  def test_metric_block_height_expands_for_wrapped_value_text(self) -> None:
    block = MetricBlock(
      'Capability Hint',
      'bounded info snapshot ready for reviewed guidance only',
      'neutral',
      1.0,
    )

    narrow_height = block.heightForWidth(220)
    wide_height = block.heightForWidth(420)

    self.assertGreater(narrow_height, wide_height)
    self.assertGreaterEqual(narrow_height, 96)
    block.close()

  def test_package_summary_panel_tracks_content_height_at_default_launch_size(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )
    window = ShellWindow(model)
    window.show()

    package_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-package-summary',
    )

    self.assertIsNotNone(package_panel)
    self.assertTrue(
      self._process_events_until(lambda: package_panel.isVisible())
    )
    self.assertLessEqual(
      package_panel.height(),
      package_panel.sizeHint().height() + 48,
    )
    window.close()

  def test_device_identity_panel_tracks_content_height_at_default_launch_size(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )
    window = ShellWindow(model)
    window.show()

    device_panel = window.findChild(
      DashboardPanel,
      'dashboard-panel-device-identity',
    )

    self.assertIsNotNone(device_panel)
    self.assertTrue(
      self._process_events_until(lambda: device_panel.isVisible())
    )
    self.assertLessEqual(
      device_panel.height(),
      device_panel.sizeHint().height() + 48,
    )
    window.close()

  def test_detect_device_button_falls_back_to_fastboot_when_adb_finds_nothing(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=(
        _no_device_adb_detection_trace(),
        _ready_fastboot_detection_trace(),
      ),
    ) as mocked_execute:
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )
      fastboot_identity = window.findChild(QtWidgets.QLabel, 'live-fastboot-serial')
      fastboot_reboot_button = window.findChild(
        QtWidgets.QPushButton,
        'live-fastboot-reboot',
      )

      self.assertIsNotNone(detect_button)
      self.assertIsNotNone(fastboot_identity)
      self.assertIsNotNone(fastboot_reboot_button)

      detect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 2)
      )
      self.assertTrue(
        self._process_events_until(
          lambda: (
            window.findChild(QtWidgets.QLabel, 'live-fastboot-serial') is not None
            and 'FASTBOOT123'
            in window.findChild(QtWidgets.QLabel, 'live-fastboot-serial').text()
          )
        )
      )

      current_fastboot_identity = window.findChild(
        QtWidgets.QLabel,
        'live-fastboot-serial',
      )
      current_fastboot_reboot_button = window.findChild(
        QtWidgets.QPushButton,
        'live-fastboot-reboot',
      )

      self.assertIsNotNone(current_fastboot_identity)
      self.assertIsNotNone(current_fastboot_reboot_button)
      self.assertIn('FASTBOOT123', current_fastboot_identity.text())
      self.assertTrue(current_fastboot_reboot_button.isEnabled())
      self.assertIn('Fastboot', window.live_status_text())
      window.close()

  def test_redetect_after_disconnect_clears_live_device_surfaces(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    no_device_fastboot_trace = normalize_android_tools_result(
      build_fastboot_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='fastboot-none',
        operation=AndroidToolsOperation.FASTBOOT_DEVICES,
        backend=AndroidToolsBackend.FASTBOOT,
        exit_code=0,
        stdout_lines=(),
      ),
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=(
        _ready_adb_detection_trace(),
        _ready_adb_info_trace(),
        _no_device_adb_detection_trace(),
        no_device_fastboot_trace,
      ),
    ) as mocked_execute:
      window = ShellWindow(model)

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )

      self.assertIsNotNone(detect_button)

      detect_button.click()
      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 2)
      )
      self.assertTrue(
        self._process_events_until(
          lambda: 'Live companion detected' in window.panel_summary('Device Identity')
        )
      )

      detect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-detect-device',
      )
      self.assertIsNotNone(detect_button)
      detect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_execute.call_count == 4)
      )
      self.assertTrue(
        self._process_events_until(
          lambda: 'No live device is currently detected.' in window.panel_summary('Device Identity')
        )
      )

      device_pills = dict(window.status_pill_values())
      adb_identity = window.findChild(QtWidgets.QLabel, 'live-adb-serial')
      fastboot_identity = window.findChild(QtWidgets.QLabel, 'live-fastboot-serial')

      self.assertEqual(device_pills['Device'], '--')
      self.assertIsNotNone(adb_identity)
      self.assertIsNotNone(fastboot_identity)
      self.assertEqual(adb_identity.text(), 'ADB: --')
      self.assertEqual(fastboot_identity.text(), 'Fastboot: --')
      window.close()

  def test_placeholder_control_reports_review_state_when_clicked(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
    )
    window = ShellWindow(model)

    load_package_button = window.findChild(
      QtWidgets.QPushButton,
      'control-action-load-package',
    )

    self.assertIsNotNone(load_package_button)
    load_package_button.click()

    self.assertIn('gui placeholder', window.live_status_text().lower())
    self.assertIn('Load package', window.live_status_text())
    window.close()

  def test_inspect_device_button_runs_bounded_read_side_lane(self) -> None:
    session = build_demo_session('no-device')
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('no-device'),
      boot_unhydrated=True,
    )

    with mock.patch(
      'calamum_vulcan.app.qt_shell.execute_android_tools_command',
      side_effect=(
        _ready_adb_detection_trace(),
        _ready_adb_info_trace(),
      ),
    ) as mocked_android, mock.patch(
      'calamum_vulcan.app.qt_shell.execute_heimdall_command',
      return_value=_ready_print_pit_trace(),
    ) as mocked_heimdall:
      window = ShellWindow(model)

      inspect_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-inspect-device',
      )

      self.assertIsNotNone(inspect_button)
      inspect_button.click()

      self.assertTrue(
        self._process_events_until(lambda: mocked_android.call_count == 2)
      )
      self.assertTrue(
        self._process_events_until(lambda: mocked_heimdall.call_count == 1)
      )
      mocked_heimdall.assert_called_once()
      self.assertTrue(
        self._process_events_until(
          lambda: 'Inspect-only workflow captured' in window.panel_summary('Session Evidence'),
          timeout_seconds=1.5,
        )
      )

      export_button = window.findChild(
        QtWidgets.QPushButton,
        'control-action-export-evidence',
      )
      self.assertIsNotNone(export_button)
      self.assertTrue(export_button.isEnabled())
      self.assertTrue(
        any(
          'Inspection posture: ready' in line
          for line in window.panel_detail_lines('Session Evidence')
        )
      )
      window.close()

  def test_export_evidence_button_writes_current_report(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = build_demo_pit_inspection(
      'ready',
      session=session,
      package_assessment=package_assessment,
    )
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label('ready'),
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
      output_path = Path(temp_dir) / 'gui-evidence.md'
      with mock.patch.object(
        QtWidgets.QFileDialog,
        'getSaveFileName',
        return_value=(str(output_path), 'Markdown (*.md)'),
      ):
        window = ShellWindow(model)
        export_button = window.findChild(
          QtWidgets.QPushButton,
          'control-action-export-evidence',
        )

        self.assertIsNotNone(export_button)
        self.assertTrue(export_button.isEnabled())

        export_button.click()

        self.assertTrue(output_path.exists())
        self.assertIn('Evidence exported to', window.live_status_text())
        self.assertIn('Calamum Vulcan session evidence', output_path.read_text(encoding='utf-8'))
        window.close()


if __name__ == '__main__':
  unittest.main()