"""Unit tests for runtime dependency satisfaction repair."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
import unittest
from unittest import mock


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan import runtime_dependencies as runtime_dependencies_module


class RuntimeDependencyRepairTests(unittest.TestCase):
  """Prove runtime dependency self-heal stays package-aware and bounded."""

  def test_repair_refreshes_source_checkout_when_metadata_drifts(self) -> None:
    logger = logging.getLogger('test.runtime')

    with mock.patch.object(
      runtime_dependencies_module,
      '_RUNTIME_DEPENDENCY_REPAIR_ATTEMPTED',
      False,
    ), mock.patch.object(
      runtime_dependencies_module,
      '_RUNTIME_DEPENDENCY_REPAIR_NOTE',
      None,
    ), mock.patch.object(
      runtime_dependencies_module,
      '_declared_runtime_requirements',
      return_value=('PySide6>=6.8,<7', 'pyusb>=1.2.1'),
    ), mock.patch.object(
      runtime_dependencies_module,
      '_missing_runtime_requirements',
      side_effect=[(), ()],
    ), mock.patch.object(
      runtime_dependencies_module,
      '_runtime_dependency_metadata_is_stale',
      side_effect=[True, False],
    ), mock.patch.object(
      runtime_dependencies_module,
      '_resolve_dependency_python_executable',
      return_value=Path('C:/Python314/python.exe'),
    ), mock.patch(
      'calamum_vulcan.runtime_dependencies.subprocess.run',
      return_value=mock.Mock(returncode=0, stdout='', stderr=''),
    ) as subprocess_run:
      note = runtime_dependencies_module.attempt_runtime_dependency_repair(logger)

    self.assertIsNotNone(note)
    self.assertIn('refreshed Calamum Vulcan from the source checkout', note)
    command = subprocess_run.call_args.args[0]
    self.assertIn('-e', command)
    self.assertIn(str(runtime_dependencies_module.PROJECT_ROOT), command)

  def test_repair_installs_declared_requirements_without_source_checkout(self) -> None:
    logger = logging.getLogger('test.runtime')

    with mock.patch.object(
      runtime_dependencies_module,
      'PYPROJECT_PATH',
      Path('C:/missing/pyproject.toml'),
    ), mock.patch.object(
      runtime_dependencies_module,
      'PROJECT_ROOT',
      Path('C:/missing'),
    ), mock.patch.object(
      runtime_dependencies_module,
      '_RUNTIME_DEPENDENCY_REPAIR_ATTEMPTED',
      False,
    ), mock.patch.object(
      runtime_dependencies_module,
      '_RUNTIME_DEPENDENCY_REPAIR_NOTE',
      None,
    ), mock.patch.object(
      runtime_dependencies_module,
      '_declared_runtime_requirements',
      return_value=('PySide6>=6.8,<7', 'pyusb>=1.2.1'),
    ), mock.patch.object(
      runtime_dependencies_module,
      '_missing_runtime_requirements',
      side_effect=[('pyusb>=1.2.1',), ()],
    ), mock.patch.object(
      runtime_dependencies_module,
      '_runtime_dependency_metadata_is_stale',
      side_effect=[False, False],
    ), mock.patch.object(
      runtime_dependencies_module,
      '_resolve_dependency_python_executable',
      return_value=Path('C:/Python314/python.exe'),
    ), mock.patch(
      'calamum_vulcan.runtime_dependencies.subprocess.run',
      return_value=mock.Mock(returncode=0, stdout='', stderr=''),
    ) as subprocess_run:
      note = runtime_dependencies_module.attempt_runtime_dependency_repair(logger)

    self.assertIsNotNone(note)
    self.assertIn('installed the declared runtime requirements', note)
    command = subprocess_run.call_args.args[0]
    self.assertNotIn('-e', command)
    self.assertEqual(command[-2:], ['PySide6>=6.8,<7', 'pyusb>=1.2.1'])