"""Long-snake rendering must not trip the guest's finite execution guard."""
import struct
import tempfile
from pathlib import Path
from runtime import NokiaRuntime, FRAME_INSTRUCTION_LIMIT, RET


def long_scene(length=100, dense_turns=False, swollen=False):
    r=NokiaRuntime();r.key('back');r.activate(0)
    field=r.word(r.state+0x24);snake=r.word(field+0x34)
    # The original program has 100 packed body entries at +0x24..+0xeb.
    assert 1<=length<=100
    if dense_turns:
        cells=[]
        for y in range(0,8,2):
            for x in range(16):
                cells.extend([(x,y),(x,y+1)] if x%2==0 else [(x,y+1),(x,y)])
    else:
        cells=[(x,y) for y in range(8) for x in (range(16) if y%2==0 else range(15,-1,-1))]
    cells=cells[:length]
    previous=cells[0]
    for i,(x,y) in enumerate(cells):
        dx,dy=x-previous[0],y-previous[1]
        direction=2 if dx>0 else 0 if dx<0 else 1 if dy>0 else 3
        packed=(x<<10)|(direction<<8)|(y<<2)|(2 if swollen else 0)
        r.u.mem_write(snake+0x24+i*2,struct.pack('>H',packed))
        previous=x,y
    r.u.mem_write(snake+0x20,struct.pack('>I',length))
    r.u.mem_write(snake+0xec,struct.pack('>I',length-1))
    r.u.mem_write(snake+4,struct.pack('>hh',*cells[-1]))
    # Do not advance a cell while measuring the complete native renderer.
    r.delay=1
    return r,snake


def main():
    old,_=long_scene()
    try:
        old.call(0x817c,old.app,old.gfx,1)
    except RuntimeError as error:
        assert 'instruction limit exceeded' in str(error),error
    else:
        raise AssertionError('fixture must reproduce the old one-million guard')
    print('Old guard rejects a valid maximum-length frame: reproduced')

    with tempfile.TemporaryDirectory() as scratch:
        for length in (32,64,100):
            for dense in (False,True):
                for swollen in (False,True):
                    r,snake=long_scene(length,dense,swollen)
                    path=Path(scratch)/'scene.state';r.save(path)
                    r.frame(1)
                    assert r.word(snake+0x20)==length
                    assert r.u.mem_read(r.state+0x1c,1)==b'\x04'
                    assert sum(r.image.convert('L').histogram()[:240])>300
                    # The budget does not alter native output or game RAM.
                    reference=NokiaRuntime(accelerated=False);reference.restore(path)
                    reference.clock+=1
                    reference.call(0x817c,reference.app,reference.gfx,1,
                                   instruction_limit=FRAME_INSTRUCTION_LIMIT*2)
                    assert r.image.tobytes()==reference.image.tobytes()
                    assert r.u.mem_read(snake,264)==reference.u.mem_read(snake,264)
                    assert r.heap==reference.heap and r.blocks==reference.blocks and r.freeblocks==reference.freeblocks
        print('32/64/100 segments, dense turns and swollen bodies: 12 full-render cases PASS')

    # Raising the frame budget must not disable runaway-program protection.
    loop=RET+0x100;r.u.mem_write(loop,b'\xe7\xfe')
    try:r.call(loop,instruction_limit=100)
    except RuntimeError as error:
        assert 'instruction limit exceeded' in str(error) and 'budget 100' in str(error)
    else:raise AssertionError('guest loop was not stopped')
    print('Finite instruction guard remains active PASS')


if __name__=='__main__':main()
