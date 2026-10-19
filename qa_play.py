"""Play the original binary; validate food, controls, score, and frame damage."""
from runtime import *
from collections import deque
from pathlib import Path
import tempfile

DIRS=[('up',0,-1),('right',1,0),('down',0,1),('left',-1,0)]
def original_state(r):
 p=r.word(r.state+0x24);s=r.word(p+0x34);f=r.word(p+0x28)
 length=r.word(s+0x20);body=[]
 for i in range(length):
  v=int.from_bytes(r.u.mem_read(s+0x24+2*i,2),'big');body.append((v>>10,(v>>2)&63))
 head=struct.unpack('>hh',r.u.mem_read(s+4,4));food=struct.unpack('>hh',r.u.mem_read(f+4,4))
 return p,s,f,head,food,body

def route(head,target,body):
 q=deque([(head,[])]);seen={head};blocked=set(body)
 while q:
  pos,path=q.popleft()
  if pos==target:return path
  for name,dx,dy in DIRS:
   nxt=((pos[0]+dx)%16,(pos[1]+dy)%8)
   if nxt not in seen and nxt not in blocked:seen.add(nxt);q.append((nxt,path+[name]))
 return []

def main():
 r=NokiaRuntime();r.random.seed(265)
 while not r.menu:r.frame()
 r.activate(0)
 assert not r.menu
 start=original_state(r);print('start',start[3:5])
 eats=0;changes=[];comparisons=[];large=0
 with tempfile.TemporaryDirectory() as tmp:
  for step in range(250):
   p,s,f,head,food,body=original_state(r)
   bonus=r.word(p+0x2c)
   if r.word(bonus+8):
    large+=1
    print('BONUS',struct.unpack('>8h',r.u.mem_read(bonus+0x20,16)),'timer',r.word(bonus+0x30)) if large==1 else None
   path=route(head,food,body)
   if not path:raise AssertionError(('no route',head,food,body))
   before=r.word(r.state+8);r.key(path[0])
   for sub in range(4):
    if sub==0:
     fn=Path(tmp)/'state';r.save(fn);clone=NokiaRuntime();clone.restore(fn)
     clone.image.paste('magenta',(0,0,96,65));r.frame(1);clone.frame(1)
     # Both execute the same original game frame and RNG state, starting with different old pixels. A full native redraw must
     # produce the same result, without any trails from an old desktop frame.
     diff=[i for i,(a,b) in enumerate(zip(r.image.tobytes(),clone.image.tobytes())) if a!=b]
     comparisons.append(len({i//3 for i in diff}))
     if diff and len([x for x in comparisons if x])<=2:
      r.image.resize((960,650),Image.Resampling.NEAREST).save(f'/tmp/nokia-incremental-{step}.png')
      clone.image.resize((960,650),Image.Resampling.NEAREST).save(f'/tmp/nokia-full-{step}.png')
    else:r.frame(1)
   assert not r.menu,('unexpected game over',step,head,food)
   after=r.word(r.state+8)
   if after>before:
    now=original_state(r);eats+=1;changes.append((food,now[4]));assert now[4]!=food,('food did not move',food)
    print('ate',eats,'score',after,'old/new',food,now[4],'length',r.word(now[1]+0x20))
   if eats>=15:break
  print('eats',eats,'large-food-frames',large,'frame mismatches',sum(bool(x) for x in comparisons),'max mismatched pixels',max(comparisons),'checks',len(comparisons))
  assert eats>=15
  assert not any(comparisons),('full redraw retained stale pixels',comparisons)
  # Continue playing from a real saved in-game state after all allocations and
  # controller objects have been deserialized, not just compare a saved menu.
  r.save(Path(tmp)/'resume');loaded=NokiaRuntime();loaded.restore(Path(tmp)/'resume')
  for i in range(12):loaded.key(['up','left','down','right'][i%4]);loaded.frame()
  print('restored game executed frames successfully')
 r.image.resize((960,650),Image.Resampling.NEAREST).save('/tmp/nokia-play-verified.png')
 r.save('/tmp/nokia-play-verified.state')
 print('PASS')
if __name__=='__main__':main()
