"""Tests for the FS-P06 TestPyPI rehearsal runner."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from scripts.run_testpypi_rehearsal import _twine_upload_command


class TestPyPIRehearsalTests(unittest.TestCase):
  """Verify the rehearsal runner chooses the correct Twine credential path."""

  def test_upload_command_uses_repository_profile_for_pypirc_credentials(self) -> None:
    wheel_path = Path('dist/calamum_vulcan-0.1.0-py3-none-any.whl')
    sdist_path = Path('dist/calamum_vulcan-0.1.0.tar.gz')
    credentials = {
      'token_env_present': False,
      'twine_password_present': False,
      'pypirc_testpypi_configured': True,
    }

    command = list(_twine_upload_command(wheel_path, sdist_path, credentials))

    self.assertIn('--repository', command)
    self.assertIn('testpypi', command)
    self.assertNotIn('--repository-url', command)

  def test_upload_command_uses_repository_url_for_env_credentials(self) -> None:
    wheel_path = Path('dist/calamum_vulcan-0.1.0-py3-none-any.whl')
    sdist_path = Path('dist/calamum_vulcan-0.1.0.tar.gz')
    credentials = {
      'token_env_present': True,
      'twine_password_present': False,
      'pypirc_testpypi_configured': False,
    }

    command = list(_twine_upload_command(wheel_path, sdist_path, credentials))

    self.assertIn('--repository-url', command)
    self.assertNotIn('--repository', command)


if __name__ == '__main__':
  unittest.main()
