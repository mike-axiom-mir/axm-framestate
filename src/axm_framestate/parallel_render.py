from __future__ import annotations

import copy
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, file_digest
from .effects import load_effect_library
from .media import MediaCache
from .render import render_frame


class ParallelRenderError(RuntimeError):
    pass


def _chunks(frame_count: int, workers: int) -> list[list[int]]:
    workers = max(1, min(workers, frame_count))
    base, extra = divmod(frame_count, workers)
    rows: list[list[int]] = []
    start = 0
    for index in range(workers):
        size = base + (1 if index < extra else 0)
        rows.append(list(range(start, start + size)))
        start += size
    return [row for row in rows if row]


def _render_chunk(
    project: dict[str, Any],
    frames: list[int],
    machine_root: str,
    chunk_root: str,
    realization: dict[str, Any] | None,
) -> dict[str, Any]:
    root = Path(machine_root)
    out = Path(chunk_root)
    frame_dir = out / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    library = load_effect_library(root)
    cache = MediaCache(project, out, root)
    rendered = []
    for frame in frames:
        ppm, state = render_frame(project, frame, library, cache, realization)
        path = frame_dir / f"frame-{frame:06d}.ppm"
        path.write_bytes(ppm)
        rendered.append({"frame": frame, "path": str(path), "state": state, "digest": file_digest(path)})
    return {
        "pid": os.getpid(),
        "frames": rendered,
        "media_manifest_digest": cache.manifest["manifest_digest"],
    }


def render_project_parallel(
    project: dict[str, Any],
    output_dir: Path,
    machine_root: Path,
    realization: dict[str, Any] | None = None,
    *,
    max_workers: int | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    machine_root = Path(machine_root)
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_count = int(project["duration_frames"])
    if frame_count < 1:
        raise ParallelRenderError("project has no frames")

    requested = int(max_workers or (os.cpu_count() or 1))
    workers = max(1, min(requested, frame_count, 64))
    if workers == 1:
        raise ParallelRenderError("cpu-parallel backend requires at least two workers")

    # Establish the canonical final media manifest once in the real output directory.
    final_cache = MediaCache(project, output_dir, machine_root)
    media_digest = final_cache.manifest["manifest_digest"]

    work_root = output_dir / ".parallel-work"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True, exist_ok=True)

    plans = _chunks(frame_count, workers)
    results: list[dict[str, Any]] = []
    try:
        with ProcessPoolExecutor(max_workers=len(plans)) as executor:
            futures = []
            for index, frames in enumerate(plans):
                chunk_root = work_root / f"worker-{index:03d}"
                futures.append(executor.submit(
                    _render_chunk,
                    copy.deepcopy(project),
                    frames,
                    str(machine_root),
                    str(chunk_root),
                    copy.deepcopy(realization),
                ))
            for future in as_completed(futures):
                results.append(future.result())

        worker_media = {row["media_manifest_digest"] for row in results}
        if worker_media != {media_digest}:
            raise ParallelRenderError("parallel worker media truth diverged from final media manifest")

        rendered = [frame for row in results for frame in row["frames"]]
        rendered.sort(key=lambda row: row["frame"])
        if [row["frame"] for row in rendered] != list(range(frame_count)):
            raise ParallelRenderError("parallel worker frame coverage is incomplete or duplicated")

        states = []
        files = []
        for row in rendered:
            source = Path(row["path"])
            target = frame_dir / f"frame-{row['frame']:06d}.ppm"
            shutil.copyfile(source, target)
            final_digest = file_digest(target)
            if final_digest != row["digest"]:
                raise ParallelRenderError(f"frame {row['frame']} changed while admitting worker output")
            states.append(row["state"])
            files.append({"path": target.name, "digest": final_digest})

        manifest = {
            "schema": "axm.framestate.frame-manifest/v0.6" if realization else "axm.framestate.frame-manifest/v0.4",
            "project_digest": digest(project),
            "media_manifest_digest": media_digest,
            "frame_count": len(states),
            "states": states,
            "files": files,
        }
        if realization:
            manifest["realization_contract_digest"] = realization.get("contract_digest")
            manifest["realization_tier"] = realization.get("tier")
            manifest["fidelity"] = realization.get("fidelity")
        manifest["manifest_digest"] = digest(manifest)
        (output_dir / "frame-manifest.json").write_bytes(canonical_json(manifest) + b"\n")

        execution = {
            "schema": "axm.framestate.parallel-execution/v0.1",
            "backend": "cpu-parallel",
            "requested_workers": requested,
            "worker_count": len(plans),
            "worker_pids": sorted({int(row["pid"]) for row in results}),
            "chunks": [{"first_frame": frames[0], "last_frame": frames[-1], "frame_count": len(frames)} for frames in plans],
            "project_digest": digest(project),
            "media_manifest_digest": media_digest,
            "frame_manifest_digest": manifest["manifest_digest"],
            "claim": "execution topology only; canonical frame order/state/bytes are admitted by the parent after worker completion",
        }
        execution["execution_digest"] = digest(execution)
        (output_dir / "parallel-execution.json").write_bytes(canonical_json(execution) + b"\n")
        return manifest
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
