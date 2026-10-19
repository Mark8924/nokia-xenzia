"""Regression tests for the phone APIs used by the original game binary."""
from runtime import NokiaRuntime, Image, ImageOps
from pathlib import Path
import tempfile, json, zlib, struct, hashlib


def main():
    r=NokiaRuntime()
    for filename,digest in json.loads((Path(__file__).parent/'assets/manifest.json').read_text()).items():
        assert hashlib.sha256((Path(__file__).parent/'assets'/filename).read_bytes()).hexdigest()==digest

    # Run Nokia's original circle routine. In particular the extreme scanlines
    # have width=0 and height=1: these must remain visible single pixels.
    for radius,widths in [(1,[1,3,1]),(3,[3,5,7,7,7,5,3])]:
        r.image.paste('white',(0,0,96,65));r.pen='#000000'
        r.call(0xb76e,r.gfx,48,30,radius)
        rows=[]
        for y in range(30-radius,31+radius):
            points=[x for x in range(96) if r.image.getpixel((x,y))!=(255,255,255)]
            assert points==list(range(48-len(points)//2,49+len(points)//2)),points
            rows.append(len(points))
        assert rows==widths,(radius,rows)
    r.image.paste('white',(0,0,96,65))
    r.virtual(r.gfx,5,0x00000000);r.virtual(r.gfx,10,48,30)
    assert r.image.getpixel((48,30))==(255,255,255),'transparent pixels must not become black'
    assert r.virtual(r.gfx,7)==0x00000000,'pen readback must preserve alpha'
    r.virtual(r.gfx,5,0x80000000);r.virtual(r.gfx,10,48,30)
    assert all(126<=v<=128 for v in r.image.getpixel((48,30)))
    print('Original circles, zero-width points and ARGB PASS')

    while not r.menu:r.frame(1)
    for background in (0xffffffff,0xff000000):
        r.frame_background=background
        r.image.paste('white' if background&0xffffff else 'black',(0,0,96,65))
        r.menu=None
        before=r.image.tobytes()
        assert r.presentation('light').getpixel((0,0))==(255,255,255)
        assert r.presentation('dark').getpixel((0,0))==(0,0,0)
        assert r.presentation('original').tobytes()==before
        assert r.image.tobytes()==before,'display choice must not modify native canvas'
    # Numeric fonts have no question-mark glyph; fallback must not crash while
    # showing score screens that use a restricted font.
    for face in ('8','9','10'):
        r.font=face;r.rendertext(2,30,'0123456789?')
    print('Colour presentation and original font fallback PASS')

    r=NokiaRuntime();r.random.seed(1110)
    while not r.menu:r.frame(1)
    r.activate(2);r.activate(1);r.activate(1);r.activate(0)
    field=r.word(r.state+0x24);food=r.word(field+0x28)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'legacy.state';r.save(path)
        data=json.loads(zlib.decompress(path.read_bytes()))
        data.pop('compatibility_version');data.pop('random_state')
        path.write_bytes(zlib.compress(json.dumps(data).encode()))
        loaded=NokiaRuntime();loaded.restore(path)
        assert loaded.word(loaded.state+8)==r.word(r.state+8)
        from qa_campaign import walls
        assert struct.unpack('>hh',loaded.u.mem_read(food+4,4)) not in walls(loaded)
        for _ in range(12):loaded.frame(1)
        assert all(isinstance(b,tuple) for b in loaded.freeblocks)
    print('Legacy game migration and subsequent execution PASS')


if __name__=='__main__':main()
