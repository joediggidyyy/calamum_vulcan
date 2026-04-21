"""Qt 6 shell surface for the Calamum Vulcan FS-03 implementation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from datetime import timezone
import math
import os
import sys
from pathlib import Path
import tempfile
import threading
import time
import traceback
from typing import Optional
from typing import Tuple

from ..adapters.adb_fastboot import AndroidToolsCommandPlan
from ..adapters.adb_fastboot import AndroidToolsNormalizedTrace
from ..adapters.adb_fastboot import AndroidToolsOperation
from ..adapters.adb_fastboot import AndroidToolsTraceState
from ..adapters.adb_fastboot import available_adb_reboot_targets
from ..adapters.adb_fastboot import available_fastboot_reboot_targets
from ..adapters.adb_fastboot import build_adb_detect_command_plan
from ..adapters.adb_fastboot import build_adb_device_info_command_plan
from ..adapters.adb_fastboot import build_adb_reboot_command_plan
from ..adapters.adb_fastboot import build_fastboot_detect_command_plan
from ..adapters.adb_fastboot import build_fastboot_reboot_command_plan
from ..adapters.adb_fastboot import execute_android_tools_command
from ..adapters.heimdall import HeimdallCommandPlan
from ..adapters.heimdall import HeimdallNormalizedTrace
from ..adapters.heimdall import build_download_pit_command_plan
from ..adapters.heimdall import build_print_pit_command_plan
from ..adapters.heimdall import execute_heimdall_command
from ..domain.live_device import LiveDeviceInfoState
from ..domain.live_device import LiveDetectionState
from ..domain.live_device import LiveDeviceSnapshot
from ..domain.live_device import LiveFallbackPosture
from ..domain.live_device import apply_live_device_info_trace
from ..domain.live_device import build_live_detection_session
from ..domain.pit import PitInspection
from ..domain.pit import PitInspectionState
from ..domain.pit import build_pit_inspection
from ..domain.reporting import write_session_evidence_report
from ..domain.state import build_inspection_workflow
from ..domain.state import inspection_in_progress
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
  )
  APP_ICON_CANDIDATES = (
    APP_ROOT / 'assets' / 'branding' / 'calamum_taskbar_icon.png',
    APP_ROOT / 'assets' / 'branding' / 'taskbar_icon.png',
    APP_ROOT / 'assets' / 'branding' / 'icon.png',
    APP_ROOT / 'assets' / 'branding' / 'logo.png',
    APP_ROOT / 'assets' / 'branding' / 'calamum_logo_color.png',
  )
  GUI_RUNTIME_LOG_PATH = Path(tempfile.gettempdir()) / 'calamum_vulcan_gui_runtime.log'
  GUI_EVENT_LOOP_STALL_SECONDS = 5.0
  GUI_EVENT_LOOP_POLL_SECONDS = 0.25
  GUI_EVENT_LOOP_HEARTBEAT_MS = 250


  def _write_gui_runtime_diagnostic(
    context: str,
    details: Tuple[str, ...] = (),
    include_thread_stacks: bool = False,
  ) -> Path:
    """Append one timestamped GUI runtime diagnostic to the temp log."""

    GUI_RUNTIME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GUI_RUNTIME_LOG_PATH.open('a', encoding='utf-8') as handle:
      handle.write(
        '[{timestamp}] {context}\n'.format(
          timestamp=datetime.now(timezone.utc).isoformat(),
          context=context,
        )
      )
      for detail in details:
        handle.write('{detail}\n'.format(detail=detail))
      if include_thread_stacks:
        handle.write('Python thread stacks:\n')
        current_frames = sys._current_frames()
        threads_by_ident = {
          thread.ident: thread
          for thread in threading.enumerate()
          if thread.ident is not None
        }
        for ident, frame in sorted(current_frames.items(), key=lambda item: item[0]):
          thread = threads_by_ident.get(ident)
          thread_name = thread.name if thread is not None else 'unknown'
          daemon_state = thread.daemon if thread is not None else 'unknown'
          handle.write(
            '--- thread ident={ident} name={name} daemon={daemon} ---\n'.format(
              ident=ident,
              name=thread_name,
              daemon=daemon_state,
            )
          )
          traceback.print_stack(frame, file=handle)
          handle.write('\n')
      handle.write('\n')
    return GUI_RUNTIME_LOG_PATH


  def _write_gui_event_loop_stall_diagnostic(
    scenario_name: str,
    phase_label: str,
    last_heartbeat_note: str,
    stall_seconds: float,
  ) -> Path:
    """Write one event-loop stall diagnostic with Python thread stacks."""

    return _write_gui_runtime_diagnostic(
      'GUI event loop stall detected',
      details=(
        'pid={pid}'.format(pid=os.getpid()),
        'scenario={scenario}'.format(scenario=scenario_name),
        'phase={phase}'.format(phase=phase_label),
        'last_heartbeat_note={note}'.format(note=last_heartbeat_note),
        'stall_seconds={stall_seconds:.2f}'.format(stall_seconds=stall_seconds),
      ),
      include_thread_stacks=True,
    )


  class _GuiHangWatchdog(object):
    """Background watchdog that records Python stacks when the GUI stops ticking."""

    def __init__(
      self,
      scenario_name: str,
      phase_label: str,
      stall_seconds: float = GUI_EVENT_LOOP_STALL_SECONDS,
      poll_seconds: float = GUI_EVENT_LOOP_POLL_SECONDS,
      diagnostic_writer=None,
    ) -> None:
      self._scenario_name = scenario_name
      self._phase_label = phase_label
      self._stall_seconds = stall_seconds
      self._poll_seconds = poll_seconds
      self._diagnostic_writer = (
        diagnostic_writer or _write_gui_event_loop_stall_diagnostic
      )
      self._lock = threading.Lock()
      self._stop_event = threading.Event()
      self._last_heartbeat_at = time.monotonic()
      self._last_heartbeat_note = 'watchdog_started'
      self._reported_stall = False
      self._thread = threading.Thread(
        target=self._watch_loop,
        name='calamum-gui-watchdog',
        daemon=True,
      )
      self._thread.start()

    def mark(self, note: str) -> None:
      """Record one observed GUI heartbeat milestone."""

      with self._lock:
        self._last_heartbeat_at = time.monotonic()
        self._last_heartbeat_note = note
        self._reported_stall = False

    def stop(self) -> None:
      """Stop the watchdog after the GUI event loop exits."""

      self._stop_event.set()

    def _watch_loop(self) -> None:
      """Check for heartbeat stalls and write one diagnostic per stall."""

      while not self._stop_event.wait(self._poll_seconds):
        should_report = False
        last_note = 'unknown'
        stall_seconds = 0.0
        with self._lock:
          stall_seconds = time.monotonic() - self._last_heartbeat_at
          last_note = self._last_heartbeat_note
          if stall_seconds >= self._stall_seconds and not self._reported_stall:
            self._reported_stall = True
            should_report = True
        if should_report:
          self._diagnostic_writer(
            scenario_name=self._scenario_name,
            phase_label=self._phase_label,
            last_heartbeat_note=last_note,
            stall_seconds=stall_seconds,
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


  def _utc_now() -> str:
    """Return an ISO8601 UTC timestamp for inspect/export flows."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
      '+00:00',
      'Z',
    )


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


  def _panel_object_name(title: str) -> str:
    """Return a stable object name for one dashboard panel."""

    normalized = title.lower()
    for old, new in (
      (' ', '-'),
      ('/', '-'),
      ('—', '-'),
      (':', ''),
    ):
      normalized = normalized.replace(old, new)
    return 'dashboard-panel-' + normalized


  def _configure_hidden_scroll_area(
    scroll: QtWidgets.QScrollArea,
    object_name: str,
  ) -> None:
    """Configure one independently scrollable region with hidden scrollbars."""

    scroll.setObjectName(object_name)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(
      QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll.setVerticalScrollBarPolicy(
      QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
    scroll.viewport().setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)


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


  class _HeimdallCommandWorker(QtCore.QObject):
    """Background worker that runs one bounded Heimdall command off the UI thread."""

    finished = QtCore.Signal(object, object)

    def __init__(self, command_plan: HeimdallCommandPlan) -> None:
      super().__init__()
      self._command_plan = command_plan

    @QtCore.Slot()
    def run(self) -> None:
      try:
        trace = execute_heimdall_command(self._command_plan)
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
      self._scale = scale
      self._label_text = label.upper()
      self._value_text = value
      self._horizontal_margin = _scaled(scale, 10)
      self._vertical_margin = _scaled(scale, 8)
      self._content_spacing = _scaled(scale, 5)
      self._minimum_block_height = _scaled(scale, 96)
      self.setObjectName('metric-block')
      self.setStyleSheet(metric_style(tone, selector='metric-block', scale=scale))
      self.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Preferred,
      )
      layout = QtWidgets.QVBoxLayout(self)
      layout.setContentsMargins(
        self._horizontal_margin,
        self._vertical_margin,
        self._horizontal_margin,
        self._vertical_margin,
      )
      layout.setSpacing(self._content_spacing)
      label_widget = QtWidgets.QLabel(self._label_text)
      self._label_widget = label_widget
      label_widget.setStyleSheet(
        'color: {muted}; font-size: {size}px; font-weight: 800; letter-spacing: 1px;'.format(
          muted=COLOR_TOKENS['muted'],
          size=_scaled(scale, 11),
        )
      )
      value_widget = QtWidgets.QLabel(value)
      self._value_widget = value_widget
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
      layout.addWidget(label_widget)
      layout.addWidget(value_widget)

    def hasHeightForWidth(self) -> bool:
      """Return whether the widget computes height from the available width."""

      return True

    def heightForWidth(self, width: int) -> int:
      """Return one content-aware height that preserves wrapped metric values."""

      content_width = max(1, width - (self._horizontal_margin * 2))
      flags = int(QtCore.Qt.TextFlag.TextWordWrap)
      label_height = self._label_widget.fontMetrics().boundingRect(
        0,
        0,
        content_width,
        10_000,
        flags,
        self._label_text,
      ).height()
      value_height = self._value_widget.fontMetrics().boundingRect(
        0,
        0,
        content_width,
        10_000,
        flags,
        self._value_text,
      ).height()
      return max(
        self._minimum_block_height,
        (self._vertical_margin * 2) + self._content_spacing + label_height + value_height,
      )

    def sizeHint(self) -> QtCore.QSize:
      """Return one size hint that respects wrapped metric content."""

      hint = super().sizeHint()
      width = max(hint.width(), _scaled(self._scale, 220))
      return QtCore.QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QtCore.QSize:
      """Return a minimum size hint large enough for wrapped metric content."""

      width = _scaled(self._scale, 180)
      return QtCore.QSize(width, self.heightForWidth(width))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
      """Refresh geometry hints when the metric block width changes."""

      super().resizeEvent(event)
      self.updateGeometry()


  class DetailRow(QtWidgets.QFrame):
    """Structured detail row used inside dashboard panels."""

    def __init__(self, detail: str, scale: float) -> None:
      super().__init__()
      self._scale = scale
      self.setObjectName('panel-detail-row')
      self.setStyleSheet(
        detail_row_style(selector='panel-detail-row', scale=scale)
      )
      self.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Preferred,
      )
      self._horizontal_margin = _scaled(scale, 10)
      self._vertical_margin = _scaled(scale, 8)
      self._horizontal_spacing = _scaled(scale, 12)
      self._minimum_key_width = _scaled(scale, 170)
      self._minimum_row_height = _scaled(scale, 54)
      layout = QtWidgets.QGridLayout(self)
      layout.setContentsMargins(
        self._horizontal_margin,
        self._vertical_margin,
        self._horizontal_margin,
        self._vertical_margin,
      )
      layout.setHorizontalSpacing(self._horizontal_spacing)
      layout.setVerticalSpacing(_scaled(scale, 4))
      self._layout = layout

      key_text, value_text = self._split_detail(detail)
      self._key_text = key_text.upper()
      self._value_text = value_text
      key_widget = QtWidgets.QLabel(key_text.upper())
      self._key_widget = key_widget
      key_widget.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
      )
      key_widget.setStyleSheet(detail_key_style(scale))
      key_widget.setMinimumWidth(self._minimum_key_width)

      value_widget = QtWidgets.QLabel(value_text)
      self._value_widget = value_widget
      value_widget.setWordWrap(True)
      value_widget.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
      )
      value_widget.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Preferred,
      )
      value_widget.setStyleSheet(detail_value_style(scale))

      layout.addWidget(key_widget, 0, 0)
      layout.addWidget(value_widget, 0, 1)
      layout.setColumnStretch(1, 1)

    def hasHeightForWidth(self) -> bool:
      """Return whether the row computes height from the available width."""

      return True

    def heightForWidth(self, width: int) -> int:
      """Return one content-aware row height for wrapped detail values."""

      content_width = max(1, width - (self._horizontal_margin * 2))
      value_width = max(
        1,
        content_width - self._minimum_key_width - self._horizontal_spacing,
      )
      flags = int(QtCore.Qt.TextFlag.TextWordWrap)
      key_height = self._key_widget.fontMetrics().boundingRect(
        0,
        0,
        self._minimum_key_width,
        10_000,
        flags,
        self._key_text,
      ).height()
      value_height = self._value_widget.fontMetrics().boundingRect(
        0,
        0,
        value_width,
        10_000,
        flags,
        self._value_text,
      ).height()
      return max(
        self._minimum_row_height,
        (self._vertical_margin * 2) + max(key_height, value_height),
      )

    def sizeHint(self) -> QtCore.QSize:
      """Return one size hint that respects wrapped detail content."""

      hint = super().sizeHint()
      width = max(hint.width(), _scaled(self._scale, 320))
      return QtCore.QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QtCore.QSize:
      """Return a minimum size hint large enough for wrapped detail rows."""

      width = _scaled(self._scale, 260)
      return QtCore.QSize(width, self.heightForWidth(width))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
      """Refresh geometry hints when the row width changes."""

      super().resizeEvent(event)
      self.updateGeometry()

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
      self._scale = scale
      object_name = _panel_object_name(model.title)
      self.setObjectName(object_name)
      self.setStyleSheet(panel_style(model.tone, selector=object_name, scale=scale))
      self.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Preferred,
      )

      layout = QtWidgets.QVBoxLayout(self)
      self._layout = layout
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

    def hasHeightForWidth(self) -> bool:
      """Return whether the panel computes height from its available width."""

      return True

    def heightForWidth(self, width: int) -> int:
      """Return one content-aware panel height for the current width."""

      return self._layout.totalHeightForWidth(max(1, width))

    def sizeHint(self) -> QtCore.QSize:
      """Return one size hint that reflects wrapped panel content."""

      hint = super().sizeHint()
      width = max(hint.width(), _scaled(self._scale, 360))
      return QtCore.QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QtCore.QSize:
      """Return a minimum size hint that stays close to actual content height."""

      return self.sizeHint()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
      """Refresh geometry hints when the panel width changes."""

      super().resizeEvent(event)
      self.updateGeometry()


  class ShellWindow(QtWidgets.QMainWindow):
    """Main desktop shell for the FS-03 GUI implementation."""

    _live_command_result_ready = QtCore.Signal(object, object, object)
    _pit_command_result_ready = QtCore.Signal(object, object, object)

    def __init__(self, model: ShellViewModel) -> None:
      super().__init__()
      self._model = model
      self._ui_scale = DEFAULT_UI_SCALE
      self._zoom_shortcuts = []
      self._panel_titles = tuple(panel.title for panel in model.panels)
      self._action_labels = tuple(action.label for action in model.control_actions)
      self._base_session = model.session
      self._base_package_assessment = model.package_assessment
      self._base_pit_inspection = model.pit_inspection
      self._base_transport_trace = model.transport_trace
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
      self._retained_live_command_objects = []
      self._live_completion_handlers = {}
      self._pit_command_thread = None
      self._pit_command_worker = None
      self._retained_pit_command_objects = []
      self._pit_completion_handlers = {}
      self._live_command_in_progress = False
      self._last_live_command_result_on_gui_thread = None
      self._wait_cursor_active = False
      self._live_command_result_ready.connect(
        self._handle_live_command_result,
        QtCore.Qt.ConnectionType.QueuedConnection,
      )
      self._pit_command_result_ready.connect(
        self._handle_pit_command_result,
        QtCore.Qt.ConnectionType.QueuedConnection,
      )
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
      root = QtWidgets.QWidget()
      self.setCentralWidget(root)
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

      primary_scroll = QtWidgets.QScrollArea()
      _configure_hidden_scroll_area(primary_scroll, 'main-pane-scroll')
      primary_frame = QtWidgets.QFrame()
      primary_scroll.setWidget(primary_frame)
      primary = QtWidgets.QVBoxLayout(primary_frame)
      primary.setSpacing(self._scaled(18))
      primary.setContentsMargins(0, 0, 0, 0)

      control_deck = self._build_control_deck()
      splitter.addWidget(primary_scroll)
      splitter.addWidget(control_deck)
      splitter.setStretchFactor(0, 4)
      splitter.setStretchFactor(1, 1)
      splitter.setSizes([1380, 380])

      primary.addWidget(BrandMark(self._model, self._ui_scale))

      dashboard = self._build_dashboard_widget()
      primary.addWidget(
        dashboard,
        0,
        QtCore.Qt.AlignmentFlag.AlignTop,
      )

      log_panel = self._build_log_panel()
      primary.addWidget(log_panel, 1)

    def _build_dashboard_widget(self) -> QtWidgets.QWidget:
      """Return one content-sized dashboard surface for the main panels."""

      widget = QtWidgets.QWidget()
      widget.setObjectName('dashboard-surface')
      widget.setSizePolicy(
        QtWidgets.QSizePolicy.Policy.Expanding,
        QtWidgets.QSizePolicy.Policy.Maximum,
      )
      layout = QtWidgets.QVBoxLayout(widget)
      layout.setContentsMargins(0, 0, 0, 0)
      layout.setSpacing(self._scaled(18))
      layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
      layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

      panels = [DashboardPanel(panel, self._ui_scale) for panel in self._model.panels]

      top_band = QtWidgets.QWidget()
      top_band.setObjectName('dashboard-top-band')
      top_band_layout = QtWidgets.QHBoxLayout(top_band)
      top_band_layout.setContentsMargins(0, 0, 0, 0)
      top_band_layout.setSpacing(self._scaled(18))
      top_band_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

      left_column = QtWidgets.QWidget()
      left_column.setObjectName('dashboard-left-column')
      left_column_layout = QtWidgets.QVBoxLayout(left_column)
      left_column_layout.setContentsMargins(0, 0, 0, 0)
      left_column_layout.setSpacing(self._scaled(18))
      left_column_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
      left_column_layout.addWidget(panels[0])
      left_column_layout.addWidget(panels[3])

      right_column = QtWidgets.QWidget()
      right_column.setObjectName('dashboard-right-column')
      right_column_layout = QtWidgets.QVBoxLayout(right_column)
      right_column_layout.setContentsMargins(0, 0, 0, 0)
      right_column_layout.setSpacing(self._scaled(18))
      right_column_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
      right_column_layout.addWidget(panels[1])
      right_column_layout.addWidget(panels[2])

      top_band_layout.addWidget(left_column, 1)
      top_band_layout.addWidget(right_column, 1)

      layout.addWidget(top_band)
      layout.addWidget(panels[4])
      return widget

    def _build_control_deck(self) -> QtWidgets.QScrollArea:
      scroll = QtWidgets.QScrollArea()
      _configure_hidden_scroll_area(scroll, 'control-deck-scroll')
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
      title.setObjectName('control-deck-title')
      title.setStyleSheet(
        'font-size: {size}px; font-weight: 900;'.format(size=self._scaled(25))
      )
      deck_note = QtWidgets.QLabel(
        'Detect device stays a quick live probe. Inspect device runs the first-class read-side lane: detect/info plus PIT review and exportable evidence, still without opening a write path.'
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
        elif action.label == 'Inspect device':
          hint_text = (
            'Run the inspect-only lane: quick live detection, bounded device '
            'info, PIT review, and exportable evidence without opening a '
            'write path.'
          )
          button.clicked.connect(self._run_inspect_workflow)
        elif action.label == 'Export evidence':
          hint_text = (
            'Export the current read-side evidence bundle to Markdown or JSON.'
          )
          button.clicked.connect(self._export_evidence_report)
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

    def _record_live_runtime_failure(self, context: str, error: Exception) -> Path:
      """Write one runtime GUI failure to the persistent temp log."""

      GUI_RUNTIME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
      with GUI_RUNTIME_LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(
          '[{timestamp}] {context}\n'.format(
            timestamp=datetime.now(timezone.utc).isoformat(),
            context=context,
          )
        )
        traceback.print_exception(
          type(error),
          error,
          error.__traceback__,
          file=handle,
        )
        handle.write('\n')
      return GUI_RUNTIME_LOG_PATH

    def _handle_live_action_exception(
      self,
      context: str,
      error: Exception,
    ) -> None:
      """Surface one top-level live-action failure without crashing the GUI."""

      log_path = self._record_live_runtime_failure(context, error)
      self._live_command_thread = None
      self._live_command_worker = None
      self._live_completion_handlers.clear()
      self._set_live_busy(False)
      message = (
        '{context} failed before command completion: {error_type}: {error}. '
        'Details were written to: {path}'.format(
          context=context,
          error_type=type(error).__name__,
          error=error,
          path=log_path,
        )
      )
      self._append_live_log_lines(
        (
          '[COMPANION-ERROR] {message}'.format(message=message),
        )
      )
      self._set_live_status(message, 'danger')

    def _probe_live_device(self) -> None:
      """Auto-detect one live companion across ADB and fastboot."""

      try:
        self._start_live_command(
          build_adb_detect_command_plan(),
          'Detecting live device via ADB…',
          self._apply_unified_adb_detection_trace,
        )
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('Detect device', error)

    def _probe_live_adb_devices(self) -> None:
      """Run a live ADB probe and refresh the companion controls."""

      try:
        self._start_live_command(
          build_adb_detect_command_plan(),
          'Running live ADB probe…',
          self._apply_adb_detection_trace,
        )
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('ADB probe', error)

    def _probe_live_fastboot_devices(self) -> None:
      """Run a live fastboot probe and refresh the companion controls."""

      try:
        self._start_live_command(
          build_fastboot_detect_command_plan(),
          'Running live fastboot probe…',
          self._apply_fastboot_detection_trace,
        )
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('Fastboot probe', error)

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
      self._set_live_status(pending_text, 'info')
      self._append_live_log_lines(
        ('[COMPANION-PENDING] {command}'.format(
          command=command_plan.display_command,
        ),)
      )
      self._set_live_busy(True)

      thread = QtCore.QThread(self)
      worker = _CompanionCommandWorker(command_plan)
      command_key = id(worker)
      self._live_completion_handlers[command_key] = completion_handler
      self._retained_live_command_objects.append((thread, worker, command_key))
      worker.moveToThread(thread)
      thread.started.connect(worker.run)
      worker.finished.connect(
        lambda trace, error_message, command_key=command_key: (
          self._live_command_result_ready.emit(
            command_key,
            trace,
            error_message,
          )
        )
      )
      worker.finished.connect(thread.quit)
      worker.finished.connect(worker.deleteLater)
      thread.finished.connect(
        lambda command_key=command_key, thread=thread, worker=worker: (
          self._finalize_live_command_thread(command_key, thread, worker)
        )
      )
      thread.finished.connect(thread.deleteLater)

      self._live_command_thread = thread
      self._live_command_worker = worker
      thread.start()

    def _finalize_live_command_thread(
      self,
      command_key: object,
      thread,
      worker,
    ) -> None:
      """Release retained live-command Qt objects only after the thread exits."""

      self._live_completion_handlers.pop(command_key, None)
      self._retained_live_command_objects = [
        retained
        for retained in self._retained_live_command_objects
        if retained[0] is not thread
      ]
      if self._live_command_thread is thread:
        self._live_command_thread = None
      if self._live_command_worker is worker:
        self._live_command_worker = None

    def _start_pit_command(
      self,
      command_plan: HeimdallCommandPlan,
      pending_text: str,
      completion_handler,
    ) -> None:
      """Run one bounded Heimdall inspect-only command in a worker thread."""

      if self._live_command_in_progress:
        self._set_live_status(
          'Wait for the current live companion action to finish before sending another command.',
          'warning',
        )
        return

      self._set_live_status(pending_text, 'info')
      self._append_live_log_lines(
        ('[INSPECTION-PENDING] {command}'.format(
          command=command_plan.display_command,
        ),)
      )
      self._set_live_busy(True)

      thread = QtCore.QThread(self)
      worker = _HeimdallCommandWorker(command_plan)
      command_key = id(worker)
      self._pit_completion_handlers[command_key] = completion_handler
      self._retained_pit_command_objects.append((thread, worker, command_key))
      worker.moveToThread(thread)
      thread.started.connect(worker.run)
      worker.finished.connect(
        lambda trace, error_message, command_key=command_key: (
          self._pit_command_result_ready.emit(
            command_key,
            trace,
            error_message,
          )
        )
      )
      worker.finished.connect(thread.quit)
      worker.finished.connect(worker.deleteLater)
      thread.finished.connect(
        lambda command_key=command_key, thread=thread, worker=worker: (
          self._finalize_pit_command_thread(command_key, thread, worker)
        )
      )
      thread.finished.connect(thread.deleteLater)

      self._pit_command_thread = thread
      self._pit_command_worker = worker
      thread.start()

    def _finalize_pit_command_thread(
      self,
      command_key: object,
      thread,
      worker,
    ) -> None:
      """Release retained PIT-command Qt objects only after the thread exits."""

      self._pit_completion_handlers.pop(command_key, None)
      self._retained_pit_command_objects = [
        retained
        for retained in self._retained_pit_command_objects
        if retained[0] is not thread
      ]
      if self._pit_command_thread is thread:
        self._pit_command_thread = None
      if self._pit_command_worker is worker:
        self._pit_command_worker = None

    @QtCore.Slot(object, object, object)
    def _handle_live_command_result(
      self,
      command_key: object,
      trace: object,
      error_message: object,
    ) -> None:
      """Apply one completed live companion command on the UI thread."""

      self._last_live_command_result_on_gui_thread = (
        QtCore.QThread.currentThread() == self.thread()
      )
      completion_handler = self._live_completion_handlers.pop(command_key, None)
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
          log_path = self._record_live_runtime_failure(
            'Live companion processing',
            error,
          )
          message = (
            'Live companion processing failed after command completion: '
            '{error_type}: {error}. Details were written to: {path}'.format(
              error_type=type(error).__name__,
              error=error,
              path=log_path,
            )
          )
          self._append_live_log_lines(
            ('[COMPANION-ERROR] {message}'.format(message=message),)
          )
          self._set_live_status(message, 'danger')

    @QtCore.Slot(object, object, object)
    def _handle_pit_command_result(
      self,
      command_key: object,
      trace: object,
      error_message: object,
    ) -> None:
      """Apply one completed bounded PIT command on the UI thread."""

      completion_handler = self._pit_completion_handlers.pop(command_key, None)
      self._set_live_busy(False)

      if error_message:
        message = str(error_message)
        self._append_live_log_lines(('[INSPECTION-ERROR] {message}'.format(
          message=message,
        ),))
        self._set_live_status(message, 'danger')
        return

      if not isinstance(trace, HeimdallNormalizedTrace):
        self._set_live_status(
          'Inspect-only PIT review returned an unexpected result shape.',
          'danger',
        )
        return

      self._append_live_log_lines(self._render_pit_trace_lines(trace))
      if completion_handler is not None:
        try:
          completion_handler(trace)
        except Exception as error:  # pragma: no cover - defensive GUI guardrail
          log_path = self._record_live_runtime_failure(
            'Inspect-only PIT processing',
            error,
          )
          message = (
            'Inspect-only PIT processing failed after command completion: '
            '{error_type}: {error}. Details were written to: {path}'.format(
              error_type=type(error).__name__,
              error=error,
              path=log_path,
            )
          )
          self._append_live_log_lines(
            ('[INSPECTION-ERROR] {message}'.format(message=message),)
          )
          self._set_live_status(message, 'danger')

    def _placeholder_action_hint(self, action_label: str, fallback_hint: str) -> str:
      """Return honest Qt-shell wording for review-only control-deck actions."""

      placeholder_hints = {
        'Load package': (
          'GUI placeholder. Stage firmware through the CLI or fixture selection.'
        ),
        'Execute flash plan': (
          'GUI placeholder. Live flash execution is not exposed here yet.'
        ),
        'Resume workflow': (
          'GUI placeholder. Resume remains scenario-backed in this stage.'
        ),
      }
      return placeholder_hints.get(
        action_label,
        'GUI placeholder. ' + fallback_hint,
      )

    def _export_evidence_report(self) -> None:
      """Export the current evidence bundle to a Markdown or JSON file."""

      default_path = Path(tempfile.gettempdir()) / (
        'calamum_vulcan_inspection_{timestamp}.md'.format(
          timestamp=_utc_now().replace(':', '').replace('-', '').replace('T', '_').replace('Z', ''),
        )
      )
      selected_path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
        self,
        'Export Calamum Vulcan evidence',
        str(default_path),
        'Markdown (*.md);;JSON (*.json)',
      )
      if not selected_path:
        self._set_live_status('Evidence export cancelled.', 'warning')
        return

      format_name = 'markdown'
      if selected_path.lower().endswith('.json') or 'JSON' in selected_filter:
        format_name = 'json'
      output_path = write_session_evidence_report(
        self._model.session_report,
        Path(selected_path),
        format_name=format_name,
        transport_trace=self._base_transport_trace,
      )
      self._append_live_log_lines(
        ('[EVIDENCE-EXPORT] {path}'.format(path=output_path),)
      )
      self._set_live_status(
        'Evidence exported to {path}.'.format(path=output_path),
        'success',
      )

    def _run_inspect_workflow(self) -> None:
      """Run the inspect-only read-side workflow inside the shell."""

      try:
        self._boot_unhydrated = False
        self._base_pit_inspection = None
        self._base_session = replace(
          self._base_session,
          inspection=inspection_in_progress(
            summary=(
              'Inspect-only workflow is running across live detect/info and '
              'PIT review.'
            ),
            captured_at_utc=_utc_now(),
          ),
        )
        self._append_live_log_lines(
          ('[INSPECTION] Inspect-only workflow started.',)
        )
        self._start_live_command(
          build_adb_detect_command_plan(),
          'Inspect-only: detecting device via ADB…',
          self._apply_inspection_adb_detection_trace,
        )
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('Inspect device', error)

    def _apply_inspection_adb_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Continue the inspect-only lane after the initial ADB probe."""

      if trace.detected_devices:
        detection = build_live_detection_session(trace)
        self._set_live_detection(detection)
        self._live_fastboot_serial = None
        self._live_fastboot_identity = 'Fastboot: --'
        if detection.snapshot is not None and detection.snapshot.command_ready:
          self._live_adb_serial = detection.snapshot.serial
          self._live_adb_identity = 'ADB: {identity}'.format(
            identity=self._live_identity_text(detection.snapshot),
          )
          if detection.snapshot.info_state == LiveDeviceInfoState.NOT_COLLECTED:
            self._refresh_live_controls()
            self._start_live_command(
              build_adb_device_info_command_plan(
                device_serial=detection.snapshot.serial,
              ),
              'Inspect-only: gathering live device info via ADB…',
              self._apply_inspection_adb_device_info_trace,
            )
            return
        else:
          self._live_adb_serial = None
          self._live_adb_identity = 'ADB: --'
        self._continue_inspection_to_pit_review()
        return

      detection = build_live_detection_session(
        trace,
        fallback_posture=LiveFallbackPosture.NEEDED,
        fallback_reason=(
          'ADB did not establish a live device; fastboot fallback will be checked next.'
        ),
        source_labels=('adb', 'fastboot'),
      )
      self._set_live_detection(detection)
      self._live_adb_serial = None
      self._live_adb_identity = 'ADB: --'
      self._live_fastboot_serial = None
      self._live_fastboot_identity = 'Fastboot: --'
      self._refresh_live_controls()
      self._start_live_command(
        build_fastboot_detect_command_plan(),
        'Inspect-only: ADB found no live device. Checking fastboot…',
        self._apply_inspection_fastboot_detection_trace,
      )

    def _apply_inspection_adb_device_info_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Continue the inspect-only lane after bounded ADB info capture."""

      if trace.command_plan.operation != AndroidToolsOperation.ADB_GETPROP:
        self._append_live_log_lines(
          (
            '[INSPECTION-STALE] Ignored one stale live result while waiting for bounded ADB info capture.',
          )
        )
        self._set_live_status(
          'Ignored one stale detect result while waiting for bounded live device info.',
          'warning',
        )
        self._refresh_live_controls()
        return

      updated_detection = apply_live_device_info_trace(
        self._base_session.live_detection,
        trace,
      )
      self._set_live_detection(updated_detection)
      snapshot = updated_detection.snapshot
      if snapshot is not None:
        self._live_adb_serial = snapshot.serial if snapshot.command_ready else None
        self._live_adb_identity = 'ADB: {identity}'.format(
          identity=self._live_identity_text(snapshot),
        )
      self._continue_inspection_to_pit_review()

    def _apply_inspection_fastboot_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Continue the inspect-only lane after fastboot fallback detection."""

      if trace.detected_devices:
        detection = build_live_detection_session(
          trace,
          fallback_posture=LiveFallbackPosture.ENGAGED,
          fallback_reason=(
            'ADB did not establish a live device; fastboot captured the active companion.'
          ),
          source_labels=('adb', 'fastboot'),
        )
      else:
        detection = build_live_detection_session(
          trace,
          fallback_posture=LiveFallbackPosture.ENGAGED,
          fallback_reason=(
            'ADB did not establish a live device; fastboot fallback also failed to capture a live companion.'
          ),
          source_labels=('adb', 'fastboot'),
        )
      self._set_live_detection(detection)
      self._live_adb_serial = None
      self._live_adb_identity = 'ADB: --'
      if detection.snapshot is not None:
        self._live_fastboot_serial = detection.snapshot.serial
        self._live_fastboot_identity = 'Fastboot: {identity}'.format(
          identity=self._live_identity_text(detection.snapshot),
        )
      else:
        self._live_fastboot_serial = None
        self._live_fastboot_identity = 'Fastboot: --'
      self._refresh_live_controls()
      self._continue_inspection_to_pit_review()

    def _continue_inspection_to_pit_review(self) -> None:
      """Continue the inspect-only lane into bounded PIT review."""

      try:
        self._start_pit_command(
          build_print_pit_command_plan(),
          'Inspect-only: capturing PIT review via Heimdall print-pit…',
          self._apply_inspection_print_pit_trace,
        )
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('Inspect device PIT review', error)

    def _apply_inspection_print_pit_trace(
      self,
      trace: HeimdallNormalizedTrace,
    ) -> None:
      """Handle the print-pit stage of the inspect-only workflow."""

      inspection = build_pit_inspection(
        trace,
        detected_product_code=self._inspection_detected_product_code(),
        package_assessment=self._base_package_assessment,
      )
      if inspection.state in (
        PitInspectionState.FAILED,
        PitInspectionState.MALFORMED,
      ):
        self._append_live_log_lines(
          (
            '[INSPECTION-PIT] print-pit did not yield trustworthy partition rows; attempting metadata-only download-pit fallback.',
          )
        )
        self._start_pit_command(
          build_download_pit_command_plan(output_path='artifacts/device.pit'),
          'Inspect-only: attempting metadata-only download-pit fallback…',
          self._apply_inspection_download_pit_trace,
        )
        return
      self._base_pit_inspection = inspection
      self._finish_inspection_workflow(inspection)

    def _apply_inspection_download_pit_trace(
      self,
      trace: HeimdallNormalizedTrace,
    ) -> None:
      """Finish the inspect-only lane after metadata-only PIT fallback."""

      inspection = build_pit_inspection(
        trace,
        detected_product_code=self._inspection_detected_product_code(),
        package_assessment=self._base_package_assessment,
      )
      self._base_pit_inspection = inspection
      self._finish_inspection_workflow(inspection)

    def _inspection_detected_product_code(self) -> Optional[str]:
      """Return the best product-code hint available for PIT alignment."""

      snapshot = self._base_session.live_detection.snapshot
      if snapshot is None:
        return self._base_session.product_code
      if snapshot.product_code is not None:
        return snapshot.product_code
      if snapshot.model_name is not None:
        return snapshot.model_name
      return self._base_session.product_code

    def _finish_inspection_workflow(
      self,
      pit_inspection: Optional[PitInspection],
    ) -> None:
      """Persist the final inspect-only posture and refresh report surfaces."""

      inspection = build_inspection_workflow(
        self._base_session.live_detection,
        pit_inspection=pit_inspection,
        captured_at_utc=_utc_now(),
      )
      self._base_session = replace(
        self._base_session,
        inspection=inspection,
      )
      self._refresh_shell_view_model()
      self._append_live_log_lines(
        (
          '[INSPECTION-SUMMARY] {summary}'.format(summary=inspection.summary),
          '[INSPECTION-NEXT] {action}'.format(action=inspection.next_action),
        )
      )
      tone = 'info'
      if inspection.posture.value == 'ready':
        tone = 'success'
      elif inspection.posture.value == 'partial':
        tone = 'warning'
      elif inspection.posture.value == 'failed':
        tone = 'danger'
      self._set_live_status(inspection.summary, tone)

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
        pit_inspection=self._base_pit_inspection,
        transport_trace=self._base_transport_trace,
        boot_unhydrated=self._boot_unhydrated,
        device_surface_cleared=self._device_surface_cleared,
      )
      self._panel_titles = tuple(panel.title for panel in self._model.panels)
      self._action_labels = tuple(action.label for action in self._model.control_actions)
      self.setWindowTitle(
        'Calamum Vulcan — {phase}'.format(phase=self._model.phase_label)
      )
      self._rebuild_ui()

    def _set_live_detection(self, live_detection) -> None:
      """Persist repo-owned live detection into the immutable session snapshot."""

      self._base_session = replace(
        self._base_session,
        live_detection=live_detection,
      )
      self._device_surface_cleared = (
        live_detection.state == LiveDetectionState.CLEARED
        and live_detection.snapshot is None
      )
      self._refresh_shell_view_model()

    def _live_identity_text(self, snapshot: LiveDeviceSnapshot) -> str:
      """Return one compact device identity string for live labels."""

      detail = snapshot.product_code or snapshot.model_name or snapshot.transport
      return '{serial} ({detail})'.format(
        serial=snapshot.serial,
        detail=detail,
      )

    def _apply_adb_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
      fallback_posture: LiveFallbackPosture = LiveFallbackPosture.NOT_NEEDED,
      fallback_reason: Optional[str] = None,
      source_labels: Optional[Tuple[str, ...]] = None,
    ) -> None:
      """Apply one ADB detection trace to shell-local live state."""

      detection = build_live_detection_session(
        trace,
        fallback_posture=fallback_posture,
        fallback_reason=fallback_reason,
        source_labels=source_labels,
      )
      self._set_live_detection(detection)
      self._live_fastboot_serial = None
      self._live_fastboot_identity = 'Fastboot: --'

      if detection.snapshot is not None and detection.snapshot.command_ready:
        self._live_adb_serial = detection.snapshot.serial
        self._live_adb_identity = 'ADB: {identity}'.format(
          identity=self._live_identity_text(detection.snapshot),
        )
        if detection.snapshot.info_state == LiveDeviceInfoState.NOT_COLLECTED:
          self._refresh_live_controls()
          self._start_live_command(
            build_adb_device_info_command_plan(
              device_serial=detection.snapshot.serial,
            ),
            'Gathering live device info via ADB…',
            self._apply_adb_device_info_trace,
          )
          return
        self._set_live_status(
          '{summary} Active companion: {identity} via ADB.'.format(
            summary=detection.summary,
            identity=self._live_identity_text(detection.snapshot),
          ),
          'success',
        )
      elif detection.snapshot is not None:
        self._live_adb_serial = None
        self._live_adb_identity = 'ADB: {identity} (authorize)'.format(
          identity=self._live_identity_text(detection.snapshot),
        )
        self._set_live_status(
          '{summary} Active companion: {identity} via ADB; authorize or reconnect before reboot commands.'.format(
            summary=detection.summary,
            identity=self._live_identity_text(detection.snapshot),
          ),
          'warning',
        )
      else:
        self._live_adb_serial = None
        self._live_adb_identity = 'ADB: --'
        self._live_fastboot_serial = None
        self._live_fastboot_identity = 'Fastboot: --'
        tone = 'neutral' if detection.state == LiveDetectionState.CLEARED else 'danger'
        self._set_live_status(
          '{summary} No live ADB companion detected.'.format(
            summary=detection.summary,
          ),
          tone,
        )
      self._refresh_live_controls()

    def _apply_adb_device_info_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply one bounded ADB property trace to the active live device session."""

      if trace.command_plan.operation != AndroidToolsOperation.ADB_GETPROP:
        self._append_live_log_lines(
          (
            '[COMPANION-STALE] Ignored one stale live result while waiting for bounded ADB info capture.',
          )
        )
        self._set_live_status(
          'Ignored one stale detect result while waiting for bounded live device info.',
          'warning',
        )
        self._refresh_live_controls()
        return

      updated_detection = apply_live_device_info_trace(
        self._base_session.live_detection,
        trace,
      )
      self._set_live_detection(updated_detection)
      snapshot = updated_detection.snapshot
      if snapshot is None:
        self._set_live_status(
          'ADB device-info collection finished, but no active live device snapshot was available to enrich.',
          'danger',
        )
        self._refresh_live_controls()
        return

      self._live_adb_serial = snapshot.serial if snapshot.command_ready else None
      self._live_adb_identity = 'ADB: {identity}'.format(
        identity=self._live_identity_text(snapshot),
      )
      if snapshot.info_state == LiveDeviceInfoState.CAPTURED:
        self._set_live_status(
          'Bounded live device info captured for {identity} via ADB.'.format(
            identity=self._live_identity_text(snapshot),
          ),
          'success',
        )
      elif snapshot.info_state == LiveDeviceInfoState.PARTIAL:
        self._set_live_status(
          'Partial live device info captured for {identity}; keep support claims narrow.'.format(
            identity=self._live_identity_text(snapshot),
          ),
          'warning',
        )
      elif snapshot.info_state == LiveDeviceInfoState.FAILED:
        self._set_live_status(
          'The live device was detected, but bounded ADB device-info collection failed.',
          'warning',
        )
      else:
        self._set_live_status(
          'Live device detected, but richer ADB device info is not available yet.',
          'warning',
        )
      self._refresh_live_controls()

    def _apply_fastboot_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
      fallback_posture: LiveFallbackPosture = LiveFallbackPosture.NOT_NEEDED,
      fallback_reason: Optional[str] = None,
      source_labels: Optional[Tuple[str, ...]] = None,
    ) -> None:
      """Apply one fastboot detection trace to shell-local live state."""

      detection = build_live_detection_session(
        trace,
        fallback_posture=fallback_posture,
        fallback_reason=fallback_reason,
        source_labels=source_labels,
      )
      self._set_live_detection(detection)
      self._live_adb_serial = None
      self._live_adb_identity = 'ADB: --'

      if detection.snapshot is not None:
        self._live_fastboot_serial = detection.snapshot.serial
        self._live_fastboot_identity = 'Fastboot: {identity}'.format(
          identity=self._live_identity_text(detection.snapshot),
        )
        self._set_live_status(
          '{summary} Active companion: {identity} via Fastboot.'.format(
            summary=detection.summary,
            identity=self._live_identity_text(detection.snapshot),
          ),
          'success' if detection.snapshot.command_ready else 'warning',
        )
      else:
        self._live_fastboot_serial = None
        self._live_fastboot_identity = 'Fastboot: --'
        tone = 'neutral' if detection.state == LiveDetectionState.CLEARED else 'danger'
        self._set_live_status(
          '{summary} No live fastboot companion detected.'.format(
            summary=detection.summary,
          ),
          tone,
        )
      self._refresh_live_controls()

    def _apply_unified_adb_detection_trace(
      self,
      trace: AndroidToolsNormalizedTrace,
    ) -> None:
      """Apply the unified detect flow after the initial ADB probe."""

      if trace.detected_devices:
        self._apply_adb_detection_trace(trace)
        return

      detection = build_live_detection_session(
        trace,
        fallback_posture=LiveFallbackPosture.NEEDED,
        fallback_reason=(
          'ADB did not establish a live device; fastboot fallback will be checked next.'
        ),
        source_labels=('adb', 'fastboot'),
      )
      self._set_live_detection(detection)
      self._live_adb_serial = None
      self._live_fastboot_serial = None
      self._live_fastboot_identity = 'Fastboot: --'
      if trace.state == AndroidToolsTraceState.FAILED:
        self._live_adb_identity = 'ADB: probe failed; checking fastboot.'
        pending_text = 'ADB probe failed. Checking fastboot…'
      else:
        self._live_adb_identity = 'ADB: --'
        pending_text = 'ADB did not find a live device. Checking fastboot…'
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
        self._apply_fastboot_detection_trace(
          trace,
          fallback_posture=LiveFallbackPosture.ENGAGED,
          fallback_reason=(
            'ADB did not establish a live device; fastboot captured the active companion.'
          ),
          source_labels=('adb', 'fastboot'),
        )
        return

      detection = build_live_detection_session(
        trace,
        fallback_posture=LiveFallbackPosture.ENGAGED,
        fallback_reason=(
          'ADB did not establish a live device; fastboot fallback also failed to capture a live companion.'
        ),
        source_labels=('adb', 'fastboot'),
      )
      self._set_live_detection(detection)
      self._live_adb_serial = None
      self._live_adb_identity = 'ADB: --'
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
      self._refresh_live_controls()

    def _handle_adb_reboot(self) -> None:
      """Issue one live ADB reboot command to the selected target mode."""

      try:
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
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('ADB reboot', error)

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

      try:
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
      except Exception as error:  # pragma: no cover - defensive GUI guardrail
        self._handle_live_action_exception('Fastboot reboot', error)

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

    def _live_command_thread_running(self) -> bool:
      """Return whether one live companion worker thread is still active."""

      retained_threads = [
        retained[0] for retained in self._retained_live_command_objects
      ] + [
        retained[0] for retained in self._retained_pit_command_objects
      ]
      for thread in retained_threads + [
        self._live_command_thread,
        self._pit_command_thread,
      ]:
        if thread is None:
          continue
        is_running = getattr(thread, 'isRunning', None)
        if not callable(is_running):
          continue
        try:
          if bool(is_running()):
            return True
        except RuntimeError:
          continue
      return False

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
      """Restore any temporary busy cursor state before the window closes."""

      if self._live_command_thread_running():
        message = (
          'Wait for the current live companion action to finish before closing the GUI.'
        )
        self._append_live_log_lines(
          ('[COMPANION-WAIT] {message}'.format(message=message),)
        )
        self._set_live_status(message, 'warning')
        event.ignore()
        return
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
      if trace.observed_properties:
        lines.append(
          '[COMPANION-INFO] manufacturer={manufacturer} android={android} build={build} security_patch={patch}'.format(
            manufacturer=trace.observed_properties.get('ro.product.manufacturer', 'unknown'),
            android=trace.observed_properties.get('ro.build.version.release', 'unknown'),
            build=trace.observed_properties.get('ro.build.id', 'unknown'),
            patch=trace.observed_properties.get('ro.build.version.security_patch', 'unknown'),
          )
        )
      for note in trace.notes:
        lines.append('[COMPANION-NOTE] {note}'.format(note=note))
      return tuple(lines)

    def _render_pit_trace_lines(
      self,
      trace: HeimdallNormalizedTrace,
    ) -> Tuple[str, ...]:
      """Render one bounded PIT trace into operational-log lines."""

      lines = [
        '[INSPECTION-PIT] {command}'.format(
          command=trace.command_plan.display_command,
        ),
        '[INSPECTION-PIT-RESULT] state={state} exit={exit_code} summary={summary}'.format(
          state=trace.state.value,
          exit_code=trace.exit_code,
          summary=trace.summary,
        ),
      ]
      for note in trace.notes[:2]:
        lines.append('[INSPECTION-PIT-NOTE] {note}'.format(note=note))
      return tuple(lines)

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
    watchdog = _GuiHangWatchdog(
      scenario_name=model.scenario_name,
      phase_label=model.phase_label,
    )
    watchdog.mark('application_created')
    heartbeat_timer = QtCore.QTimer(application)
    heartbeat_timer.setInterval(GUI_EVENT_LOOP_HEARTBEAT_MS)
    heartbeat_timer.timeout.connect(lambda: watchdog.mark('event_loop_tick'))
    try:
      window = ShellWindow(model)
      watchdog.mark('window_constructed')
      window.show()
      watchdog.mark('window_shown')
      heartbeat_timer.start()
      if duration_ms > 0:
        QtCore.QTimer.singleShot(duration_ms, application.quit)
      exit_code = application.exec()
      watchdog.mark('application_exec_returned')
      return exit_code
    finally:
      if heartbeat_timer.isActive():
        heartbeat_timer.stop()
      watchdog.stop()