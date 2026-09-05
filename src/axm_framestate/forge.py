from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest
from .effects import normalize_effect, test_effect_manifest
from .roots import evaluate_root_fit
from .snapshot import create_daily_snapshot


class ForgeError(RuntimeError):
    pass


def spawn_effect(candidate_file: Path, output_dir: Path) -> dict[str, Any]:
    raw = json.loads(Path(candidate_file).read_text(encoding="utf-8"))
    manifest = normalize_effect(raw)
    target = Path(output_dir) / manifest["ref"].replace(":", "_").replace("@", "-")
    if target.exists():
        raise ForgeError("detached candidate destination already exists")
    target.mkdir(parents=True)
    (target / "effect.json").write_bytes(canonical_json({k: v for k, v in manifest.items() if k != "ref"}) + b"\n")
    test = test_effect_manifest(manifest)
    receipt = {
        "schema": "axm.framestate.spawn-receipt/v0.1",
        "ref": manifest["ref"],
        "manifest_digest": digest(manifest),
        "detached": True,
        "installed": False,
        "test": test,
    }
    receipt["receipt_digest"] = digest(receipt)
    (target / "spawn-receipt.json").write_bytes(canonical_json(receipt) + b"\n")
    return {"path": str(target), **receipt}


def inspect_spawned(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = json.loads((Path(path) / "effect.json").read_text(encoding="utf-8"))
    manifest = normalize_effect(raw)
    receipt = json.loads((Path(path) / "spawn-receipt.json").read_text(encoding="utf-8"))
    if receipt.get("manifest_digest") != digest(manifest):
        raise ForgeError("candidate manifest drift detected")
    return manifest, receipt


def adopt_effect(root: Path, candidate_dir: Path, reason: str, root_fit: Any, *, day: dt.date | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    manifest, receipt = inspect_spawned(candidate_dir)
    current_test = test_effect_manifest(manifest)
    if current_test.get("passed") is not True:
        return {"adopted": False, "truth_status": "HOLD_CANDIDATE_TESTS_FAILED", "test": current_test}
    declared = evaluate_root_fit(manifest.get("root_fit"))
    adoption = evaluate_root_fit(root_fit)
    if declared.get("fit") is not True or adoption.get("fit") is not True:
        return {"adopted": False, "truth_status": "HOLD_ROOT_FIT", "candidate_root_fit": declared, "adoption_root_fit": adoption}
    destination = root / "effect-organs" / f"{manifest['id']}-{manifest['version']}.json"
    if destination.exists():
        return {"adopted": False, "truth_status": "HOLD_REF_COLLISION", "destination": str(destination)}
    recovery = create_daily_snapshot(root, day=day)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = Path(candidate_dir) / "effect.json"
    shutil.copyfile(source, destination)
    installed = normalize_effect(json.loads(destination.read_text(encoding="utf-8")))
    if installed["ref"] != manifest["ref"] or digest(installed) != digest(manifest):
        destination.unlink(missing_ok=True)
        raise ForgeError("installed effect differs from tested candidate")
    return {
        "adopted": True,
        "truth_status": "ADOPTED_LIVE_EFFECT_ORGAN",
        "ref": manifest["ref"],
        "reason": reason,
        "candidate_receipt_digest": receipt.get("receipt_digest"),
        "test": current_test,
        "candidate_root_fit": declared,
        "adoption_root_fit": adoption,
        "recovery_snapshot": recovery,
        "destination": str(destination),
        "authority_change": {"installed": True, "registered": True, "canon_changed": False, "permissions_changed": False},
    }
