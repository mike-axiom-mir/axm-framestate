from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .audio import render_audio
from .captions import write_webvtt
from .canonical import canonical_json, digest, file_digest
from .render import render_project


def _ffmpeg_version() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    proc = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, check=False)
    return proc.stdout.splitlines()[0] if proc.stdout else "ffmpeg-present-version-unknown"


def render_with_receipt(project: dict[str, Any], output_dir: Path, machine_root: Path, *, assemble: bool = True) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_manifest = render_project(project, output_dir, machine_root)
    audio_manifest = render_audio(project, output_dir / "audio.wav", machine_root)
    caption_manifest = write_webvtt(project, output_dir / "captions.vtt")
    ffmpeg_version = _ffmpeg_version()
    video = None
    assembly = {
        "attempted": False,
        "succeeded": False,
        "external_boundary": "ffmpeg",
        "version": ffmpeg_version,
        "bit_exact_claim": False,
    }
    if assemble and ffmpeg_version:
        assembly["attempted"] = True
        fps = project["canvas"]["fps"]
        video_path = output_dir / "video.mp4"
        command = [
            shutil.which("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(fps), "-i", str(output_dir / "frames" / "frame-%06d.ppm"),
            "-i", str(output_dir / "audio.wav"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            "-movflags", "+faststart", str(video_path),
        ]
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        assembly.update({"returncode": proc.returncode, "stderr": proc.stderr[-4000:]})
        if proc.returncode == 0 and video_path.is_file():
            video = {"path": str(video_path), "digest": file_digest(video_path)}
            assembly["succeeded"] = True
    receipt = {
        "schema": "axm.framestate.render-receipt/v0.2",
        "project_id": project["id"],
        "project_digest": digest(project),
        "frame_manifest_digest": frame_manifest["manifest_digest"],
        "audio_manifest": audio_manifest,
        "caption_manifest": caption_manifest,
        "video": video,
        "assembly": assembly,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "truth_boundary": {
            "canonical_project": "normalized and digest-bound",
            "frame_state": "deterministic integer timeline plus exact PPM bytes receipted",
            "audio": "exact mixed WAV bytes receipted; imported audio decode is an explicit FFmpeg boundary",
            "media": "image/video inputs are digest-bound and conformed to exact PPM frames through an explicit FFmpeg boundary",
            "captions": "caption cues render through the bundled bitmap font and export exact WebVTT bytes",
            "container_video": "external FFmpeg encoding boundary; no cross-machine bit-identical MP4 claim",
        },
    }
    receipt["receipt_digest"] = digest(receipt)
    (output_dir / "render-receipt.json").write_bytes(canonical_json(receipt) + b"\n")
    return receipt


def verify_repeat(project: dict[str, Any], base_dir: Path, machine_root: Path) -> dict[str, Any]:
    first = render_with_receipt(project, Path(base_dir) / "repeat-a", machine_root, assemble=False)
    second = render_with_receipt(project, Path(base_dir) / "repeat-b", machine_root, assemble=False)
    a_manifest = json.loads((Path(base_dir) / "repeat-a" / "frame-manifest.json").read_text(encoding="utf-8"))
    b_manifest = json.loads((Path(base_dir) / "repeat-b" / "frame-manifest.json").read_text(encoding="utf-8"))
    checks = {
        "project_digest_equal": first["project_digest"] == second["project_digest"],
        "frame_manifest_equal": a_manifest == b_manifest,
        "audio_pcm_equal": first["audio_manifest"]["pcm_digest"] == second["audio_manifest"]["pcm_digest"],
        "audio_wav_equal": first["audio_manifest"]["wav_digest"] == second["audio_manifest"]["wav_digest"],
    }
    result = {
        "schema": "axm.framestate.repeat-verification/v0.2",
        "passed": all(checks.values()),
        "checks": checks,
        "project_digest": first["project_digest"],
        "frame_manifest_digest": a_manifest["manifest_digest"],
        "audio_pcm_digest": first["audio_manifest"]["pcm_digest"],
        "claim": "repeat proof covers canonical state, frame states, PPM frame bytes and WAV bytes in this runtime; it does not claim arbitrary external codecs are bit-identical",
    }
    result["verification_digest"] = digest(result)
    return result
