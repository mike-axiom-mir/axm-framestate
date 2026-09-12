from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest
from .receipts import _stable_receipt_digest


_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_METADATA_LIMIT = 64 * 1024 * 1024
_RECEIPT_SCHEMAS = {
    "axm.framestate.render-receipt/v0.8",
    "axm.framestate.render-receipt/v0.10",
}
_MEDIA_SCHEMAS = {
    "axm.framestate.media-manifest/v0.4",
    "axm.framestate.media-manifest/v0.5",
}
_AUDIO_SCHEMAS = {
    "axm.framestate.audio-manifest/v0.8",
    "axm.framestate.audio-manifest/v0.9",
}


class RenderVerificationError(ValueError):
    """A caller-pinned render output cannot be admitted as intact evidence."""


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise RenderVerificationError(f"{label} must be a sha256 digest")
    return value


def _stable_regular_file(path: Path) -> tuple[int, int, int, int, int]:
    try:
        before = path.lstat()
    except OSError as exc:
        raise RenderVerificationError(f"missing evidence file: {path.name}") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise RenderVerificationError(
            f"evidence path must be a regular non-symlink file: {path.name}"
        )
    return (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )


def _confirm_stable_file(
    path: Path,
    before: tuple[int, int, int, int, int],
    opened: os.stat_result,
) -> None:
    try:
        after = path.lstat()
    except OSError as exc:
        raise RenderVerificationError(
            f"evidence file changed while verifying: {path.name}"
        ) from exc
    opened_id = (
        opened.st_dev,
        opened.st_ino,
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_ctime_ns,
    )
    after_id = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or before != opened_id
        or before != after_id
    ):
        raise RenderVerificationError(
            f"evidence file changed while verifying: {path.name}"
        )


def _read_stable(path: Path, *, limit: int = _METADATA_LIMIT) -> bytes:
    before = _stable_regular_file(path)
    if before[2] > limit:
        raise RenderVerificationError(
            f"evidence metadata exceeds {limit} bytes: {path.name}"
        )
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(limit + 1)
            closed = os.fstat(handle.fileno())
    except OSError as exc:
        raise RenderVerificationError(f"cannot read evidence file: {path.name}") from exc
    if len(raw) > limit:
        raise RenderVerificationError(
            f"evidence metadata exceeds {limit} bytes: {path.name}"
        )
    _confirm_stable_file(path, before, opened)
    closed_id = (
        closed.st_dev,
        closed.st_ino,
        closed.st_size,
        closed.st_mtime_ns,
        closed.st_ctime_ns,
    )
    if closed_id != before:
        raise RenderVerificationError(
            f"evidence file changed while verifying: {path.name}"
        )
    return raw


def _hash_stable(path: Path) -> str:
    before = _stable_regular_file(path)
    hashed = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                hashed.update(chunk)
            closed = os.fstat(handle.fileno())
    except OSError as exc:
        raise RenderVerificationError(f"cannot read evidence file: {path.name}") from exc
    _confirm_stable_file(path, before, opened)
    closed_id = (
        closed.st_dev,
        closed.st_ino,
        closed.st_size,
        closed.st_mtime_ns,
        closed.st_ctime_ns,
    )
    if closed_id != before:
        raise RenderVerificationError(
            f"evidence file changed while verifying: {path.name}"
        )
    return "sha256:" + hashed.hexdigest()


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RenderVerificationError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise RenderVerificationError(f"non-finite JSON number: {value}")


def _read_canonical_json(path: Path) -> dict[str, Any]:
    raw = _read_stable(path)
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_constant=_reject_constant,
        )
    except RenderVerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RenderVerificationError(f"invalid JSON evidence: {path.name}") from exc
    if not isinstance(value, dict):
        raise RenderVerificationError(
            f"evidence document must be an object: {path.name}"
        )
    try:
        encoded = canonical_json(value) + b"\n"
    except (TypeError, ValueError, RecursionError) as exc:
        raise RenderVerificationError(
            f"non-canonical JSON evidence: {path.name}"
        ) from exc
    if raw != encoded:
        raise RenderVerificationError(
            f"evidence document is not canonical JSON: {path.name}"
        )
    return value


def _verify_embedded_digest(value: dict[str, Any], field: str, label: str) -> str:
    actual = _require_digest(value.get(field), f"{label} {field}")
    core = copy.deepcopy(value)
    core.pop(field, None)
    if digest(core) != actual:
        raise RenderVerificationError(f"{label} digest does not match its content")
    return actual


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise RenderVerificationError(f"{label} mismatch")


