from __future__ import annotations

import datetime as dt
import hashlib
import zipfile
from pathlib import Path

EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", "renders", "snapshots"}


def create_daily_snapshot(root: Path, output_dir: Path | None = None, day: dt.date | None = None) -> dict[str, object]:
    root = Path(root).resolve()
    day = day or dt.date.today()
    out_dir = (Path(output_dir).resolve() if output_dir else root.parent / "axm-framestate-snapshots")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"AXM_FrameState_{day.isoformat()}.zip"
    if target.exists():
        return {"created": False, "path": str(target), "day": day.isoformat(), "digest": "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()}
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        files.append((path, rel.as_posix()))
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, rel in files:
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return {"created": True, "path": str(target), "day": day.isoformat(), "digest": "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest(), "files": len(files)}
