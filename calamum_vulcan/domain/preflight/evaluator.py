"""Rule evaluation for the Calamum Vulcan FS-04 preflight board."""

from __future__ import annotations

from typing import List
from typing import Optional

from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind

from .model import PreflightCategory
from .model import PreflightGate
from .model import PreflightInput
from .model import PreflightReport
from .model import PreflightSeverity
from .model import PreflightSignal


def evaluate_preflight(inputs: PreflightInput) -> PreflightReport:
  """Evaluate the current operator context into a preflight report."""

  signals = []  # type: List[PreflightSignal]

  signals.append(_host_signal(inputs))
  signals.append(_driver_signal(inputs))
  signals.append(_device_presence_signal(inputs))

  if inputs.device_present:
    signals.append(_device_registry_signal(inputs))
    signals.append(_device_mode_signal(inputs))
    signals.append(_battery_signal(inputs))
    signals.append(_cable_signal(inputs))

  if _pit_review_required(inputs):
    signals.append(_pit_required_signal(inputs))

  signals.append(_package_presence_signal(inputs))

  if inputs.package_selected:
    signals.append(_package_completeness_signal(inputs))
    signals.append(_checksum_signal(inputs))
    signals.append(_analyzed_snapshot_signal(inputs))
    signals.append(_package_suspiciousness_signal(inputs))

  if (
    inputs.device_present
    and inputs.package_selected
    and inputs.device_registry_known
  ):
    signals.append(_compatibility_signal(inputs))

  if inputs.pit_state not in (None, 'not_collected'):
    signals.append(_pit_state_signal(inputs))
    if inputs.pit_state not in ('failed', 'malformed'):
      pit_device_signal = _pit_device_alignment_signal(inputs)
      if pit_device_signal is not None:
        signals.append(pit_device_signal)
      pit_package_signal = _pit_package_alignment_signal(inputs)
      if pit_package_signal is not None:
        signals.append(pit_package_signal)

  signals.append(_destructive_ack_signal(inputs))

  warning_findings_present = any(
    signal.severity == PreflightSeverity.WARN for signal in signals
  )
  if inputs.device_present and inputs.package_selected:
    signals.append(
      _operator_acknowledgement_signal(inputs, warning_findings_present)
    )

  pass_count = _count_signals(signals, PreflightSeverity.PASS)
  warning_count = _count_signals(signals, PreflightSeverity.WARN)
  block_count = _count_signals(signals, PreflightSeverity.BLOCK)

  gate = _determine_gate(
    block_count,
    warning_count,
    warnings_acknowledged=inputs.warnings_acknowledged,
  )
  ready_for_execution = gate == PreflightGate.READY
  summary, recommended_action = _summary_for_gate(
    gate,
    warnings_acknowledged=inputs.warnings_acknowledged,
    warning_count=warning_count,
  )

  return PreflightReport(
    gate=gate,
    signals=tuple(signals),
    ready_for_execution=ready_for_execution,
    summary=summary,
    recommended_action=recommended_action,
    pass_count=pass_count,
    warning_count=warning_count,
    block_count=block_count,
  )


def _host_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.host_ready:
    return PreflightSignal(
      rule_id='host_runtime',
      category=PreflightCategory.HOST,
      severity=PreflightSeverity.PASS,
      title='Host runtime ready',
      summary='Host environment is available for a controlled flashing session.',
      remediation='No host action required.',
    )
  return PreflightSignal(
    rule_id='host_runtime',
    category=PreflightCategory.HOST,
    severity=PreflightSeverity.BLOCK,
    title='Host runtime unavailable',
    summary='The host environment is not ready for a flashing workflow.',
    remediation='Resolve the local runtime issue before opening the trust gate.',
  )


def _driver_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.driver_ready:
    return PreflightSignal(
      rule_id='usb_driver',
      category=PreflightCategory.HOST,
      severity=PreflightSeverity.PASS,
      title='USB driver surface ready',
      summary='Driver prerequisites are satisfied for the current review path.',
      remediation='No driver action required.',
    )
  return PreflightSignal(
    rule_id='usb_driver',
    category=PreflightCategory.HOST,
    severity=PreflightSeverity.BLOCK,
    title='USB driver surface blocked',
    summary='Driver readiness is insufficient for Samsung download-mode work.',
    remediation='Repair the USB driver path before allowing execution.',
  )