def _require_real_directory(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise RenderVerificationError(f"{label} directory is missing") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise RenderVerificationError(f"{label} must be a non-symlink directory")


def verify_render_output(
    output_dir: Path,
    *,
    expected_receipt_digest: str,
    expected_project_digest: str,
) -> dict[str, Any]:
    """Verify completed local render evidence without rerendering or acquiring authority."""
    receipt_pin = _require_digest(expected_receipt_digest, "caller receipt pin")
    project_pin = _require_digest(expected_project_digest, "caller project pin")
    output = Path(output_dir)
    _require_real_directory(output, "render output")

    receipt = _read_canonical_json(output / "render-receipt.json")
    if receipt.get("schema") not in _RECEIPT_SCHEMAS:
        raise RenderVerificationError("render receipt schema is unsupported")
    recorded_receipt_digest = _require_digest(
        receipt.get("receipt_digest"), "render receipt digest"
    )
    receipt_core = copy.deepcopy(receipt)
    receipt_core.pop("receipt_digest", None)
    if _stable_receipt_digest(receipt_core) != recorded_receipt_digest:
        raise RenderVerificationError("render receipt digest does not match its content")
    _require_equal(recorded_receipt_digest, receipt_pin, "caller receipt pin")
    _require_equal(receipt.get("project_digest"), project_pin, "caller project pin")

    media = _read_canonical_json(output / "media-manifest.json")
    if media.get("schema") not in _MEDIA_SCHEMAS:
        raise RenderVerificationError("media manifest schema is unsupported")
    media_digest = _verify_embedded_digest(media, "manifest_digest", "media manifest")
    _require_equal(
        receipt.get("media_manifest_digest"),
        media_digest,
        "receipt media manifest binding",
    )

    frame_manifest = _read_canonical_json(output / "frame-manifest.json")
    expected_frame_schema = (
        "axm.framestate.frame-manifest/v0.6"
        if receipt.get("schema") == "axm.framestate.render-receipt/v0.10"
        else "axm.framestate.frame-manifest/v0.4"
    )
    if frame_manifest.get("schema") != expected_frame_schema:
        raise RenderVerificationError(
            "frame manifest schema is unsupported for this receipt"
        )
    frame_manifest_digest = _verify_embedded_digest(
        frame_manifest, "manifest_digest", "frame manifest"
    )
    _require_equal(
        receipt.get("frame_manifest_digest"),
        frame_manifest_digest,
        "receipt frame manifest binding",
    )
    _require_equal(
        frame_manifest.get("project_digest"),
        project_pin,
        "frame manifest project binding",
    )
    _require_equal(
        frame_manifest.get("media_manifest_digest"),
        media_digest,
        "frame manifest media binding",
    )

    states = frame_manifest.get("states")
    files = frame_manifest.get("files")
    frame_count = frame_manifest.get("frame_count")
    if (
        isinstance(frame_count, bool)
        or not isinstance(frame_count, int)
        or frame_count < 0
    ):
        raise RenderVerificationError("frame count is invalid")
    if (
        not isinstance(states, list)
        or not isinstance(files, list)
        or len(states) != frame_count
        or len(files) != frame_count
    ):
        raise RenderVerificationError(
            "frame manifest count does not match states and files"
        )

    frames_dir = output / "frames"
    _require_real_directory(frames_dir, "frames")
    expected_names: list[str] = []
    for index, state_value in enumerate(states):
        if not isinstance(state_value, dict) or state_value.get("frame") != index:
            raise RenderVerificationError(f"frame state sequence mismatch at {index}")
        _verify_embedded_digest(state_value, "state_digest", f"frame state {index}")
    for index, file_value in enumerate(files):
        expected_name = f"frame-{index:06d}.ppm"
        if (
            not isinstance(file_value, dict)
            or set(file_value) != {"path", "digest"}
            or file_value.get("path") != expected_name
        ):
            raise RenderVerificationError(f"frame file sequence mismatch at {index}")
        expected_digest = _require_digest(
            file_value.get("digest"), f"frame {index} digest"
        )
        if _hash_stable(frames_dir / expected_name) != expected_digest:
            raise RenderVerificationError(f"frame digest mismatch at {index}")
        expected_names.append(expected_name)
    try:
        frame_names = sorted(item.name for item in frames_dir.iterdir())
    except OSError as exc:
        raise RenderVerificationError("frame inventory cannot be read") from exc
    if frame_names != expected_names:
        raise RenderVerificationError("frame inventory does not match manifest")

    audio = receipt.get("audio_manifest")
    if not isinstance(audio, dict):
        raise RenderVerificationError("audio manifest is missing from receipt")
    if audio.get("schema") not in _AUDIO_SCHEMAS:
        raise RenderVerificationError("audio manifest schema is unsupported")
    audio_manifest_digest = _verify_embedded_digest(
        audio, "manifest_digest", "audio manifest"
    )
    audio_digest = _require_digest(audio.get("wav_digest"), "audio digest")
    if _hash_stable(output / "audio.wav") != audio_digest:
        raise RenderVerificationError("audio digest mismatch")

    subtitle = receipt.get("subtitle_export")
    if not isinstance(subtitle, dict):
        raise RenderVerificationError("subtitle export is missing from receipt")
    if subtitle.get("schema") != "axm.framestate.subtitle-export/v0.1":
        raise RenderVerificationError("subtitle export schema is unsupported")
    caption_digest = _require_digest(subtitle.get("digest"), "caption digest")
    if _hash_stable(output / "captions.vtt") != caption_digest:
        raise RenderVerificationError("caption digest mismatch")

    video = receipt.get("video")
    video_digest: str | None = None
    video_path = output / "video.mp4"
    if video is None:
        if video_path.exists() or video_path.is_symlink():
            raise RenderVerificationError("unreceipted video is present")
    elif isinstance(video, dict):
        video_digest = _require_digest(video.get("digest"), "video digest")
        if _hash_stable(video_path) != video_digest:
            raise RenderVerificationError("video digest mismatch")
        assembly = receipt.get("assembly")
        if not isinstance(assembly, dict) or assembly.get("succeeded") is not True:
            raise RenderVerificationError(
                "video exists without successful assembly evidence"
            )
    else:
        raise RenderVerificationError("video receipt must be an object or null")

    realization_contract_digest: str | None = None
    realization = receipt.get("realization")
    if receipt.get("schema") == "axm.framestate.render-receipt/v0.10":
        if not isinstance(realization, dict):
            raise RenderVerificationError("realization evidence is missing")
        machine = _read_canonical_json(output / "machine-capabilities.json")
        policy = _read_canonical_json(output / "realization-policy.json")
        contract = _read_canonical_json(output / "realization-contract.json")
        if machine.get("schema") != "axm.framestate.machine-capabilities/v0.1":
            raise RenderVerificationError("machine capability schema is unsupported")
        if policy.get("schema") != "axm.framestate.realization-policy/v0.2":
            raise RenderVerificationError("realization policy schema is unsupported")
        if contract.get("schema") != "axm.framestate.render-contract/v0.2":
            raise RenderVerificationError("realization contract schema is unsupported")
        machine_digest = _verify_embedded_digest(
            machine, "capability_digest", "machine capability"
        )
        policy_digest = _verify_embedded_digest(
            policy, "policy_digest", "realization policy"
        )
        realization_contract_digest = _verify_embedded_digest(
            contract, "contract_digest", "realization contract"
        )
        _require_equal(
            realization.get("machine_capability_digest"),
            machine_digest,
            "receipt machine capability binding",
        )
        _require_equal(
            realization.get("policy_digest"),
            policy_digest,
            "receipt realization policy binding",
        )
        _require_equal(
            realization.get("contract_digest"),
            realization_contract_digest,
            "receipt realization contract binding",
        )
        _require_equal(
            contract.get("canonical_project_digest"),
            project_pin,
            "realization contract project binding",
        )
        _require_equal(
            contract.get("machine_capability_digest"),
            machine_digest,
            "contract machine capability binding",
        )
        _require_equal(
            contract.get("policy_digest"),
            policy_digest,
            "contract policy binding",
        )
        _require_equal(
            frame_manifest.get("realization_contract_digest"),
            realization_contract_digest,
            "frame manifest realization binding",
        )
        for key in (
            "tier",
            "backend",
            "render",
            "fidelity",
            "fidelity_limited",
            "expression_deltas",
        ):
            _require_equal(
                realization.get(key),
                contract.get(key),
                f"receipt realization {key} binding",
            )
    elif realization is not None:
        raise RenderVerificationError(
            "legacy receipt contains unexpected realization evidence"
        )

    result = {
        "schema": "axm.framestate.render-output-verification/v0.1",
        "verified": True,
        "receipt_digest": recorded_receipt_digest,
        "project_digest": project_pin,
        "media_manifest_digest": media_digest,
        "frame_manifest_digest": frame_manifest_digest,
        "frame_count": frame_count,
        "audio_manifest_digest": audio_manifest_digest,
        "audio_wav_digest": audio_digest,
        "caption_digest": caption_digest,
        "video_digest": video_digest,
        "realization_contract_digest": realization_contract_digest,
        "authority": "EVIDENCE_ADMISSION_ONLY",
        "truth_boundary": (
            "verifies caller-pinned receipt identity and current local render bytes "
            "without rerendering; does not grant canonical project, merge, publication, "
            "or CANON authority"
        ),
    }
    result["verification_digest"] = digest(result)
    return result
