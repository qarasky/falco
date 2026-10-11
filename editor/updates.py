"""Opt-in editor update checks. Never downloads or runs replacement code."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

API_URL = "https://api.github.com/repos/qarasky/falco/releases/latest"
ASSETS = {
    "macos": "Falco-Editor-mac.dmg",
    "windows": "falco-editor-windows.exe",
    "linux": "falco-editor-linux",
}
MAX_RESPONSE_BYTES = 1024 * 1024


class UpdateError(Exception):
    pass


@dataclass(frozen=True)
class EditorRelease:
    build_number: int
    download_url: str

    def is_newer_than(self, installed_build: int) -> bool:
        return self.build_number > installed_build


def installed_build() -> int | None:
    """Source checkouts and unversioned local builds have no release number."""
    try:
        data = json.loads((Path(__file__).parent / "build_info.json").read_text(encoding="utf-8"))
        number = data["build_number"]
        return number if type(number) is int and number > 0 else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def parse_release(data: object, platform: str) -> EditorRelease:
    if platform not in ASSETS:
        raise UpdateError("This platform has no editor download.")
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        raise UpdateError("GitHub did not return a stable editor release.")
    tag = data.get("tag_name")
    match = re.fullmatch(r"build-([1-9][0-9]{0,9})", tag) if isinstance(tag, str) else None
    if not match:
        raise UpdateError("The latest release has an unrecognized build number.")
    expected_url = f"https://github.com/qarasky/falco/releases/download/{tag}/{ASSETS[platform]}"
    assets = data.get("assets")
    if isinstance(assets, list):
        for asset in assets:
            if (isinstance(asset, dict) and asset.get("name") == ASSETS[platform]
                    and asset.get("browser_download_url") == expected_url
                    and asset.get("state") == "uploaded"):
                return EditorRelease(int(match[1]), expected_url)
    raise UpdateError("The latest release has no ready editor download for this OS. Try again later.")


def check_latest(platform: str) -> EditorRelease:
    request = Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Falco-Editor-Update-Checker",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise UpdateError("GitHub returned an unexpectedly large response.")
        data = json.loads(raw)
    except (URLError, OSError, ValueError) as exc:
        raise UpdateError("Could not check GitHub for updates. Check your connection and try again later.") from exc
    return parse_release(data, platform)
