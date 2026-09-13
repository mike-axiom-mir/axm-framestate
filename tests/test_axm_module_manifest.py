from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "AXM_MODULE.json"


class AxmNativeCallableManifestTests(unittest.TestCase):
    def test_timeline_sampler_descriptor_points_to_real_existing_callable(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.4")
        self.assertEqual(manifest["module"]["name"], "axm-framestate")

        callable_capabilities = [row for row in manifest["capabilities"] if row.get("callable")]
        self.assertEqual(len(callable_capabilities), 1)
        capability = callable_capabilities[0]
        self.assertEqual(capability["id"], "timeline.integer-sample")
        descriptor = capability["callable"]
        self.assertEqual(descriptor["schema"], "axm.callable-capability/v0.1")
        self.assertEqual(descriptor["kind"], "module-export")
        self.assertEqual(descriptor["runtime"], "python")
        self.assertEqual(descriptor["authority"], "none")
        self.assertEqual(descriptor["network"], "none")
        self.assertEqual(descriptor["export"], "sample")

        relative = Path(descriptor["path"])
        self.assertFalse(relative.is_absolute())
        self.assertNotIn("..", relative.parts)
        target = (ROOT / relative).resolve()
        target.relative_to(ROOT.resolve())
        self.assertTrue(target.is_file())

        spec = importlib.util.spec_from_file_location("axm_framestate_native_callable_timeline", target)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        callable_fn = getattr(module, descriptor["export"])
        self.assertTrue(callable(callable_fn))

        # Existing FrameState semantics are exercised; this manifest adds no new sampler logic.
        self.assertEqual(callable_fn(37, 100, 0, 11), 37)
        self.assertEqual(callable_fn({"from": 0, "to": 100, "easing": "linear"}, 5, 0, 11), 50)
        self.assertEqual(callable_fn({
            "keyframes": [
                {"frame": 0, "value": 10, "easing": "linear"},
                {"frame": 10, "value": 110}
            ]
        }, 5, 0, 11), 60)
        self.assertEqual(callable_fn({
            "keyframes": [
                {"frame": 0, "value": 10, "easing": "hold"},
                {"frame": 10, "value": 110}
            ]
        }, 5, 0, 11), 10)

        not_claimed = manifest["truth_boundary"]["not_claimed"]
        self.assertTrue(any("Monolith execution" in item for item in not_claimed))
        self.assertTrue(any("CANON" in item for item in not_claimed))


if __name__ == "__main__":
    unittest.main()
