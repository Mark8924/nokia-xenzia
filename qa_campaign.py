from runtime import *
from qa_play import original_state,route

def walls(r):
 field=r.word(r.state+0x24);maze=r.word(field+0x30);it=maze+0x1c
 if not r.word(it+4):return set()
 tmp=r.alloc(0x30);r.u.mem_write(tmp,bytes(r.u.mem_read(it,0x30)));out=set()
 for segment in range(r.word(it+4)):
  pos=r.call(0xb2d0,tmp,segment)
  for _ in range(160):
   if not pos:break
   out.add(tuple(r.u.mem_read(pos,2)));pos=r.call(0xb300,tmp)
  else:raise AssertionError('maze iterator')
 r.free(tmp);return out

def main():
 r=NokiaRuntime();r.random.seed(845)
 while not r.menu:r.frame()
 r.activate(2);r.activate(2);r.activate(0)
 stage=-1;transitions=[];score=0
 for step in range(1000):
  phase=r.u.mem_read(r.state+0x1c,1)[0]
  if phase!=4:
   for _ in range(140):
    r.frame(1)
    if r.u.mem_read(r.state+0x1c,1)[0]==4 or r.menu:break
   if r.menu:break
  current=r.word(r.state+0x58)
  if current!=stage:
   stage=current;transitions.append(stage);print('campaign stage',stage,'maze',r.u.mem_read(r.state+0xd,1)[0],'score',r.word(r.state+8),flush=True)
  if stage>=1:break
  field,s,f,head,food,body=original_state(r);blocked=walls(r)
  assert food not in blocked,('food in wall',food)
  path=route(head,food,body+list(blocked));assert path,('bot trapped',stage,head,food)
  r.key(path[0])
  for _ in range(4):r.frame(1)
  now=r.word(r.state+8)
  if now!=score:score=now;print('campaign score',score,flush=True)
 assert transitions[:2]==[0,1],transitions
 r.image.resize((960,650),Image.Resampling.NEAREST).save('/tmp/nokia-campaign-transition.png')
 print('Campaign level transition PASS',transitions)
if __name__=='__main__':main()
