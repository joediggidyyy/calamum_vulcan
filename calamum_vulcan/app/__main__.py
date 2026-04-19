"""CLI entry point for the Calamum Vulcan FS-03 shell sandbox."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Optional
from typing import Sequence

from ..adapters.adb_fastboot import AndroidToolsCommandPlan
from ..adapters.adb_fastboot import AndroidToolsNormalizedTrace
from ..adapters.adb_fastboot import available_adb_reboot_targets
from ..adapters.adb_fastboot import available_fastboot_reboot_targets
from ..adapters.adb_fastboot import build_adb_detect_command_plan
from ..adapters.adb_fastboot import build_adb_reboot_command_plan
from ..adapters.adb_fastboot import build_fastboot_detect_command_plan
from ..adapters.adb_fastboot import build_fastboot_reboot_command_plan
from ..adapters.adb_fastboot import execute_android_tools_command
from .demo import available_scenarios
from .demo import available_adapter_fixtures
from .demo import available_transport_sources
from .demo import build_demo_adapter_session
from .demo import build_demo_package_assessment
from .demo import build_demo_session
from .demo import scenario_label
from .integration import available_integration_suites
from .integration import build_sprint_close_bundle
from .integration import render_sprint_close_bundle_markdown
from .integration import serialize_sprint_close_bundle_json
from .integration import write_sprint_close_bundle
from ..domain.reporting import REPORT_EXPORT_TARGETS
from ..domain.reporting import build_session_evidence_report
from ..domain.reporting import render_session_evidence_markdown
from ..domain.reporting import serialize_session_evidence_json
from ..domain.reporting import write_session_evidence_report
from ..fixtures import available_package_manifest_fixtures
from .qt_compat import QT_AVAILABLE
from .qt_compat import QtWidgets
from .qt_compat import runtime_requirement_message
from .qt_shell import launch_shell
from .view_models import build_shell_view_model
from .view_models import describe_shell


GUI_STARTUP_LOG_PATH = Path(tempfile.gettempdir()) / 'calamum_vulcan_gui_startup.log'


class _GuiStartupStream(io.TextIOBase):
  """Append-only text stream used when the GUI launcher has no console."""

  encoding = 'utf-8'

  def __init__(self, log_path: Path) -> None:
    super().__init__()
    self._log_path = log_path

  def writable(self) -> bool:
    return True

  def isatty(self) -> bool:
    return False

  def write(self, text: str) -> int:
    if not text:
      return 0
    self._log_path.parent.mkdir(parents=True, exist_ok=True)
    with self._log_path.open('a', encoding='utf-8') as handle:
      handle.write(text)
    return len(text)

  def flush(self) -> None:
    return None


def _has_writable_stream(stream: object) -> bool:
  """Return whether the provided stream can accept text output."""

  return hasattr(stream, 'write') and callable(getattr(stream, 'write'))


def _show_gui_launch_error(message: str) -> None:
  """Show a GUI-facing startup error message when Qt is available."""

  if not QT_AVAILABLE or QtWidgets is None:
    return
  application = QtWidgets.QApplication.instance()
  owns_application = False
  if application is None:
    application = QtWidgets.QApplication([])
    owns_application = True
  QtWidgets.QMessageBox.critical(
    None,
    'Calamum Vulcan launch failed',
    message,
  )
  if owns_application:
    application.quit()


def gui_main(argv: Optional[Sequence[str]] = None) -> int:
  """Run the GUI launcher safely even when Windows provides no console streams."""

  original_stdout = sys.stdout
  original_stderr = sys.stderr
  startup_stream = _GuiStartupStream(GUI_STARTUP_LOG_PATH)

  if not _has_writable_stream(sys.stdout):
    sys.stdout = startup_stream
  if not _has_writable_stream(sys.stderr):
    sys.stderr = startup_stream

  try:
    return main(argv)
  except SystemExit as exit_signal:
    exit_code = exit_signal.code
    if exit_code in (None, 0):
      return 0
    message = str(exit_code)
    startup_stream.write(message + '\n')
    _show_gui_launch_error(
      message + '\n\nStartup details were written to:\n' + str(GUI_STARTUP_LOG_PATH)
    )
    if isinstance(exit_code, int):
      return exit_code
    return 1
  except Exception:
    traceback.print_exc(file=startup_stream)
    _show_gui_launch_error(
      'Calamum Vulcan could not finish launching.\n\n'
      'Startup details were written to:\n{path}'.format(
        path=GUI_STARTUP_LOG_PATH,
      )
    )
    return 1
  finally:
    sys.stdout = original_stdout
    sys.stderr = original_stderr


def main(argv: Optional[Sequence[str]] = None) -> int:
  """Run the FS-03 shell sandbox from one named fixture scenario."""

  parser = argparse.ArgumentParser(
    description='Launch the Calamum Vulcan Sprint 0.1.0 GUI shell.'
  )
  parser.add_argument(
    '--scenario',
    choices=available_scenarios(),
    default='ready',
    help='Fixture scenario to bind into the GUI shell.',
  )
  parser.add_argument(
    '--duration-ms',
    type=int,
    default=0,
    help='Optional auto-close duration for offscreen sandbox runs.',
  )
  parser.add_argument(
    '--adb-detect',
    action='store_true',
    help='Probe live adb-connected devices using `adb devices -l`.',
  )
  parser.add_argument(
    '--fastboot-detect',
    action='store_true',
    help='Probe live fastboot-connected devices using `fastboot devices`.',
  )
  parser.add_argument(
    '--adb-reboot',
    choices=available_adb_reboot_targets(),
    default=None,
    help='Issue a live adb reboot command to the selected target mode.',
  )
  parser.add_argument(
    '--fastboot-reboot',
    choices=available_fastboot_reboot_targets(),
    default=None,
    help='Issue a live fastboot reboot command to the selected target mode.',
  )
  parser.add_argument(
    '--device-serial',
    default=None,
    help='Optional serial selector for live adb/fastboot control commands.',
  )
  parser.add_argument(
    '--control-format',
    choices=('text', 'json'),
    default='text',
    help='Choose how live adb/fastboot command plans and results should be rendered.',
  )
  parser.add_argument(
    '--describe-only',
    action='store_true',
    help='Print the shell summary without launching Qt.',
  )
  parser.add_argument(
    '--package-fixture',
    choices=('scenario-default',) + available_package_manifest_fixtures(),
    default='scenario-default',
    help='Optional public package fixture override for shell review.',
  )
  parser.add_argument(
    '--transport-source',
    choices=available_transport_sources(),
    default='state-fixture',
    help='Choose direct state fixtures or the FS-07 Heimdall adapter seam.',
  )
  parser.add_argument(
    '--adapter-fixture',
    choices=('scenario-default',) + available_adapter_fixtures(),
    default='scenario-default',
    help='Optional Heimdall process fixture override for adapter-backed scenarios.',
  )
  parser.add_argument(
    '--integration-suite',
    choices=available_integration_suites(),
    default=None,
    help='Run the FS-08 integrated sprint-close bundle instead of one scenario.',
  )
  parser.add_argument(
    '--suite-format',
    choices=REPORT_EXPORT_TARGETS,
    default='markdown',
    help='Choose how the FS-08 integrated bundle should be rendered.',
  )
  parser.add_argument(
    '--suite-output',
    default=None,
    help='Optional path to write the FS-08 integrated bundle.',
  )
  parser.add_argument(
    '--export-evidence',
    action='store_true',
    help='Render the FS-06 session evidence bundle to stdout or a file.',
  )
  parser.add_argument(
    '--evidence-format',
    choices=REPORT_EXPORT_TARGETS,
    default='markdown',
    help='Choose how the session evidence bundle should be rendered.',
  )
  parser.add_argument(
    '--evidence-output',
    default=None,
    help='Optional path to write the rendered evidence bundle.',
  )
  parser.add_argument(
    '--captured-at-utc',
    default=None,
    help='Optional fixed UTC timestamp for deterministic evidence and bundle generation.',
  )
  args = parser.parse_args(argv)

  control_plan = _build_live_control_plan(args)
  if control_plan is not None:
    print(_render_control_plan(control_plan, args.control_format))
    if args.describe_only:
      return 0
    trace = execute_android_tools_command(control_plan)
    print(_render_control_trace(trace, args.control_format))
    return 0

  if args.integration_suite == 'sprint-close':
    bundle = build_sprint_close_bundle(captured_at_utc=args.captured_at_utc)
    if args.suite_output:
      output_path = write_sprint_close_bundle(
        bundle,
        Path(args.suite_output),
        format_name=args.suite_format,
      )
      print(
        'bundle_written="{path}" format="{format_name}"'.format(
          path=output_path,
          format_name=args.suite_format,
        )
      )
    elif args.suite_format == 'json':
      print(serialize_sprint_close_bundle_json(bundle))
    else:
      print(render_sprint_close_bundle_markdown(bundle))
    return 0

  scenario = scenario_label(args.scenario)
  transport_trace = None
  if args.transport_source == 'heimdall-adapter':
    session, package_assessment, transport_trace = build_demo_adapter_session(
      args.scenario,
      package_fixture_name=args.package_fixture,
      adapter_fixture_name=args.adapter_fixture,
    )
  else:
    session = build_demo_session(args.scenario)
    package_assessment = None
    if session.guards.package_loaded or args.package_fixture != 'scenario-default':
      package_assessment = build_demo_package_assessment(
        args.scenario,
        session=session,
        package_fixture_name=args.package_fixture,
      )
  session_report = build_session_evidence_report(
    session,
    scenario_name=scenario,
    package_assessment=package_assessment,
    transport_trace=transport_trace,
    captured_at_utc=args.captured_at_utc,
  )
  model = build_shell_view_model(
    session,
    scenario_name=scenario,
    package_assessment=package_assessment,
    transport_trace=transport_trace,
    session_report=session_report,
  )
  print(describe_shell(model))

  if args.export_evidence or args.evidence_output:
    if args.evidence_output:
      output_path = write_session_evidence_report(
        session_report,
        Path(args.evidence_output),
        format_name=args.evidence_format,
      )
      print(
        'evidence_written="{path}" format="{format_name}"'.format(
          path=output_path,
          format_name=args.evidence_format,
        )
      )
    elif args.evidence_format == 'json':
      print(serialize_session_evidence_json(session_report))
    else:
      print(render_session_evidence_markdown(session_report))

  if args.describe_only:
    return 0
  if not QT_AVAILABLE:
    raise SystemExit(runtime_requirement_message())
  return launch_shell(model, duration_ms=args.duration_ms)


def _build_live_control_plan(args: argparse.Namespace) -> Optional[AndroidToolsCommandPlan]:
  """Return one bounded live-control command plan when requested."""

  requested = [
    bool(args.adb_detect),
    bool(args.fastboot_detect),
    args.adb_reboot is not None,
    args.fastboot_reboot is not None,
  ]
  if sum(1 for item in requested if item) > 1:
    raise SystemExit(
      'Select only one live companion action at a time: '
      '--adb-detect, --fastboot-detect, --adb-reboot, or --fastboot-reboot.'
    )
  if args.adb_detect:
    return build_adb_detect_command_plan(device_serial=args.device_serial)
  if args.fastboot_detect:
    return build_fastboot_detect_command_plan(device_serial=args.device_serial)
  if args.adb_reboot is not None:
    return build_adb_reboot_command_plan(
      args.adb_reboot,
      device_serial=args.device_serial,
    )
  if args.fastboot_reboot is not None:
    return build_fastboot_reboot_command_plan(
      args.fastboot_reboot,
      device_serial=args.device_serial,
    )
  return None


def _render_control_plan(
  command_plan: AndroidToolsCommandPlan,
  format_name: str,
) -> str:
  """Render one live-control plan for operator review."""

  if format_name == 'json':
    return json.dumps(command_plan.to_dict(), indent=2, sort_keys=True)

  lines = [
    'control_plan backend="{backend}" capability="{capability}" command="{command}" vendor_specific="{vendor}"'.format(
      backend=command_plan.backend.value,
      capability=command_plan.capability.value,
      command=command_plan.display_command,
      vendor='yes' if command_plan.vendor_specific else 'no',
    )
  ]
  if command_plan.reboot_target is not None:
    lines.append('control_target="{target}"'.format(
      target=command_plan.reboot_target,
    ))
  for note in command_plan.notes:
    lines.append('control_note="{note}"'.format(note=note))
  return '\n'.join(lines)


def _render_control_trace(
  trace: AndroidToolsNormalizedTrace,
  format_name: str,
) -> str:
  """Render one live-control result for operator review."""

  if format_name == 'json':
    return json.dumps(trace.to_dict(), indent=2, sort_keys=True)

  lines = [
    'control_result state="{state}" exit_code="{exit_code}" summary="{summary}"'.format(
      state=trace.state.value,
      exit_code=trace.exit_code,
      summary=trace.summary,
    )
  ]
  for device in trace.detected_devices:
    lines.append(
      'device serial="{serial}" state="{state}" transport="{transport}" product="{product}" model="{model}"'.format(
        serial=device.serial,
        state=device.state,
        transport=device.transport,
        product=device.product or 'unknown',
        model=device.model or 'unknown',
      )
    )
  for note in trace.notes:
    lines.append('control_note="{note}"'.format(note=note))
  return '\n'.join(lines)


if __name__ == '__main__':
  raise SystemExit(main())