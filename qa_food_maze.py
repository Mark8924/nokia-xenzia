"""Drive actual native food consumption in every maze and consume large food."""
from runtime import NokiaRuntime,struct
from qa_play import original_state,route
from qa_campaign import walls


def main():
    for maze in range(6):
        r=NokiaRuntime();r.random.seed(400+maze)
        while not r.menu:r.frame(1)
        r.activate(2);r.activate(1);r.activate(maze);r.activate(0)
        blocked=walls(r)
        for step in range(200):
            p,s,f,head,food,body=original_state(r)
            assert food not in blocked,('food in wall',maze,food)
            path=route(head,food,body+list(blocked))
            assert path,('no route',maze,head,food)
            r.key(path[0])
            for _ in range(4):r.frame(1)
            assert not r.menu,('unexpected end',maze,step)
            if r.word(r.state+8)>=3:break
        assert r.word(r.state+8)>=3,maze
        print('Maze',maze,'native walls',len(blocked),'at least three foods PASS',flush=True)

    r=NokiaRuntime();r.random.seed(265)
    while not r.menu:r.frame(1)
    r.activate(0);large=0;small=0
    for step in range(500):
        field,s,f,head,food,body=original_state(r);bonus=r.word(field+0x2c)
        bonus_active=bool(r.word(bonus+8));target=food
        if bonus_active:
            coords=struct.unpack('>8h',r.u.mem_read(bonus+0x20,16))
            candidates=[route(head,tuple(coords[i:i+2]),body) for i in range(0,8,2)]
            paths=[p for p in candidates if p]
            if paths:path=min(paths,key=len)
            else:path=route(head,food,body)
        else:path=route(head,food,body)
        assert path,('no route',head,food)
        before=r.word(r.state+8);r.key(path[0])
        for _ in range(4):r.frame(1)
        assert not r.menu,('unexpected end',step)
        gain=r.word(r.state+8)-before
        if gain:
            if bonus_active and not r.word(bonus+8) and gain>1:
                large+=1;print('Large bonus consumed; score gain',gain,flush=True)
            else:small+=1
        if large>=2:break
    assert large>=2,(small,large)
    print('Normal and large food consumption PASS',small,large)


if __name__=='__main__':main()
