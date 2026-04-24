"""Unit tests for the Calamum Vulcan FS4-02 session-authority contract."""

from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.domain.live_device import LiveDetectionSession
from calamum_vulcan.domain.live_device import LiveDetectionState
from calamum_vulcan.domain.live_device import LiveDeviceInfoState
from calamum_vulcan.domain.live_device import LiveDeviceSnapshot
from calamum_vulcan.domain.live_device import LiveDeviceSource
from calamum_vulcan.domain.live_device import LiveDeviceSupportPosture
from calamum_vulcan.domain.live_device import LiveFallbackPosture
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.pit import PitDeviceAlignment
from calamum_vulcan.domain.pit import PitPackageAlignment
from calamum_vulcan.domain.safe_path import SafePathOwnership
from calamum_vulcan.domain.safe_path import SafePathReadiness
from calamum_vulcan.domain.state import SessionLaunchPath
from calamum_vulcan.domain.state import SessionPhase
from calamum_vulcan.domain.state import SessionRefreshState
from calamum_vulcan.domain.state import build_session_authority_snapshot


class SessionAuthorityContractTests(unittest.TestCase):
  """Prove the FS4-02 session-authority snapshot across core boundary cases."""

  def test_no_device_session_stays_on_standby(self) -> None:
    session = build_demo_session('no-device')

    authority = build_session_authority_snapshot(session)

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.STANDBY)
    self.assertEqual(authority.ownership, SafePathOwnership.BLOCKED)
    self.assertEqual(authority.readiness, SafePathReadiness.BLOCKED)
    self.assertIn('No Samsung download-mode device is currently attached.', authority.block_reason)
    self.assertEqual(authority.refresh_state, SessionRefreshState.FRESH)

  def test_ready_session_marks_bounded_safe_path_candidate(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)

    authority = build_session_authority_snapshot(
      session,
      package_assessment=package_assessment,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.SAFE_PATH_CANDIDATE)
    self.assertEqual(authority.ownership, SafePathOwnership.DELEGATED)
    self.assertEqual(authority.readiness, SafePathReadiness.READY)
    self.assertIsNone(authority.block_reason)
    self.assertIn('bounded safe-path candidate', authority.summary)

  def test_blocked_alignment_surfaces_explicit_block_reason(self) -> None:
    session = build_demo_session('blocked')
    package_assessment = build_demo_package_assessment('blocked', session=session)

    authority = build_session_authority_snapshot(
      session,
      package_assessment=package_assessment,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.BLOCKED)
    self.assertEqual(authority.ownership, SafePathOwnership.BLOCKED)
    self.assertEqual(authority.readiness, SafePathReadiness.BLOCKED)
    self.assertIn('Package compatibility does not include Galaxy S21', authority.block_reason)

  def test_fallback_review_lane_is_explicit_when_live_path_engages_fallback(self) -> None:
    session = build_demo_session('no-device')
    session = replace(
      session,
      live_detection=LiveDetectionSession(
        state=LiveDetectionState.DETECTED,
        summary='Fastboot captured the active companion after ADB did not establish a live device.',
        source=LiveDeviceSource.FASTBOOT,
        source_labels=('adb', 'fastboot'),
        fallback_posture=LiveFallbackPosture.ENGAGED,
        fallback_reason='ADB did not establish a live device; fastboot captured the active companion.',
        snapshot=LiveDeviceSnapshot(
          source=LiveDeviceSource.FASTBOOT,
          serial='R58N12345AB',
          connection_state='fastboot',
          transport='usb',
          mode='fastboot/fastboot',
          command_ready=True,
          product_code='SM-G991U',
          model_name='SM-G991U',
          device_name='o1q',
          canonical_product_code='SM-G991U',
          marketing_name='Galaxy S21',
          registry_match_kind='exact',
          support_posture=LiveDeviceSupportPosture.SUPPORTED,
          info_state=LiveDeviceInfoState.UNAVAILABLE,
        ),
      ),
    )

    authority = build_session_authority_snapshot(session)

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.FALLBACK_REVIEW)
    self.assertEqual(authority.ownership, SafePathOwnership.FALLBACK)
    self.assertTrue(authority.fallback_active)
    self.assertIn('fastboot captured the active companion', authority.block_reason)

  def test_direct_fastboot_review_stays_delegated_not_native(self) -> None:
    session = build_demo_session('no-device')
    session = replace(
      session,
      phase=SessionPhase.DEVICE_DETECTED,
      live_detection=LiveDetectionSession(
        state=LiveDetectionState.DETECTED,
        summary='Fastboot captured a delegated companion for review.',
        source=LiveDeviceSource.FASTBOOT,
        source_labels=('fastboot',),
        fallback_posture=LiveFallbackPosture.NOT_NEEDED,
        snapshot=LiveDeviceSnapshot(
          source=LiveDeviceSource.FASTBOOT,
          serial='FASTBOOT123',
          connection_state='fastboot',
          transport='usb',
          mode='fastboot/fastboot',
          command_ready=True,
          product_code='SM-G991U',
          model_name='SM-G991U',
          device_name='dm3q',
          canonical_product_code='SM-G991U',
          marketing_name='Galaxy S21',
          registry_match_kind='exact',
          support_posture=LiveDeviceSupportPosture.SUPPORTED,
          info_state=LiveDeviceInfoState.UNAVAILABLE,
        ),
      ),
    )

    preflight_report = evaluate_preflight(
      PreflightInput(
        device_present=True,
        in_download_mode=True,
        package_selected=True,
        package_complete=True,
        checksums_present=True,
        device_registry_known=True,
        product_code='SM-G991U',
        canonical_product_code='SM-G991U',
        device_marketing_name='Galaxy S21',
        product_code_match=True,
        warnings_acknowledged=True,
        battery_level=72,
        package_id='regional-match-demo',
      )
    )

    authority = build_session_authority_snapshot(
      session,
      preflight_report=preflight_report,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.REVIEW_ONLY)
    self.assertEqual(authority.ownership, SafePathOwnership.DELEGATED)

  def test_degraded_live_output_requests_refresh_and_narrows_readiness(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    session = replace(
      session,
      live_detection=LiveDetectionSession(
        state=LiveDetectionState.ATTENTION,
        summary='ADB detected a companion, but the current live output still needs operator attention.',
        source=LiveDeviceSource.ADB,
        source_labels=('adb',),
        fallback_posture=LiveFallbackPosture.NOT_NEEDED,
        snapshot=LiveDeviceSnapshot(
          source=LiveDeviceSource.ADB,
          serial='R58N12345AB',
          connection_state='offline',
          transport='usb',
          mode='adb/offline',
          command_ready=False,
          product_code='SM-G991U',
          model_name='SM-G991U',
          device_name='o1q',
          canonical_product_code='SM-G991U',
          marketing_name='Galaxy S21',
          registry_match_kind='exact',
          support_posture=LiveDeviceSupportPosture.SUPPORTED,
          info_state=LiveDeviceInfoState.UNAVAILABLE,
        ),
      ),
    )

    authority = build_session_authority_snapshot(
      session,
      package_assessment=package_assessment,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.SAFE_PATH_CANDIDATE)
    self.assertEqual(authority.readiness, SafePathReadiness.NARROWED)
    self.assertEqual(authority.refresh_state, SessionRefreshState.REFRESH_RECOMMENDED)
    self.assertIn('Refresh live detection', authority.refresh_reason)
    self.assertIn('needs operator attention', authority.block_reason)

  def test_download_mode_live_target_promotes_reviewed_target_label(self) -> None:
    session = build_demo_session('no-device')
    session = replace(
      session,
      live_detection=LiveDetectionSession(
        state=LiveDetectionState.DETECTED,
        summary='Native USB detected a Samsung download-mode target for bounded PIT review.',
        source=LiveDeviceSource.USB,
        source_labels=('usb',),
        fallback_posture=LiveFallbackPosture.NOT_NEEDED,
        snapshot=LiveDeviceSnapshot(
          source=LiveDeviceSource.USB,
          serial='usb-1-13',
          connection_state='download',
          transport='download-mode',
          mode='usb/download',
          command_ready=True,
          support_posture=LiveDeviceSupportPosture.IDENTITY_INCOMPLETE,
          info_state=LiveDeviceInfoState.UNAVAILABLE,
        ),
      ),
    )

    authority = build_session_authority_snapshot(session)

    self.assertEqual(authority.reviewed_target_label, 'Download-Mode Target Detected')
    self.assertEqual(authority.live_phase_label, 'Download-Mode Device Detected')

  def test_download_mode_attention_promotes_reviewed_target_attention_label(self) -> None:
    session = build_demo_session('no-device')
    session = replace(
      session,
      live_detection=LiveDetectionSession(
        state=LiveDetectionState.ATTENTION,
        summary='Native USB found download mode, but direct USB access still needs attention.',
        source=LiveDeviceSource.USB,
        source_labels=('usb',),
        fallback_posture=LiveFallbackPosture.NOT_NEEDED,
        snapshot=LiveDeviceSnapshot(
          source=LiveDeviceSource.USB,
          serial='usb-1-13',
          connection_state='download',
          transport='download-mode',
          mode='usb/download',
          command_ready=False,
          support_posture=LiveDeviceSupportPosture.IDENTITY_INCOMPLETE,
          info_state=LiveDeviceInfoState.UNAVAILABLE,
        ),
      ),
    )

    authority = build_session_authority_snapshot(session)

    self.assertEqual(authority.reviewed_target_label, 'Download-Mode Target Attention')
    self.assertEqual(authority.live_phase_label, 'Download-Mode Device Attention')

  def test_pit_device_mismatch_blocks_safe_path_candidate(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = replace(
      build_demo_pit_inspection(
        'ready',
        session=session,
        package_assessment=package_assessment,
      ),
      device_alignment=PitDeviceAlignment.MISMATCHED,
      observed_product_code='SM-G996U',
      canonical_product_code='SM-G996U',
      marketing_name='Galaxy S21+',
    )

    authority = build_session_authority_snapshot(
      session,
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.BLOCKED)
    self.assertEqual(authority.readiness, SafePathReadiness.BLOCKED)
    self.assertIn('Observed PIT product code does not match', authority.block_reason)

  def test_missing_pit_fingerprint_comparison_narrows_safe_path_candidate(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)
    pit_inspection = replace(
      build_demo_pit_inspection(
        'ready',
        session=session,
        package_assessment=package_assessment,
      ),
      package_alignment=PitPackageAlignment.MISSING_OBSERVED,
      observed_pit_fingerprint=None,
    )

    authority = build_session_authority_snapshot(
      session,
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.SAFE_PATH_CANDIDATE)
    self.assertEqual(authority.readiness, SafePathReadiness.NARROWED)
    self.assertIn('usable PIT fingerprint', authority.block_reason)

  def test_missing_pit_blocks_safe_path_when_pit_is_required(self) -> None:
    session = build_demo_session('ready')
    package_assessment = build_demo_package_assessment('ready', session=session)

    authority = build_session_authority_snapshot(
      session,
      package_assessment=package_assessment,
      pit_inspection=None,
      pit_required_for_safe_path=True,
    )

    self.assertEqual(authority.selected_launch_path, SessionLaunchPath.BLOCKED)
    self.assertEqual(authority.ownership, SafePathOwnership.BLOCKED)
    self.assertEqual(authority.readiness, SafePathReadiness.BLOCKED)
    self.assertIn('Run Read PIT before continuing the bounded safe-path workflow.', authority.block_reason)


if __name__ == '__main__':
  unittest.main()
