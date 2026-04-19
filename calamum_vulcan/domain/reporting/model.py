"""Session evidence and reporting contracts for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple


REPORT_SCHEMA_VERSION = '0.1.0'
REPORT_EXPORT_TARGETS = ('json', 'markdown')

REQUIRED_SESSION_REPORT_FIELDS = (
  'schema_version',
  'report_id',
  'captured_at_utc',
  'scenario_name',
  'session_phase',
  'summary',
  'host',
  'device',
  'package',
  'preflight',
  'transport',
  'outcome',
  'decision_trace',
  'log_lines',
)

OPTIONAL_SESSION_REPORT_FIELDS = (
  'failure_reason',
  'package_contract_issues',
)


@dataclass(frozen=True)
class HostEnvironmentEvidence:
  """Host/runtime summary captured in the session evidence bundle."""

  runtime: str
  platform: str
  execution_posture: str
  export_targets: Tuple[str, ...] = REPORT_EXPORT_TARGETS


@dataclass(frozen=True)
class DeviceEvidence:
  """Device identity fields carried into the reporting layer."""

  device_present: bool
  device_id: Optional[str]
  product_code: Optional[str]
  mode: Optional[str]


@dataclass(frozen=True)
class PackageEvidence:
  """Package summary fields carried into the reporting layer."""

  fixture_name: Optional[str]
  package_id: str
  display_name: str
  version: str
  source_build: str
  risk_level: str
  compatibility_expectation: str
  contract_complete: bool
  issue_count: int
  partition_count: int
  checksum_count: int
  contract_issues: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PreflightEvidence:
  """Preflight summary fields carried into the reporting layer."""

  gate: str
  ready_for_execution: bool
  summary: str
  recommended_action: str
  pass_count: int
  warning_count: int
  block_count: int


@dataclass(frozen=True)
class TransportEvidence:
  """Normalized adapter surface carried into the reporting layer."""

  adapter_name: str
  capability: str
  command_display: str
  state: str
  summary: str
  exit_code: Optional[int]
  normalized_event_count: int
  progress_markers: Tuple[str, ...] = ()
  notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class OutcomeEvidence:
  """Outcome and recovery guidance recorded for one session."""

  outcome: str
  export_ready: bool
  next_action: str
  failure_reason: Optional[str] = None
  recovery_guidance: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionTraceEntry:
  """One decision-trace statement recorded for operator review."""

  source: str
  label: str
  summary: str
  severity: str = 'info'


@dataclass(frozen=True)
class SessionEvidenceReport:
  """Structured session evidence for shell display and export surfaces."""

  schema_version: str
  report_id: str
  captured_at_utc: str
  scenario_name: str
  session_phase: str
  summary: str
  host: HostEnvironmentEvidence
  device: DeviceEvidence
  package: PackageEvidence
  preflight: PreflightEvidence
  transport: TransportEvidence
  outcome: OutcomeEvidence
  decision_trace: Tuple[DecisionTraceEntry, ...]
  log_lines: Tuple[str, ...]

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this evidence bundle."""

    return asdict(self)