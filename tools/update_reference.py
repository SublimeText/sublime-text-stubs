#!/usr/bin/env python3
"""Extract the reference sources of the latest Sublime Text build.

Queries the stable and dev update check endpoints, and if either reports a build
newer than ``ST_BUILD`` in ``generate_stubs.py``, downloads that build's tarball,
extracts ``sublime.py``, ``sublime_plugin.py`` and ``sublime_types.py`` into the
reference directory, and bumps ``ST_BUILD`` and the build number in
``references/README.md``.

    python tools/update_reference.py              # the latest build, if newer
    python tools/update_reference.py --build N    # build N, unconditionally

It neither runs the generator nor commits: it only edits the working tree, and it
leaves the tree untouched when there is nothing newer or when any step fails, so a
caller can tell "nothing to do" from "updated" by the tree being clean.
"""

from __future__ import annotations

import argparse
import json
import lzma
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from collections.abc import Sequence
from http.client import HTTPException, HTTPResponse
from pathlib import Path
from typing import cast

from generate_stubs import REFERENCE_DIR, REPO_ROOT, ST_BUILD

# Stable and dev are separate channels that report different builds, so both are
# asked and the higher build wins.
UPDATE_CHECK_URLS = {
    "stable": "https://www.sublimetext.com/updates/4/stable_update_check",
    "dev": "https://www.sublimetext.com/updates/4/dev_update_check",
}
TARBALL_URL = "https://download.sublimetext.com/sublime_text_build_{build}_x64.tar.xz"
TIMEOUT_SECONDS = 60

REFERENCE_FILES = ("sublime.py", "sublime_plugin.py", "sublime_types.py")
ARCHIVE_LIB = "sublime_text/Lib"
PLUGIN_HOST_DIR = re.compile(rf"^{re.escape(ARCHIVE_LIB)}/(python3\d+)/")
# The deprecated Python 3.3 plugin host ships alongside the current one and is not
# targeted by these stubs, see `references/README.md`.
LEGACY_PLUGIN_HOST = "python33"

GENERATOR = REPO_ROOT / "tools" / "generate_stubs.py"
REFERENCE_README = REPO_ROOT / "references" / "README.md"
ST_BUILD_PATTERN = re.compile(r'^ST_BUILD = "\d+"$', re.MULTILINE)
# Only the first two lines of the README name the extracted build; the patterns are
# applied there alone, so a build number mentioned further down is never rewritten.
README_HEAD_LINES = 2
README_BUILD_PATTERN = re.compile(r"extracted from ST build \d+")
README_TARBALL_PATTERN = re.compile(r"sublime_text_build_\d+_x64\.tar\.xz")


class UpdateError(Exception):
    """A step failed; the message is shown to the user and nothing has been written."""


class Options(argparse.Namespace):
    """Typed view of the parsed arguments; `argparse.Namespace` is otherwise untyped."""

    build: int | None = None


def fetch_latest_build(channel: str, url: str) -> int:
    try:
        with cast("HTTPResponse", urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS)) as response:
            body = response.read()
        data = cast("object", json.loads(body))
    # `http.client.HTTPException` (`IncompleteRead`, ...) is no `OSError` but escapes `read()`.
    except (OSError, HTTPException, ValueError) as error:
        raise UpdateError(f"cannot query the {channel} update check at {url}: {error}") from error
    # The response is untrusted input: check its shape instead of assuming it.
    if not isinstance(data, dict):
        raise UpdateError(f"unexpected {channel} update check response from {url}: {data!r}")
    value = cast("dict[str, object]", data).get("latest_version")
    if not isinstance(value, int) or isinstance(value, bool):
        raise UpdateError(f"unexpected {channel} latest_version from {url}: {value!r}")
    return value


def latest_build() -> int:
    builds: list[int] = []
    for channel, url in UPDATE_CHECK_URLS.items():
        build = fetch_latest_build(channel, url)
        print(f"{channel}: {build}")
        builds.append(build)
    return max(builds)


def download(url: str, target: Path) -> None:
    print(f"downloading {url}")
    try:
        with (
            cast("HTTPResponse", urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS)) as response,
            target.open("wb") as file,
        ):
            shutil.copyfileobj(response, file)
    except (OSError, HTTPException) as error:
        raise UpdateError(f"cannot download {url}: {error}") from error


