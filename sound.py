"""Original Nokia sampled effects on an app-local low-latency audio stream.

The original game selects note, bank, instrument, duration and levels. PCM uses
samples extracted from RH-93's embedded DLS, rendered offline with TinySoundFont.
The original DSP and phone speaker response are not emulated.
"""
import ctypes,ctypes.util,json,logging,queue,threading
from pathlib import Path
from asset_store import resource

RATE=22050
AUDIO=resource('audio')
EFFECTS=json.loads((AUDIO/'effects.json').read_text())


def synthesize(command):
    # Kept as a small loader so the audio worker never synthesizes samples or
    # starts a player process while the main game thread is accepting input.
    effect=EFFECTS.get(','.join(map(str,command)))
    if effect is None:
        logging.warning('Unsupported original sound parameters: %s',command)
        return b''
    return (AUDIO/effect['file']).read_bytes()



class SampleSpec(ctypes.Structure):
    _fields_=[('format',ctypes.c_int),('rate',ctypes.c_uint32),('channels',ctypes.c_uint8)]


class BufferAttr(ctypes.Structure):
    _fields_=[(n,ctypes.c_uint32) for n in ('maxlength','tlength','prebuf','minreq','fragsize')]


class PulseStream:
    def __init__(self):
        lib=ctypes.CDLL(ctypes.util.find_library('pulse-simple') or 'libpulse-simple.so.0')
        self.lib=lib;ptr=ctypes.c_void_p;error=ctypes.POINTER(ctypes.c_int)
        lib.pa_simple_new.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p,ctypes.POINTER(SampleSpec),ptr,ctypes.POINTER(BufferAttr),error]
        lib.pa_simple_new.restype=ptr
        lib.pa_simple_write.argtypes=[ptr,ptr,ctypes.c_size_t,error];lib.pa_simple_write.restype=ctypes.c_int
        lib.pa_simple_flush.argtypes=[ptr,error];lib.pa_simple_flush.restype=ctypes.c_int
        lib.pa_simple_free.argtypes=[ptr];lib.pa_simple_free.restype=None
        self.error=ctypes.c_int();spec=SampleSpec(3,RATE,1) # PA_SAMPLE_S16LE
        chunk=round(RATE*.01)*2;target=chunk*3
        attr=BufferAttr(target*2,target,chunk,chunk,0xffffffff)
        self.stream=lib.pa_simple_new(None,b'Snake Xenzia',1,None,b'Original Nokia sampled effects',ctypes.byref(spec),None,ctypes.byref(attr),ctypes.byref(self.error))
        if not self.stream:raise RuntimeError(f'PulseAudio connection error {self.error.value}')

    def write(self,pcm):
        if self.lib.pa_simple_write(self.stream,pcm,len(pcm),ctypes.byref(self.error))<0:raise RuntimeError(f'Audio write error {self.error.value}')

    def flush(self):self.lib.pa_simple_flush(self.stream,ctypes.byref(self.error))

    def close(self):
        if self.stream:self.lib.pa_simple_free(self.stream);self.stream=None


class TonePlayer:
    def __init__(self):
        self.commands=queue.Queue();self.thread=None;self.cache={};self.closed=False

    def play(self,command):
        if self.closed:return
        self.commands.put(tuple(command))
        if self.thread is None:
            self.thread=threading.Thread(target=self.run,name='nokia-tone-player',daemon=True);self.thread.start()

    def stop(self):self.commands.put('stop')

    def close(self):
        self.closed=True;self.commands.put('quit')

    def run(self):
        stream=None;pcm=b'';position=0;chunk=round(RATE*.01)*2
        try:
            while True:
                try:command=self.commands.get(timeout=0 if position<len(pcm) else 1)
                except queue.Empty:
                    command=None
                    if position>=len(pcm):
                        if stream:stream.close();stream=None
                        continue
                # A new tone replaces the previous tone, as on the phone's
                # monophonic channel. Never discard it because old audio plays.
                if command is not None:
                    if command=='quit':break
                    if stream:stream.flush()
                    if command=='stop':pcm=b'';position=0;continue
                    if command not in self.cache:
                        if len(self.cache)>=64:self.cache.clear()
                        self.cache[command]=synthesize(command)
                    pcm=self.cache[command];position=0
                if position<len(pcm):
                    if stream is None:stream=PulseStream()
                    stream.write(pcm[position:position+chunk]);position+=chunk
        except Exception:logging.exception('Game tone playback failed')
        finally:
            if stream:stream.close()
            self.thread=None
