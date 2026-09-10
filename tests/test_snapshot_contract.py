from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from axm_framestate.forge import adopt_effect, spawn_effect
from axm_framestate.snapshot import SNAPSHOT_SCHEMA, SnapshotError, create_daily_snapshot, verify_snapshot

ROOT = Path(__file__).resolve().parents[1]
DAY = dt.date(2026, 9, 10)


class SnapshotContractTests(unittest.TestCase):
    def make_root(self, td: Path) -> Path:
        root = td / "machine"
        root.mkdir()
        (root / "seed.txt").write_text("seed", encoding="utf-8")
        (root / "nested").mkdir()
        (root / "nested" / "state.json").write_text('{"v":1}', encoding="utf-8")
        return root

    def test_corrupt_existing_daily_snapshot_is_rejected_without_rewrite(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"
            out.mkdir()
            target = out / f"AXM_FrameState_{DAY.isoformat()}.zip"
            original = b"not-a-zip"
            target.write_bytes(original)

            with self.assertRaises(SnapshotError):
                create_daily_snapshot(root, out, DAY)

            self.assertEqual(target.read_bytes(), original)

    def test_created_snapshot_is_manifest_bound_and_repeatable(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"

            first = create_daily_snapshot(root, out, DAY)
            self.assertTrue(first["created"])
            self.assertTrue(first["verified"])
            self.assertEqual(first["schema"], SNAPSHOT_SCHEMA)

            check = verify_snapshot(Path(first["path"]), expected_day=DAY)
            self.assertEqual(check["digest"], first["digest"])
            self.assertEqual(check["tree_digest"], first["tree_digest"])

            second = create_daily_snapshot(root, out, DAY)
            self.assertFalse(second["created"])
            self.assertEqual(second["publication"], "EXISTING_VERIFIED")
            self.assertEqual(second["digest"], first["digest"])

    def test_source_symlink_cannot_pull_external_bytes_into_recovery_snapshot(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            outside = td / "outside-secret.txt"
            outside.write_bytes(b"outside-secret-must-not-enter-recovery")
            leak = root / "linked-secret.txt"
            try:
                leak.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")

            out = td / "snapshots"
            target = out / f"AXM_FrameState_{DAY.isoformat()}.zip"
            try:
                create_daily_snapshot(root, out, DAY)
            except SnapshotError as exc:
                self.assertIn("source tree contains symlink", str(exc))
            else:
                with zipfile.ZipFile(target, "r") as zf:
                    leaked = zf.read("linked-secret.txt")
                self.assertNotEqual(leaked, outside.read_bytes(), "external source bytes were archived through a symlink")
                self.fail("recovery snapshot admitted a source-tree symlink")

            self.assertFalse(target.exists())

    def test_source_content_drift_during_capture_blocks_publication(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"
            target = out / f"AXM_FrameState_{DAY.isoformat()}.zip"
            original_writestr = zipfile.ZipFile.writestr
            changed = False

            def racing_writestr(archive, member, data, *args, **kwargs):
                nonlocal changed
                result = original_writestr(archive, member, data, *args, **kwargs)
                name = member.filename if isinstance(member, zipfile.ZipInfo) else str(member)
                if name == "nested/state.json" and not changed:
                    (root / "nested" / "state.json").write_text('{"v":2}', encoding="utf-8")
                    changed = True
                return result

            with mock.patch.object(zipfile.ZipFile, "writestr", new=racing_writestr):
                with self.assertRaisesRegex(SnapshotError, "source changed during capture"):
                    create_daily_snapshot(root, out, DAY)

            self.assertTrue(changed)
            self.assertFalse(target.exists())
            self.assertEqual(list(out.glob("*.tmp")), [])

    def test_source_inventory_drift_during_capture_blocks_publication(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"
            target = out / f"AXM_FrameState_{DAY.isoformat()}.zip"
            original_writestr = zipfile.ZipFile.writestr
            changed = False

            def racing_writestr(archive, member, data, *args, **kwargs):
                nonlocal changed
                result = original_writestr(archive, member, data, *args, **kwargs)
                name = member.filename if isinstance(member, zipfile.ZipInfo) else str(member)
                if name == "nested/state.json" and not changed:
                    (root / "late-state.txt").write_text("late", encoding="utf-8")
                    changed = True
                return result

            with mock.patch.object(zipfile.ZipFile, "writestr", new=racing_writestr):
                with self.assertRaisesRegex(SnapshotError, "source changed during capture"):
                    create_daily_snapshot(root, out, DAY)

            self.assertTrue(changed)
            self.assertFalse(target.exists())
            self.assertEqual(list(out.glob("*.tmp")), [])

    def test_valid_zip_with_changed_member_is_rejected_by_tree_digest(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"
            result = create_daily_snapshot(root, out, DAY)
            target = Path(result["path"])

            with zipfile.ZipFile(target, "r") as zf:
                comment = zf.comment
                members = {info.filename: zf.read(info) for info in zf.infolist()}
            members["seed.txt"] = b"changed"
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for name in sorted(members):
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    zf.writestr(info, members[name])
                zf.comment = comment
            changed = target.read_bytes()

            with self.assertRaisesRegex(SnapshotError, "content does not match"):
                create_daily_snapshot(root, out, DAY)

            self.assertEqual(target.read_bytes(), changed)

    def test_daily_boundary_remains_create_only_after_root_changes(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"

            first = create_daily_snapshot(root, out, DAY)
            (root / "seed.txt").write_text("later-state", encoding="utf-8")
            second = create_daily_snapshot(root, out, DAY)

            self.assertFalse(second["created"])
            self.assertEqual(second["digest"], first["digest"])
            self.assertEqual(second["tree_digest"], first["tree_digest"])

    def test_wrong_day_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            root = self.make_root(td)
            out = td / "snapshots"
            result = create_daily_snapshot(root, out, DAY)
            target = Path(result["path"])

            with self.assertRaisesRegex(SnapshotError, "day does not match"):
                verify_snapshot(target, expected_day=DAY + dt.timedelta(days=1))

            link = td / "linked.zip"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(SnapshotError, "must not be a symlink"):
                verify_snapshot(link, expected_day=DAY)

    def test_live_adoption_stops_before_write_when_recovery_snapshot_is_invalid(self):
        raw = json.loads((ROOT / "examples" / "posterize.effect.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw_td:
            td = Path(raw_td)
            machine = td / "machine"
            machine.mkdir()
            (machine / "seed.txt").write_text("seed", encoding="utf-8")
            candidate_file = td / "candidate.json"
            candidate_file.write_text(json.dumps(raw), encoding="utf-8")
            spawned = spawn_effect(candidate_file, td / "spawned")

            recovery_dir = td / "axm-framestate-snapshots"
            recovery_dir.mkdir()
            recovery = recovery_dir / f"AXM_FrameState_{DAY.isoformat()}.zip"
            original = b"truncated-recovery"
            recovery.write_bytes(original)

            with self.assertRaises(SnapshotError):
                adopt_effect(machine, Path(spawned["path"]), "recovery gate regression", raw["root_fit"], day=DAY)

            self.assertFalse((machine / "effect-organs").exists())
            self.assertEqual(recovery.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
