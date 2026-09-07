from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path

from axm_framestate.canonical import digest,load_project
from axm_framestate.prompts import apply_prompt_plan,interpret_prompt,prompt_project
from axm_framestate.capabilities import analyze_requirements

ROOT=Path(__file__).resolve().parents[1]

class PromptFabricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'examples'/'make_demo_media.py')],check=True,capture_output=True)

    def test_same_prompt_same_plan_and_candidate(self):
        p=load_project(ROOT/'examples'/'first_light.json');raw=json.loads((ROOT/'examples'/'prompt_cinematic.json').read_text())
        a=interpret_prompt(p,raw);b=interpret_prompt(p,raw)
        self.assertEqual(a['plan_digest'],b['plan_digest'])
        self.assertEqual(digest(apply_prompt_plan(p,a)['project']),digest(apply_prompt_plan(p,b)['project']))
        self.assertIn('cinematic',[r['token'] for r in a['recognized']])

    def test_ambiguous_semantic_prompt_holds_without_state_operation(self):
        p=load_project(ROOT/'examples'/'first_light.json');raw=json.loads((ROOT/'examples'/'prompt_ambiguous.json').read_text())
        plan=interpret_prompt(p,raw);self.assertEqual(plan['status'],'HELD_AMBIGUOUS');self.assertFalse(plan['operations'])
        self.assertEqual({'cooler','dramatic'},{x['term'] for x in plan['ambiguous']})
        candidate=apply_prompt_plan(p,plan)['project']
        a=copy.deepcopy(p);b=copy.deepcopy(candidate);a['metadata']={};b['metadata']={}
        self.assertEqual(digest(a),digest(b))

    def test_direct_edits_change_native_state(self):
        from axm_framestate.director import compile_brief
        brief=json.loads((ROOT/'examples'/'creative_brief.json').read_text());p=compile_brief(brief,ROOT)
        raw=json.loads((ROOT/'examples'/'prompt_direct.json').read_text());plan=interpret_prompt(p,raw);candidate=apply_prompt_plan(p,plan)['project']
        old_title=next(l for l in p['layers'] if l['kind']=='text');new_title=next(l for l in candidate['layers'] if l['id']==old_title['id'])
        self.assertGreater(new_title['scale'],old_title['scale'])
        non_speech_before=next(a for a in p['audio'] if a['kind']!='speech');non_speech_after=next(a for a in candidate['audio'] if a['id']==non_speech_before['id'])
        old_gain=non_speech_before['gain_milli']['from'] if isinstance(non_speech_before['gain_milli'],dict) else non_speech_before['gain_milli']
        new_gain=non_speech_after['gain_milli']['from'] if isinstance(non_speech_after['gain_milli'],dict) else non_speech_after['gain_milli']
        self.assertLess(new_gain,old_gain)
        self.assertTrue(all(c['end_frame']>=o['end_frame'] for c,o in zip(candidate['captions'],p['captions'])))

    def test_prompt_make_bridges_to_rehearsal_and_repeat(self):
        from axm_framestate.director import compile_brief
        brief=json.loads((ROOT/'examples'/'rehearsal_brief_compact.json').read_text());project=compile_brief(brief,ROOT)
        raw={'schema':'axm.framestate.prompt/v0.1','id':'readable-cinematic','text':'Make it cinematic and more readable','allow_classes':['direct','style','semantic'],'ambiguity_policy':'hold','scope':'all'}
        with tempfile.TemporaryDirectory() as td:
            r=prompt_project(project,raw,Path(td),ROOT,rehearse=True,verify_final=True)
            self.assertTrue(r['rehearsed']);self.assertIsNotNone(r['rehearsal_receipt_digest']);self.assertTrue(r['final_repeat_verification']['passed'])
            self.assertIn('cinematic',r['recognized_tokens']);self.assertIn('more-readable',r['recognized_tokens'])

    def test_prompt_capabilities_ready(self):
        req=json.loads((ROOT/'examples'/'prompt_requirements.json').read_text())['required'];self.assertTrue(analyze_requirements(req)['ready'])

if __name__=='__main__':unittest.main()
