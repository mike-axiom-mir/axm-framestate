from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from axm_framestate.canonical import digest
from axm_framestate.forge import ForgeError, adopt_effect, adopt_recipe, spawn_effect, spawn_recipe
from axm_framestate.snapshot import create_daily_snapshot


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

    def test_concurrent_adoptions_publish_exactly_one_live_organ(self):
        cases = (
            ("posterize.effect.json", spawn_effect, adopt_effect, "effect-organs"),
            ("lower_third.recipe.json", spawn_recipe, adopt_recipe, "recipe-organs"),
        )
        for example, spawn, adopt, organ_directory in cases:
            with self.subTest(example=example), tempfile.TemporaryDirectory() as directory:
                temporary = Path(directory)
                raw, _, candidate = self._spawn(temporary, example, spawn)
                machine = self._machine(temporary)
                snapshot_barrier = threading.Barrier(2)

                def synchronized_snapshot(*args, **kwargs):
                    recovery = create_daily_snapshot(*args, **kwargs)
                    snapshot_barrier.wait(timeout=5)
                    return recovery

                def run_adoption(index: int):
                    return adopt(machine, candidate, f"concurrent adoption {index}", raw["root_fit"])

                with mock.patch("axm_framestate.forge.create_daily_snapshot", new=synchronized_snapshot):
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        results = list(executor.map(run_adoption, range(2)))

                adopted = [result for result in results if result["adopted"]]
                held = [result for result in results if result["truth_status"] == "HOLD_REF_COLLISION"]
                self.assertEqual(len(adopted), 1)
                self.assertEqual(len(held), 1)
                installed = list((machine / organ_directory).glob("*.json"))
                self.assertEqual(len(installed), 1)


if __name__ == "__main__":
    unittest.main()
