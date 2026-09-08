from __future__ import annotations
import hashlib, io, json, shutil, subprocess
from pathlib import Path
from typing import Any
from PIL import Image
from .canonical import canonical_json, digest, file_digest, load_project

class MediaError(RuntimeError): pass

def resolve_source(root:Path, declared:str)->Path:
    p=Path(declared).expanduser()
    if p.is_absolute(): return p.resolve()
    return (Path(root).resolve()/p).resolve()

def ffmpeg_version()->str|None:
    exe=shutil.which('ffmpeg')
    if not exe: return None
    p=subprocess.run([exe,'-version'],capture_output=True,text=True,check=False)
    return p.stdout.splitlines()[0] if p.stdout else 'ffmpeg-present-version-unknown'

def pillow_version()->str:
    import PIL
    return f'Pillow {getattr(PIL,"__version__","unknown")}'

def _ppm_bytes(img:Image.Image)->bytes:
    rgb=img.convert('RGB'); w,h=rgb.size
    return f'P6\n{w} {h}\n255\n'.encode('ascii')+rgb.tobytes()

def read_ppm(path:Path)->tuple[int,int,bytes]:
    raw=Path(path).read_bytes()
    if not raw.startswith(b'P6'):
        with Image.open(io.BytesIO(raw)) as im:
            rgb=im.convert('RGB'); return rgb.width,rgb.height,rgb.tobytes()
    # tiny parser, comments unsupported intentionally for internally emitted PPMs
    head,body=raw.split(b'\n255\n',1)
    parts=head.split()
    return int(parts[1]),int(parts[2]),body

def conform_media(project:dict[str,Any], output_dir:Path, machine_root:Path)->dict[str,Any]:
    output_dir=Path(output_dir); root=Path(machine_root); target=output_dir/'conformed-media'; target.mkdir(parents=True,exist_ok=True)
    rows=[]; fps=project['canvas']['fps']; cw,ch=project['canvas']['width'],project['canvas']['height']
    for m in project.get('media',[]):
        src=resolve_source(root,m['path'])
        if not src.is_file(): raise MediaError(f"media missing: {m['path']}")
        evidence={'id':m['id'],'kind':m['kind'],'declared_path':m['path'],'source_digest':file_digest(src)}
        if m['kind']=='image':
            with Image.open(src) as im:
                rgb=im.convert('RGB'); data=_ppm_bytes(rgb)
            d=target/m['id']; d.mkdir(exist_ok=True); p=d/'frame-000000.ppm'; p.write_bytes(data)
            evidence.update({'width':rgb.width,'height':rgb.height,'frame_count':1,'conformed_digest':file_digest(p),'boundary':pillow_version()})
        elif m['kind']=='video':
            exe=shutil.which('ffmpeg')
            if not exe: raise MediaError('ffmpeg required for video media')
            d=target/m['id']; d.mkdir(exist_ok=True)
            for old in d.glob('frame-*.ppm'): old.unlink()
            cmd=[exe,'-y','-loglevel','error','-i',str(src),'-vf',f'fps={fps}','-start_number','0',str(d/'frame-%06d.ppm')]
            p=subprocess.run(cmd,capture_output=True,text=True,check=False)
            if p.returncode!=0: raise MediaError(p.stderr[-4000:])
            fs=sorted(d.glob('frame-*.ppm'))
            if not fs: raise MediaError(f'video decoded zero frames: {src}')
            evidence.update({'frame_count':len(fs),'frame_digests':[file_digest(x) for x in fs],'decoder':ffmpeg_version()})
        elif m['kind']=='mesh':
            evidence.update({'bytes':src.stat().st_size,'boundary':'native-obj-parser'})
        elif m['kind']=='font': evidence.update({'bytes':src.stat().st_size,'boundary':pillow_version()})
        elif m['kind']=='audio': evidence.update({'bytes':src.stat().st_size,'boundary':'audio-event-decoder'})
        elif m['kind']=='framestate':
            child=load_project(src); evidence.update({'child_project_digest':digest(child),'boundary':'native-framestate-child'})
        rows.append(evidence)
    result={'schema':'axm.framestate.media-manifest/v0.4','rows':rows}; result['manifest_digest']=digest(result)
    (output_dir/'media-manifest.json').write_bytes(canonical_json(result)+b'\n')
    return result

class MediaCache:
    def __init__(self,project:dict[str,Any],output_dir:Path,machine_root:Path):
        self.project=project; self.output_dir=Path(output_dir); self.root=Path(machine_root); self.by_id={m['id']:m for m in project.get('media',[])}
        self.manifest=conform_media(project,output_dir,machine_root)
        self._ppm:{}={}; self._mesh:{}={}; self._child:{}={}
    def item(self,mid:str)->dict[str,Any]:
        if mid not in self.by_id: raise MediaError(f'missing media id {mid}')
        return self.by_id[mid]
    def frame_count(self,mid:str)->int:
        item=self.item(mid)
        if item['kind']=='image': return 1
        if item['kind']=='video': return len(list((self.output_dir/'conformed-media'/mid).glob('frame-*.ppm')))
        if item['kind']=='framestate':
            c=self.child(mid); return c['project']['duration_frames']
        return 0
    def image_frame(self,mid:str,index:int)->tuple[int,int,bytes]:
        item=self.item(mid)
        key=(mid,index)
        if key in self._ppm: return self._ppm[key]
        if item['kind']=='image': p=self.output_dir/'conformed-media'/mid/'frame-000000.ppm'
        elif item['kind']=='video': p=self.output_dir/'conformed-media'/mid/f'frame-{index:06d}.ppm'
        else: raise MediaError(f'{mid} is not image/video')
        out=read_ppm(p); self._ppm[key]=out; return out
    def mesh(self,mid:str):
        if mid in self._mesh: return self._mesh[mid]
        item=self.item(mid)
        from .three_d import parse_obj
        out=parse_obj(resolve_source(self.root,item['path'])); self._mesh[mid]=out; return out
    def font_path(self,mid:str)->Path:
        item=self.item(mid)
        if item['kind']!='font': raise MediaError('font media expected')
        return resolve_source(self.root,item['path'])
    def child(self,mid:str)->dict[str,Any]:
        if mid in self._child: return self._child[mid]
        item=self.item(mid)
        if item['kind']!='framestate': raise MediaError('framestate media expected')
        path=resolve_source(self.root,item['path']); project=load_project(path)
        child_out=self.output_dir/'child'/mid
        from .receipts import render_with_receipt
        receipt=render_with_receipt(project,child_out,self.root,assemble=False)
        result={'project':project,'output':child_out,'receipt':receipt}; self._child[mid]=result; return result
