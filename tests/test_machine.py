from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import load_project, normalize_project, ProjectError
from axm_framestate.effects import normalize_effect, test_effect_manifest
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.review import review_project
from axm_framestate.forge import adopt_effect, spawn_effect
from axm_framestate.receipts import verify_repeat

ROOT = Path(__file__).resolve().parents[1]


class FrameStateTests(unittest.TestCase):
    def test_project_rejects_unknown_fields(self):
        raw = json.loads((ROOT / "examples" / "first_light.json").read_text())
        raw["mystery"] = True
        with self.assertRaises(ProjectError):
            normalize_project(raw)

    def test_repeat_render_is_exact(self):
        project = load_project(ROOT / "examples" / "first_light.json")
        with tempfile.TemporaryDirectory() as td:
            result = verify_repeat(project, Path(td), ROOT)
            self.assertTrue(result["passed"], result)

    def test_effect_fixture_replay(self):
        raw = json.loads((ROOT / "examples" / "posterize.effect.json").read_text())
        manifest = normalize_effect(raw)
        result = test_effect_manifest(manifest)
        self.assertTrue(result["passed"], result)

    def test_detached_effect_adoption_requires_root_fit_and_snapshot(self):
        raw = json.loads((ROOT / "examples" / "posterize.effect.json").read_text())
        root_fit = raw["root_fit"]
        with tempfile.TemporaryDirectory() as td:
            machine = Path(td) / "machine"
            machine.mkdir()
            (machine / "seed.txt").write_text("seed", encoding="utf-8")
            candidate_file = Path(td) / "candidate.json"
            candidate_file.write_text(json.dumps(raw), encoding="utf-8")
            spawned = spawn_effect(candidate_file, Path(td) / "spawned")
            result = adopt_effect(machine, Path(spawned["path"]), "test adoption", root_fit)
            self.assertTrue(result["adopted"], result)
            self.assertTrue(Path(result["destination"]).is_file())
            self.assertTrue(Path(result["recovery_snapshot"]["path"]).is_file())

    def test_pixel_program_effect(self):
        raw = json.loads((ROOT / "examples" / "signal_program.effect.json").read_text())
        result = test_effect_manifest(normalize_effect(raw))
        self.assertTrue(result["passed"], result)

    def test_gap_analysis_exposes_missing_capability(self):
        result = analyze_requirements(["camera-animation", "captions-subtitles", "imaginary-capability"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["smallest_visible_gaps"], ["captions-subtitles", "imaginary-capability"])

    def test_mechanical_review_has_truth_boundary(self):
        project = load_project(ROOT / "examples" / "first_light.json")
        result = review_project(project, ROOT)
        self.assertIn("does not score", result["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
