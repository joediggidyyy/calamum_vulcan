"""Run a broad PIT transport diagnostic across parser, fallback, and runtime paths."""

from __future__ import annotations

import argparse
from enum import Enum
import json
import re
import sys
import tomllib
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Mapping
from typing import Optional
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallProcessResult
from calamum_vulcan.adapters.heimdall import HeimdallRuntimeProbe
from calamum_vulcan.adapters.heimdall import build_download_pit_command_plan
from calamum_vulcan.adapters.heimdall import build_print_pit_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.adapters.heimdall import probe_heimdall_runtime
from calamum_vulcan.domain.pit.builder import build_pit_inspection
from calamum_vulcan.domain.pit.model import PitInspection
from calamum_vulcan.domain.pit.model import PitInspectionState
from calamum_vulcan.domain.pit.model import PitSource
from calamum_vulcan.domain.state.integrated_runtime import execute_integrated_command
from calamum_vulcan.domain.state.integrated_runtime import integrated_command_display
from calamum_vulcan.domain.state.integrated_runtime import project_heimdall_trace_to_integrated_runtime
from calamum_vulcan.fixtures.heimdall_pit_fixtures import load_heimdall_pit_fixture


ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'pit_transport_diagnostic'
DEFAULT_LIVE_OUTPUT_NAME = 'live-device.pit'
CURRENT_GUI_DISCONNECT_MARKERS = (
  'disconnected during pit acquisition',
  'lost access to the samsung download-mode interface during pit acquisition',
)
USB_DEVICE_PATH_PATTERN = re.compile(
  r'USB#VID_(?P<vendor>[0-9A-Fa-f]{4})&PID_(?P<product>[0-9A-Fa-f]{4})(?:&MI_(?P<interface>[0-9A-Fa-f]{2}))?'
)
LIBUSB_ERROR_PATTERN = re.compile(r'libusb error:\s*(?P<code>-?\d+)', re.IGNORECASE)


def _project_version() -> str:
  """Return the current package version from pyproject.toml."""

  with (REPO_ROOT / 'pyproject.toml').open('rb') as handle:
    project = tomllib.load(handle)['project']
  return str(project['version'])


CURRENT_PACKAGE_VERSION = _project_version()


def _utc_timestamp() -> str:
  """Return one filesystem-safe UTC timestamp."""

  return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _json_ready_runtime_probe(probe: HeimdallRuntimeProbe) -> Mapping[str, object]:
  """Return one JSON-serializable runtime probe payload."""

  return {
    'executable_name': probe.executable_name,
    'resolved_path': probe.resolved_path,
    'resolution_source': probe.resolution_source,
    'packaged_candidate': probe.packaged_candidate,
    'packaged_candidate_present': probe.packaged_candidate_present,
    'smoke_test_exit_code': probe.smoke_test_exit_code,
    'smoke_test_summary': probe.smoke_test_summary,
    'stdout_lines': list(probe.stdout_lines),
    'stderr_lines': list(probe.stderr_lines),
    'available': probe.available,
  }


def _json_ready_command_plan(command_plan) -> Mapping[str, object]:
  """Return one JSON-serializable command-plan payload."""

  return {
    'capability': command_plan.capability.value,
    'operation': command_plan.operation.value,
    'display_command': command_plan.display_command,
    'integrated_display_command': integrated_command_display(command_plan),
    'expected_exit_codes': list(command_plan.expected_exit_codes),
    'arguments': list(command_plan.arguments),
  }


def _json_ready_process_result(process_result: HeimdallProcessResult) -> Mapping[str, object]:
  """Return one JSON-serializable process result payload."""

  return {
    'fixture_name': process_result.fixture_name,
    'operation': process_result.operation.value,
    'exit_code': process_result.exit_code,
    'stdout_lines': list(process_result.stdout_lines),
    'stderr_lines': list(process_result.stderr_lines),
  }