def _device_presence_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.device_present:
    return PreflightSignal(
      rule_id='device_presence',
      category=PreflightCategory.DEVICE,
      severity=PreflightSeverity.PASS,
      title='Device detected',
      summary='A Samsung device is present for preflight inspection.',
      remediation='No detection action required.',
    )
  return PreflightSignal(
    rule_id='device_presence',
    category=PreflightCategory.DEVICE,
    severity=PreflightSeverity.BLOCK,
    title='No device detected',
    summary='No Samsung download-mode device is currently attached.',
    remediation='Attach a compatible device before preflight can proceed.',
  )


def _device_mode_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.in_download_mode:
    return PreflightSignal(
      rule_id='device_mode',
      category=PreflightCategory.DEVICE,
      severity=PreflightSeverity.PASS,
      title='Download mode confirmed',
      summary='The current device is in the required Samsung flashing mode.',
      remediation='No mode change required.',
    )
  return PreflightSignal(
    rule_id='device_mode',
    category=PreflightCategory.DEVICE,
    severity=PreflightSeverity.BLOCK,
    title='Download mode missing',
    summary='The attached device is not yet in Samsung download mode.',
    remediation='Re-enter download mode before enabling any flash path.',
  )


def _device_registry_signal(inputs: PreflightInput) -> PreflightSignal:
  if not inputs.product_code:
    return PreflightSignal(
      rule_id='device_registry',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.BLOCK,
      title='Device product code missing',
      summary='The attached device did not produce a product code for registry-backed review.',
      remediation='Re-detect the device before allowing compatibility checks.',
    )
  if not inputs.device_registry_known:
    return PreflightSignal(
      rule_id='device_registry',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.BLOCK,
      title='Device profile unknown',
      summary='The repo-owned device registry does not recognize {product_code}.'.format(
        product_code=inputs.product_code,
      ),
      remediation='Add or confirm a supported device-registry profile before execution.',
    )
  if inputs.device_registry_match_kind == DeviceRegistryMatchKind.ALIAS:
    return PreflightSignal(
      rule_id='device_registry',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.PASS,
      title='Device profile resolved via alias',
      summary='{detected} resolves to {canonical} ({name}) in the device registry.'.format(
        detected=inputs.product_code,
        canonical=inputs.canonical_product_code or inputs.product_code,
        name=inputs.device_marketing_name or 'Samsung device',
      ),
      remediation='No registry action required.',
    )
  return PreflightSignal(
    rule_id='device_registry',
    category=PreflightCategory.COMPATIBILITY,
    severity=PreflightSeverity.PASS,
    title='Device profile resolved',
    summary='The device registry recognizes {name} ({product_code}).'.format(
      name=inputs.device_marketing_name or 'Samsung device',
      product_code=inputs.canonical_product_code or inputs.product_code,
    ),
    remediation='No registry action required.',
  )


def _battery_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.battery_level is None:
    return PreflightSignal(
      rule_id='battery_level',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.WARN,
      title='Battery level unknown',
      summary='Battery telemetry is unavailable for the current device.',
      remediation='Verify device charge manually before execution.',
    )
  if inputs.battery_level < 15:
    return PreflightSignal(
      rule_id='battery_level',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.BLOCK,
      title='Battery too low',
      summary='Battery level is below the safe threshold for flashing.',
      remediation='Charge the device above the minimum threshold before continuing.',
    )
  if inputs.battery_level < 30:
    return PreflightSignal(
      rule_id='battery_level',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.WARN,
      title='Battery guidance warning',
      summary='Battery level is low enough to justify operator caution.',
      remediation='Prefer a higher charge level before proceeding.',
    )
  return PreflightSignal(
    rule_id='battery_level',
    category=PreflightCategory.SAFETY,
    severity=PreflightSeverity.PASS,
    title='Battery guidance satisfied',
    summary='Battery level is adequate for the reviewed workflow.',
    remediation='No battery action required.',
  )


def _cable_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.cable_quality == 'unstable':
    return PreflightSignal(
      rule_id='cable_path',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.BLOCK,
      title='USB path unstable',
      summary='The current cable or hub path is not trustworthy enough to flash safely.',
      remediation='Move to a stable direct USB path before proceeding.',
    )
  if inputs.cable_quality == 'unknown':
    return PreflightSignal(
      rule_id='cable_path',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.WARN,
      title='USB path unverified',
      summary='Cable quality is not yet known-good for flashing.',
      remediation='Prefer a direct, known-good cable and avoid flaky hubs.',
    )
  return PreflightSignal(
    rule_id='cable_path',
    category=PreflightCategory.SAFETY,
    severity=PreflightSeverity.PASS,
    title='USB path stable',
    summary='The current USB path is acceptable for the reviewed session.',
    remediation='No cable action required.',
  )


