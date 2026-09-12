#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import tomllib
from typing import Any

REPOSITORY = "mike-axiom-mir/axm-framestate"
DISPLAY_NAME = "AXM FrameState"
DISCOVERY_BUDDY_REF = "565c38ecf93a9d563b02211258d8d36fcb1162b5"
PATTERN_REPOSITORY = "mike-axiom-mir/axm-casual-loop"
PATTERN_REF = "f561a8a325444be30ad0b4fee412b3958aa1f1ee"

MARKER_PATH = ".axm/discovery-public.json"
PACKAGE_PATH = "pyproject.toml"
CAPABILITY_MAP_PATH = "src/axm_framestate/capabilities.py"
CANONICAL_PATH = "src/axm_framestate/canonical.py"
CLI_PATH = "src/axm_framestate/cli.py"
MEDIA_PATH = "src/axm_framestate/media.py"
LICENSE_PATH = "LICENSE"
REGISTRY_PATH = "registry/capabilities.jsonl"
RECEIPT_PATH = "registry/capabilities.receipt.json"

CAPABILITY_ID = "axm.framestate.local-deterministic-video-machine"
CAPABILITY_MAP_SCHEMA = "axm.framestate.capability-map/v0.16"
PROJECT_SCHEMA = "axm.framestate.project/v0.5"
EXPECTED_VERSION = "0.16.0"
EXPECTED_DESCRIPTION = "Standalone deterministic video creation and growth machine"
SOURCE_PATHS = (
    PACKAGE_PATH,
    CAPABILITY_MAP_PATH,
    CANONICAL_PATH,
    CLI_PATH,
    MEDIA_PATH,
    LICENSE_PATH,
)

ANCHORS = {
    "canonical-project-state": "executable",
    "repeat-verification": "tested",
    "adaptive-realization-planner": "tested",
    "dependency-free-core-package": "tested",
    "media-output-confinement": "tested",
    "forge-single-writer-publication": "tested",
    "render-checkpoint-integrity": "tested",
    "renderer-neutral-visual-state-bridge": "tested",
    "echoworld-replay-visual-bridge": "tested",
    "caller-pinned-render-output-verification": "tested",
    "mp4-assembly": "external-boundary",
    "human-intelligible-native-speech": "gap",
}


