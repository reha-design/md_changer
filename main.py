"""Unified Entry Point for md_changer (GUI / CLI)."""

import sys
from pathlib import Path

# Add src to sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from md_changer.cli import main as cli_main
from md_changer.gui import launch_gui


def main() -> int | None:
    if len(sys.argv) > 1:
        return cli_main()
    else:
        launch_gui()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