def _package_presence_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.package_selected:
    return PreflightSignal(
      rule_id='package_selected',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.PASS,
      title='Package selected',
      summary='A package is staged for compatibility and integrity review.',
      remediation='No package-selection action required.',
    )
  return PreflightSignal(
    rule_id='package_selected',
    category=PreflightCategory.PACKAGE,
    severity=PreflightSeverity.BLOCK,
    title='No package selected',
    summary='No firmware package is available to evaluate or execute.',
    remediation='Load a package before opening the trust gate.',
  )


def _package_completeness_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.package_complete:
    return PreflightSignal(
      rule_id='package_manifest',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.PASS,
      title='Package metadata complete',
      summary='Current package metadata is sufficient for preflight review.',
      remediation='No manifest action required.',
    )
  return PreflightSignal(
    rule_id='package_manifest',
    category=PreflightCategory.PACKAGE,
    severity=PreflightSeverity.BLOCK,
    title='Package metadata incomplete',
    summary='Package manifest data is insufficient for a trusted flash plan.',
    remediation='Supply complete package metadata before execution.',
  )


def _checksum_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.checksums_present:
    return PreflightSignal(
      rule_id='package_checksums',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.PASS,
      title='Checksums present',
      summary='Package integrity data exists for the staged package review path.',
      remediation='No checksum action required.',
    )
  return PreflightSignal(
    rule_id='package_checksums',
    category=PreflightCategory.PACKAGE,
    severity=PreflightSeverity.BLOCK,
    title='Checksums missing',
    summary='Package integrity data is absent for the current review path.',
    remediation='Provide checksum coverage before allowing execution.',
  )


def _analyzed_snapshot_signal(inputs: PreflightInput) -> PreflightSignal:
  if not inputs.snapshot_required:
    return PreflightSignal(
      rule_id='analyzed_snapshot',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.PASS,
      title='Analyzed snapshot deferred',
      summary='This review path does not yet require a sealed analyzed snapshot.',
      remediation='No analyzed-snapshot action required for the current fixture path.',
    )
  if not inputs.snapshot_created:
    return PreflightSignal(
      rule_id='analyzed_snapshot',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.BLOCK,
      title='Analyzed snapshot missing',
      summary='No sealed analyzed snapshot exists for the current reviewed package.',
      remediation='Seal a reviewed package snapshot before allowing execution.',
    )
  if inputs.snapshot_drift_detected or not inputs.snapshot_verified:
    return PreflightSignal(
      rule_id='analyzed_snapshot',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.BLOCK,
      title='Analyzed snapshot drift detected',
      summary='The reviewed package snapshot no longer matches the current execution input.',
      remediation='Re-import, re-seal, and re-verify the reviewed package before execution.',
    )
  return PreflightSignal(
    rule_id='analyzed_snapshot',
    category=PreflightCategory.PACKAGE,
    severity=PreflightSeverity.PASS,
    title='Analyzed snapshot verified',
    summary='The reviewed package snapshot was sealed and re-verified immediately before execution.',
    remediation='No analyzed-snapshot follow-up required.',
  )


def _package_suspiciousness_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.suspicious_warning_count <= 0:
    return PreflightSignal(
      rule_id='package_suspiciousness',
      category=PreflightCategory.PACKAGE,
      severity=PreflightSeverity.PASS,
      title='No suspicious Android traits surfaced',
      summary='The current package review did not surface warning-tier suspicious Android traits.',
      remediation='No suspiciousness follow-up required.',
    )
  return PreflightSignal(
    rule_id='package_suspiciousness',
    category=PreflightCategory.PACKAGE,
    severity=PreflightSeverity.WARN,
    title='Suspicious Android traits detected',
    summary=inputs.suspiciousness_summary,
    remediation='Review and explicitly acknowledge the warning-tier suspicious Android traits before execution.',
  )


def _compatibility_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.product_code_match:
    if (
      inputs.device_registry_match_kind == DeviceRegistryMatchKind.ALIAS
      and inputs.canonical_product_code is not None
    ):
      return PreflightSignal(
        rule_id='product_code_match',
        category=PreflightCategory.COMPATIBILITY,
        severity=PreflightSeverity.PASS,
        title='Product code matched through alias resolution',
        summary='The staged package matches detected {detected} through canonical device code {canonical}.'.format(
          detected=inputs.product_code,
          canonical=inputs.canonical_product_code,
        ),
        remediation='No compatibility action required.',
      )
    return PreflightSignal(
      rule_id='product_code_match',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.PASS,
      title='Product code matched',
      summary='The staged package is compatible with {name} ({product_code}).'.format(
        name=inputs.device_marketing_name or 'the detected device',
        product_code=inputs.canonical_product_code or inputs.product_code,
      ),
      remediation='No compatibility action required.',
    )
  return PreflightSignal(
    rule_id='product_code_match',
    category=PreflightCategory.COMPATIBILITY,
    severity=PreflightSeverity.BLOCK,
    title='Product code mismatch',
    summary='Package compatibility does not include {name} ({product_code}).'.format(
      name=inputs.device_marketing_name or 'the detected Samsung device',
      product_code=inputs.canonical_product_code or inputs.product_code or 'unknown',
    ),
    remediation='Switch to a package that explicitly supports the resolved device profile before continuing.',
  )


