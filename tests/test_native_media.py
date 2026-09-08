from __future__ import annotations

import io
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from axm_framestate.audio import render_audio
from axm_framestate.canonical import normalize_project
from axm_framestate.media import conform_media
from axm_framestate.native_audio import decode_wav_bytes
from axm_framestate.native_image import NativeImageError, decode_png, encode_png_rgb
from axm_framestate.render import render_project


def project_base():
    return {
        "schema":"axm.framestate.project/v0.5","id":"native-media","title":"Native Media",
        "canvas":{"width":32,"height":24,"fps":12},"duration_frames":2,"background":[0,0,0],
        "camera":{"x":0,"y":0,"zoom_milli":1000},"media":[],"layers":[],"captions":[],"audio":[],"effects":[],"markers":[],"metadata":{}
    }


class NativeMediaTests(unittest.TestCase):
    def test_native_png_rgb_round_trip_and_crc_refusal(self):
        rgb=bytes([255,0,0,0,255,0,0,0,255,240,240,240])
        png=encode_png_rgb(2,2,rgb)
        w,h,out,ev=decode_png(png)
        self.assertEqual((w,h,out),(2,2,rgb));self.assertEqual(ev['boundary'],'native-png-v0.1')
        broken=bytearray(png);broken[-5]^=1
        with self.assertRaises(NativeImageError):decode_png(bytes(broken))

    def test_png_project_conforms_and_renders_without_pillow_path(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);asset=root/'asset.png';asset.write_bytes(encode_png_rgb(2,2,bytes([255,0,0]*4)))
            p=project_base();p['media']=[{'id':'pic','kind':'image','path':'asset.png'}];p['layers']=[{'id':'pic-layer','kind':'image','media_id':'pic','x':16,'y':12,'w':16,'h':16,'start_frame':0,'end_frame':2}];p=normalize_project(p)
            with patch('axm_framestate.media._pillow_image',side_effect=AssertionError('Pillow path must not run')):
                manifest=conform_media(p,root/'conform',root);rendered=render_project(p,root/'render',root)
            self.assertEqual(manifest['rows'][0]['boundary'],'native-png-v0.1');self.assertEqual(rendered['frame_count'],2)

    def test_native_wav_resample_is_deterministic(self):
        bio=io.BytesIO()
        with wave.open(bio,'wb') as wf:
            wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(24000);wf.writeframes(struct.pack('<hhhh',0,1000,-1000,2000))
        a,ev1=decode_wav_bytes(bio.getvalue(),48000,1);b,ev2=decode_wav_bytes(bio.getvalue(),48000,1)
        self.assertEqual(a,b);self.assertEqual(ev1,ev2);self.assertEqual(ev1['target_frames'],8);self.assertEqual(len(a),16)

    def test_wav_audio_event_needs_no_ffmpeg(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);wav=root/'tone.wav'
            with wave.open(str(wav),'wb') as wf:
                wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(48000);wf.writeframes(struct.pack('<h',1200)*4000)
            p=project_base();p['audio']=[{'id':'file','kind':'file','path':'tone.wav','start_frame':0,'end_frame':2,'gain_milli':1000,'pan_milli':0}];p=normalize_project(p)
            with patch('axm_framestate.audio.shutil.which',return_value=None): manifest=render_audio(p,root/'out.wav',root,root)
            self.assertEqual(manifest['source_evidence'][0]['decoder']['boundary'],'native-wav-pcm-v0.1')


if __name__=='__main__':unittest.main()
