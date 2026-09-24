#!/usr/bin/env python3
"""Guard the hand-off of a verified canon artifact into a public checkout.

This helper is packaged beside ``canon_publication.py``.  It deliberately has
no network or git-write operation: CI obtains the public checkout, this script
checks that checkout is the repository named by the release contract, and then
materializes exactly the already-verified artifact.  The workflow owns the
reviewable git commit, tag and push.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib


FORMAT = "law.canon-publication/1"
MANIFEST_FORMAT = "law.canon-manifest/1"
PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class ReleaseError(ValueError):
    """A publication precondition was not met."""


def load_contract(path: Path) -> dict:
    exporter = Path(__file__).with_name("canon_publication.py")
    if not exporter.is_file():
        exporter = Path(__file__).parent.parent / "canon_publication.py"
    try:
        spec = importlib.util.spec_from_file_location("_canon_publication", exporter)
        if spec is None or spec.loader is None:
            raise OSError("cannot load canon_publication.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.read_config(path)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        raise ReleaseError(f"cannot read publication contract: {error}") from error


def run_exporter(mode: str, artifact: Path) -> None:
    exporter = Path(__file__).with_name("canon_publication.py")
    # Source-tree tests keep the exporter one directory above this template
    # directory.  Released tools always use the sibling copy.
    if not exporter.is_file():
        exporter = Path(__file__).parent.parent / "canon_publication.py"
    if not exporter.is_file():
        raise ReleaseError("canon_publication.py is missing beside canon_release.py")
    try:
        subprocess.run([sys.executable, str(exporter), mode, "--artifact", str(artifact)],
                       check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        raise ReleaseError("canon artifact verification failed") from error


def manifest(artifact: Path) -> dict:
    run_exporter("verify", artifact)
    try:
        data = json.loads((artifact / "CANON-MANIFEST.json").read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseError(f"cannot read canonical manifest: {error}") from error
    if data.get("format") != MANIFEST_FORMAT:
        raise ReleaseError("canonical manifest has an unsupported format")
    return data


def verify_contract(contract: dict, artifact: Path) -> dict:
    data = manifest(artifact)
    if (not all(isinstance(name, str) and PACKAGE_NAME.fullmatch(name)
                for name in data["packages"])):
        raise ReleaseError("manifest contains an invalid package name")
    fields = ("version", "repository", "releasedAt")
    if (any(data.get(key) != contract[key] for key in fields)
            or data.get("packages") != sorted(contract["packages"])
            or data.get("requiredFiles") != sorted(contract["requiredFiles"])):
        raise ReleaseError("artifact identity does not match publication contract")
    expected = {entry["path"] for entry in data.get("files", []) if isinstance(entry, dict) and "path" in entry}
    # The generated manifest cannot hash itself.  The exporter verifies it
    # separately, so its `files` list contains only contract allowlist entries.
    if expected != set(contract["files"]):
        raise ReleaseError("artifact inventory does not match publication contract")
    return data


def normalize_repository(value: str) -> str:
    value = value.removesuffix("/")
    if value.endswith(".git"):
        value = value[:-4]
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    return value


def assert_checkout_repository(checkout: Path, repository: str) -> None:
    try:
        actual = subprocess.check_output(["git", "-C", str(checkout), "remote", "get-url", "origin"], text=True).strip()
    except subprocess.CalledProcessError as error:
        raise ReleaseError("public checkout has no origin remote") from error
    if normalize_repository(actual) != normalize_repository(repository):
        raise ReleaseError("public checkout origin differs from the repository bound by publication.toml")


def assert_clean_checkout(checkout: Path) -> None:
    try:
        dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain",
                                         "--untracked-files=all", "--ignored"], text=True)
    except subprocess.CalledProcessError as error:
        raise ReleaseError("cannot determine public checkout status") from error
    if dirty:
        raise ReleaseError("public checkout is dirty; refusing to delete or replace files")


def assert_nonoverlapping(first: Path, second: Path) -> None:
    first, second = first.resolve(), second.resolve()
    if first == second or first.is_relative_to(second) or second.is_relative_to(first):
        raise ReleaseError("artifact and public checkout must not overlap")


def copy_artifact(artifact: Path, checkout: Path) -> None:
    if not checkout.is_dir() or not (checkout / ".git").exists():
        raise ReleaseError("output must be an existing git checkout")
    # The exporter permits only regular files below its artifact root.  Still,
    # reject unexpected filesystem objects before deleting any public content.
    for path in artifact.rglob("*"):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise ReleaseError("artifact contains an unsafe filesystem object")
    for child in checkout.iterdir():
        if child.name == ".git":
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            raise ReleaseError("public checkout contains an unsafe filesystem object")
    for source in sorted(path for path in artifact.rglob("*") if path.is_file()):
        relative = source.relative_to(artifact)
        target = checkout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o644)


def copied_inventory(root: Path) -> dict[str, bytes]:
    result = {}
    for path in root.rglob("*"):
        if ".git" in path.relative_to(root).parts:
            continue
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise ReleaseError("public checkout contains an unsafe filesystem object")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def stage(contract_path: Path, artifact: Path, checkout: Path) -> dict:
    contract = load_contract(contract_path)
    data = verify_contract(contract, artifact)
    assert_nonoverlapping(artifact, checkout)
    assert_checkout_repository(checkout, contract["repository"])
    assert_clean_checkout(checkout)
    copy_artifact(artifact, checkout)
    # The checkout has .git, so it is not itself an export artifact.  Compare
    # its non-git bytes with the artifact after copying instead.
    if copied_inventory(checkout) != copied_inventory(artifact):
        raise ReleaseError("public checkout changed while staging artifact")
    return data


def build_packages(artifact: Path, tools: Path, out: Path) -> None:
    """Build precisely the packages declared by the verified public manifest."""
    data = manifest(artifact)
    if out.exists():
        raise ReleaseError("package release output must be new")
    assert_nonoverlapping(artifact, out)
    assert_nonoverlapping(tools, out)
    runner, binary = tools / "package.py", tools / "law-cli"
    if not runner.is_file() or not binary.is_file():
        raise ReleaseError("pinned toolchain lacks package.py or law-cli")
    roots: dict[str, Path] = {}
    try:
        top_level = artifact / "packages"
        if top_level.is_dir():
            for law_toml in top_level.glob("*/law.toml"):
                name = tomllib.loads(law_toml.read_text(encoding="utf-8"))["package"]["name"]
                if name not in data["packages"]:
                    raise ReleaseError(f"top-level exported package {name} is absent from manifest packages")
        for law_toml in artifact.rglob("law.toml"):
            if law_toml.is_symlink():
                raise ReleaseError("exported law.toml is a symlink")
            name = tomllib.loads(law_toml.read_text(encoding="utf-8"))["package"]["name"]
            if name in data["packages"]:
                if name in roots:
                    raise ReleaseError(f"package {name} has more than one exported root")
                roots[name] = law_toml.parent
        if set(roots) != set(data["packages"]):
            raise ReleaseError("not every manifest package has exactly one exported law.toml")
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ReleaseError(f"cannot resolve exported package roots: {error}") from error
    out.mkdir(parents=True)
    for number, name in enumerate(data["packages"], start=1):
        try:
            subprocess.run([sys.executable, str(runner), str(roots[name]), "--lawc", str(binary),
                            "--offline", "--out", str(out / str(number))], check=True)
        except subprocess.CalledProcessError as error:
            raise ReleaseError(f"pinned package validation failed for {name}") from error
    # package.py must be read-only with respect to the public candidate.
    manifest(artifact)


def preview(artifact: Path, previous: Path | None) -> dict:
    """Return a deterministic candidate inventory diff, without copying files."""
    current = manifest(artifact)
    current_files = {item["path"]: item["sha256"] for item in current["files"]}
    if previous is None:
        return {"format": "law.canon-preview/1", "firstRelease": True,
                "added": sorted(current_files), "changed": [], "removed": []}
    old = manifest(previous)
    old_files = {item["path"]: item["sha256"] for item in old["files"]}
    return {"format": "law.canon-preview/1", "firstRelease": False,
            "added": sorted(set(current_files) - set(old_files)),
            "changed": sorted(path for path in set(current_files) & set(old_files)
                              if current_files[path] != old_files[path]),
            "removed": sorted(set(old_files) - set(current_files))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "stage", "identity", "build", "preview"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            if args.artifact is None or args.tools is None or args.out is None:
                raise ReleaseError("build requires --artifact, --tools and --out")
            build_packages(args.artifact, args.tools, args.out)
        else:
            if args.command == "preview":
                if args.artifact is None:
                    raise ReleaseError("preview requires --artifact")
                print(json.dumps(preview(args.artifact, args.previous), sort_keys=True))
                return
            if args.command == "verify" and args.config is None:
                if args.artifact is None:
                    raise ReleaseError("verify requires --artifact")
                print(json.dumps(manifest(args.artifact), sort_keys=True))
                return
            if args.config is None:
                raise ReleaseError(f"{args.command} requires --config")
            contract = load_contract(args.config)
            if args.command == "identity":
                print(json.dumps({key: contract[key] for key in ("version", "repository")}, sort_keys=True))
            elif args.command == "verify":
                if args.artifact is None:
                    raise ReleaseError("verify requires --artifact")
                print(json.dumps(verify_contract(contract, args.artifact), sort_keys=True))
            else:
                if args.artifact is None or args.checkout is None:
                    raise ReleaseError("stage requires --artifact and --checkout")
                print(json.dumps(stage(args.config, args.artifact, args.checkout), sort_keys=True))
    except ReleaseError as error:
        parser.exit(1, f"canon release: REFUSED: {error}\n")


if __name__ == "__main__":
    main()
