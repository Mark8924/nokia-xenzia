"""Compare the production display path to original retained-canvas transitions."""
from pathlib import Path
import tempfile
from runtime import NokiaRuntime


def check_campaign(stage=1):
    r=NokiaRuntime();r.random.seed(265);r.key('back')
    r.activate(2);r.activate(2);r.activate(0)
    # Use the original next-stage callback, rather than fabricate a bitmap.
    r.call(0xa9f4,r.state,stage)
    assert r.u.mem_read(r.state+0x1c,1)==b'\x07'
    with tempfile.TemporaryDirectory() as tmp:
        state=Path(tmp)/'transition.state';r.save(state)
        reference=NokiaRuntime();reference.restore(state)
        previous_host=NokiaRuntime();previous_host.restore(state)
        differences=0;frames=0
        while r.u.mem_read(r.state+0x1c,1)==b'\x07':
            r.frame_for_display();reference.frame(0);previous_host.frame(1)
            assert r.image.tobytes()==reference.image.tobytes(),('retained frame mismatch',stage,frames)
            assert r.word(r.state+0x34)==reference.word(reference.state+0x34)
            differences+=r.image.tobytes()!=previous_host.image.tobytes()
            frames+=1;assert frames<=62
        assert frames==61 and differences>10,(stage,frames,differences)
        assert r.u.mem_read(r.state+0x1c,1)==b'\x05'
        r.key('right');reference.key('right')
        assert r.u.mem_read(r.state+0x1c,1)==b'\x04'
        r.frame_for_display();reference.frame(1)
        assert r.image.tobytes()==reference.image.tobytes(),'gameplay must resume full redraw'
        return {'stage':stage,'retained_frames':frames,'previous_host_corrupted_frames':differences}


def main():
    for stage in range(1,5):print(check_campaign(stage),flush=True)
    r=NokiaRuntime();r.key('back');r.activate(2);r.activate(2);r.activate(0)
    # The fifth completed stage ends the campaign instead of another wipe.
    r.call(0xa9f4,r.state,5)
    assert r.u.mem_read(r.state+0x1c,1)==b'\x06'
    for _ in range(250):
        if r.menu:break
        r.frame_for_display()
    assert r.menu
    print('Four native between-level wipes, return to gameplay and final completion PASS')


if __name__=='__main__':main()
