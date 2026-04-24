"""Calamum-owned supported-path runtime helpers for Sprint 6 execution."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Callable
from typing import Optional

from calamum_vulcan.adapters.heimdall import HeimdallCommandPlan
from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallProcessResult
from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.adapters.heimdall import apply_heimdall_trace
from calamum_vulcan.adapters.heimdall import build_flash_command_plan_from_reviewed_plan
from calamum_vulcan.adapters.heimdall import execute_heimdall_command
from calamum_vulcan.domain.flash_plan import ReviewedFlashPlan
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
from calamum_vulcan.domain.package import PackageManifestAssessment

from .model import PlatformSession
from .runtime import RuntimeSessionRejected
from .runtime import ensure_safe_path_runtime_ready
from .runtime import ensure_runtime_ready


ProcessRunner = Callable[[HeimdallCommandPlan], HeimdallProcessResult]
INTEGRATED_RUNTIME_BACKEND = 'integrated-runtime'


@dataclass(frozen=True)
class IntegratedRuntimeResult:
  """One supported-path runtime result normalized behind the integrated boundary."""

  session: PlatformSession
  trace: HeimdallNormalizedTrace
  command_plan: HeimdallCommandPlan
  reviewed_plan_id: str
  snapshot_id: Optional[str]
  execution_source: str
  runtime_policy: str = 'bounded_reviewed_flash_session'
  transcript_policy: str = 'preserve_bounded_transport_transcript'

  @property
  def summary(self) -> str:
    """Return one operator-facing supported-path summary."""

    return (
      'Calamum integrated runtime executed the supported-path session through '
      '{source} while keeping delegated lower-transport details packaged.'.format(
        source=self.execution_source.replace('_', ' '),
      )
    )


def build_integrated_reviewed_flash_plan(
  package_assessment: PackageManifestAssessment,
) -> ReviewedFlashPlan:
  """Return one reviewed flash plan for the Sprint 6 supported-path runtime."""

  return build_reviewed_flash_plan(
    package_assessment,
    transport_backend=INTEGRATED_RUNTIME_BACKEND,
  )


def integrated_command_display(command_plan: HeimdallCommandPlan) -> str:
  """Return the operator-visible supported-path command display."""

  return ' '.join((INTEGRATED_RUNTIME_BACKEND,) + command_plan.arguments)


def project_heimdall_trace_to_integrated_runtime(
  trace: HeimdallNormalizedTrace,
) -> HeimdallNormalizedTrace:
  """Project one delegated Heimdall trace onto the supported-path runtime boundary."""

  if getattr(trace, 'adapter_name', 'heimdall') == INTEGRATED_RUNTIME_BACKEND:
    return trace

  supported_command_plan = replace(
    trace.command_plan,
    executable=INTEGRATED_RUNTIME_BACKEND,
    display_command=integrated_command_display(trace.command_plan),
  )
  return replace(
    trace,
    command_plan=supported_command_plan,
    summary=_integrated_summary(trace),
    notes=_integrated_notes(trace),
    adapter_name=INTEGRATED_RUNTIME_BACKEND,
  )


def execute_integrated_command(
  command_plan: HeimdallCommandPlan,
  runner: Optional[ProcessRunner] = None,
  fixture_name: str = 'live-process',
) -> HeimdallNormalizedTrace:
  """Execute one supported-path command while reusing the packaged lower transport."""

  return project_heimdall_trace_to_integrated_runtime(
    execute_heimdall_command(
      command_plan,
      runner=runner,
      fixture_name=fixture_name,
    )
  )


def run_integrated_flash_session(
  session: PlatformSession,
  reviewed_flash_plan: ReviewedFlashPlan,
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
  runner: Optional[ProcessRunner] = None,
  fixture_name: str = 'live-process',
) -> IntegratedRuntimeResult:
  """Run one supported-path flash session behind the integrated runtime boundary."""

  if reviewed_flash_plan.transport_backend != INTEGRATED_RUNTIME_BACKEND:
    raise RuntimeSessionRejected(
      'Integrated runtime requires a reviewed flash plan for the integrated-runtime backend.'
    )
  if not reviewed_flash_plan.ready_for_transport:
    raise RuntimeSessionRejected(
      'Integrated runtime requires a transport-ready reviewed flash plan.'
    )
  if (
    reviewed_flash_plan.source_kind != 'fixture'
    and reviewed_flash_plan.snapshot_id is None
  ):
    raise RuntimeSessionRejected(
      'Integrated runtime requires a reviewed snapshot identity.'
    )

  ensure_runtime_ready(session)
  ensure_safe_path_runtime_ready(
    session,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
  )
  command_plan = build_flash_command_plan_from_reviewed_plan(reviewed_flash_plan)
  trace = execute_integrated_command(
    command_plan,
    runner=runner,
    fixture_name=fixture_name,
  )
  execution_source = 'explicit_runner' if runner is not None else 'bounded_subprocess'
  return IntegratedRuntimeResult(
    session=apply_heimdall_trace(session, trace),
    trace=trace,
    command_plan=command_plan,
    reviewed_plan_id=reviewed_flash_plan.plan_id,
    snapshot_id=reviewed_flash_plan.snapshot_id,
    execution_source=execution_source,
  )


def _integrated_summary(trace: HeimdallNormalizedTrace) -> str:
  """Return one supported-path summary that hides the delegated boundary from control surfaces."""

  operation = trace.command_plan.operation
  if operation == HeimdallOperation.FLASH:
    if trace.state == HeimdallTraceState.COMPLETED:
      return (
        'Calamum integrated runtime completed the supported-path flash session '
        'and preserved delegated lower-transport transcript details.'
      )
    if trace.state == HeimdallTraceState.RESUME_NEEDED:
      return (
        'Calamum integrated runtime paused for manual recovery before the '
        'supported-path flash session can continue.'
      )
    if trace.state == HeimdallTraceState.FAILED:
      return (
        'Calamum integrated runtime normalized a delegated lower-transport '
        'failure into supported-path execution state.'
      )
    if trace.state == HeimdallTraceState.EXECUTING:
      return (
        'Calamum integrated runtime started the supported-path flash session '
        'and is preserving delegated lower-transport progress markers.'
      )
  if operation in (
    HeimdallOperation.PRINT_PIT,
    HeimdallOperation.DOWNLOAD_PIT,
  ):
    if trace.state == HeimdallTraceState.FAILED:
      return (
        'Calamum integrated runtime could not capture bounded PIT truth before '
        'repo-owned inspection could continue.'
      )
    return (
      'Calamum integrated runtime captured bounded PIT truth while delegated '
      'lower-transport details remained packaged.'
    )
  if operation == HeimdallOperation.DETECT:
    if trace.state == HeimdallTraceState.DETECTED:
      return (
        'Calamum integrated runtime verified Samsung download-mode presence '
        'and preserved delegated lower-transport probe details.'
      )
    return (
      'Calamum integrated runtime could not verify Samsung download-mode '
      'presence from the delegated lower-transport probe.'
    )
  return (
    'Calamum integrated runtime preserved delegated lower-transport details '
    'behind the supported-path boundary.'
  )


def _integrated_notes(trace: HeimdallNormalizedTrace) -> tuple[str, ...]:
  """Return one deduplicated supported-path note set."""

  values = [
    'Calamum integrated runtime owns the operator-visible supported path for this action.',
    'Delegated lower-transport internals remain packaged behind the supported path.',
    'Delegated lower-transport command: {command}'.format(
      command=trace.command_plan.display_command,
    ),
  ]
  values.extend(trace.notes)
  deduped = []
  for value in values:
    if value not in deduped:
      deduped.append(value)
  return tuple(deduped)