class DiscoveryError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DiscoveryError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise DiscoveryError(f"non-finite JSON number: {value}")


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise DiscoveryError(str(exc)) from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def regular_file(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = root / relative_path
    try:
        info = candidate.lstat()
    except FileNotFoundError as exc:
        raise DiscoveryError(f"required source is missing: {relative_path}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise DiscoveryError(f"source must be a regular non-symlink file: {relative_path}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except ValueError as exc:
        raise DiscoveryError(f"source path escapes repository root: {relative_path}") from exc
    return resolved


def read_json_file(root: Path, relative_path: str) -> Any:
    try:
        text = regular_file(root, relative_path).read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise DiscoveryError(f"source is not valid UTF-8: {relative_path}") from exc
    return strict_json_loads(text)


def source_record(root: Path, relative_path: str) -> dict[str, str]:
    data = regular_file(root, relative_path).read_bytes()
    return {"path": relative_path, "git_blob_sha1": git_blob_sha1(data)}


def load_source_module(root: Path, relative_path: str, module_name: str):
    source = regular_file(root, relative_path)
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise DiscoveryError(f"cannot load source module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise DiscoveryError(f"cannot load source module {relative_path}: {exc}") from exc
    return module


def validate_marker(root: Path) -> None:
    marker = read_json_file(root, MARKER_PATH)
    expected = {
        "schema": "axm.discovery-public/v1",
        "public": True,
        "repo": REPOSITORY,
        "display_name": DISPLAY_NAME,
    }
    if marker != expected:
        raise DiscoveryError("public discovery marker drift")


def validate_package(root: Path) -> dict[str, Any]:
    try:
        package = tomllib.loads(regular_file(root, PACKAGE_PATH).read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeError) as exc:
        raise DiscoveryError(f"invalid pyproject.toml: {exc}") from exc
    project = package.get("project")
    if not isinstance(project, dict):
        raise DiscoveryError("pyproject project table missing")
    if project.get("name") != "axm-framestate":
        raise DiscoveryError("package name drift")
    if project.get("version") != EXPECTED_VERSION:
        raise DiscoveryError("package version drift; review public capability mapping")
    if project.get("description") != EXPECTED_DESCRIPTION:
        raise DiscoveryError("package description drift; review public capability mapping")
    if project.get("requires-python") != ">=3.11":
        raise DiscoveryError("Python runtime boundary drift")
    if project.get("dependencies") != []:
        raise DiscoveryError("declared package dependency boundary drift")
    if project.get("license") != "Apache-2.0":
        raise DiscoveryError("package license declaration drift")
    scripts = project.get("scripts")
    expected_scripts = {
        "framestate": "axm_framestate.cli:main",
        "framestate-studio": "axm_framestate.studio:main",
        "framestate-render-resume": "axm_framestate.resumable:main",
        "framestate-render-parallel": "axm_framestate.parallel_movie:main",
        "framestate-semantic": "axm_framestate.semantic:main",
        "framestate-portable": "axm_framestate.portable:main",
    }
    if scripts != expected_scripts:
        raise DiscoveryError("installed command boundary drift")
    license_text = regular_file(root, LICENSE_PATH).read_text(encoding="utf-8")
    if "Apache License" not in license_text or "Version 2.0, January 2004" not in license_text:
        raise DiscoveryError("Apache-2.0 license evidence drift")
    return project

def validate_current_cli_import_boundary(root: Path) -> None:
    media_source = regular_file(root, MEDIA_PATH).read_text(encoding="utf-8")
    if "\nfrom PIL import Image" in media_source:
        raise DiscoveryError("current CLI Pillow import boundary drift; top-level Pillow dependency returned")
    if "def _pillow_image():" not in media_source or "from PIL import Image" not in media_source:
        raise DiscoveryError("current CLI Pillow import boundary drift; lazy compatibility boundary changed")
    cli_source = regular_file(root, CLI_PATH).read_text(encoding="utf-8")
    if "from .receipts import" not in cli_source or "from .capabilities import" not in cli_source:
        raise DiscoveryError("current CLI import graph drift; review public runtime mapping")

def validate_capability_map(root: Path) -> dict[str, Any]:
    module = load_source_module(root, CAPABILITY_MAP_PATH, "_axm_framestate_public_capabilities")
    summary = module.capability_summary()
    if not isinstance(summary, dict) or summary.get("schema") != CAPABILITY_MAP_SCHEMA:
        raise DiscoveryError("capability-map schema drift")
    capabilities = summary.get("capabilities")
    if not isinstance(capabilities, dict):
        raise DiscoveryError("capability-map rows missing")
    for capability_id, expected_status in ANCHORS.items():
        row = capabilities.get(capability_id)
        if not isinstance(row, dict) or row.get("status") != expected_status:
            raise DiscoveryError(f"capability-map anchor drift: {capability_id}")
        if not isinstance(row.get("evidence"), str) or not row["evidence"]:
            raise DiscoveryError(f"capability-map evidence missing: {capability_id}")
    canonical = load_source_module(root, CANONICAL_PATH, "_axm_framestate_public_canonical")
    if getattr(canonical, "PROJECT_SCHEMA", None) != PROJECT_SCHEMA:
        raise DiscoveryError("canonical project schema drift")
    return summary


def build_artifacts(root: Path | str = Path.cwd()) -> dict[str, str]:
    root = Path(root)
    validate_marker(root)
    project = validate_package(root)
    validate_current_cli_import_boundary(root)
    capability_map = validate_capability_map(root)
    sources = [source_record(root, relative_path) for relative_path in SOURCE_PATHS]

    record = {
        "schema": "axm.public-capability/v1",
        "id": CAPABILITY_ID,
        "version": project["version"],
        "status": None,
        "providers": [REPOSITORY],
        "consumers": [],
        "summary": project["description"],
        "license": project["license"],
        "runtime": {
            "language": "python",
            "minimumVersion": "3.11",
            "dependencies": 0,
            "declaredPackageDependencies": 0,
            "externalPythonPackages": [],
            "network": False,
            "account": False,
            "aiModel": False,
        },
        "entrypoints": {
            "command": "framestate",
            "discoveryCommand": "framestate capabilities",
            "library": "axm_framestate",
        },
        "contracts": {
            "capabilityMap": capability_map["schema"],
            "canonicalProject": PROJECT_SCHEMA,
            "currentCliImportBoundary": "dependency-free-core-lazy-optional-media-v0.16",
        },
        "source": {
            "metadata": PACKAGE_PATH,
            "capabilityMap": CAPABILITY_MAP_PATH,
            "canonicalProject": CANONICAL_PATH,
            "command": CLI_PATH,
            "cliMediaImportBoundary": MEDIA_PATH,
            "license": LICENSE_PATH,
        },
        "authority": {
            "discoveryOnly": True,
            "execution": False,
            "automaticSelection": False,
            "automaticInstall": False,
            "projectMutation": False,
            "merge": False,
            "canon": False,
        },
    }
    registry_text = canonical_json(record) + "\n"

    receipt_body = {
        "schema": "axm.public-capability-registry-receipt/v1",
        "repository": REPOSITORY,
        "registry": {
            "path": REGISTRY_PATH,
            "sha256": sha256_bytes(registry_text.encode("utf-8")),
            "capability_count": 1,
            "capability_ids": [CAPABILITY_ID],
        },
        "sources": sources,
        "compatibility": {
            "consumer": "mike-axiom-mir/axm-discovery-buddy",
            "pinned_ref": DISCOVERY_BUDDY_REF,
            "portable_boundary": "discovery-buddy.pyz",
            "marker_contract": "axm.discovery-public/v1",
            "registry_contract": "registry/*capabilit*.jsonl",
        },
        "pattern_provenance": {
            "adapted_from_repository": PATTERN_REPOSITORY,
            "adapted_from_ref": PATTERN_REF,
            "adapted_paths": [
                ".axm/discovery-public.json",
                "tools/generate_public_capabilities.py",
                ".github/workflows/public-capability-discovery.yml",
            ],
            "copied_runtime_code": False,
        },
        "truth_boundary": {
            "source_backed": True,
            "public_export_intent": True,
            "runtime_proof": False,
            "current_cli_external_python_boundary": [],
            "execution_authority": False,
            "automatic_selection_authority": False,
            "automatic_install_authority": False,
            "project_mutation_authority": False,
            "merge_authority": False,
            "canon_authority": False,
        },
    }
    receipt = dict(receipt_body)
    receipt["receipt_sha256"] = sha256_bytes(canonical_json(receipt_body).encode("utf-8"))
    return {
        REGISTRY_PATH: registry_text,
        RECEIPT_PATH: json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
    }


def check_artifacts(root: Path | str = Path.cwd()) -> tuple[bool, list[str], dict[str, str]]:
    root = Path(root)
    expected = build_artifacts(root)
    mismatches: list[str] = []
    for relative_path, expected_text in expected.items():
        target = root / relative_path
        try:
            actual_text = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            actual_text = None
        if actual_text != expected_text:
            mismatches.append(relative_path)
    return not mismatches, mismatches, expected


def write_artifacts(root: Path | str = Path.cwd()) -> dict[str, str]:
    root = Path(root)
    artifacts = build_artifacts(root)
    for relative_path, text in artifacts.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate FrameState public capability discovery evidence.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail when committed generated evidence is stale")
    mode.add_argument("--write", action="store_true", help="write generated evidence (default)")
    parser.add_argument("--root", default=".", help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.check:
            ok, mismatches, _ = check_artifacts(root)
            if not ok:
                print("public capability registry is stale: " + ", ".join(mismatches), file=sys.stderr)
                return 1
            print("FrameState public capability registry: PASS")
            return 0
        artifacts = write_artifacts(root)
        print("FrameState public capability registry: wrote " + ", ".join(artifacts))
        return 0
    except (DiscoveryError, OSError, ValueError, TypeError) as exc:
        print(f"FrameState public capability registry: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