def read_reference_files(tarball: Path) -> dict[str, bytes]:
    """Return the reference files of the tarball's plugin host, keyed by file name.

    Members are only ever looked up by their exact expected name and their content
    is later written to fixed paths, so no path taken from the archive is trusted.
    """
    wanted = {f"{ARCHIVE_LIB}/{REFERENCE_DIR.name}/{name}": name for name in REFERENCE_FILES}
    hosts: set[str] = set()
    contents: dict[str, bytes] = {}
    try:
        # A single sequential pass: seeking back in an xz stream means decompressing
        # it again from the start.
        with tarfile.open(tarball, "r:xz") as archive:
            for member in archive:
                if match := PLUGIN_HOST_DIR.match(member.name):
                    hosts.add(match.group(1))
                name = wanted.get(member.name)
                if name is None or not member.isreg():
                    continue
                file = archive.extractfile(member)
                if file is None:
                    continue
                with file:
                    contents[name] = file.read()
    except (tarfile.TarError, lzma.LZMAError, EOFError, OSError) as error:
        raise UpdateError(f"cannot read {tarball.name}: {error}") from error

    hosts.discard(LEGACY_PLUGIN_HOST)
    if hosts != {REFERENCE_DIR.name}:
        found = ", ".join(sorted(hosts)) or "none"
        raise UpdateError(
            " ".join(
                (
                    f"expected the plugin host {REFERENCE_DIR.name} in {ARCHIVE_LIB}/, found: {found}.",
                    "If the build ships a new Python version, `git mv` the reference directory",
                    "and point REFERENCE_DIR in tools/generate_stubs.py at it first,",
                    'see "Onboarding a new Sublime Text build" in CONTRIBUTING.md.',
                )
            )
        )
    if missing := [name for name in REFERENCE_FILES if name not in contents]:
        raise UpdateError(
            f"{tarball.name} has no regular file {', '.join(missing)} in {ARCHIVE_LIB}/{REFERENCE_DIR.name}/"
        )
    return contents


def substitute_once(pattern: re.Pattern[str], replacement: str, text: str, path: Path) -> str:
    result, count = pattern.subn(replacement, text)
    if count != 1:
        raise UpdateError(
            f"expected exactly one match of {pattern.pattern!r} in {path.relative_to(REPO_ROOT)}, found {count}"
        )
    return result


def rewrite_build_mentions(build: int) -> dict[Path, str]:
    """Return the generator and the reference README with their build numbers set to `build`."""
    generator = substitute_once(ST_BUILD_PATTERN, f'ST_BUILD = "{build}"', GENERATOR.read_text(), GENERATOR)

    lines = REFERENCE_README.read_text().splitlines(keepends=True)
    head = "".join(lines[:README_HEAD_LINES])
    head = substitute_once(README_BUILD_PATTERN, f"extracted from ST build {build}", head, REFERENCE_README)
    head = substitute_once(README_TARBALL_PATTERN, f"sublime_text_build_{build}_x64.tar.xz", head, REFERENCE_README)
    readme = head + "".join(lines[README_HEAD_LINES:])

    return {GENERATOR: generator, REFERENCE_README: readme}


def update(build: int) -> None:
    with tempfile.TemporaryDirectory() as directory:
        tarball = Path(directory) / f"sublime_text_build_{build}_x64.tar.xz"
        download(TARBALL_URL.format(build=build), tarball)
        references = read_reference_files(tarball)
    rewrites = rewrite_build_mentions(build) if str(build) != ST_BUILD else {}

    # Every step that can fail has succeeded: only now is the repository touched,
    # so a failure never leaves it half updated.
    for name, content in references.items():
        path = REFERENCE_DIR / name
        _ = path.write_bytes(content)
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    for path, text in rewrites.items():
        _ = path.write_text(text)
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    print(f"extracted the reference sources of ST build {build}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    _ = parser.add_argument(
        "--build",
        type=int,
        help="extract this build instead of the latest one, even if it is not newer than ST_BUILD",
    )
    options = parser.parse_args(argv, namespace=Options())

    try:
        build = options.build
        if build is None:
            build = latest_build()
            if build <= int(ST_BUILD):
                print(f"main is up to date: ST_BUILD is {ST_BUILD}, the latest build is {build}")
                return 0
        update(build)
    except UpdateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
