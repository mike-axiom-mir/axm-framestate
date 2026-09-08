from __future__ import annotations

import hashlib
import importlib.util
import json
import multiprocessing
import shutil
import sys
from importlib import resources
from typing import Any


def _resource_digest(name: str) -> str:
    data = resources.files("axm_framestate").joinpath("studio_ui", name).read_bytes()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def portable_doctor() -> dict[str, Any]:
    from . import __version__
    from .capabilities import capability_summary

    resource_digests = {name: _resource_digest(name) for name in ("index.html", "style.css", "app.js")}
    capabilities = capability_summary()["capabilities"]
    return {
        "schema": "axm.framestate.portable-doctor/v0.2",
        "version": __version__,
        "frozen_executable": bool(getattr(sys, "frozen", False)),
        "platform_family": sys.platform,
        "studio_resources": resource_digests,
        "owned_core_paths": {
            "canonical_project_state": capabilities["canonical-project-state"]["status"],
            "native_png": capabilities.get("native-png-import", {}).get("status", "unknown"),
            "native_wav": capabilities.get("native-wav-import", {}).get("status", "unknown"),
            "native_speech": capabilities["native-speech-synthesis"]["status"],
            "cpu_renderer": capabilities["2d-procedural-shapes"]["status"],
            "parallel_frames": capabilities.get("parallel-frame-render-backend", {}).get("status", "unpromoted"),
        },
        "optional_compatibility_tools": {
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "espeak": bool(shutil.which("espeak") or shutil.which("espeak-ng")),
            "pillow": importlib.util.find_spec("PIL") is not None,
        },
        "truth_boundary": "A frozen FrameState executable owns the canonical/native core and Studio resources. Optional compatibility tools remain external unless separately packaged and evidenced.",
    }


def _usage() -> str:
    return """FrameState portable application

Usage:
  FrameState                      Launch local FrameState Studio
  FrameState studio [project]     Launch Studio, optionally opening a project
  FrameState open [project]       Alias for studio
  FrameState cli <args...>        Run the canonical framestate CLI
  FrameState resume <args...>     Run crash-resumable rendering
  FrameState parallel <args...>   Run deterministic multi-process full-movie rendering
  FrameState doctor               Inspect this portable application's owned/optional boundaries
  FrameState --help               Show this help
"""


def main(argv: list[str] | None = None) -> int:
    # Required by frozen Windows executables before any ProcessPool child can re-enter safely.
    multiprocessing.freeze_support()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        from .studio import main as studio_main
        return studio_main([])
    command, rest = args[0], args[1:]
    if command in {"-h", "--help", "help"}:
        print(_usage(), end="")
        return 0
    if command in {"studio", "open"}:
        from .studio import main as studio_main
        return studio_main(rest)
    if command == "cli":
        from .cli import main as cli_main
        return cli_main(rest)
    if command == "resume":
        from .resumable import main as resume_main
        return resume_main(rest)
    if command == "parallel":
        from .parallel_movie import main as parallel_main
        return parallel_main(rest)
    if command == "doctor":
        print(json.dumps(portable_doctor(), indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    print(f"unknown portable command: {command}\n", file=sys.stderr)
    print(_usage(), file=sys.stderr, end="")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