def _pit_review_required(inputs: PreflightInput) -> bool:
  """Return whether the current review path explicitly requires PIT truth."""

  return bool(
    inputs.pit_required
    and inputs.device_present
    and inputs.in_download_mode
    and inputs.pit_state in (None, 'not_collected')
  )


def _pit_required_signal(inputs: PreflightInput) -> PreflightSignal:
  """Return the missing-PIT prerequisite signal for bounded safe-path review."""

  return PreflightSignal(
    rule_id='pit_required',
    category=PreflightCategory.COMPATIBILITY,
    severity=PreflightSeverity.BLOCK,
    title='PIT review required',
    summary='Bounded safe-path review requires PIT truth before package or execute claims widen.',
    remediation='Run Read PIT before continuing the bounded safe-path workflow.',
  )


def _pit_state_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.pit_state == 'captured':
    return PreflightSignal(
      rule_id='pit_state',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.PASS,
      title='PIT inspection captured',
      summary='Observed PIT truth is available for bounded alignment review.',
      remediation='No PIT-state action required.',
    )
  if inputs.pit_state == 'partial':
    return PreflightSignal(
      rule_id='pit_state',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.WARN,
      title='PIT inspection partial',
      summary=(
        inputs.pit_summary
        or 'Observed PIT truth is only partially available; keep safe-path claims narrowed until PIT metadata and partition rows agree fully.'
      ),
      remediation='Keep PIT review bounded until metadata and partition rows agree fully.',
    )
  if inputs.pit_state == 'malformed':
    return PreflightSignal(
      rule_id='pit_state',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.BLOCK,
      title='PIT inspection malformed',
      summary=(
        inputs.pit_summary
        or 'Observed PIT truth did not satisfy the parser contract and cannot back a safe-path claim.'
      ),
      remediation='Resolve the malformed PIT output before continuing.',
    )
  if inputs.pit_state == 'failed':
    return PreflightSignal(
      rule_id='pit_state',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.BLOCK,
      title='PIT inspection failed',
      summary=(
        inputs.pit_summary
        or 'Observed PIT truth could not be captured reliably enough for safe-path review.'
      ),
      remediation='Re-run PIT acquisition only after the failure is understood and bounded.',
    )
  return PreflightSignal(
    rule_id='pit_state',
    category=PreflightCategory.COMPATIBILITY,
    severity=PreflightSeverity.WARN,
    title='PIT inspection unresolved',
    summary=(
      inputs.pit_summary
      or 'Observed PIT truth is not yet stable enough to widen the current safe-path claim.'
    ),
    remediation='Stabilize PIT inspection before widening safe-path claims.',
  )


def _pit_device_alignment_signal(
  inputs: PreflightInput,
) -> Optional[PreflightSignal]:
  if inputs.pit_device_alignment == 'matched':
    return PreflightSignal(
      rule_id='pit_device_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.PASS,
      title='PIT/device alignment matched',
      summary='Observed PIT product code agrees with the current session device identity.',
      remediation='No PIT/device follow-up required.',
    )
  if inputs.pit_device_alignment == 'mismatched':
    observed_product_code = inputs.pit_observed_product_code or 'unknown'
    return PreflightSignal(
      rule_id='pit_device_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.BLOCK,
      title='PIT/device alignment mismatch',
      summary='Observed PIT product code {product_code} does not match the current session device identity.'.format(
        product_code=observed_product_code,
      ),
      remediation='Do not proceed until the observed PIT product code agrees with the current session device identity.',
    )
  if inputs.pit_device_alignment == 'not_provided':
    return PreflightSignal(
      rule_id='pit_device_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.WARN,
      title='PIT/device alignment unresolved',
      summary='Observed PIT truth did not provide a comparable product code for device alignment review.',
      remediation='Capture clearer PIT identity before widening the safe-path claim.',
    )
  return None


