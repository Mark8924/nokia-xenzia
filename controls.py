"""Preserve quick consecutive turns without changing native grid timing."""
from collections import deque

DIRECTIONS={'left':0,'down':1,'right':2,'up':3}
KEYS={v:k for k,v in DIRECTIONS.items()}


class TurnBuffer:
    def __init__(self):self.reset()

    def reset(self):
        self.pending=deque();self.waiting=None;self.position=None;self.field=None

    def native(self,r):
        if r.menu or r.u.mem_read(r.state+0x1c,1)!=b'\x04':return None
        field=r.word(r.state+0x24);snake=r.word(field+0x34)
        pos=bytes(r.u.mem_read(snake+4,4));index=r.word(snake+0xec)
        current=int.from_bytes(r.u.mem_read(snake+0x24+index*2,2),'big')>>8&3
        return field,pos,current

    def sync(self,r):
        state=self.native(r)
        if state is None:self.reset();return
        field,pos,current=state
        if self.field!=field:
            self.reset();self.field=field;self.position=pos
        elif self.position!=pos:
            self.position=pos;self.waiting=None
            if self.pending:
                direction=self.pending.popleft()
                r.key(KEYS[direction]);self.waiting=direction

    def push(self,r,key):
        self.sync(r);state=self.native(r)
        if state is None:r.key(key);return
        direction=DIRECTIONS[key]
        base=self.pending[-1] if self.pending else self.waiting if self.waiting is not None else state[2]
        if direction in (base,(base+2)%4):return
        if self.waiting is None:
            r.key(key);self.waiting=direction
        elif len(self.pending)<2:self.pending.append(direction)
