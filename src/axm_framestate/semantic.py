from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, file_digest, load_project, normalize_project

DIRECTION_SCHEMA = "axm.framestate.semantic-direction/v0.1"
REQUEST_SCHEMA = "axm.framestate.semantic-request/v0.1"
RESPONSE_SCHEMA = "axm.framestate.semantic-response/v0.1"
TRANSLATOR_CONFIG_SCHEMA = "axm.framestate.semantic-translator-command/v0.1"
RECEIPT_SCHEMA = "axm.framestate.semantic-receipt/v0.1"
_MAX_TRANSLATOR_OUTPUT = 16 * 1024 * 1024


class SemanticError(ValueError):
    pass


def normalize_direction(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) - {"schema", "id", "text", "metadata"}:
        raise SemanticError("semantic direction must contain only schema/id/text/metadata")
    if raw.get("schema") != DIRECTION_SCHEMA:
        raise SemanticError(f"direction schema must be {DIRECTION_SCHEMA}")
    did = raw.get("id")
    text = raw.get("text")
    if not isinstance(did, str) or not did.strip() or len(did) > 200:
        raise SemanticError("direction id must be 1..200 characters")
    if not isinstance(text, str) or not text.strip() or len(text) > 8000:
        raise SemanticError("direction text must be 1..8000 characters")
    metadata = raw.get("metadata", {}) or {}
    if not isinstance(metadata, dict):
        raise SemanticError("direction metadata must be an object")
    return {"schema": DIRECTION_SCHEMA, "id": did.strip(), "text": text.strip(), "metadata": metadata}


def semantic_request(project: dict[str, Any], direction: dict[str, Any]) -> dict[str, Any]:
    project = normalize_project(project)
    direction = normalize_direction(direction)
    request = {
        "schema": REQUEST_SCHEMA,
        "project": project,
        "project_digest": digest(project),
        "direction": direction,
        "direction_text_digest": digest(direction["text"]),
        "contract": {
            "output_schema": RESPONSE_SCHEMA,
            "candidate_must_be_canonicalizable": True,
            "proposal_has_no_automatic_write_authority": True,
        },
    }
    request["request_digest"] = digest(request)
    return request


def normalize_translator_config(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) - {"schema", "command", "timeout_seconds"}:
        raise SemanticError("translator config must contain only schema/command/timeout_seconds")
    if raw.get("schema") != TRANSLATOR_CONFIG_SCHEMA:
        raise SemanticError(f"translator config schema must be {TRANSLATOR_CONFIG_SCHEMA}")
    command = raw.get("command")
    if not isinstance(command, list) or not 1 <= len(command) <= 32 or not all(isinstance(v, str) and v and len(v) <= 4000 for v in command):
        raise SemanticError("translator command must be a non-empty text array with at most 32 items")
    timeout = raw.get("timeout_seconds", 120)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 900:
        raise SemanticError("translator timeout_seconds must be integer in 1..900")
    return {"schema": TRANSLATOR_CONFIG_SCHEMA, "command": list(command), "timeout_seconds": timeout}


def _translator_boundary(config: dict[str, Any]) -> dict[str, Any]:
    command = config["command"]
    executable = shutil.which(command[0])
    path = Path(executable).resolve() if executable else Path(command[0]).expanduser()
    boundary = {
        "mode": "external-command",
        "executable_name": Path(command[0]).name,
        "argument_count": max(0, len(command) - 1),
        "timeout_seconds": config["timeout_seconds"],
        "command_arguments_recorded": False,
        "reason_arguments_not_recorded": "arguments can contain private configuration or credentials",
    }
    if path.is_file():
        boundary["executable_digest"] = file_digest(path)
    else:
        boundary["executable_digest"] = None
    return boundary


