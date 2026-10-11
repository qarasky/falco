"""Headless launcher build, for source checkouts and CI.

A thin wrapper around the editor's own CLI (:mod:`editor.cli`), so
``python build/build_launcher.py …`` and running the packaged editor with the
same arguments are one code path; one produces a launcher without opening the
editor window::

    python build/build_launcher.py \\
        --name server-client-X --host 203.0.113.10 --user deploy --port 22 \\
        --output server-client-X --out-dir dist --requires-vpn

Omit ``--private-key`` for password authentication (the password is entered
privately on the launcher's first run); ``--all-platforms`` builds every
bundled platform. Unlike the GUI, the CLI replaces named output files without
asking.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repo packages importable when run as a bare script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from editor import cli  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
