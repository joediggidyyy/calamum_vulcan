"""Run the Calamum Vulcan shared security validation suite."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import write_security_validation_artifacts


ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'security_validation'


def _print(lines):
  for line in lines:
    print(line)


def main() -> int:
  summary = run_security_validation_suite(REPO_ROOT)
  write_security_validation_artifacts(ARCHIVE_ROOT, summary)
  _print(
    [
      'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
      'security_decision="{decision}"'.format(decision=summary.decision),
      'blocking_findings="{count}"'.format(count=len(summary.blocking_findings)),
      'warnings="{count}"'.format(count=len(summary.warnings)),
    ]
  )
  if summary.decision == 'failed':
    return 1
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
