"""Clock accounting, immediate tones, and native canvas equivalence regressions."""
import tempfile,time,struct,json,gc,weakref
from pathlib import Path
from unittest import mock
from runtime import NokiaRuntime
from test_frame_budget import long_scene
from graphics import Graphics


def main():
    r=NokiaRuntime();engine=weakref.ref(r.u);owner=weakref.ref(r)
    del r;gc.collect()
    assert owner() is None and engine() is None,'native helper must not retain old game sessions'
    print('Discarded sessions and native engines are collected PASS')
    # Simulate a costly frame without depending on the test machine's speed.
    r=NokiaRuntime();r.key('back');r.activate(0)
    clock=r.clock
    def work(*_,**__):
        r.delay=35;r._next_deadline=time.perf_counter()+.035
        time.sleep(.040)
    with mock.patch.object(r,'call',work):r.frame(realtime=True)
    assert r.clock-clock>=75,(r.clock-clock,'render work was missing from guest clock')
    assert r.wait_ms()==1,'expired timer must not add a whole new frame interval'
    assert r.menu is None
    print('Busy-frame work counts toward guest clock; expired timer has no added frame wait PASS')

    r=NokiaRuntime();heard=[]
    r.sound_sink=lambda command:heard.append((command,len(r.sounds)))
    r.call(0x9fa2,r.state+0x64,0)
    assert len(heard)==1 and heard[0][1]==1 and heard[0][0]==r.sounds[0]
    try:from session import Session
    except ImportError:from ports.session import Session
    with tempfile.TemporaryDirectory() as directory:
        game=Session(directory);played=[];game.audio_sink=played.append
        game.runtime.call(0x9fa2,game.runtime.state+0x64,0)
        assert played==['effect-0'] and json.loads(game.take_audio())==[]
        game.configure('muted',True);game.runtime.call(0x9fa2,game.runtime.state+0x64,0)
        assert len(played)==1
    print('Original sound dispatch occurs at the native event; no later replay; mute preserved PASS')

    # Compare every guest RAM arena and frame against the Python-only path.
    with tempfile.TemporaryDirectory() as directory:
        for length in (1,32,64,100):
            r,snake=long_scene(length,True,True)
            assert r.graphics is not None,'this test must exercise the native batcher'
            path=Path(directory)/'fixture';r.save(path)
            reference=NokiaRuntime(accelerated=False);reference.restore(path)
            for step in range(4):
                r.delay=reference.delay=1;r.frame_for_display();reference.frame_for_display()
                assert r.image.tobytes()==reference.image.tobytes(),(length,step,'pixels')
                assert r.heap==reference.heap and r.blocks==reference.blocks and r.freeblocks==reference.freeblocks
                for address,size in ((0x2000000,0x10000),(0x2100000,r.heap-0x2100000),(0x3000000,0x10000)):
                    assert r.u.mem_read(address,size)==reference.u.mem_read(address,size),(length,step,hex(address))
    print('1/32/64/100 segments: 16 frames, every pixel and all guest RAM match the reference PASS')

    # Native allocator coalescing and zero-on-reuse must match the Python API.
    r=NokiaRuntime();reference=NokiaRuntime(accelerated=False)
    r.alloc(32);reference.alloc(32)
    allocated=[]
    for n in (1,17,88,256,11):
        p=r.call(0x4000070,0,n);q=reference.call(0x4000070,0,n);assert p==q;allocated.append(p)
    for p in allocated[1:]:r.call(0x4000080,0,p);reference.call(0x4000080,0,p)
    for n in (256,17,1):assert r.call(0x4000070,0,n)==reference.call(0x4000070,0,n)
    assert r.blocks==reference.blocks and r.freeblocks==reference.freeblocks
    print('Native allocator split, coalesce, zero-on-reuse and Python interop PASS')


if __name__=='__main__':main()
