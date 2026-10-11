"""Package the Linux Falco Editor as an AppImage (one release artifact).

A bare ELF cannot carry an icon; an AppImage can, and Linux desktop
environments also pick up its desktop entry and icon. The release job runs
this on Linux after ``build_editor.py``::

    python build/build_appimage.py --binary dist/falco-editor \\
        --out falco-editor-linux.AppImage --tool ./appimagetool

``--tool`` defaults to ``appimagetool`` on PATH; CI downloads the official
continuous-build AppImage. The AppDir is assembled from ``build/appimage/``
(``AppRun`` and the desktop entry) plus ``editor/assets/falco.png``.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RESOURCES = _REPO_ROOT / "build" / "appimage"
_DEFAULT_ICON = _REPO_ROOT / "editor" / "assets" / "falco.png"


def appimage_arch() -> str:
    """Map the host architecture to appimagetool's ARCH names.

    The editor is always packaged on the architecture it runs on, so the host's
    machine type names the AppImage correctly (and lets appimagetool build from
    an AppDir whose payload it cannot inspect, such as a script in tests).
    """

    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "aarch64"
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    raise SystemExit(f"unsupported AppImage architecture: {machine}")


def stage_appdir(binary: Path, appdir: Path, *, icon: Path, name: str = "falco-editor") -> None:
    """Assemble an AppDir: binary, ``AppRun``, desktop entry, icon and ``.DirIcon``."""

    binary = binary.resolve()
    if not binary.is_file():
        raise SystemExit(f"editor binary not found: {binary}")
    if not icon.is_file():
        raise SystemExit(f"icon not found: {icon}")
    appdir.mkdir(parents=True, exist_ok=True)
    for resource in ("AppRun", f"{name}.desktop"):
        shutil.copy2(_RESOURCES / resource, appdir / resource)
    os.chmod(appdir / "AppRun", 0o755)
    shutil.copy2(binary, appdir / name)
    os.chmod(appdir / name, 0o755)
    shutil.copy2(icon, appdir / f"{name}.png")
    try:
        os.symlink(f"{name}.png", appdir / ".DirIcon")
    except OSError:  # creating symlinks needs extra privileges on Windows
        shutil.copy2(appdir / f"{name}.png", appdir / ".DirIcon")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Package the Falco Editor as a Linux AppImage.")
    parser.add_argument("--binary", required=True, help="The built editor executable")
    parser.add_argument("--out", required=True, help="Output .AppImage path")
    parser.add_argument("--tool", default="appimagetool", help="appimagetool executable (default: on PATH)")
    parser.add_argument("--icon", default=str(_DEFAULT_ICON), help="App icon (PNG)")
    args = parser.parse_args(argv)

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".falco-appimage-", dir=out.parent) as scratch:
        appdir = Path(scratch) / "AppDir"
        stage_appdir(Path(args.binary), appdir, icon=Path(args.icon))
        env = os.environ.copy()
        # appimagetool cannot always guess the architecture from the payload.
        env.setdefault("ARCH", appimage_arch())
        # The tool itself is often an AppImage; run it without FUSE when needed.
        env.setdefault("APPIMAGE_EXTRACT_AND_RUN", "1")
        proc = subprocess.run([args.tool, "--no-appstream", str(appdir), str(out)], env=env)
    if proc.returncode != 0 or not out.is_file():
        print("appimagetool failed to produce the AppImage", file=sys.stderr)
        return 1
    print(f"Built {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
