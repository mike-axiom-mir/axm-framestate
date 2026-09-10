from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", "renders", "snapshots"}
SNAPSHOT_SCHEMA = "axm.framestate.recovery-snapshot/v0.1"
_MAX_EXISTING_FILES = 100_000
_MAX_EXISTING_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


class SnapshotError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def _strict_json_loads(raw: bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-portable JSON constant {value!r}")

    return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _tree_digest(records: list[dict[str, Any]]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(records)).hexdigest()


def _manifest_bytes(day: dt.date, records: list[dict[str, Any]]) -> bytes:
    return _canonical_json(
        {
            "schema": SNAPSHOT_SCHEMA,
            "day": day.isoformat(),
            "files": len(records),
            "tree_digest": _tree_digest(records),
        }
    )


def _validate_member_name(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or path.is_absolute()
        or ".." in path.parts
        or name.endswith("/")
    ):
        raise SnapshotError(f"unsafe recovery snapshot member {name!r}")


def verify_snapshot(path: Path, *, expected_day: dt.date | None = None) -> dict[str, object]:
    path = Path(path)
    if path.is_symlink():
        raise SnapshotError("recovery snapshot must not be a symlink")
    try:
        mode = path.stat().st_mode
    except FileNotFoundError as exc:
        raise SnapshotError("recovery snapshot is missing") from exc
    if not stat.S_ISREG(mode):
        raise SnapshotError("recovery snapshot must be a regular file")

    try:
        with zipfile.ZipFile(path, "r") as zf:
            try:
                manifest = _strict_json_loads(zf.comment)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise SnapshotError("recovery snapshot manifest is missing or invalid") from exc
            expected_keys = {"schema", "day", "files", "tree_digest"}
            if not isinstance(manifest, dict) or set(manifest) != expected_keys:
                raise SnapshotError("recovery snapshot manifest shape is invalid")
            if manifest["schema"] != SNAPSHOT_SCHEMA:
                raise SnapshotError("unsupported recovery snapshot schema")
            if not isinstance(manifest["day"], str):
                raise SnapshotError("recovery snapshot day is invalid")
            if expected_day is not None and manifest["day"] != expected_day.isoformat():
                raise SnapshotError("recovery snapshot day does not match requested boundary")
            if type(manifest["files"]) is not int or manifest["files"] < 0:
                raise SnapshotError("recovery snapshot file count is invalid")
            if not isinstance(manifest["tree_digest"], str) or not manifest["tree_digest"].startswith("sha256:"):
                raise SnapshotError("recovery snapshot tree digest is invalid")

            infos = zf.infolist()
            if len(infos) > _MAX_EXISTING_FILES:
                raise SnapshotError("recovery snapshot contains too many files")
            names = [info.filename for info in infos]
            if len(set(names)) != len(names):
                raise SnapshotError("recovery snapshot contains duplicate member names")
            for name in names:
                _validate_member_name(name)
            total_declared = sum(info.file_size for info in infos)
            if total_declared > _MAX_EXISTING_UNCOMPRESSED_BYTES:
                raise SnapshotError("recovery snapshot exceeds verification size bound")

            records: list[dict[str, Any]] = []
            for info in sorted(infos, key=lambda item: item.filename):
                hasher = hashlib.sha256()
                size = 0
                with zf.open(info, "r") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        hasher.update(chunk)
                        size += len(chunk)
                if size != info.file_size:
                    raise SnapshotError(f"recovery snapshot size drift for {info.filename!r}")
                records.append(
                    {
                        "path": info.filename,
                        "size": size,
                        "sha256": "sha256:" + hasher.hexdigest(),
                    }
                )
    except SnapshotError:
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise SnapshotError("recovery snapshot archive is unreadable") from exc

    if manifest["files"] != len(records):
        raise SnapshotError("recovery snapshot file count does not match archive")
    tree_digest = _tree_digest(records)
    if manifest["tree_digest"] != tree_digest:
        raise SnapshotError("recovery snapshot content does not match its manifest")

    return {
        "verified": True,
        "schema": SNAPSHOT_SCHEMA,
        "path": str(path),
        "day": manifest["day"],
        "files": len(records),
        "tree_digest": tree_digest,
        "digest": _sha256_file(path),
    }


def _fsync_directory(path: Path) -> bool:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return False
    try:
        os.fsync(fd)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


def _collect_snapshot_files(root: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError as exc:
            raise SnapshotError(f"recovery snapshot source changed during enumeration: {rel.as_posix()!r}") from exc
        except OSError as exc:
            raise SnapshotError(f"recovery snapshot source is unreadable: {rel.as_posix()!r}") from exc
        if stat.S_ISLNK(mode):
            raise SnapshotError(f"recovery snapshot source tree contains symlink {rel.as_posix()!r}")
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise SnapshotError(f"recovery snapshot source tree contains non-regular entry {rel.as_posix()!r}")
        files.append((path, rel.as_posix()))
    return files


def create_daily_snapshot(root: Path, output_dir: Path | None = None, day: dt.date | None = None) -> dict[str, object]:
    root = Path(root).resolve()
    day = day or dt.date.today()
    out_dir = Path(output_dir).resolve() if output_dir else root.parent / "axm-framestate-snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"AXM_FrameState_{day.isoformat()}.zip"

    if os.path.lexists(target):
        verified = verify_snapshot(target, expected_day=day)
        return {
            "created": False,
            **verified,
            "publication": "EXISTING_VERIFIED",
            "directory_fsync": None,
        }

    files = _collect_snapshot_files(root)

    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=out_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        records: list[dict[str, Any]] = []
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path, rel in files:
                data = path.read_bytes()
                info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, data)
                records.append(
                    {
                        "path": rel,
                        "size": len(data),
                        "sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
                    }
                )
            records.sort(key=lambda item: item["path"])
            zf.comment = _manifest_bytes(day, records)

        with temp_path.open("rb") as handle:
            os.fsync(handle.fileno())
        verify_snapshot(temp_path, expected_day=day)

        try:
            os.link(temp_path, target)
        except FileExistsError:
            verified = verify_snapshot(target, expected_day=day)
            return {
                "created": False,
                **verified,
                "publication": "CONCURRENT_EXISTING_VERIFIED",
                "directory_fsync": None,
            }
        except OSError as exc:
            raise SnapshotError("atomic create-only recovery snapshot publication failed") from exc

        directory_fsync = _fsync_directory(out_dir)
        verified = verify_snapshot(target, expected_day=day)
        return {
            "created": True,
            **verified,
            "publication": "CREATED_ATOMIC_CREATE_ONLY",
            "directory_fsync": directory_fsync,
        }
    finally:
        temp_path.unlink(missing_ok=True)
