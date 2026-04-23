"""Optional Qt 6 runtime detection for the Calamum Vulcan shell."""

from __future__ import annotations

import logging

from ..runtime_dependencies import attempt_runtime_dependency_repair


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
  attempt_runtime_dependency_repair(logging.getLogger('vulcan.runtime'))
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
    'Qt 6 shell runtime is unavailable because the declared Calamum '
    'Vulcan runtime dependency set is still incomplete in the active '
    'environment. Reinstall Calamum Vulcan in that environment so the '
    'full dependency set, including PySide6, is restored.'
  )