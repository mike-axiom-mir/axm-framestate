from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import normalize_project
from axm_framestate.realization import plan_realization
from axm_framestate.render import render_project
from axm_framestate.resumable import ResumeError, compare_resumable_to_reference, render_frames_resumable
from axm_framestate.studio import default_project


def small_project():
    p = default_project()
    p["canvas"] = {"width": 48, "height": 32, "fps": 12}
    p["duration_frames"] = 6
    p["layers"] = [{"id": "box", "kind": "rect", "z": 0, "x": 24, "y": 16, "w": 16, "h": 10, "color": [180, 90, 40], "start_frame": 0, "end_frame": 6}]
    p["captions"] = []
    p["audio"] = []
    p["effects"] = []
    return normalize_project(p)


class ResumableRenderTests(unittest.TestCase):
    def test_interrupted_then_resumed_manifest_matches_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = compare_resumable_to_reference(small_project(), root, root)
            self.assertTrue(result["passed"], result)

    def test_project_drift_refuses_old_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = small_project()
            out = root / "out"
            paused = render_frames_resumable(project, out, root, checkpoint_interval=1, max_new_frames=2)
            self.assertEqual(paused["status"], "PAUSED")
            changed = small_project()
            changed["background"] = [1, 2, 3]
            with self.assertRaises(ResumeError):
                render_frames_resumable(changed, out, root)

    def test_corrupt_checkpointed_frame_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = small_project()
            out = root / "out"
            render_frames_resumable(project, out, root, checkpoint_interval=1, max_new_frames=2)
            (out / "frames" / "frame-000000.ppm").write_bytes(b"corrupt")
            with self.assertRaises(ResumeError):
                render_frames_resumable(project, out, root)

    def test_tampered_checkpoint_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = small_project()
            out = root / "out"
            render_frames_resumable(project, out, root, checkpoint_interval=1, max_new_frames=2)
            checkpoint_path = out / "render-checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint["completed"][0]["state"]["forged"] = "accepted"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            tampered_bytes = checkpoint_path.read_bytes()
            with self.assertRaisesRegex(ResumeError, "checkpoint digest"):
                render_frames_resumable(project, out, root)
            self.assertEqual(checkpoint_path.read_bytes(), tampered_bytes)

    def test_unadmitted_tail_is_discarded_and_rerendered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = small_project()
            out = root / "out"
            render_frames_resumable(project, out, root, checkpoint_interval=1, max_new_frames=2)
            tail = out / "frames" / "frame-000002.ppm"
            tail.write_bytes(b"unadmitted")
            result = render_frames_resumable(project, out, root, checkpoint_interval=2)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["removed_unadmitted_frames_on_resume"], 1)
            self.assertNotEqual(tail.read_bytes(), b"unadmitted")

    def test_realized_resume_matches_same_contract_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = small_project()
            machine = {
                "schema": "axm.framestate.machine-capabilities/v0.1",
                "id": "test-machine",
                "logical_cores": 8,
                "memory_mb": 8192,
                "ffmpeg_available": False,
                "espeak_available": False,
                "pillow_available": False,
                "render_backends": ["cpu-software"],
                "platform": "test",
            }
            contract = plan_realization(project, machine, {"mode": "adaptive"})
            reference = render_project(project, root / "reference", root, realization=contract)
            out = root / "resumed"
            render_frames_resumable(project, out, root, realization=contract, checkpoint_interval=1, max_new_frames=3)
            result = render_frames_resumable(project, out, root, realization=contract, checkpoint_interval=2)
            resumed = json.loads((out / "frame-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(reference, resumed)


if __name__ == "__main__":
    unittest.main()