def _json_ready_trace(trace) -> Mapping[str, object]:
  """Return one JSON-serializable trace payload."""

  return {
    'adapter_name': trace.adapter_name,
    'operation': trace.command_plan.operation.value,
    'state': trace.state.value,
    'summary': trace.summary,
    'exit_code': trace.exit_code,
    'display_command': trace.command_plan.display_command,
    'notes': list(trace.notes),
    'stdout_lines': list(trace.stdout_lines),
    'stderr_lines': list(trace.stderr_lines),
  }


def _json_ready_inspection(inspection: Optional[PitInspection]) -> Optional[Mapping[str, object]]:
  """Return one JSON-serializable inspection payload."""

  if inspection is None:
    return None
  return _json_safe_value(inspection.to_dict())


def _json_safe_value(value: object) -> object:
  """Return one recursively JSON-safe value with enums flattened to plain values."""

  if isinstance(value, Enum):
    return value.value
  if isinstance(value, dict):
    return {
      str(key): _json_safe_value(nested)
      for key, nested in value.items()
    }
  if isinstance(value, (list, tuple)):
    return [_json_safe_value(item) for item in value]
  return value


def _current_gui_disconnect_detected(
  pit_inspection: Optional[PitInspection],
) -> bool:
  """Mirror the current Qt-shell disconnect classifier for PIT failures."""

  if pit_inspection is None:
    return False
  if pit_inspection.state != PitInspectionState.FAILED:
    return False
  summary = pit_inspection.summary.lower()
  return any(marker in summary for marker in CURRENT_GUI_DISCONNECT_MARKERS)


def _fallback_recommendation(
  pit_inspection: Optional[PitInspection],
) -> str:
  """Return the diagnostic fallback recommendation for one PIT outcome."""

  if pit_inspection is None:
    return 'no_inspection_available'
  if pit_inspection.state == PitInspectionState.CAPTURED:
    return 'no_fallback_needed'
  if pit_inspection.state == PitInspectionState.PARTIAL:
    if pit_inspection.source in (
      PitSource.HEIMDALL_DOWNLOAD_PIT,
      PitSource.INTEGRATED_RUNTIME_DOWNLOAD_PIT,
    ):
      return 'print_pit_still_needed_for_partition_rows'
    return 'partial_truth_requires_operator_review'
  if pit_inspection.state in (
    PitInspectionState.FAILED,
    PitInspectionState.MALFORMED,
  ):
    if _current_gui_disconnect_detected(pit_inspection):
      return 'current_gui_would_skip_download_pit_fallback'
    return 'attempt_download_pit_fallback'
  return 'no_additional_recommendation'


def _extract_usb_identity_from_lines(lines: Sequence[str]) -> Mapping[str, Optional[str]]:
  """Return one best-effort USB identity payload from stderr/stdout text."""

  for line in lines:
    match = USB_DEVICE_PATH_PATTERN.search(str(line))
    if match is None:
      continue
    return {
      'vendor_id': match.group('vendor').upper(),
      'product_id': match.group('product').upper(),
      'interface_id': (
        match.group('interface').upper()
        if match.group('interface') is not None
        else None
      ),
    }
  return {
    'vendor_id': None,
    'product_id': None,
    'interface_id': None,
  }


def _extract_libusb_error_code(lines: Sequence[str]) -> Optional[int]:
  """Return one best-effort libusb error code from raw command output."""

  for line in lines:
    match = LIBUSB_ERROR_PATTERN.search(str(line))
    if match is None:
      continue
    return int(match.group('code'))
  return None


