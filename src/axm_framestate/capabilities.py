from __future__ import annotations
from typing import Any

CAPABILITIES={
'canonical-project-state':('executable','closed normalized project state + digest'),
'2d-procedural-shapes':('rendered','rectangles/circles render to exact PPM'),
'procedural-particles':('rendered','seeded deterministic particle field'),
'transform-animation':('rendered','integer scalar/from-to/keyframe tracks'),
'multi-keyframe-animation':('rendered','ordered integer keyframe curves'),
'camera-animation':('rendered','camera x/y/zoom sampled into frame state'),
'image-sprite-import':('external-boundary','input digest + Pillow conforming evidence'),
'video-clip-import':('external-boundary','input digest + FFmpeg-conformed frame evidence'),
'video-time-remap':('rendered','speed/reverse/freeze/source-frame selection'),
'video-compositor':('rendered','normal/add/multiply/screen, opacity, rotation, wipes'),
'masks-chroma':('rendered','image masks and chroma threshold in compositor'),
'text-rendering':('rendered','native 5x7 fallback plus supplied-font boundary'),
'unicode-font-shaping':('external-boundary','supplied font digest + Pillow/FreeType runtime evidence'),
'captions-subtitles':('rendered','burned captions + exact WebVTT export'),
'procedural-tone-audio':('rendered','48k tone synthesis'),
'external-audio-import':('external-boundary','FFmpeg decode source/PCM receipts'),
'audio-mixing':('rendered','timeline mixing with gain automation'),
'stereo-pan':('rendered','deterministic per-event pan/gain into stereo WAV'),
'speech-synthesis':('external-boundary','eSpeak synthesis + FFmpeg conform receipts'),
'effect-organs':('executable','detached effect forge/adoption path'),
'pixel-program-effects':('executable','bounded effect stack language, no eval'),
'3d-scene-rendering':('rendered','fixed-point primitive/mesh projection + triangle raster'),
'mesh-import':('rendered','native OBJ v/vt/f parser'),
'uv-texture-mapping':('rendered','nearest UV texture sampling on triangles'),
'cast-shadows':('rendered','deterministic directional screen-space shadow projection'),
'skeletal-animation':('rendered','hierarchical rig2d runtime'),
'morph-target-animation':('rendered','vertex interpolation between compatible meshes'),
'nested-compositions':('rendered','FrameState project as visual child with child lineage'),
'nested-audio':('rendered','child FrameState audio can enter parent mix with lineage'),
'shot-plan-compiler':('executable','relative shots compile into one canonical project'),
'creative-brief-compiler':('executable','high-level beats/style/media compile into canonical shot plan and project'),
'shot-recipe-organs':('executable','detached reusable shot templates can be replay-tested and adopted behind four-root + recovery gate'),
'shot-manager':('executable','markers derive shot spans'),
'storyboard-generator':('rendered','representative actual rendered frames + digest lineage'),
'render-queue':('executable','batch project rendering with queue receipt'),
'frame-analysis':('executable','non-mutating frame color/delta analysis and cut proposals'),
'mp4-assembly':('external-boundary','FFmpeg profile encode, version/output digest'),
'repeat-verification':('tested','second full render compares project/media/frame/audio truth'),
'mechanical-video-review':('executable','bounded framing/audio/camera checks'),
'daily-recovery':('executable','whole-body snapshot before supported effect adoption'),
'natural-language-directing':('gap','free-form language still requires an explicit translator; creative briefs and shot plans are native'),
'arbitrary-self-modification':('gap','growth remains bounded; no arbitrary self-write authority'),
}

def capability_summary()->dict[str,Any]:
    return {'schema':'axm.framestate.capability-map/v0.5','capabilities':{k:{'status':v[0],'evidence':v[1]} for k,v in CAPABILITIES.items()}}

def analyze_requirements(required:list[str])->dict[str,Any]:
    rows=[];ready=True
    for cap in required:
        if cap not in CAPABILITIES: rows.append({'capability':cap,'status':'unknown','evidence':'not present in current capability map'});ready=False
        else:
            s,e=CAPABILITIES[cap];rows.append({'capability':cap,'status':s,'evidence':e});ready &= s!='gap'
    return {'ready':bool(ready),'requirements':rows,'smallest_visible_gaps':[r['capability'] for r in rows if r['status'] in {'gap','unknown'}]}
