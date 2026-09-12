from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import digest, load_project
from axm_framestate.studio import StudioApp, default_project, ppm_to_png


class StudioTests(unittest.TestCase):
    def test_default_project_is_canonical_v05(self):
        project = default_project()
        self.assertEqual(project["schema"], "axm.framestate.project/v0.5")
        self.assertEqual(project["canvas"]["width"], 640)
        self.assertTrue(project["layers"])

    def test_ppm_to_png_is_valid_png_container(self):
        ppm = b"P6\n2 1\n255\n" + bytes([255, 0, 0, 0, 255, 0])
        png = ppm_to_png(ppm)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn(b"IHDR", png)
        self.assertIn(b"IDAT", png)
        self.assertTrue(png.endswith(b"IEND\xaeB`\x82"))

    def test_preview_uses_native_renderer_and_returns_frame_state(self):
        with tempfile.TemporaryDirectory() as td:
            app = StudioApp(Path(td))
            project = default_project()
            project["canvas"] = {"width": 64, "height": 36, "fps": 12}
            project["duration_frames"] = 2
            project["layers"] = [{"id": "box", "kind": "rect", "z": 1, "x": 32, "y": 18, "w": 24, "h": 12, "color": [200, 80, 40], "start_frame": 0, "end_frame": 2}]
            result = app.preview(project, 0, "exact")
            normalized = app.normalize(project)["project"]
            self.assertEqual(result["frame_state"]["frame"], 0)
            self.assertEqual(result["project_digest"], digest(normalized))
            prefix = "data:image/png;base64,"
            self.assertTrue(result["image"].startswith(prefix))
            self.assertTrue(base64.b64decode(result["image"][len(prefix):]).startswith(b"\x89PNG"))

    def test_prompt_is_explicit_plan_then_candidate_state(self):
        with tempfile.TemporaryDirectory() as td:
            app = StudioApp(Path(td))
            project = default_project()
            result = app.apply_prompt(project, "cinematic and warmer colors")
            self.assertEqual(result["plan"]["status"], "ACTIONABLE")
            self.assertNotEqual(result["project_digest"], digest(project))
            self.assertTrue(result["applied_operations"])

    def test_save_is_canonical_and_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = StudioApp(root)
            project = default_project()
            project["title"] = "Saved from Studio"
            result = app.save(project)
            path = Path(result["path"])
            self.assertTrue(path.exists())
            restored = load_project(path)
            self.assertEqual(restored["title"], "Saved from Studio")
            self.assertEqual(result["project_digest"], digest(restored))
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw, restored)


if __name__ == "__main__":
    unittest.main()