def _classify_trace_pattern(trace_payload: Mapping[str, object]) -> Mapping[str, object]:
  """Classify one trace into a likely connection-issue family."""

  combined_lines = tuple(str(line) for line in (
    list(trace_payload.get('stderr_lines', ()))
    + list(trace_payload.get('stdout_lines', ()))
    + list(trace_payload.get('notes', ()))
  ))
  lowered = ' '.join(combined_lines).lower()
  usb_identity = _extract_usb_identity_from_lines(combined_lines)
  libusb_error_code = _extract_libusb_error_code(combined_lines)
  family = 'healthy_capture'
  confidence = 'high'
  summary = 'Transport evidence looks healthy for PIT capture.'
  next_steps = []

  if trace_payload.get('state') == 'completed' and 'download-pit' in str(trace_payload.get('display_command', '')):
    family = 'metadata_only_fallback'
    summary = 'Download-pit metadata capture succeeded, but detailed partition rows still require print-pit.'
    next_steps = [
      'Treat this as bounded metadata only; it cannot replace a trustworthy print-pit partition-row capture.',
    ]
  elif 'missing dll dependency' in lowered or '0xc0000135' in lowered:
    family = 'runtime_dependency_failure'
    summary = 'The Heimdall runtime is present but Windows is missing one or more required DLL dependencies.'
    next_steps = [
      'Repair the packaged or installed Heimdall runtime dependencies before retrying PIT transport.',
    ]
  elif 'no download-mode device' in lowered or 'no device detected' in lowered:
    family = 'device_not_present'
    summary = 'The transport did not detect a compatible Samsung download-mode device at command time.'
    next_steps = [
      'Confirm the device is still in Samsung download mode before retrying PIT transport.',
    ]
  elif 'failed to claim interface' in lowered or 'access denied' in lowered or 'permission denied' in lowered:
    family = 'driver_or_claim_conflict'
    summary = 'The transport reached the device path but could not claim the expected USB interface.'
    next_steps = [
      'Inspect Windows driver binding for the Samsung download-mode interface and check for competing claims from other tools.',
    ]
  elif 'no longer connected' in lowered or 'failed to access device' in lowered:
    family = 'interface_loss_or_driver_rebind'
    summary = 'The transport initialized against a USB path, then lost the device/interface before PIT transfer could start.'
    next_steps = [
      'Treat this as a transport/interface-class failure rather than a parser problem.',
      'Check for Windows driver rebinding, interface claim churn, or unstable USB path changes during Samsung download-mode handoff.',
    ]
    if usb_identity.get('vendor_id') not in (None, '04E8'):
      confidence = 'high'
      next_steps.append(
        'The raw USB path reported a non-Samsung vendor id (`{vendor}`), which strongly suggests the wrong interface or driver binding is being captured.'.format(
          vendor=usb_identity.get('vendor_id'),
        )
      )
    else:
      confidence = 'medium'
  elif 'timed out' in lowered or 'timeout' in lowered:
    family = 'transport_timeout'
    summary = 'The transport stalled long enough to hit the bounded PIT timeout.'
    next_steps = [
      'Inspect long-running USB negotiation, cable/hub stability, and command timeout suitability.',
    ]
  elif trace_payload.get('state') == 'completed':
    family = 'healthy_capture'
    summary = 'Transport completed without a lower-transport failure signature.'
  else:
    family = 'unclassified_transport_failure'
    confidence = 'medium'
    summary = 'Transport failed, but the current classifier could not map it to a known PIT failure family.'
    next_steps = [
      'Review the raw stdout/stderr lines directly and extend the classifier if this pattern is repeatable.',
    ]

  return {
    'family': family,
    'confidence': confidence,
    'summary': summary,
    'libusb_error_code': libusb_error_code,
    'usb_identity': usb_identity,
    'next_steps': next_steps,
  }


def _likely_known_issue(summary: Mapping[str, object]) -> Mapping[str, object]:
  """Return the dominant likely issue family across the live PIT evidence."""

  live_suite = summary.get('live_command_suite', {})
  if not live_suite.get('executed'):
    return {
      'family': 'insufficient_live_evidence',
      'confidence': 'low',
      'summary': 'No live PIT command evidence was captured, so the known-issue selector cannot rank likely connection families yet.',
      'next_steps': ['Run the diagnostic with --run-live-commands.'],
    }

  print_trace = live_suite['print_pit']['trace']
  download_trace = live_suite['download_pit']['trace']
  print_pattern = _classify_trace_pattern(print_trace)
  download_pattern = _classify_trace_pattern(download_trace)
  if (
    print_pattern['family'] == 'interface_loss_or_driver_rebind'
    and download_pattern['family'] == 'interface_loss_or_driver_rebind'
  ):
    return {
      'family': 'interface_loss_or_driver_rebind',
      'confidence': 'high',
      'summary': 'Both live print-pit and live download-pit fell into the same interface-loss-class pattern, so the dominant known issue is transport/interface churn rather than parser failure.',
      'next_steps': list(dict.fromkeys(
        list(print_pattern['next_steps']) + list(download_pattern['next_steps'])
      )),
    }
  if print_pattern['family'] != 'healthy_capture':
    return print_pattern
  return download_pattern


