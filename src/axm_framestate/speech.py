from __future__ import annotations

import hashlib
import re
import wave
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from .canonical import digest
from .three_d import sincos_mdeg

SAMPLE_RATE = 48_000
SYNTH_SCHEMA = 'axm.framestate.native-speech/v0.1'
TABLE_SIZE = 2048
_PHASE_MOD = 1 << 32

# Build the oscillator table with FrameState's integer CORDIC primitive. No host
# speech engine, floating trig function, model, network, or downloaded voice is
# involved in native synthesis.
_SIN_TABLE = tuple((sincos_mdeg(i * 360_000 // TABLE_SIZE)[0] * 32767) // 1_000_000 for i in range(TABLE_SIZE))


@dataclass(frozen=True)
class Phoneme:
    symbol: str
    duration_ms: int
    voiced: bool
    formants: tuple[int, int, int]
    noise_milli: int = 0
    amplitude_milli: int = 700


# Intentionally small, inspectable first-generation formant vocabulary. These
# values are construction parameters, not claims about universal human speech.
P: dict[str, Phoneme] = {
    'AA': Phoneme('AA', 105, True, (730, 1090, 2440), amplitude_milli=760),
    'AE': Phoneme('AE', 105, True, (660, 1720, 2410), amplitude_milli=760),
    'AH': Phoneme('AH', 95, True, (640, 1190, 2390), amplitude_milli=730),
    'AO': Phoneme('AO', 105, True, (570, 840, 2410), amplitude_milli=760),
    'EH': Phoneme('EH', 95, True, (530, 1840, 2480), amplitude_milli=740),
    'ER': Phoneme('ER', 110, True, (490, 1350, 1690), amplitude_milli=720),
    'IH': Phoneme('IH', 90, True, (400, 1990, 2550), amplitude_milli=720),
    'IY': Phoneme('IY', 105, True, (270, 2290, 3010), amplitude_milli=720),
    'UH': Phoneme('UH', 90, True, (440, 1020, 2240), amplitude_milli=720),
    'UW': Phoneme('UW', 105, True, (300, 870, 2240), amplitude_milli=720),
    'EY': Phoneme('EY', 115, True, (500, 1900, 2550), amplitude_milli=735),
    'AY': Phoneme('AY', 125, True, (650, 1500, 2500), amplitude_milli=745),
    'OW': Phoneme('OW', 120, True, (500, 950, 2400), amplitude_milli=740),
    'AW': Phoneme('AW', 125, True, (700, 1200, 2500), amplitude_milli=745),
    'OY': Phoneme('OY', 125, True, (550, 1100, 2400), amplitude_milli=740),
    'B':  Phoneme('B', 55, True, (300, 800, 2100), amplitude_milli=520),
    'D':  Phoneme('D', 50, True, (350, 1700, 2600), amplitude_milli=500),
    'G':  Phoneme('G', 55, True, (300, 1300, 2400), amplitude_milli=500),
    'JH': Phoneme('JH', 75, True, (400, 1800, 2700), noise_milli=250, amplitude_milli=560),
    'V':  Phoneme('V', 75, True, (350, 1350, 2500), noise_milli=320, amplitude_milli=520),
    'Z':  Phoneme('Z', 75, True, (350, 1800, 3000), noise_milli=360, amplitude_milli=520),
    'ZH': Phoneme('ZH', 85, True, (350, 1550, 2600), noise_milli=330, amplitude_milli=520),
    'DH': Phoneme('DH', 70, True, (350, 1450, 2500), noise_milli=260, amplitude_milli=500),
    'M':  Phoneme('M', 85, True, (250, 1100, 2100), amplitude_milli=500),
    'N':  Phoneme('N', 80, True, (300, 1500, 2500), amplitude_milli=500),
    'NG': Phoneme('NG', 90, True, (300, 1150, 2300), amplitude_milli=500),
    'L':  Phoneme('L', 80, True, (400, 1300, 2600), amplitude_milli=540),
    'R':  Phoneme('R', 85, True, (400, 1200, 1700), amplitude_milli=540),
    'W':  Phoneme('W', 75, True, (300, 900, 2200), amplitude_milli=520),
    'Y':  Phoneme('Y', 70, True, (280, 2200, 3000), amplitude_milli=520),
    'F':  Phoneme('F', 85, False, (900, 2600, 4200), noise_milli=900, amplitude_milli=480),
    'S':  Phoneme('S', 90, False, (1200, 3500, 5200), noise_milli=1000, amplitude_milli=500),
    'SH': Phoneme('SH', 95, False, (900, 2400, 3900), noise_milli=950, amplitude_milli=500),
    'TH': Phoneme('TH', 85, False, (800, 2500, 4300), noise_milli=850, amplitude_milli=470),
    'HH': Phoneme('HH', 70, False, (700, 1800, 3200), noise_milli=720, amplitude_milli=400),
    'P':  Phoneme('P', 55, False, (700, 2200, 3800), noise_milli=650, amplitude_milli=430),
    'T':  Phoneme('T', 50, False, (1000, 3200, 4800), noise_milli=700, amplitude_milli=440),
    'K':  Phoneme('K', 60, False, (800, 1800, 3400), noise_milli=680, amplitude_milli=440),
    'CH': Phoneme('CH', 80, False, (900, 2600, 4200), noise_milli=850, amplitude_milli=470),
}

VOICE_PROFILES: dict[str, dict[str, int]] = {
    'native-neutral-1': {'f0_hz': 122, 'formant_scale_milli': 1000, 'amplitude_milli': 1000},
    'native-low-1': {'f0_hz': 96, 'formant_scale_milli': 920, 'amplitude_milli': 1050},
    'native-bright-1': {'f0_hz': 158, 'formant_scale_milli': 1080, 'amplitude_milli': 920},
}
VOICE_ALIASES = {'en': 'native-neutral-1', 'default': 'native-neutral-1', 'native': 'native-neutral-1'}

# A small deterministic pronunciation core, deliberately visible and extensible.
# Fallback grapheme rules cover unknown words; lexicon entries improve high-value
# words without relying on OS dictionaries or downloaded language models.
LEXICON: dict[str, tuple[str, ...]] = {
    'a': ('AH',), 'an': ('AE','N'), 'and': ('AE','N','D'), 'are': ('AA','R'),
    'as': ('AE','Z'), 'be': ('B','IY'), 'can': ('K','AE','N'), 'deterministic': ('D','IH','T','ER','M','IH','N','IH','S','T','IH','K'),
    'frame': ('F','R','EY','M'), 'framestate': ('F','R','EY','M','S','T','EY','T'),
    'from': ('F','R','AH','M'), 'hello': ('HH','EH','L','OW'), 'in': ('IH','N'),
    'is': ('IH','Z'), 'it': ('IH','T'), 'its': ('IH','T','S'), 'machine': ('M','AH','SH','IY','N'),
    'native': ('N','EY','T','IH','V'), 'of': ('AH','V'), 'offline': ('AO','F','L','AY','N'),
    'own': ('OW','N'), 'render': ('R','EH','N','D','ER'), 'speaks': ('S','P','IY','K','S'),
    'speech': ('S','P','IY','CH'), 'state': ('S','T','EY','T'), 'the': ('DH','AH'),
    'this': ('DH','IH','S'), 'to': ('T','UW'), 'video': ('V','IH','D','IY','OW'),
    'voice': ('V','OY','S'), 'with': ('W','IH','TH'), 'without': ('W','IH','DH','AW','T'),
    'you': ('Y','UW'), 'zero': ('Z','IH','R','OW'), 'external': ('EH','K','S','T','ER','N','AH','L'),
}

DIGRAPHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('tion', ('SH','AH','N')), ('sion', ('ZH','AH','N')), ('tch', ('CH',)),
    ('igh', ('AY',)), ('eigh', ('EY',)), ('ough', ('AW',)), ('ph', ('F',)),
    ('sh', ('SH',)), ('ch', ('CH',)), ('th', ('TH',)), ('ng', ('NG',)),
    ('qu', ('K','W')), ('ee', ('IY',)), ('ea', ('IY',)), ('oo', ('UW',)),
    ('ai', ('EY',)), ('ay', ('EY',)), ('oa', ('OW',)), ('oi', ('OY',)), ('oy', ('OY',)),
    ('ou', ('AW',)), ('ow', ('AW',)), ('er', ('ER',)), ('ar', ('AA','R')), ('or', ('AO','R')),
)


def _fallback_word(word: str) -> tuple[str, ...]:
    w = re.sub(r'[^a-z]', '', word.lower())
    if not w:
        return ()
    # crude silent-e handling for the first native generation
    silent_final_e = len(w) > 2 and w.endswith('e') and not w.endswith(('ee','oe','ye'))
    limit = len(w) - 1 if silent_final_e else len(w)
    out: list[str] = []
    i = 0
    while i < limit:
        matched = False
        for pat, phones in DIGRAPHS:
            if i + len(pat) <= limit and w.startswith(pat, i):
                out.extend(phones); i += len(pat); matched = True; break
        if matched:
            continue
        c = w[i]
        nxt = w[i+1] if i+1 < len(w) else ''
        prev = w[i-1] if i else ''
        if c == 'a': out.append('EY' if silent_final_e and i == limit-2 else 'AE')
        elif c == 'e': out.append('EH')
        elif c == 'i': out.append('AY' if silent_final_e and i == limit-2 else 'IH')
        elif c == 'o': out.append('OW' if silent_final_e and i == limit-2 else 'AO')
        elif c == 'u': out.append('UW' if silent_final_e and i == limit-2 else 'AH')
        elif c == 'b': out.append('B')
        elif c == 'c': out.append('S' if nxt in 'eiy' else 'K')
        elif c == 'd': out.append('D')
        elif c == 'f': out.append('F')
        elif c == 'g': out.append('JH' if nxt in 'eiy' else 'G')
        elif c == 'h': out.append('HH')
        elif c == 'j': out.append('JH')
        elif c == 'k': out.append('K')
        elif c == 'l': out.append('L')
        elif c == 'm': out.append('M')
        elif c == 'n': out.append('N')
        elif c == 'p': out.append('P')
        elif c == 'q': out.extend(('K','W'))
        elif c == 'r': out.append('R')
        elif c == 's': out.append('Z' if prev in 'aeiou' and nxt in 'aeiou' else 'S')
        elif c == 't': out.append('T')
        elif c == 'v': out.append('V')
        elif c == 'w': out.append('W')
        elif c == 'x': out.extend(('K','S'))
        elif c == 'y': out.append('Y' if i == 0 else 'IY')
        elif c == 'z': out.append('Z')
        i += 1
    return tuple(out)


def text_to_phonemes(text: str) -> list[dict[str, Any]]:
    tokens = re.findall(r"[A-Za-z']+|[.,!?;:]", text)
    result: list[dict[str, Any]] = []
    word_index = 0
    for token in tokens:
        if token in '.,!?;:':
            result.append({'kind':'pause','symbol':'SIL','duration_ms': 190 if token in '.!?' else 110, 'punctuation':token})
            continue
        word = token.lower().strip("'")
        phones = LEXICON.get(word) or _fallback_word(word)
        if not phones:
            continue
        if word_index:
            result.append({'kind':'pause','symbol':'SP','duration_ms':35})
        for symbol in phones:
            ph = P[symbol]
            result.append({'kind':'phoneme','symbol':symbol,'duration_ms':ph.duration_ms})
        word_index += 1
    return result


def _sin(phase: int) -> int:
    return _SIN_TABLE[(phase >> (32 - 11)) & (TABLE_SIZE - 1)]


def _inc(freq_hz: int) -> int:
    return max(1, (int(freq_hz) * _PHASE_MOD) // SAMPLE_RATE)


def _lcg(state: int) -> tuple[int, int]:
    state = (1664525 * state + 1013904223) & 0xFFFFFFFF
    return state, ((state >> 16) & 0xFFFF) - 32768


def _voice_profile(name: str) -> tuple[str, dict[str, int]]:
    n = VOICE_ALIASES.get(name, name)
    if n not in VOICE_PROFILES:
        raise ValueError(f'unsupported native voice profile: {name}')
    return n, VOICE_PROFILES[n]


def synthesize_native(text: str, voice: str='native-neutral-1', rate_wpm: int=165) -> tuple[bytes, dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return b'', {'schema':SYNTH_SCHEMA,'voice':'native-neutral-1','rate_wpm':rate_wpm,'phonemes':[],'phoneme_digest':digest([]),'sample_rate':SAMPLE_RATE,'sample_count':0,'pcm_digest':'sha256:'+hashlib.sha256(b'').hexdigest()}
    if rate_wpm < 80 or rate_wpm > 450:
        raise ValueError('rate_wpm must be between 80 and 450')
    voice_name, profile = _voice_profile(voice)
    seq = text_to_phonemes(text)
    rate_scale = (165_000 // rate_wpm)  # milli
    seed = int.from_bytes(hashlib.sha256((voice_name+'\0'+text).encode('utf-8')).digest()[:4], 'little') or 1
    phases = [0,0,0,0]
    out: list[int] = []
    phoneme_rows: list[dict[str, Any]] = []

    phone_indices=[i for i,r in enumerate(seq) if r['kind']=='phoneme']
    for pos,row in enumerate(seq):
        dur_ms=max(12, int(row['duration_ms']) * rate_scale // 1000)
        n=max(1, dur_ms * SAMPLE_RATE // 1000)
        if row['kind']=='pause':
            out.extend([0]*n)
            phoneme_rows.append({'symbol':row['symbol'],'duration_ms':dur_ms,'samples':n})
            continue
        ph=P[row['symbol']]
        # Find nearest voiced/phoneme neighbors for smooth deterministic formant travel.
        prev_form=ph.formants; next_form=ph.formants
        j=pos-1
        while j>=0:
            if seq[j]['kind']=='phoneme': prev_form=P[seq[j]['symbol']].formants; break
            j-=1
        j=pos+1
        while j<len(seq):
            if seq[j]['kind']=='phoneme': next_form=P[seq[j]['symbol']].formants; break
            j+=1
        attack=max(1,min(n//5,SAMPLE_RATE//100)); release=attack
        f0=profile['f0_hz']
        for k in range(n):
            # Transition through current target, entering from previous and leaving toward next.
            if k < n//3:
                t=(k*1000)//max(1,n//3); a=prev_form; b=ph.formants
            elif k > (2*n)//3:
                t=((k-(2*n)//3)*1000)//max(1,n-(2*n)//3); a=ph.formants; b=next_form
            else:
                t=1000; a=ph.formants; b=ph.formants
            form=[]
            for ai,bi in zip(a,b):
                f=(ai*(1000-t)+bi*t)//1000
                f=f*profile['formant_scale_milli']//1000
                form.append(max(40,min(9000,f)))
            phases[0]=(phases[0]+_inc(f0))&0xFFFFFFFF
            tonal=0
            if ph.voiced:
                tonal += _sin(phases[0])*180//1000
            weights=(470,285,145)
            for q,(freq,w) in enumerate(zip(form,weights),start=1):
                phases[q]=(phases[q]+_inc(freq))&0xFFFFFFFF
                tonal += _sin(phases[q])*w//1000
            noise=0
            if ph.noise_milli:
                seed,rnd=_lcg(seed);noise=rnd*ph.noise_milli//1000
            v=(tonal + noise) * ph.amplitude_milli // 1000
            v=v*profile['amplitude_milli']//1000
            env=1000
            if k<attack: env=k*1000//attack
            elif k>=n-release: env=(n-1-k)*1000//release
            v=v*max(0,env)//1000
            out.append(max(-32768,min(32767,v)))
        phoneme_rows.append({'symbol':ph.symbol,'duration_ms':dur_ms,'samples':n,'voiced':ph.voiced,'formants_hz':list(ph.formants)})

    # Pack little-endian s16 PCM without using any external decoder/conformer.
    pcm=bytearray(len(out)*2)
    for i,v in enumerate(out):
        u=v & 0xFFFF
        pcm[2*i]=u & 0xFF; pcm[2*i+1]=(u>>8)&0xFF
    raw=bytes(pcm)
    evidence={
        'schema':SYNTH_SCHEMA,
        'engine':'native',
        'synthesizer':'FrameState Native Speech v0.1',
        'voice':voice_name,
        'rate_wpm':rate_wpm,
        'text_digest':digest(text),
        'phoneme_digest':digest(phoneme_rows),
        'phonemes':phoneme_rows,
        'sample_rate':SAMPLE_RATE,
        'sample_count':len(out),
        'pcm_digest':'sha256:'+hashlib.sha256(raw).hexdigest(),
        'external_dependencies':[],
    }
    evidence['receipt_digest']=digest(evidence)
    return raw,evidence


def write_native_wav(text: str, path: Path, voice: str='native-neutral-1', rate_wpm: int=165) -> dict[str, Any]:
    pcm,evidence=synthesize_native(text,voice,rate_wpm)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(SAMPLE_RATE);wf.writeframes(pcm)
    result={**evidence,'wav_path':str(path),'wav_digest':'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()}
    result['write_receipt_digest']=digest(result)
    return result
