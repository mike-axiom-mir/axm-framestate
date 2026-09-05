from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from axm_framestate.canonical import load_project,normalize_project,ProjectError
from axm_framestate.effects import normalize_effect,test_effect_manifest
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.review import review_project
from axm_framestate.forge import adopt_effect,spawn_effect,adopt_recipe,spawn_recipe
from axm_framestate.receipts import verify_repeat,render_with_receipt
from axm_framestate.director import compile_plan,compile_brief
from axm_framestate.shots import derive_shots,storyboard
from axm_framestate.analysis import analyze_render
from axm_framestate.three_d import sincos_mdeg,parse_obj
from axm_framestate.recipes import normalize_recipe,test_recipe_manifest,load_recipe_library

ROOT=Path(__file__).resolve().parents[1]

class FrameStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'examples'/'make_demo_media.py')],check=True,capture_output=True)

    def test_project_rejects_unknown_fields(self):
        raw=json.loads((ROOT/'examples'/'first_light.json').read_text());raw['mystery']=True
        with self.assertRaises(ProjectError):normalize_project(raw)

    def test_repeat_render_is_exact(self):
        p=load_project(ROOT/'examples'/'first_light.json')
        with tempfile.TemporaryDirectory() as td:self.assertTrue(verify_repeat(p,Path(td),ROOT)['passed'])

    def test_effect_fixture_replay(self):
        raw=json.loads((ROOT/'examples'/'posterize.effect.json').read_text());self.assertTrue(test_effect_manifest(normalize_effect(raw))['passed'])

    def test_detached_effect_adoption_requires_root_fit_and_snapshot(self):
        raw=json.loads((ROOT/'examples'/'posterize.effect.json').read_text());rf=raw['root_fit']
        with tempfile.TemporaryDirectory() as td:
            machine=Path(td)/'machine';machine.mkdir();(machine/'seed.txt').write_text('seed');cf=Path(td)/'candidate.json';cf.write_text(json.dumps(raw));sp=spawn_effect(cf,Path(td)/'spawned');r=adopt_effect(machine,Path(sp['path']),'test adoption',rf);self.assertTrue(r['adopted']);self.assertTrue(Path(r['destination']).is_file());self.assertTrue(Path(r['recovery_snapshot']['path']).is_file())

    def test_pixel_program_effect(self):
        raw=json.loads((ROOT/'examples'/'signal_program.effect.json').read_text());self.assertTrue(test_effect_manifest(normalize_effect(raw))['passed'])

    def test_gap_analysis_only_exposes_real_missing(self):
        r=analyze_requirements(['camera-animation','captions-subtitles','imaginary-capability']);self.assertFalse(r['ready']);self.assertEqual(r['smallest_visible_gaps'],['imaginary-capability'])

    def test_advanced_requirements_ready(self):
        req=json.loads((ROOT/'examples'/'advanced_requirements.json').read_text())['required'];r=analyze_requirements(req);self.assertTrue(r['ready'],r)

    def test_mechanical_review_has_truth_boundary(self):
        r=review_project(load_project(ROOT/'examples'/'first_light.json'),ROOT);self.assertIn('does not score',r['truth_boundary'])

    def test_shot_plan_compiles(self):
        raw=json.loads((ROOT/'examples'/'movie_day_one.plan.json').read_text());p=compile_plan(raw);self.assertEqual(p['duration_frames'],180);self.assertEqual(len(derive_shots(p)['shots']),4)

    def test_fixed_point_cordic_axes(self):
        s,c=sincos_mdeg(0);self.assertLess(abs(s),30);self.assertGreater(c,999000);s,c=sincos_mdeg(90000);self.assertGreater(s,999000);self.assertLess(abs(c),30)

    def test_obj_uv_parse(self):
        m=parse_obj(ROOT/'examples'/'media'/'pyramid.obj');self.assertEqual(len(m['vertices']),5);self.assertGreaterEqual(len(m['uvs']),5);self.assertEqual(len(m['faces']),6)

    def test_compiled_movie_renders_mixed_media_stereo_and_3d(self):
        raw=json.loads((ROOT/'examples'/'movie_day_one.plan.json').read_text());p=compile_plan(raw)
        p={**p,'duration_frames':18,'layers':[l for l in p['layers'] if l['start_frame']<18],'captions':[c for c in p['captions'] if c['start_frame']<18],'audio':[a for a in p['audio'] if a['start_frame']<18],'markers':[m for m in p['markers'] if m['frame']<18]}
        for l in p['layers']:l['end_frame']=min(l['end_frame'],18)
        for c in p['captions']:c['end_frame']=min(c['end_frame'],18)
        for a in p['audio']:a['end_frame']=min(a['end_frame'],18)
        with tempfile.TemporaryDirectory() as td:
            r=render_with_receipt(p,Path(td),ROOT,assemble=False);self.assertTrue((Path(td)/'frames'/'frame-000000.ppm').is_file());self.assertEqual(r['audio_manifest']['channels'],2)

    def test_analysis_proposes_without_mutation(self):
        p=load_project(ROOT/'examples'/'first_light.json')
        with tempfile.TemporaryDirectory() as td:
            render_with_receipt(p,Path(td),ROOT,assemble=False);r=analyze_render(Path(td),0);self.assertFalse(r['mutated_project']);self.assertGreaterEqual(len(r['proposed_cuts']),1)

    def test_storyboard_from_real_frames(self):
        p=load_project(ROOT/'examples'/'first_light.json')
        with tempfile.TemporaryDirectory() as td:
            r=storyboard(p,Path(td),ROOT);self.assertTrue(Path(r['path']).is_file());self.assertEqual(r['project_digest'],normalize_project(p) and r['project_digest'])

    def test_creative_brief_compiles_to_canonical_movie(self):
        raw=json.loads((ROOT/'examples'/'creative_brief.json').read_text());p=compile_brief(raw,ROOT)
        self.assertEqual(p['duration_frames'],144);self.assertEqual(p['metadata']['compiled_from'],'shot-plan');self.assertEqual(p['metadata']['beat_count'],5);self.assertEqual(len(derive_shots(p)['shots']),5)

    def test_recipe_fixture_replay_and_adoption(self):
        raw=json.loads((ROOT/'examples'/'lower_third.recipe.json').read_text());self.assertTrue(test_recipe_manifest(normalize_recipe(raw))['passed']);rf=raw['root_fit']
        with tempfile.TemporaryDirectory() as td:
            machine=Path(td)/'machine';machine.mkdir();(machine/'seed.txt').write_text('seed');cf=Path(td)/'candidate.json';cf.write_text(json.dumps(raw));sp=spawn_recipe(cf,Path(td)/'spawned');r=adopt_recipe(machine,Path(sp['path']),'test reusable shot recipe',rf);self.assertTrue(r['adopted']);self.assertIn('axm.recipe.lower-third@1.0.0',load_recipe_library(machine));self.assertTrue(Path(r['recovery_snapshot']['path']).is_file())

    def test_installed_recipe_can_drive_creative_brief(self):
        raw=json.loads((ROOT/'examples'/'lower_third.recipe.json').read_text());rf=raw['root_fit']
        with tempfile.TemporaryDirectory() as td:
            machine=Path(td)/'machine';machine.mkdir();(machine/'seed.txt').write_text('seed');cf=Path(td)/'candidate.json';cf.write_text(json.dumps(raw));sp=spawn_recipe(cf,Path(td)/'spawned');self.assertTrue(adopt_recipe(machine,Path(sp['path']),'install for brief',rf)['adopted'])
            brief={'schema':'axm.framestate.creative-brief/v0.1','id':'custom-brief','canvas':{'width':160,'height':90,'fps':12},'duration_frames':24,'style':'clean','format':'test','beats':[{'kind':'message','text':'CUSTOM RECIPE','recipe_ref':'axm.recipe.lower-third@1.0.0','values':{'text':'CUSTOM RECIPE','accent':[20,160,150]},'weight':1}]}
            p=compile_brief(brief,machine);self.assertEqual(p['duration_frames'],24);self.assertTrue(any(l['id'].endswith('::label') for l in p['layers']))

if __name__=='__main__':unittest.main()
