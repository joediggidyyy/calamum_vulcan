"""CLI entry point for the Calamum Vulcan FS-03 shell sandbox."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from dataclasses import replace
from datetime import datetime
from datetime import timezone
import io
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import traceback
from typing import Optional
from typing import Sequence

from ..adapters.adb_fastboot import AndroidToolsCommandPlan
from ..adapters.adb_fastboot import AndroidToolsNormalizedTrace
from ..adapters.adb_fastboot import AndroidToolsOperation
from ..adapters.adb_fastboot import available_adb_reboot_targets
from ..adapters.adb_fastboot import available_fastboot_reboot_targets
from ..adapters.adb_fastboot import build_adb_detect_command_plan
from ..adapters.adb_fastboot import build_adb_device_info_command_plan
from ..adapters.adb_fastboot import build_adb_reboot_command_plan
from ..adapters.adb_fastboot import build_fastboot_detect_command_plan
from ..adapters.adb_fastboot import build_fastboot_reboot_command_plan
from ..adapters.adb_fastboot import execute_android_tools_command
from ..adapters.heimdall import build_download_pit_command_plan
from ..adapters.heimdall import build_print_pit_command_plan
from ..adapters.heimdall import run_bounded_heimdall_flash_session
from .demo import available_scenarios
from .demo import available_adapter_fixtures
from .demo import build_demo_pit_inspection
from .demo import available_transport_sources
from .demo import build_demo_adapter_session
from .demo import build_demo_integrated_runtime_session
from .demo import build_demo_package_assessment
from .demo import build_demo_safe_path_runtime_context
from .demo import build_demo_session
from .demo import scenario_label
from .integration import available_integration_suites
from .integration import build_autonomy_close_bundle
from .integration import build_orchestration_close_bundle
from .integration import build_read_side_close_bundle
from .integration import build_safe_path_close_bundle
from .integration import build_sprint_close_bundle
from .integration import render_sprint_close_bundle_markdown
from .integration import serialize_sprint_close_bundle_json
from .integration import write_sprint_close_bundle
from ..domain.live_device import LiveFallbackPosture
from ..domain.live_device import LiveDeviceSource
from ..domain.live_device import apply_live_device_info_trace
from ..domain.live_device import build_live_detection_session
from ..domain.live_device import build_usb_live_detection_session
from ..domain.flash_plan import build_reviewed_flash_plan
from ..domain.package import PackageArchiveImportError
from ..domain.package import assess_package_archive
from ..domain.pit import PitInspectionState
from ..domain.pit import build_pit_inspection
from ..domain.reporting import REPORT_EXPORT_TARGETS
from ..domain.reporting import build_session_evidence_report
from ..domain.reporting import render_session_evidence_markdown
from ..domain.reporting import serialize_session_evidence_json
from ..domain.reporting import write_session_evidence_report
from ..domain.state import build_inspection_workflow
from ..domain.state import RuntimeSessionRejected
from ..domain.state.integrated_runtime import INTEGRATED_RUNTIME_BACKEND
from ..domain.state.integrated_runtime import build_integrated_reviewed_flash_plan
from ..domain.state.integrated_runtime import execute_integrated_command
from ..domain.state.integrated_runtime import run_integrated_flash_session
from ..fixtures import available_package_manifest_fixtures
from .qt_compat import QT_AVAILABLE
from .qt_compat import QtWidgets
from .qt_compat import runtime_requirement_message
from .qt_shell import launch_shell
from ..usb import VulcanUSBScanner
from .view_models import build_shell_view_model
from .view_models import describe_shell


GUI_STARTUP_LOG_PATH = Path(tempfile.gettempdir()) / 'calamum_vulcan_gui_startup.log'
APPLICATION_DISPLAY_NAME = 'Calamum Vulcan'
PACKAGE_DISTRIBUTION_NAME = 'calamum_vulcan'
GUI_TERMINAL_BRAND_TITLE = APPLICATION_DISPLAY_NAME + ' GUI'
GUI_HOST_PROCESS_FLAG = '--gui-host-process'
VERSION_FLAG_NAMES = frozenset(('-v', '--version'))
HELP_FLAG_NAMES = frozenset(('-h', '--help'))
INFORMATIONAL_FLAG_NAMES = VERSION_FLAG_NAMES | HELP_FLAG_NAMES
DEFAULT_GUI_BOOT_ARGS = ('--scenario', 'no-device', '--boot-unhydrated')
ANSI_RESET = '\x1b[0m'
ANSI_BRAND_BLUE = '\x1b[96m'
INTEGRATED_RUNTIME_REVIEW_SCENARIOS = frozenset(('happy', 'failure', 'resume'))


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


def _show_gui_launch_information(title: str, message: str) -> None:
  """Show a GUI-facing informational message when no console is available."""

  if not QT_AVAILABLE or QtWidgets is None:
    return
  application = QtWidgets.QApplication.instance()
  owns_application = False
  if application is None:
    application = QtWidgets.QApplication([])
    owns_application = True
  QtWidgets.QMessageBox.information(
    None,
    title,
    message,
  )
  if owns_application:
    application.quit()


def _fallback_project_version() -> str:
  """Return the repository version when distribution metadata is unavailable."""

  pyproject_path = Path(__file__).resolve().parents[2] / 'pyproject.toml'
  try:
    project_data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
  except (OSError, tomllib.TOMLDecodeError):
    return 'unknown'
  project_table = project_data.get('project', {})
  return str(project_table.get('version', 'unknown'))


def _application_version() -> str:
  """Return the installed package version or a source-tree fallback."""

  fallback_version = _fallback_project_version()
  try:
    installed_version = metadata.version(PACKAGE_DISTRIBUTION_NAME)
  except metadata.PackageNotFoundError:
    return fallback_version
  if fallback_version != 'unknown':
    return fallback_version
  return installed_version


def _build_argument_parser() -> argparse.ArgumentParser:
  """Create the Calamum Vulcan command-line parser."""

  parser = argparse.ArgumentParser(
    description='Launch the Calamum Vulcan GUI shell.'
  )
  parser.add_argument(
    '-v',
    '--version',
    action='version',
    version='{name} {version}'.format(
      name=APPLICATION_DISPLAY_NAME,
      version=_application_version(),
    ),
    help='Show the installed Calamum Vulcan version and exit.',
  )
  return parser


def _argv_requests_informational_output(
  argv: Optional[Sequence[str]],
) -> bool:
  """Return whether the requested GUI invocation only needs informational text."""

  if argv is None:
    return False
  return any(argument in INFORMATIONAL_FLAG_NAMES for argument in argv)


def _informational_output_title(argv: Optional[Sequence[str]]) -> str:
  """Return the most useful GUI title for captured help or version text."""

  if argv is not None and any(argument in VERSION_FLAG_NAMES for argument in argv):
    return APPLICATION_DISPLAY_NAME + ' version'
  return APPLICATION_DISPLAY_NAME + ' help'


def _surface_gui_informational_output(
  capture_stream: Optional[io.StringIO],
  startup_stream: _GuiStartupStream,
  argv: Optional[Sequence[str]],
) -> None:
  """Display captured help or version text for GUI entrypoint invocations."""

  if capture_stream is None:
    return
  message = capture_stream.getvalue().strip()
  if not message:
    return
  startup_stream.write(message + '\n')
  _show_gui_launch_information(_informational_output_title(argv), message)


def gui_main(argv: Optional[Sequence[str]] = None) -> int:
  """Run the GUI launcher safely even when Windows provides no console streams."""

  normalized_argv = _normalized_gui_argv(argv)
  original_stdout = sys.stdout
  original_stderr = sys.stderr
  startup_stream = _GuiStartupStream(GUI_STARTUP_LOG_PATH)
  capture_stream: Optional[io.StringIO] = None
  needs_informational_capture = _argv_requests_informational_output(normalized_argv)

  if needs_informational_capture and (
    not _has_writable_stream(sys.stdout) or not _has_writable_stream(sys.stderr)
  ):
    capture_stream = io.StringIO()
    sys.stdout = capture_stream
    sys.stderr = capture_stream
  else:
    if not _has_writable_stream(sys.stdout):
      sys.stdout = startup_stream
    if not _has_writable_stream(sys.stderr):
      sys.stderr = startup_stream

  try:
    return main(normalized_argv)
  except SystemExit as exit_signal:
    exit_code = exit_signal.code
    if exit_code in (None, 0):
      _surface_gui_informational_output(
        capture_stream,
        startup_stream,
        normalized_argv,
      )
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

  effective_argv = tuple(sys.argv[1:] if argv is None else argv)
  parser = _build_argument_parser()
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
    '--inspect-device',
    action='store_true',
    help='Run the inspect-only workflow: live detect/info plus PIT review with exportable read-side evidence.',
  )
  parser.add_argument(
    '--execute-flash-plan',
    action='store_true',
    help='Run the platform-supervised bounded safe-path flash lane. Use --transport-source integrated-runtime for the Sprint 6 supported path, or --transport-source heimdall-adapter for the explicit historical fallback lane.',
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
    help='Choose how live companion and inspect-only command results should be rendered.',
  )
  parser.add_argument(
    '--pit-output-path',
    default='artifacts/device.pit',
    help='Fallback output path when inspect-only PIT review uses metadata-only download-pit capture.',
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
    '--package-archive',
    default=None,
    help='Optional real package zip archive to ingest and checksum-verify for shell review.',
  )
  parser.add_argument(
    '--transport-source',
    choices=available_transport_sources(),
    default='state-fixture',
    help='Choose fixture review (state-fixture), the Sprint 6 supported-path runtime (integrated-runtime), or the historical Heimdall adapter seam (heimdall-adapter).',
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
    help='Run one integrated closeout bundle instead of one scenario.',
  )
  parser.add_argument(
    '--suite-format',
    choices=REPORT_EXPORT_TARGETS,
    default='markdown',
    help='Choose how the integrated closeout bundle should be rendered.',
  )
  parser.add_argument(
    '--suite-output',
    default=None,
    help='Optional path to write the integrated closeout bundle.',
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
  parser.add_argument(
    '--boot-unhydrated',
    action='store_true',
    help=argparse.SUPPRESS,
  )
  parser.add_argument(
    GUI_HOST_PROCESS_FLAG,
    action='store_true',
    help=argparse.SUPPRESS,
  )
  args = parser.parse_args(effective_argv)

  control_plan = _build_live_control_plan(args)
  if control_plan is not None:
    print(_render_control_plan(control_plan, args.control_format))
    if args.describe_only:
      return 0
    trace = execute_android_tools_command(control_plan)
    live_detection = _enrich_live_detection_for_control_trace(trace)
    print(_render_control_trace(trace, args.control_format, live_detection=live_detection))
    return 0

  _validate_transport_source_selection(args)

  if args.inspect_device:
    _validate_inspection_inputs(args)
    inspection_report = _run_inspect_only_workflow(
      args,
      scenario_label(args.scenario),
    )
    print(_render_inspection_result(inspection_report, args.control_format))
    if args.evidence_output:
      output_path = write_session_evidence_report(
        inspection_report,
        Path(args.evidence_output),
        format_name=args.evidence_format,
      )
      print(
        'evidence_written="{path}" format="{format_name}"'.format(
          path=output_path,
          format_name=args.evidence_format,
        )
      )
    elif args.export_evidence:
      if args.evidence_format == 'json':
        print(serialize_session_evidence_json(inspection_report))
      else:
        print(render_session_evidence_markdown(inspection_report))
    return 0

  if args.execute_flash_plan:
    _validate_execution_inputs(args)
    execution_report, execution_rejected, transport_trace = _run_execute_flash_plan_workflow(
      args,
      scenario_label(args.scenario),
    )
    print(
      _render_execute_result(
        execution_report,
        execution_rejected,
        args.control_format,
      )
    )
    if args.evidence_output:
      output_path = write_session_evidence_report(
        execution_report,
        Path(args.evidence_output),
        format_name=args.evidence_format,
        transport_trace=transport_trace,
      )
      print(
        'evidence_written="{path}" format="{format_name}"'.format(
          path=output_path,
          format_name=args.evidence_format,
        )
      )
    elif args.export_evidence:
      if args.evidence_format == 'json':
        print(serialize_session_evidence_json(execution_report))
      else:
        print(render_session_evidence_markdown(execution_report))
    return 0

  bundle = None
  if args.integration_suite == 'sprint-close':
    bundle = build_sprint_close_bundle(captured_at_utc=args.captured_at_utc)
  elif args.integration_suite == 'orchestration-close':
    bundle = build_orchestration_close_bundle(captured_at_utc=args.captured_at_utc)
  elif args.integration_suite == 'read-side-close':
    bundle = build_read_side_close_bundle(captured_at_utc=args.captured_at_utc)
  elif args.integration_suite == 'safe-path-close':
    bundle = build_safe_path_close_bundle(captured_at_utc=args.captured_at_utc)
  elif args.integration_suite == 'autonomy-close':
    bundle = build_autonomy_close_bundle(captured_at_utc=args.captured_at_utc)
  if bundle is not None:
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
  _validate_package_inputs(args)
  transport_trace = None
  transport_backend = 'heimdall'
  if args.transport_source == 'heimdall-adapter':
    session, package_assessment, transport_trace = build_demo_adapter_session(
      args.scenario,
      package_fixture_name=args.package_fixture,
      adapter_fixture_name=args.adapter_fixture,
    )
  else:
    if args.transport_source == INTEGRATED_RUNTIME_BACKEND:
      transport_backend = INTEGRATED_RUNTIME_BACKEND
    if (
      transport_backend == INTEGRATED_RUNTIME_BACKEND
      and args.scenario in INTEGRATED_RUNTIME_REVIEW_SCENARIOS
      and not args.package_archive
    ):
      session, package_assessment, transport_trace = build_demo_integrated_runtime_session(
        args.scenario,
        package_fixture_name=args.package_fixture,
        adapter_fixture_name=args.adapter_fixture,
      )
    else:
      session = build_demo_session(args.scenario)
      package_assessment = None
      if args.package_archive:
        try:
          package_assessment = assess_package_archive(
            Path(args.package_archive),
            detected_product_code=session.product_code,
          )
        except PackageArchiveImportError as error:
          raise SystemExit(str(error))
      elif session.guards.package_loaded or args.package_fixture != 'scenario-default':
        package_assessment = build_demo_package_assessment(
          args.scenario,
          session=session,
          package_fixture_name=args.package_fixture,
        )
  pit_inspection = build_demo_pit_inspection(
    args.scenario,
    session=session,
    package_assessment=package_assessment,
    transport_backend=transport_backend,
  )
  session_report = build_session_evidence_report(
    session,
    scenario_name=scenario,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_trace=transport_trace,
    transport_backend=transport_backend,
    captured_at_utc=args.captured_at_utc,
    pit_required_for_safe_path=True,
  )
  model = build_shell_view_model(
    session,
    scenario_name=scenario,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_trace=transport_trace,
    session_report=session_report,
    transport_backend=transport_backend,
    boot_unhydrated=args.boot_unhydrated,
    pit_required_for_safe_path=True,
  )
  shell_contract = describe_shell(model)
  if args.describe_only:
    print(shell_contract)
  elif not args.gui_host_process:
    print(
      _render_codesentinel_status_block(
        title='Calamum Vulcan GUI launch status',
        status='confirm' if QT_AVAILABLE else 'fail',
        decision='gui_launch_ready' if QT_AVAILABLE else 'qt_runtime_missing',
        sections=(),
      ),
      end='\n\n',
    )

  if args.export_evidence or args.evidence_output:
    if args.evidence_output:
      output_path = write_session_evidence_report(
        session_report,
        Path(args.evidence_output),
        format_name=args.evidence_format,
        transport_trace=transport_trace,
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
  if _should_spawn_detached_gui_host(args):
    if _spawn_detached_gui_host(effective_argv):
      return 0
  exit_code = launch_shell(model, duration_ms=args.duration_ms)
  if not args.gui_host_process:
    print(
      _render_codesentinel_status_block(
        title='Calamum Vulcan GUI exit status',
        status='confirm' if exit_code == 0 else 'fail',
        decision='gui_session_closed_cleanly' if exit_code == 0 else 'gui_session_closed_with_error',
        sections=(),
      ),
      end='\n\n',
    )
  return exit_code


def _validate_package_inputs(args: argparse.Namespace) -> None:
  """Validate mutually exclusive package-input combinations."""

  if args.package_archive and args.package_fixture != 'scenario-default':
    raise SystemExit(
      'Choose either --package-fixture or --package-archive, not both.'
    )
  if args.package_archive and args.transport_source == 'heimdall-adapter':
    raise SystemExit(
      'Real package archive intake is currently supported only with --transport-source state-fixture.'
    )


def _validate_transport_source_selection(args: argparse.Namespace) -> None:
  """Validate transport-source combinations that span shell and live-runtime lanes."""

  del args


def _validate_inspection_inputs(args: argparse.Namespace) -> None:
  """Validate inspect-only workflow boundaries before any live backend work begins."""

  if args.integration_suite is not None:
    raise SystemExit(
      'Choose either --inspect-device or --integration-suite, not both.'
    )
  if args.transport_source == 'heimdall-adapter':
    raise SystemExit(
      'Inspect-only workflow uses the supported integrated-runtime or state-fixture review lanes; the Heimdall adapter remains an explicit historical fallback lane only.'
    )


def _validate_execution_inputs(args: argparse.Namespace) -> None:
  """Validate bounded safe-path execution boundaries before transport begins."""

  if args.integration_suite is not None:
    raise SystemExit(
      'Choose either --execute-flash-plan or --integration-suite, not both.'
    )
  if args.transport_source not in (
    INTEGRATED_RUNTIME_BACKEND,
    'heimdall-adapter',
  ):
    raise SystemExit(
      'Bounded safe-path execution requires --transport-source integrated-runtime for the supported path or --transport-source heimdall-adapter for the explicit historical fallback lane.'
    )


def _normalized_gui_argv(argv: Optional[Sequence[str]]) -> Sequence[str]:
  """Return the effective argv for the GUI entrypoint."""

  if argv is None:
    process_argv = tuple(sys.argv[1:])
    if process_argv:
      return process_argv
    return DEFAULT_GUI_BOOT_ARGS
  if not tuple(argv):
    return DEFAULT_GUI_BOOT_ARGS
  return argv


def _render_codesentinel_status_block(
  title: str,
  status: str,
  decision: str,
  sections: Sequence[tuple[str, Sequence[tuple[str, str]]]],
) -> str:
  """Render an ASCII-safe CodeSentinel-style status block."""

  lines = [
    _colorize_gui_terminal_title(title),
    '',
  ]
  lines.extend(
    _format_codesentinel_status_rows(
      (
        ('generated_at_utc', _utc_now()),
        ('status', status),
        ('decision', decision),
      )
    )
  )
  if sections:
    lines.append('')
  for heading, rows in sections:
    lines.append(heading)
    lines.extend(_format_codesentinel_status_rows(rows, indent='  '))
    lines.append('')
  return '\n'.join(lines).rstrip()


def _format_codesentinel_status_rows(
  rows: Sequence[tuple[str, str]],
  indent: str = '',
) -> list[str]:
  """Return aligned status rows for terminal-facing status blocks."""

  if not rows:
    return []
  prefix_width = max(len(label) + 1 for label, _value in rows)
  formatted_rows = []
  for label, value in rows:
    prefix = '{label}:'.format(label=label).ljust(prefix_width)
    formatted_rows.append(
      '{indent}{prefix} {value}'.format(
        indent=indent,
        prefix=prefix,
        value=value,
      )
    )
  return formatted_rows


def _should_spawn_detached_gui_host(args: argparse.Namespace) -> bool:
  """Return whether the GUI should detach into a background host process."""

  if not sys.platform.startswith('win'):
    return False
  if args.gui_host_process:
    return False
  if args.duration_ms > 0:
    return False
  if args.export_evidence or args.evidence_output:
    return False
  return _is_interactive_terminal_stream(sys.stdout)


def _spawn_detached_gui_host(argv: Sequence[str]) -> bool:
  """Launch the real GUI host in a detached child process and return success."""

  command = _build_detached_gui_host_command(argv)
  if command is None:
    return False
  try:
    subprocess.Popen(
      command,
      stdin=subprocess.DEVNULL,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      close_fds=True,
      **_detached_gui_process_kwargs(),
    )
  except OSError:
    return False
  return True


def _build_detached_gui_host_command(argv: Sequence[str]) -> list[str] | None:
  """Return the detached child-process command for the real GUI host."""

  executable = _resolve_gui_host_python_executable()
  if executable is None:
    return None
  forwarded_argv = [argument for argument in argv if argument != GUI_HOST_PROCESS_FLAG]
  forwarded_argv.append(GUI_HOST_PROCESS_FLAG)
  return [
    str(executable),
    '-m',
    'calamum_vulcan.launch_shell',
    *forwarded_argv,
  ]


def _resolve_gui_host_python_executable() -> Path | None:
  """Resolve the GUI-capable Python executable used for detached launches."""

  executable = Path(sys.executable)
  scripts_dir = executable.parent
  candidates = [
    scripts_dir / 'pythonw.exe',
    scripts_dir / 'python.exe',
    Path(sys.prefix) / 'Scripts' / 'pythonw.exe',
    Path(sys.prefix) / 'Scripts' / 'python.exe',
  ]
  for candidate in candidates:
    if candidate.exists():
      return candidate
  return None


def _detached_gui_process_kwargs() -> dict[str, object]:
  """Return subprocess options for a detached GUI child process."""

  if not sys.platform.startswith('win'):
    return {'start_new_session': True}
  detached_process = getattr(subprocess, 'DETACHED_PROCESS', 0)
  new_process_group = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
  return {
    'creationflags': detached_process | new_process_group,
  }


def _colorize_gui_terminal_title(title: str) -> str:
  """Return the GUI title with a blue brand prefix when ANSI color is supported."""

  if not title.startswith(GUI_TERMINAL_BRAND_TITLE):
    return title
  if not _supports_ansi_terminal_output(sys.stdout):
    return title
  return title.replace(
    GUI_TERMINAL_BRAND_TITLE,
    '{blue}{brand}{reset}'.format(
      blue=ANSI_BRAND_BLUE,
      brand=GUI_TERMINAL_BRAND_TITLE,
      reset=ANSI_RESET,
    ),
    1,
  )


def _supports_ansi_terminal_output(stream: object) -> bool:
  """Return whether the current output stream should receive ANSI color."""

  if os.getenv('NO_COLOR'):
    return False
  if os.getenv('TERM') == 'dumb':
    return False
  isatty = getattr(stream, 'isatty', None)
  if not callable(isatty):
    return False
  try:
    return bool(isatty())
  except Exception:
    return False


def _is_interactive_terminal_stream(stream: object) -> bool:
  """Return whether the provided stream is an interactive terminal."""

  if not _has_writable_stream(stream):
    return False
  isatty = getattr(stream, 'isatty', None)
  if not callable(isatty):
    return False
  try:
    return bool(isatty())
  except Exception:
    return False


def _status_pill_value(model, label: str) -> str:
  """Return one status-pill value from the shell model."""

  for pill in model.status_pills:
    if pill.label == label:
      return pill.value
  raise KeyError('Unknown status pill label: {label}'.format(label=label))


def _utc_now() -> str:
  """Return an ISO8601 UTC timestamp for CLI status blocks."""

  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    '+00:00',
    'Z',
  )


def _build_live_control_plan(args: argparse.Namespace) -> Optional[AndroidToolsCommandPlan]:
  """Return one bounded live-control command plan when requested."""

  requested = [
    bool(args.adb_detect),
    bool(args.fastboot_detect),
    args.adb_reboot is not None,
    args.fastboot_reboot is not None,
    bool(args.inspect_device),
    bool(args.execute_flash_plan),
  ]
  if sum(1 for item in requested if item) > 1:
    raise SystemExit(
      'Select only one live companion action at a time: '
      '--adb-detect, --fastboot-detect, --adb-reboot, --fastboot-reboot, --inspect-device, or --execute-flash-plan.'
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
  live_detection=None,
) -> str:
  """Render one live-control result for operator review."""

  if live_detection is None:
    live_detection = _live_detection_for_control_trace(trace)
  if format_name == 'json':
    payload = trace.to_dict()
    if live_detection is not None:
      payload['live_detection'] = live_detection.to_dict()
    return json.dumps(payload, indent=2, sort_keys=True)

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
  if live_detection is not None:
    lines.append(
      'live_detection state="{state}" source="{source}" fallback_posture="{fallback}" device_present="{present}" command_ready="{ready}" summary="{summary}"'.format(
        state=live_detection.state.value,
        source=(
          live_detection.source.value
          if live_detection.source is not None
          else 'none'
        ),
        fallback=live_detection.fallback_posture.value,
        present='yes' if live_detection.device_present else 'no',
        ready='yes' if live_detection.command_ready else 'no',
        summary=live_detection.summary,
      )
    )
    lines.append(
      'live_path ownership="{ownership}" path_label="{label}" delegated_path_label="{delegated}" identity_confidence="{confidence}" mode_label="{mode}" summary="{summary}"'.format(
        ownership=live_detection.path_identity.ownership.value,
        label=live_detection.path_identity.path_label,
        delegated=live_detection.path_identity.delegated_path_label,
        confidence=live_detection.path_identity.identity_confidence.value,
        mode=live_detection.path_identity.mode_label,
        summary=live_detection.path_identity.summary,
      )
    )
    for guidance in live_detection.path_identity.operator_guidance[:2]:
      lines.append('live_path_guidance="{guidance}"'.format(guidance=guidance))
    if live_detection.snapshot is not None:
      lines.append(
        'live_identity serial="{serial}" mode="{mode}" transport="{transport}" support_posture="{support}" product="{product}" canonical_product="{canonical}" marketing_name="{name}"'.format(
          serial=live_detection.snapshot.serial,
          mode=live_detection.snapshot.mode,
          transport=live_detection.snapshot.transport,
          support=live_detection.snapshot.support_posture.value,
          product=live_detection.snapshot.product_code or 'unknown',
          canonical=live_detection.snapshot.canonical_product_code or 'unknown',
          name=live_detection.snapshot.marketing_name or 'unknown',
        )
      )
      lines.append(
        'live_info posture="{posture}" manufacturer="{manufacturer}" android_version="{android}" security_patch="{patch}" bootloader="{bootloader}"'.format(
          posture=live_detection.snapshot.info_state.value,
          manufacturer=live_detection.snapshot.manufacturer or 'unknown',
          android=live_detection.snapshot.android_version or 'unknown',
          patch=live_detection.snapshot.security_patch or 'unknown',
          bootloader=live_detection.snapshot.bootloader_version or 'unknown',
        )
      )
      for hint in live_detection.snapshot.capability_hints:
        lines.append('live_capability="{hint}"'.format(hint=hint))
      for guidance in live_detection.snapshot.operator_guidance[:2]:
        lines.append('live_guidance="{guidance}"'.format(guidance=guidance))
    if live_detection.fallback_reason:
      lines.append(
        'live_fallback_reason="{reason}"'.format(
          reason=live_detection.fallback_reason,
        )
      )
    for note in live_detection.notes:
      lines.append('live_detection_note="{note}"'.format(note=note))
  return '\n'.join(lines)


def _live_detection_for_control_trace(
  trace: AndroidToolsNormalizedTrace,
):
  """Return repo-owned live detection truth when the control trace is a detect operation."""

  if trace.command_plan.operation not in (
    AndroidToolsOperation.ADB_DEVICES,
    AndroidToolsOperation.FASTBOOT_DEVICES,
  ):
    return None

  fallback_posture = LiveFallbackPosture.NOT_NEEDED
  fallback_reason = None
  if (
    trace.command_plan.operation == AndroidToolsOperation.ADB_DEVICES
    and not trace.detected_devices
  ):
    fallback_posture = LiveFallbackPosture.NEEDED
    fallback_reason = (
      'ADB did not establish a live device; fastboot is the next supported detect source.'
    )

  return build_live_detection_session(
    trace,
    fallback_posture=fallback_posture,
    fallback_reason=fallback_reason,
  )


def _enrich_live_detection_for_control_trace(
  trace: AndroidToolsNormalizedTrace,
):
  """Return a repo-owned live snapshot enriched with bounded info when possible."""

  live_detection = _live_detection_for_control_trace(trace)
  if live_detection is None or live_detection.snapshot is None:
    return live_detection
  snapshot = live_detection.snapshot
  if snapshot.source != LiveDeviceSource.ADB or not snapshot.command_ready:
    return live_detection
  info_trace = execute_android_tools_command(
    build_adb_device_info_command_plan(device_serial=snapshot.serial)
  )
  return apply_live_device_info_trace(live_detection, info_trace)


def _run_supported_download_mode_detection(
  source_labels: Sequence[str],
):
  """Return the shared Sprint 6 native USB download-mode detection result."""

  probe_result = VulcanUSBScanner().probe_download_mode_devices()
  return build_usb_live_detection_session(
    probe_result,
    source_labels=tuple(source_labels),
  )


def _run_inspect_only_workflow(
  args: argparse.Namespace,
  scenario_name: str,
):
  """Run the first-class inspect-only workflow and return one evidence report."""

  _validate_package_inputs(args)
  session = build_demo_session(args.scenario)
  package_assessment = None
  if args.package_archive:
    try:
      package_assessment = assess_package_archive(
        Path(args.package_archive),
        detected_product_code=session.product_code,
      )
    except PackageArchiveImportError as error:
      raise SystemExit(str(error))
  elif session.guards.package_loaded or args.package_fixture != 'scenario-default':
    package_assessment = build_demo_package_assessment(
      args.scenario,
      session=session,
      package_fixture_name=args.package_fixture,
    )

  live_detection = _run_inspect_only_live_detection(args.device_serial)
  pit_inspection = _run_inspect_only_pit_review(
    live_detection,
    package_assessment=package_assessment,
    output_path=args.pit_output_path,
  )
  captured_at_utc = args.captured_at_utc or _utc_now()
  session = replace(session, live_detection=live_detection)
  session = replace(
    session,
    inspection=build_inspection_workflow(
      live_detection,
      pit_inspection=pit_inspection,
      captured_at_utc=captured_at_utc,
    ),
  )
  return build_session_evidence_report(
    session,
    scenario_name=scenario_name,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_backend=INTEGRATED_RUNTIME_BACKEND,
    captured_at_utc=captured_at_utc,
  )


def _run_execute_flash_plan_workflow(
  args: argparse.Namespace,
  scenario_name: str,
):
  """Run the bounded safe-path execution lane and return report plus status."""

  _validate_package_inputs(args)
  transport_backend = (
    INTEGRATED_RUNTIME_BACKEND
    if args.transport_source == INTEGRATED_RUNTIME_BACKEND
    else 'heimdall'
  )
  (
    base_session,
    package_assessment,
    pit_inspection,
    fixture_name,
    process_result,
  ) = build_demo_safe_path_runtime_context(
    args.scenario,
    package_fixture_name=args.package_fixture,
    adapter_fixture_name=args.adapter_fixture,
    transport_backend=transport_backend,
  )
  if transport_backend == INTEGRATED_RUNTIME_BACKEND:
    reviewed_flash_plan = build_integrated_reviewed_flash_plan(package_assessment)
  else:
    reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)
  execution_rejected = None
  transport_trace = None

  def _runner(command_plan: object) -> object:
    del command_plan
    return process_result

  try:
    if transport_backend == INTEGRATED_RUNTIME_BACKEND:
      runtime_result = run_integrated_flash_session(
        base_session,
        reviewed_flash_plan,
        package_assessment=package_assessment,
        pit_inspection=pit_inspection,
        runner=_runner,
        fixture_name=fixture_name,
      )
    else:
      runtime_result = run_bounded_heimdall_flash_session(
        base_session,
        reviewed_flash_plan,
        package_assessment=package_assessment,
        pit_inspection=pit_inspection,
        runner=_runner,
        fixture_name=fixture_name,
      )
    session = runtime_result.session
    transport_trace = runtime_result.trace
  except RuntimeSessionRejected as error:
    session = base_session
    execution_rejected = str(error)

  report = build_session_evidence_report(
    session,
    scenario_name=scenario_name,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_trace=transport_trace,
    transport_backend=transport_backend,
    captured_at_utc=args.captured_at_utc,
    pit_required_for_safe_path=True,
  )
  return report, execution_rejected, transport_trace


def _run_inspect_only_live_detection(
  device_serial: Optional[str],
):
  """Run the unified inspect-only detection path across ADB, fastboot, and native USB."""

  adb_trace = execute_android_tools_command(
    build_adb_detect_command_plan(device_serial=device_serial)
  )
  if adb_trace.detected_devices:
    detection = build_live_detection_session(adb_trace)
    snapshot = detection.snapshot
    if snapshot is not None and snapshot.source == LiveDeviceSource.ADB and snapshot.command_ready:
      info_trace = execute_android_tools_command(
        build_adb_device_info_command_plan(device_serial=snapshot.serial)
      )
      return apply_live_device_info_trace(detection, info_trace)
    return detection

  fastboot_trace = execute_android_tools_command(
    build_fastboot_detect_command_plan(device_serial=device_serial)
  )
  if fastboot_trace.detected_devices:
    return build_live_detection_session(
      fastboot_trace,
      fallback_posture=LiveFallbackPosture.ENGAGED,
      fallback_reason=(
        'ADB did not establish a live device; fastboot captured the active companion.'
      ),
      source_labels=('adb', 'fastboot'),
    )
  return _run_supported_download_mode_detection(
    source_labels=('adb', 'fastboot', 'usb'),
  )


def _run_inspect_only_pit_review(
  live_detection,
  package_assessment=None,
  output_path: str = 'artifacts/device.pit',
):
  """Run bounded PIT inspection for the inspect-only workflow."""

  detected_product_code = _inspection_detected_product_code(live_detection)
  print_trace = execute_integrated_command(build_print_pit_command_plan())
  inspection = build_pit_inspection(
    print_trace,
    detected_product_code=detected_product_code,
    package_assessment=package_assessment,
  )
  if inspection.state not in (
    PitInspectionState.FAILED,
    PitInspectionState.MALFORMED,
  ):
    return inspection

  download_trace = execute_integrated_command(
    build_download_pit_command_plan(output_path=output_path)
  )
  download_inspection = build_pit_inspection(
    download_trace,
    detected_product_code=detected_product_code,
    package_assessment=package_assessment,
  )
  if download_inspection.state != PitInspectionState.FAILED:
    return download_inspection
  return inspection


def _inspection_detected_product_code(live_detection) -> Optional[str]:
  """Return the best product-code hint available for PIT alignment review."""

  snapshot = live_detection.snapshot
  if snapshot is None:
    return None
  if snapshot.product_code is not None:
    return snapshot.product_code
  return snapshot.model_name


def _render_inspection_result(report, format_name: str) -> str:
  """Render one inspect-only result bundle for operator review."""

  if format_name == 'json':
    payload = report.to_dict()
    return json.dumps(
      {
        'scenario_name': payload['scenario_name'],
        'session_phase': payload['session_phase'],
        'summary': payload['summary'],
        'inspection': payload['inspection'],
        'device_live': payload['device']['live'],
        'pit': payload['pit'],
      },
      indent=2,
      sort_keys=True,
    )

  lines = [
    'inspection_result posture="{posture}" evidence_ready="{ready}" write_ready="no" reviewed_phase="{phase}" summary="{summary}"'.format(
      posture=report.inspection.posture,
      ready='yes' if report.inspection.evidence_ready else 'no',
      phase=report.session_phase,
      summary=report.inspection.summary,
    ),
    'inspection_live state="{state}" source="{source}" info_state="{info_state}" device_present="{present}" summary="{summary}"'.format(
      state=report.device.live.state,
      source=report.device.live.source or 'none',
      info_state=report.device.live.info_state,
      present='yes' if report.device.live.device_present else 'no',
      summary=report.device.live.summary,
    ),
    'inspection_pit state="{state}" source="{source}" package_alignment="{alignment}" fallback="{fallback}" summary="{summary}"'.format(
      state=report.pit.state,
      source=report.pit.source or 'none',
      alignment=report.pit.package_alignment,
      fallback=report.pit.fallback_posture,
      summary=report.pit.summary,
    ),
    'inspection_next="{next_action}"'.format(
      next_action=report.inspection.next_action,
    ),
  ]
  for boundary in report.inspection.action_boundaries:
    lines.append('inspection_boundary="{boundary}"'.format(boundary=boundary))
  return '\n'.join(lines)


def _render_execute_result(
  report,
  execution_rejected: Optional[str],
  format_name: str,
) -> str:
  """Render one bounded safe-path execute result for operator review."""

  execution_allowed = (
    execution_rejected is None and report.transport.command_display != 'not_invoked'
  )
  if format_name == 'json':
    return json.dumps(
      {
        'scenario_name': report.scenario_name,
        'session_phase': report.session_phase,
        'summary': report.summary,
        'execution_allowed': execution_allowed,
        'execution_rejected': execution_rejected,
        'authority': asdict(report.authority),
        'flash_plan': {
          'plan_id': report.flash_plan.plan_id,
          'ready_for_transport': report.flash_plan.ready_for_transport,
          'transport_backend': report.flash_plan.transport_backend,
        },
        'transport': asdict(report.transport),
        'outcome': asdict(report.outcome),
      },
      indent=2,
      sort_keys=True,
    )

  boundary = (
    'Platform supervises the bounded reviewed flash session while integrated-runtime owns the supported-path boundary and delegated lower-transport details remain packaged.'
    if report.flash_plan.transport_backend == INTEGRATED_RUNTIME_BACKEND
    else 'Platform supervises the bounded reviewed flash session while Heimdall remains the delegated lower transport lane.'
  )
  lines = [
    'safe_path_result execution_allowed="{allowed}" session_phase="{phase}" launch_path="{path}" ownership="{ownership}" readiness="{readiness}" transport_state="{transport_state}" summary="{summary}"'.format(
      allowed='yes' if execution_allowed else 'no',
      phase=report.session_phase,
      path=report.authority.selected_launch_path,
      ownership=report.authority.ownership,
      readiness=report.authority.readiness,
      transport_state=report.transport.state,
      summary=report.summary,
    ),
    'safe_path_boundary="{boundary}"'.format(boundary=boundary),
  ]
  if execution_rejected is not None:
    lines.append('safe_path_rejected="{reason}"'.format(
      reason=execution_rejected,
    ))
  elif report.transport.command_display != 'not_invoked':
    lines.append('safe_path_command="{command}"'.format(
      command=report.transport.command_display,
    ))
  lines.append('safe_path_next="{next_action}"'.format(
    next_action=report.outcome.next_action,
  ))
  if report.outcome.recovery_guidance:
    lines.append('safe_path_recovery="{guidance}"'.format(
      guidance=report.outcome.recovery_guidance[0],
    ))
  return '\n'.join(lines)


if __name__ == '__main__':
  raise SystemExit(main())