"""Session evidence and reporting contracts for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple


REPORT_SCHEMA_VERSION = '0.3.0-fs3-05'
REPORT_EXPORT_TARGETS = ('json', 'markdown')

REQUIRED_SESSION_REPORT_FIELDS = (
  'schema_version',
  'report_id',
  'captured_at_utc',
  'scenario_name',
  'session_phase',
  'summary',
  'host',
  'inspection',
  'device',
  'pit',
  'package',
  'flash_plan',
  'preflight',
  'transport',
  'transcript',
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
class InspectionWorkflowEvidence:
  """Inspect-only read-side workflow posture carried into reporting."""

  posture: str
  summary: str
  detect_ran: bool
  info_ran: bool
  pit_ran: bool
  evidence_ready: bool
  next_action: str
  read_side_only: bool = True
  action_boundaries: Tuple[str, ...] = ()
  notes: Tuple[str, ...] = ()
  captured_at_utc: Optional[str] = None


@dataclass(frozen=True)
class LiveDeviceEvidence:
  """Live detection and identity fields carried into the reporting layer."""

  state: str
  summary: str
  source: Optional[str]
  source_labels: Tuple[str, ...] = ()
  fallback_posture: str = 'not_needed'
  fallback_reason: Optional[str] = None
  device_present: bool = False
  command_ready: bool = False
  support_posture: str = 'identity_incomplete'
  serial: Optional[str] = None
  transport: Optional[str] = None
  product_code: Optional[str] = None
  canonical_product_code: Optional[str] = None
  marketing_name: Optional[str] = None
  registry_match_kind: str = 'unknown'
  mode: Optional[str] = None
  info_state: str = 'not_collected'
  info_source_label: Optional[str] = None
  manufacturer: Optional[str] = None
  brand: Optional[str] = None
  android_version: Optional[str] = None
  build_id: Optional[str] = None
  security_patch: Optional[str] = None
  build_fingerprint: Optional[str] = None
  bootloader_version: Optional[str] = None
  build_tags: Optional[str] = None
  capability_hints: Tuple[str, ...] = ()
  operator_guidance: Tuple[str, ...] = ()
  notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DeviceEvidence:
  """Device identity fields carried into the reporting layer."""

  device_present: bool
  device_id: Optional[str]
  product_code: Optional[str]
  canonical_product_code: Optional[str]
  marketing_name: Optional[str]
  registry_match_kind: str
  mode: Optional[str]
  mode_entry_instructions: Tuple[str, ...] = ()
  known_quirks: Tuple[str, ...] = ()
  live: LiveDeviceEvidence = field(
    default_factory=lambda: LiveDeviceEvidence(
      state='unhydrated',
      summary='No live device probe has run yet.',
      source=None,
    )
  )


@dataclass(frozen=True)
class PitEvidence:
  """PIT inspection fields carried into the reporting layer."""

  schema_version: str
  state: str
  source: Optional[str]
  summary: str
  fallback_posture: str = 'not_needed'
  fallback_reason: Optional[str] = None
  observed_product_code: Optional[str] = None
  canonical_product_code: Optional[str] = None
  marketing_name: Optional[str] = None
  registry_match_kind: str = 'unknown'
  observed_pit_fingerprint: Optional[str] = None
  reviewed_pit_fingerprint: Optional[str] = None
  package_alignment: str = 'not_reviewed'
  device_alignment: str = 'not_provided'
  download_path: Optional[str] = None
  entry_count: int = 0
  partition_names: Tuple[str, ...] = ()
  notes: Tuple[str, ...] = ()
  operator_guidance: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PackageEvidence:
  """Package summary fields carried into the reporting layer."""

  fixture_name: Optional[str]
  source_kind: str
  package_id: str
  display_name: str
  version: str
  source_build: str
  risk_level: str
  compatibility_expectation: str
  compatibility_summary: str
  contract_complete: bool
  issue_count: int
  partition_count: int
  checksum_count: int
  checksum_verification_complete: bool
  verified_checksum_count: int
  snapshot_id: Optional[str]
  snapshot_created_at_utc: Optional[str]
  snapshot_verified: bool
  snapshot_drift_detected: bool
  snapshot_issue_count: int
  suspicious_warning_count: int
  suspiciousness_summary: str
  suspicious_indicator_ids: Tuple[str, ...] = ()
  suspicious_titles: Tuple[str, ...] = ()
  contract_issues: Tuple[str, ...] = ()
  snapshot_issues: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FlashPlanEvidence:
  """Reviewed flash-plan evidence carried into the reporting layer."""

  schema_version: str
  plan_id: str
  summary: str
  source_kind: str
  package_id: str
  snapshot_id: Optional[str]
  ready_for_transport: bool
  transport_backend: str
  risk_level: str
  reboot_policy: str
  repartition_allowed: bool
  pit_fingerprint: str
  partition_count: int
  required_partition_count: int
  optional_partition_count: int
  verified_partition_count: int
  partition_targets: Tuple[str, ...] = ()
  partition_files: Tuple[str, ...] = ()
  required_capabilities: Tuple[str, ...] = ()
  advanced_requirements: Tuple[str, ...] = ()
  suspicious_warning_count: int = 0
  operator_warnings: Tuple[str, ...] = ()
  requires_operator_acknowledgement: bool = False
  blocking_reasons: Tuple[str, ...] = ()
  recovery_guidance: Tuple[str, ...] = ()


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
class TranscriptEvidence:
  """Transport-transcript retention fields carried into the reporting layer."""

  policy: str
  preserved: bool
  summary: str
  line_count: int
  stdout_line_count: int = 0
  stderr_line_count: int = 0
  progress_marker_count: int = 0
  note_count: int = 0
  reference_file_name: Optional[str] = None


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
  inspection: InspectionWorkflowEvidence
  device: DeviceEvidence
  pit: PitEvidence
  package: PackageEvidence
  flash_plan: FlashPlanEvidence
  preflight: PreflightEvidence
  transport: TransportEvidence
  transcript: TranscriptEvidence
  outcome: OutcomeEvidence
  decision_trace: Tuple[DecisionTraceEntry, ...]
  log_lines: Tuple[str, ...]

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this evidence bundle."""

    return asdict(self)