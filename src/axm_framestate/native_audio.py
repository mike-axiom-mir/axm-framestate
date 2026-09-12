from __future__ import annotations

import io
import struct
import wave
from pathlib import Path
from typing import Any

class NativeAudioError(ValueError): pass

def _sample_to_s16(raw:bytes,width:int)->int:
    if width==1:return (raw[0]-128)<<8
    if width==2:return struct.unpack('<h',raw)[0]
    if width==3:
        v=raw[0]|(raw[1]<<8)|(raw[2]<<16)
        if v&0x800000:v-=1<<24
        return max(-32768,min(32767,v>>8))
    if width==4:
        v=struct.unpack('<i',raw)[0]
        return max(-32768,min(32767,v>>16))
    raise NativeAudioError('native WAV supports 8/16/24/32-bit integer PCM only')

def decode_wav_bytes(data:bytes,target_rate:int=48000,target_channels:int=1)->tuple[bytes,dict[str,Any]]:
    if target_rate<1 or target_channels not in {1,2}: raise NativeAudioError('invalid target WAV format')
    try:
        with wave.open(io.BytesIO(data),'rb') as wf:
            source_channels=wf.getnchannels(); width=wf.getsampwidth(); source_rate=wf.getframerate(); frames=wf.getnframes(); comptype=wf.getcomptype(); raw=wf.readframes(frames)
    except (wave.Error,EOFError) as exc:
        raise NativeAudioError('invalid WAV container') from exc
    if comptype!='NONE': raise NativeAudioError('native WAV supports uncompressed PCM only')
    if source_channels<1 or source_channels>32: raise NativeAudioError('unsupported WAV channel count')
    if source_rate<1 or frames<0: raise NativeAudioError('invalid WAV timing')
    frame_bytes=source_channels*width
    if len(raw)!=frames*frame_bytes: raise NativeAudioError('truncated WAV PCM body')
    decoded=[]
    pos=0
    for _ in range(frames):
        row=[]
        for _ch in range(source_channels):
            row.append(_sample_to_s16(raw[pos:pos+width],width)); pos+=width
        decoded.append(row)
    if not decoded:
        return b'',{'boundary':'native-wav-pcm-v0.1','source_rate':source_rate,'source_channels':source_channels,'source_sample_width':width,'target_rate':target_rate,'target_channels':target_channels,'source_frames':0,'target_frames':0}
    target_frames=(len(decoded)*target_rate)//source_rate
    if target_frames<1:target_frames=1
    out=bytearray()
    for i in range(target_frames):
        src_i=min(len(decoded)-1,(i*source_rate)//target_rate); row=decoded[src_i]
        if target_channels==1:
            v=sum(row)//len(row); out.extend(struct.pack('<h',max(-32768,min(32767,v))))
        elif len(row)==1:
            v=max(-32768,min(32767,row[0])); out.extend(struct.pack('<hh',v,v))
        else:
            left=max(-32768,min(32767,row[0])); right=max(-32768,min(32767,row[1])); out.extend(struct.pack('<hh',left,right))
    evidence={'boundary':'native-wav-pcm-v0.1','source_rate':source_rate,'source_channels':source_channels,'source_sample_width':width,'target_rate':target_rate,'target_channels':target_channels,'source_frames':len(decoded),'target_frames':target_frames,'resampler':'integer-nearest-v0.1'}
    return bytes(out),evidence

def decode_wav_file(path:Path,target_rate:int=48000,target_channels:int=1)->tuple[bytes,dict[str,Any]]:
    return decode_wav_bytes(Path(path).read_bytes(),target_rate,target_channels)
