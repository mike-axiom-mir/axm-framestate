from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest

RECIPE_SCHEMA = "axm.framestate.shot-recipe/v0.1"
PARAM_TYPES = {"text", "integer", "boolean", "color", "media_id"}
_REF_RE = re.compile(r"^[A-Za-z0-9._-]+@[0-9]+\.[0-9]+\.[0-9]+$")
_TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_.-]+)\}\}")


class RecipeError(ValueError):
    pass


def _text(value: Any, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecipeError(f"{label} must be non-empty text")
    if len(value) > maximum:
        raise RecipeError(f"{label} exceeds {maximum} characters")
    return value


def _param_definition(name: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RecipeError(f"parameter {name} must be object")
    if set(raw) - {"type", "required", "default"}:
        raise RecipeError(f"parameter {name} has unknown fields")
    kind = raw.get("type")
    if kind not in PARAM_TYPES:
        raise RecipeError(f"parameter {name} type unsupported")
    required = bool(raw.get("required", "default" not in raw))
    out = {"type": kind, "required": required}
    if "default" in raw:
        out["default"] = _validate_param_value(name, kind, raw["default"])
    return out


def _validate_param_value(name: str, kind: str, value: Any) -> Any:
    if kind in {"text", "media_id"}:
        if not isinstance(value, str):
            raise RecipeError(f"parameter {name} must be text")
        return value
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise RecipeError(f"parameter {name} must be integer")
        return value
    if kind == "boolean":
        if not isinstance(value, bool):
            raise RecipeError(f"parameter {name} must be boolean")
        return value
    if kind == "color":
        if not isinstance(value, list) or len(value) != 3 or not all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 255 for x in value):
            raise RecipeError(f"parameter {name} must be [r,g,b]")
        return list(value)
    raise RecipeError(f"parameter {name} type unsupported")


def normalize_recipe(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RecipeError("recipe must be object")
    allowed = {"schema", "id", "version", "purpose", "parameters", "shot_template", "fixtures", "root_fit", "metadata"}
    if set(raw) - allowed:
        raise RecipeError(f"recipe has unknown fields: {sorted(set(raw) - allowed)}")
    if raw.get("schema") != RECIPE_SCHEMA:
        raise RecipeError("unsupported recipe schema")
    rid = _text(raw.get("id"), "id", 200)
    version = _text(raw.get("version"), "version", 40)
    ref = f"{rid}@{version}"
    if not _REF_RE.match(ref):
        raise RecipeError("recipe id/version do not form a stable ref")
    purpose = _text(raw.get("purpose"), "purpose", 1000)
    params_raw = raw.get("parameters", {})
    if not isinstance(params_raw, dict):
        raise RecipeError("parameters must be object")
    parameters = {name: _param_definition(name, spec) for name, spec in sorted(params_raw.items())}
    template = raw.get("shot_template")
    if not isinstance(template, dict):
        raise RecipeError("shot_template must be object")
    fixtures = raw.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise RecipeError("fixtures must be non-empty list")
    normalized_fixtures = []
    for i, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict) or set(fixture) - {"name", "values"}:
            raise RecipeError(f"fixtures[{i}] invalid")
        name = _text(fixture.get("name"), f"fixtures[{i}].name", 200)
        values = fixture.get("values", {})
        if not isinstance(values, dict):
            raise RecipeError(f"fixtures[{i}].values must be object")
        normalized_fixtures.append({"name": name, "values": _resolve_values(parameters, values)})
    root_fit = raw.get("root_fit")
    if not isinstance(root_fit, dict):
        raise RecipeError("root_fit must be inspectable object")
    metadata = raw.get("metadata", {}) or {}
    if not isinstance(metadata, dict):
        raise RecipeError("metadata must be object")
    return {
        "schema": RECIPE_SCHEMA,
        "id": rid,
        "version": version,
        "ref": ref,
        "purpose": purpose,
        "parameters": parameters,
        "shot_template": copy.deepcopy(template),
        "fixtures": normalized_fixtures,
        "root_fit": copy.deepcopy(root_fit),
        "metadata": copy.deepcopy(metadata),
    }


def _resolve_values(parameters: dict[str, Any], supplied: dict[str, Any]) -> dict[str, Any]:
    unknown = set(supplied) - set(parameters)
    if unknown:
        raise RecipeError(f"unknown recipe values: {sorted(unknown)}")
    out: dict[str, Any] = {}
    for name, spec in parameters.items():
        if name in supplied:
            value = supplied[name]
        elif "default" in spec:
            value = spec["default"]
        elif spec["required"]:
            raise RecipeError(f"missing required recipe value: {name}")
        else:
            continue
        out[name] = _validate_param_value(name, spec["type"], value)
    return out


def _substitute(value: Any, values: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$param"}:
            name = value["$param"]
            if name not in values:
                raise RecipeError(f"template references missing value: {name}")
            return copy.deepcopy(values[name])
        return {k: _substitute(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, values) for v in value]
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in values:
                raise RecipeError(f"template references missing value: {name}")
            return str(values[name])
        return _TOKEN_RE.sub(repl, value)
    return copy.deepcopy(value)


def instantiate_recipe(recipe: dict[str, Any], supplied: dict[str, Any]) -> dict[str, Any]:
    manifest = normalize_recipe({k: v for k, v in recipe.items() if k != "ref"}) if recipe.get("ref") else normalize_recipe(recipe)
    values = _resolve_values(manifest["parameters"], supplied)
    shot = _substitute(manifest["shot_template"], values)
    if not isinstance(shot, dict):
        raise RecipeError("recipe did not produce shot object")
    shot.setdefault("id", manifest["id"])
    shot.setdefault("label", manifest["purpose"])
    return shot


def test_recipe_manifest(recipe: dict[str, Any]) -> dict[str, Any]:
    manifest = normalize_recipe({k: v for k, v in recipe.items() if k != "ref"}) if recipe.get("ref") else normalize_recipe(recipe)
    observations = []
    passed = True
    for fixture in manifest["fixtures"]:
        try:
            first = instantiate_recipe(manifest, fixture["values"])
            second = instantiate_recipe(manifest, fixture["values"])
            same = canonical_json(first) == canonical_json(second)
            from .director import compile_plan
            plan = {
                "schema": "axm.framestate.shot-plan/v0.2",
                "id": f"recipe-test-{manifest['id']}",
                "title": "Recipe fixture",
                "canvas": {"width": 96, "height": 64, "fps": 12},
                "background": [0, 0, 0],
                "media": [],
                "effects": [],
                "shots": [first],
                "metadata": {},
            }
            project = compile_plan(plan)
            row = {"name": fixture["name"], "passed": bool(same), "shot_digest": digest(first), "project_digest": digest(project)}
        except Exception as exc:
            row = {"name": fixture.get("name", "fixture"), "passed": False, "error": str(exc)}
        observations.append(row)
        passed = passed and row["passed"]
    return {
        "passed": bool(passed),
        "ref": manifest["ref"],
        "fixtures": observations,
        "truth_boundary": "fixture replay proves deterministic template materialization and current project validation; it does not prove artistic quality or universal suitability",
    }


def load_recipe_library(root: Path) -> dict[str, dict[str, Any]]:
    root = Path(root).resolve()
    library: dict[str, dict[str, Any]] = {}
    folder = root / "recipe-organs"
    if not folder.is_dir():
        return library
    for path in sorted(folder.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            manifest = normalize_recipe(raw)
            library[manifest["ref"]] = manifest
        except Exception:
            continue
    return library
