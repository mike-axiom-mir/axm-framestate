from __future__ import annotations

import struct
import zlib
from typing import Any

PNG_SIGNATURE=b'\x89PNG\r\n\x1a\n'

class NativeImageError(ValueError): pass

def _paeth(a:int,b:int,c:int)->int:
    p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
    if pa<=pb and pa<=pc:return a
    if pb<=pc:return b
    return c

def decode_png(data:bytes)->tuple[int,int,bytes,dict[str,Any]]:
    if not data.startswith(PNG_SIGNATURE): raise NativeImageError('not a PNG file')
    off=len(PNG_SIGNATURE); width=height=None; bit_depth=color_type=None; interlace=None; compressed=bytearray(); saw_ihdr=False; saw_iend=False
    while off+12<=len(data):
        length=struct.unpack('>I',data[off:off+4])[0]; kind=data[off+4:off+8]; start=off+8; end=start+length
        if end+4>len(data): raise NativeImageError('truncated PNG chunk')
        payload=data[start:end]; expected=struct.unpack('>I',data[end:end+4])[0]; actual=zlib.crc32(kind+payload)&0xffffffff
        if expected!=actual: raise NativeImageError(f'PNG CRC mismatch in {kind.decode("latin1")}')
        off=end+4
        if kind==b'IHDR':
            if saw_ihdr or length!=13: raise NativeImageError('invalid PNG IHDR')
            width,height,bit_depth,color_type,compression,filter_method,interlace=struct.unpack('>IIBBBBB',payload)
            if width<1 or height<1 or width>16384 or height>16384: raise NativeImageError('PNG dimensions outside native boundary')
            if bit_depth!=8: raise NativeImageError('native PNG supports 8-bit channels only')
            if color_type not in {0,2,4,6}: raise NativeImageError('native PNG supports grayscale/RGB/gray-alpha/RGBA only')
            if compression!=0 or filter_method!=0 or interlace!=0: raise NativeImageError('native PNG supports standard non-interlaced encoding only')
            saw_ihdr=True
        elif kind==b'IDAT':
            if not saw_ihdr: raise NativeImageError('PNG IDAT before IHDR')
            compressed.extend(payload)
        elif kind==b'IEND':
            saw_iend=True; break
    if not saw_ihdr or not saw_iend or width is None or height is None: raise NativeImageError('incomplete PNG')
    channels={0:1,2:3,4:2,6:4}[color_type]; stride=width*channels
    try: raw=zlib.decompress(bytes(compressed))
    except zlib.error as exc: raise NativeImageError('PNG zlib stream invalid') from exc
    expected_len=height*(stride+1)
    if len(raw)!=expected_len: raise NativeImageError('PNG decompressed size mismatch')
    rows=[]; prior=bytearray(stride); pos=0
    for _ in range(height):
        f=raw[pos]; pos+=1; src=raw[pos:pos+stride]; pos+=stride
        out=bytearray(stride)
        for i,x in enumerate(src):
            a=out[i-channels] if i>=channels else 0; b=prior[i]; c=prior[i-channels] if i>=channels else 0
            if f==0:v=x
            elif f==1:v=(x+a)&255
            elif f==2:v=(x+b)&255
            elif f==3:v=(x+((a+b)//2))&255
            elif f==4:v=(x+_paeth(a,b,c))&255
            else: raise NativeImageError(f'unsupported PNG filter {f}')
            out[i]=v
        rows.append(bytes(out)); prior=out
    rgb=bytearray(width*height*3); o=0
    for row in rows:
        for i in range(0,len(row),channels):
            if color_type==0:r=g=b=row[i]
            elif color_type==2:r,g,b=row[i],row[i+1],row[i+2]
            elif color_type==4:
                gray,alpha=row[i],row[i+1]; r=g=b=(gray*alpha+255*(255-alpha))//255
            else:
                r0,g0,b0,alpha=row[i],row[i+1],row[i+2],row[i+3]
                r=(r0*alpha+255*(255-alpha))//255; g=(g0*alpha+255*(255-alpha))//255; b=(b0*alpha+255*(255-alpha))//255
            rgb[o:o+3]=bytes((r,g,b)); o+=3
    evidence={'boundary':'native-png-v0.1','width':width,'height':height,'bit_depth':bit_depth,'color_type':color_type,'interlace':interlace}
    return width,height,bytes(rgb),evidence

def encode_png_rgb(width:int,height:int,rgb:bytes)->bytes:
    if width<1 or height<1 or len(rgb)!=width*height*3: raise NativeImageError('invalid RGB image')
    def chunk(kind:bytes,payload:bytes)->bytes:
        body=kind+payload; return len(payload).to_bytes(4,'big')+body+(zlib.crc32(body)&0xffffffff).to_bytes(4,'big')
    scan=b''.join(b'\x00'+rgb[y*width*3:(y+1)*width*3] for y in range(height))
    ihdr=struct.pack('>IIBBBBB',width,height,8,2,0,0,0)
    return PNG_SIGNATURE+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(scan,9))+chunk(b'IEND',b'')
