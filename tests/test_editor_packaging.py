from pathlib import Path

import pytest

from build import build_editor


@pytest.mark.parametrize("platform,extension", [("darwin", "icns"), ("win32", "ico"), ("linux", "png")])
def test_editor_bundles_assets_and_platform_icon(monkeypatch, tmp_path, platform, extension):
    monkeypatch.setattr(build_editor.sys, "platform", platform)
    command = build_editor.pyinstaller_command(
        name="falco-editor", dist_dir=tmp_path, work_dir=tmp_path,
        stubs_dir=tmp_path / "stubs", windowed=True,
    )
    icon = Path(command[command.index("--icon") + 1])
    assert icon.name == f"falco.{extension}"
    assert icon.is_file()
    assert any("editor/assets" in argument for argument in command)


def test_release_build_number_is_embedded(tmp_path):
    import json
    command = build_editor.pyinstaller_command(
        name="falco-editor", dist_dir=tmp_path, work_dir=tmp_path,
        stubs_dir=tmp_path / "stubs", windowed=True, build_number=21,
    )
    metadata = tmp_path / "build_info.json"
    assert json.loads(metadata.read_text()) == {"build_number": 21}
    assert any(str(metadata) in argument for argument in command)


def test_unversioned_local_build_does_not_embed_a_release_number(tmp_path):
    command = build_editor.pyinstaller_command(
        name="falco-editor", dist_dir=tmp_path, work_dir=tmp_path,
        stubs_dir=tmp_path / "stubs", windowed=True,
    )
    assert not any("build_info.json" in argument for argument in command)


def test_windows_editor_keeps_console_for_cli_and_hides_it_when_owned(monkeypatch, tmp_path):
    monkeypatch.setattr(build_editor.sys, "platform", "win32")
    command = build_editor.pyinstaller_command(
        name="falco-editor", dist_dir=tmp_path, work_dir=tmp_path,
        stubs_dir=tmp_path / "stubs", windowed=False,
    )
    assert "--windowed" not in command
    assert command[command.index("--hide-console") + 1] == "hide-early"


def test_macos_app_bundle_is_windowed_without_windows_console_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(build_editor.sys, "platform", "darwin")
    command = build_editor.pyinstaller_command(
        name="falco-editor", dist_dir=tmp_path, work_dir=tmp_path,
        stubs_dir=tmp_path / "stubs", windowed=True,
    )
    assert "--windowed" in command
    assert "--hide-console" not in command


def test_linux_editor_has_no_platform_window_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(build_editor.sys, "platform", "linux")
    command = build_editor.pyinstaller_command(
        name="falco-editor", dist_dir=tmp_path, work_dir=tmp_path,
        stubs_dir=tmp_path / "stubs", windowed=False,
    )
    assert "--windowed" not in command
    assert "--hide-console" not in command
