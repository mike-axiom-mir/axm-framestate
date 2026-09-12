from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from axm_framestate import __version__
from axm_framestate.portable import main, portable_doctor


class PortableTests(unittest.TestCase):
    def test_doctor_exposes_owned_resources_and_truth_boundary(self):
        result = portable_doctor()
        self.assertEqual(result["schema"], "axm.framestate.portable-doctor/v0.2")
        self.assertEqual(result["version"], __version__)
        self.assertEqual(set(result["studio_resources"]), {"index.html", "style.css", "app.js"})
        self.assertTrue(all(v.startswith("sha256:") for v in result["studio_resources"].values()))
        self.assertEqual(result["owned_core_paths"]["native_png"], "tested")
        self.assertEqual(result["owned_core_paths"]["native_wav"], "tested")
        boundary = result["truth_boundary"]
        self.assertIn("Optional compatibility tools", boundary)
        self.assertIn("semantic translators remain external", boundary)

    def test_portable_cli_routes_to_canonical_capability_map(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["cli", "capabilities"])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["schema"].startswith("axm.framestate.capability-map/"))
        self.assertEqual(payload["capabilities"]["canonical-project-state"]["status"], "executable")

    def test_help_is_available_without_launching_studio(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("FrameState portable application", out.getvalue())
        self.assertIn("FrameState parallel", out.getvalue())
        self.assertIn("FrameState semantic", out.getvalue())


if __name__ == "__main__":
    unittest.main()
