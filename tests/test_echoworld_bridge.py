from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from axm_framestate.echoworld_bridge import (
    EchoWorldBridgeError,
    create_echoworld_visual_projection,
    load_receipt_file,
    verify_echoworld_visual_projection,
)


def _canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _ordered_bytes(value):
    return json.dumps(
        value, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def make_receipt():
    width = 5
    height = 5
    cells = {}
    for y in range(height):
        for x in range(width):
            cid = f"C_{x}_{y}"
            occupants = []
            if (x, y) == (1, 1):
                occupants = ["A"]
            elif (x, y) == (4, 1):
                occupants = ["B"]
            truth_type = "structure" if (x, y) == (2, 1) else "terrain"
            material = "bridge" if (x, y) == (2, 1) else "ground"
            properties = {"integrity": 75} if (x, y) == (2, 1) else {}
            cells[cid] = {
                "cellId": cid,
                "x": x,
                "y": y,
                "canonicalRevision": 1 if (x, y) == (2, 1) else 0,
                "truthState": {
                    "type": truth_type,
                    "material": material,
                    "occupants": occupants,
                    "properties": properties,
                },
            }
    world = {
        "schema": "axm.echoworld/v0.01",
        "width": width,
        "height": height,
        "revision": 1,
        "cells": cells,
        "actors": {
            "A": {"actorId": "A", "x": 1, "y": 1},
            "B": {"actorId": "B", "x": 4, "y": 1},
        },
    }
    final_hash = _sha(_ordered_bytes(world))
    input_doc = {
        "schema": "axm.echoworld.event-stream/v0.01",
        "width": width,
        "height": height,
        "events": [
            {
                "eventId": "DAMAGE_1",
                "type": "DAMAGE_STRUCTURE",
                "actorId": "A",
                "cellId": "C_2_1",
                "amount": 25,
            }
        ],
    }
    run = {
        "memoryEnabled": False,
        "events": [
            {
                "eventId": "DAMAGE_1",
                "committed": True,
                "reason": None,
                "revision": 1,
                "canonicalHash": final_hash,
                "affectedCellIds": ["C_2_1"],
            }
        ],
        "finalRevision": 1,
        "finalCanonicalHash": final_hash,
        "truthReceiptCount": 1,
        "memoryReceiptCount": 0,
        "handoffReceiptCount": 0,
    }
    run_with_memory = copy.deepcopy(run)
    run_with_memory["memoryEnabled"] = True
    payload = {
        "schema": "axm.echoworld.portable-replay/v0.01",
        "provider": {
            "id": "axm.echoworld.deterministic-event-replay",
            "version": "0.1.0",
        },
        "inputHash": _sha(_canonical_bytes(input_doc)),
        "input": input_doc,
        "memoryDisabled": run,
        "memoryEnabled": run_with_memory,
        "canonicalEquivalent": True,
        "finalCanonicalState": world,
        "authority": {
            "canonical": False,
            "authorshipVerified": False,
            "physicalRealismProven": False,
            "automaticMerge": False,
        },
    }
    return {**payload, "receiptHash": _sha(_canonical_bytes(payload))}


class EchoWorldBridgeTests(unittest.TestCase):
    def test_projection_is_deterministic_and_frame_state_valid(self):
        receipt = make_receipt()
        first = create_echoworld_visual_projection(
            receipt, expected_receipt_hash=receipt["receiptHash"]
        )
        second = create_echoworld_visual_projection(
            copy.deepcopy(receipt), expected_receipt_hash=receipt["receiptHash"]
        )
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "READY_FOR_RENDER")
        self.assertEqual(first["project"]["schema"], "axm.framestate.project/v0.5")
        self.assertEqual(first["project"]["canvas"], {"width": 40, "height": 40, "fps": 1})
        self.assertEqual(len(first["project"]["layers"]), 27)
        self.assertFalse(any(first["authority"].values()))
        self.assertIn("sha256:", first["projectDigest"])

    def test_exact_caller_owned_receipt_pin_is_required(self):
        receipt = make_receipt()
        with self.assertRaisesRegex(EchoWorldBridgeError, "RECEIPT_PIN_MISMATCH"):
            create_echoworld_visual_projection(
                receipt, expected_receipt_hash="0" * 64
            )

    def test_source_receipt_tamper_fails_integrity(self):
        receipt = make_receipt()
        pinned = receipt["receiptHash"]
        receipt["finalCanonicalState"]["cells"]["C_2_1"]["truthState"]["properties"]["integrity"] = 74
        with self.assertRaisesRegex(EchoWorldBridgeError, "RECEIPT_INTEGRITY_MISMATCH"):
            create_echoworld_visual_projection(receipt, expected_receipt_hash=pinned)

    def test_resealed_source_authority_widening_still_fails_closed(self):
        receipt = make_receipt()
        receipt["authority"]["canonical"] = True
        unsigned = {key: value for key, value in receipt.items() if key != "receiptHash"}
        receipt["receiptHash"] = _sha(_canonical_bytes(unsigned))
        with self.assertRaisesRegex(EchoWorldBridgeError, "SOURCE_AUTHORITY_WIDENED"):
            create_echoworld_visual_projection(
                receipt, expected_receipt_hash=receipt["receiptHash"]
            )

    def test_actor_occupancy_mismatch_is_rejected_even_if_resealed(self):
        receipt = make_receipt()
        receipt["finalCanonicalState"]["cells"]["C_1_1"]["truthState"]["occupants"] = []
        unsigned = {key: value for key, value in receipt.items() if key != "receiptHash"}
        receipt["receiptHash"] = _sha(_canonical_bytes(unsigned))
        with self.assertRaisesRegex(EchoWorldBridgeError, "FINAL_STATE_HASH_MISMATCH|ACTOR_OCCUPANCY_MISMATCH"):
            create_echoworld_visual_projection(
                receipt, expected_receipt_hash=receipt["receiptHash"]
            )

    def test_projection_tamper_is_detected_by_recomputation(self):
        receipt = make_receipt()
        projection = create_echoworld_visual_projection(
            receipt, expected_receipt_hash=receipt["receiptHash"]
        )
        projection["project"]["background"] = [0, 0, 0]
        with self.assertRaisesRegex(EchoWorldBridgeError, "PROJECTION_MISMATCH"):
            verify_echoworld_visual_projection(
                receipt,
                projection,
                expected_receipt_hash=receipt["receiptHash"],
            )

    def test_file_loader_rejects_duplicate_keys_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(EchoWorldBridgeError, "DUPLICATE_JSON_KEY"):
                load_receipt_file(path)
            path.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(EchoWorldBridgeError, "NON_FINITE_JSON"):
                load_receipt_file(path)


if __name__ == "__main__":
    unittest.main()
