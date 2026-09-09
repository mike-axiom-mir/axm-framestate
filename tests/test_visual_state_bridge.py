from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_framestate.canonical import digest, load_project
from axm_framestate.visual_state_bridge import (
    BRIDGE_PLAN_SCHEMA,
    BRIDGE_RESULT_SCHEMA,
    VisualStateBridgeError,
    apply_visual_state_realization,
    plan_visual_state_realization,
)


def compilation(state, *, status="COMPILED_VISUAL_STATE"):
    return {
        "schema": "axm.visual-state-compilation/v0.1",
        "truth_status": status,
        "state": state,
        "state_sha256": "donor-claim-fixture",
        "truth": {
            "automaticExecution": False,
            "compiledAppearanceUniquelyDetermines3D": False,
        },
    }


class VisualStateBridgeTests(unittest.TestCase):
    def setUp(self):
        self.project = load_project(ROOT / "examples" / "adaptive_realization.json")
        self.machine = json.loads(
            (ROOT / "examples" / "machine_high.json").read_text(encoding="utf-8")
        )

    def test_high_fidelity_and_detail_project_into_existing_realization_controls(self):
        plan = plan_visual_state_realization(
            compilation(
                {
                    "appearance": {"render_fidelity": 0.9},
                    "projection": {"detail_level": 0.9},
                }
            )
        )
        self.assertEqual(plan["schema"], BRIDGE_PLAN_SCHEMA)
        self.assertEqual(plan["effective_policy"]["min_internal_sample_scale"], 2)
        self.assertEqual(plan["effective_policy"]["preferred_texture_filter"], "bilinear")
        self.assertEqual(plan["effective_policy"]["min_particle_density_milli"], 900)
        self.assertTrue(plan["summary"]["policy_changed"])
        self.assertEqual([row["status"] for row in plan["mapped_paths"]], [
            "PARTIAL_NATIVE_PROJECTION",
            "PARTIAL_NATIVE_PROJECTION",
        ])
        self.assertEqual(plan["authority"], "NONE")

    def test_resolution_request_is_held_instead_of_rewriting_canonical_canvas(self):
        plan = plan_visual_state_realization(
            compilation(
                {
                    "projection": {
                        "detail_level": 0.7,
                        "resolution_tier": "8k",
                    }
                }
            )
        )
        held = {row["source_path"]: row for row in plan["held_paths"]}
        self.assertEqual(
            held["projection.resolution_tier"]["reason"],
            "CANONICAL_CANVAS_NOT_SILENTLY_REWRITTEN",
        )

    def test_unknown_cross_media_state_remains_visible_as_hold(self):
        plan = plan_visual_state_realization(
            compilation(
                {
                    "appearance": {"render_modes": ["3d"]},
                    "scene": {"lighting_setups": ["rim"]},
                    "temporal": {"capture_modes": ["motion-blur"]},
                }
            )
        )
        self.assertEqual(plan["summary"]["mapped_paths"], 0)
        self.assertEqual(plan["summary"]["held_paths"], 3)
        self.assertEqual(
            {row["source_path"] for row in plan["held_paths"]},
            {
                "appearance.render_modes",
                "scene.lighting_setups",
                "temporal.capture_modes",
            },
        )

    def test_explicit_user_policy_wins_over_donor_direction(self):
        plan = plan_visual_state_realization(
            compilation(
                {
                    "appearance": {"render_fidelity": 0.95},
                    "projection": {"detail_level": 1.0},
                }
            ),
            {
                "schema": "axm.framestate.realization-policy/v0.2",
                "preferred_texture_filter": "nearest",
                "min_internal_sample_scale": 1,
                "min_particle_density_milli": 400,
            },
        )
        self.assertEqual(plan["effective_policy"]["preferred_texture_filter"], "nearest")
        self.assertEqual(plan["effective_policy"]["min_internal_sample_scale"], 1)
        self.assertEqual(plan["effective_policy"]["min_particle_density_milli"], 400)
        self.assertEqual(
            [row["status"] for row in plan["mapped_paths"]],
            ["USER_POLICY_PRECEDENCE", "USER_POLICY_PRECEDENCE"],
        )

    def test_conflicted_donor_compilation_fails_closed(self):
        with self.assertRaisesRegex(VisualStateBridgeError, "conflict-resolved"):
            plan_visual_state_realization(
                compilation(
                    {"projection": {"camera_viewpoints": ["top-down", "low-angle"]}},
                    status="HOLD_VISUAL_STATE_CONFLICT",
                )
            )

    def test_malformed_numeric_direction_fails_closed(self):
        for bad in (-0.1, 1.1, True, "high"):
            with self.subTest(value=bad):
                with self.assertRaises(VisualStateBridgeError):
                    plan_visual_state_realization(
                        compilation({"appearance": {"render_fidelity": bad}})
                    )

    def test_apply_preserves_project_truth_and_emits_verified_contract(self):
        original = copy.deepcopy(self.project)
        before = digest(original)
        result = apply_visual_state_realization(
            self.project,
            self.machine,
            compilation(
                {
                    "appearance": {
                        "render_fidelity": 0.9,
                        "aesthetics": ["cinematic"],
                    },
                    "projection": {
                        "detail_level": 0.85,
                        "resolution_tier": "4k",
                    },
                }
            ),
        )
        self.assertEqual(result["schema"], BRIDGE_RESULT_SCHEMA)
        self.assertTrue(result["canonical_project_unchanged"])
        self.assertTrue(result["invariant_check"]["passed"])
        self.assertEqual(digest(self.project), before)
        self.assertEqual(self.project, original)
        self.assertEqual(
            result["realization_contract"]["canonical_project_digest"], before
        )
        held_paths = {
            row["source_path"] for row in result["bridge_plan"]["held_paths"]
        }
        self.assertIn("appearance.aesthetics", held_paths)
        self.assertIn("projection.resolution_tier", held_paths)
        self.assertEqual(result["authority"], "NONE")

    def test_plan_is_deterministic_for_equivalent_state_key_order(self):
        first = plan_visual_state_realization(
            compilation(
                {
                    "projection": {"resolution_tier": "8k", "detail_level": 0.8},
                    "appearance": {"render_fidelity": 0.8},
                }
            )
        )
        second = plan_visual_state_realization(
            compilation(
                {
                    "appearance": {"render_fidelity": 0.8},
                    "projection": {"detail_level": 0.8, "resolution_tier": "8k"},
                }
            )
        )
        self.assertEqual(first, second)
        self.assertEqual(first["plan_digest"], second["plan_digest"])


if __name__ == "__main__":
    unittest.main()
