"""Qt 6 shell surface for the Calamum Vulcan FS-03 implementation."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional
from typing import Tuple

from ..adapters.adb_fastboot import AndroidDeviceRecord
from ..adapters.adb_fastboot import AndroidToolsCommandPlan
from ..adapters.adb_fastboot import AndroidToolsNormalizedTrace
from ..adapters.adb_fastboot import AndroidToolsTraceState
from ..adapters.adb_fastboot import available_adb_reboot_targets
from ..adapters.adb_fastboot import available_fastboot_reboot_targets
from ..adapters.adb_fastboot import build_adb_detect_command_plan
from ..adapters.adb_fastboot import build_adb_reboot_command_plan
from ..adapters.adb_fastboot import build_fastboot_detect_command_plan
from ..adapters.adb_fastboot import build_fastboot_reboot_command_plan
from ..adapters.adb_fastboot import execute_android_tools_command
from .qt_compat import QT_AVAILABLE
from .qt_compat import QtCore
from .qt_compat import QtGui
from .qt_compat import QtWidgets
from .qt_compat import runtime_requirement_message
from .style import COLOR_TOKENS
from .style import WINDOW_STYLE
from .style import action_button_style
from .style import brand_frame_style
from .style import control_hint_style
from .style import detail_key_style
from .style import detail_row_style
from .style import detail_value_style
from .style import metric_style
from .style import mono_terminal_style
from .style import panel_style
from .style import pill_style
from .view_models import LiveCompanionDeviceViewModel
from .view_models import PanelViewModel
from .view_models import ShellViewModel
from .view_models import build_shell_view_model


if not QT_AVAILABLE:

  class ShellWindow(object):
    """Runtime placeholder when Qt 6 bindings are unavailable."""

    def __init__(self, _model: ShellViewModel) -> None:
      raise RuntimeError(runtime_requirement_message())


  def get_or_create_application() -> object:
    """Raise a deterministic error when Qt is not installed."""

    raise RuntimeError(runtime_requirement_message())


  def launch_shell(_model: ShellViewModel, duration_ms: int = 0) -> int:
    """Raise a deterministic error when Qt is not installed."""

    raise RuntimeError(runtime_requirement_message())

else:


  DEFAULT_UI_SCALE = 0.9
  ZOOM_MIN = 0.55
  ZOOM_MAX = 1.4
  ZOOM_STEP = 0.05
  PREFERRED_ADB_REBOOT_TARGETS = ('download',) + tuple(
    target for target in available_adb_reboot_targets() if target != 'download'
  )
  PREFERRED_FASTBOOT_REBOOT_TARGETS = available_fastboot_reboot_targets()

  APP_ROOT = Path(__file__).resolve().parents[1]
  HEADER_LOGO_CANDIDATES = (
    APP_ROOT / 'assets' / 'branding' / 'calamum_logo_color.png',
    APP_ROOT / 'assets' / 'branding' / 'calamum_logo.png',
    APP_ROOT / 'assets' / 'branding' / 'calamum_logo.svg',
    APP_ROOT / 'assets' / 'branding' / 'logo.png',
    APP_ROOT / 'assets' / 'branding' / 'logo.svg',
    APP_ROOT / 'assets' / 'calamum_logo.png',
    APP_ROOT / 'assets' / 'calamum_logo.svg',
    APP_ROOT / 'assets' / 'logo.png',
    APP_ROOT / 'assets' / 'logo.svg',
  )
  APP_ICON_CANDIDATES = (
    APP_ROOT / 'assets' / 'branding' / 'calamum_taskbar_icon.png',
    APP_ROOT / 'assets' / 'branding' / 'taskbar_icon.png',
    APP_ROOT / 'assets' / 'branding' / 'icon.png',
    APP_ROOT / 'assets' / 'branding' / 'logo.png',
    APP_ROOT / 'assets' / 'branding' / 'calamum_logo_color.png',
  )


  def _scaled(scale: float, value: int) -> int:
    """Return a scaled pixel value with a sensible lower bound."""

    return max(1, int(round(value * scale)))


  def _set_windows_app_id() -> None:
    """Set an explicit Windows app id so the taskbar uses the branded icon."""

    if not sys.platform.startswith('win'):
      return
    try:
      import ctypes
      ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        'Calamum.Vulcan.Sprint0_1_0'
      )
    except Exception:
      return


  def _build_brand_icon_pixmap(size: int) -> QtGui.QPixmap:
    """Return a generated Calamum shield icon pixmap."""

    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

    outer = QtGui.QPainterPath()
    outer.moveTo(size * 0.5, size * 0.07)
    outer.lineTo(size * 0.82, size * 0.19)
    outer.lineTo(size * 0.76, size * 0.63)
    outer.quadTo(size * 0.74, size * 0.8, size * 0.5, size * 0.93)
    outer.quadTo(size * 0.26, size * 0.8, size * 0.24, size * 0.63)
    outer.lineTo(size * 0.18, size * 0.19)
    outer.closeSubpath()

    shield_gradient = QtGui.QLinearGradient(0, 0, size, size)
    shield_gradient.setColorAt(0.0, QtGui.QColor('#263746'))
    shield_gradient.setColorAt(0.5, QtGui.QColor('#0f1722'))
    shield_gradient.setColorAt(1.0, QtGui.QColor('#16212d'))
    painter.setBrush(QtGui.QBrush(shield_gradient))
    painter.setPen(QtGui.QPen(QtGui.QColor('#90a4b8'), max(2, size // 24)))
    painter.drawPath(outer)

    glow_pen = QtGui.QPen(QtGui.QColor(COLOR_TOKENS['brand']), max(1, size // 40))
    glow_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    painter.setPen(glow_pen)

    center = QtCore.QPointF(size * 0.5, size * 0.48)
    node_radius = size * 0.07
    orbit_radius = size * 0.18
    node_points = []
    for index in range(5):
      angle = -math.pi / 2 + ((2 * math.pi) / 5) * index
      node_points.append(
        QtCore.QPointF(
          center.x() + orbit_radius * math.cos(angle),
          center.y() + orbit_radius * math.sin(angle),
        )
      )
    for point in node_points:
      painter.drawLine(center, point)

    for point in node_points:
      radial = QtGui.QRadialGradient(point, node_radius * 1.2)
      radial.setColorAt(0.0, QtGui.QColor('#f8fcff'))
      radial.setColorAt(0.5, QtGui.QColor('#a5efff'))
      radial.setColorAt(1.0, QtGui.QColor('#1f7892'))
      painter.setBrush(QtGui.QBrush(radial))
      painter.setPen(QtGui.QPen(QtGui.QColor('#dcecf4'), max(1, size // 48)))
      painter.drawEllipse(point, node_radius, node_radius)

    center_gradient = QtGui.QRadialGradient(center, node_radius * 1.8)
    center_gradient.setColorAt(0.0, QtGui.QColor('#ffffff'))
    center_gradient.setColorAt(0.45, QtGui.QColor('#c7f7ff'))
    center_gradient.setColorAt(1.0, QtGui.QColor('#2f8aa3'))
    painter.setBrush(QtGui.QBrush(center_gradient))
    painter.setPen(QtGui.QPen(QtGui.QColor('#edf6fb'), max(1, size // 48)))
    painter.drawEllipse(center, node_radius * 1.25, node_radius * 1.25)
    painter.end()
    return pixmap


  def _load_pixmap(candidates: tuple[Path, ...]) -> QtGui.QPixmap | None:
    """Load the first valid pixmap from a candidate list."""

    for candidate in candidates:
      if not candidate.exists():
        continue
      pixmap = QtGui.QPixmap(str(candidate))
      if pixmap.isNull():
        continue
      return pixmap
    return None


  def _load_brand_logo_pixmap(max_height: int) -> QtGui.QPixmap | None:
    """Load a checked-in branding logo when one is available."""

    pixmap = _load_pixmap(HEADER_LOGO_CANDIDATES)
    if pixmap is None:
      return None
    return pixmap.scaledToHeight(
      max_height,
      QtCore.Qt.TransformationMode.SmoothTransformation,
    )


  def create_app_icon() -> QtGui.QIcon:
    """Create the application icon used for the window and taskbar."""

    icon = QtGui.QIcon()
    source = _load_pixmap(APP_ICON_CANDIDATES)
    if source is not None:
      icon.addPixmap(source)
      return icon
    for size in (16, 24, 32, 48, 64, 128, 256):
      icon.addPixmap(_build_brand_icon_pixmap(size))
    return icon


  def _action_object_name(label: str) -> str:
    """Return a stable object name for one control-deck action button."""

    return 'control-action-' + label.lower().replace(' ', '-')


  class _CompanionCommandWorker(QtCore.QObject):
    """Background worker that runs one live companion command off the UI thread."""

    finished = QtCore.Signal(object, object)

    def __init__(self, command_plan: AndroidToolsCommandPlan) -> None:
      super().__init__()
      self._command_plan = command_plan

    @QtCore.Slot()
    def run(self) -> None:
      try:
        trace = execute_android_tools_command(self._command_plan)
      except Exception as error:  # pragma: no cover - defensive runtime bridge
        self.finished.emit(None, str(error))
        return
      self.finished.emit(trace, None)


  class BrandMark(QtWidgets.QFrame):
    """Header branding surface with icon and wordmark."""

    def __init__(self, model: ShellViewModel, scale: float) -> None:
      super().__init__()
      self.setObjectName('brand-mark')
      self.setStyleSheet(brand_frame_style(selector='brand-mark', scale=scale))
      layout = QtWidgets.QHBoxLayout(self)
      layout.setContentsMargins(
        _scaled(scale, 22),
        _scaled(scale, 18),
        _scaled(scale, 22),
        _scaled(scale, 18),
      )
      layout.setSpacing(_scaled(scale, 24))

      icon_label = QtWidgets.QLabel()
      logo_pixmap = _load_brand_logo_pixmap(_scaled(scale, 116))
      if logo_pixmap is None:
        logo_pixmap = _build_brand_icon_pixmap(_scaled(scale, 116))
      icon_label.setPixmap(logo_pixmap)
      icon_label.setMinimumHeight(_scaled(scale, 116))
      icon_label.setMinimumWidth(_scaled(scale, 340))
      icon_label.setMaximumWidth(_scaled(scale, 420))
      icon_label.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
      )
      icon_label.setScaledContents(False)

      text_layout = QtWidgets.QVBoxLayout()
      text_layout.setSpacing(_scaled(scale, 8))
      title = QtWidgets.QLabel('VULCAN')
      title.setStyleSheet(
        'font-size: {size}px; font-weight: 900; letter-spacing: 1.4px;'.format(
          size=_scaled(scale, 32),
        )
      )
      subtitle = QtWidgets.QLabel(
        '{phase} · {scenario}'.format(
          phase=model.phase_label,
          scenario=model.scenario_name,
        )
      )
      subtitle.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 700;'.format(
          muted=COLOR_TOKENS['muted'],
          size=_scaled(scale, 15),
        )
      )
      subtitle.setWordWrap(True)
      text_layout.addWidget(title)
      text_layout.addWidget(subtitle)

      pill_layout = QtWidgets.QHBoxLayout()
      pill_layout.setSpacing(_scaled(scale, 8))
      for pill in model.status_pills:
        pill_layout.addWidget(StatusPill(pill.label, pill.value, pill.tone, scale))
      pill_layout.addStretch(1)
      text_layout.addLayout(pill_layout)
      text_layout.addStretch(1)

      layout.addWidget(icon_label)
      layout.addLayout(text_layout, 1)


  class MetricBlock(QtWidgets.QFrame):
    """Compact metric widget used inside dashboard panels."""

    def __init__(self, label: str, value: str, tone: str, scale: float) -> None:
      super().__init__()
      self.setObjectName('metric-block')
      self.setStyleSheet(metric_style(tone, selector='metric-block', scale=scale))
      layout = QtWidgets.QVBoxLayout(self)
      layout.setContentsMargins(
        _scaled(scale, 10),
        _scaled(scale, 8),
        _scaled(scale, 10),
        _scaled(scale, 8),
      )
      layout.setSpacing(_scaled(scale, 5))
      label_widget = QtWidgets.QLabel(label.upper())
      label_widget.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 800; letter-spacing: 1px;'.format(
          muted=COLOR_TOKENS['muted'],
          size=_scaled(scale, 11),
        )
      )
      value_widget = QtWidgets.QLabel(value)
      value_widget.setWordWrap(True)
      value_widget.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
      )
      value_widget.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Expanding,
      )
      value_widget.setMinimumHeight(_scaled(scale, 28))
      value_widget.setStyleSheet(
        'font-size: {size}px; font-weight: 800; line-height: 1.2;'.format(
          size=_scaled(scale, 15),
        )
      )
      self.setMinimumHeight(_scaled(scale, 88))
      layout.addWidget(label_widget)
      layout.addWidget(value_widget)


  class DetailRow(QtWidgets.QFrame):
    """Structured detail row used inside dashboard panels."""

    def __init__(self, detail: str, scale: float) -> None:
      super().__init__()
      self.setObjectName('panel-detail-row')
      self.setStyleSheet(
        detail_row_style(selector='panel-detail-row', scale=scale)
      )
      layout = QtWidgets.QGridLayout(self)
      layout.setContentsMargins(
        _scaled(scale, 10),
        _scaled(scale, 8),
        _scaled(scale, 10),
        _scaled(scale, 8),
      )
      layout.setHorizontalSpacing(_scaled(scale, 12))
      layout.setVerticalSpacing(_scaled(scale, 4))

      key_text, value_text = self._split_detail(detail)
      key_widget = QtWidgets.QLabel(key_text.upper())
      key_widget.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
      )
      key_widget.setStyleSheet(detail_key_style(scale))
      key_widget.setMinimumWidth(_scaled(scale, 170))

      value_widget = QtWidgets.QLabel(value_text)
      value_widget.setWordWrap(True)
      value_widget.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
      )
      value_widget.setStyleSheet(detail_value_style(scale))

      layout.addWidget(key_widget, 0, 0)
      layout.addWidget(value_widget, 0, 1)
      layout.setColumnStretch(1, 1)

    @staticmethod
    def _split_detail(detail: str) -> Tuple[str, str]:
      if ' — ' in detail:
        key, value = detail.split(' — ', 1)
        return key, value
      if ': ' in detail:
        key, value = detail.split(': ', 1)
        return key, value
      return 'Note', detail


  class StatusPill(QtWidgets.QFrame):
    """Header status pill."""

    def __init__(self, label: str, value: str, tone: str, scale: float) -> None:
      super().__init__()
      self.setObjectName('status-pill')
      self.setStyleSheet(pill_style(tone, selector='status-pill', scale=scale))
      layout = QtWidgets.QVBoxLayout(self)
      layout.setContentsMargins(
        _scaled(scale, 10),
        _scaled(scale, 7),
        _scaled(scale, 10),
        _scaled(scale, 7),
      )
      layout.setSpacing(_scaled(scale, 2))
      label_widget = QtWidgets.QLabel(label.upper())
      label_widget.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 800; letter-spacing: 0.8px;'.format(
          muted=COLOR_TOKENS['muted'],
          size=_scaled(scale, 11),
        )
      )
      value_widget = QtWidgets.QLabel(value)
      value_widget.setStyleSheet(
        'font-size: {size}px; font-weight: 800;'.format(
          size=_scaled(scale, 15),
        )
      )
      layout.addWidget(label_widget)
      layout.addWidget(value_widget)


  class DashboardPanel(QtWidgets.QFrame):
    """Dashboard panel widget driven entirely by a panel view model."""

    def __init__(self, model: PanelViewModel, scale: float) -> None:
      super().__init__()
      self._model = model
      self.setObjectName('dashboard-panel')
      self.setStyleSheet(panel_style(model.tone, selector='dashboard-panel', scale=scale))

      layout = QtWidgets.QVBoxLayout(self)
      layout.setContentsMargins(
        _scaled(scale, 14),
        _scaled(scale, 14),
        _scaled(scale, 14),
        _scaled(scale, 14),
      )
      layout.setSpacing(_scaled(scale, 10))

      eyebrow = QtWidgets.QLabel(model.eyebrow)
      eyebrow.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 800; letter-spacing: 1.2px;'.format(
          muted=COLOR_TOKENS['muted'],
          size=_scaled(scale, 12),
        )
      )
      title = QtWidgets.QLabel(model.title)
      title.setStyleSheet(
        'font-size: {size}px; font-weight: 900;'.format(
          size=_scaled(scale, 25),
        )
      )
      summary = QtWidgets.QLabel(model.summary)
      summary.setWordWrap(True)
      summary.setStyleSheet(
        'font-size: {size}px; font-weight: 700; line-height: 1.3;'.format(
          size=_scaled(scale, 17),
        )
      )

      layout.addWidget(eyebrow)
      layout.addWidget(title)
      layout.addWidget(summary)

      metrics_layout = QtWidgets.QGridLayout()
      metrics_layout.setHorizontalSpacing(_scaled(scale, 8))
      metrics_layout.setVerticalSpacing(_scaled(scale, 8))
      for index, metric in enumerate(model.metrics):
        metrics_layout.addWidget(
          MetricBlock(metric.label, metric.value, metric.tone, scale),
          index // 2,
          index % 2,
        )
      if model.metrics:
        layout.addLayout(metrics_layout)
        layout.addSpacing(_scaled(scale, 4))

      for detail in model.detail_lines:
        layout.addWidget(DetailRow(detail, scale))

      layout.addStretch(1)


  class ShellWindow(QtWidgets.QMainWindow):
    """Main desktop shell for the FS-03 GUI implementation."""

    def __init__(self, model: ShellViewModel) -> None:
      super().__init__()
      self._model = model
      self._ui_scale = DEFAULT_UI_SCALE
      self._zoom_shortcuts = []
      self._panel_titles = tuple(panel.title for panel in model.panels)
      self._action_labels = tuple(action.label for action in model.control_actions)
      self._base_session = model.session
      self._base_package_assessment = model.package_assessment
      self._base_transport_trace = model.transport_trace
      self._live_dashboard_device = model.live_device
      self._boot_unhydrated = model.boot_unhydrated
      self._device_surface_cleared = model.device_surface_cleared
      self._live_log_lines = list(model.log_lines)
      self._live_status_text = 'Standby. No live device probe has run since startup.'
      self._live_status_tone = 'neutral'
      self._live_adb_serial = None
      self._live_fastboot_serial = None
      self._live_adb_identity = 'ADB: --'
      self._live_fastboot_identity = 'Fastboot: --'
      self._terminal = None
      self._live_status_label = None
      self._live_adb_serial_label = None
      self._live_fastboot_serial_label = None
      self._live_adb_mode_combo = None
      self._live_fastboot_mode_combo = None
      self._live_adb_reboot_button = None
      self._live_fastboot_reboot_button = None
      self._live_adb_detect_button = None
      self._live_fastboot_detect_button = None
      self._control_action_buttons = {}
      self._live_command_thread = None
      self._live_command_worker = None
      self._live_command_in_progress = False
      self._live_completion_handler = None
      self._wait_cursor_active = False
      self.setWindowTitle('Calamum Vulcan — {phase}'.format(phase=model.phase_label))
      self.resize(1680, 1040)
      self.setMinimumSize(1080, 720)
      self.setStyleSheet(WINDOW_STYLE)
      self.setWindowIcon(create_app_icon())
      self._install_zoom_shortcuts()
      self._build()

    def panel_titles(self) -> Tuple[str, ...]:
      """Return panel titles for validation and sandbox review."""

      return self._panel_titles

    def action_labels(self) -> Tuple[str, ...]:
      """Return control labels for validation and sandbox review."""

      return self._action_labels

    def live_status_text(self) -> str:
      """Return the current live companion status text."""

      return self._live_status_text

    def phase_label(self) -> str:
      """Return the current reviewed session phase label."""

      return self._model.phase_label

    def status_pill_values(self) -> Tuple[Tuple[str, str], ...]:
      """Return the current header pill label/value pairs."""

      return tuple((pill.label, pill.value) for pill in self._model.status_pills)

    def panel_summary(self, title: str) -> str:
      """Return the summary text for one named dashboard panel."""

      for panel in self._model.panels:
        if panel.title == title:
          return panel.summary
      raise KeyError('Unknown panel title: {title}'.format(title=title))

    def panel_detail_lines(self, title: str) -> Tuple[str, ...]:
      """Return the detail lines for one named dashboard panel."""

      for panel in self._model.panels:
        if panel.title == title:
          return panel.detail_lines
      raise KeyError('Unknown panel title: {title}'.format(title=title))

    def live_adb_reboot_targets(self) -> Tuple[str, ...]:
      """Return the available ADB reboot targets surfaced in the shell."""

      return PREFERRED_ADB_REBOOT_TARGETS

    def live_fastboot_reboot_targets(self) -> Tuple[str, ...]:
      """Return the available fastboot reboot targets surfaced in the shell."""

      return PREFERRED_FASTBOOT_REBOOT_TARGETS

    def zoom_percent(self) -> int:
      """Return the current shell zoom as a whole-number percentage."""

      return int(round(self._ui_scale * 100))

    def increase_zoom(self) -> None:
      """Increase the shell zoom level."""

      self._set_zoom(self._ui_scale + ZOOM_STEP)

    def decrease_zoom(self) -> None:
      """Decrease the shell zoom level."""

      self._set_zoom(self._ui_scale - ZOOM_STEP)

    def reset_zoom(self) -> None:
      """Restore the shell zoom level to the default density."""

      self._set_zoom(DEFAULT_UI_SCALE)

    def _install_zoom_shortcuts(self) -> None:
      """Register keyboard shortcuts for runtime UI zoom."""

      for sequence in ('Ctrl++', 'Ctrl+='):
        shortcut = QtGui.QShortcut(QtGui.QKeySequence(sequence), self)
        shortcut.activated.connect(self.increase_zoom)
        self._zoom_shortcuts.append(shortcut)
      for sequence, handler in (
        ('Ctrl+-', self.decrease_zoom),
        ('Ctrl+0', self.reset_zoom),
      ):
        shortcut = QtGui.QShortcut(QtGui.QKeySequence(sequence), self)
        shortcut.activated.connect(handler)
        self._zoom_shortcuts.append(shortcut)

    def _set_zoom(self, requested_scale: float) -> None:
      """Apply a bounded zoom level and rebuild the shell when it changes."""

      bounded = max(ZOOM_MIN, min(ZOOM_MAX, round(requested_scale, 2)))
      if abs(bounded - self._ui_scale) < 0.001:
        return
      self._ui_scale = bounded
      self._rebuild_ui()

    def _rebuild_ui(self) -> None:
      """Rebuild the shell widgets at the current zoom level."""

      existing = self.takeCentralWidget()
      if existing is not None:
        existing.deleteLater()
      self._build()

    def _scaled(self, value: int) -> int:
      """Return a pixel value scaled by the current shell zoom."""

      return _scaled(self._ui_scale, value)

    def _build(self) -> None:
      root_scroll = QtWidgets.QScrollArea()
      root_scroll.setWidgetResizable(True)
      root_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
      self.setCentralWidget(root_scroll)

      root = QtWidgets.QWidget()
      root_scroll.setWidget(root)
      root_layout = QtWidgets.QHBoxLayout(root)
      root_layout.setContentsMargins(
        self._scaled(20),
        self._scaled(20),
        self._scaled(20),
        self._scaled(20),
      )
      root_layout.setSpacing(self._scaled(18))

      splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
      splitter.setChildrenCollapsible(False)
      root_layout.addWidget(splitter, 1)

      primary_frame = QtWidgets.QFrame()
      primary = QtWidgets.QVBoxLayout(primary_frame)
      primary.setSpacing(self._scaled(18))
      primary.setContentsMargins(0, 0, 0, 0)

      control_deck = self._build_control_deck()
      splitter.addWidget(primary_frame)
      splitter.addWidget(control_deck)
      splitter.setStretchFactor(0, 4)
      splitter.setStretchFactor(1, 1)
      splitter.setSizes([1380, 380])

      primary.addWidget(BrandMark(self._model, self._ui_scale))

      dashboard = self._build_dashboard()
      primary.addLayout(dashboard, 3)

      log_panel = self._build_log_panel()
      primary.addWidget(log_panel, 1)

    def _build_dashboard(self) -> QtWidgets.QGridLayout:
      grid = QtWidgets.QGridLayout()
      grid.setHorizontalSpacing(self._scaled(18))
      grid.setVerticalSpacing(self._scaled(18))
      panels = [DashboardPanel(panel, self._ui_scale) for panel in self._model.panels]
      grid.addWidget(panels[0], 0, 0)
      grid.addWidget(panels[1], 0, 1)
      grid.addWidget(panels[2], 1, 0, 1, 2)
      grid.addWidget(panels[3], 2, 0)
      grid.addWidget(panels[4], 2, 1)
      grid.setColumnStretch(0, 1)
      grid.setColumnStretch(1, 1)
      return grid

    def _build_control_deck(self) -> QtWidgets.QScrollArea:
      scroll = QtWidgets.QScrollArea()
      scroll.setWidgetResizable(True)
      scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
      scroll.setMinimumWidth(self._scaled(360))
      scroll.setMaximumWidth(self._scaled(440))

      frame = QtWidgets.QFrame()
      frame.setObjectName('control-deck')
      frame.setStyleSheet(
        panel_style(self._model.phase_tone, selector='control-deck', scale=self._ui_scale)
      )
      layout = QtWidgets.QVBoxLayout(frame)
      layout.setContentsMargins(
        self._scaled(14),
        self._scaled(14),
        self._scaled(14),
        self._scaled(14),
      )
      layout.setSpacing(self._scaled(10))
      scroll.setWidget(frame)

      eyebrow = QtWidgets.QLabel('CONTROL DECK')
      eyebrow.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 800; letter-spacing: 1.2px;'.format(
          muted=COLOR_TOKENS['muted'],
          size=self._scaled(11),
        )
      )
      title = QtWidgets.QLabel(self._model.phase_label)
      title.setStyleSheet(
        'font-size: {size}px; font-weight: 900;'.format(size=self._scaled(25))
      )
      deck_note = QtWidgets.QLabel(
        'Detect device finds the live companion. Other deck buttons report status only.'
      )
      deck_note.setWordWrap(True)
      deck_note.setStyleSheet(control_hint_style(self._ui_scale))
      layout.addWidget(eyebrow)
      layout.addWidget(title)
      layout.addWidget(deck_note)

      for action in self._model.control_actions:
        hint_text = action.hint
        button_emphasis = action.emphasis
        button = QtWidgets.QPushButton(action.label)
        button.setObjectName(_action_object_name(action.label))
        button.setProperty('shell_base_enabled', action.enabled)
        if action.label == 'Detect device':
          hint_text = (
            'Auto-detect the active live companion through ADB first, then '
            'fastboot if needed.'
          )
          button.clicked.connect(self._probe_live_device)
        else:
          button_emphasis = 'normal'
          hint_text = self._placeholder_action_hint(action.label, action.hint)
          button.clicked.connect(
            lambda _checked=False, action_label=action.label, action_hint=hint_text: (
              self._handle_placeholder_action(action_label, action_hint)
            )
          )
        button.setProperty('shell_button_emphasis', button_emphasis)
        button.setEnabled(action.enabled)
        button.setStyleSheet(
          action_button_style(button_emphasis, action.enabled, self._ui_scale)
        )
        layout.addWidget(button)
        self._control_action_buttons[action.label] = button

        hint = QtWidgets.QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setStyleSheet(control_hint_style(self._ui_scale))
        layout.addWidget(hint)

      layout.addSpacing(self._scaled(12))

      companion_eyebrow = QtWidgets.QLabel('LIVE COMPANION')
      companion_eyebrow.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 800; letter-spacing: 1.2px;'.format(
          muted=COLOR_TOKENS['muted'],
          size=self._scaled(11),
        )
      )
      companion_summary = QtWidgets.QLabel(
        'Detect device checks ADB, then fastboot. Reboot unlocks after detection.'
      )
      companion_summary.setWordWrap(True)
      companion_summary.setStyleSheet(control_hint_style(self._ui_scale))
      layout.addWidget(companion_eyebrow)
      layout.addWidget(companion_summary)

      self._live_status_label = QtWidgets.QLabel(self._live_status_text)
      self._live_status_label.setObjectName('live-companion-status')
      self._live_status_label.setWordWrap(True)
      layout.addWidget(self._live_status_label)

      self._live_adb_serial_label = QtWidgets.QLabel(self._live_adb_identity)
      self._live_adb_serial_label.setObjectName('live-adb-serial')
      self._live_adb_serial_label.setWordWrap(True)
      self._live_adb_serial_label.setStyleSheet(control_hint_style(self._ui_scale))
      layout.addWidget(self._live_adb_serial_label)

      self._live_fastboot_serial_label = QtWidgets.QLabel(self._live_fastboot_identity)
      self._live_fastboot_serial_label.setObjectName('live-fastboot-serial')
      self._live_fastboot_serial_label.setWordWrap(True)
      self._live_fastboot_serial_label.setStyleSheet(control_hint_style(self._ui_scale))
      layout.addWidget(self._live_fastboot_serial_label)

      adb_target_label = QtWidgets.QLabel('ADB reboot target')
      adb_target_label.setStyleSheet(control_hint_style(self._ui_scale))
      layout.addWidget(adb_target_label)

      self._live_adb_mode_combo = QtWidgets.QComboBox()
      self._live_adb_mode_combo.setObjectName('live-adb-mode')
      self._live_adb_mode_combo.addItems(PREFERRED_ADB_REBOOT_TARGETS)
      self._live_adb_mode_combo.setStyleSheet(self._combo_box_style())
      self._live_adb_mode_combo.currentTextChanged.connect(self._refresh_live_controls)
      layout.addWidget(self._live_adb_mode_combo)

      self._live_adb_reboot_button = QtWidgets.QPushButton('ADB reboot to selected mode')
      self._live_adb_reboot_button.setObjectName('live-adb-reboot')
      self._live_adb_reboot_button.clicked.connect(self._handle_adb_reboot)
      layout.addWidget(self._live_adb_reboot_button)

      fastboot_target_label = QtWidgets.QLabel('Fastboot reboot target')
      fastboot_target_label.setStyleSheet(control_hint_style(self._ui_scale))
      layout.addWidget(fastboot_target_label)

      self._live_fastboot_mode_combo = QtWidgets.QComboBox()
      self._live_fastboot_mode_combo.setObjectName('live-fastboot-mode')
      self._live_fastboot_mode_combo.addItems(PREFERRED_FASTBOOT_REBOOT_TARGETS)
      self._live_fastboot_mode_combo.setStyleSheet(self._combo_box_style())
      self._live_fastboot_mode_combo.currentTextChanged.connect(self._refresh_live_controls)
      layout.addWidget(self._live_fastboot_mode_combo)

      self._live_fastboot_reboot_button = QtWidgets.QPushButton(
        'Fastboot reboot to selected mode'
      )
      self._live_fastboot_reboot_button.setObjectName('live-fastboot-reboot')
      self._live_fastboot_reboot_button.clicked.connect(self._handle_fastboot_reboot)
      layout.addWidget(self._live_fastboot_reboot_button)

      self._refresh_live_controls()

      layout.addStretch(1)
      return scroll

    def _build_log_panel(self) -> QtWidgets.QFrame:
      frame = QtWidgets.QFrame()
      frame.setObjectName('log-panel')
      frame.setStyleSheet(panel_style('neutral', selector='log-panel', scale=self._ui_scale))
      layout = QtWidgets.QVBoxLayout(frame)
      layout.setContentsMargins(
        self._scaled(18),
        self._scaled(18),
        self._scaled(18),
        self._scaled(18),
      )
      layout.setSpacing(self._scaled(10))

      title = QtWidgets.QLabel('OPERATIONAL LOG')
      title.setStyleSheet(
        'font-size: {size}px; font-weight: 800;'.format(size=self._scaled(22))
      )
      terminal = QtWidgets.QPlainTextEdit()
      self._terminal = terminal
      terminal.setReadOnly(True)
      terminal.setMinimumHeight(self._scaled(240))
      terminal.setStyleSheet(mono_terminal_style(self._ui_scale))
      terminal.setPlainText('\n'.join(self._live_log_lines))

      layout.addWidget(title)
      layout.addWidget(terminal)
      return frame

    def _combo_box_style(self) -> str:
      """Return the style for the live-control combo boxes."""

      return (
        'QComboBox {'
        'background-color: ' + COLOR_TOKENS['surface_alt'] + ';'
        'color: ' + COLOR_TOKENS['text'] + ';'
        'border: 1px solid ' + COLOR_TOKENS['line_soft'] + ';'
        'border-radius: ' + str(self._scaled(10)) + 'px;'
        'padding: ' + str(self._scaled(10)) + 'px;'
        'font-size: ' + str(self._scaled(13)) + 'px;'
        'min-height: ' + str(self._scaled(40)) + 'px;'
        '}'
        'QComboBox QAbstractItemView {'
        'background-color: ' + COLOR_TOKENS['surface_card'] + ';'
        'color: ' + COLOR_TOKENS['text'] + ';'
        'selection-background-color: ' + COLOR_TOKENS['info'] + ';'
        'selection-color: ' + COLOR_TOKENS['text'] + ';'
        '}'
      )

    def _live_status_style(self) -> str:
      """Return the style for the live companion status label."""

      return (
        'color: {accent}; font-size: {size}px; font-weight: 800; line-height: 1.3;'.format(
          accent=COLOR_TOKENS.get(self._live_status_tone, COLOR_TOKENS['text']),
          size=self._scaled(14),
        )
      )

    def _refresh_live_controls(self, *_args: object) -> None:
      """Refresh live companion labels and button enablement."""

      if self._live_status_label is not None:
        self._live_status_label.setText(self._live_status_text)
        self._live_status_label.setStyleSheet(self._live_status_style())
      for button in self._control_action_buttons.values():
        base_enabled = bool(button.property('shell_base_enabled'))
        emphasis = str(button.property('shell_button_emphasis') or 'normal')
        enabled = base_enabled and not self._live_command_in_progress
        button.setEnabled(enabled)
        button.setStyleSheet(
          action_button_style(emphasis, enabled, self._ui_scale)
        )
      if self._live_adb_serial_label is not None:
        self._live_adb_serial_label.setText(self._live_adb_identity)
      if self._live_fastboot_serial_label is not None:
        self._live_fastboot_serial_label.setText(self._live_fastboot_identity)
      if self._live_adb_detect_button is not None:
        detect_enabled = not self._live_command_in_progress
        self._live_adb_detect_button.setEnabled(detect_enabled)
        self._live_adb_detect_button.setStyleSheet(
          action_button_style('primary', detect_enabled, self._ui_scale)
        )
      if self._live_fastboot_detect_button is not None:
        detect_enabled = not self._live_command_in_progress
        self._live_fastboot_detect_button.setEnabled(detect_enabled)
        self._live_fastboot_detect_button.setStyleSheet(
          action_button_style('normal', detect_enabled, self._ui_scale)
        )
      if self._live_adb_mode_combo is not None:
        self._live_adb_mode_combo.setEnabled(not self._live_command_in_progress)
      if self._live_fastboot_mode_combo is not None:
        self._live_fastboot_mode_combo.setEnabled(not self._live_command_in_progress)
      if self._live_adb_reboot_button is not None:
        adb_enabled = (
          self._live_adb_serial is not None and not self._live_command_in_progress
        )
        self._live_adb_reboot_button.setEnabled(adb_enabled)
        self._live_adb_reboot_button.setStyleSheet(
          action_button_style(self._adb_reboot_emphasis(), adb_enabled, self._ui_scale)
        )
      if self._live_fastboot_reboot_button is not None:
        fastboot_enabled = (
          self._live_fastboot_serial is not None and not self._live_command_in_progress
        )
        self._live_fastboot_reboot_button.setEnabled(fastboot_enabled)
        self._live_fastboot_reboot_button.setStyleSheet(
          action_button_style(
            self._fastboot_reboot_emphasis(),
            fastboot_enabled,
            self._ui_scale,
          )
        )

    def _adb_reboot_emphasis(self) -> str:
      """Return button emphasis for the currently selected ADB target."""

      if self._live_adb_mode_combo is None:
        return 'warning'
      target = self._live_adb_mode_combo.currentText()
      if target == 'download':
        return 'danger'
      if target in ('recovery', 'bootloader', 'sideload', 'sideload-auto-reboot'):
        return 'warning'
      return 'primary'

    def _fastboot_reboot_emphasis(self) -> str:
      """Return button emphasis for the currently selected fastboot target."""

      if self._live_fastboot_mode_combo is None:
        return 'primary'
      if self._live_fastboot_mode_combo.currentText() == 'bootloader':
        return 'warning'
      return 'primary'

    def _set_live_status(self, text: str, tone: str) -> None:
      """Persist one live companion status update."""

      self._live_status_text = text
      self._live_status_tone = tone
      self._refresh_live_controls()

    def _set_live_busy(self, busy: bool) -> None:
      """Apply busy-state feedback for live companion work."""

      self._live_command_in_progress = busy
      application = QtWidgets.QApplication.instance()
      if application is not None:
        if busy and not self._wait_cursor_active:
          application.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
          self._wait_cursor_active = True
        elif not busy and self._wait_cursor_active:
          application.restoreOverrideCursor()
          self._wait_cursor_active = False
      self._refresh_live_controls()

    def _append_live_log_lines(self, lines: Tuple[str, ...]) -> None:
      """Append new live-control lines to the operational log."""

      if not lines:
        return
      self._live_log_lines.extend(lines)
      if self._terminal is None:
        return
      for line in lines:
        self._terminal.appendPlainText(line)

    def _probe_live_device(self) -> None:
      """Auto-detect one live companion across ADB and fastboot."""

      self._start_live_command(
        build_adb_detect_command_plan(),
        'Detecting live device via ADB…',
        self._apply_unified_adb_detection_trace,
      )

    def _probe_live_adb_devices(self) -> None:
      """Run a live ADB probe and refresh the companion controls."""

      self._start_live_command(
        build_adb_detect_command_plan(),
        'Running live ADB probe…',
        self._apply_adb_detection_trace,
      )

    def _probe_live_fastboot_devices(self) -> None:
      """Run a live fastboot probe and refresh the companion controls."""

      self._start_live_command(
        build_fastboot_detect_command_plan(),
        'Running live fastboot probe…',
        self._apply_fastboot_detection_trace,
      )

    def _apply_unified_adb_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply the unified detect flow after the initial ADB probe."""

      if trace.detected_devices:
        self._apply_adb_detection_trace(trace)
        return

      self._clear_live_dashboard_device(trace.command_plan.backend.value)
      self._live_adb_serial = None
      if trace.state == AndroidToolsTraceState.FAILED:
        self._live_adb_identity = 'ADB: probe failed; checking fastboot.'
        pending_text = 'ADB probe failed. Checking fastboot…'
      else:
        self._live_adb_identity = 'ADB: --'
        pending_text = 'ADB did not find a live device. Checking fastboot…'
      self._device_surface_cleared = True
      self._refresh_shell_view_model()
      self._refresh_live_controls()
      self._start_live_command(
        build_fastboot_detect_command_plan(),
        pending_text,
        self._apply_unified_fastboot_detection_trace,
      )

    def _apply_unified_fastboot_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply the unified detect flow after the fastboot fallback probe."""

      if trace.detected_devices:
        self._apply_fastboot_detection_trace(trace)
        return

      self._clear_live_dashboard_device(trace.command_plan.backend.value)
      self._live_fastboot_serial = None
      if trace.state == AndroidToolsTraceState.FAILED:
        self._live_fastboot_identity = 'Fastboot: probe failed.'
        self._set_live_status(
          'ADB did not identify a live device, and the fastboot probe failed.',
          'danger',
        )
      else:
        self._live_fastboot_identity = 'Fastboot: --'
        self._set_live_status(
          'No live device detected after checking ADB and fastboot.',
          'neutral',
        )
      self._device_surface_cleared = True
      self._refresh_shell_view_model()
      self._refresh_live_controls()

    def _start_live_command(
      self,
      command_plan: AndroidToolsCommandPlan,
      pending_text: str,
      completion_handler,
    ) -> None:
      """Run one live companion command in a worker thread."""

      if self._live_command_in_progress:
        self._set_live_status(
          'Wait for the current live companion action to finish before sending another command.',
          'warning',
        )
        return

      self._boot_unhydrated = False
      self._live_completion_handler = completion_handler
      self._set_live_status(pending_text, 'info')
      self._append_live_log_lines(
        ('[COMPANION-PENDING] {command}'.format(
          command=command_plan.display_command,
        ),)
      )
      self._set_live_busy(True)

      thread = QtCore.QThread(self)
      worker = _CompanionCommandWorker(command_plan)
      worker.moveToThread(thread)
      thread.started.connect(worker.run)
      worker.finished.connect(self._handle_live_command_result)
      worker.finished.connect(thread.quit)
      worker.finished.connect(worker.deleteLater)
      thread.finished.connect(thread.deleteLater)

      self._live_command_thread = thread
      self._live_command_worker = worker
      thread.start()

    def _handle_live_command_result(
      self,
      trace: object,
      error_message: object,
    ) -> None:
      """Apply one completed live companion command on the UI thread."""

      completion_handler = self._live_completion_handler
      self._live_completion_handler = None
      self._live_command_thread = None
      self._live_command_worker = None
      self._set_live_busy(False)

      if error_message:
        message = str(error_message)
        self._append_live_log_lines(('[COMPANION-ERROR] {message}'.format(
          message=message,
        ),))
        self._set_live_status(message, 'danger')
        return

      if not isinstance(trace, AndroidToolsNormalizedTrace):
        self._set_live_status(
          'Live companion returned an unexpected result shape.',
          'danger',
        )
        return

      self._append_live_log_lines(self._render_live_trace_lines(trace))
      if completion_handler is not None:
        try:
          completion_handler(trace)
        except Exception as error:  # pragma: no cover - defensive GUI guardrail
          message = (
            'Live companion processing failed after command completion: '
            '{error_type}: {error}'.format(
              error_type=type(error).__name__,
              error=error,
            )
          )
          self._append_live_log_lines(
            ('[COMPANION-ERROR] {message}'.format(message=message),)
          )
          self._set_live_status(message, 'danger')

    def _placeholder_action_hint(self, action_label: str, fallback_hint: str) -> str:
      """Return honest Qt-shell wording for review-only control-deck actions."""

      placeholder_hints = {
        'Load package': (
          'GUI placeholder. Stage firmware through the CLI or fixture selection.'
        ),
        'Review preflight': (
          'GUI placeholder. Read the Preflight and Evidence panels for trust state.'
        ),
        'Execute flash plan': (
          'GUI placeholder. Live flash execution is not exposed here yet.'
        ),
        'Resume workflow': (
          'GUI placeholder. Resume remains scenario-backed in this stage.'
        ),
        'Export evidence': (
          'GUI placeholder. Export via the CLI or scripted validation.'
        ),
      }
      return placeholder_hints.get(
        action_label,
        'GUI placeholder. ' + fallback_hint,
      )

    def _handle_placeholder_action(self, action_label: str, hint_text: str) -> None:
      """Make review-only control-deck actions respond honestly when clicked."""

      message = '{label}: {hint}'.format(
        label=action_label,
        hint=hint_text,
      )
      self._set_live_status(message, 'warning')
      self._append_live_log_lines(
        ('[CONTROL-PLACEHOLDER] {message}'.format(message=message),)
      )

    def _refresh_shell_view_model(self) -> None:
      """Rebuild the shell model after live companion metadata changes."""

      self._model = build_shell_view_model(
        self._base_session,
        scenario_name=self._model.scenario_name,
        package_assessment=self._base_package_assessment,
        transport_trace=self._base_transport_trace,
        live_device=self._live_dashboard_device,
        boot_unhydrated=self._boot_unhydrated,
        device_surface_cleared=self._device_surface_cleared,
      )
      self._panel_titles = tuple(panel.title for panel in self._model.panels)
      self._action_labels = tuple(action.label for action in self._model.control_actions)
      self.setWindowTitle(
        'Calamum Vulcan — {phase}'.format(phase=self._model.phase_label)
      )
      self._rebuild_ui()

    def _build_live_dashboard_device(
      self,
      device: AndroidDeviceRecord,
      backend: str,
    ) -> LiveCompanionDeviceViewModel:
      """Build one live-device overlay for the main dashboard surfaces."""

      return LiveCompanionDeviceViewModel(
        backend=backend,
        serial=device.serial,
        state=device.state,
        transport=device.transport,
        product_code=device.model or device.product,
        model_name=device.model,
        device_name=device.device,
      )

    def _clear_live_dashboard_device(self, backend: str) -> None:
      """Clear the live dashboard overlay when the active backend no longer detects a device."""

      if (
        self._live_dashboard_device is None
        or self._live_dashboard_device.backend != backend
      ):
        return
      self._live_dashboard_device = None

    def _apply_adb_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply one ADB detection trace to shell-local live state."""

      ready_device = self._first_device_with_state(trace.detected_devices, 'device')
      if ready_device is not None:
        self._device_surface_cleared = False
        self._live_dashboard_device = self._build_live_dashboard_device(
          ready_device,
          trace.command_plan.backend.value,
        )
        self._refresh_shell_view_model()
        self._live_adb_serial = ready_device.serial
        self._live_adb_identity = 'ADB: {identity}'.format(
          identity=self._device_identity_text(ready_device),
        )
        self._set_live_status(
          '{summary} Active companion: {identity} via ADB.'.format(
            summary=trace.summary,
            identity=self._device_identity_text(ready_device),
          ),
          'success',
        )
      elif trace.detected_devices:
        self._device_surface_cleared = False
        selected_device = trace.detected_devices[0]
        self._live_dashboard_device = self._build_live_dashboard_device(
          selected_device,
          trace.command_plan.backend.value,
        )
        self._refresh_shell_view_model()
        self._live_adb_serial = None
        self._live_adb_identity = 'ADB: {identity} (authorize)'.format(
          identity=self._device_identity_text(selected_device),
        )
        tone = 'warning' if trace.state != AndroidToolsTraceState.FAILED else 'danger'
        self._set_live_status(
          '{summary} Active companion: {identity} via ADB; authorize or reconnect before reboot commands.'.format(
            summary=trace.summary,
            identity=self._device_identity_text(selected_device),
          ),
          tone,
        )
      else:
        self._clear_live_dashboard_device(trace.command_plan.backend.value)
        self._device_surface_cleared = True
        self._refresh_shell_view_model()
        self._live_adb_serial = None
        self._live_adb_identity = 'ADB: --'
        tone = 'neutral' if trace.state == AndroidToolsTraceState.NO_DEVICES else 'danger'
        self._set_live_status(
          '{summary} No live ADB companion detected.'.format(
            summary=trace.summary,
          ),
          tone,
        )
      self._refresh_live_controls()

    def _apply_fastboot_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply one fastboot detection trace to shell-local live state."""

      if trace.detected_devices:
        self._device_surface_cleared = False
        selected = trace.detected_devices[0]
        self._live_dashboard_device = self._build_live_dashboard_device(
          selected,
          trace.command_plan.backend.value,
        )
        self._refresh_shell_view_model()
        self._live_fastboot_serial = selected.serial
        self._live_fastboot_identity = 'Fastboot: {identity}'.format(
          identity=self._device_identity_text(selected),
        )
        self._set_live_status(
          '{summary} Active companion: {identity} via Fastboot.'.format(
            summary=trace.summary,
            identity=self._device_identity_text(selected),
          ),
          'success',
        )
      else:
        self._clear_live_dashboard_device(trace.command_plan.backend.value)
        self._device_surface_cleared = True
        self._refresh_shell_view_model()
        self._live_fastboot_serial = None
        self._live_fastboot_identity = 'Fastboot: --'
        tone = 'neutral' if trace.state == AndroidToolsTraceState.NO_DEVICES else 'danger'
        self._set_live_status(
          '{summary} No live fastboot companion detected.'.format(
            summary=trace.summary,
          ),
          tone,
        )
      self._refresh_live_controls()

    def _handle_adb_reboot(self) -> None:
      """Issue one live ADB reboot command to the selected target mode."""

      if self._live_adb_serial is None or self._live_adb_mode_combo is None:
        self._set_live_status(
          'Run the live ADB probe before issuing an ADB reboot command.',
          'warning',
        )
        return
      target = self._live_adb_mode_combo.currentText()
      command_plan = build_adb_reboot_command_plan(
        target,
        device_serial=self._live_adb_serial,
      )
      if not self._confirm_live_command(command_plan):
        return
      pending_text = 'Running live ADB reboot command for {target}…'.format(
        target=target,
      )
      if command_plan.vendor_specific:
        pending_text = 'Running vendor-specific ADB reboot command for {target}…'.format(
          target=target,
        )
      self._start_live_command(
        command_plan,
        pending_text,
        self._apply_adb_reboot_trace,
      )

    def _apply_adb_reboot_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply one completed ADB reboot trace to shell-local live state."""

      if trace.state == AndroidToolsTraceState.COMPLETED:
        self._live_adb_serial = None
        self._live_adb_identity = 'ADB: re-detect after reboot.'
        self._set_live_status(
          'ADB reboot accepted for {target}; re-detect after the device settles into its new mode.'.format(
            target=trace.command_plan.reboot_target or 'system',
          ),
          'warning',
        )
      else:
        self._set_live_status(trace.summary, 'danger')
      self._refresh_live_controls()

    def _handle_fastboot_reboot(self) -> None:
      """Issue one live fastboot reboot command to the selected target mode."""

      if self._live_fastboot_serial is None or self._live_fastboot_mode_combo is None:
        self._set_live_status(
          'Run the live fastboot probe before issuing a fastboot reboot command.',
          'warning',
        )
        return
      target = self._live_fastboot_mode_combo.currentText()
      command_plan = build_fastboot_reboot_command_plan(
        target,
        device_serial=self._live_fastboot_serial,
      )
      if not self._confirm_live_command(command_plan):
        return
      self._start_live_command(
        command_plan,
        'Running live fastboot reboot command for {target}…'.format(target=target),
        self._apply_fastboot_reboot_trace,
      )

    def _apply_fastboot_reboot_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply one completed fastboot reboot trace to shell-local live state."""

      if trace.state == AndroidToolsTraceState.COMPLETED:
        self._live_fastboot_serial = None
        self._live_fastboot_identity = 'Fastboot: re-detect after reboot.'
        self._set_live_status(
          'Fastboot reboot accepted for {target}; re-detect after the device settles into its new mode.'.format(
            target=trace.command_plan.reboot_target or 'system',
          ),
          'warning',
        )
      else:
        self._set_live_status(trace.summary, 'danger')
      self._refresh_live_controls()

    def _confirm_live_command(self, command_plan: AndroidToolsCommandPlan) -> bool:
      """Ask the operator to confirm a live reboot command."""

      details = [
        'This will issue a live device control command.',
        '',
        command_plan.display_command,
      ]
      if command_plan.target_serial is not None:
        details.append('serial: {serial}'.format(serial=command_plan.target_serial))
      if command_plan.reboot_target is not None:
        details.append('target: {target}'.format(target=command_plan.reboot_target))
      if command_plan.vendor_specific:
        details.append('vendor-specific: yes')
      details.extend(command_plan.notes)
      message = '\n'.join(details)
      buttons = (
        QtWidgets.QMessageBox.StandardButton.Yes
        | QtWidgets.QMessageBox.StandardButton.No
      )
      default = QtWidgets.QMessageBox.StandardButton.No
      if command_plan.vendor_specific:
        result = QtWidgets.QMessageBox.warning(
          self,
          'Confirm vendor-specific reboot',
          message,
          buttons,
          default,
        )
      else:
        result = QtWidgets.QMessageBox.question(
          self,
          'Confirm live reboot command',
          message,
          buttons,
          default,
        )
      return result == QtWidgets.QMessageBox.StandardButton.Yes

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
      """Restore any temporary busy cursor state before the window closes."""

      if self._wait_cursor_active:
        application = QtWidgets.QApplication.instance()
        if application is not None:
          application.restoreOverrideCursor()
        self._wait_cursor_active = False
      super().closeEvent(event)

    def _render_live_trace_lines(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> Tuple[str, ...]:
      """Render one companion trace into operational-log lines."""

      lines = [
        '[COMPANION] {command}'.format(
          command=trace.command_plan.display_command,
        ),
        '[COMPANION-RESULT] backend={backend} state={state} exit={exit_code} summary={summary}'.format(
          backend=trace.command_plan.backend.value,
          state=trace.state.value,
          exit_code=trace.exit_code,
          summary=trace.summary,
        ),
      ]
      for device in trace.detected_devices:
        lines.append(
          '[COMPANION-DEVICE] serial={serial} state={state} transport={transport} product={product} model={model}'.format(
            serial=device.serial,
            state=device.state,
            transport=device.transport,
            product=device.product or 'unknown',
            model=device.model or 'unknown',
          )
        )
      for note in trace.notes:
        lines.append('[COMPANION-NOTE] {note}'.format(note=note))
      return tuple(lines)

    def _device_identity_text(self, device: AndroidDeviceRecord) -> str:
      """Return one compact device identity string for live labels."""

      detail = device.model or device.product or device.transport
      return '{serial} ({detail})'.format(
        serial=device.serial,
        detail=detail,
      )

    def _first_device_with_state(
      self,
      devices: Tuple[AndroidDeviceRecord, ...],
      state: str,
    ) -> Optional[AndroidDeviceRecord]:
      """Return the first device that matches the requested live state."""

      for device in devices:
        if device.state == state:
          return device
      return None


  def get_or_create_application() -> QtWidgets.QApplication:
    """Return the active Qt application or create one."""

    _set_windows_app_id()
    application = QtWidgets.QApplication.instance()
    if application is None:
      application = QtWidgets.QApplication([])
    application.setApplicationName('Calamum Vulcan')
    application.setApplicationDisplayName('Calamum Vulcan')
    application.setOrganizationName('Calamum Vulcan')
    application.setWindowIcon(create_app_icon())
    return application


  def launch_shell(model: ShellViewModel, duration_ms: int = 0) -> int:
    """Launch the Qt shell and optionally auto-close it for sandbox use."""

    application = get_or_create_application()
    window = ShellWindow(model)
    window.show()
    if duration_ms > 0:
      QtCore.QTimer.singleShot(duration_ms, application.quit)
    return application.exec()