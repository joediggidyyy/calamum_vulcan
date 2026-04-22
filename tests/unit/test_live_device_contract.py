"""Unit tests for the repo-owned live-device contract."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_fastboot_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
from calamum_vulcan.adapters.heimdall import HeimdallOperation
from calamum_vulcan.adapters.heimdall import HeimdallProcessResult
from calamum_vulcan.adapters.heimdall import build_detect_device_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.domain.live_device import LiveDeviceInfoState
from calamum_vulcan.domain.live_device import LiveIdentityConfidence
from calamum_vulcan.domain.live_device import LiveDetectionState
from calamum_vulcan.domain.live_device import LivePathOwnership
from calamum_vulcan.domain.live_device import LiveDeviceSource
from calamum_vulcan.domain.live_device import LiveDeviceSupportPosture
from calamum_vulcan.domain.live_device import LiveFallbackPosture
from calamum_vulcan.domain.live_device import apply_live_device_info_trace
from calamum_vulcan.domain.live_device import build_heimdall_live_detection_session
from calamum_vulcan.domain.live_device import build_live_detection_session
from calamum_vulcan.fixtures import load_heimdall_process_fixture


class LiveDeviceContractTests(unittest.TestCase):
  """Prove FS3-03 live detection/info semantics stay repo-owned and explicit."""

  def test_heimdall_detect_trace_builds_supported_download_mode_snapshot(self) -> None:
    trace = normalize_heimdall_result(
      build_detect_device_command_plan(),
      load_heimdall_process_fixture('detect-ready'),
    )

    detection = build_heimdall_live_detection_session(trace)

    self.assertEqual(detection.state, LiveDetectionState.DETECTED)
    self.assertEqual(detection.source, LiveDeviceSource.HEIMDALL)
    self.assertTrue(detection.device_present)
    self.assertTrue(detection.command_ready)
    self.assertIsNotNone(detection.snapshot)
    self.assertEqual(detection.snapshot.mode, 'heimdall/download')
    self.assertEqual(detection.snapshot.transport, 'download-mode')
    self.assertEqual(detection.snapshot.product_code, 'SM-G991U')
    self.assertEqual(
      detection.snapshot.support_posture,
      LiveDeviceSupportPosture.SUPPORTED,
    )
    self.assertEqual(detection.snapshot.marketing_name, 'Galaxy S21')
    self.assertEqual(
      detection.snapshot.info_state,
      LiveDeviceInfoState.UNAVAILABLE,
    )
    self.assertIn('heimdall_print_pit', detection.snapshot.capability_hints)
    self.assertEqual(
      detection.path_identity.path_label,
      'Heimdall Download-Mode Session',
    )

  def test_heimdall_missing_device_can_clear_after_unified_probe(self) -> None:
    trace = normalize_heimdall_result(
      build_detect_device_command_plan(),
      HeimdallProcessResult(
        fixture_name='detect-none',
        operation=HeimdallOperation.DETECT,
        exit_code=1,
        stderr_lines=('ERROR: Failed to detect compatible download-mode device',),
      ),
    )

    detection = build_heimdall_live_detection_session(
      trace,
      source_labels=('adb', 'fastboot', 'heimdall'),
      treat_missing_device_as_cleared=True,
    )

    self.assertEqual(detection.state, LiveDetectionState.CLEARED)
    self.assertEqual(detection.source, LiveDeviceSource.HEIMDALL)
    self.assertFalse(detection.device_present)
    self.assertEqual(detection.path_identity.path_label, 'No Download-Mode Device')
    self.assertIn(
      'No live device detected after checking ADB, fastboot, and Heimdall.',
      detection.summary,
    )

  def test_adb_ready_trace_builds_supported_command_ready_snapshot(self) -> None:
    trace = normalize_android_tools_result(
      build_adb_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='adb-ready',
        operation=AndroidToolsOperation.ADB_DEVICES,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          'List of devices attached',
          'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
        ),
      ),
    )

    detection = build_live_detection_session(trace)

    self.assertEqual(detection.state, LiveDetectionState.DETECTED)
    self.assertEqual(detection.source, LiveDeviceSource.ADB)
    self.assertTrue(detection.device_present)
    self.assertTrue(detection.command_ready)
    self.assertIsNotNone(detection.snapshot)
    self.assertEqual(
      detection.snapshot.support_posture,
      LiveDeviceSupportPosture.SUPPORTED,
    )
    self.assertEqual(detection.snapshot.marketing_name, 'Galaxy S21')
    self.assertEqual(detection.snapshot.mode, 'adb/device')
    self.assertEqual(
      detection.snapshot.info_state,
      LiveDeviceInfoState.NOT_COLLECTED,
    )

  def test_adb_unauthorized_trace_enters_attention_state(self) -> None:
    trace = normalize_android_tools_result(
      build_adb_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='adb-unauthorized',
        operation=AndroidToolsOperation.ADB_DEVICES,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          'List of devices attached',
          'R58N12345AB\tunauthorized usb:1-1 model:SM_G991U device:dm3q',
        ),
      ),
    )

    detection = build_live_detection_session(trace)

    self.assertEqual(detection.state, LiveDetectionState.ATTENTION)
    self.assertFalse(detection.command_ready)
    self.assertTrue(detection.device_present)
    self.assertEqual(
      detection.snapshot.info_state,
      LiveDeviceInfoState.UNAVAILABLE,
    )
    self.assertTrue(any('command-ready' in note for note in detection.notes))

  def test_adb_no_device_marks_fallback_needed(self) -> None:
    trace = normalize_android_tools_result(
      build_adb_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='adb-none',
        operation=AndroidToolsOperation.ADB_DEVICES,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=('List of devices attached',),
      ),
    )

    detection = build_live_detection_session(
      trace,
      fallback_posture=LiveFallbackPosture.NEEDED,
      fallback_reason='ADB did not establish a live device; fastboot should be checked next.',
      source_labels=('adb', 'fastboot'),
    )

    self.assertEqual(detection.state, LiveDetectionState.CLEARED)
    self.assertFalse(detection.device_present)
    self.assertEqual(detection.fallback_posture, LiveFallbackPosture.NEEDED)
    self.assertEqual(detection.source_labels, ('adb', 'fastboot'))
    self.assertIn('Fastboot fallback is recommended.', detection.summary)
    self.assertEqual(detection.path_identity.ownership, LivePathOwnership.DELEGATED)
    self.assertEqual(detection.path_identity.path_label, 'Fallback Check Pending')
    self.assertEqual(
      detection.path_identity.delegated_path_label,
      'adb -> fastboot handoff',
    )

  def test_fastboot_fallback_detects_device_with_identity_incomplete_posture(self) -> None:
    trace = normalize_android_tools_result(
      build_fastboot_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='fastboot-ready',
        operation=AndroidToolsOperation.FASTBOOT_DEVICES,
        backend=AndroidToolsBackend.FASTBOOT,
        exit_code=0,
        stdout_lines=('FASTBOOT123\tfastboot',),
      ),
    )

    detection = build_live_detection_session(
      trace,
      fallback_posture=LiveFallbackPosture.ENGAGED,
      fallback_reason='ADB did not establish a live device; fastboot captured the active companion.',
      source_labels=('adb', 'fastboot'),
    )

    self.assertEqual(detection.state, LiveDetectionState.DETECTED)
    self.assertEqual(detection.fallback_posture, LiveFallbackPosture.ENGAGED)
    self.assertIsNotNone(detection.snapshot)
    self.assertEqual(detection.snapshot.source, LiveDeviceSource.FASTBOOT)
    self.assertEqual(
      detection.snapshot.support_posture,
      LiveDeviceSupportPosture.IDENTITY_INCOMPLETE,
    )
    self.assertEqual(detection.snapshot.mode, 'fastboot/fastboot')
    self.assertEqual(
      detection.snapshot.info_state,
      LiveDeviceInfoState.UNAVAILABLE,
    )
    self.assertEqual(detection.path_identity.ownership, LivePathOwnership.FALLBACK)
    self.assertEqual(detection.path_identity.path_label, 'Fastboot Fallback Session')
    self.assertEqual(
      detection.path_identity.identity_confidence,
      LiveIdentityConfidence.SERIAL_ONLY,
    )
    self.assertIn('serial-only', detection.path_identity.summary)

  def test_fastboot_identity_tokens_can_resolve_supported_profile(self) -> None:
    trace = normalize_android_tools_result(
      build_fastboot_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='fastboot-profiled',
        operation=AndroidToolsOperation.FASTBOOT_DEVICES,
        backend=AndroidToolsBackend.FASTBOOT,
        exit_code=0,
        stdout_lines=(
          'FASTBOOT123\tfastboot product:dm3q model:SM_G991U device:dm3q',
        ),
      ),
    )

    detection = build_live_detection_session(
      trace,
      fallback_posture=LiveFallbackPosture.ENGAGED,
      fallback_reason='ADB did not establish a live device; fastboot captured the active companion.',
      source_labels=('adb', 'fastboot'),
    )

    self.assertIsNotNone(detection.snapshot)
    self.assertEqual(
      detection.snapshot.support_posture,
      LiveDeviceSupportPosture.SUPPORTED,
    )
    self.assertEqual(detection.snapshot.marketing_name, 'Galaxy S21')
    self.assertEqual(
      detection.path_identity.identity_confidence,
      LiveIdentityConfidence.PROFILED,
    )
    self.assertIn('Fastboot fallback resolved Galaxy S21', detection.path_identity.summary)

  def test_adb_info_trace_enriches_ready_detection_with_bounded_snapshot(self) -> None:
    detection = build_live_detection_session(
      normalize_android_tools_result(
        build_adb_detect_command_plan(),
        AndroidToolsProcessResult(
          fixture_name='adb-ready',
          operation=AndroidToolsOperation.ADB_DEVICES,
          backend=AndroidToolsBackend.ADB,
          exit_code=0,
          stdout_lines=(
            'List of devices attached',
            'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
          ),
        ),
      )
    )
    info_trace = normalize_android_tools_result(
      build_adb_device_info_command_plan(device_serial='R58N12345AB'),
      AndroidToolsProcessResult(
        fixture_name='adb-info-ready',
        operation=AndroidToolsOperation.ADB_GETPROP,
        backend=AndroidToolsBackend.ADB,
        exit_code=0,
        stdout_lines=(
          '[ro.product.manufacturer]: [samsung]',
          '[ro.product.brand]: [samsung]',
          '[ro.product.model]: [SM-G991U]',
          '[ro.product.device]: [dm3q]',
          '[ro.build.version.release]: [14]',
          '[ro.build.id]: [UP1A.231005.007]',
          '[ro.build.version.security_patch]: [2026-04-05]',
          '[ro.build.fingerprint]: [samsung/dm3q/dm3q:14/UP1A.231005.007/9910001:user/release-keys]',
          '[ro.bootloader]: [G991USQS9HYD1]',
        ),
      ),
    )

    enriched = apply_live_device_info_trace(detection, info_trace)

    self.assertIsNotNone(enriched.snapshot)
    self.assertEqual(enriched.snapshot.info_state, LiveDeviceInfoState.CAPTURED)
    self.assertEqual(enriched.snapshot.manufacturer, 'samsung')
    self.assertEqual(enriched.snapshot.android_version, '14')
    self.assertEqual(enriched.snapshot.security_patch, '2026-04-05')
    self.assertIn('bounded_info_snapshot_ready', enriched.snapshot.capability_hints)
    self.assertTrue(
      any('read-side guidance only' in guidance for guidance in enriched.snapshot.operator_guidance)
    )

  def test_failed_detect_trace_preserves_failure_state_without_snapshot(self) -> None:
    trace = normalize_android_tools_result(
      build_adb_detect_command_plan(),
      AndroidToolsProcessResult(
        fixture_name='adb-failed',
        operation=AndroidToolsOperation.ADB_DEVICES,
        backend=AndroidToolsBackend.ADB,
        exit_code=1,
        stderr_lines=('adb executable not found',),
      ),
    )

    detection = build_live_detection_session(trace)

    self.assertEqual(detection.state, LiveDetectionState.FAILED)
    self.assertFalse(detection.device_present)
    self.assertIsNone(detection.snapshot)
    self.assertTrue(any('adb executable not found' in note for note in detection.notes))

  def test_unparsed_heimdall_detect_output_stays_failed_not_cleared(self) -> None:
    trace = normalize_heimdall_result(
      build_detect_device_command_plan(),
      HeimdallProcessResult(
        fixture_name='detect-unparsed',
        operation=HeimdallOperation.DETECT,
        exit_code=0,
        stdout_lines=(
          'Detecting device...',
          'Device connected but product identity could not be normalized from this fixture.',
        ),
      ),
    )

    detection = build_heimdall_live_detection_session(
      trace,
      source_labels=('adb', 'fastboot', 'heimdall'),
      treat_missing_device_as_cleared=True,
    )

    self.assertEqual(detection.state, LiveDetectionState.FAILED)
    self.assertFalse(detection.device_present)
    self.assertIsNone(detection.snapshot)
    self.assertIn('could not normalize a trustworthy Samsung download-mode identity', detection.summary)
    self.assertTrue(
      any('Review raw Heimdall stdout/stderr' in note for note in detection.notes)
    )

  def test_heimdall_detect_with_late_runtime_warning_preserves_snapshot_but_marks_attention(self) -> None:
    trace = normalize_heimdall_result(
      build_detect_device_command_plan(),
      load_heimdall_process_fixture('detect-late-warning'),
    )

    detection = build_heimdall_live_detection_session(
      trace,
      source_labels=('adb', 'fastboot', 'heimdall'),
      treat_missing_device_as_cleared=True,
    )

    self.assertEqual(detection.state, LiveDetectionState.ATTENTION)
    self.assertTrue(detection.device_present)
    self.assertIsNotNone(detection.snapshot)
    self.assertEqual(detection.snapshot.product_code, 'SM-G991U')
    self.assertIn('later transport warning', detection.summary)


if __name__ == '__main__':
  unittest.main()
