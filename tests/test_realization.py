from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path

from axm_framestate.canonical import digest,load_project
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.realization import normalize_machine_capabilities,plan_realization,verify_contract
from axm_framestate.receipts import render_realized_with_receipt,verify_realized_repeat,render_with_receipt

ROOT=Path(__file__).resolve().parents[1]


def fixture(name:str):
    return json.loads((ROOT/'examples'/name).read_text(encoding='utf-8'))


def ppm_body(path:Path)->bytes:
    data=path.read_bytes();return data.split(b'\n',3)[3]


class AdaptiveRealizationTests(unittest.TestCase):
    def setUp(self):
        self.project=load_project(ROOT/'examples'/'adaptive_realization.json')
        self.low=fixture('machine_low.json')
        self.high=fixture('machine_high.json')
        self.policy=fixture('realization_policy.json')

    def test_planner_is_deterministic_and_canonical_digest_is_same_across_tiers(self):
        a=plan_realization(self.project,self.low,self.policy);b=plan_realization(self.project,self.low,self.policy);hi=plan_realization(self.project,self.high,self.policy)
        self.assertEqual(a,b);self.assertEqual(a['canonical_project_digest'],digest(self.project));self.assertEqual(hi['canonical_project_digest'],digest(self.project))
        self.assertEqual(a['tier'],'minimum');self.assertEqual(hi['tier'],'high');self.assertNotEqual(a['contract_digest'],hi['contract_digest'])

    def test_low_and_high_change_expression_not_canonical_state(self):
        low=plan_realization(self.project,self.low,self.policy);high=plan_realization(self.project,self.high,self.policy)
        self.assertLess(low['render']['particle_density_milli'],high['render']['particle_density_milli'])
        self.assertFalse(low['render']['shadows_enabled']);self.assertTrue(high['render']['shadows_enabled'])
        self.assertTrue(low['degraded_expression']);self.assertFalse(high['degraded_expression'])
        self.assertTrue(verify_contract(self.project,low)['passed']);self.assertTrue(verify_contract(self.project,high)['passed'])

    def test_user_can_forbid_automatic_visual_degradation(self):
        policy={**self.policy,'mode':'adaptive','allow_particle_reduction':False,'allow_shadow_disable':False}
        c=plan_realization(self.project,self.low,policy)
        self.assertEqual(c['tier'],'minimum');self.assertEqual(c['render']['particle_density_milli'],1000);self.assertTrue(c['render']['shadows_enabled'])
        self.assertEqual(c['expression_deltas'],[]);self.assertFalse(c['degraded_expression'])

    def test_effect_reduction_is_opt_in_and_receipted(self):
        default=plan_realization(self.project,self.low,self.policy);self.assertIsNone(default['render']['effect_pass_limit'])
        policy={**self.policy,'allow_effect_pass_reduction':True,'min_effect_passes':1}
        c=plan_realization(self.project,self.low,policy)
        self.assertEqual(c['render']['effect_pass_limit'],1);self.assertTrue(any(x['capability']=='effect-pass-budget' for x in c['expression_deltas']))

    def test_realized_renders_differ_but_keep_same_project_and_audio_truth(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);lo=render_realized_with_receipt(self.project,td/'low',ROOT,self.low,self.policy,assemble=False);hi=render_realized_with_receipt(self.project,td/'high',ROOT,self.high,self.policy,assemble=False)
            self.assertEqual(lo['project_digest'],hi['project_digest']);self.assertEqual(lo['audio_manifest']['pcm_digest'],hi['audio_manifest']['pcm_digest'])
            self.assertNotEqual(lo['frame_manifest_digest'],hi['frame_manifest_digest'])
            self.assertTrue(lo['realization']['invariants_after']['passed']);self.assertTrue(hi['realization']['invariants_after']['passed'])
            lm=json.loads((td/'low'/'frame-manifest.json').read_text());hm=json.loads((td/'high'/'frame-manifest.json').read_text())
            lpart=next(x for x in lm['states'][0]['visible_layers'] if x['id']=='field');hpart=next(x for x in hm['states'][0]['visible_layers'] if x['id']=='field')
            self.assertLess(lpart['particle_count'],hpart['particle_count'])

    def test_exact_realization_matches_legacy_native_pixels(self):
        exact={**self.policy,'mode':'exact','allow_particle_reduction':False,'allow_shadow_disable':False,'min_internal_sample_scale':1,'max_internal_sample_scale':1,'preferred_texture_filter':'nearest'}
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);legacy=render_with_receipt(self.project,td/'legacy',ROOT,assemble=False);realized=render_realized_with_receipt(self.project,td/'exact',ROOT,self.low,exact,assemble=False)
            lm=json.loads((td/'legacy'/'frame-manifest.json').read_text());rm=json.loads((td/'exact'/'frame-manifest.json').read_text())
            self.assertEqual([x['pixel_digest'] for x in lm['states']],[x['pixel_digest'] for x in rm['states']])
            self.assertEqual(legacy['audio_manifest']['pcm_digest'],realized['audio_manifest']['pcm_digest'])

    def test_same_machine_policy_repeats_realized_output(self):
        with tempfile.TemporaryDirectory() as td:
            r=verify_realized_repeat(self.project,Path(td),ROOT,self.low,self.policy);self.assertTrue(r['passed'],r)

    def test_unknown_memory_is_conservative_and_probe_schema_has_privacy_boundary(self):
        m={**self.high,'memory_mb':0};c=plan_realization(self.project,m,self.policy);self.assertEqual(c['tier'],'minimum')
        n=normalize_machine_capabilities(self.low);self.assertIn('no person/device identity fingerprint',n['probe_scope'])

    def test_capability_map_exposes_v010_floor(self):
        req=fixture('realization_requirements.json')['required'];self.assertTrue(analyze_requirements(req)['ready'])

    def test_fidelity_is_separate_from_detail_density(self):
        lo=plan_realization(self.project,self.low,self.policy);hi=plan_realization(self.project,self.high,self.policy)
        self.assertEqual(lo['canonical_project_digest'],hi['canonical_project_digest'])
        self.assertEqual(lo['render']['internal_sample_scale'],1);self.assertEqual(hi['render']['internal_sample_scale'],2)
        self.assertEqual(lo['render']['texture_filter'],'nearest');self.assertEqual(hi['render']['texture_filter'],'bilinear')
        self.assertEqual(lo['fidelity']['internal_pixel_samples_per_output_pixel'],1);self.assertEqual(hi['fidelity']['internal_pixel_samples_per_output_pixel'],4)

    def test_supersampling_creates_real_edge_fidelity_not_extra_objects(self):
        project=load_project(ROOT/'examples'/'fidelity_probe.json')
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);lo=render_realized_with_receipt(project,td/'low',ROOT,self.low,self.policy,assemble=False);hi=render_realized_with_receipt(project,td/'high',ROOT,self.high,self.policy,assemble=False)
            lb=ppm_body(td/'low'/'frames'/'frame-000000.ppm');hb=ppm_body(td/'high'/'frames'/'frame-000000.ppm')
            low_mid=sum(1 for i in range(0,len(lb),3) if 0<lb[i]<255 and lb[i]==lb[i+1]==lb[i+2])
            high_mid=sum(1 for i in range(0,len(hb),3) if 0<hb[i]<255 and hb[i]==hb[i+1]==hb[i+2])
            self.assertEqual(low_mid,0);self.assertGreater(high_mid,0)
            lm=json.loads((td/'low'/'frame-manifest.json').read_text());hm=json.loads((td/'high'/'frame-manifest.json').read_text())
            self.assertEqual(lm['states'][0]['visible_layers'],hm['states'][0]['visible_layers'])
            self.assertEqual(lo['project_digest'],hi['project_digest'])

    def test_user_can_cap_fidelity_work_independently_of_machine_power(self):
        policy={**self.policy,'max_internal_sample_scale':1,'preferred_texture_filter':'nearest'}
        hi=plan_realization(self.project,self.high,policy)
        self.assertEqual(hi['tier'],'high');self.assertEqual(hi['render']['internal_sample_scale'],1);self.assertEqual(hi['render']['texture_filter'],'nearest')
        self.assertTrue(hi['fidelity_limited'])

    def test_effects_remain_canonical_output_resolution_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);lo=render_realized_with_receipt(self.project,td/'low',ROOT,self.low,self.policy,assemble=False);hi=render_realized_with_receipt(self.project,td/'high',ROOT,self.high,self.policy,assemble=False)
            lm=json.loads((td/'low'/'frame-manifest.json').read_text());hm=json.loads((td/'high'/'frame-manifest.json').read_text())
            self.assertEqual(lm['states'][0]['effects'],hm['states'][0]['effects'])
            self.assertEqual(lm['states'][0]['realization']['skipped_effects'],hm['states'][0]['realization']['skipped_effects'])

if __name__=='__main__':unittest.main()
