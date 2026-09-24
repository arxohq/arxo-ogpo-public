#!/usr/bin/env python3
"""Pinned delivery of law-cli + package.py; installed only against an external SHA-256.

Python 3.12+, standard library only. `download` needs gh with access to the Releases
of the repository named by the lock; `install` works from a local archive. No file
from the archive is executed during installation. Building a release is not done
here: this file only obtains one and verifies it against the pin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import tempfile
import zipfile

TARGET = "x86_64-unknown-linux-musl"
FILES = {"law-cli", "package.py", "LICENSE"}
CANON_FILES = {"canon_publication.py", "canon_release.py"}
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_UNPACKED = 128 * 1024 * 1024


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def validate_lock(lock: dict) -> dict:
    if not isinstance(lock, dict) or set(lock) != {
        "format", "version", "target", "sourceCommit", "repository", "tag", "asset", "sha256"
    } or lock["format"] != "law.package-toolchain-lock/0.1":
        raise ValueError("unsupported toolchain lock format")
    if not all(isinstance(v, str) for v in lock.values()):
        raise ValueError("toolchain lock fields must be strings")
    if (not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", lock["version"])
            or not re.fullmatch(r"[a-f0-9]{40}", lock["sourceCommit"])
            or not re.fullmatch(r"[a-f0-9]{64}", lock["sha256"])
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", lock["repository"])
            or lock["target"] != TARGET
            or lock["tag"] != f"law-package-tools@{lock['version']}"
            or lock["asset"] != f"law-package-tools-{lock['version']}-{TARGET}.zip"):
        raise ValueError("invalid toolchain lock coordinates or hashes")
    return lock


def install(archive: Path, lock: dict, out: Path) -> dict:
    validate_lock(lock)
    if lock["sourceCommit"] == "0" * 40:
        raise ValueError(f"release {lock['version']} ещё не закреплён: замените временный lock пином выпуска")
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise ValueError("this release supports Linux x86_64 only")
    if out.exists() or out.is_symlink():
        raise ValueError("the installation directory must be a new one")
    if archive.stat().st_size > MAX_ARCHIVE or sha(archive.read_bytes()) != lock["sha256"]:
        raise ValueError("archive SHA-256 or size does not match the pin")
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        names = [entry.filename for entry in entries]
        allowed_sets = (FILES | {"toolchain.json"}, FILES | CANON_FILES | {"toolchain.json"})
        if len(names) != len(set(names)) or set(names) not in allowed_sets:
            raise ValueError("invalid paths, contents or duplicates in the archive")
        if sum(entry.file_size for entry in entries) > MAX_UNPACKED:
            raise ValueError("the unpacked size limit is exceeded")
        if any(stat.S_IFMT(entry.external_attr >> 16) != stat.S_IFREG for entry in entries):
            raise ValueError("only regular files are allowed in the archive")
        payloads = {name: bundle.read(name) for name in names}
    manifest = json.loads(payloads.pop("toolchain.json"))
    expected = {"format": "law.package-toolchain/0.1",
                **{key: lock[key] for key in ("version", "target", "sourceCommit")},
                "files": {name: sha(data) for name, data in sorted(payloads.items())}}
    if manifest != expected:
        raise ValueError("toolchain file set, identity or hashes diverge from the pin")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="law-toolchain-", dir=out.parent) as temp:
        staged = Path(temp) / "tools"
        staged.mkdir()
        for name, data in {**payloads, "toolchain.json": encoded(manifest)}.items():
            path = staged / name
            path.write_bytes(data)
            path.chmod(0o755 if name == "law-cli" else 0o644)
        os.rename(staged, out)
    return manifest


def download(lock: dict, out: Path) -> dict:
    validate_lock(lock)
    if lock["sourceCommit"] == "0" * 40:
        raise ValueError(f"release {lock['version']} ещё не закреплён: замените временный lock пином выпуска")
    with tempfile.TemporaryDirectory(prefix="law-toolchain-download-") as temp:
        subprocess.run(["gh", "release", "download", lock["tag"], "--repo", lock["repository"],
                        "--pattern", lock["asset"], "--dir", temp], check=True, timeout=180)
        return install(Path(temp) / lock["asset"], lock, out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("install", "download"):
        command = sub.add_parser(mode)
        command.add_argument("--lock", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        if mode == "install":
            command.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        lock = validate_lock(json.loads(args.lock.read_bytes()))
        result = (install(args.archive, lock, args.out) if args.mode == "install"
                  else download(lock, args.out))
        print(encoded(result).decode(), end="")
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        parser.exit(1, f"toolchain: REFUSED: {error}\n")


if __name__ == "__main__":
    main()
