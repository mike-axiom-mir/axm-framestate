from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from axm_framestate.portable import main, portable_doctor


class PortableTests(unittest.TestCase):
    def test_doctor_exposes_owned_resources_and_truth_boundary(self):
        result = portable_doctor()
        self.assertEqual(result["schema"], "axm.framestate.portable-doctor/v0.1")
        self.assertEqual(result["version"], "0.14.0")
        self.assertEqual(set(result["studio_resources"]), {"index.html", "style.css", "app.js"})
        self.assertTrue(all(v.startswith("sha256:") for v in result["studio_resources"].values()))
        self.assertIn("Optional compatibility tools remain external", result["truth_boundary"])

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


if __name__ == "__main__":
    unittest.main()