def _run_fixture_case(
  scenario_id: str,
  command_plan,
  process_result: HeimdallProcessResult,
  integrated_runtime: bool,
  detected_product_code: Optional[str] = 'SM-G991U',
) -> Mapping[str, object]:
  """Return one parser/fallback diagnostic case result."""

  trace = normalize_heimdall_result(command_plan, process_result)
  if integrated_runtime:
    trace = project_heimdall_trace_to_integrated_runtime(trace)
  inspection = build_pit_inspection(
    trace,
    detected_product_code=detected_product_code,
  )
  return {
    'scenario_id': scenario_id,
    'integrated_runtime': integrated_runtime,
    'process_result': _json_ready_process_result(process_result),
    'trace': _json_ready_trace(trace),
    'inspection': _json_ready_inspection(inspection),
    'gui_disconnect_detected': _current_gui_disconnect_detected(inspection),
    'fallback_recommendation': _fallback_recommendation(inspection),
    'classification': _classify_trace_pattern(_json_ready_trace(trace)),
  }


def _synthetic_interface_loss_result() -> HeimdallProcessResult:
  """Return one synthetic print-pit failure that looks like interface loss."""

  return HeimdallProcessResult(
    fixture_name='pit-print-interface-loss',
    operation=HeimdallOperation.PRINT_PIT,
    exit_code=1,
    stderr_lines=(
      "libusb: error [init_device] device '\\\\.\\USB#VID_04E8&PID_B7E8&MI_02#{6834F87EB9B80&0002}' is no longer connected!",
    ),
  )


def _build_fixture_matrix() -> list[Mapping[str, object]]:
  """Return the deterministic PIT parser/fallback matrix."""

  print_plan = build_print_pit_command_plan()
  download_plan = build_download_pit_command_plan(output_path='artifacts/device-ready.pit')
  return [
    _run_fixture_case(
      'heimdall_print_ready_g991u',
      print_plan,
      load_heimdall_pit_fixture('pit-print-ready-g991u'),
      integrated_runtime=False,
    ),
    _run_fixture_case(
      'integrated_print_ready_g991u',
      print_plan,
      load_heimdall_pit_fixture('pit-print-ready-g991u'),
      integrated_runtime=True,
    ),
    _run_fixture_case(
      'integrated_print_malformed',
      print_plan,
      load_heimdall_pit_fixture('pit-print-malformed'),
      integrated_runtime=True,
    ),
    _run_fixture_case(
      'integrated_print_interface_loss',
      print_plan,
      _synthetic_interface_loss_result(),
      integrated_runtime=True,
    ),
    _run_fixture_case(
      'integrated_download_ready_g991u',
      download_plan,
      load_heimdall_pit_fixture('pit-download-ready-g991u'),
      integrated_runtime=True,
    ),
  ]


