"""CLI entry point for the Calamum Vulcan FS-03 shell sandbox."""

from __future__ import annotations

import argparse
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
from .integration import build_orchestration_close_bundle
from .integration import build_sprint_close_bundle
from .integration import render_sprint_close_bundle_markdown
from .integration import serialize_sprint_close_bundle_json
from .integration import write_sprint_close_bundle
from ..domain.package import PackageArchiveImportError
from ..domain.package import assess_package_archive
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

  try:
    return metadata.version(PACKAGE_DISTRIBUTION_NAME)
  except metadata.PackageNotFoundError:
    return _fallback_project_version()


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
    '--package-archive',
    default=None,
    help='Optional real package zip archive to ingest and checksum-verify for shell review.',
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
    print(_render_control_trace(trace, args.control_format))
    return 0

  bundle = None
  if args.integration_suite == 'sprint-close':
    bundle = build_sprint_close_bundle(captured_at_utc=args.captured_at_utc)
  elif args.integration_suite == 'orchestration-close':
    bundle = build_orchestration_close_bundle(captured_at_utc=args.captured_at_utc)
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
  if args.transport_source == 'heimdall-adapter':
    session, package_assessment, transport_trace = build_demo_adapter_session(
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
    boot_unhydrated=args.boot_unhydrated,
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
      )
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
      )
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
    'generated_at_utc: {timestamp}'.format(timestamp=_utc_now()),
    'status: {status}'.format(status=status),
    'decision: {decision}'.format(decision=decision),
  ]
  if sections:
    lines.append('')
  for heading, rows in sections:
    lines.append(heading)
    for key, value in rows:
      lines.append('  {key}: {value}'.format(key=key, value=value))
    lines.append('')
  return '\n'.join(lines).rstrip()


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