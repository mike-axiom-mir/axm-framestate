from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import ProjectError, normalize_project
from axm_framestate.media import MediaError, conform_media


def project_with_media(media_id: str) -> dict:
    return {
        "schema": "axm.framestate.project/v0.5",
        "id": "media-boundary",
        "title": "Media boundary",
        "canvas": {"width": 16, "height": 16, "fps": 1},
        "duration_frames": 1,
        "background": [0, 0, 0],
        "media": [{"id": media_id, "kind": "image", "path": "source.ppm"}],
        "layers": [],
        "captions": [],
        "audio": [],
        "effects": [],
        "markers": [],
        "metadata": {},
    }


class MediaOutputBoundaryTests(unittest.TestCase):
    def test_media_ids_cannot_escape_or_alias_platform_paths(self):
        unsafe = ["../../outside", r"..\outside", "/tmp/outside", "C:outside", "NUL", "trailing."]
        for media_id in unsafe:
            with self.subTest(media_id=media_id), self.assertRaises(ProjectError):
                normalize_project(project_with_media(media_id))

    def test_output_guard_rejects_unnormalized_traversal_before_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "source.ppm").write_bytes(b"P6\n1 1\n255\n\xff\x00\x00")
            with self.assertRaises(MediaError):
                conform_media(project_with_media("../../outside"), root / "render", root)
            self.assertFalse((root / "outside").exists())

    def test_valid_media_id_conforms_inside_render_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "source.ppm").write_bytes(b"P6\n1 1\n255\n\xff\x00\x00")
            project = normalize_project(project_with_media("still-01"))
            manifest = conform_media(project, root / "render", root)
            self.assertEqual(manifest["rows"][0]["id"], "still-01")
            self.assertTrue((root / "render" / "conformed-media" / "still-01" / "frame-000000.ppm").is_file())
            self.assertFalse((root / "outside").exists())

    def test_symlinked_media_directory_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "source.ppm").write_bytes(b"P6\n1 1\n255\n\xff\x00\x00")
            render = root / "render"
            target = render / "conformed-media"
            outside = root / "outside"
            target.mkdir(parents=True)
            outside.mkdir()
            (target / "still-01").symlink_to(outside, target_is_directory=True)
            project = normalize_project(project_with_media("still-01"))
            with self.assertRaises(MediaError):
                conform_media(project, render, root)
            self.assertFalse((outside / "frame-000000.ppm").exists())

    def test_symlinked_frame_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "source.ppm").write_bytes(b"P6\n1 1\n255\n\xff\x00\x00")
            render = root / "render"
            media_dir = render / "conformed-media" / "still-01"
            media_dir.mkdir(parents=True)
            outside = root / "outside.ppm"
            outside.write_bytes(b"keep-me")
            (media_dir / "frame-000000.ppm").symlink_to(outside)
            project = normalize_project(project_with_media("still-01"))
            with self.assertRaises(MediaError):
                conform_media(project, render, root)
            self.assertEqual(outside.read_bytes(), b"keep-me")


if __name__ == "__main__":
    unittest.main()
