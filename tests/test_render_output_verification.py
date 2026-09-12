from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import canonical_json, load_project
from axm_framestate.receipts import (
    _stable_receipt_digest,
    render_realized_with_receipt,
    render_with_receipt,
)
from axm_framestate.render_verify import RenderVerificationError, verify_render_output


ROOT = Path(__file__).resolve().parents[1]


class RenderOutputVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = load_project(ROOT / "examples" / "first_light.json")

    def render(self, root: Path) -> tuple[Path, dict]:
        output = root / "render"
        receipt = render_with_receipt(self.project, output, ROOT, assemble=False)
        return output, receipt

    def verify(self, output: Path, receipt: dict) -> dict:
        return verify_render_output(
            output,
            expected_receipt_digest=receipt["receipt_digest"],
            expected_project_digest=receipt["project_digest"],
        )

    def test_exact_render_output_round_trips_through_caller_pins(self):
        with tempfile.TemporaryDirectory() as raw:
            output, receipt = self.render(Path(raw))
            result = self.verify(output, receipt)
            self.assertTrue(result["verified"])
            self.assertEqual(result["receipt_digest"], receipt["receipt_digest"])
            self.assertEqual(result["project_digest"], receipt["project_digest"])
            self.assertEqual(result["frame_count"], self.project["duration_frames"])
            self.assertEqual(result["authority"], "EVIDENCE_ADMISSION_ONLY")

    def test_changed_frame_is_rejected_without_rewriting_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            output, receipt = self.render(Path(raw))
            receipt_path = output / "render-receipt.json"
            original_receipt = receipt_path.read_bytes()
            frame = output / "frames" / "frame-000000.ppm"
            frame.write_bytes(frame.read_bytes() + b"changed")
            with self.assertRaisesRegex(RenderVerificationError, "frame digest"):
                self.verify(output, receipt)
            self.assertEqual(receipt_path.read_bytes(), original_receipt)

    def test_unreceipted_stale_frame_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            output, receipt = self.render(Path(raw))
            stale = output / "frames" / "frame-999999.ppm"
            stale.write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")
            with self.assertRaisesRegex(RenderVerificationError, "frame inventory"):
                self.verify(output, receipt)

    def test_changed_audio_and_captions_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            output, receipt = self.render(Path(raw))
            audio = output / "audio.wav"
            audio.write_bytes(audio.read_bytes() + b"changed")
            with self.assertRaisesRegex(RenderVerificationError, "audio digest"):
                self.verify(output, receipt)

        with tempfile.TemporaryDirectory() as raw:
            output, receipt = self.render(Path(raw))
            captions = output / "captions.vtt"
            captions.write_text("WEBVTT\n\nchanged\n", encoding="utf-8")
            with self.assertRaisesRegex(RenderVerificationError, "caption digest"):
                self.verify(output, receipt)

    def test_self_consistently_resealed_receipt_cannot_replace_caller_pin(self):
        with tempfile.TemporaryDirectory() as raw:
            output, receipt = self.render(Path(raw))
            receipt_path = output / "render-receipt.json"
            changed = json.loads(receipt_path.read_text(encoding="utf-8"))
            changed["project_id"] = "substituted"
            changed.pop("receipt_digest")
            changed["receipt_digest"] = _stable_receipt_digest(changed)
            receipt_path.write_bytes(canonical_json(changed) + b"\n")
            with self.assertRaisesRegex(RenderVerificationError, "caller receipt pin"):
                self.verify(output, receipt)

    def test_realized_render_contract_is_admitted(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / "realized"
            machine = json.loads(
                (ROOT / "examples" / "machine_high.json").read_text(encoding="utf-8")
            )
            policy = json.loads(
                (ROOT / "examples" / "realization_policy.json").read_text(encoding="utf-8")
            )
            receipt = render_realized_with_receipt(
                self.project, output, ROOT, machine, policy, assemble=False
            )
            result = self.verify(output, receipt)
            self.assertEqual(
                result["realization_contract_digest"],
                receipt["realization"]["contract_digest"],
            )


if __name__ == "__main__":
    unittest.main()
