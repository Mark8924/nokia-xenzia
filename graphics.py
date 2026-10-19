"""Optional native FFI batcher; the reference Python canvas stays authoritative."""
import ctypes as C
import ctypes.util
import os
import platform
import weakref
from pathlib import Path


class Command(C.Structure):
    _fields_=[('index',C.c_int32),('lr',C.c_int32),('v',C.c_int32*4)]


class Block(C.Structure):
    _fields_=[('address',C.c_uint32),('size',C.c_uint32)]


def _dispose(lib,context,engine,hooks):
    from unicorn.unicorn_py3.unicorn import uclib
    for hook in hooks:uclib.uc_hook_del(engine,hook)
    lib.xenzia_gfx_destroy(context)


class Graphics:
    def __init__(self,runtime):
        from unicorn.unicorn_py3.unicorn import uclib
        from unicorn import UC_HOOK_BLOCK
        root=Path(__file__).resolve().parent
        machine=platform.machine().lower()
        system=platform.system()
        if system=='Linux' and 'ANDROID_ROOT' not in os.environ:
            C.CDLL(C.util.find_library('m') or 'libm.so.6',mode=C.RTLD_GLOBAL)
        name=('windows-x86_64.dll' if system=='Windows' else
              'macos-aarch64.dylib' if system=='Darwin' else
              'linux-aarch64.so' if machine in ('aarch64','arm64') else 'linux-x86_64.so')
        candidates=[root/'native/bin'/name,root/'native'/name]
        if os.environ.get('XENZIA_AUDIO_LIBRARY'):
            candidates.insert(0,Path(os.environ['XENZIA_AUDIO_LIBRARY']))
        if os.environ.get('ANDROID_ARGUMENT') or 'ANDROID_ROOT' in os.environ:
            candidates.insert(0,Path('libxenzia_audio.so'))
        self.lib=lib=next((C.CDLL(str(p)) for p in candidates if p.is_file()),None)
        if lib is None and 'ANDROID_ROOT' in os.environ:lib=self.lib=C.CDLL('libxenzia_audio.so')
        if lib is None:raise OSError('Native canvas batcher is not installed')
        ptr=C.c_void_p
        lib.xenzia_gfx_create.argtypes=[ptr]*5;lib.xenzia_gfx_create.restype=ptr
        lib.xenzia_gfx_destroy.argtypes=[ptr];lib.xenzia_gfx_destroy.restype=None
        lib.xenzia_gfx_state.argtypes=[ptr,C.c_uint32,C.c_uint32];lib.xenzia_gfx_state.restype=None
        lib.xenzia_gfx_commands.argtypes=[ptr];lib.xenzia_gfx_commands.restype=C.POINTER(Command)
        lib.xenzia_gfx_count.argtypes=[ptr];lib.xenzia_gfx_count.restype=C.c_int
        lib.xenzia_gfx_clear.argtypes=[ptr];lib.xenzia_gfx_clear.restype=None
        lib.xenzia_heap_import.argtypes=[ptr,C.c_uint32,C.c_int,ptr,C.c_int,ptr];lib.xenzia_heap_import.restype=C.c_int
        lib.xenzia_heap_export.argtypes=[ptr,ptr,ptr,ptr,ptr];lib.xenzia_heap_export.restype=C.c_uint32
        self.blocks=(Block*4096)();self.freeblocks=(Block*4096)()
        self.context=lib.xenzia_gfx_create(*(C.cast(getattr(uclib,n),ptr) for n in ('uc_reg_read','uc_reg_write','uc_mem_read','uc_mem_write','uc_emu_stop')))
        if not self.context:raise MemoryError('Canvas batch allocation failed')
        self.commands=lib.xenzia_gfx_commands(self.context)
        # Install a C callback directly through Unicorn's stable C API. Keep the
        # engine alive until our finalizer removes the hook and frees its data.
        hooks=[]
        for method,start,end in [('xenzia_gfx_hook',0x4001020,0x40010ef),('xenzia_heap_hook',0x4000070,0x400008f)]:
            handle=C.c_size_t()
            error=uclib.uc_hook_add(runtime.u._uch,C.byref(handle),UC_HOOK_BLOCK,
                                   C.cast(getattr(lib,method),ptr),self.context,
                                   C.c_uint64(start),C.c_uint64(end))
            if error:_dispose(lib,self.context,runtime.u._uch,hooks);raise OSError('Cannot install canvas hook')
            hooks.append(handle.value)
        # Register after Unicorn's own finalizer, on the SAME owner. Weakref
        # callbacks run newest first, removing our hooks before uc_close. Keep
        # only the raw handle here: retaining Uc would retain runtime -> self
        # through its callbacks and prevent every engine from being collected.
        self._finalizer=weakref.finalize(runtime.u,_dispose,lib,self.context,runtime.u._uch,hooks)
        self.sync(runtime)

    def sync(self,r):
        self.lib.xenzia_gfx_state(self.context,r.color,r.bg)
        self.push_heap(r)

    def push_heap(self,r):
        if len(r.blocks)>4096 or len(r.freeblocks)>4096:raise RuntimeError('Too many guest allocations')
        for i,(address,size) in enumerate(r.blocks.items()):self.blocks[i]=Block(address,size)
        for i,(address,size) in enumerate(r.freeblocks):self.freeblocks[i]=Block(address,size)
        if self.lib.xenzia_heap_import(self.context,r.heap,len(r.blocks),self.blocks,len(r.freeblocks),self.freeblocks):raise RuntimeError('Invalid guest heap')

    def pull_heap(self,r):
        count=C.c_int();freecount=C.c_int()
        r.heap=self.lib.xenzia_heap_export(self.context,C.byref(count),self.blocks,C.byref(freecount),self.freeblocks)
        r.blocks={self.blocks[i].address:self.blocks[i].size for i in range(count.value)}
        r.freeblocks=[(self.freeblocks[i].address,self.freeblocks[i].size) for i in range(freecount.value)]

    def drain(self,r):
        count=self.lib.xenzia_gfx_count(self.context)
        if count<0:raise RuntimeError('Native canvas command buffer exceeded its limit')
        try:
            for i in range(count):
                c=self.commands[i];r.canvas(c.index,c.v,c.lr)
        finally:self.lib.xenzia_gfx_clear(self.context)


def create(runtime):
    if os.environ.get('NOKIA_SOFTWARE_GFX'):return None
    try:return Graphics(runtime)
    except (OSError,AttributeError,ImportError):return None
