from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from .audio import render_audio
from .canonical import canonical_json, digest
from .captions import export_vtt
from .parallel_render import render_project_parallel
from .receipts import _assemble_video, _stable_receipt_digest


def render_parallel_with_receipt(
    project: dict[str, Any],
    output_dir: Path,
    machine_root: Path,
    *,
    assemble: bool = True,
    profile: str = "h264",
    max_workers: int | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame_manifest = render_project_parallel(project, out, machine_root, max_workers=max_workers)
    execution = json.loads((out / "parallel-execution.json").read_text(encoding="utf-8"))
    audio_manifest = render_audio(project, out / "audio.wav", machine_root, out)
    subtitles = export_vtt(project, out / "captions.vtt")
    assembly, video = _assemble_video(project, out, profile, assemble)
    receipt = {
        "schema": "axm.framestate.parallel-render-receipt/v0.1",
        "project_id": project["id"],
        "project_digest": digest(project),
        "media_manifest_digest": frame_manifest["media_manifest_digest"],
        "frame_manifest_digest": frame_manifest["manifest_digest"],
        "parallel_execution": execution,
        "audio_manifest": audio_manifest,
        "subtitle_export": subtitles,
        "video": video,
        "assembly": assembly,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "truth_boundary": {
            "canonical_project": "unchanged normalized project state",
            "frame_execution": "frames may execute concurrently, but parent admits them in canonical frame order only after digest verification",
            "frame_truth": "parallel frame manifest is required to match the same sequential renderer semantics; concurrency is not allowed to alter frame state/bytes",
            "audio": "audio is rendered once through the canonical mixer after frame execution",
            "container_video": "external FFmpeg encoding boundary when assembly is requested",
            "performance": "parallel topology is evidenced; no universal wall-clock speedup claim is made because workload and host scheduling vary",
        },
    }
    receipt["receipt_digest"] = _stable_receipt_digest(receipt)
    (out / "parallel-render-receipt.json").write_bytes(canonical_json(receipt) + b"\n")
    return receipt