def _run_live_pit_suite(
  runtime_probe: HeimdallRuntimeProbe,
  archive_root: Path,
  run_live_commands: bool,
) -> Mapping[str, object]:
  """Return the optional live PIT subprocess suite result."""

  if not run_live_commands:
    return {
      'enabled': False,
      'executed': False,
      'status': 'skipped',
      'summary': 'Live PIT subprocess commands were not requested.',
      'notes': [
        'Enable --run-live-commands to capture real print-pit and download-pit subprocess evidence.',
      ],
    }
  if not runtime_probe.available:
    return {
      'enabled': True,
      'executed': False,
      'status': 'blocked',
      'summary': 'Live PIT subprocess commands were skipped because the Heimdall runtime probe is not available.',
      'notes': [runtime_probe.smoke_test_summary, *runtime_probe.stderr_lines],
    }

  artifacts_root = archive_root / 'artifacts'
  artifacts_root.mkdir(parents=True, exist_ok=True)
  print_trace = execute_integrated_command(
    build_print_pit_command_plan(),
    fixture_name='pit-diagnostic-live-print',
  )
  print_inspection = build_pit_inspection(print_trace)
  download_output_path = artifacts_root / DEFAULT_LIVE_OUTPUT_NAME
  download_trace = execute_integrated_command(
    build_download_pit_command_plan(output_path=str(download_output_path)),
    fixture_name='pit-diagnostic-live-download',
  )
  download_inspection = build_pit_inspection(download_trace)

  notes = []
  if (
    print_inspection.state in (PitInspectionState.FAILED, PitInspectionState.MALFORMED)
    and download_inspection.state in (PitInspectionState.CAPTURED, PitInspectionState.PARTIAL)
  ):
    notes.append(
      'Live download-pit recovered bounded PIT truth after live print-pit failed or malformed.'
    )
  if _current_gui_disconnect_detected(print_inspection):
    notes.append(
      'Current GUI disconnect heuristic would classify the live print-pit failure as interface loss.'
    )
  if _current_gui_disconnect_detected(download_inspection):
    notes.append(
      'The live download-pit attempt also resolved to the same interface-loss-class failure, so the fallback path did not recover additional truth in this run.'
    )
  if not notes:
    notes.append('Live PIT subprocess evidence did not expose a stronger fallback signal than the deterministic matrix.')

  return {
    'enabled': True,
    'executed': True,
    'status': 'complete',
    'summary': 'Live PIT subprocess commands executed through the integrated runtime boundary.',
    'print_pit': {
      'trace': _json_ready_trace(print_trace),
      'inspection': _json_ready_inspection(print_inspection),
      'gui_disconnect_detected': _current_gui_disconnect_detected(print_inspection),
      'fallback_recommendation': _fallback_recommendation(print_inspection),
      'classification': _classify_trace_pattern(_json_ready_trace(print_trace)),
    },
    'download_pit': {
      'trace': _json_ready_trace(download_trace),
      'inspection': _json_ready_inspection(download_inspection),
      'gui_disconnect_detected': _current_gui_disconnect_detected(download_inspection),
      'fallback_recommendation': _fallback_recommendation(download_inspection),
      'classification': _classify_trace_pattern(_json_ready_trace(download_trace)),
      'output_path': str(download_output_path),
    },
    'notes': notes,
  }


def _command_inventory() -> Mapping[str, object]:
  """Return the PIT command inventory used by the diagnostic lane."""

  print_plan = build_print_pit_command_plan()
  download_plan = build_download_pit_command_plan(output_path='artifacts/device.pit')
  return {
    'print_pit': _json_ready_command_plan(print_plan),
    'download_pit': _json_ready_command_plan(download_plan),
  }


def _findings(
  runtime_probe: HeimdallRuntimeProbe,
  fixture_matrix: Sequence[Mapping[str, object]],
  live_suite: Mapping[str, object],
) -> list[str]:
  """Return the high-value findings extracted from the diagnostic evidence."""

  findings = []
  if not runtime_probe.available:
    findings.append(runtime_probe.smoke_test_summary)
  for case in fixture_matrix:
    if case['scenario_id'] == 'integrated_print_interface_loss' and case['fallback_recommendation'] == 'current_gui_would_skip_download_pit_fallback':
      findings.append(
        'Current GUI PIT handling suppresses download-pit fallback whenever the failure summary is classified as interface loss.'
      )
    if case['scenario_id'] == 'integrated_print_malformed' and case['fallback_recommendation'] == 'attempt_download_pit_fallback':
      findings.append(
        'Malformed print-pit output remains eligible for metadata-only download-pit fallback under the current bounded transport policy.'
      )
    if case['scenario_id'] == 'integrated_download_ready_g991u':
      findings.append(
        'Download-pit yields bounded metadata only; detailed partition rows still require a trustworthy print-pit capture.'
      )
  if live_suite.get('executed'):
    findings.extend(str(note) for note in live_suite.get('notes', ()))
  deduped = []
  for finding in findings:
    if finding and finding not in deduped:
      deduped.append(finding)
  return deduped


