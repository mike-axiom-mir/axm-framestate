from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def fs_digest(value) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def run_json(exe: Path, *args: str, timeout: int = 120) -> dict:
    proc = subprocess.run([str(exe), *args], capture_output=True, text=True, check=False, timeout=timeout)
    if proc.returncode != 0:
        raise SystemExit(f"portable command failed ({proc.returncode}): {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"portable command did not emit JSON: {' '.join(args)}\n{proc.stdout}\n{proc.stderr}") from exc


def tiny_project() -> dict:
    return {
        "schema": "axm.framestate.project/v0.5",
        "id": "portable-parallel-proof",
        "title": "Portable parallel proof",
        "canvas": {"width": 48, "height": 32, "fps": 12},
        "duration_frames": 4,
        "background": [4, 6, 10],
        "camera": {"x": 0, "y": 0, "zoom_milli": 1000},
        "media": [],
        "layers": [{
            "id": "box", "kind": "rect", "z": 1,
            "x": {"from": 12, "to": 36}, "y": 16,
            "w": 12, "h": 8, "color": [220, 100, 60],
            "start_frame": 0, "end_frame": 4,
        }],
        "captions": [], "audio": [], "effects": [], "markers": [], "metadata": {},
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: python packaging/smoke_portable.py <FrameState executable>")
    exe = Path(args[0]).resolve()
    if not exe.is_file():
        raise SystemExit(f"portable executable missing: {exe}")

    doctor = run_json(exe, "doctor")
    assert doctor["schema"] == "axm.framestate.portable-doctor/v0.2", doctor
    assert doctor["frozen_executable"] is True, doctor
    assert set(doctor["studio_resources"]) == {"index.html", "style.css", "app.js"}, doctor
    assert all(str(v).startswith("sha256:") for v in doctor["studio_resources"].values()), doctor
    assert doctor["owned_core_paths"]["native_png"] == "tested", doctor
    assert doctor["owned_core_paths"]["native_wav"] == "tested", doctor

    capabilities = run_json(exe, "cli", "capabilities")
    assert capabilities["schema"].startswith("axm.framestate.capability-map/"), capabilities
    assert capabilities["capabilities"]["canonical-project-state"]["status"] == "executable", capabilities

    help_proc = subprocess.run([str(exe), "--help"], capture_output=True, text=True, check=False, timeout=30)
    assert help_proc.returncode == 0, help_proc.stderr
    assert "FrameState portable application" in help_proc.stdout, help_proc.stdout
    assert "FrameState parallel" in help_proc.stdout, help_proc.stdout
    assert "FrameState semantic" in help_proc.stdout, help_proc.stdout

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        project_path = root / "portable-proof.json"
        render_output = root / "render"
        project_path.write_text(json.dumps(tiny_project(), sort_keys=True) + "\n", encoding="utf-8")

        parallel = run_json(exe, "parallel", str(project_path), str(render_output), "--workers", "2", "--no-assemble", timeout=180)
        assert parallel["schema"] == "axm.framestate.parallel-render-receipt/v0.1", parallel
        assert parallel["parallel_execution"]["backend"] == "cpu-parallel", parallel
        assert parallel["parallel_execution"]["worker_count"] == 2, parallel
        assert parallel["parallel_execution"]["frame_manifest_digest"] == parallel["frame_manifest_digest"], parallel
        assert (render_output / "frame-manifest.json").is_file(), parallel
        assert (render_output / "parallel-execution.json").is_file(), parallel

        normalized = run_json(exe, "cli", "inspect", str(project_path))
        direction = {
            "schema": "axm.framestate.semantic-direction/v0.1",
            "id": "portable-semantic-proof",
            "text": "Make the test candidate calmer.",
        }
        candidate = json.loads(json.dumps(normalized))
        candidate["title"] = "Portable semantic candidate"
        response = {
            "schema": "axm.framestate.semantic-response/v0.1",
            "input_project_digest": fs_digest(normalized),
            "direction_text_digest": fs_digest(direction["text"]),
            "translator": {"id": "portable-fixture", "version": "1", "implementation": "precomputed-smoke"},
            "candidate_project": candidate,
            "rationale": "portable staging proof only",
            "assumptions": [],
        }
        direction_path = root / "direction.json"
        response_path = root / "response.json"
        stage_output = root / "semantic-stage"
        direction_path.write_text(json.dumps(direction, sort_keys=True) + "\n", encoding="utf-8")
        response_path.write_text(json.dumps(response, sort_keys=True) + "\n", encoding="utf-8")
        semantic = run_json(exe, "semantic", str(project_path), str(direction_path), str(stage_output), "--response", str(response_path))
        assert semantic["schema"] == "axm.framestate.semantic-receipt/v0.1", semantic
        assert semantic["status"] == "STAGED_CHANGED", semantic
        assert semantic["automatic_canonical_write"] is False, semantic
        assert (stage_output / "semantic-candidate-project.json").is_file(), semantic

    print(json.dumps({
        "portable_smoke": "PASS",
        "parallel_smoke": "PASS",
        "semantic_smoke": "PASS",
        "executable": exe.name,
        "platform_family": doctor["platform_family"],
        "version": doctor["version"],
        "studio_resource_count": len(doctor["studio_resources"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