def run_translator(request: dict[str, Any], config: dict[str, Any], machine_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = normalize_translator_config(config)
    boundary = _translator_boundary(config)
    try:
        proc = subprocess.run(
            config["command"],
            input=canonical_json(request) + b"\n",
            capture_output=True,
            check=False,
            timeout=config["timeout_seconds"],
            cwd=Path(machine_root),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SemanticError(f"semantic translator execution failed: {type(exc).__name__}") from exc
    boundary["returncode"] = proc.returncode
    boundary["stdout_digest"] = "sha256:" + hashlib.sha256(proc.stdout).hexdigest()
    boundary["stderr_digest"] = "sha256:" + hashlib.sha256(proc.stderr).hexdigest()
    boundary["stdout_bytes"] = len(proc.stdout)
    boundary["stderr_bytes"] = len(proc.stderr)
    if proc.returncode != 0:
        raise SemanticError(f"semantic translator returned exit code {proc.returncode}")
    if len(proc.stdout) > _MAX_TRANSLATOR_OUTPUT:
        raise SemanticError("semantic translator output exceeds 16 MiB boundary")
    try:
        raw = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticError("semantic translator must emit one UTF-8 JSON response") from exc
    return raw, boundary


def normalize_response(raw: Any, request: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema", "input_project_digest", "direction_text_digest", "translator",
        "candidate_project", "rationale", "assumptions", "metadata",
    }
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise SemanticError("semantic response contains unsupported fields")
    if raw.get("schema") != RESPONSE_SCHEMA:
        raise SemanticError(f"semantic response schema must be {RESPONSE_SCHEMA}")
    if raw.get("input_project_digest") != request["project_digest"]:
        raise SemanticError("semantic response input_project_digest does not match current project")
    if raw.get("direction_text_digest") != request["direction_text_digest"]:
        raise SemanticError("semantic response direction_text_digest does not match current direction")
    translator = raw.get("translator")
    if not isinstance(translator, dict) or set(translator) - {"id", "version", "implementation", "provider", "model"}:
        raise SemanticError("semantic response translator attribution is invalid")
    tid = translator.get("id")
    version = translator.get("version")
    implementation = translator.get("implementation")
    if not all(isinstance(v, str) and v.strip() and len(v) <= 500 for v in (tid, version, implementation)):
        raise SemanticError("translator id/version/implementation are required attribution")
    attr = {"id": tid.strip(), "version": version.strip(), "implementation": implementation.strip()}
    for key in ("provider", "model"):
        if key in translator and translator[key] is not None:
            if not isinstance(translator[key], str) or len(translator[key]) > 500:
                raise SemanticError(f"translator {key} must be text")
            attr[key] = translator[key]
    candidate = normalize_project(raw.get("candidate_project"))
    assumptions = raw.get("assumptions", []) or []
    if not isinstance(assumptions, list) or len(assumptions) > 100 or not all(isinstance(v, str) and len(v) <= 2000 for v in assumptions):
        raise SemanticError("semantic assumptions must be a bounded text array")
    rationale = raw.get("rationale", "") or ""
    if not isinstance(rationale, str) or len(rationale) > 10000:
        raise SemanticError("semantic rationale must be bounded text")
    metadata = raw.get("metadata", {}) or {}
    if not isinstance(metadata, dict):
        raise SemanticError("semantic response metadata must be an object")
    return {
        "schema": RESPONSE_SCHEMA,
        "input_project_digest": request["project_digest"],
        "direction_text_digest": request["direction_text_digest"],
        "translator": attr,
        "candidate_project": candidate,
        "rationale": rationale,
        "assumptions": assumptions,
        "metadata": metadata,
    }


def _changed_paths(before: Any, after: Any, path: str = "$", *, limit: int = 512) -> list[str]:
    rows: list[str] = []
    def walk(a: Any, b: Any, p: str) -> None:
        if len(rows) >= limit:
            return
        if type(a) is not type(b):
            rows.append(p)
            return
        if isinstance(a, dict):
            for key in sorted(set(a) | set(b)):
                child = f"{p}.{key}"
                if key not in a or key not in b:
                    rows.append(child)
                else:
                    walk(a[key], b[key], child)
                if len(rows) >= limit:
                    return
            return
        if isinstance(a, list):
            if len(a) != len(b):
                rows.append(f"{p}.length")
            for index, (av, bv) in enumerate(zip(a, b)):
                walk(av, bv, f"{p}[{index}]")
                if len(rows) >= limit:
                    return
            return
        if a != b:
            rows.append(p)
    walk(before, after, path)
    return rows


def stage_semantic_candidate(
    project: dict[str, Any],
    direction: dict[str, Any],
    output_dir: Path,
    machine_root: Path,
    *,
    translator_config: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    response_source_digest: str | None = None,
) -> dict[str, Any]:
    if (translator_config is None) == (response is None):
        raise SemanticError("provide exactly one translator_config or response")
    source = normalize_project(project)
    request = semantic_request(source, direction)
    boundary: dict[str, Any]
    if translator_config is not None:
        raw_response, boundary = run_translator(request, translator_config, machine_root)
    else:
        raw_response = response
        boundary = {"mode": "precomputed-response", "source_digest": response_source_digest}
    normalized = normalize_response(raw_response, request)
    candidate = normalized["candidate_project"]
    changed = _changed_paths(source, candidate)
    truncated = len(changed) >= 512
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "semantic-request.json").write_bytes(canonical_json(request) + b"\n")
    (out / "semantic-response.json").write_bytes(canonical_json(normalized) + b"\n")
    (out / "semantic-candidate-project.json").write_bytes(canonical_json(candidate) + b"\n")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "request_digest": request["request_digest"],
        "input_project_digest": request["project_digest"],
        "direction_text_digest": request["direction_text_digest"],
        "translator": normalized["translator"],
        "translator_boundary": boundary,
        "candidate_project_digest": digest(candidate),
        "candidate_changed": digest(candidate) != request["project_digest"],
        "changed_paths": changed,
        "changed_paths_truncated": truncated,
        "status": "STAGED_CHANGED" if digest(candidate) != request["project_digest"] else "STAGED_UNCHANGED",
        "automatic_canonical_write": False,
        "truth_boundary": "semantic interpretation is attributed proposal evidence, not canonical truth; FrameState validates and stages the candidate but does not overwrite the source project automatically",
    }
    receipt["receipt_digest"] = digest(receipt)
    (out / "semantic-receipt.json").write_bytes(canonical_json(receipt) + b"\n")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="framestate-semantic", description="Stage an attributed semantic candidate without granting it automatic project truth")
    parser.add_argument("project")
    parser.add_argument("direction")
    parser.add_argument("output")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--translator", help="semantic translator command config JSON")
    source.add_argument("--response", help="precomputed semantic response JSON")
    args = parser.parse_args(argv)
    project = load_project(Path(args.project))
    direction = json.loads(Path(args.direction).read_text(encoding="utf-8"))
    if args.translator:
        config = json.loads(Path(args.translator).read_text(encoding="utf-8"))
        receipt = stage_semantic_candidate(project, direction, Path(args.output), Path.cwd().resolve(), translator_config=config)
    else:
        response_path = Path(args.response)
        raw = json.loads(response_path.read_text(encoding="utf-8"))
        receipt = stage_semantic_candidate(project, direction, Path(args.output), Path.cwd().resolve(), response=raw, response_source_digest=file_digest(response_path))
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
