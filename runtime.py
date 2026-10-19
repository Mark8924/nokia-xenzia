from pathlib import Path
from unicorn import *
from unicorn.arm_const import *
import struct,json,re,base64,zlib,hashlib,random,time
from PIL import Image, ImageDraw, ImageOps
ROOT=Path(__file__).resolve().parent
GFX_ARGS={258:0,259:0,261:1,262:1,263:0,264:0,266:2,268:4,269:4,270:4}
CODE=0x8000;SB=0x2000000;HEAP=0x2100000;KERNEL=0x3000000;VT=KERNEL+0x1000;HOST=0x4000000;RET=0x5000000;STACK=0x6000000
CALL_INSTRUCTION_LIMIT=1_000_000
# A full redraw of a long snake can exceed one million valid instructions.
# Keep a finite per-frame budget and the independent five-second deadline.
FRAME_INSTRUCTION_LIMIT=8_000_000
class NokiaRuntime:
 def __init__(self):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_BIG_ENDIAN);u=self.u
  for addr,size in [(CODE,0x10000),(SB,0x10000),(HEAP,0x100000),(KERNEL,0x10000),(HOST,0x10000),(RET,0x1000),(STACK,0x10000)]:u.mem_map(addr,size)
  self.code=(ROOT/'assets/snake-code.bin').read_bytes()
  u.mem_write(CODE,self.code);u.mem_write(SB,(ROOT/'assets/snake-data.bin').read_bytes())
  u.mem_write(KERNEL,struct.pack('>I',VT));u.mem_write(VT,b''.join(struct.pack('>I',(HOST+i*16+1-VT)&0xffffffff) for i in range(128)));u.mem_write(HOST,b'\x47\x70'*0x8000)
  self.heap=HEAP;self.calls=[];self.stop_reason='';self.clock=0
  self.random=random.Random()
  self._frame_start=None
  self.objs={};self.classes={};self.textpos=SB+0x2000;self.pending=[];self.tracing=False;self.menu_stack=[];self.menu=None;self.overlay=None;self.close_requested=False;self.ui_reset=False;self.sounds=[]
  self.texts=[self.widealloc(t,static=True) for t in json.loads((ROOT/'assets/texts.json').read_text())]
  self.fonts=json.loads((ROOT/'assets/fonts.json').read_text());self.font='3'
  self.image=Image.new('RGB',(96,65),'white');self.draw=ImageDraw.Draw(self.image,'RGBA');self.pen='#000000';self.bg=0xffffffff;self.frame_background=0xffffffff;self.delay=58;self.blocks={};self.freeblocks=[]
  self.gfx=KERNEL+0x100
  u.mem_write(self.gfx,struct.pack('>I',VT+0x1000))
  u.mem_write(VT+0x1000,b''.join(struct.pack('>I',(HOST+0x1000+i*16+1-VT-0x1000)&0xffffffff) for i in range(128)))
  u.reg_write(UC_ARM_REG_R9,SB)
  u.hook_add(UC_HOOK_CODE,self.host_hook,begin=HOST,end=HOST+0xffff);u.hook_add(UC_HOOK_CODE,lambda u,a,s,d:u.emu_stop(),begin=RET,end=RET+4)
  u.hook_add(UC_HOOK_MEM_INVALID,self.invalid)
  self.call(CODE+0x4db4,KERNEL);self.app=self.call(CODE,0);self.state=self.word(self.app+0x18)
  self.frame(1)
 def alloc(self,n):
  n=max(16,(n+7)&~7);p=self.heap
  for i,(q,m) in enumerate(self.freeblocks):
   if m>=n:
    self.freeblocks.pop(i)
    if m>n:self.freeblocks.append((q+n,m-n));self.freeblocks.sort(key=lambda b:b[0])
    self.blocks[q]=n;self.u.mem_write(q,bytes(n));return q
  if n>0x20000 or p+n>HEAP+0x100000:raise ValueError(f'alloc {n:x}')
  self.heap+=n;self.blocks[p]=n;return p
 def free(self,p):
  if p not in self.blocks:return
  self.freeblocks.append((p,self.blocks.pop(p)));self.freeblocks.sort();out=[]
  for q,n in self.freeblocks:
   if out and out[-1][0]+out[-1][1]==q:out[-1]=(out[-1][0],out[-1][1]+n)
   else:out.append((q,n))
  self.freeblocks=out
 def retain(self,p):
  if p:self.u.mem_write(p+4,struct.pack('>I',(self.word(p+4)+1)&0xffffffff))
 def release(self,p):
  if p:self.pending.append((0xd818,(p,)))
 def invalid(self,u,access,addr,size,value,data):
  self.stop_reason=f'invalid {access} mem {addr:x} size {size} pc {u.reg_read(UC_ARM_REG_PC):x} lr {u.reg_read(UC_ARM_REG_LR):x}';return False
 def string(self,p):
  if CODE<=p<CODE+0x5e3c:
   raw=bytes(self.u.mem_read(p,64)).split(b'\0')[0]
   if raw and all(32<=c<127 for c in raw):return raw.decode()
  return None
 def word(self,p):return int.from_bytes(self.u.mem_read(p,4),'big')
 @property
 def pen(self):return ((self.color>>16)&255,(self.color>>8)&255,self.color&255,self.color>>24)
 @pen.setter
 def pen(self,value):
  self.color=(0xff000000|int(value[1:],16)) if isinstance(value,str) else value
 def readtext(self,p,wide=True):
  if not p:return ''
  out=bytearray();step=2 if wide else 1
  for i in range(2048):
   c=bytes(self.u.mem_read(p+i*step,step))
   if not any(c):break
   out+=c
  return out.decode('utf-16-be' if wide else 'latin1',errors='replace')
 def widealloc(self,s,static=False):
  b=s.encode('utf-16-be')+b'\0\0'
  if static:p=self.textpos;self.textpos+=(len(b)+3)&~3
  else:p=self.alloc(len(b))
  self.u.mem_write(p,b);return p
 def obj(self,name,extra=()):
  if name not in self.classes:
   n=len(self.classes);self.classes[name]=n;vt=VT+0x3000+n*0x100
   self.u.mem_write(vt,b''.join(struct.pack('>I',(HOST+(512+n*32+i)*16+1-vt)&0xffffffff) for i in range(32)))
  n=self.classes[name];p=self.alloc(32);self.u.mem_write(p,struct.pack('>II',VT+0x3000+n*0x100,0))
  self.objs[p]={'name':name,'text':'','extra':list(extra),'items':[],'selected':0}
  if name.endswith('Controller') and extra:self.retain(extra[0])
  if name=='NaiTextViewItemController' and len(extra)>1:
   owned=self.widealloc(self.readtext(extra[1]));self.objs[p]['extra'][1]=owned;self.objs[p]['owned_ptr']=owned
  return p
 def rendertext(self,x,y,text,align=0):
  font=self.fonts[self.font];fallback=self.fonts['2'] if self.font in ('8','9') else self.fonts['3']
  glyphs=[font.get(c) or fallback.get(c,fallback['?']) for c in text]
  w=sum(g['width'] for g in glyphs)
  asc=max((g['baseline'] for g in glyphs),default=9)
  desc=max((g['height']-g['baseline'] for g in glyphs),default=3)
  if align&1:x-=w//2
  elif align&8:x-=w
  if align&16:y+=asc
  elif align&32:y-=desc-1
  elif align&2:y+=(asc-desc)//2
  for g in glyphs:
   for yy,row in enumerate(g['rows']):
    for xx,v in enumerate(row):
     if v=='1':self.draw.point((x+xx,y+yy-g['baseline']),fill=self.pen)
   x+=g['width']
  return w
 def canvas(self,index,v,lr):
  if index==258:return 96
  if index==259:return 65
  if index==261:self.pen=v[0]&0xffffffff
  elif index==262:
   self.bg=v[0]&0xffffffff
   if lr==0xa709:self.frame_background=self.bg
  elif index==263:return self.color
  elif index==264:return self.bg
  elif index==266:
   if 0<=v[0]<96 and 0<=v[1]<65:self.draw.point((v[0],v[1]),fill=self.pen)
  elif index==268:self.draw.line(tuple(v[:4]),fill=self.pen)
  elif index==269:
   # MCU NaiCanvas::drawRect uses inclusive endpoints for thin lines.
   x,y,w,h=v[:4]
   if w==1:self.draw.line((x,y,x,y+h),fill=self.pen)
   elif h==1:self.draw.line((x,y,x+w,y),fill=self.pen)
   elif w>=2 and h>=2:self.draw.rectangle((x,y,x+w-1,y+h-1),outline=self.pen)
  elif index==270 and v[2]>0 and v[3]>0:
   box=(v[0],v[1],v[0]+v[2]-1,v[1]+v[3]-1)
   self.draw.rectangle(box,fill=self.pen)
   if box[0]<=0 and box[1]<=0 and box[2]>=95 and box[3]>=64 and self.color>>24==255:self.frame_background=self.color
  return 0
 def host_hook(self,u,a,size,data):
  index=(a-HOST)//16
  if not self.tracing and index in GFX_ARGS:
   # Hundreds of calls per frame: read only the registers this method uses.
   # No object/string/unused-stack inspection is needed for drawing primitives.
   count=GFX_ARGS[index];v=[u.reg_read(UC_ARM_REG_R1+i) for i in range(min(3,count))]
   if count==4:v.append(self.word(u.reg_read(UC_ARM_REG_SP)))
   v=[x if x<0x80000000 else x-0x100000000 for x in v]
   lr=u.reg_read(UC_ARM_REG_LR);ret=self.canvas(index,v,lr)
   u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,lr);return
  args=[u.reg_read(UC_ARM_REG_R0+i) for i in range(4)]
  sp=u.reg_read(UC_ARM_REG_SP);extra=struct.unpack('>4I',u.mem_read(sp,16));v=[x if x<0x80000000 else x-0x100000000 for x in args[1:]+list(extra)]
  names=[self.string(x) for x in args]
  if self.tracing:self.calls.append({'index':index,'args':[hex(x) for x in args],'stack':[hex(x) for x in extra],'names':names,'lr':hex(u.reg_read(UC_ARM_REG_LR))})
  if index==7:ret=self.alloc(args[1])
  elif index==1:
   name=names[1];ret=self.obj(name,extra[:args[3]]) if name in ['NaiStringIf','NaiMenu','NaiActionItemController','NaiTextViewItemController','NaiLevelItemController','NaiMenuControl','NaiRingToneSound','NaiSoundManager','NaiDeviceControl'] else 0
  elif index==16:ret=self.texts[args[1]] if args[1]<len(self.texts) else 0
  elif index==8:
   self.free(args[1])
   ret=0
  elif index==15:ret=(self.clock+(int(1000*(time.perf_counter()-self._frame_start)) if self._frame_start is not None else 0))&0xffffffff
  elif index==12:
   lo,hi=v[:2]
   if lo>hi:raise RuntimeError(f'Invalid guest random bounds: {lo}, {hi}')
   ret=self.random.randint(lo,hi)&0xffffffff
  elif index==13:self.delay=args[2];ret=0
  elif index in GFX_ARGS:ret=self.canvas(index,v,u.reg_read(UC_ARM_REG_LR))
  elif index==273:
   name=self.readtext(args[1],False).lower();weight=self.readtext(args[3],False).lower()
   if name.startswith('agfa'):self.font='8' if args[2]>=19 else '10' if args[2]>=16 else '9'
   else:self.font='2' if name in ('large','medium') or weight=='bold' else '3'
   ret=1
  elif index in (274,275):
   ptr=self.word(args[3]);text=self.objs.get(ptr,{}).get('text','');ret=self.rendertext(v[0],v[1],text,extra[0])
  elif index>=512:
   ob=self.objs[args[0]];slot=(index-512)%32;name=ob['name'];ret=0
   if slot==0:
    if ob.get('ptr'):self.free(ob['ptr'])
    if ob.get('owned_ptr'):self.free(ob['owned_ptr'])
    if name.endswith('Controller') and ob['extra']:self.release(ob['extra'][0])
    for q in ob['items']:self.release(q)
    del self.objs[args[0]];self.free(args[0])
   elif name=='NaiStringIf':
    if slot in (2,3):ob['text']=self.readtext(args[1],slot==3)
    elif slot==8:
     if ob.get('last')!=ob['text']:
      if ob.get('ptr'):self.free(ob['ptr'])
      ob['ptr']=self.widealloc(ob['text']);ob['last']=ob['text']
     ret=ob.get('ptr',0)
    elif slot==9:ret=len(ob['text'])
    elif slot==12:ob['text']=str(v[0])
    elif slot==10:ob['text']+=self.objs.get(self.word(args[1]),{}).get('text','')
    elif slot==14:
     fmt=self.readtext(args[1],False);vp=self.word(args[2]);types=re.findall(r'%(?:0?[0-9]*)?([uds])',fmt);values=[]
     for j,t in enumerate(types):
      z=self.word(vp+4*j);values.append(self.readtext(z,True) if t=='s' else (z if t=='u' or z<0x80000000 else z-0x100000000))
     try:ob['text']=fmt%tuple(values)
     except (TypeError,ValueError):ob['text']=fmt
    elif slot==7:
     val=ob['text'].encode('latin1',errors='replace')[:max(0,args[2]-1)]+b'\0';u.mem_write(args[1],val);ret=len(val)-1
   elif name=='NaiMenu':
    if slot==1:
     ob['items'].append(args[1]);self.retain(args[1])
    elif slot==2:
     if args[1] in ob['items']:ob['items'].remove(args[1]);self.release(args[1])
    elif slot==4:ob['selected']=args[1]
    elif slot==5:
     if self.menu!=args[0]:
      if self.menu:self.menu_stack.append(self.menu)
      self.menu=args[0];self.retain(self.menu);self.ui_reset=True
   elif name=='NaiMenuControl':self.close_requested=True
   elif name=='NaiSoundManager' and slot==3:
    # Original MCU 0x0110b36c forwards all eight sound parameters. The
    # third value is the instrument program, NOT a duration. Duration is sixth.
    self.sounds.append(tuple(v+[self.word(sp+16)]))
  else:ret=0
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def call(self,addr,*args,instruction_limit=CALL_INSTRUCTION_LIMIT):
  u=self.u
  for i in range(8):u.reg_write(UC_ARM_REG_R0+i,0)
  for i,x in enumerate(args):u.reg_write(UC_ARM_REG_R0+i,x)
  u.reg_write(UC_ARM_REG_SP,STACK+0xfff0);u.reg_write(UC_ARM_REG_LR,RET+1)
  try:u.emu_start(addr|1,RET+4,timeout=5000000,count=instruction_limit)
  except UcError as e:raise RuntimeError(f'Original game: {e}; {self.stop_reason}') from e
  pc=u.reg_read(UC_ARM_REG_PC)
  if pc!=RET:
   reason='execution deadline exceeded' if u.query(UC_QUERY_TIMEOUT) else 'instruction limit exceeded'
   raise RuntimeError(f'Guest {reason}: call 0x{addr:x}, PC 0x{pc:x}, budget {instruction_limit}')
  result=u.reg_read(UC_ARM_REG_R0)
  while self.pending:
   addr,aa=self.pending.pop(0);self.call(addr,*aa)
  return result
 def virtual(self,p,slot,*args):
  vt=self.word(p);return self.call((vt+self.word(vt+4*slot))&0xffffffff,p,*args)
 def frame_for_display(self,realtime=False):
  # Both native opening (phase 2) and campaign wipe (phase 7) call the
  # retained-canvas animation at 0xa26e. Exposing the whole canvas on every
  # frame erases body sections which the animation does not repaint.
  phase=self.u.mem_read(self.state+0x1c,1)[0]
  self.frame(0 if phase in (2,7) else 1,realtime=realtime)
 def frame(self,redraw=0,realtime=False):
  if self.menu:return
  if self.u.mem_read(self.state+0x1c,1)==b'\x03':
   controller=self.word(self.state+0x30);m=self.word(controller+8)
   if m in self.objs:
    for q in self.objs[m]['items']:self.release(q)
    self.objs[m]['items']=[]
    while self.pending:
     addr,aa=self.pending.pop(0);self.call(addr,*aa)
  self.clock+=max(1,self.delay);self._frame_start=time.perf_counter() if realtime else None
  try:self.call(0x817c,self.app,self.gfx,redraw,instruction_limit=FRAME_INSTRUCTION_LIMIT)
  finally:self._frame_start=None
 def label(self,item):
  ob=self.objs[item];return self.readtext(self.virtual(ob['extra'][0],1))
 def menu_labels(self):
  if not self.menu:return []
  return [self.label(q) for q in self.objs[self.menu]['items']]
 def activate(self,selection=None):
  menu=self.menu;ob=self.objs[menu];sel=ob['selected'] if selection is None else selection
  if not ob['items']:return
  item=self.objs[ob['items'][sel]]
  if item['name']=='NaiTextViewItemController':self.overlay={'type':'text','text':self.readtext(item['extra'][1]),'title':self.label(ob['items'][sel]),'scroll':0};return
  if item['name']=='NaiLevelItemController':self.overlay={'type':'level','item':ob['items'][sel],'value':item['extra'][1],'max':item['extra'][2]};return
  self.close_requested=False;ret=self.virtual(item['extra'][0],2)
  if not ret:
   self.close_menus();self.frame(1)
  elif self.menu==menu and self.close_requested:self.back()
 def close_menus(self):
  for p in self.menu_stack+([self.menu] if self.menu else []):self.release(p)
  self.menu_stack=[];self.menu=None;self.overlay=None
  while self.pending:
   addr,a=self.pending.pop(0);self.call(addr,*a)
 def back(self):
  if self.overlay:self.overlay=None;return
  if self.menu_stack:
   p=self.menu;self.menu=self.menu_stack.pop();self.release(p)
   while self.pending:
    addr,a=self.pending.pop(0);self.call(addr,*a)
  elif self.menu and self.word(self.state):
   self.close_menus();self.call(0xaade,self.state);self.frame(1)
 def key(self,key):
  if self.overlay:
   o=self.overlay
   if o['type']=='level':
    if key in ('up','right'):o['value']=min(o['max'],o['value']+1)
    elif key in ('down','left'):o['value']=max(0,o['value']-1)
    elif key=='select':
     ob=self.objs[o['item']];ob['extra'][1]=o['value'];self.virtual(ob['extra'][0],2,o['value']);self.overlay=None
    elif key=='back':self.overlay=None
   elif key in ('select','back'):self.overlay=None
   elif key=='down':o['scroll']+=1
   elif key=='up':o['scroll']=max(0,o['scroll']-1)
  elif self.menu:
   ob=self.objs[self.menu];n=len(ob['items'])
   if key=='up' and n:ob['selected']=(ob['selected']-1)%n
   elif key=='down' and n:ob['selected']=(ob['selected']+1)%n
   elif key=='select':self.activate()
   elif key=='back':self.back()
  elif key in ('select','back'):
   self.call(0xa0d0,self.state);self.frame(1)
  else:
   code={'up':0x32,'down':0x38,'left':0x34,'right':0x36}.get(key)
   if code:self.call(0x81fe,self.app,code)
 def render_menu(self):
  if not self.menu:return self.image
  self.image.paste('white',(0,0,96,65));self.pen='#000000';self.font='3';menu=self.objs[self.menu]
  if self.overlay:
   o=self.overlay
   if o['type']=='level':
    self.rendertext(48,10,'Level',1);self.rendertext(48,32,str(o['value']+1),1)
    self.draw.rectangle((11,42,84,46),outline='black');self.draw.rectangle((13,44,13+int(69*(o['value']+1)/(o['max']+1)),44),fill='black')
   else:
    self.rendertext(48,10,o['title'],1);words=o['text'].split();lines=[];line=''
    for word in words:
     trial=(line+' '+word).strip()
     if sum(self.fonts['3'].get(c,self.fonts['3']['?'])['width'] for c in trial)>92 and line:lines.append(line);line=word
     else:line=trial
    if line:lines.append(line)
    o['scroll']=min(o['scroll'],max(0,len(lines)-3))
    for i,line in enumerate(lines[o['scroll']:o['scroll']+3]):self.rendertext(2,24+i*12,line)
   self.rendertext(94,63,'Back',8);return self.image
  title=self.readtext(menu['extra'][0]) if menu['extra'] else 'Snake Xenzia';self.rendertext(48,10,title,1);self.draw.line((0,13,95,13),fill='black')
  labels=self.menu_labels();selected=min(menu['selected'],max(0,len(labels)-1));offset=max(0,min(selected-1,len(labels)-3))
  for i,label in enumerate(labels[offset:offset+3]):
   y=15+i*12
   if offset+i==selected:self.draw.rectangle((0,y,93,y+11),fill='black');self.pen='#ffffff'
   else:self.pen='#000000'
   self.rendertext(2,y+9,label)
  self.pen='#000000'
  if len(labels)>3:
   self.draw.line((95,15,95,49),fill='black');self.draw.rectangle((94,15+int(31*selected/(len(labels)-1)),95,19+int(31*selected/(len(labels)-1))),fill='black')
  self.rendertext(1,63,'Select');self.rendertext(94,63,'Back',8);return self.image
 def presentation(self,mode='original'):
  if mode=='original':return self.image
  dark=False if self.menu else (self.frame_background&0xffffff)<0x808080
  target=mode=='dark'
  return ImageOps.invert(self.image) if dark!=target else self.image
 def save(self,path):
  data={k:getattr(self,k) for k in ['heap','blocks','freeblocks','objs','classes','textpos','texts','clock','delay','font','menu','menu_stack','overlay','app','state','color','bg','frame_background']}
  data['sha256']=hashlib.sha256(self.code).hexdigest();data['format']=1
  data['compatibility_version']=2
  data['random_state']=self.random.getstate()
  data['ram']={str(a):base64.b64encode(bytes(self.u.mem_read(a,n))).decode() for a,n in [(SB,0x10000),(HEAP,self.heap-HEAP),(KERNEL,0x10000)]}
  data['screen']=base64.b64encode(self.image.tobytes()).decode();path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_bytes(zlib.compress(json.dumps(data).encode(),6));tmp.replace(path)
 def restore(self,path):
  data=json.loads(zlib.decompress(Path(path).read_bytes()))
  if data.get('format')!=1 or data['sha256']!=hashlib.sha256(self.code).hexdigest():raise ValueError('Different game data')
  for a,b in data['ram'].items():self.u.mem_write(int(a),base64.b64decode(b))
  for k in ['heap','freeblocks','classes','textpos','texts','clock','delay','font','menu','menu_stack','overlay','app','state']:setattr(self,k,data[k])
  self.freeblocks=[tuple(b) for b in self.freeblocks]
  if 'random_state' in data:
   version,state,gauss=data['random_state'];self.random.setstate((version,tuple(state),gauss))
  self.color=data.get('color',0xff000000);self.bg=data.get('bg',0xffffffff);self.frame_background=data.get('frame_background',0xffffffff)
  self.blocks={int(k):v for k,v in data['blocks'].items()};self.objs={int(k):v for k,v in data['objs'].items()};self.image.frombytes(base64.b64decode(data['screen']));self.draw=ImageDraw.Draw(self.image,'RGBA')
  # Host trampolines are code, never stored as executable files on the host.
  for name,n in self.classes.items():
   vt=VT+0x3000+n*0x100;self.u.mem_write(vt,b''.join(struct.pack('>I',(HOST+(512+n*32+i)*16+1-vt)&0xffffffff) for i in range(32)))
  if data.get('compatibility_version',0)<2 and self.word(self.state):
   # The first host erroneously returned zero for every random coordinate.
   # Let the original game's own spawn/overlap logic repair legacy food;
   # keep snake, score, level, maze and native high-score tables intact.
   field=self.word(self.state+0x24);food=self.word(field+0x28);bonus=self.word(field+0x2c)
   if self.word(food+8):self.call(0x83f8,field)
   if self.word(bonus+8):self.call(0x84e0,field)
