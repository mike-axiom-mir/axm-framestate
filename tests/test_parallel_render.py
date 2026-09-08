from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import normalize_project
from axm_framestate.parallel_render import ParallelRenderError, render_project_parallel
from axm_framestate.render import render_project


def project_fixture():
    return normalize_project({
        "schema": "axm.framestate.project/v0.5",
        "id": "parallel-proof",
        "title": "Parallel proof",
        "canvas": {"width": 80, "height": 48, "fps": 12},
        "duration_frames": 8,
        "background": [6, 8, 14],
        "camera": {"x": 0, "y": 0, "zoom_milli": 1000},
        "media": [],
        "layers": [
            {"id": "box", "kind": "rect", "z": 1, "x": {"from": 18, "to": 62}, "y": 24, "w": 20, "h": 12, "color": [220, 100, 55], "start_frame": 0, "end_frame": 8},
            {"id": "orb", "kind": "circle", "z": 2, "x": 40, "y": {"from": 12, "to": 36}, "radius": 7, "color": [80, 180, 240], "start_frame": 0, "end_frame": 8},
        ],
        "captions": [], "audio": [], "effects": [], "markers": [], "metadata": {},
    })


class ParallelRenderTests(unittest.TestCase):
    def test_parallel_backend_matches_sequential_manifest_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = project_fixture()
            sequential = render_project(project, root / "sequential", root)
            parallel = render_project_parallel(project, root / "parallel", root, max_workers=2)
            self.assertEqual(sequential, parallel)
            receipt = json.loads((root / "parallel" / "parallel-execution.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["backend"], "cpu-parallel")
            self.assertEqual(receipt["worker_count"], 2)
            self.assertEqual(receipt["frame_manifest_digest"], parallel["manifest_digest"])
            self.assertEqual(sum(row["frame_count"] for row in receipt["chunks"]), project["duration_frames"])

    def test_parallel_backend_rejects_single_worker_false_acceleration(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ParallelRenderError):
                render_project_parallel(project_fixture(), Path(td) / "out", Path(td), max_workers=1)


if __name__ == "__main__":
    unittest.main()
