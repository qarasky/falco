"""Headless launcher builds from the editor executable itself.

The packaged editor is dual-mode: with no arguments it opens the Tk window;
with arguments it builds launchers without any UI, so the same single
executable works for humans and for agents and scripts::

    falco-editor --name server-client-X --host 203.0.113.10 --user deploy \\
        --output server-client-X --out-dir dist

Only non-secret configuration is embedded. Passwords and passphrases are never
read, accepted as arguments, or written anywhere; an encrypted key is embedded
as-is, and its passphrase is entered privately on the launcher's first run.
Unlike the window, the CLI replaces existing output files without asking.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from editor.builder import build_all_launchers, build_launcher
from editor.updates import installed_build
from shared.config import DEFAULT_SSH_PORT, LauncherConfig
from shared.errors import FalcoError
from shared.ssh_keys import MAX_KEY_BYTES


def _print(message: str, *, err: bool = False) -> None:
    """Write a CLI line, tolerating a missing stream in console-less builds."""

    stream = sys.stderr if err else sys.stdout
    if stream is None:
        stream = sys.stdout if err else sys.stderr
    if stream is not None:
        print(message, file=stream)


def _progress(message: str) -> None:
    """Send build progress to stderr so stdout stays parseable."""

    _print(message, err=True)


def version_text() -> str:
    """Describe this editor build the same way the update check does."""

    build = installed_build()
    return "Falco Editor development build" if build is None else f"Falco Editor build {build}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="falco-editor",
        description="Build Falco launchers without opening the editor window. "
        "Run with no arguments to open the editor instead.",
    )
    parser.add_argument("--version", action="version", version=version_text())
    parser.add_argument("--name", required=True, help="Launcher name, e.g. server-client-X")
    parser.add_argument("--host", required=True, help="SSH host or IP")
    parser.add_argument("--user", required=True, help="SSH username")
    parser.add_argument("--port", type=int, default=DEFAULT_SSH_PORT, help=f"SSH port (default {DEFAULT_SSH_PORT})")
    parser.add_argument("--output", required=True, help="Output filename, e.g. server-client-X.exe")
    parser.add_argument("--out-dir", default="dist", help="Output directory (default dist)")
    parser.add_argument(
        "--private-key",
        help="Encrypted OpenSSH private key to embed; its passphrase is entered on first launcher use",
    )
    parser.add_argument("--requires-vpn", action="store_true", help="Include Tailscale/WireGuard/VPN troubleshooting guidance")
    parser.add_argument("--all-platforms", action="store_true", help="Build a launcher for every bundled platform")
    parser.add_argument("--icon", default=None, help="Rejected: prebuilt launcher stubs do not support custom icons")
    return parser


def _launcher_config(args: argparse.Namespace) -> LauncherConfig:
    key = None
    if args.private_key:
        with Path(args.private_key).open("rb") as stream:
            raw = stream.read(MAX_KEY_BYTES + 1)
        if len(raw) > MAX_KEY_BYTES:
            raise FalcoError("Encrypted OpenSSH key must be smaller than 128 KiB.")
        try:
            key = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FalcoError("Key must be an encrypted OpenSSH text file.") from exc
    return LauncherConfig.create(
        launcher_name=args.name,
        host=args.host,
        username=args.user,
        port=args.port,
        auth_method="private_key" if key is not None else "password",
        encrypted_private_key=key,
        requires_vpn=args.requires_vpn,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help/--version and usage errors
        return exc.code if type(exc.code) is int else 0
    try:
        config = _launcher_config(args)
        if args.icon:
            raise FalcoError("Custom executable icons are not supported by prebuilt launcher stubs.")
        if args.all_platforms:
            multi = build_all_launchers(config, base_name=args.output, output_dir=args.out_dir, progress=_progress)
            for path in multi.executables:
                _print(f"Built {path}")
            _print(f"Agent instructions: {multi.how_to_use}")
            if multi.skipped:
                _print("Unavailable platforms: " + ", ".join(multi.skipped))
        else:
            single = build_launcher(config, output_name=args.output, output_dir=args.out_dir, progress=_progress)
            _print(f"Built {single.executable}")
            _print(f"Agent instructions: {single.how_to_use}")
        _print(f"credential_id: {config.credential_id}")
    except (FalcoError, OSError) as exc:
        _print(f"build failed: {exc}", err=True)
        return 1
    except Exception as exc:  # defensive; the window recovers the same way
        _print(f"build failed ({type(exc).__name__}): {exc}. Check the output folder and launcher files, then retry.", err=True)
        return 1
    return 0
