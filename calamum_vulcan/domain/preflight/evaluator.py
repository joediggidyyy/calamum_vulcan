"""Rule evaluation for the Calamum Vulcan FS-04 preflight board."""

from __future__ import annotations

from typing import List

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
    signals.append(_device_mode_signal(inputs))
    signals.append(_battery_signal(inputs))
    signals.append(_cable_signal(inputs))

  signals.append(_package_presence_signal(inputs))

  if inputs.package_selected:
    signals.append(_package_completeness_signal(inputs))
    signals.append(_checksum_signal(inputs))

  if inputs.device_present and inputs.package_selected:
    signals.append(_compatibility_signal(inputs))

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

  gate = _determine_gate(block_count, warning_count)
  ready_for_execution = gate == PreflightGate.READY
  summary, recommended_action = _summary_for_gate(gate)

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
      summary='Checksum placeholders or values exist for the staged package.',
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


def _compatibility_signal(inputs: PreflightInput) -> PreflightSignal:
  if inputs.product_code_match:
    return PreflightSignal(
      rule_id='product_code_match',
      category=PreflightCategory.COMPATIBILITY,
      severity=PreflightSeverity.PASS,
      title='Product code matched',
      summary='The staged package is compatible with the detected product code.',
      remediation='No compatibility action required.',
    )
  return PreflightSignal(
    rule_id='product_code_match',
    category=PreflightCategory.COMPATIBILITY,
    severity=PreflightSeverity.BLOCK,
    title='Product code mismatch',
    summary='Package compatibility does not match the detected Samsung product code.',
    remediation='Switch to a compatible package before continuing.',
  )


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
) -> PreflightGate:
  if block_count > 0:
    return PreflightGate.BLOCKED
  if warning_count > 0:
    return PreflightGate.WARN
  return PreflightGate.READY


def _summary_for_gate(gate: PreflightGate) -> tuple:
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
  return (
    'Preflight gate is open for the current device and package.',
    'The current session satisfies the preflight gate for execution.',
  )


def _count_signals(
  signals: List[PreflightSignal],
  severity: PreflightSeverity,
) -> int:
  return sum(1 for signal in signals if signal.severity == severity)