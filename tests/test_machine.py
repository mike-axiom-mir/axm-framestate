from __future__ import annotations

import json
import tempfile
import unittest
import shutil
import subprocess
import sys
from pathlib import Path

from axm_framestate.canonical import load_project, normalize_project, ProjectError
from axm_framestate.effects import normalize_effect, test_effect_manifest
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.review import review_project
from axm_framestate.forge import adopt_effect, spawn_effect
from axm_framestate.receipts import verify_repeat, render_with_receipt
from axm_framestate.director import compile_plan
from axm_framestate.shots import derive_shots, build_storyboard
from axm_framestate.queue import run_queue
from axm_framestate.three_d import sincos_mdeg

ROOT = Path(__file__).resolve().parents[1]


class FrameStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "examples" / "make_demo_media.py")], check=True, capture_output=True)
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
        self.assertEqual(result["smallest_visible_gaps"], ["imaginary-capability"])

    def test_mechanical_review_has_truth_boundary(self):
        project = load_project(ROOT / "examples" / "first_light.json")
        result = review_project(project, ROOT)
        self.assertIn("does not score", result["truth_boundary"])

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg unavailable")
    def test_v02_mixed_media_render(self):
        project = load_project(ROOT / "examples" / "mixed_media.json")
        with tempfile.TemporaryDirectory() as td:
            result = render_with_receipt(project, Path(td), ROOT, assemble=False)
            self.assertEqual(result["caption_manifest"]["cue_count"], 2)
            self.assertTrue(result["audio_manifest"]["source_evidence"])
            manifest = json.loads((Path(td) / "frame-manifest.json").read_text())
            self.assertEqual(len(manifest["media_conform"]["assets"]), 2)
            self.assertTrue((Path(td) / "captions.vtt").is_file())

    def test_v02_keyframe_track_and_text(self):
        project = load_project(ROOT / "examples" / "mixed_media.json")
        self.assertIn("keyframes", project["camera"]["zoom_milli"])
        self.assertEqual(next(x for x in project["layers"] if x["kind"] == "text")["text"], "FRAMESTATE V0.2")

    def test_fixed_point_cordic_axes(self):
        s0, c0 = sincos_mdeg(0)
        s90, c90 = sincos_mdeg(90000)
        self.assertLess(abs(s0), 20)
        self.assertGreater(c0, 999000)
        self.assertGreater(s90, 999000)
        self.assertLess(abs(c90), 20)

    def test_cube_and_obj_mesh_render(self):
        for name in ("cube_cinematic.json", "mesh_cinematic.json"):
            project = load_project(ROOT / "examples" / name)
            with tempfile.TemporaryDirectory() as td:
                result = render_with_receipt(project, Path(td), ROOT, assemble=False)
                self.assertEqual(result["project_digest"], result["project_digest"])
                manifest = json.loads((Path(td) / "frame-manifest.json").read_text())
                self.assertTrue(manifest["states"][5]["visible_layers"])

    def test_shot_plan_compile_and_storyboard(self):
        raw = json.loads((ROOT / "examples" / "three_shot.plan.json").read_text())
        project = compile_plan(raw)
        self.assertEqual(project["duration_frames"], 60)
        self.assertEqual(len(derive_shots(project)), 3)
        with tempfile.TemporaryDirectory() as td:
            board = build_storyboard(project, Path(td), ROOT, thumb_width=64)
            self.assertEqual(len(board["shots"]), 3)
            self.assertTrue(Path(board["storyboard"]["path"]).is_file())

    def test_render_queue(self):
        with tempfile.TemporaryDirectory() as td:
            q = Path(td) / "q.json"
            q.write_text(json.dumps({"jobs":[{"id":"a","project":str(ROOT / "examples" / "first_light.json"),"output":str(Path(td)/"out"),"assemble":False}]}))
            result = run_queue(q, ROOT)
            self.assertTrue(result["passed"])

    @unittest.skipUnless(shutil.which("espeak") or shutil.which("espeak-ng"), "speech synthesizer unavailable")
    def test_speech_event_is_receipted(self):
        project = load_project(ROOT / "examples" / "narrated_motion.json")
        with tempfile.TemporaryDirectory() as td:
            result = render_with_receipt(project, Path(td), ROOT, assemble=False)
            speech = next(x for x in result["audio_manifest"]["source_evidence"] if x["kind"] == "speech")
            self.assertIn("synthesizer", speech)
            self.assertTrue(speech["decoded_pcm_digest"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
