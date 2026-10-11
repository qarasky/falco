"""Linux AppImage packaging: AppDir layout and appimagetool invocation."""

from __future__ import annotations

import os
import stat
import subprocess

import pytest

from build import build_appimage


def _fake_binary(tmp_path):
    binary = tmp_path / "falco-editor"
    binary.write_bytes(b"#!/bin/sh\necho fake editor\n")
    return binary


def test_appdir_contains_binary_apprun_desktop_and_icon(tmp_path):
    binary = _fake_binary(tmp_path)
    appdir = tmp_path / "AppDir"
    build_appimage.stage_appdir(binary, appdir, icon=build_appimage._DEFAULT_ICON)

    assert (appdir / "falco-editor").read_bytes() == binary.read_bytes()
    assert (appdir / "AppRun").read_text().startswith("#!/bin/sh")
    if os.name == "posix":
        assert (appdir / "falco-editor").stat().st_mode & stat.S_IXUSR
        assert (appdir / "AppRun").stat().st_mode & stat.S_IXUSR
    assert 'exec "$APPDIR/falco-editor" "$@"' in (appdir / "AppRun").read_text()
    desktop = (appdir / "falco-editor.desktop").read_text()
    assert "Name=Falco Editor" in desktop
    assert "Exec=falco-editor" in desktop
    assert "Icon=falco-editor" in desktop
    assert "Categories=Development;" in desktop
    assert (appdir / "falco-editor.png").read_bytes() == build_appimage._DEFAULT_ICON.read_bytes()
    assert (appdir / ".DirIcon").exists()


def test_main_runs_appimagetool_with_staged_appdir_and_output(tmp_path, monkeypatch):
    binary = _fake_binary(tmp_path)
    out = tmp_path / "falco-editor-linux.AppImage"
    calls = []

    def fake_run(command, env=None):
        calls.append((command, env))
        out.write_bytes(b"APPIMAGE")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(build_appimage.subprocess, "run", fake_run)
    assert build_appimage.main(["--binary", str(binary), "--out", str(out), "--tool", "appimagetool"]) == 0

    command, env = calls[0]
    assert command[0] == "appimagetool"
    assert command[-1] == str(out)
    assert command[command.index("--no-appstream") + 1].endswith("AppDir")
    assert env["APPIMAGE_EXTRACT_AND_RUN"] == "1"
    assert env["ARCH"] in ("aarch64", "x86_64")
    assert out.read_bytes() == b"APPIMAGE"


def test_failed_tool_reports_and_returns_nonzero(tmp_path, monkeypatch, capsys):
    binary = _fake_binary(tmp_path)
    out = tmp_path / "falco-editor-linux.AppImage"
    monkeypatch.setattr(
        build_appimage.subprocess, "run", lambda command, env=None: subprocess.CompletedProcess(command, 1)
    )
    assert build_appimage.main(["--binary", str(binary), "--out", str(out)]) == 1
    assert "appimagetool failed" in capsys.readouterr().err


def test_missing_binary_is_rejected(tmp_path):
    with pytest.raises(SystemExit, match="editor binary not found"):
        build_appimage.stage_appdir(
            tmp_path / "missing", tmp_path / "AppDir", icon=build_appimage._DEFAULT_ICON
        )
