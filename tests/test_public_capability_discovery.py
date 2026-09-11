from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools import generate_public_capabilities as discovery


ROOT = Path(__file__).resolve().parents[1]


def fixture(root: Path) -> Path:
    paths = [discovery.MARKER_PATH, *discovery.SOURCE_PATHS]
    for relative_path in paths:
        source = ROOT / relative_path
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return root


class PublicCapabilityDiscoveryTests(unittest.TestCase):
    def test_committed_artifacts_are_exact_and_source_backed(self) -> None:
        ok, mismatches, expected = discovery.check_artifacts(ROOT)
        self.assertTrue(ok, mismatches)

        registry_bytes = (ROOT / discovery.REGISTRY_PATH).read_bytes()
        receipt = json.loads((ROOT / discovery.RECEIPT_PATH).read_text(encoding="utf-8"))
        record = json.loads(registry_bytes.decode("utf-8"))

        self.assertEqual(record["schema"], "axm.public-capability/v1")
        self.assertEqual(record["id"], discovery.CAPABILITY_ID)
        self.assertIsNone(record["status"])
        self.assertEqual(record["providers"], [discovery.REPOSITORY])
        self.assertFalse(record["runtime"]["network"])
        self.assertEqual(record["runtime"]["dependencies"], 0)
        self.assertEqual(record["contracts"]["capabilityMap"], discovery.CAPABILITY_MAP_SCHEMA)
        self.assertEqual(record["contracts"]["canonicalProject"], discovery.PROJECT_SCHEMA)
        self.assertEqual(
            record["authority"],
            {
                "discoveryOnly": True,
                "execution": False,
                "automaticSelection": False,
                "automaticInstall": False,
                "projectMutation": False,
                "merge": False,
                "canon": False,
            },
        )

        self.assertEqual(
            receipt["registry"]["sha256"],
            hashlib.sha256(registry_bytes).hexdigest(),
        )
        body = dict(receipt)
        receipt_hash = body.pop("receipt_sha256")
        self.assertEqual(
            receipt_hash,
            hashlib.sha256(discovery.canonical_json(body).encode("utf-8")).hexdigest(),
        )
        for source in receipt["sources"]:
            raw = (ROOT / source["path"]).read_bytes()
            self.assertEqual(source["git_blob_sha1"], discovery.git_blob_sha1(raw))
        self.assertEqual(expected[discovery.REGISTRY_PATH].encode("utf-8"), registry_bytes)

    def test_marker_must_remain_explicit_exact_public_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            marker = json.loads((root / discovery.MARKER_PATH).read_text(encoding="utf-8"))
            marker["public"] = False
            (root / discovery.MARKER_PATH).write_text(json.dumps(marker), encoding="utf-8")
            with self.assertRaisesRegex(discovery.DiscoveryError, "marker drift"):
                discovery.build_artifacts(root)

    def test_duplicate_marker_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            (root / discovery.MARKER_PATH).write_text(
                '{"schema":"axm.discovery-public/v1","public":true,"public":false,'
                '"repo":"mike-axiom-mir/axm-framestate","display_name":"AXM FrameState"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(discovery.DiscoveryError, "duplicate JSON key"):
                discovery.build_artifacts(root)

    def test_runtime_package_contract_drift_holds_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            path = root / discovery.PACKAGE_PATH
            text = path.read_text(encoding="utf-8").replace(
                'version = "0.10.0"', 'version = "9.9.9"'
            )
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(discovery.DiscoveryError, "version drift"):
                discovery.build_artifacts(root)

    def test_capability_map_anchor_drift_holds_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            path = root / discovery.CAPABILITY_MAP_PATH
            text = path.read_text(encoding="utf-8").replace(
                "'canonical-project-state':('executable'",
                "'canonical-project-state':('gap'",
                1,
            )
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(discovery.DiscoveryError, "anchor drift"):
                discovery.build_artifacts(root)

    def test_canonical_project_schema_drift_holds_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            path = root / discovery.CANONICAL_PATH
            text = path.read_text(encoding="utf-8").replace(
                "PROJECT_SCHEMA='axm.framestate.project/v0.5'",
                "PROJECT_SCHEMA='axm.framestate.project/v9.9'",
                1,
            )
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(discovery.DiscoveryError, "project schema drift"):
                discovery.build_artifacts(root)

    def test_symlinked_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            target = root / discovery.CLI_PATH
            replacement = root / "cli-real.py"
            target.replace(replacement)
            target.symlink_to(replacement)
            with self.assertRaisesRegex(discovery.DiscoveryError, "regular non-symlink"):
                discovery.build_artifacts(root)

    def test_generated_output_drift_is_reported_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            discovery.write_artifacts(root)
            registry = root / discovery.REGISTRY_PATH
            registry.write_text(registry.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
            ok, mismatches, _ = discovery.check_artifacts(root)
            self.assertFalse(ok)
            self.assertEqual(mismatches, [discovery.REGISTRY_PATH])
            self.assertTrue(registry.read_text(encoding="utf-8").endswith("drift\n"))


if __name__ == "__main__":
    unittest.main()
