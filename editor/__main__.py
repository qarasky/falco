"""Entry point for ``python -m editor`` and the ``falco-editor`` script.

Dual-mode: with no arguments it opens the Tk editor window; with arguments it
runs one headless build (see :mod:`editor.cli`). macOS may pass a process
serial number (``-psn_…``) to an app launched from Finder even when the user
passed nothing; those arguments are ignored so the window still opens.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if sys.platform == "darwin":
        arguments = [argument for argument in arguments if not argument.startswith("-psn_")]
    if not arguments:
        from editor.app import launch

        return launch()
    from editor.cli import main as cli_main

    return cli_main(arguments)


if __name__ == "__main__":
    sys.exit(main())