def build_pit_transport_summary(
  runtime_probe: HeimdallRuntimeProbe,
  archive_root: Path,
  run_live_commands: bool = False,
) -> dict[str, object]:
  """Return the broad PIT transport diagnostic summary payload."""

  fixture_matrix = _build_fixture_matrix()
  live_suite = _run_live_pit_suite(
    runtime_probe,
    archive_root,
    run_live_commands=run_live_commands,
  )
  return {
    'package_version': CURRENT_PACKAGE_VERSION,
    'generated_at_utc': _utc_timestamp(),
    'repo_root': str(REPO_ROOT),
    'archive_root': str(archive_root),
    'investigative_paths': [
      'heimdall runtime probe',
      'pit command-plan inventory',
      'deterministic parser and fallback matrix',
      'current GUI disconnect heuristic mirror',
      'optional live print-pit and download-pit subprocess comparison',
    ],
    'runtime_probe': _json_ready_runtime_probe(runtime_probe),
    'command_inventory': _command_inventory(),
    'fixture_matrix': fixture_matrix,
    'live_command_suite': live_suite,
    'live_known_issue_selector': _likely_known_issue({
      'live_command_suite': live_suite,
    }),
    'findings': _findings(runtime_probe, fixture_matrix, live_suite),
  }


def render_pit_transport_markdown(summary: Mapping[str, object]) -> str:
  """Render the PIT transport diagnostic summary as Markdown."""

  runtime_probe = summary['runtime_probe']
  lines = [
    '# PIT transport diagnostic',
    '',
    '- package version: `{version}`'.format(version=summary['package_version']),
    '- generated at UTC: `{generated}`'.format(generated=summary['generated_at_utc']),
    '- archive root: `{root}`'.format(root=summary['archive_root']),
    '',
    '## Runtime probe',
    '',
    '- available: `{available}`'.format(available=runtime_probe['available']),
    '- resolution source: `{source}`'.format(source=runtime_probe['resolution_source']),
    '- resolved path: `{path}`'.format(path=runtime_probe['resolved_path']),
    '- smoke test exit code: `{code}`'.format(code=runtime_probe['smoke_test_exit_code']),
    '- summary: {summary}'.format(summary=runtime_probe['smoke_test_summary']),
    '',
    '## Command inventory',
    '',
    '| command | backend display | integrated display | expected exit codes |',
    '| --- | --- | --- | --- |',
  ]
  for label, payload in summary['command_inventory'].items():
    lines.append(
      '| `{label}` | `{display}` | `{integrated}` | `{codes}` |'.format(
        label=label,
        display=payload['display_command'],
        integrated=payload['integrated_display_command'],
        codes=', '.join(str(code) for code in payload['expected_exit_codes']),
      )
    )
  lines.extend(
    [
      '',
      '## Fixture investigation matrix',
      '',
      '| scenario | trace state | inspection state | GUI disconnect heuristic | fallback recommendation |',
      '| --- | --- | --- | --- | --- |',
    ]
  )
  for case in summary['fixture_matrix']:
    inspection = case['inspection'] or {}
    lines.append(
      '| `{scenario}` | `{trace_state}` | `{inspection_state}` | `{disconnect}` | `{fallback}` |'.format(
        scenario=case['scenario_id'],
        trace_state=case['trace']['state'],
        inspection_state=inspection.get('state', 'none'),
        disconnect=case['gui_disconnect_detected'],
        fallback=case['fallback_recommendation'],
      )
    )
  lines.extend(['', '## Fixture notes', ''])
  for case in summary['fixture_matrix']:
    inspection = case['inspection'] or {}
    lines.extend(
      [
        '### `{scenario}`'.format(scenario=case['scenario_id']),
        '',
        '- trace summary: {summary}'.format(summary=case['trace']['summary']),
        '- inspection summary: {summary}'.format(
          summary=inspection.get('summary', 'No inspection summary recorded.')
        ),
        '- fallback recommendation: `{fallback}`'.format(
          fallback=case['fallback_recommendation']
        ),
        '- classified issue family: `{family}` ({confidence})'.format(
          family=case['classification']['family'],
          confidence=case['classification']['confidence'],
        ),
        '',
      ]
    )
  live_suite = summary['live_command_suite']
  known_issue = summary['live_known_issue_selector']
  lines.extend(['## Known-issue selector', ''])
  lines.append('- dominant family: `{family}`'.format(family=known_issue['family']))
  lines.append('- confidence: `{confidence}`'.format(confidence=known_issue['confidence']))
  lines.append('- summary: {summary}'.format(summary=known_issue['summary']))
  if known_issue.get('next_steps'):
    lines.extend(['', '### Next steps', ''])
    for step in known_issue['next_steps']:
      lines.append('- ' + str(step))
  lines.extend(['## Live PIT command suite', ''])
  lines.append('- status: `{status}`'.format(status=live_suite['status']))
  lines.append('- summary: {summary}'.format(summary=live_suite['summary']))
  if live_suite.get('executed'):
    print_pit = live_suite['print_pit']
    download_pit = live_suite['download_pit']
    lines.extend(
      [
        '',
        '### `print-pit`',
        '',
        '- trace state: `{state}`'.format(state=print_pit['trace']['state']),
        '- inspection state: `{state}`'.format(
          state=print_pit['inspection']['state']
        ),
        '- GUI disconnect heuristic: `{value}`'.format(
          value=print_pit['gui_disconnect_detected']
        ),
        '- fallback recommendation: `{value}`'.format(
          value=print_pit['fallback_recommendation']
        ),
        '- classified issue family: `{family}` ({confidence})'.format(
          family=print_pit['classification']['family'],
          confidence=print_pit['classification']['confidence'],
        ),
        '',
        '### `download-pit`',
        '',
        '- trace state: `{state}`'.format(state=download_pit['trace']['state']),
        '- inspection state: `{state}`'.format(
          state=download_pit['inspection']['state']
        ),
        '- fallback recommendation: `{value}`'.format(
          value=download_pit['fallback_recommendation']
        ),
        '- classified issue family: `{family}` ({confidence})'.format(
          family=download_pit['classification']['family'],
          confidence=download_pit['classification']['confidence'],
        ),
        '- output path: `{path}`'.format(path=download_pit['output_path']),
      ]
    )
  if live_suite.get('notes'):
    lines.extend(['', '### Notes', ''])
    for note in live_suite['notes']:
      lines.append('- ' + str(note))
  lines.extend(['', '## Findings', ''])
  for finding in summary['findings']:
    lines.append('- ' + finding)
  return '\n'.join(lines)


