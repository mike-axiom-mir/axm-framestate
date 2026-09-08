from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_json(exe: Path, *args: str) -> dict:
    proc = subprocess.run([str(exe), *args], capture_output=True, text=True, check=False, timeout=120)
    if proc.returncode != 0:
        raise SystemExit(f"portable command failed ({proc.returncode}): {' '.join(args)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"portable command did not emit JSON: {' '.join(args)}\n{proc.stdout}\n{proc.stderr}") from exc


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: python packaging/smoke_portable.py <FrameState executable>")
    exe = Path(args[0]).resolve()
    if not exe.is_file():
        raise SystemExit(f"portable executable missing: {exe}")

    doctor = run_json(exe, "doctor")
    assert doctor["schema"] == "axm.framestate.portable-doctor/v0.1", doctor
    assert doctor["frozen_executable"] is True, doctor
    assert set(doctor["studio_resources"]) == {"index.html", "style.css", "app.js"}, doctor
    assert all(str(v).startswith("sha256:") for v in doctor["studio_resources"].values()), doctor

    capabilities = run_json(exe, "cli", "capabilities")
    assert capabilities["schema"].startswith("axm.framestate.capability-map/"), capabilities
    assert capabilities["capabilities"]["canonical-project-state"]["status"] == "executable", capabilities

    help_proc = subprocess.run([str(exe), "--help"], capture_output=True, text=True, check=False, timeout=30)
    assert help_proc.returncode == 0, help_proc.stderr
    assert "FrameState portable application" in help_proc.stdout, help_proc.stdout

    print(json.dumps({
        "portable_smoke": "PASS",
        "executable": exe.name,
        "platform_family": doctor["platform_family"],
        "version": doctor["version"],
        "studio_resource_count": len(doctor["studio_resources"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
