import json
from urllib.error import URLError

import pytest

from editor import updates


def release_data(platform="macos", build=21):
    name = updates.ASSETS[platform]
    return {
        "tag_name": f"build-{build}", "draft": False, "prerelease": False,
        "assets": [{"name": name, "state": "uploaded",
                    "browser_download_url": f"https://github.com/qarasky/falco/releases/download/build-{build}/{name}"}],
    }


@pytest.mark.parametrize("platform", updates.ASSETS)
def test_release_selects_editor_asset_and_compares_numeric_builds(platform):
    release = updates.parse_release(release_data(platform, 21), platform)
    assert release.download_url.endswith(updates.ASSETS[platform])
    assert release.is_newer_than(9)
    assert not release.is_newer_than(21)
    assert not release.is_newer_than(22)


@pytest.mark.parametrize("data", [None, [], {}, {"tag_name": "v0.1.0"}, {"tag_name": "build-" + "9" * 5000}])
def test_invalid_release_is_rejected(data):
    with pytest.raises(updates.UpdateError):
        updates.parse_release(data, "macos")


@pytest.mark.parametrize("field,value", [("draft", True), ("prerelease", True), ("assets", [])])
def test_incomplete_or_unstable_release_is_rejected(field, value):
    data = release_data()
    data[field] = value
    with pytest.raises(updates.UpdateError):
        updates.parse_release(data, "macos")


@pytest.mark.parametrize("field,value", [
    ("name", "falco-stub-macos"), ("state", "new"),
    ("browser_download_url", "https://example.com/editor.dmg"),
    ("browser_download_url", "http://github.com/qarasky/falco/releases/download/build-21/Falco-Editor-mac.dmg"),
])
def test_only_ready_official_editor_assets_are_accepted(field, value):
    data = release_data()
    data["assets"][0][field] = value
    with pytest.raises(updates.UpdateError):
        updates.parse_release(data, "macos")


def test_update_check_has_timeout_and_bounded_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            assert limit == updates.MAX_RESPONSE_BYTES + 1
            return json.dumps(release_data()).encode()

    def open_request(request, timeout):
        assert request.full_url == updates.API_URL
        assert timeout == 10
        return Response()

    monkeypatch.setattr(updates, "urlopen", open_request)
    assert updates.check_latest("macos").build_number == 21


@pytest.mark.parametrize("error", [URLError("offline"), TimeoutError("timed out")])
def test_network_failures_are_useful_errors(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(updates, "urlopen", fail)
    with pytest.raises(updates.UpdateError, match="connection"):
        updates.check_latest("macos")


def test_bad_response_is_rejected(monkeypatch):
    from io import BytesIO
    monkeypatch.setattr(updates, "urlopen", lambda *args, **kwargs: BytesIO(b"not json"))
    with pytest.raises(updates.UpdateError):
        updates.check_latest("macos")


def test_oversized_response_is_rejected(monkeypatch):
    # Built inside the test: a megabyte-sized parametrized value would become
    # part of the test ID, and pytest exports that ID in PYTEST_CURRENT_TEST,
    # which hangs Windows runners on oversized environment variables.
    oversized = b"x" * (updates.MAX_RESPONSE_BYTES + 1)
    from io import BytesIO
    monkeypatch.setattr(updates, "urlopen", lambda *args, **kwargs: BytesIO(oversized))
    with pytest.raises(updates.UpdateError):
        updates.check_latest("macos")


@pytest.mark.parametrize("metadata,expected", [
    ({"build_number": 21}, 21), ({"build_number": 0}, None),
    ({"build_number": "21"}, None), ({"build_number": True}, None),
    ({}, None), ([], None),
])
def test_installed_build_metadata(monkeypatch, tmp_path, metadata, expected):
    monkeypatch.setattr(updates, "__file__", str(tmp_path / "updates.py"))
    (tmp_path / "build_info.json").write_text(json.dumps(metadata))
    assert updates.installed_build() == expected


def test_development_checkout_has_no_build_number(monkeypatch, tmp_path):
    monkeypatch.setattr(updates, "__file__", str(tmp_path / "updates.py"))
    assert updates.installed_build() is None
