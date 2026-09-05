from __future__ import annotations
from typing import Any

CAPABILITIES: dict[str,dict[str,str]]={
"canonical-project-state":{"status":"executable","evidence":"closed v0.1/v0.2 normalized project schemas and digest"},
"2d-procedural-shapes":{"status":"rendered","evidence":"rectangles and circles render to exact PPM bytes"},
"multi-keyframe-animation":{"status":"rendered","evidence":"ordered integer keyframes with linear/hold/smoothstep interpolation"},
"transform-animation":{"status":"rendered","evidence":"integer tracks and keyframe curves"},
"camera-animation":{"status":"rendered","evidence":"camera x/y/zoom sampled into frame state"},
"text-rendering":{"status":"rendered","evidence":"bundled deterministic 5x7 bitmap text renderer with visible fallback glyph"},
"captions-subtitles":{"status":"rendered","evidence":"burned-in caption cues plus exact WebVTT export"},
"image-sprite-import":{"status":"rendered","evidence":"digest-bound image input conformed to exact PPM through explicit FFmpeg boundary"},
"video-clip-import":{"status":"rendered","evidence":"digest-bound video input conformed at project FPS to exact PPM frame sequence"},
"media-conformer":{"status":"executable","evidence":"image/video source digest + conformed frame digest manifest"},
"video-compositor":{"status":"rendered","evidence":"normal/add/multiply/screen layers with fades, media, text and procedural graphics"},
"external-audio-import":{"status":"rendered","evidence":"FFmpeg-decoded mono 48k PCM is digest-bound and mixed deterministically"},
"procedural-tone-audio":{"status":"rendered","evidence":"mono 48k WAV synthesis with PCM/WAV receipts"},
"audio-mixing":{"status":"rendered","evidence":"integer sample mixing of procedural and imported sources"},
"timeline-markers":{"status":"validated","evidence":"typed frame markers remain in canonical state for cuts/scenes/notes"},
"effect-organs":{"status":"executable","evidence":"live reusable effects plus detached forge/adoption path"},
"pixel-program-effects":{"status":"executable","evidence":"bounded deterministic stack program, no eval"},
"repeat-verification":{"status":"tested","evidence":"two full renders compared for exact frame manifest and WAV equality"},
"mp4-assembly":{"status":"external-boundary","evidence":"FFmpeg when installed; version and output digest recorded"},
"mechanical-video-review":{"status":"executable","evidence":"bounded framing/visibility/audio/camera checks with evidence"},
"daily-recovery":{"status":"executable","evidence":"deterministic whole-body ZIP snapshot before supported live effect adoption"},
"render-queue":{"status":"executable","evidence":"closed batch job list renders multiple projects and emits a queue receipt"},
"shot-manager":{"status":"executable","evidence":"structured shot plans compile independent relative shot timelines into one canonical movie state"},
"shot-plan-compiler":{"status":"executable","evidence":"per-shot camera/layers/audio/captions are deterministically shifted and stitched"},
"storyboard-generator":{"status":"rendered","evidence":"representative rendered frame per derived shot assembled into digest-bound contact sheet"},
"primitive-3d-rendering":{"status":"rendered","evidence":"fixed-point CORDIC transforms plus filled cube rasterization"},
"static-mesh-3d":{"status":"rendered","evidence":"OBJ vertices/faces quantized and rasterized with animated fixed-point transforms"},
"3d-scene-rendering":{"status":"rendered","evidence":"multiple primitive/OBJ layers share perspective depth, fixed-point transforms, painter ordering and deterministic face lighting"},
"texture-mapped-3d":{"status":"gap","evidence":"mesh surfaces currently use bounded flat color and deterministic face illumination; UV textures absent"},
"3d-shadows":{"status":"gap","evidence":"depth/perspective and face lighting exist; cast-shadow rasterization absent"},
"mesh-import":{"status":"rendered","evidence":"bounded OBJ vertex/face parser with exact source digest and triangle count"},
"skeletal-animation":{"status":"gap","evidence":"vocabulary known, runtime absent"},
"speech-synthesis":{"status":"external-boundary","evidence":"espeak/espeak-ng when installed; synthesized bytes and conformed PCM are receipted"},
"unicode-font-shaping":{"status":"gap","evidence":"v0.2 bundled bitmap font is bounded ASCII-ish, not a Unicode shaping engine"},
"natural-language-directing":{"status":"gap","evidence":"no model is required or bundled"},
"arbitrary-self-modification":{"status":"gap","evidence":"current live growth supports bounded effect organs, not arbitrary code mutation"},
}

def capability_summary()->dict[str,Any]: return {"schema":"axm.framestate.capability-map/v0.2","capabilities":CAPABILITIES}

def analyze_requirements(required:list[str])->dict[str,Any]:
    if not isinstance(required,list) or not all(isinstance(x,str) and x for x in required): raise ValueError("required must be a list of capability ids")
    rows=[]; ready=True
    for cap in required:
        row=CAPABILITIES.get(cap)
        if row is None: rows.append({"capability":cap,"status":"unknown","evidence":"not present in current capability map"}); ready=False
        else:
            rows.append({"capability":cap,**row})
            if row["status"]=="gap": ready=False
    return {"ready":ready,"requirements":rows,"smallest_visible_gaps":[r["capability"] for r in rows if r["status"] in {"gap","unknown"}]}
