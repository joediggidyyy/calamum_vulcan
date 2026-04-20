"""Script entry point for launching the Calamum Vulcan shell sandbox."""

from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from calamum_vulcan.app.__main__ import gui_main


if __name__ == '__main__':
  raise SystemExit(gui_main(sys.argv[1:]))