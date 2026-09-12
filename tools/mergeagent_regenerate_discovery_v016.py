from __future__ import annotations

from pathlib import Path
import re


def replace_function(source: str, name: str, next_name: str, body: str) -> str:
    start = source.index(f"def {name}(")
    end = source.index(f"\ndef {next_name}(", start)
    return source[:start] + body.rstrip() + "\n\n" + source[end + 1 :]


def main() -> None:
    cap = Path("src/axm_framestate/capabilities.py")
    text = cap.read_text(encoding="utf-8")
    old = "'cross-python-regression':('tested','69-test complete regression tree passes on CPython 3.11, 3.12 and 3.13 in GitHub Actions'),"
    rows = [
        "'strict-canonical-json-admission':('tested','canonical JSON rejects non-finite state instead of emitting non-portable JSON'),",
        "'media-output-confinement':('tested','portable media ids and symlink-aware output guards keep generated media beneath the selected render root'),",
        "'forge-single-writer-publication':('tested','effect and recipe adoption use create-only single-writer publication with concurrent losers held'),",
        "'render-checkpoint-integrity':('tested','resumable checkpoint admission binds persisted progress to checkpoint and frame evidence before continuation'),",
        "'renderer-neutral-visual-state-bridge':('tested','pinned Universal Creation visual-state evidence maps only bounded realization direction; unsupported state remains held'),",
        "'echoworld-replay-visual-bridge':('tested','caller-pinned EchoWorld replay evidence is admitted and rendered through a non-authoritative deterministic projection'),",
        "'caller-pinned-render-output-verification':('tested','read-only local admission verifies caller-pinned receipt/project identity plus manifests, frames, audio, captions and realization evidence'),",
        "'cross-python-regression':('tested','complete regression tree is exercised on CPython 3.11, 3.12 and 3.13 in GitHub Actions'),",
    ]
    if text.count(old) != 1:
        raise SystemExit("capability map insertion target drift")
    cap.write_text(text.replace(old, "\n".join(rows), 1), encoding="utf-8")

    gen = Path("tools/generate_public_capabilities.py")
    text = gen.read_text(encoding="utf-8")
    text = text.replace(
        'CAPABILITY_MAP_SCHEMA = "axm.framestate.capability-map/v0.10"',
        'CAPABILITY_MAP_SCHEMA = "axm.framestate.capability-map/v0.16"',
    )
    text = text.replace('EXPECTED_VERSION = "0.10.0"', 'EXPECTED_VERSION = "0.16.0"')

    anchors = "\n".join(
        [
            "ANCHORS = {",
            '    "canonical-project-state": "executable",',
            '    "repeat-verification": "tested",',
            '    "adaptive-realization-planner": "tested",',
            '    "dependency-free-core-package": "tested",',
            '    "media-output-confinement": "tested",',
            '    "forge-single-writer-publication": "tested",',
            '    "render-checkpoint-integrity": "tested",',
            '    "renderer-neutral-visual-state-bridge": "tested",',
            '    "echoworld-replay-visual-bridge": "tested",',
            '    "caller-pinned-render-output-verification": "tested",',
            '    "mp4-assembly": "external-boundary",',
            '    "human-intelligible-native-speech": "gap",',
            "}",
        ]
    )
    text, count = re.subn(r"ANCHORS = \{.*?\n\}", anchors, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("generator anchor block drift")

    package_fn = "\n".join(
        [
            "def validate_package(root: Path) -> dict[str, Any]:",
            "    try:",
            '        package = tomllib.loads(regular_file(root, PACKAGE_PATH).read_text(encoding="utf-8"))',
            "    except (tomllib.TOMLDecodeError, UnicodeError) as exc:",
            '        raise DiscoveryError(f"invalid pyproject.toml: {exc}") from exc',
            '    project = package.get("project")',
            "    if not isinstance(project, dict):",
            '        raise DiscoveryError("pyproject project table missing")',
            '    if project.get("name") != "axm-framestate":',
            '        raise DiscoveryError("package name drift")',
            '    if project.get("version") != EXPECTED_VERSION:',
            '        raise DiscoveryError("package version drift; review public capability mapping")',
            '    if project.get("description") != EXPECTED_DESCRIPTION:',
            '        raise DiscoveryError("package description drift; review public capability mapping")',
            '    if project.get("requires-python") != ">=3.11":',
            '        raise DiscoveryError("Python runtime boundary drift")',
            '    if project.get("dependencies") != []:',
            '        raise DiscoveryError("declared package dependency boundary drift")',
            '    if project.get("license") != "Apache-2.0":',
            '        raise DiscoveryError("package license declaration drift")',
            '    scripts = project.get("scripts")',
            "    expected_scripts = {",
            '        "framestate": "axm_framestate.cli:main",',
            '        "framestate-studio": "axm_framestate.studio:main",',
            '        "framestate-render-resume": "axm_framestate.resumable:main",',
            '        "framestate-render-parallel": "axm_framestate.parallel_movie:main",',
            '        "framestate-semantic": "axm_framestate.semantic:main",',
            '        "framestate-portable": "axm_framestate.portable:main",',
            "    }",
            "    if scripts != expected_scripts:",
            '        raise DiscoveryError("installed command boundary drift")',
            '    license_text = regular_file(root, LICENSE_PATH).read_text(encoding="utf-8")',
            '    if "Apache License" not in license_text or "Version 2.0, January 2004" not in license_text:',
            '        raise DiscoveryError("Apache-2.0 license evidence drift")',
            "    return project",
        ]
    )
    text = replace_function(text, "validate_package", "validate_current_cli_import_boundary", package_fn)

    cli_fn = "\n".join(
        [
            "def validate_current_cli_import_boundary(root: Path) -> None:",
            '    media_source = regular_file(root, MEDIA_PATH).read_text(encoding="utf-8")',
            '    if "\\nfrom PIL import Image" in media_source:',
            '        raise DiscoveryError("current CLI Pillow import boundary drift; top-level Pillow dependency returned")',
            '    if "def _pillow_image():" not in media_source or "from PIL import Image" not in media_source:',
            '        raise DiscoveryError("current CLI Pillow import boundary drift; lazy compatibility boundary changed")',
            '    cli_source = regular_file(root, CLI_PATH).read_text(encoding="utf-8")',
            '    if "from .receipts import" not in cli_source or "from .capabilities import" not in cli_source:',
            '        raise DiscoveryError("current CLI import graph drift; review public runtime mapping")',
        ]
    )
    text = replace_function(
        text,
        "validate_current_cli_import_boundary",
        "validate_capability_map",
        cli_fn,
    )

    text = text.replace('"license": project["license"]["text"],', '"license": project["license"],')
    text = text.replace('"dependencies": 1,', '"dependencies": 0,')
    text = text.replace('"externalPythonPackages": ["Pillow"],', '"externalPythonPackages": [],')
    text = text.replace(
        '"currentCliImportBoundary": "Pillow-required-on-v0.10-main",',
        '"currentCliImportBoundary": "dependency-free-core-lazy-optional-media-v0.16",',
    )
    text = text.replace(
        '"current_cli_external_python_boundary": ["Pillow"],',
        '"current_cli_external_python_boundary": [],',
    )
    gen.write_text(text, encoding="utf-8")

    tests = Path("tests/test_public_capability_discovery.py")
    text = tests.read_text(encoding="utf-8")
    text = text.replace('record["runtime"]["dependencies"], 1', 'record["runtime"]["dependencies"], 0')
    text = text.replace(
        'record["runtime"]["externalPythonPackages"], ["Pillow"]',
        'record["runtime"]["externalPythonPackages"], []',
    )
    text = text.replace(
        '"Pillow-required-on-v0.10-main"',
        '"dependency-free-core-lazy-optional-media-v0.16"',
    )
    text = text.replace(
        'receipt["truth_boundary"]["current_cli_external_python_boundary"], ["Pillow"]',
        'receipt["truth_boundary"]["current_cli_external_python_boundary"], []',
    )
    text = text.replace('version = "0.10.0"', 'version = "0.16.0"')
    tests.write_text(text, encoding="utf-8")

    workflow = Path(".github/workflows/public-capability-discovery.yml")
    text = workflow.read_text(encoding="utf-8")
    text = text.replace(
        "      - name: Install the current v0.10 CLI Pillow compatibility boundary\n        run: python -m pip install Pillow==12.3.0\n",
        "",
    )
    text = text.replace("axm.framestate.capability-map/v0.10", "axm.framestate.capability-map/v0.16")
    text = text.replace("assert registry['runtime']['dependencies'] == 1", "assert registry['runtime']['dependencies'] == 0")
    text = text.replace(
        "assert registry['runtime']['externalPythonPackages'] == ['Pillow']",
        "assert registry['runtime']['externalPythonPackages'] == []",
    )
    text = text.replace(
        "'currentCliImportBoundary': 'Pillow-required-on-v0.10-main'",
        "'currentCliImportBoundary': 'dependency-free-core-lazy-optional-media-v0.16'",
    )
    text = text.replace(
        "'source_registry_cli_boundary': registry['runtime']['externalPythonPackages']",
        "'source_registry_cli_boundary': registry['contracts']['currentCliImportBoundary']",
    )
    workflow.write_text(text, encoding="utf-8")

    doc = Path("DISCOVERY.md")
    text = doc.read_text(encoding="utf-8")
    replacement = "\n".join(
        [
            "## Current v0.16 CLI import boundary",
            "",
            "The growth merge changed this truth materially. FrameState v0.16 still declares zero mandatory Python package dependencies, and the core installed CLI now loads and exposes `framestate capabilities` without Pillow installed. Pillow remains a **lazy optional compatibility boundary** for non-native imported image/font formats; it is not a core CLI dependency.",
            "",
            "The regenerated public declaration therefore states:",
            "",
            "- `declaredPackageDependencies: 0`;",
            "- `dependencies: 0` and `externalPythonPackages: []` for the core discovery/CLI boundary;",
            "- `currentCliImportBoundary: dependency-free-core-lazy-optional-media-v0.16`.",
            "",
            "This does not erase external per-capability boundaries. The capability map still names FFmpeg, optional Pillow/FreeType, legacy eSpeak, imported media and other boundaries where they actually apply. Public discovery points to that finer-grained map instead of flattening optional compatibility into a fake mandatory dependency.",
            "",
            "The discovery generator also anchors the newly merged growth capabilities: strict canonical JSON admission, media-output confinement, Forge single-writer publication, render checkpoint integrity, the renderer-neutral visual-state bridge, the EchoWorld replay visual bridge, and caller-pinned render-output verification. If those source-backed capability rows or runtime boundaries drift, regeneration fails closed.",
            "",
            "`network: false`, `account: false`, and `aiModel: false` mean the declared core FrameState machine requires none of those services to expose its deterministic local contracts. They do not claim that caller-selected external codecs/assets are intrinsically offline.",
            "",
            "## Discovery Buddy bridge",
        ]
    )
    text, count = re.subn(
        r"## Current v0\.10 CLI import boundary.*?## Discovery Buddy bridge",
        replacement,
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise SystemExit("DISCOVERY dependency-boundary section drift")
    doc.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
