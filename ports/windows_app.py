"""Dependency-free Win32 window for the shared original-game controller."""
import ctypes as C
from ctypes import wintypes as W
import json,logging,os,sys,time,winsound
from pathlib import Path
from session import Session
from asset_store import resource,ensure_assets

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'SnakeXenzia'
if '--self-test' in sys.argv:DATA=Path(sys.argv[sys.argv.index('--self-test')+1])
DATA.mkdir(parents=True,exist_ok=True)
logging.basicConfig(filename=DATA/'game.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s',encoding='utf-8')
u=C.WinDLL('user32',use_last_error=True);g=C.WinDLL('gdi32',use_last_error=True);k=C.WinDLL('kernel32',use_last_error=True)
PTR=C.c_void_p;LRESULT=C.c_ssize_t;WPARAM=C.c_size_t;LPARAM=C.c_ssize_t
PROC=C.WINFUNCTYPE(LRESULT,W.HWND,W.UINT,WPARAM,LPARAM)

class WC(C.Structure):
    _fields_=[('style',W.UINT),('proc',PROC),('extra',C.c_int),('windowextra',C.c_int),('instance',W.HINSTANCE),('icon',PTR),('cursor',PTR),('background',PTR),('menu',W.LPCWSTR),('name',W.LPCWSTR)]
class PAINT(C.Structure):
    _fields_=[('dc',W.HDC),('erase',W.BOOL),('rect',W.RECT),('restore',W.BOOL),('update',W.BOOL),('reserved',C.c_byte*32)]
class BMI(C.Structure):
    _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('image_size',W.DWORD),('xres',W.LONG),('yres',W.LONG),('used',W.DWORD),('important',W.DWORD)]
class MONITOR(C.Structure):
    _fields_=[('size',W.DWORD),('monitor',W.RECT),('work',W.RECT),('flags',W.DWORD)]

def api(lib,name,restype,*args):
    f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f

api(k,'GetModuleHandleW',PTR,W.LPCWSTR);api(k,'CreateMutexW',PTR,PTR,W.BOOL,W.LPCWSTR)
api(u,'RegisterClassW',W.ATOM,C.POINTER(WC));api(u,'CreateWindowExW',W.HWND,W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,PTR,PTR,PTR)
api(u,'DefWindowProcW',LRESULT,W.HWND,W.UINT,WPARAM,LPARAM);api(u,'LoadCursorW',PTR,PTR,PTR)
api(u,'LoadImageW',PTR,PTR,W.LPCWSTR,W.UINT,C.c_int,C.c_int,W.UINT)
api(u,'BeginPaint',W.HDC,W.HWND,C.POINTER(PAINT));api(u,'EndPaint',W.BOOL,W.HWND,C.POINTER(PAINT))
api(u,'GetClientRect',W.BOOL,W.HWND,C.POINTER(W.RECT));api(u,'FillRect',C.c_int,W.HDC,C.POINTER(W.RECT),PTR)
api(u,'DrawTextW',C.c_int,W.HDC,W.LPCWSTR,C.c_int,C.POINTER(W.RECT),W.UINT)
api(u,'SetTimer',C.c_size_t,W.HWND,C.c_size_t,W.UINT,PTR);api(u,'KillTimer',W.BOOL,W.HWND,C.c_size_t)
api(u,'InvalidateRect',W.BOOL,W.HWND,C.POINTER(W.RECT),W.BOOL);api(u,'DestroyWindow',W.BOOL,W.HWND)
api(u,'ShowWindow',W.BOOL,W.HWND,C.c_int);api(u,'UpdateWindow',W.BOOL,W.HWND)
api(u,'GetMessageW',W.BOOL,C.POINTER(W.MSG),W.HWND,W.UINT,W.UINT);api(u,'TranslateMessage',W.BOOL,C.POINTER(W.MSG));api(u,'DispatchMessageW',LRESULT,C.POINTER(W.MSG))
api(u,'PostQuitMessage',None,C.c_int);api(u,'SetCapture',W.HWND,W.HWND);api(u,'ReleaseCapture',W.BOOL)
api(u,'MessageBoxW',C.c_int,W.HWND,W.LPCWSTR,W.LPCWSTR,W.UINT)
api(u,'CreateMenu',PTR);api(u,'CreatePopupMenu',PTR);api(u,'AppendMenuW',W.BOOL,PTR,W.UINT,C.c_size_t,W.LPCWSTR)
api(u,'SetMenu',W.BOOL,W.HWND,PTR);api(u,'CheckMenuItem',W.DWORD,PTR,W.UINT,W.UINT)
api(u,'GetWindowRect',W.BOOL,W.HWND,C.POINTER(W.RECT));api(u,'GetWindowLongPtrW',C.c_ssize_t,W.HWND,C.c_int)
api(u,'SetWindowLongPtrW',C.c_ssize_t,W.HWND,C.c_int,C.c_ssize_t)
api(u,'SetWindowPos',W.BOOL,W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT)
api(u,'MonitorFromWindow',PTR,W.HWND,W.DWORD);api(u,'GetMonitorInfoW',W.BOOL,PTR,C.POINTER(MONITOR))
api(u,'FindWindowW',W.HWND,W.LPCWSTR,W.LPCWSTR);api(u,'SetForegroundWindow',W.BOOL,W.HWND)
api(g,'CreateSolidBrush',PTR,W.DWORD);api(g,'CreatePen',PTR,C.c_int,C.c_int,W.DWORD)
api(g,'SelectObject',PTR,W.HDC,PTR);api(g,'DeleteObject',W.BOOL,PTR)
api(g,'SetTextColor',W.DWORD,W.HDC,W.DWORD);api(g,'SetBkMode',C.c_int,W.HDC,C.c_int)
api(g,'RoundRect',W.BOOL,W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int)
api(g,'CreateFontW',PTR,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.DWORD,W.LPCWSTR)
api(g,'SetStretchBltMode',C.c_int,W.HDC,C.c_int)
api(g,'StretchDIBits',C.c_int,W.HDC,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,PTR,C.POINTER(BMI),W.UINT,W.DWORD)
api(u,'GetWindowDC',W.HDC,W.HWND);api(u,'ReleaseDC',C.c_int,W.HWND,W.HDC);api(u,'PrintWindow',W.BOOL,W.HWND,W.HDC,W.UINT)
api(g,'CreateCompatibleDC',W.HDC,W.HDC);api(g,'CreateCompatibleBitmap',PTR,W.HDC,C.c_int,C.c_int)
api(g,'GetDIBits',C.c_int,W.HDC,PTR,W.UINT,W.UINT,PTR,C.POINTER(BMI),W.UINT);api(g,'DeleteDC',W.BOOL,W.HDC)

