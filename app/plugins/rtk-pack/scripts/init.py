#!/usr/bin/env python3
"""Fetch, verify and install the rtk binary for this platform.

Run by `ai-toolkit plugin install rtk-pack` (scripts/plugin.py invokes
`init.py` if present). This is the only point at which the pack touches the
network; nothing is fetched at runtime.

Design constraints from kb/planning/rtk-pack-integration-plan.md section 6:

- Verify before install. A digest mismatch aborts and removes the partial
  download; a half-installed binary is worse than none.
- A fetch failure is not an install failure. The pack degrades to inert and
  says so, matching how the core behaves when jq is missing. plugin.py only
  warns on a non-zero exit, so the message has to carry the meaning.
- Never silent. Every path that ends without a working binary prints why.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import ssl
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PACK_NAME = "rtk-pack"
TOOLKIT_DATA_DIR = Path(os.environ.get("AI_TOOLKIT_DATA_DIR", Path.home() / ".softspark" / "ai-toolkit"))
INSTALL_DIR = TOOLKIT_DATA_DIR / "plugin-scripts" / PACK_NAME / "bin"
VERSION_FILE = TOOLKIT_DATA_DIR / "plugin-scripts" / PACK_NAME / "version.json"

DOWNLOAD_TIMEOUT = 120
CHUNK = 1 << 16

# Bounded so a wrong URL cannot fill the disk. The largest real asset is ~4 MB.
MAX_ASSET_BYTES = 64 * 1024 * 1024


class InstallError(Exception):
    """Anything that leaves the pack without a usable binary."""


def manifest_path() -> Path:
    """The pack manifest, resolved relative to this script's source location."""
    return Path(__file__).resolve().parent.parent / "plugin.json"


def detect_platform() -> str:
    """Map this host to an asset key in plugin.json.

    Linux x86_64 is served the static musl build, which runs on glibc; upstream
    routes Linux x86_64 to musl in its own Homebrew formula for the same reason.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64" if system == "darwin" else "aarch64",
        "aarch64": "arm64" if system == "darwin" else "aarch64",
    }.get(machine)
    if arch is None:
        raise InstallError(f"unsupported architecture: {platform.machine()}")
    if system not in ("darwin", "linux", "windows"):
        raise InstallError(f"unsupported platform: {platform.system()}")
    return f"{system}-{arch}"


def asset_url(binary: dict, asset: dict) -> str:
    """Where to fetch this asset from.

    RTK_PACK_RELEASE_BASE_URL points the fetch at a mirror instead of GitHub,
    for networks that cannot reach it directly. The digest check is unchanged,
    so a mirror serving different bytes is rejected exactly like a corrupt
    download.
    """
    base = os.environ.get("RTK_PACK_RELEASE_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}/{asset['file']}"
    return (
        f"https://github.com/{binary['release_repo']}/releases/download/"
        f"{binary['release_tag']}/{asset['file']}"
    )


def download(url: str, dest: Path) -> str:
    """Fetch to dest, returning the SHA-256 of what actually landed."""
    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "ai-toolkit-rtk-pack"})
    # A default TLS context for https; file:// mirrors (and the tests) take the
    # handler that ignores it.
    kwargs = {"timeout": DOWNLOAD_TIMEOUT}
    if url.startswith("https:"):
        kwargs["context"] = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, **kwargs) as response:
            with dest.open("wb") as handle:
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ASSET_BYTES:
                        raise InstallError(f"asset exceeds {MAX_ASSET_BYTES} bytes, refusing to continue")
                    digest.update(chunk)
                    handle.write(chunk)
    except urllib.error.HTTPError as exc:
        raise InstallError(f"HTTP {exc.code} fetching {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise InstallError(f"could not fetch {url}: {exc}") from exc
    if total == 0:
        raise InstallError(f"empty response from {url}")
    return digest.hexdigest()


def extract_member(archive: Path, member: str, dest: Path) -> None:
    """Pull exactly one flat entry out of the archive.

    The archives are built to hold a single flat binary and CI asserts it, so
    anything else means the asset is not what the manifest claims and is
    refused rather than extracted.
    """
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            if names != [member]:
                raise InstallError(f"expected exactly [{member}] in {archive.name}, found {names}")
            with zf.open(member) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
        return

    with tarfile.open(archive, "r:gz") as tf:
        names = tf.getnames()
        if names != [member]:
            raise InstallError(f"expected exactly [{member}] in {archive.name}, found {names}")
        extracted = tf.extractfile(member)
        if extracted is None:
            raise InstallError(f"{member} in {archive.name} is not a regular file")
        with extracted as src, dest.open("wb") as out:
            shutil.copyfileobj(src, out)


def already_installed(asset: dict, target: Path) -> bool:
    """True when this exact asset is already in place.

    `ai-toolkit plugin install --editor all` calls the init step twice in a
    single command (plugin.py invokes _copy_plugin_scripts per editor), so
    without this the binary is downloaded twice. It also makes a re-install
    cheap instead of re-fetching.
    """
    if not target.is_file():
        return False
    try:
        record = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return record.get("sha256") == asset["sha256"] and record.get("asset") == asset["file"]


def install(manifest: dict) -> dict | None:
    binary = manifest.get("binary")
    if not binary:
        raise InstallError("plugin.json has no 'binary' section")

    key = detect_platform()
    asset = binary.get("assets", {}).get(key)
    if asset is None:
        raise InstallError(f"no asset published for {key}")

    url = asset_url(binary, asset)
    install_name = binary.get("install_name", "rtk")
    if platform.system().lower() == "windows":
        install_name += ".exe"
    target = INSTALL_DIR / install_name

    if already_installed(asset, target):
        return None

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / asset["file"]
        actual = download(url, staged)
        if actual != asset["sha256"]:
            # Nothing is installed on a mismatch. The temp dir takes the
            # partial download with it.
            raise InstallError(
                f"digest mismatch for {asset['file']}: "
                f"expected {asset['sha256']}, got {actual}"
            )
        unpacked = Path(tmp) / install_name
        extract_member(staged, asset["member"], unpacked)

        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(unpacked), str(target))

    target.chmod(target.stat().st_mode | 0o111)

    record = {
        "pack_version": manifest.get("version"),
        "upstream_version": manifest.get("upstream", {}).get("version"),
        "release_tag": binary["release_tag"],
        "platform": key,
        "asset": asset["file"],
        "sha256": asset["sha256"],
        "binary": str(target),
    }
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> int:
    try:
        manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"rtk-pack: cannot read plugin.json: {exc}", file=sys.stderr)
        return 1

    try:
        record = install(manifest)
        if record is None:
            print("rtk already installed and digest matches, nothing to do")
            return 0
    except InstallError as exc:
        # plugin.py prints this as "WARN init failed" and continues, which is
        # the intended behaviour: the hook stays wired but finds no binary and
        # passes every command through untouched.
        print(
            f"rtk-pack: no binary installed ({exc}). "
            "The pack is inert: commands are passed through unchanged. "
            "Re-run 'ai-toolkit plugin install rtk-pack' once the cause is resolved.",
            file=sys.stderr,
        )
        return 1

    print(
        f"rtk {record['upstream_version']} installed for {record['platform']} "
        f"({record['binary']}), digest verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
