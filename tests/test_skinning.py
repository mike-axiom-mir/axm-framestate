from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import normalize_project
from axm_framestate.render import render_project
from axm_framestate.skinning import SkinningError, skin_vertices


def rig():
    return {
        "schema": "axm.framestate.skin-rig3d/v0.1",
        "bones": [{"id": "root", "parent": None, "pivot": [0, 0, 0], "rotation_mdeg": [0, 0, 0]}],
    }


class SkinningTests(unittest.TestCase):
    def test_single_bone_rotates_weighted_vertex_deterministically(self):
        vertices = [(1000, 0, 0), (0, 1000, 0)]
        weights = [{"vertex": 0, "influences": [{"bone": "root", "weight_milli": 1000}]}]
        clip = {"schema": "axm.framestate.skin-clip3d/v0.1", "bones": {"root": {"rot_z_mdeg": 90000}}}
        a, ev_a = skin_vertices(vertices, rig(), weights, clip, 0, 0, 2)
        b, ev_b = skin_vertices(vertices, rig(), weights, clip, 0, 0, 2)
        self.assertEqual(a, b)
        self.assertEqual(ev_a, ev_b)
        self.assertLessEqual(abs(a[0][0]), 4)
        self.assertLessEqual(abs(a[0][1] - 1000), 4)
        self.assertEqual(a[1], vertices[1])
        self.assertEqual(ev_a["algorithm"], "deterministic-linear-blend-skinning3d-v0.1")

    def test_weights_must_be_explicit_and_sum_to_1000(self):
        with self.assertRaises(SkinningError):
            skin_vertices(
                [(1000, 0, 0)],
                rig(),
                [{"vertex": 0, "influences": [{"bone": "root", "weight_milli": 999}]}],
                {},
                0,
                0,
                2,
            )

    def test_skinned_mesh_renderer_deforms_shape_and_receipts_pose(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mesh.obj").write_text("v -1 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
            project = normalize_project({
                "schema": "axm.framestate.project/v0.5",
                "id": "skin-proof",
                "title": "Skin proof",
                "canvas": {"width": 96, "height": 72, "fps": 12},
                "duration_frames": 2,
                "background": [0, 0, 0],
                "camera": {"x": 0, "y": 0, "zoom_milli": 1000},
                "media": [{"id": "mesh", "kind": "mesh", "path": "mesh.obj"}],
                "layers": [{
                    "id": "deform",
                    "kind": "skinned_mesh3d",
                    "media_id": "mesh",
                    "z": 1,
                    "x": 48,
                    "y": 36,
                    "depth": 220,
                    "size": 80,
                    "color": [220, 160, 80],
                    "start_frame": 0,
                    "end_frame": 2,
                    "rig": rig(),
                    "weights": [{"vertex": 2, "influences": [{"bone": "root", "weight_milli": 1000}]}],
                    "clip": {"schema": "axm.framestate.skin-clip3d/v0.1", "bones": {"root": {"rot_z_mdeg": {"from": 0, "to": 60000, "easing": "linear"}}}},
                }],
                "captions": [], "audio": [], "effects": [], "markers": [], "metadata": {},
            })
            manifest = render_project(project, root / "render", root)
            a = manifest["states"][0]
            b = manifest["states"][1]
            self.assertNotEqual(a["pixel_digest"], b["pixel_digest"])
            layer_a = next(x for x in a["visible_layers"] if x["id"] == "deform")
            layer_b = next(x for x in b["visible_layers"] if x["id"] == "deform")
            self.assertEqual(layer_a["weighted_vertex_count"], 1)
            self.assertEqual(layer_a["bone_count"], 1)
            self.assertNotEqual(layer_a["bone_pose_digest"], layer_b["bone_pose_digest"])
            self.assertEqual(layer_a["skin_state_digest"], layer_b["skin_state_digest"])


if __name__ == "__main__":
    unittest.main()
