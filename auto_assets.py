"""Prepare supported resources on-device from verified public source archives.

The application ships this extraction code, not the original game program.
No save or preference file is read, replaced or included in this process.
"""
import array
import ctypes
import ctypes.util
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import shutil
import ssl
import struct
import sys
import tempfile
import time
import urllib.request
import wave
import zlib

from asset_store import complete, ensure_assets, manifest, matches_hash

ROOT = Path(__file__).resolve().parent
FIRMWARE_URL = 'https://firmware.center/firmware/Nokia/1110i%20%281112%29/Flash%20Files/RH-093%20v.07.02%201110i%201112.rar'
FIRMWARE_SHA256 = 'aeae974329c84a51882ff3956a0302228ae207cbeb1df23a7071ba85ebe0059f'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(url, target, expected, size, progress):
    if target.is_file() and target.stat().st_size == size and digest(target.read_bytes()) == expected:
        progress(100)
        return target.read_bytes()
    context = ssl.create_default_context(cafile=str(ROOT / 'certs/cacert.pem'))
    temporary = target.with_suffix('.part')
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'SnakeXenzia/1.1 (+https://github.com/Mark8924/nokia-xenzia)'})
            with urllib.request.urlopen(request, timeout=20, context=context) as response, temporary.open('wb') as output:
                received = 0
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > size:
                        raise ValueError('Downloaded file exceeds the supported size')
                    output.write(chunk)
                    progress(min(99, received * 100 // size))
            data = temporary.read_bytes()
            if len(data) != size or digest(data) != expected:
                raise ValueError('Downloaded file failed integrity verification')
            os.replace(temporary, target)
            progress(100)
            return data
        except (OSError, ValueError, http.client.HTTPException) as error:
            last_error = error
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError('无法获取游戏数据，请检查网络后重试。 / Unable to download game data. Check your connection and retry.') from last_error


def stored_rar_files(data):
    """Read the two required stored records; the unrelated compressed PM is skipped."""
    if not data.startswith(b'Rar!\x1a\x07\x00'):
        raise ValueError('Unsupported archive')
    wanted = {'rh93_07.02ej', 'rh930_nai7.02ej'}
    result, position = {}, 7
    while position + 7 <= len(data):
        _, kind, flags, header_size = struct.unpack_from('<HBHH', data, position)
        if header_size < 7 or position + header_size > len(data):
            raise ValueError('Invalid archive header')
        packed = 0
        if kind == 0x74:
            if header_size < 32 or flags & 0x100:
                raise ValueError('Unsupported archive record')
            packed, unpacked = struct.unpack_from('<II', data, position + 7)
            checksum = struct.unpack_from('<I', data, position + 16)[0]
            method = data[position + 25]
            name_size = struct.unpack_from('<H', data, position + 26)[0]
            name = data[position + 32:position + 32 + name_size].decode('ascii')
            if name in wanted:
                if method != 0x30 or packed != unpacked or packed > 4 * 1024 * 1024:
                    raise ValueError('Required firmware record is not stored')
                content = data[position + header_size:position + header_size + packed]
                if len(content) != unpacked or zlib.crc32(content) != checksum:
                    raise ValueError('Firmware record checksum mismatch')
                result[name] = content
        elif flags & 0x8000:
            packed = struct.unpack_from('<I', data, position + 7)[0]
        position += header_size + packed
    if set(result) != wanted:
        raise ValueError('Supported firmware records not found')
    return result


def flash_records(data):
    """Unwrap bounded DCT4 distribution records; decoding is a separate step."""
    position = 5 + int.from_bytes(data[1:5], 'big')
    records = []
    while position < len(data):
        marker = data[position]
        position += 1
        if marker == 0x21:
            position += 5
        elif marker == 0x20:
            position += 5 + int.from_bytes(data[position + 2:position + 4], 'big')
        elif marker == 0x14:
            address = int.from_bytes(data[position:position + 4], 'big')
            length = int.from_bytes(data[position + 5:position + 8], 'big')
            position += 9
            if length > 4 * 1024 * 1024 or position + length > len(data):
                raise ValueError('Invalid flash record')
            records.append((address, data[position:position + length]))
            position += length
        else:
            raise ValueError('Unknown flash record')
    if not records:
        raise ValueError('Empty firmware')
    start = min(address for address, _ in records)
    end = max(address + len(content) for address, content in records)
    if end - start > 4 * 1024 * 1024:
        raise ValueError('Unsupported flash range')
    output = bytearray(end - start)
    for address, content in records:
        output[address - start:address - start + len(content)] = content
    return output, start


def decode_range(data, base, offset, length):
    from dct4_format import decode_region
    return decode_region(data, base, offset, length, 0x1b85)


def extract_program(records, target, progress):
    ppm, ppm_base = flash_records(records['rh93_07.02ej'])
    nai, nai_base = flash_records(records['rh930_nai7.02ej'])
    if ppm_base != 0x011e0000 or nai_base != 0x01380000:
        raise ValueError('Unsupported firmware layout')
    progress('正在准备游戏画面… / Preparing game graphics…', 55)
    decoded = decode_range(nai, nai_base, 0, 0x6b20)
    (target / 'snake-code.bin').write_bytes(decoded[0xb28:0xb28 + 24124])
    (target / 'snake-data.bin').write_bytes(decoded[0x696c:0x696c + 436])
    labels = []
    for offset in struct.unpack('>29I', decoded[0x808:0x87c]):
        labels.append('' if offset == 0xffffffff else decoded[0x884 + offset:0xb20].decode('utf-16-be').split('\0')[0])
    (target / 'texts.json').write_text(json.dumps(labels, indent=2), encoding='utf-8', newline='\n')
    font_data = decode_range(ppm, ppm_base, 0, 0x2ca5c)
    fonts = {}
    for number in (2, 3, 8, 9, 10):
        header = 0x3f8c + 44 * number
        glyphs, _, cmap = struct.unpack_from('>3I', font_data, header)
        glyphs += header; cmap += header
        count = struct.unpack_from('>H', font_data, header + 14)[0] + 1
        characters = {}
        for index in range(count):
            first, last, offset, flags = struct.unpack_from('>HHII', font_data, cmap + 12 * index)
            group, height, baseline = flags >> 27, (flags >> 22) & 31, (flags >> 17) & 31
            entry = glyphs + 12 * group
            pixels = entry + struct.unpack_from('>I', font_data, entry)[0]
            width = struct.unpack_from('>H', font_data, entry + 6)[0]
            for codepoint in range(first, min(last + 1, 128)):
                if codepoint < 32 or not width or height > 30:
                    continue
                rows = []
                for y in range(height):
                    bit = offset + (codepoint - first) * height + y
                    rows.append(''.join('1' if font_data[pixels + (bit // 8) * width + x] & (1 << (bit % 8)) else '0' for x in range(width)))
                characters[chr(codepoint)] = {'width': width, 'height': height, 'baseline': baseline, 'rows': rows}
        fonts[str(number)] = characters
    (target / 'fonts.json').write_text(json.dumps(fonts), encoding='utf-8', newline='\n')
    audio = target / 'audio'; audio.mkdir()
    bank = decode_range(ppm, ppm_base, 0x159c40, 130556)
    (audio / 'original-rh93.dls').write_bytes(bank)


def audio_library():
    explicit = os.environ.get('XENZIA_AUDIO_LIBRARY')
    if explicit:
        return ctypes.CDLL(explicit)
    machine = platform.machine().lower()
    machine = {'arm64': 'aarch64', 'amd64': 'x86_64'}.get(machine, machine)
    if sys.platform == 'darwin': name = 'macos-aarch64.dylib'
    elif sys.platform == 'win32': name = 'windows-x86_64.dll'
    else:
        ctypes.CDLL(ctypes.util.find_library('m') or 'libm.so.6', mode=ctypes.RTLD_GLOBAL)
        name = 'linux-' + machine + '.so'
    path = ROOT / 'native' / name
    if not path.exists(): path = ROOT / 'native/bin' / name
    return ctypes.CDLL(str(path))


def render_sounds(target, bank):
    library = audio_library()
    render = library.xenzia_render
    render.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int]
    render.restype = ctypes.c_int
    bank_memory = ctypes.create_string_buffer(bank)
    capacity = 22050 * 11
    output = (ctypes.c_short * capacity)()
    code = (target / 'snake-code.bin').read_bytes()
    profiles = {}
    names = {120: 'Fret Noise / CRASH', 12: 'Marimba / VIBAs4', 55: 'Orchestra Hit / ORCHC5D'}
    for index in range(7):
        program, note, duration, repeat = struct.unpack_from('>4h', code, 0x5d70 + index * 8)
        command = (note, 0, program, repeat, 0, duration, 100, 100)
        key = ','.join(map(str, command))
        if key in profiles:
            continue
        count = render(bank_memory, len(bank), program, note, duration, output, capacity)
        if count < 1:
            raise RuntimeError('Unable to prepare game sounds: ' + str(count))
        samples = array.array('h', output[:count])
        last = len(samples) - 1
        while last > round(22050 * duration / 1000) and abs(samples[last]) < 8:
            last -= 1
        samples = samples[:min(len(samples), last + int(22050 * .01))]
        if sys.byteorder != 'little': samples.byteswap()
        raw = samples.tobytes(); filename = 'effect-' + str(min(index, 4)) + '.s16le'
        (target / 'audio' / filename).write_bytes(raw)
        profiles[key] = {'file': filename, 'program': program, 'note': note, 'note_off_ms': duration, 'instrument': names[program], 'frames': len(samples), 'sha256': digest(raw)}
    (target / 'audio/effects.json').write_text(json.dumps(profiles, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def obtain(data, progress=lambda message, percent: None, *, firmware=None):
    """Download, extract, verify, and atomically install; keep user progress untouched."""
    data = Path(data)
    if ensure_assets(data):
        return True
    data.mkdir(parents=True, exist_ok=True)
    cache = data / 'download-cache'; cache.mkdir(exist_ok=True)
    if firmware is None:
        firmware = download(FIRMWARE_URL, cache / 'rh93.rar', FIRMWARE_SHA256, 3700384,
                            lambda value: progress('正在下载游戏数据… / Downloading game data…', value * 50 // 100))
    if digest(firmware) != FIRMWARE_SHA256:
        raise ValueError('Source archive integrity check failed')
    with tempfile.TemporaryDirectory(prefix='prepare-', dir=data) as temporary:
        target = Path(temporary) / 'assets'; target.mkdir()
        shutil.copyfile(ROOT / 'assets/icon.png', target / 'icon.png')
        extract_program(stored_rar_files(firmware), target, progress)
        progress('正在准备游戏音效… / Preparing game sounds…', 80)
        from audio_layout import build_bank
        bank = build_bank((target / 'audio/original-rh93.dls').read_bytes())
        (target / 'audio/nokia-rh93.sf2').write_bytes(bank)
        render_sounds(target, bank)
        for pcm in (target / 'audio').glob('effect-*.s16le'):
            with wave.open(str(pcm.with_suffix('.wav')), 'wb') as output:
                output.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                output.writeframes(pcm.read_bytes())
        progress('正在校验游戏数据… / Verifying game data…', 95)
        if not complete(target):
            failed = [name for name, expected in manifest().items() if not (target / name).is_file() or not matches_hash((target / name).read_bytes(), expected)]
            raise ValueError('Prepared resource verification failed: ' + ', '.join(failed))
        destination, previous = data / 'assets', data / 'assets.previous'
        if previous.exists(): shutil.rmtree(previous)
        if destination.exists(): destination.rename(previous)
        try: target.rename(destination)
        except OSError:
            if previous.exists(): previous.rename(destination)
            raise
        if previous.exists(): shutil.rmtree(previous)
    progress('准备完成 / Ready', 100)
    return ensure_assets(data)
