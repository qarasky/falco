"""Dual-mode entry point: arguments build headlessly, no arguments open the GUI."""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from editor import builder, cli
from editor import __main__ as entry


def _fake_stubs(tmp_path: Path, monkeypatch, only: str | None = None) -> None:
    stubs = {}
    for target in builder.TARGETS:
        path = tmp_path / target.bundled_name
        path.write_bytes(b"STUB-" + target.key.encode() + b"FALCO_SCHEMA_2")
        stubs[target.key] = path
    if only is not None:
        stubs = {only: stubs[only]}
    monkeypatch.setattr(builder, "discover_stubs", lambda: stubs)
    monkeypatch.setattr(builder, "_current_os_key", lambda: "linux")


def _cli_args(tmp_path: Path, output: str = "server-client-X") -> list[str]:
    return [
        "--name", output,
        "--host", "203.0.113.10",
        "--user", "deploy",
        "--output", output,
        "--out-dir", str(tmp_path / "out"),
    ]


def test_build_without_arguments_opens_the_window(monkeypatch):
    from editor import app
    monkeypatch.setattr(app, "launch", lambda: 7)
    assert entry.main([]) == 7


def test_macos_process_serial_number_still_opens_the_window(monkeypatch):
    from editor import app
    cli_calls: list[list[str]] = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(app, "launch", lambda: 0)
    monkeypatch.setattr(cli, "main", lambda argv=None: cli_calls.append(list(argv or [])) or 0)
    assert entry.main(["-psn_0_123456"]) == 0
    assert cli_calls == []


def test_arguments_route_to_the_headless_builder(monkeypatch):
    cli_calls: list[list[str]] = []
    monkeypatch.setattr(cli, "main", lambda argv=None: cli_calls.append(list(argv or [])) or 5)
    assert entry.main(["--name", "n"]) == 5
    assert cli_calls == [["--name", "n"]]


def test_cli_never_imports_the_gui(monkeypatch):
    # Importing a module that is None in sys.modules raises ImportError.
    monkeypatch.setitem(sys.modules, "editor.app", None)
    assert entry.main(["--help"]) == 0


def test_help_and_version_exit_zero(capsys, monkeypatch):
    monkeypatch.setattr(cli, "installed_build", lambda: 21)
    assert cli.main(["--help"]) == 0
    assert "usage:" in capsys.readouterr().out
    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "Falco Editor build 21"


def test_cli_builds_a_single_launcher(tmp_path, monkeypatch, capsys):
    _fake_stubs(tmp_path, monkeypatch)
    assert cli.main(_cli_args(tmp_path)) == 0
    console = capsys.readouterr()
    built = (tmp_path / "out" / "server-client-X").resolve()
    assert built.is_file()
    assert (tmp_path / "out" / "how-to-use.md").is_file()
    assert f"Built {built}" in console.out
    assert "credential_id: falco:server-client-X:deploy@203.0.113.10:22" in console.out
    # Progress goes to stderr, keeping stdout parseable.
    assert "Wrote server-client-X" in console.err


def test_cli_all_platforms_reports_unavailable(tmp_path, monkeypatch, capsys):
    _fake_stubs(tmp_path, monkeypatch, only="linux")
    assert cli.main([*_cli_args(tmp_path), "--all-platforms"]) == 0
    console = capsys.readouterr()
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["how-to-use.md", "server-client-X-linux"]
    assert "Unavailable platforms: windows, macos" in console.out


def test_cli_replaces_existing_output_without_asking(tmp_path, monkeypatch):
    _fake_stubs(tmp_path, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    (out / "server-client-X").write_bytes(b"old launcher")
    assert cli.main(_cli_args(tmp_path)) == 0
    assert (out / "server-client-X").read_bytes().startswith(b"STUB-")


def test_cli_failures_return_nonzero_and_explain(tmp_path, monkeypatch, capsys):
    _fake_stubs(tmp_path, monkeypatch)
    code = cli.main(["--name", "n", "--host", "http://example.com", "--user", "u", "--output", "n", "--out-dir", str(tmp_path / "out")])
    assert code == 1
    assert "build failed" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_cli_rejects_password_arguments(tmp_path, capsys):
    code = cli.main([*_cli_args(tmp_path), "--password", "hunter2"])
    assert code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_cli_has_no_secret_reading_options():
    parser = cli.build_parser()
    options = [option for action in parser._actions for option in action.option_strings]
    assert not any("password" in option or "passphrase" in option for option in options)


def test_cli_embeds_an_encrypted_key_file(tmp_path, monkeypatch):
    _fake_stubs(tmp_path, monkeypatch)
    key = Path(__file__).parent / "fixtures" / "encrypted_ed25519"
    assert cli.main([*_cli_args(tmp_path), "--private-key", str(key)]) == 0
    blob = (tmp_path / "out" / "server-client-X").read_bytes()
    length = struct.unpack("<Q", blob[-16:-8])[0]
    embedded = json.loads(blob[-16 - length : -16])
    assert embedded["auth_method"] == "private_key"
    assert embedded["encrypted_private_key"].startswith("-----BEGIN OPENSSH PRIVATE KEY-----")


def test_cli_reports_unexpected_errors_without_a_traceback(tmp_path, monkeypatch, capsys):
    _fake_stubs(tmp_path, monkeypatch)

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "build_launcher", explode)
    assert cli.main(_cli_args(tmp_path)) == 1
    error = capsys.readouterr().err
    assert "RuntimeError" in error and "boom" in error


def test_build_launcher_script_delegates_to_the_editor_cli(monkeypatch):
    from build import build_launcher
    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "main", lambda argv=None: seen.append(list(argv or [])) or 0)
    assert build_launcher.main(["--name", "n"]) == 0
    assert seen == [["--name", "n"]]
