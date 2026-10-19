"""Exercise original ARM game code, menus, input, and persistent state."""
from runtime import NokiaRuntime,HEAP
from pathlib import Path
import tempfile,time,hashlib

def main():
 r=NokiaRuntime()
 for _ in range(100):
  r.frame()
  if r.menu:break
 assert r.menu, 'Original intro must lead to menu'
 print('menu:',r.menu_labels())
 assert r.menu_labels()==['New game','Level','Game type','Instructions','High scores']
 r.render_menu().resize((768,520)).save('/tmp/nokia-original-menu.png')
 r.activate(2);assert r.menu_labels()==['Classic','Modern','Campaign']
 r.activate(1);assert r.menu_labels()==['No Maze','Box','Tunnel','Mill','Rails','Apartment']
 r.activate(1);assert r.menu_labels()[0]=='New game'
 r.activate(0);assert not r.menu
 for i in range(15):
  r.key('up' if i%8==0 else 'right' if i%8==4 else 'down' if i%8==6 else 'left' if i%8==2 else 'noop');r.frame()
 r.key('back');assert r.menu
 print('paused menu:',r.menu_labels())
 assert 'Continue' in r.menu_labels()
 r.render_menu()
 with tempfile.TemporaryDirectory() as t:
  f=Path(t)/'state';r.save(f);r2=NokiaRuntime();r2.restore(f)
  assert r2.menu_labels()==r.menu_labels()
  assert r2.image.tobytes()==r.image.tobytes()
  print('save bytes',f.stat().st_size)
 r.activate(2 if r.menu_labels()[0]=='Continue' else 1)
 assert r.overlay['type']=='level';r.key('up');r.key('select')
 print('level changed; menu',r.menu_labels())
 r.overlay=None;r.close_menus();r.call(0xaa86,r.state)
 initialheap=r.heap;begin=time.perf_counter()
 for i in range(600):
  if r.menu:r.activate(0)
  r.frame()
 print('600 frames',round(time.perf_counter()-begin,3),'s','heap',r.heap-HEAP,'growth',r.heap-initialheap,'objects',len(r.objs))
 r.image.resize((768,520)).save('/tmp/nokia-original-game.png')
 print('OK')
if __name__=='__main__':main()
