from __future__ import annotations

import argparse
import base64
import json
import os
import re
import tempfile
import threading
import webbrowser
import zlib
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, load_project, normalize_project
from .capabilities import capability_summary
from .effects import load_effect_library
from .media import MediaCache
from .prompts import apply_prompt_plan, interpret_prompt
from .realization import plan_realization, probe_machine
from .render import render_frame
from .review import review_project
from .receipts import render_with_receipt, render_realized_with_receipt

STUDIO_SCHEMA = "axm.framestate.studio-session/v0.1"
_JSON_LIMIT = 8 * 1024 * 1024
_LOOPBACK = {"127.0.0.1", "localhost"}
_SAFE_OUTPUT = re.compile(r"[^A-Za-z0-9._-]+")


class StudioError(ValueError):
    pass


def default_project() -> dict[str, Any]:
    return normalize_project(
        {
            "schema": "axm.framestate.project/v0.5",
            "id": "untitled-film",
            "title": "Untitled FrameState Film",
            "canvas": {"width": 640, "height": 360, "fps": 24},
            "duration_frames": 120,
            "background": [10, 12, 18],
            "camera": {"x": 0, "y": 0, "zoom_milli": 1000},
            "layers": [
                {
                    "id": "title",
                    "kind": "text",
                    "z": 10,
                    "x": 320,
                    "y": 180,
                    "text": "FRAMESTATE",
                    "scale": 4,
                    "color": [240, 244, 255],
                    "start_frame": 0,
                    "end_frame": 120,
                }
            ],
            "captions": [],
            "audio": [],
            "effects": [],
            "markers": [{"frame": 0, "label": "start"}],
            "metadata": {"created_by": "FrameState Studio"},
        }
    )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return len(data).to_bytes(4, "big") + body + crc.to_bytes(4, "big")


def ppm_to_png(ppm: bytes) -> bytes:
    parts = ppm.split(b"\n", 3)
    if len(parts) != 4 or parts[0] != b"P6" or parts[2] != b"255":
        raise StudioError("preview renderer returned unsupported PPM")
    try:
        width, height = (int(v) for v in parts[1].split())
    except Exception as exc:
        raise StudioError("preview renderer returned invalid PPM dimensions") from exc
    body = parts[3]
    if width < 1 or height < 1 or len(body) != width * height * 3:
        raise StudioError("preview renderer returned invalid PPM body")
    stride = width * 3
    scanlines = b"".join(b"\x00" + body[y * stride : (y + 1) * stride] for y in range(height))
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes((8, 2, 0, 0, 0))
    return signature + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(scanlines, 9)) + _png_chunk(b"IEND", b"")


def _atomic_write(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)


def _safe_output_name(value: str) -> str:
    value = _SAFE_OUTPUT.sub("-", str(value).strip()).strip(".-")
    if not value:
        value = "render"
    return value[:120]


@dataclass
class StudioApp:
    machine_root: Path
    project_path: Path | None = None

    def __post_init__(self) -> None:
        self.machine_root = Path(self.machine_root).resolve()
        if self.project_path is not None:
            self.project_path = Path(self.project_path).resolve()
            self.project = load_project(self.project_path)
            self.workspace_root = self.project_path.parent
        else:
            self.project = default_project()
            self.workspace_root = self.machine_root
        self.preview_root = self.workspace_root / ".framestate" / "studio-preview"
        self.render_root = self.workspace_root / ".framestate" / "renders"
        self._lock = threading.RLock()

    def session_state(self) -> dict[str, Any]:
        machine = probe_machine()
        return {
            "schema": STUDIO_SCHEMA,
            "project": self.project,
            "project_digest": digest(self.project),
            "project_path": str(self.project_path) if self.project_path else None,
            "workspace_root": str(self.workspace_root),
            "machine": machine,
            "capabilities": capability_summary(),
            "truth_boundary": "Studio edits canonical project state; previews/renders are realizations and never overwrite canonical state implicitly.",
        }

    def normalize(self, raw: Any) -> dict[str, Any]:
        project = normalize_project(raw)
        return {"project": project, "project_digest": digest(project)}

    def preview(self, raw: Any, frame: int = 0, mode: str = "exact") -> dict[str, Any]:
        project = normalize_project(raw)
        frame = max(0, min(project["duration_frames"] - 1, int(frame)))
        if mode not in {"exact", "adaptive"}:
            raise StudioError("preview mode must be exact or adaptive")
        realization = None
        if mode == "adaptive":
            realization = plan_realization(project, probe_machine(), {"mode": "adaptive"})
        key = digest({"project": project, "mode": mode}).replace("sha256:", "")[:24]
        out = self.preview_root / key
        out.mkdir(parents=True, exist_ok=True)
        library = load_effect_library(self.machine_root)
        cache = MediaCache(project, out, self.machine_root)
        ppm, state = render_frame(project, frame, library, cache, realization)
        png = ppm_to_png(ppm)
        return {
            "frame": frame,
            "mode": mode,
            "project_digest": digest(project),
            "frame_state": state,
            "image": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
            "realization_contract": realization,
        }

    def review(self, raw: Any) -> dict[str, Any]:
        return review_project(normalize_project(raw), self.machine_root)

    def apply_prompt(self, raw: Any, text: str) -> dict[str, Any]:
        project = normalize_project(raw)
        text = str(text).strip()
        if not text:
            raise StudioError("prompt text must not be empty")
        prompt = {
            "schema": "axm.framestate.prompt/v0.1",
            "id": "studio-prompt",
            "text": text,
            "ambiguity_policy": "hold",
        }
        plan = interpret_prompt(project, prompt)
        applied = apply_prompt_plan(project, plan)
        return {
            "plan": plan,
            "project": applied["project"],
            "project_digest": digest(applied["project"]),
            "applied_operations": applied["applied_operations"],
        }

    def save(self, raw: Any) -> dict[str, Any]:
        project = normalize_project(raw)
        path = self.project_path or (self.workspace_root / "framestate-project.json")
        _atomic_write(path, canonical_json(project) + b"\n")
        self.project_path = path.resolve()
        self.workspace_root = self.project_path.parent
        self.project = project
        return {"saved": True, "path": str(self.project_path), "project_digest": digest(project)}

    def render(self, raw: Any, name: str, profile: str = "h264", mode: str = "exact") -> dict[str, Any]:
        project = normalize_project(raw)
        if profile not in {"fast", "h264", "quality"}:
            raise StudioError("profile must be fast, h264, or quality")
        if mode not in {"exact", "adaptive"}:
            raise StudioError("render mode must be exact or adaptive")
        output = self.render_root / _safe_output_name(name)
        if mode == "adaptive":
            receipt = render_realized_with_receipt(project, output, self.machine_root, probe_machine(), {"mode": "adaptive"}, assemble=True)
        else:
            receipt = render_with_receipt(project, output, self.machine_root, assemble=True, profile=profile)
        return {"output": str(output), "receipt": receipt}