def _write_summary_files(summary: Mapping[str, object], archive_root: Path) -> None:
  """Write the JSON and Markdown diagnostic summaries."""

  archive_root.mkdir(parents=True, exist_ok=True)
  (archive_root / 'pit_transport_diagnostic.json').write_text(
    json.dumps(summary, indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
  )
  (archive_root / 'pit_transport_diagnostic.md').write_text(
    render_pit_transport_markdown(summary) + '\n',
    encoding='utf-8',
  )


def main(argv: Optional[Sequence[str]] = None) -> int:
  """Run the broad PIT transport diagnostic and write its report archive."""

  parser = argparse.ArgumentParser(
    description='Run the PIT transport diagnostic across runtime, parser, and fallback paths.',
  )
  parser.add_argument(
    '--run-live-commands',
    action='store_true',
    help='Execute live integrated-runtime print-pit and download-pit subprocesses in addition to the deterministic matrix.',
  )
  args = parser.parse_args(argv)

  archive_root = ARCHIVE_ROOT / _utc_timestamp()
  runtime_probe = probe_heimdall_runtime()
  summary = build_pit_transport_summary(
    runtime_probe,
    archive_root,
    run_live_commands=args.run_live_commands,
  )
  _write_summary_files(summary, archive_root)

  print('archive_root="{root}"'.format(root=archive_root))
  print('runtime_available="{value}"'.format(value=summary['runtime_probe']['available']))
  print('fixture_case_count="{count}"'.format(count=len(summary['fixture_matrix'])))
  print('live_command_status="{status}"'.format(status=summary['live_command_suite']['status']))
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
