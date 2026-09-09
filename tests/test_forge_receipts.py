from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import digest
from axm_framestate.forge import ForgeError, adopt_effect, adopt_recipe, spawn_effect, spawn_recipe


ROOT = Path(__file__).resolve().parents[1]


class ForgeReceiptIntegrityTests(unittest.TestCase):
    def _spawn(self, temporary: Path, example: str, spawn):
        raw = json.loads((ROOT / "examples" / example).read_text(encoding="utf-8"))
        source = temporary / "candidate.json"
        source.write_text(json.dumps(raw), encoding="utf-8")
        spawned = spawn(source, temporary / "spawned")
        return raw, spawned, Path(spawned["path"])

    def _machine(self, temporary: Path) -> Path:
        machine = temporary / "machine"
        machine.mkdir()
        (machine / "seed.txt").write_text("seed", encoding="utf-8")
        return machine

    def test_effect_adoption_rejects_self_consistent_receipt_without_spawn_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            raw, spawned, candidate = self._spawn(temporary, "posterize.effect.json", spawn_effect)
            forged = {"manifest_digest": spawned["manifest_digest"]}
            forged["receipt_digest"] = digest(forged)
            (candidate / "spawn-receipt.json").write_text(json.dumps(forged), encoding="utf-8")
            machine = self._machine(temporary)

            with self.assertRaisesRegex(ForgeError, "receipt schema mismatch"):
                adopt_effect(machine, candidate, "forged receipt probe", raw["root_fit"])

            self.assertFalse((machine / "effect-organs").exists())
            self.assertFalse((temporary / "axm-framestate-snapshots").exists())

    def test_effect_adoption_rejects_forged_receipt_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            raw, _, candidate = self._spawn(temporary, "posterize.effect.json", spawn_effect)
            receipt_path = candidate / "spawn-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["receipt_digest"] = "sha256:forged"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            machine = self._machine(temporary)

            with self.assertRaisesRegex(ForgeError, "receipt digest mismatch"):
                adopt_effect(machine, candidate, "forged digest probe", raw["root_fit"])

            self.assertFalse((machine / "effect-organs").exists())
            self.assertFalse((temporary / "axm-framestate-snapshots").exists())

    def test_recipe_adoption_rejects_resealed_false_replay_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            raw, _, candidate = self._spawn(temporary, "lower_third.recipe.json", spawn_recipe)
            receipt_path = candidate / "spawn-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["test"]["passed"] = False
            receipt.pop("receipt_digest")
            receipt["receipt_digest"] = digest(receipt)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            machine = self._machine(temporary)

            with self.assertRaisesRegex(ForgeError, "test evidence does not match current replay"):
                adopt_recipe(machine, candidate, "forged replay probe", raw["root_fit"])

            self.assertFalse((machine / "recipe-organs").exists())
            self.assertFalse((temporary / "axm-framestate-snapshots").exists())

    def test_effect_adoption_accepts_untouched_spawn_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            raw, _, candidate = self._spawn(temporary, "posterize.effect.json", spawn_effect)
            result = adopt_effect(self._machine(temporary), candidate, "valid receipt", raw["root_fit"])
            self.assertTrue(result["adopted"])

    def test_recipe_adoption_accepts_untouched_spawn_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            raw, _, candidate = self._spawn(temporary, "lower_third.recipe.json", spawn_recipe)
            result = adopt_recipe(self._machine(temporary), candidate, "valid receipt", raw["root_fit"])
            self.assertTrue(result["adopted"])


if __name__ == "__main__":
    unittest.main()
