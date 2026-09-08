from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from axm_framestate.canonical import digest
from axm_framestate.semantic import (
    DIRECTION_SCHEMA,
    RESPONSE_SCHEMA,
    SemanticError,
    semantic_request,
    stage_semantic_candidate,
)
from axm_framestate.studio import default_project


def direction():
    return {"schema": DIRECTION_SCHEMA, "id": "mood-1", "text": "Make this scene feel lonely but readable."}


def response_for(project, *, title="Lonely candidate"):
    request = semantic_request(project, direction())
    candidate = json.loads(json.dumps(project))
    candidate["title"] = title
    candidate["background"] = [4, 8, 18]
    return {
        "schema": RESPONSE_SCHEMA,
        "input_project_digest": request["project_digest"],
        "direction_text_digest": request["direction_text_digest"],
        "translator": {"id": "fixture-translator", "version": "1", "implementation": "test-fixture", "model": "none"},
        "candidate_project": candidate,
        "rationale": "A bounded test proposal, not an artistic truth claim.",
        "assumptions": ["dark blue is only a proposal"],
    }


class SemanticTests(unittest.TestCase):
    def test_precomputed_response_stages_candidate_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = default_project()
            before = digest(project)
            receipt = stage_semantic_candidate(project, direction(), root / "stage", root, response=response_for(project), response_source_digest="sha256:fixture")
            self.assertEqual(digest(project), before)
            self.assertTrue(receipt["candidate_changed"])
            self.assertFalse(receipt["automatic_canonical_write"])
            self.assertIn("$.title", receipt["changed_paths"])
            candidate = json.loads((root / "stage" / "semantic-candidate-project.json").read_text(encoding="utf-8"))
            self.assertEqual(candidate["title"], "Lonely candidate")
            self.assertNotEqual(receipt["candidate_project_digest"], before)

    def test_stale_semantic_response_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            project = default_project()
            response = response_for(project)
            response["input_project_digest"] = "sha256:" + "0" * 64
            with self.assertRaises(SemanticError):
                stage_semantic_candidate(project, direction(), Path(td) / "stage", Path(td), response=response)

    def test_external_translator_is_attributed_and_command_arguments_are_not_receipted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            script = root / "translator.py"
            script.write_text(
                "import json,sys\n"
                "r=json.loads(sys.stdin.read())\n"
                "p=r['project']; p['title']='External semantic candidate'\n"
                "out={'schema':'axm.framestate.semantic-response/v0.1','input_project_digest':r['project_digest'],'direction_text_digest':r['direction_text_digest'],'translator':{'id':'fake-local','version':'0.1','implementation':'python-fixture'},'candidate_project':p,'rationale':'test','assumptions':[]}\n"
                "print(json.dumps(out))\n",
                encoding="utf-8",
            )
            secretish = "DO-NOT-RECEIPT-THIS-ARG"
            config = {
                "schema": "axm.framestate.semantic-translator-command/v0.1",
                "command": [sys.executable, str(script), secretish],
                "timeout_seconds": 30,
            }
            receipt = stage_semantic_candidate(default_project(), direction(), root / "stage", root, translator_config=config)
            self.assertEqual(receipt["translator"]["id"], "fake-local")
            self.assertEqual(receipt["translator_boundary"]["mode"], "external-command")
            self.assertFalse(receipt["translator_boundary"]["command_arguments_recorded"])
            self.assertNotIn(secretish, json.dumps(receipt))
            self.assertEqual(receipt["status"], "STAGED_CHANGED")


if __name__ == "__main__":
    unittest.main()
