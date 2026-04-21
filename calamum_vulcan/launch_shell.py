"""Script entry point for launching the Calamum Vulcan shell sandbox."""

from __future__ import annotations

import atexit
from datetime import datetime
from datetime import timezone
import faulthandler
import sys
from pathlib import Path
import tempfile
import threading
import traceback


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from calamum_vulcan.app.__main__ import gui_main


GUI_RUNTIME_LOG_PATH = Path(tempfile.gettempdir()) / 'calamum_vulcan_gui_runtime.log'
_GUI_RUNTIME_STREAM = None
_ORIGINAL_SYS_EXCEPTHOOK = sys.excepthook
_ORIGINAL_THREADING_EXCEPTHOOK = getattr(threading, 'excepthook', None)
_ORIGINAL_UNRAISABLEHOOK = getattr(sys, 'unraisablehook', None)


def _ensure_gui_runtime_stream():
  """Return the append-only runtime diagnostic stream for detached GUI hosts."""

  global _GUI_RUNTIME_STREAM
  if _GUI_RUNTIME_STREAM is not None and not _GUI_RUNTIME_STREAM.closed:
    return _GUI_RUNTIME_STREAM
  GUI_RUNTIME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  _GUI_RUNTIME_STREAM = GUI_RUNTIME_LOG_PATH.open('a', encoding='utf-8')
  return _GUI_RUNTIME_STREAM


def _append_gui_runtime_diagnostic(
  context: str,
  error_type,
  error_value,
  error_traceback,
) -> None:
  """Append one detached-host diagnostic traceback to the runtime log."""

  stream = _ensure_gui_runtime_stream()
  if stream is None:
    return
  stream.write(
    '[{timestamp}] {context}\n'.format(
      timestamp=datetime.now(timezone.utc).isoformat(),
      context=context,
    )
  )
  traceback.print_exception(
    error_type,
    error_value,
    error_traceback,
    file=stream,
  )
  stream.write('\n')
  stream.flush()


def _close_gui_runtime_stream() -> None:
  """Flush and close the detached-host runtime stream when the process exits."""

  global _GUI_RUNTIME_STREAM
  if _GUI_RUNTIME_STREAM is None:
    return
  try:
    _GUI_RUNTIME_STREAM.flush()
    _GUI_RUNTIME_STREAM.close()
  finally:
    _GUI_RUNTIME_STREAM = None


def _install_gui_host_diagnostics() -> None:
  """Install runtime hooks so detached GUI host failures leave evidence."""

  stream = _ensure_gui_runtime_stream()
  try:
    faulthandler.enable(file=stream, all_threads=True)
  except Exception:
    pass

  def _gui_sys_excepthook(error_type, error_value, error_traceback) -> None:
    _append_gui_runtime_diagnostic(
      'GUI host uncaught exception',
      error_type,
      error_value,
      error_traceback,
    )
    try:
      _ORIGINAL_SYS_EXCEPTHOOK(error_type, error_value, error_traceback)
    except Exception:
      return

  def _gui_thread_excepthook(args) -> None:
    _append_gui_runtime_diagnostic(
      'GUI host uncaught thread exception',
      args.exc_type,
      args.exc_value,
      args.exc_traceback,
    )
    if _ORIGINAL_THREADING_EXCEPTHOOK is None:
      return
    try:
      _ORIGINAL_THREADING_EXCEPTHOOK(args)
    except Exception:
      return

  def _gui_unraisablehook(args) -> None:
    object_repr = repr(args.object) if getattr(args, 'object', None) is not None else 'unknown'
    _append_gui_runtime_diagnostic(
      'GUI host unraisable exception ({object_repr})'.format(object_repr=object_repr),
      args.exc_type,
      args.exc_value,
      args.exc_traceback,
    )
    if _ORIGINAL_UNRAISABLEHOOK is None:
      return
    try:
      _ORIGINAL_UNRAISABLEHOOK(args)
    except Exception:
      return

  sys.excepthook = _gui_sys_excepthook
  if _ORIGINAL_THREADING_EXCEPTHOOK is not None:
    threading.excepthook = _gui_thread_excepthook
  if _ORIGINAL_UNRAISABLEHOOK is not None:
    sys.unraisablehook = _gui_unraisablehook


atexit.register(_close_gui_runtime_stream)


if __name__ == '__main__':
  _install_gui_host_diagnostics()
  try:
    raise SystemExit(gui_main(sys.argv[1:]))
  except SystemExit:
    raise
  except BaseException as error:
    _append_gui_runtime_diagnostic(
      'GUI host top-level exception',
      type(error),
      error,
      error.__traceback__,
    )
    raise