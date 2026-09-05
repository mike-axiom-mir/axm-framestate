from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_SCHEMAS = {"axm.framestate.project/v0.1", "axm.framestate.project/v0.2"}
PROJECT_SCHEMA = "axm.framestate.project/v0.2"


class ProjectError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value: Any, label: str, low: int | None = None, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectError(f"{label} must be an integer")
    if low is not None and value < low:
        raise ProjectError(f"{label} must be >= {low}")
    if high is not None and value > high:
        raise ProjectError(f"{label} must be <= {high}")
    return value


def _text(value: Any, label: str, maximum: int = 10000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectError(f"{label} must be non-empty text")
    if len(value) > maximum:
        raise ProjectError(f"{label} exceeds {maximum} characters")
    return value


def _color(value: Any, label: str) -> list[int]:
    if not isinstance(value, list) or len(value) != 3:
        raise ProjectError(f"{label} must be [r,g,b]")
    return [_integer(v, f"{label}[{i}]", 0, 255) for i, v in enumerate(value)]


def _validate_track(track: Any, label: str, duration: int | None = None) -> dict[str, Any]:
    if not isinstance(track, dict):
        raise ProjectError(f"{label} must be an object")
    if "keyframes" in track:
        if set(track) != {"keyframes"}:
            raise ProjectError(f"{label} keyframe track accepts only keyframes")
        rows = track["keyframes"]
        if not isinstance(rows, list) or len(rows) < 1:
            raise ProjectError(f"{label}.keyframes must be non-empty")
        out=[]; last=-1
        for i,row in enumerate(rows):
            if not isinstance(row,dict) or set(row)-{"frame","value","easing"}:
                raise ProjectError(f"{label}.keyframes[{i}] has unsupported fields")
            frame=_integer(row.get("frame"),f"{label}.keyframes[{i}].frame",0,duration-1 if duration else None)
            if frame<=last: raise ProjectError(f"{label}.keyframes must be strictly ordered")
            last=frame
            value=_integer(row.get("value"),f"{label}.keyframes[{i}].value",-1_000_000,1_000_000)
            easing=row.get("easing","linear")
            if easing not in {"linear","hold","smoothstep"}: raise ProjectError(f"{label}.keyframes[{i}].easing unsupported")
            out.append({"frame":frame,"value":value,"easing":easing})
        return {"keyframes":out}
    allowed={"from","to","easing"}
    unknown=set(track)-allowed
    if unknown: raise ProjectError(f"{label} has unknown fields: {sorted(unknown)}")
    start=_integer(track.get("from"),f"{label}.from",-1_000_000,1_000_000)
    end=_integer(track.get("to"),f"{label}.to",-1_000_000,1_000_000)
    easing=track.get("easing","linear")
    if easing not in {"linear","hold","smoothstep"}: raise ProjectError(f"{label}.easing unsupported")
    return {"from":start,"to":end,"easing":easing}


def _track_default(value: int) -> dict[str,Any]:
    return {"from":value,"to":value}


def normalize_project(raw: Any) -> dict[str, Any]:
    if not isinstance(raw,dict): raise ProjectError("project must be an object")
    schema=raw.get("schema")
    if schema not in PROJECT_SCHEMAS: raise ProjectError(f"schema must be one of {sorted(PROJECT_SCHEMAS)}")
    allowed={"schema","id","title","canvas","duration_frames","background","camera","layers","audio","effects","metadata","media","captions","markers"}
    unknown=set(raw)-allowed
    if unknown: raise ProjectError(f"project has unknown fields: {sorted(unknown)}")
    project_id=_text(raw.get("id"),"id",200).strip(); title=_text(raw.get("title",project_id),"title",500).strip()
    canvas=raw.get("canvas")
    if not isinstance(canvas,dict) or set(canvas)-{"width","height","fps"}: raise ProjectError("canvas must contain only width, height and fps")
    width=_integer(canvas.get("width"),"canvas.width",16,4096); height=_integer(canvas.get("height"),"canvas.height",16,4096); fps=_integer(canvas.get("fps"),"canvas.fps",1,120)
    duration=_integer(raw.get("duration_frames"),"duration_frames",1,fps*60*60)
    background=_color(raw.get("background",[0,0,0]),"background")
    camera_raw=raw.get("camera",{})
    if not isinstance(camera_raw,dict) or set(camera_raw)-{"x","y","zoom_milli"}: raise ProjectError("camera fields must be x, y and zoom_milli")
    camera={
        "x":_validate_track(camera_raw.get("x",_track_default(0)),"camera.x",duration),
        "y":_validate_track(camera_raw.get("y",_track_default(0)),"camera.y",duration),
        "zoom_milli":_validate_track(camera_raw.get("zoom_milli",_track_default(1000)),"camera.zoom_milli",duration),
    }
    def track_values(t):
        if "keyframes" in t: return [x["value"] for x in t["keyframes"]]
        return [t["from"],t["to"]]
    if min(track_values(camera["zoom_milli"]))<=0: raise ProjectError("camera zoom_milli must stay positive")

    media_raw=raw.get("media",[])
    if not isinstance(media_raw,list): raise ProjectError("media must be an array")
    media=[]; media_ids=set()
    for i,item in enumerate(media_raw):
        label=f"media[{i}]"
        if not isinstance(item,dict) or set(item)-{"id","kind","path"}: raise ProjectError(f"{label} has unsupported fields")
        mid=_text(item.get("id"),f"{label}.id",200)
        if mid in media_ids: raise ProjectError(f"{label}.id must be unique")
        media_ids.add(mid)
        kind=item.get("kind")
        if kind not in {"image","video","mesh"}: raise ProjectError(f"{label}.kind must be image, video or mesh")
        media.append({"id":mid,"kind":kind,"path":_text(item.get("path"),f"{label}.path",2000)})

    layers_raw=raw.get("layers",[])
    if not isinstance(layers_raw,list): raise ProjectError("layers must be an array")
    layers=[]; ids=set()
    for index,layer in enumerate(layers_raw):
        label=f"layers[{index}]"
        if not isinstance(layer,dict): raise ProjectError(f"{label} must be an object")
        allowed_layer={"id","kind","z","start_frame","end_frame","color","x","y","w","h","radius","opacity_milli","media_id","source_start_frame","playback_milli","loop","blend_mode","fade_in_frames","fade_out_frames","text","scale","align","background_color","padding","depth","size","rot_x_mdeg","rot_y_mdeg","rot_z_mdeg"}
        extra=set(layer)-allowed_layer
        if extra: raise ProjectError(f"{label} has unknown fields: {sorted(extra)}")
        lid=_text(layer.get("id"),f"{label}.id",200)
        if lid in ids: raise ProjectError(f"{label}.id must be unique")
        ids.add(lid)
        kind=layer.get("kind")
        if kind not in {"rect","circle","image","video","text","cube3d","mesh3d"}: raise ProjectError(f"{label}.kind unsupported")
        start=_integer(layer.get("start_frame",0),f"{label}.start_frame",0,duration-1)
        end=_integer(layer.get("end_frame",duration),f"{label}.end_frame",start+1,duration)
        norm={
            "id":lid,"kind":kind,"z":_integer(layer.get("z",0),f"{label}.z",-10000,10000),
            "start_frame":start,"end_frame":end,"color":_color(layer.get("color",[255,255,255]),f"{label}.color"),
            "x":_validate_track(layer.get("x",_track_default(0)),f"{label}.x",duration),
            "y":_validate_track(layer.get("y",_track_default(0)),f"{label}.y",duration),
            "opacity_milli":_validate_track(layer.get("opacity_milli",_track_default(1000)),f"{label}.opacity_milli",duration),
            "blend_mode":layer.get("blend_mode","normal"),
            "fade_in_frames":_integer(layer.get("fade_in_frames",0),f"{label}.fade_in_frames",0,end-start),
            "fade_out_frames":_integer(layer.get("fade_out_frames",0),f"{label}.fade_out_frames",0,end-start),
        }
        if norm["blend_mode"] not in {"normal","add","multiply","screen"}: raise ProjectError(f"{label}.blend_mode unsupported")
        if kind=="circle": norm["radius"]=_validate_track(layer.get("radius",_track_default(5)),f"{label}.radius",duration)
        elif kind in {"cube3d","mesh3d"}:
            norm["depth"]=_validate_track(layer.get("depth",_track_default(180)),f"{label}.depth",duration)
            norm["size"]=_validate_track(layer.get("size",_track_default(80)),f"{label}.size",duration)
            norm["rot_x_mdeg"]=_validate_track(layer.get("rot_x_mdeg",_track_default(0)),f"{label}.rot_x_mdeg",duration)
            norm["rot_y_mdeg"]=_validate_track(layer.get("rot_y_mdeg",_track_default(0)),f"{label}.rot_y_mdeg",duration)
            norm["rot_z_mdeg"]=_validate_track(layer.get("rot_z_mdeg",_track_default(0)),f"{label}.rot_z_mdeg",duration)
            if min(track_values(norm["depth"])) <= 1: raise ProjectError(f"{label}.depth must stay > 1")
        elif kind in {"rect","image","video"}:
            norm["w"]=_validate_track(layer.get("w",_track_default(10)),f"{label}.w",duration); norm["h"]=_validate_track(layer.get("h",_track_default(10)),f"{label}.h",duration)
        if kind in {"image","video","mesh3d"}:
            mid=_text(layer.get("media_id"),f"{label}.media_id",200)
            if mid not in media_ids: raise ProjectError(f"{label}.media_id does not resolve")
            expected="image" if kind=="image" else "video" if kind=="video" else "mesh"
            actual=next(x["kind"] for x in media if x["id"]==mid)
            if actual!=expected: raise ProjectError(f"{label}.media_id kind mismatch")
            norm["media_id"]=mid
            if kind in {"image","video"}: norm.update({"source_start_frame":_integer(layer.get("source_start_frame",0),f"{label}.source_start_frame",0,10_000_000),"playback_milli":_integer(layer.get("playback_milli",1000),f"{label}.playback_milli",1,100_000),"loop":bool(layer.get("loop",False))})
        if kind=="text":
            norm.update({"text":_text(layer.get("text"),f"{label}.text",10000),"scale":_integer(layer.get("scale",2),f"{label}.scale",1,20),"align":layer.get("align","center"),"background_color":_color(layer.get("background_color",[0,0,0]),f"{label}.background_color"),"padding":_integer(layer.get("padding",2),f"{label}.padding",0,100)})
            if norm["align"] not in {"left","center","right"}: raise ProjectError(f"{label}.align unsupported")
        layers.append(norm)

    captions_raw=raw.get("captions",[])
    if not isinstance(captions_raw,list): raise ProjectError("captions must be an array")
    captions=[]; cap_ids=set()
    for i,c in enumerate(captions_raw):
        label=f"captions[{i}]"
        if not isinstance(c,dict) or set(c)-{"id","start_frame","end_frame","text","color","background_color","scale","position","padding"}: raise ProjectError(f"{label} has unsupported fields")
        cid=_text(c.get("id",f"caption-{i}"),f"{label}.id",200)
        if cid in cap_ids: raise ProjectError(f"{label}.id must be unique")
        cap_ids.add(cid); start=_integer(c.get("start_frame"),f"{label}.start_frame",0,duration-1); end=_integer(c.get("end_frame"),f"{label}.end_frame",start+1,duration)
        position=c.get("position","bottom")
        if position not in {"top","middle","bottom"}: raise ProjectError(f"{label}.position unsupported")
        captions.append({"id":cid,"start_frame":start,"end_frame":end,"text":_text(c.get("text"),f"{label}.text",10000),"color":_color(c.get("color",[255,255,255]),f"{label}.color"),"background_color":_color(c.get("background_color",[0,0,0]),f"{label}.background_color"),"scale":_integer(c.get("scale",2),f"{label}.scale",1,20),"position":position,"padding":_integer(c.get("padding",3),f"{label}.padding",0,100)})

    audio_raw=raw.get("audio",[])
    if not isinstance(audio_raw,list): raise ProjectError("audio must be an array")
    audio=[]
    for index,event in enumerate(audio_raw):
        label=f"audio[{index}]"
        if not isinstance(event,dict): raise ProjectError(f"{label} must be an object")
        kind=event.get("kind")
        if kind=="tone":
            allowed_a={"id","kind","start_frame","end_frame","frequency_hz","gain_milli"}
        elif kind=="file":
            allowed_a={"id","kind","start_frame","end_frame","path","gain_milli","source_start_frame","loop"}
        elif kind=="speech":
            allowed_a={"id","kind","start_frame","end_frame","text","gain_milli","voice","rate_wpm"}
        else: raise ProjectError(f"{label}.kind supports tone, file or speech")
        if set(event)-allowed_a: raise ProjectError(f"{label} has unsupported fields")
        start=_integer(event.get("start_frame",0),f"{label}.start_frame",0,duration-1); end=_integer(event.get("end_frame",duration),f"{label}.end_frame",start+1,duration)
        row={"id":str(event.get("id",f"audio-{index}")),"kind":kind,"start_frame":start,"end_frame":end,"gain_milli":_integer(event.get("gain_milli",100),f"{label}.gain_milli",0,4000)}
        if kind=="tone": row["frequency_hz"]=_integer(event.get("frequency_hz",440),f"{label}.frequency_hz",20,20000)
        elif kind=="file": row.update({"path":_text(event.get("path"),f"{label}.path",2000),"source_start_frame":_integer(event.get("source_start_frame",0),f"{label}.source_start_frame",0,10_000_000),"loop":bool(event.get("loop",False))})
        else: row.update({"text":_text(event.get("text"),f"{label}.text",5000),"voice":str(event.get("voice","en")),"rate_wpm":_integer(event.get("rate_wpm",170),f"{label}.rate_wpm",80,450)})
        audio.append(row)

    effects=raw.get("effects",[])
    if not isinstance(effects,list) or not all(isinstance(x,str) and x.strip() for x in effects): raise ProjectError("effects must be an array of effect refs")
    markers_raw=raw.get("markers",[])
    if not isinstance(markers_raw,list): raise ProjectError("markers must be an array")
    markers=[]
    for i,m in enumerate(markers_raw):
        if not isinstance(m,dict) or set(m)-{"frame","label","kind"}: raise ProjectError(f"markers[{i}] has unsupported fields")
        markers.append({"frame":_integer(m.get("frame"),f"markers[{i}].frame",0,duration-1),"label":_text(m.get("label"),f"markers[{i}].label",500),"kind":str(m.get("kind","marker"))})
    metadata=raw.get("metadata",{})
    if not isinstance(metadata,dict): raise ProjectError("metadata must be an object")
    return {"schema":schema,"id":project_id,"title":title,"canvas":{"width":width,"height":height,"fps":fps},"duration_frames":duration,"background":background,"camera":camera,"media":media,"layers":sorted(layers,key=lambda x:(x["z"],x["id"])),"captions":captions,"audio":audio,"effects":effects,"markers":markers,"metadata":metadata}


def load_project(path: Path) -> dict[str, Any]:
    try: raw=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise ProjectError(f"could not load project: {exc}") from exc
    return normalize_project(raw)
