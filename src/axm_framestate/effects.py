from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .canonical import canonical_json, digest

EFFECT_SCHEMA = "axm.framestate.effect-organ/v0.1"
PixelFn = Callable[[int, int, int, int, int], tuple[int, int, int]]


class EffectError(ValueError):
    pass


PROGRAM_OPS = {"+", "-", "*", "/", "min", "max", "abs", "neg", "clamp255"}
PROGRAM_VARS = {"r", "g", "b", "x", "y"}


def _validate_program(program: Any, label: str) -> list[Any]:
    if not isinstance(program, list) or not program or len(program) > 64:
        raise EffectError(f"{label} must be a non-empty token array of at most 64 tokens")
    for token in program:
        if isinstance(token, bool):
            raise EffectError(f"{label} boolean token is invalid")
        if isinstance(token, int):
            if token < -1_000_000 or token > 1_000_000:
                raise EffectError(f"{label} integer token out of bounds")
            continue
        if isinstance(token, str) and (token in PROGRAM_OPS or token in PROGRAM_VARS):
            continue
        raise EffectError(f"{label} unsupported token: {token!r}")
    # Static stack-depth proof.
    depth = 0
    for token in program:
        if isinstance(token, int) or token in PROGRAM_VARS:
            depth += 1
        elif token in {"abs", "neg", "clamp255"}:
            if depth < 1:
                raise EffectError(f"{label} stack underflow")
        else:
            if depth < 2:
                raise EffectError(f"{label} stack underflow")
            depth -= 1
    if depth != 1:
        raise EffectError(f"{label} must leave exactly one value on the stack")
    return list(program)


