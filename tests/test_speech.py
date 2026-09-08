from __future__ import annotations
import copy,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from axm_framestate.audio import render_audio
from axm_framestate.canonical import digest,normalize_project,load_project
from axm_framestate.capabilities import analyze_requirements
from axm_framestate.director import compile_brief
from axm_framestate.speech import synthesize_native,text_to_phonemes

ROOT=Path(__file__).resolve().parents[1]

class NativeSpeechTests(unittest.TestCase):
    def test_native_speech_is_exact_and_receipted(self):
        text='FrameState speaks with its own deterministic voice.'
        a,ea=synthesize_native(text,'native-neutral-1',165);b,eb=synthesize_native(text,'native-neutral-1',165)
        self.assertEqual(a,b);self.assertEqual(ea['pcm_digest'],eb['pcm_digest']);self.assertEqual(ea['receipt_digest'],eb['receipt_digest'])
        self.assertEqual(ea['external_dependencies'],[]);self.assertGreater(ea['sample_count'],0);self.assertGreater(len(text_to_phonemes(text)),10)
        vals=[x[0] for x in struct.iter_unpack('<h',a)];self.assertGreater(max(map(abs,vals)),1000)

    def test_native_speech_renders_with_no_espeak_or_ffmpeg_available(self):
        p=load_project(ROOT/'examples'/'native_speech.json')
        with tempfile.TemporaryDirectory() as td, patch('axm_framestate.audio.shutil.which',return_value=None):
            out=Path(td)/'native.wav';r=render_audio(p,out,ROOT,Path(td));self.assertTrue(out.is_file())
            ev=r['source_evidence'][0];self.assertEqual(ev['engine'],'native');self.assertEqual(ev['external_dependencies'],[]);self.assertEqual(ev['synthesizer'],'FrameState Native Speech v0.1')

    def test_project_schema_migrates_legacy_speech_without_rewriting_its_engine(self):
        base={'id':'legacy','canvas':{'width':32,'height':24,'fps':6},'duration_frames':6,'background':[0,0,0],'camera':{'x':0,'y':0,'zoom_milli':1000},'media':[],'layers':[],'captions':[],'audio':[{'id':'v','kind':'speech','start_frame':0,'end_frame':6,'text':'hello','voice':'en','rate_wpm':165,'gain_milli':1000,'pan_milli':0}],'effects':[],'markers':[],'metadata':{}}
        old=normalize_project({'schema':'axm.framestate.project/v0.4',**copy.deepcopy(base)});new=normalize_project({'schema':'axm.framestate.project/v0.5',**copy.deepcopy(base)})
        self.assertEqual(old['audio'][0]['engine'],'espeak');self.assertEqual(new['audio'][0]['engine'],'native')

    def test_director_narration_defaults_to_native_engine(self):
        brief={'schema':'axm.framestate.creative-brief/v0.1','id':'talk','canvas':{'width':64,'height':36,'fps':6},'duration_frames':12,'style':'clean','beats':[{'kind':'message','text':'HELLO','narration':'hello','weight':1}]}
        p=compile_brief(brief,ROOT);self.assertEqual(p['audio'][0]['engine'],'native');self.assertEqual(p['audio'][0]['voice'],'native-neutral-1')

    def test_native_speech_capabilities_ready(self):
        req=json.loads((ROOT/'examples'/'native_speech_requirements.json').read_text())['required'];self.assertTrue(analyze_requirements(req)['ready'])

if __name__=='__main__': unittest.main()
