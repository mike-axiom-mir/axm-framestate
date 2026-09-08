from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from axm_framestate.audio import render_audio
from axm_framestate.native_image import encode_png_rgb
from axm_framestate.studio import StudioApp, StudioError, default_project


class StudioAssetTests(unittest.TestCase):
    def test_png_import_is_project_local_sanitized_digest_bound_and_previewable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = StudioApp(root)
            png = encode_png_rgb(2, 2, bytes([250, 40, 20] * 4))
            with patch("axm_framestate.media._pillow_image", side_effect=AssertionError("Pillow path must not run")):
                result = app.import_asset(
                    default_project(),
                    name="../../ Weird poster.png",
                    kind="image",
                    data_b64=base64.b64encode(png).decode("ascii"),
                )
                preview = app.preview(result["project"], 0, "exact")
            receipt = result["import_receipt"]
            self.assertEqual(receipt["decode"]["boundary"], "native-png-v0.1")
            self.assertTrue(receipt["project_relative_path"].startswith("assets/"))
            self.assertNotIn("..", receipt["project_relative_path"])
            target = root / receipt["project_relative_path"]
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), png)
            self.assertEqual(result["project"]["media"][-1]["path"], receipt["project_relative_path"])
            self.assertEqual(result["project"]["layers"][-1]["media_id"], receipt["media_id"])
            self.assertTrue(preview["image"].startswith("data:image/png;base64,"))

    def test_wav_import_creates_project_relative_file_event_and_renders_without_ffmpeg(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = StudioApp(root)
            bio = io.BytesIO()
            with wave.open(bio, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes((b"\x00\x04" * 4000))
            result = app.import_asset(
                default_project(),
                name="voice sample.wav",
                kind="audio",
                data_b64=base64.b64encode(bio.getvalue()).decode("ascii"),
            )
            event = result["project"]["audio"][-1]
            self.assertEqual(event["kind"], "file")
            self.assertTrue(event["path"].startswith("assets/"))
            with patch("axm_framestate.audio.shutil.which", return_value=None):
                manifest = render_audio(result["project"], root / "mix.wav", root, root)
            evidence = next(x for x in manifest["source_evidence"] if x["id"] == event["id"])
            self.assertEqual(evidence["decoder"]["boundary"], "native-wav-pcm-v0.1")

    def test_invalid_child_project_is_rejected_before_asset_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = StudioApp(root)
            bad = base64.b64encode(json.dumps({"not": "a project"}).encode("utf-8")).decode("ascii")
            with self.assertRaises(StudioError):
                app.import_asset(default_project(), name="bad.json", kind="framestate", data_b64=bad)
            assets = root / "assets"
            self.assertFalse(assets.exists() and any(assets.iterdir()))


if __name__ == "__main__":
    unittest.main()
