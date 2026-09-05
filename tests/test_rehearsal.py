from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from axm_framestate.canonical import load_project,normalize_project
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.rehearsal import rehearse_project

ROOT=Path(__file__).resolve().parents[1]

class RehearsalTests(unittest.TestCase):
    def test_rehearsal_requirements_ready(self):
        req=json.loads((ROOT/'examples'/'rehearsal_requirements.json').read_text())['required'];self.assertTrue(analyze_requirements(req)['ready'])

    def test_repairs_mechanical_quality_debt(self):
        p=load_project(ROOT/'examples'/'rehearsal_challenge.json');policy=json.loads((ROOT/'examples'/'rehearsal_policy.json').read_text())
        with tempfile.TemporaryDirectory() as td:
            r=rehearse_project(p,Path(td),ROOT,policy=policy,assemble_final=False)
            self.assertEqual(r['accepted_delta_count'],4);self.assertEqual(r['stop_reason'],'NO_JUSTIFIED_AUTO_DELTA');self.assertEqual(r['remaining_proposals'],[])
            codes=[a['proposal']['code'] for it in r['iterations'] for a in it['attempts'] if a['comparison']['accepted']];self.assertEqual(codes,['AUDIO_HEADROOM','CAPTION_READABILITY','FADE_BUDGET','TEXT_FIT'])

    def test_repeatable(self):
        p=normalize_project({'schema':'axm.framestate.project/v0.4','id':'tiny-rehearsal','canvas':{'width':32,'height':24,'fps':6},'duration_frames':6,'background':[0,0,0],'camera':{'x':0,'y':0,'zoom_milli':1000},'media':[],'layers':[],'captions':[],'audio':[{'id':'hot','kind':'tone','start_frame':0,'end_frame':6,'frequency_hz':100,'gain_milli':2200,'pan_milli':0}],'effects':[],'markers':[],'metadata':{}})
        policy={'schema':'axm.framestate.rehearsal-policy/v0.1','max_passes':2,'target_declared_audio_gain_milli':1600,'target_pcm_peak_abs':30000,'max_caption_words_per_second_milli':3500,'auto_accept_codes':['AUDIO_HEADROOM']}
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            ra=rehearse_project(p,Path(a),ROOT,policy=policy,assemble_final=False);rb=rehearse_project(p,Path(b),ROOT,policy=policy,assemble_final=False)
            self.assertEqual(ra['final_project_digest'],rb['final_project_digest']);self.assertEqual(ra['rehearsal_receipt_digest'],rb['rehearsal_receipt_digest'])

    def test_clean_project_can_stop_without_rewrite(self):
        p=normalize_project({'schema':'axm.framestate.project/v0.4','id':'tiny-clean','canvas':{'width':32,'height':24,'fps':6},'duration_frames':6,'background':[0,0,0],'camera':{'x':0,'y':0,'zoom_milli':1000},'media':[],'layers':[{'id':'dot','kind':'circle','z':1,'start_frame':0,'end_frame':6,'x':16,'y':12,'radius':3,'color':[100,160,255]}],'captions':[],'audio':[{'id':'quiet','kind':'tone','start_frame':0,'end_frame':6,'frequency_hz':100,'gain_milli':200,'pan_milli':0}],'effects':[],'markers':[],'metadata':{}})
        with tempfile.TemporaryDirectory() as td:
            r=rehearse_project(p,Path(td),ROOT,assemble_final=False);self.assertEqual(r['accepted_delta_count'],0);self.assertEqual(r['initial_project_digest'],r['final_project_digest']);self.assertEqual(r['stop_reason'],'NO_JUSTIFIED_AUTO_DELTA')

if __name__=='__main__':unittest.main()
