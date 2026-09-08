from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path

from axm_framestate.canonical import digest,load_project
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.realization import normalize_machine_capabilities,normalize_realization_policy,plan_realization,verify_contract
from axm_framestate.receipts import render_realized_with_receipt,verify_realized_repeat,render_with_receipt

ROOT=Path(__file__).resolve().parents[1]


def fixture(name:str):
    return json.loads((ROOT/'examples'/name).read_text(encoding='utf-8'))


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
        exact={**self.policy,'mode':'exact','allow_particle_reduction':False,'allow_shadow_disable':False}
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

    def test_capability_map_exposes_v09_floor(self):
        req=fixture('realization_requirements.json')['required'];self.assertTrue(analyze_requirements(req)['ready'])

if __name__=='__main__':unittest.main()