KEYS={0x25:'left',0x26:'up',0x27:'right',0x28:'down',ord('W'):'up',ord('A'):'left',ord('S'):'down',ord('D'):'right',ord('2'):'up',ord('4'):'left',ord('6'):'right',ord('8'):'down',0x62:'up',0x64:'left',0x66:'right',0x68:'down',0x0d:'select',0x20:'select',ord('5'):'select',0x65:'select',0x1b:'back',ord('P'):'back',0x08:'back'}
def rgb(r,g,b):return r|(g<<8)|(b<<16)

class Window:
    def __init__(self):
        try:u.SetProcessDpiAwarenessContext(PTR(-4))
        except Exception:u.SetProcessDPIAware()
        self.game=Session(DATA);self.hwnd=None;self.failed=False;self.full=False;self.pointer=None;self.dragged=False
        self.game.audio_sink=lambda effect:winsound.PlaySound(str(resource('audio/'+effect+'.wav')),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        self.buttons=[];self.scale=1;self.left=0;self.top=0;self.pixels=self.game.pixels('BGRX')
        self.dpi=1
        try:self.dpi=u.GetDpiForSystem()/96
        except Exception:pass
        self.font=g.CreateFontW(-int(17*self.dpi),0,0,0,400,0,0,0,1,0,0,0,0,'Segoe UI')
        self.small=g.CreateFontW(-int(13*self.dpi),0,0,0,400,0,0,0,1,0,0,0,0,'Segoe UI')
        self.proc=PROC(self.dispatch)
        wc=WC();wc.proc=self.proc;wc.instance=k.GetModuleHandleW(None);wc.name='SnakeXenziaPortable'
        wc.cursor=u.LoadCursorW(None,PTR(32512));wc.icon=u.LoadImageW(None,str(ROOT/'assets/icon.ico'),1,0,0,0x10|0x40)
        if not u.RegisterClassW(C.byref(wc)):raise C.WinError(C.get_last_error())
        self.hwnd=u.CreateWindowExW(0,wc.name,'Snake Xenzia',0x00cf0000,-2147483648,-2147483648,int(780*self.dpi),int(880*self.dpi),None,None,wc.instance,None)
        if not self.hwnd:raise C.WinError(C.get_last_error())
        self.menu=u.CreateMenu()
        for title,items in [('游戏 / Game',[(10,'暂停 / Pause\tEsc'),(11,'全屏 / Fullscreen\tF11'),(12,'退出 / Exit')]),('显示 / View',[(20,'屏幕方向键 / Direction pad'),(21,'原版配色 / Original'),(22,'白底黑字 / Light'),(23,'黑底白字 / Dark')]),('设置 / Settings',[(30,'音效 / Sound'),(31,'启动动画 / Opening animation'),(32,'操作说明 / Help')])]:
            popup=u.CreatePopupMenu()
            for item,label in items:u.AppendMenuW(popup,0,item,label)
            u.AppendMenuW(self.menu,0x10,popup,title)
        u.SetMenu(self.hwnd,self.menu);self.check_menu()
        u.ShowWindow(self.hwnd,5);u.UpdateWindow(self.hwnd);u.SetTimer(self.hwnd,1,1,None)
        self.started=time.monotonic()
        if '--self-test' in sys.argv:u.SetTimer(self.hwnd,2,5000,None)

    def check_menu(self):
        opts=self.game.options
        for item,on in [(20,opts['controls_visible']),(30,not opts['muted']),(31,opts['play_intro']),*[(21+i,opts['color_mode']==mode) for i,mode in enumerate(('original','light','dark'))]]:
            u.CheckMenuItem(self.menu,item,8 if on else 0)

    def refresh(self):
        self.pixels=self.game.pixels('BGRX')
        for effect in json.loads(self.game.take_audio()):
            winsound.PlaySound(str(resource('audio/'+effect+'.wav')),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        u.InvalidateRect(self.hwnd,None,False)

    def key(self,key):
        before=bool(self.game.active.menu);self.game.key(key);self.refresh()
        if before and not self.game.active.menu:u.KillTimer(self.hwnd,1);u.SetTimer(self.hwnd,1,self.game.delay(),None)

    def text(self,dc,box,label,small=False):
        old=g.SelectObject(dc,self.small if small else self.font)
        rect=W.RECT(*map(int,box));u.DrawTextW(dc,label,-1,C.byref(rect),0x1|0x4|0x20)
        g.SelectObject(dc,old)

    def fill(self,dc,box,color):
        brush=g.CreateSolidBrush(color);rect=W.RECT(*map(int,box));u.FillRect(dc,C.byref(rect),brush);g.DeleteObject(brush)

    def button(self,dc,box,label,key):
        box=tuple(map(int,box));self.buttons.append((box,key))
        brush=g.CreateSolidBrush(rgb(247,248,249));pen=g.CreatePen(0,1,rgb(163,170,175))
        ob=g.SelectObject(dc,brush);op=g.SelectObject(dc,pen)
        g.RoundRect(dc,*box,int(12*self.dpi),int(12*self.dpi))
        g.SelectObject(dc,ob);g.SelectObject(dc,op);g.DeleteObject(brush);g.DeleteObject(pen)
        self.text(dc,box,label)

    def paint(self,dc=None):
        ps=None
        if dc is None:ps=PAINT();dc=u.BeginPaint(self.hwnd,C.byref(ps))
        try:
            rect=W.RECT();u.GetClientRect(self.hwnd,C.byref(rect));w,h=rect.right,rect.bottom;d=self.dpi
            self.fill(dc,(0,0,w,h),rgb(213,217,219));g.SetBkMode(dc,1);g.SetTextColor(dc,rgb(30,36,39))
            self.text(dc,(12*d,8*d,w-12*d,43*d),'S N A K E   X E N Z I A')
            pad=190*d if self.game.options['controls_visible'] else 0
            area_bottom=h-92*d-pad
            self.scale=max(1,int(min((w-36*d)/96,(area_bottom-58*d)/65)))
            self.left=int((w-96*self.scale)/2);self.top=int(54*d+(area_bottom-54*d-65*self.scale)/2)
            x,y,s=self.left,self.top,self.scale
            self.fill(dc,(x-4,y-4,x+96*s+4,y+65*s+4),rgb(42,47,51))
            bmi=BMI(C.sizeof(BMI),96,-65,1,32,0,len(self.pixels),0,0,0,0)
            buf=C.create_string_buffer(self.pixels);g.SetStretchBltMode(dc,3)
            g.StretchDIBits(dc,x,y,96*s,65*s,0,0,96,65,buf,C.byref(bmi),0,0x00cc0020)
            self.buttons=[];margin=18*d;gap=12*d;by=h-76*d-pad;bh=44*d
            self.button(dc,(margin,by,w/2-gap/2,by+bh),'选择 / 暂停   Select','select')
            self.button(dc,(w/2+gap/2,by,w-margin,by+bh),'返回   Back','back')
            if pad:
                size=min(110*d,(w-60*d)/3);cell_h=48*d;cx=w/2-size/2;cy=by+58*d
                for label,key,col,row in [('↑  2','up',0,0),('←  4','left',-1,1),('→  6','right',1,1),('↓  8','down',0,2)]:
                    xx=cx+col*(size+8*d);yy=cy+row*(cell_h+8*d)
                    self.button(dc,(xx,yy,xx+size,yy+cell_h),label,key)
            self.text(dc,(0,h-26*d,w,h-5*d),'↑ ↓ ← → / WASD / 2 4 6 8  ·  Enter  ·  Esc  ·  F11',True)
        finally:
            if ps is not None:u.EndPaint(self.hwnd,C.byref(ps))

    def fullscreen(self):
        if not self.full:
            self.saved=W.RECT();u.GetWindowRect(self.hwnd,C.byref(self.saved));self.style=u.GetWindowLongPtrW(self.hwnd,-16)
            monitor=MONITOR();monitor.size=C.sizeof(MONITOR);u.GetMonitorInfoW(u.MonitorFromWindow(self.hwnd,2),C.byref(monitor))
            r=monitor.monitor;u.SetWindowLongPtrW(self.hwnd,-16,self.style&~0x00cf0000);u.SetWindowPos(self.hwnd,None,r.left,r.top,r.right-r.left,r.bottom-r.top,0x20|4)
        else:
            r=self.saved;u.SetWindowLongPtrW(self.hwnd,-16,self.style);u.SetWindowPos(self.hwnd,None,r.left,r.top,r.right-r.left,r.bottom-r.top,0x20|4)
        self.full=not self.full

    def command(self,item):
        if item==10:self.game.pause();self.refresh()
        elif item==11:self.fullscreen()
        elif item==12:u.DestroyWindow(self.hwnd)
        elif item in (20,30,31):
            key={20:'controls_visible',30:'muted',31:'play_intro'}[item]
            self.game.configure(key,not self.game.options[key])
            if item==30 and self.game.options[key]:winsound.PlaySound(None,0)
            self.check_menu();self.refresh()
        elif item in (21,22,23):self.game.configure('color_mode',('original','light','dark')[item-21]);self.check_menu();self.refresh()
        elif item==32:
            self.game.pause();self.refresh()
            u.MessageBoxW(self.hwnd,'方向键 / WASD / 数字 2 4 6 8：转向\nEnter / 5：选择或暂停\nEsc / P：暂停或返回\nF11：全屏\n\n支持鼠标、触屏、滑动转向。\n菜单中 Level 调整速度；Game type 选择玩法。\n自动保存；关闭窗口后可用 Continue 继续。\n设置中的启动动画在下次打开时生效。\n\nControls: arrows / WASD / 2 4 6 8; Enter to select; Esc to pause.\nSaves and settings: '+str(DATA),'Snake Xenzia',0x40)

    def dispatch(self,hwnd,msg,wp,lp):
        try:return self.message(hwnd,msg,wp,lp)
        except Exception:
            logging.exception('Window/game error')
            if not self.failed:
                self.failed=True;u.KillTimer(hwnd,1)
                u.MessageBoxW(hwnd,'运行出错，已保留之前的自动存档。\nError details: '+str(DATA/'game.log'),'Snake Xenzia',0x10)
            return 0

    def message(self,hwnd,msg,wp,lp):
        if msg in (0x0317,0x0318) and self.hwnd:self.paint(wp);return 0
        if msg==0x000f:
            if self.hwnd:self.paint()
            else:return u.DefWindowProcW(hwnd,msg,wp,lp)
            return 0
        if msg==0x0014:return 1
        if msg==0x0005:u.InvalidateRect(hwnd,None,False);return 0
        if msg==0x0113:
            if wp==1 and not self.failed:
                u.KillTimer(hwnd,1);self.game.tick();self.refresh();u.SetTimer(hwnd,1,self.game.delay(),None)
            elif wp==2:
                from test_portable import run as test
                result=test(DATA/'qa');result['window_seconds']=time.monotonic()-self.started
                self.capture_self()
                (DATA/'windows-test.json').write_text(json.dumps(result,indent=2))
                u.DestroyWindow(hwnd)
            return 0
        if msg==0x0111:self.command(wp&0xffff);return 0
        if msg==0x0100:
            if wp==0x7a:self.fullscreen()
            elif wp in KEYS:self.key(KEYS[wp])
            return 0
        if msg==0x0201:
            x=C.c_short(lp&0xffff).value;y=C.c_short((lp>>16)&0xffff).value
            for box,key in self.buttons:
                if box[0]<=x<box[2] and box[1]<=y<box[3]:self.key(key);return 0
            self.pointer=x,y,self.game.intro is not None;self.dragged=False;u.SetCapture(hwnd);return 0
        if msg==0x0200 and self.pointer and wp&1:
            x=C.c_short(lp&0xffff).value;y=C.c_short((lp>>16)&0xffff).value
            x0,y0,intro=self.pointer;dx,dy=x-x0,y-y0
            if not self.dragged and max(abs(dx),abs(dy))>24*self.dpi:
                self.dragged=True;self.key(('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>0 else 'up'))
            return 0
        if msg==0x0202 and self.pointer:
            x0,y0,intro=self.pointer;self.pointer=None;u.ReleaseCapture()
            if not self.dragged:
                if intro:
                    if self.game.intro is not None:self.key('select')
                else:self.game.tap((x0-self.left)/self.scale,(y0-self.top)/self.scale);self.refresh()
            return 0
        if msg==0x001c and not wp:
            if not self.failed:self.game.pause();self.refresh()
            winsound.PlaySound(None,0);return 0
        if msg==0x0010:u.DestroyWindow(hwnd);return 0
        if msg==0x0002:
            u.KillTimer(hwnd,1)
            if not self.failed:self.game.close()
            winsound.PlaySound(None,0);g.DeleteObject(self.font);g.DeleteObject(self.small);u.PostQuitMessage(0);return 0
        return u.DefWindowProcW(hwnd,msg,wp,lp)

    def capture_self(self):
        from PIL import Image
        rect=W.RECT();u.GetWindowRect(self.hwnd,C.byref(rect));w,h=rect.right-rect.left,rect.bottom-rect.top
        dc=u.GetWindowDC(self.hwnd);memory=g.CreateCompatibleDC(dc);bitmap=g.CreateCompatibleBitmap(dc,w,h);old=g.SelectObject(memory,bitmap)
        try:
            assert u.PrintWindow(self.hwnd,memory,2)
            g.SelectObject(memory,old)
            bmi=BMI(C.sizeof(BMI),w,-h,1,32,0,w*h*4,0,0,0,0);pixels=C.create_string_buffer(w*h*4)
            assert g.GetDIBits(memory,bitmap,0,h,pixels,C.byref(bmi),0)
            Image.frombytes('RGB',(w,h),pixels.raw,'raw','BGRX').save(DATA/'windows-window.png')
        finally:g.DeleteObject(bitmap);g.DeleteDC(memory);u.ReleaseDC(self.hwnd,dc)


def main():
    mutex=k.CreateMutexW(None,False,'Local\\SnakeXenziaPortable')
    if C.get_last_error()==183:
        hwnd=u.FindWindowW('SnakeXenziaPortable',None)
        if hwnd:u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd)
        return
    if not ensure_assets(DATA):
        from startup_windows import prepare
        if not prepare(DATA,u,k,WC,PROC,api):return
    window=Window();msg=W.MSG()
    while u.GetMessageW(C.byref(msg),None,0,0)>0:u.TranslateMessage(C.byref(msg));u.DispatchMessageW(C.byref(msg))

if __name__=='__main__':
    try:main()
    except Exception:
        logging.exception('Startup failed');u.MessageBoxW(None,'无法启动。错误日志 / Error log:\n'+str(DATA/'game.log'),'Snake Xenzia',0x10)
