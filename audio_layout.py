"""Build a three-voice SF2 in memory from the phone's original DLS samples.

Only functional MIDI zone/envelope parameters are described here; no sample
audio is included. Layout follows the documented SF2 conversion used during
the original sound research; see audio-source/README.md.
"""
import struct

# program, DLS wave, sample rate, root key, loop start/end, region generators
VOICES = [
    (12, 1, 15845, 70, 1933, 1967, [(43,27660),(13,20),(16,250),(22,64686),(24,64690),(30,62750),(36,2604),(37,1000),(38,386),(48,150),(54,1)]),
    (55, 23, 8000, 72, 3288, 6953, [(43,27660),(16,250),(22,63805),(24,64690),(30,62750),(34,56363),(36,3485),(37,1000),(38,1586),(48,150),(54,1)]),
    (120, 32, 16000, 49, 3370, 9194, [(43,27660),(16,250),(22,57917),(24,64690),(30,62750),(34,62252),(36,62252),(37,1000),(38,64336),(48,150),(54,1)]),
]
LENGTHS = (1969, 6955, 9196)
# Retain the source positions used by the original conversion. TinySoundFont's
# interpolation uses absolute sample positions; rebasing them can change rounding.
STARTS = (251, 49984, 78593)


def chunks(data, offset=0):
    while offset + 8 <= len(data):
        size = struct.unpack_from('<I', data, offset + 4)[0]
        if offset + 8 + size > len(data): raise ValueError('Invalid DLS chunk')
        yield data[offset:offset + 4], data[offset + 8:offset + 8 + size]
        offset += 8 + size + (size & 1)


def chunk(tag, data):
    return tag + struct.pack('<I', len(data)) + data + (b'\0' if len(data) & 1 else b'')


def build_bank(original):
    waves = None
    for tag, payload in chunks(original, 12):
        if tag == b'LIST' and payload[:4] == b'wvpl':
            waves = [dict(chunks(wave, 4))[b'data'] for _, wave in chunks(payload, 4)]
    if waves is None or len(waves) < 33: raise ValueError('Unsupported original sound bank')
    pool = bytearray(); headers = []; phdr = []; pbag = []; pgen = []; inst = []; ibag = []; igen = []
    for index, (program, wave_index, rate, key, loop_start, loop_end, region) in enumerate(VOICES):
        sample = waves[wave_index][:LENGTHS[index]]
        if len(sample) != LENGTHS[index]: raise ValueError('Unsupported sample length')
        start = STARTS[index]; end = start + len(sample)
        pool.extend(bytes(start * 2 - len(pool)))
        pool.extend(b''.join(struct.pack('<h', (value if value < 128 else value - 256) * 256) for value in sample))
        pool.extend(bytes(46 * 2))
        headers.append(struct.pack('<20sIIIIIBbHH', f'Voice{program}'.encode(), start, end, start + loop_start, start + loop_end, rate, key, 0, 0, 1))
        phdr.append(struct.pack('<20sHHHIII', f'Program{program}'.encode(), program, 0, len(pbag), 0, 0, 0))
        pbag.append((len(pgen), 0))
        if program == 12: pgen.extend([(5, 5), (22, 0)])
        pbag.append((len(pgen), 0)); pgen.append((41, index))
        inst.append(struct.pack('<20sH', f'Instrument{program}'.encode(), len(ibag)))
        ibag.append((len(igen), 0)); ibag.append((len(igen), 0))
        igen.extend(region); igen.append((53, index))
    phdr.append(struct.pack('<20sHHHIII', b'EOP', 0, 0, len(pbag), 0, 0, 0)); pbag.append((len(pgen), 0)); pgen.append((0, 0))
    inst.append(struct.pack('<20sH', b'EOI', len(ibag))); ibag.append((len(igen), 0)); igen.append((0, 0))
    end = len(pool) // 2
    headers.append(struct.pack('<20sIIIIIBbHH', b'EOS', end, end, end, end, 0, 0, 0, 0, 1))
    def pairs(values): return b''.join(struct.pack('<HH', *value) for value in values)
    tables = [(b'phdr', b''.join(phdr)), (b'pbag', pairs(pbag)), (b'pmod', bytes(10)), (b'pgen', pairs(pgen)),
              (b'inst', b''.join(inst)), (b'ibag', pairs(ibag)), (b'imod', bytes(10)), (b'igen', pairs(igen)), (b'shdr', b''.join(headers))]
    info = chunk(b'LIST', b'INFO' + chunk(b'ifil', struct.pack('<HH', 2, 1)) + chunk(b'INAM', b'Xenzia runtime voices\0'))
    samples = chunk(b'LIST', b'sdta' + chunk(b'smpl', bytes(pool)))
    parameters = chunk(b'LIST', b'pdta' + b''.join(chunk(tag, data) for tag, data in tables))
    body = b'sfbk' + info + samples + parameters
    return b'RIFF' + struct.pack('<I', len(body)) + body
