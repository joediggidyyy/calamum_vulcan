"""Optional Qt 6 runtime detection for the Calamum Vulcan shell."""

from __future__ import annotations


QT_AVAILABLE = False
QT_API = 'unavailable'
QtCore = None
QtGui = None
QtWidgets = None

try:
  from PySide6 import QtCore as _QtCore
  from PySide6 import QtGui as _QtGui
  from PySide6 import QtWidgets as _QtWidgets

  QtCore = _QtCore
  QtGui = _QtGui
  QtWidgets = _QtWidgets
  QT_AVAILABLE = True
  QT_API = 'PySide6'
except ImportError:
  QT_AVAILABLE = False
  QT_API = 'unavailable'


def runtime_requirement_message() -> str:
  """Return the operator-facing guidance for a missing Qt runtime."""

  return (
    'Qt 6 shell runtime is unavailable. Install PySide6 in the active '
    'environment to launch the Calamum Vulcan desktop shell.'
  )