def _pit_package_alignment_signal(
  inputs: PreflightInput,
) -> Optional[PreflightSignal]:
  if inputs.pit_package_alignment == 'matched':
    return PreflightSignal(
      rule_id='pit_package_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.PASS,
      title='PIT/package alignment matched',
      summary='Observed PIT fingerprint matches the reviewed package fingerprint.',
      remediation='No PIT/package follow-up required.',
    )
  if inputs.pit_package_alignment == 'mismatched':
    return PreflightSignal(
      rule_id='pit_package_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.BLOCK,
      title='PIT/package alignment mismatch',
      summary='Observed PIT fingerprint does not match the reviewed package fingerprint.',
      remediation='Do not proceed until the reviewed package PIT fingerprint matches the observed device PIT.',
    )
  if inputs.pit_package_alignment == 'missing_reviewed':
    return PreflightSignal(
      rule_id='pit_package_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.WARN,
      title='PIT/package alignment unresolved',
      summary='Reviewed package truth does not yet provide a usable PIT fingerprint for comparison.',
      remediation='Hydrate reviewed package PIT truth before widening the safe-path claim.',
    )
  if inputs.pit_package_alignment == 'missing_observed':
    return PreflightSignal(
      rule_id='pit_package_alignment',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.WARN,
      title='Observed PIT fingerprint missing',
      summary='Observed PIT output did not provide a usable PIT fingerprint for comparison.',
      remediation='Capture clearer PIT output before widening the safe-path claim.',
    )
  return None


def _destructive_ack_signal(inputs: PreflightInput) -> PreflightSignal:
  if not inputs.destructive_operation:
    return PreflightSignal(
      rule_id='destructive_ack',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.PASS,
      title='Standard risk path',
      summary='The current package does not require destructive-operation acknowledgement.',
      remediation='No destructive acknowledgement required.',
    )
  if inputs.destructive_acknowledged:
    return PreflightSignal(
      rule_id='destructive_ack',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.PASS,
      title='Destructive acknowledgement captured',
      summary='Operator acknowledgement exists for the destructive flash path.',
      remediation='No destructive-action follow-up required.',
    )
  return PreflightSignal(
    rule_id='destructive_ack',
    category=PreflightCategory.SAFETY,
    severity=PreflightSeverity.BLOCK,
    title='Destructive acknowledgement missing',
    summary='The current flash path is destructive and still needs explicit acknowledgement.',
    remediation='Capture destructive acknowledgement before enabling execution.',
  )


def _operator_acknowledgement_signal(
  inputs: PreflightInput,
  warning_findings_present: bool,
) -> PreflightSignal:
  if inputs.warnings_acknowledged:
    return PreflightSignal(
      rule_id='operator_acknowledgement',
      category=PreflightCategory.SAFETY,
      severity=PreflightSeverity.PASS,
      title='Operator acknowledgement captured',
      summary='The operator has acknowledged the current preflight posture.',
      remediation='No acknowledgement action required.',
    )
  if warning_findings_present:
    summary = 'Warnings remain visible and still need explicit operator acknowledgement.'
  else:
    summary = 'Operator acknowledgement is still pending before execution can begin.'
  return PreflightSignal(
    rule_id='operator_acknowledgement',
    category=PreflightCategory.SAFETY,
    severity=PreflightSeverity.WARN,
    title='Operator acknowledgement pending',
    summary=summary,
    remediation='Capture acknowledgement before enabling execution.',
  )


def _determine_gate(
  block_count: int,
  warning_count: int,
  warnings_acknowledged: bool,
) -> PreflightGate:
  if block_count > 0:
    return PreflightGate.BLOCKED
  if warning_count > 0:
    if warnings_acknowledged:
      return PreflightGate.READY
    return PreflightGate.WARN
  return PreflightGate.READY


def _summary_for_gate(
  gate: PreflightGate,
  warnings_acknowledged: bool,
  warning_count: int,
) -> tuple:
  if gate == PreflightGate.BLOCKED:
    return (
      'Preflight is blocked until blocking findings are resolved.',
      'Resolve the blocking findings before any flash action becomes available.',
    )
  if gate == PreflightGate.WARN:
    return (
      'Preflight has warnings that still require operator acknowledgement.',
      'Review and acknowledge the remaining warnings before execution.',
    )
  if warning_count > 0 and warnings_acknowledged:
    return (
      'Preflight warnings are acknowledged and the execution gate is open.',
      'Preserve the acknowledged warning evidence while reviewing the execution surface.',
    )
  return (
    'Preflight gate is open for the current device and package.',
    'The current session satisfies the preflight gate for execution.',
  )


def _count_signals(
  signals: List[PreflightSignal],
  severity: PreflightSeverity,
) -> int:
  return sum(1 for signal in signals if signal.severity == severity)