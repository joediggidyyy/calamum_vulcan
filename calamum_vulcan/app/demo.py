"""Fixture-backed shell scenarios for FS-03 sandbox work."""

from __future__ import annotations

from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.adapters.heimdall import apply_heimdall_trace
from calamum_vulcan.adapters.heimdall import build_command_plan_for_operation
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.package import assess_package_manifest
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import replay_events
from calamum_vulcan.fixtures import available_heimdall_process_fixtures
from calamum_vulcan.fixtures import blocked_then_cleared_events
from calamum_vulcan.fixtures import blocked_validation_events
from calamum_vulcan.fixtures import execution_failure_events
from calamum_vulcan.fixtures import happy_path_events
from calamum_vulcan.fixtures import load_heimdall_process_fixture
from calamum_vulcan.fixtures import load_package_manifest_fixture
from calamum_vulcan.fixtures import package_first_events
from calamum_vulcan.fixtures import resume_needed_events


ScenarioBuilder = Callable[[], object]


SCENARIO_BUILDERS = {
  'no-device': PlatformSession,
  'ready': blocked_then_cleared_events,
  'blocked': blocked_validation_events,
  'happy': happy_path_events,
  'resume': resume_needed_events,
  'failure': execution_failure_events,
  'package-first': package_first_events,
}  # type: Dict[str, ScenarioBuilder]

SCENARIO_LABELS = {
  'no-device': 'No-device control deck',
  'ready': 'Ready-to-execute control deck',
  'blocked': 'Blocked preflight review',
  'happy': 'Completed happy-path walkthrough',
  'resume': 'Resume-needed recovery path',
  'failure': 'Transport failure review',
  'package-first': 'Package-first operator setup',
}  # type: Dict[str, str]

SCENARIO_PACKAGE_FIXTURES = {
  'ready': 'ready-standard',
  'blocked': 'blocked-review',
  'happy': 'matched',
  'resume': 'matched',
  'failure': 'matched',
  'package-first': 'package-first-standard',
}  # type: Dict[str, str]

SCENARIO_ADAPTER_FIXTURES = {
  'happy': 'flash-success',
  'failure': 'flash-failure',
  'resume': 'flash-no-reboot-resume',
}  # type: Dict[str, str]

TRANSPORT_SOURCES = ('state-fixture', 'heimdall-adapter')


def available_scenarios() -> Tuple[str, ...]:
  """Return the supported sandbox scenario names in display order."""

  return tuple(SCENARIO_BUILDERS.keys())


def available_transport_sources() -> Tuple[str, ...]:
  """Return supported transport sources for demo session assembly."""

  return TRANSPORT_SOURCES


def scenario_label(name: str) -> str:
  """Return the human-readable label for a sandbox scenario."""

  if name not in SCENARIO_LABELS:
    raise KeyError('Unknown scenario: {name}'.format(name=name))
  return SCENARIO_LABELS[name]


def build_demo_session(name: str) -> PlatformSession:
  """Replay one named fixture stream into a session snapshot."""

  if name not in SCENARIO_BUILDERS:
    raise KeyError('Unknown scenario: {name}'.format(name=name))
  built = SCENARIO_BUILDERS[name]()
  if isinstance(built, PlatformSession):
    return built
  return replay_events(built)


def default_package_fixture_for_scenario(name: str) -> str:
  """Return the default package fixture bound to one shell scenario."""

  if name not in SCENARIO_PACKAGE_FIXTURES:
    raise KeyError('Unknown scenario: {name}'.format(name=name))
  return SCENARIO_PACKAGE_FIXTURES[name]


def default_adapter_fixture_for_scenario(name: str) -> str:
  """Return the default Heimdall process fixture bound to one adapter scenario."""

  if name not in SCENARIO_ADAPTER_FIXTURES:
    raise KeyError('Scenario has no adapter fixture: {name}'.format(name=name))
  return SCENARIO_ADAPTER_FIXTURES[name]


def build_demo_package_assessment(
  name: str,
  session: Optional[PlatformSession] = None,
  package_fixture_name: str = 'scenario-default',
) -> PackageManifestAssessment:
  """Return the assessed package context for one shell scenario."""

  if session is None:
    session = build_demo_session(name)
  fixture_name = package_fixture_name
  if fixture_name == 'scenario-default':
    fixture_name = default_package_fixture_for_scenario(name)
  manifest = load_package_manifest_fixture(fixture_name)
  return assess_package_manifest(
    manifest,
    detected_product_code=session.product_code,
    fixture_name=fixture_name,
  )


def build_demo_adapter_trace(
  name: str,
  package_assessment: PackageManifestAssessment,
  adapter_fixture_name: str = 'scenario-default',
) -> HeimdallNormalizedTrace:
  """Return the normalized Heimdall trace for one adapter-backed scenario."""

  fixture_name = adapter_fixture_name
  if fixture_name == 'scenario-default':
    fixture_name = default_adapter_fixture_for_scenario(name)
  process_result = load_heimdall_process_fixture(fixture_name)
  command_plan = build_command_plan_for_operation(
    process_result.operation,
    package_assessment=package_assessment,
  )
  return normalize_heimdall_result(command_plan, process_result)


def build_demo_adapter_session(
  name: str,
  package_fixture_name: str = 'scenario-default',
  adapter_fixture_name: str = 'scenario-default',
) -> Tuple[PlatformSession, PackageManifestAssessment, HeimdallNormalizedTrace]:
  """Build one demo session from a normalized Heimdall adapter trace."""

  base_session = replay_events(_adapter_prefix_events(name))
  package_assessment = build_demo_package_assessment(
    name,
    session=base_session,
    package_fixture_name=package_fixture_name,
  )
  trace = build_demo_adapter_trace(
    name,
    package_assessment,
    adapter_fixture_name=adapter_fixture_name,
  )
  session = apply_heimdall_trace(base_session, trace)
  return session, package_assessment, trace


def available_adapter_fixtures() -> Tuple[str, ...]:
  """Return supported Heimdall process fixtures for CLI and tests."""

  return available_heimdall_process_fixtures()


def _adapter_prefix_events(name: str) -> object:
  if name in ('happy', 'failure', 'resume'):
    return happy_path_events()[:-2]
  raise KeyError('Scenario has no adapter-backed prefix: {name}'.format(
    name=name,
  ))