def _ui_bytes(name: str) -> bytes:
    base = resources.files("axm_framestate").joinpath("studio_ui")
    return base.joinpath(name).read_bytes()


def make_handler(app: StudioApp):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FrameStateStudio/0.11"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' data:; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, value: Any) -> None:
            self._send(status, json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _read_json(self) -> Any:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise StudioError("invalid Content-Length") from exc
            if length < 0 or length > _JSON_LIMIT:
                raise StudioError("request body too large")
            data = self.rfile.read(length)
            try:
                return json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise StudioError("request body must be UTF-8 JSON") from exc

        def do_GET(self) -> None:
            try:
                if self.path in {"/", "/index.html"}:
                    return self._send(HTTPStatus.OK, _ui_bytes("index.html"), "text/html; charset=utf-8")
                if self.path == "/style.css":
                    return self._send(HTTPStatus.OK, _ui_bytes("style.css"), "text/css; charset=utf-8")
                if self.path == "/app.js":
                    return self._send(HTTPStatus.OK, _ui_bytes("app.js"), "text/javascript; charset=utf-8")
                if self.path == "/api/state":
                    return self._json(HTTPStatus.OK, app.session_state())
                return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            except Exception as exc:
                return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_POST(self) -> None:
            try:
                host = self.headers.get("Host", "")
                origin = self.headers.get("Origin")
                if origin and origin not in {f"http://{host}", f"https://{host}"}:
                    raise StudioError("cross-origin Studio request refused")
                body = self._read_json()
                if not isinstance(body, dict):
                    raise StudioError("request body must be an object")
                with app._lock:
                    if self.path == "/api/normalize":
                        result = app.normalize(body.get("project"))
                    elif self.path == "/api/preview":
                        result = app.preview(body.get("project"), body.get("frame", 0), body.get("mode", "exact"))
                    elif self.path == "/api/review":
                        result = app.review(body.get("project"))
                    elif self.path == "/api/prompt":
                        result = app.apply_prompt(body.get("project"), body.get("text", ""))
                    elif self.path == "/api/save":
                        result = app.save(body.get("project"))
                    elif self.path == "/api/render":
                        result = app.render(body.get("project"), body.get("name", "render"), body.get("profile", "h264"), body.get("mode", "exact"))
                    else:
                        return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return self._json(HTTPStatus.OK, result)
            except (StudioError, ValueError, OSError) as exc:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:
                return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    return Handler


def launch_studio(
    project: str | Path | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    machine_root: str | Path | None = None,
) -> int:
    if host not in _LOOPBACK:
        raise StudioError("FrameState Studio is local-only; host must be loopback")
    if not 1 <= int(port) <= 65535:
        raise StudioError("port must be in 1..65535")
    root = Path(machine_root or Path.cwd()).resolve()
    app = StudioApp(root, Path(project) if project else None)
    server = ThreadingHTTPServer((host, int(port)), make_handler(app))
    url = f"http://{host}:{port}/"
    print(json.dumps({"studio": "READY", "url": url, "project": str(app.project_path) if app.project_path else None}, sort_keys=True))
    if open_browser:
        threading.Timer(0.15, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="framestate-studio", description="Launch the local offline FrameState visual creation surface")
    parser.add_argument("project", nargs="?", help="optional FrameState project JSON to open")
    parser.add_argument("--host", default="127.0.0.1", help="loopback host only")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="do not open the system browser automatically")
    args = parser.parse_args(argv)
    return launch_studio(args.project, host=args.host, port=args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    raise SystemExit(main())
