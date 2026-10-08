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
