import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import ProjectError, canonical_json, digest, load_project, normalize_project


def minimal_project():
    return {
        "schema": "axm.framestate.project/v0.5",
        "id": "portable-json-proof",
        "canvas": {"width": 16, "height": 16, "fps": 1},
        "duration_frames": 1,
        "metadata": {},
    }


class CanonicalJsonContractTests(unittest.TestCase):
    def test_normalized_project_is_strict_json_roundtrip_stable(self):
        raw = minimal_project()
        raw["metadata"] = {"quality_score": 1.25, "nested": {"enabled": True}}
        project = normalize_project(raw)
        encoded = canonical_json(project)
        decoded = json.loads(encoded.decode("utf-8"), parse_constant=self._reject_constant)
        self.assertEqual(project, decoded)
        self.assertEqual(digest(project), digest(decoded))

    def test_non_finite_metadata_fails_project_admission(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                raw = minimal_project()
                raw["metadata"] = {"quality_score": value}
                with self.assertRaisesRegex(ProjectError, "strict JSON"):
                    normalize_project(raw)

    def test_non_finite_value_fails_canonical_serialization(self):
        with self.assertRaisesRegex(ProjectError, "strict JSON"):
            canonical_json({"evidence": {"score": float("nan")}})

    def test_python_json_constants_fail_when_loaded_as_project(self):
        payload = (
            '{"schema":"axm.framestate.project/v0.5","id":"portable-json-proof",'
            '"canvas":{"width":16,"height":16,"fps":1},"duration_frames":1,'
            '"metadata":{"quality_score":NaN}}'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            path.write_text(payload, encoding="utf-8")
            with self.assertRaisesRegex(ProjectError, "strict JSON"):
                load_project(path)

    @staticmethod
    def _reject_constant(value):
        raise AssertionError(f"non-standard JSON constant escaped contract: {value}")


if __name__ == "__main__":
    unittest.main()
