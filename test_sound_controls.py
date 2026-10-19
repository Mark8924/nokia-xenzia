"""Native sound-argument and consecutive-key regression tests."""
from runtime import NokiaRuntime
from sound import synthesize,RATE,EFFECTS,AUDIO
from controls import TurnBuffer
from qa_play import original_state
import array,sys,hashlib


def main():
    r=NokiaRuntime()
    expected=[(55,0,120,1,0,200,100,100),(45,0,120,1,0,300,100,100),
              (99,0,12,1,0,200,100,100),(90,0,12,1,0,200,100,100)]
    expected.extend([(63,0,55,1,0,900,100,100)]*3)
    for index,command in enumerate(expected):
        r.sounds.clear();r.call(0x9fa2,r.state+0x64,index)
        assert r.sounds==[command],(index,r.sounds)
        effect=EFFECTS[','.join(map(str,command))]
        raw=synthesize(command)
        assert len(raw)==effect['frames']*2
        assert hashlib.sha256(raw).hexdigest()==effect['sha256']
        assert len(raw)>=round(RATE*command[5]/1000)*2,'note release must not be truncated'
        pcm=array.array('h');pcm.frombytes(raw)
        if sys.byteorder!='little':pcm.byteswap()
        assert max(map(abs,pcm))>5000
        assert max(map(abs,pcm))<32767,'no hard clipping'
        assert effect['program']==command[2] and effect['note']==command[0]
    assert {x['program'] for x in EFFECTS.values()}=={12,55,120}
    print('All seven native parameter sets, original voice mapping, release tails and PCM hashes PASS')

    while not r.menu:r.frame(1)
    r.activate(0);turns=TurnBuffer();clock=r.clock
    head=original_state(r)[3]
    for key in ('up','left','down'):turns.push(r,key)
    assert r.clock==clock and original_state(r)[3]==head,'input must not fast-forward simulation'
    visited=[]
    for _ in range(12):
        r.frame(1);turns.sync(r)
        current=original_state(r)[3]
        if current!=head:visited.append(current);head=current
    assert visited[:3]==[(8,3),(7,3),(7,4)],visited
    print('Quick Up/Left/Down executes in order; native timing unchanged PASS')


if __name__=='__main__':main()