def _run_program(program: list[Any], env: dict[str, int]) -> int:
    stack: list[int] = []
    for token in program:
        if isinstance(token, int):
            stack.append(token)
        elif token in PROGRAM_VARS:
            stack.append(int(env[token]))
        elif token in {"abs", "neg", "clamp255"}:
            a = stack.pop()
            if token == "abs":
                stack.append(abs(a))
            elif token == "neg":
                stack.append(-a)
            else:
                stack.append(max(0, min(255, a)))
        else:
            b = stack.pop()
            a = stack.pop()
            if token == "+":
                stack.append(a + b)
            elif token == "-":
                stack.append(a - b)
            elif token == "*":
                stack.append(a * b)
            elif token == "/":
                stack.append(0 if b == 0 else a // b)
            elif token == "min":
                stack.append(min(a, b))
            elif token == "max":
                stack.append(max(a, b))
    return max(0, min(255, stack[0]))


@dataclass(frozen=True)
class EffectOrgan:
    ref: str
    kind: str
    params: dict[str, Any]
    source: str

    def apply(self, r: int, g: int, b: int, x: int, y: int) -> tuple[int, int, int]:
        if self.kind == "identity":
            return r, g, b
        if self.kind == "grayscale":
            v = (299 * r + 587 * g + 114 * b) // 1000
            return v, v, v
        if self.kind == "posterize":
            levels = int(self.params.get("levels", 4))
            levels = max(2, min(32, levels))
            step = 255 // (levels - 1)
            def q(v: int) -> int:
                return min(255, ((v + step // 2) // step) * step)
            return q(r), q(g), q(b)
        if self.kind == "scanline":
            every = max(2, int(self.params.get("every", 4)))
            strength = max(0, min(1000, int(self.params.get("strength_milli", 250))))
            if y % every == 0:
                keep = 1000 - strength
                return r * keep // 1000, g * keep // 1000, b * keep // 1000
            return r, g, b
        if self.kind == "channel-shift":
            # Pixel-local variant: deterministic channel rotation rather than spatial sampling.
            mode = self.params.get("mode", "rgb-to-gbr")
            if mode == "rgb-to-gbr":
                return g, b, r
            if mode == "rgb-to-brg":
                return b, r, g
            raise EffectError("unsupported channel-shift mode")
        if self.kind == "pixel-program":
            channels = self.params.get("channels", {})
            env = {"r": r, "g": g, "b": b, "x": x, "y": y}
            return tuple(_run_program(channels[name], env) for name in ("r", "g", "b"))
        raise EffectError(f"unsupported effect kind: {self.kind}")


def builtin_effects() -> dict[str, EffectOrgan]:
    return {
        "builtin:identity@1": EffectOrgan("builtin:identity@1", "identity", {}, "builtin"),
        "builtin:grayscale@1": EffectOrgan("builtin:grayscale@1", "grayscale", {}, "builtin"),
        "builtin:scanline@1": EffectOrgan("builtin:scanline@1", "scanline", {"every": 4, "strength_milli": 220}, "builtin"),
    }


def normalize_effect(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EffectError("effect organ must be an object")
    allowed = {"schema", "id", "version", "kind", "params", "fixtures", "root_fit", "provenance", "limitations"}
    extra = set(raw) - allowed
    if extra:
        raise EffectError(f"unknown effect fields: {sorted(extra)}")
    if raw.get("schema") != EFFECT_SCHEMA:
        raise EffectError(f"schema must be {EFFECT_SCHEMA}")
    effect_id = raw.get("id")
    version = raw.get("version")
    kind = raw.get("kind")
    if not isinstance(effect_id, str) or not effect_id.strip():
        raise EffectError("id must be non-empty text")
    if not isinstance(version, str) or not version.strip():
        raise EffectError("version must be non-empty text")
    if kind not in {"identity", "grayscale", "posterize", "scanline", "channel-shift", "pixel-program"}:
        raise EffectError("unsupported effect kind")
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise EffectError("params must be an object")
    if kind == "pixel-program":
        if set(params) != {"channels"} or not isinstance(params.get("channels"), dict) or set(params["channels"]) != {"r", "g", "b"}:
            raise EffectError("pixel-program params must contain exactly channels.r/g/b")
        params = {"channels": {name: _validate_program(params["channels"][name], f"params.channels.{name}") for name in ("r", "g", "b")}}
    fixtures = raw.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise EffectError("fixtures must contain at least one pixel fixture")
    normalized_fixtures: list[dict[str, Any]] = []
    for i, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict) or set(fixture) != {"input", "xy", "expected"}:
            raise EffectError(f"fixtures[{i}] must have input, xy, expected")
        inp, xy, expected = fixture["input"], fixture["xy"], fixture["expected"]
        if not (isinstance(inp, list) and len(inp) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in inp)):
            raise EffectError(f"fixtures[{i}].input invalid")
        if not (isinstance(expected, list) and len(expected) == 3 and all(isinstance(v, int) and 0 <= v <= 255 for v in expected)):
            raise EffectError(f"fixtures[{i}].expected invalid")
        if not (isinstance(xy, list) and len(xy) == 2 and all(isinstance(v, int) for v in xy)):
            raise EffectError(f"fixtures[{i}].xy invalid")
        normalized_fixtures.append({"input": inp, "xy": xy, "expected": expected})
    return {
        "schema": EFFECT_SCHEMA,
        "id": effect_id.strip(),
        "version": version.strip(),
        "ref": f"{effect_id.strip()}@{version.strip()}",
        "kind": kind,
        "params": params,
        "fixtures": normalized_fixtures,
        "root_fit": raw.get("root_fit"),
        "provenance": raw.get("provenance", {}),
        "limitations": raw.get("limitations", []),
    }


def effect_from_manifest(manifest: dict[str, Any], source: str) -> EffectOrgan:
    return EffectOrgan(manifest["ref"], manifest["kind"], manifest["params"], source)


def load_effect_library(root: Path) -> dict[str, EffectOrgan]:
    library = builtin_effects()
    directory = Path(root) / "effect-organs"
    if not directory.exists():
        return library
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        normalized = normalize_effect(raw)
        ref = normalized["ref"]
        if ref in library:
            raise EffectError(f"duplicate effect ref: {ref}")
        library[ref] = effect_from_manifest(normalized, str(path))
    return library


def test_effect_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    organ = effect_from_manifest(manifest, "detached-candidate")
    observations = []
    passed = True
    for fixture in manifest["fixtures"]:
        actual = list(organ.apply(*fixture["input"], *fixture["xy"]))
        ok = actual == fixture["expected"]
        passed = passed and ok
        observations.append({"fixture": fixture, "actual": actual, "passed": ok})
    # Repeat the fixture pass exactly to prove candidate behavior is stable for known fixtures.
    replay = [list(organ.apply(*f["input"], *f["xy"])) for f in manifest["fixtures"]]
    replay_digest = digest(replay)
    return {
        "passed": passed and replay == [row["actual"] for row in observations],
        "manifest_digest": digest(manifest),
        "fixture_observations": observations,
        "replay_digest": replay_digest,
        "replay_identical": replay == [row["actual"] for row in observations],
    }
