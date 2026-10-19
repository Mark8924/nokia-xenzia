"""Native Cocoa application, with no external Python installation required."""
import io,json,logging,sys,time
from pathlib import Path
import objc
from AppKit import *
from Foundation import NSObject,NSTimer,NSData,NSMakeRect
from session import Session
from asset_store import resource,ensure_assets,import_assets

DATA=Path.home()/'Library/Application Support/Snake Xenzia'
if '--self-test' in sys.argv:DATA=Path(sys.argv[sys.argv.index('--self-test')+1])
DATA.mkdir(parents=True,exist_ok=True)
logging.basicConfig(filename=DATA/'game.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')


class Background(NSView):
    def drawRect_(self,rect):
        NSColor.colorWithCalibratedRed_green_blue_alpha_(.835,.85,.86,1).set();NSRectFill(self.bounds())


class Screen(NSView):
    def isFlipped(self):return True
    def acceptsFirstResponder(self):return True

    def drawRect_(self,rect):
        NSColor.colorWithCalibratedRed_green_blue_alpha_(.835,.85,.86,1).set();NSRectFill(self.bounds())
        if not hasattr(self,'image') or self.image is None:return
        width,height=self.bounds().size
        scale=max(1,int(min((width-24)/96,(height-24)/65)))
        self.geometry=((width-96*scale)/2,(height-65*scale)/2,scale)
        x,y,s=self.geometry
        NSColor.darkGrayColor().set();NSRectFill(NSMakeRect(x-4,y-4,96*s+8,65*s+8))
        NSGraphicsContext.currentContext().setImageInterpolation_(NSImageInterpolationNone)
        self.image.drawInRect_fromRect_operation_fraction_respectFlipped_hints_(NSMakeRect(x,y,96*s,65*s),NSZeroRect,NSCompositingOperationCopy,1,True,None)

    def keyDown_(self,event):
        key={123:'left',124:'right',125:'down',126:'up',36:'select',76:'select',53:'back'}.get(event.keyCode())
        if not key:key={'w':'up','a':'left','s':'down','d':'right','2':'up','4':'left','6':'right','8':'down','5':'select',' ':'select','p':'back'}.get(event.charactersIgnoringModifiers().lower())
        if key:self.owner.input(key)
        elif event.keyCode()==103:self.window().toggleFullScreen_(None)
        else:objc.super(Screen,self).keyDown_(event)

    def mouseDown_(self,event):
        point=self.convertPoint_fromView_(event.locationInWindow(),None)
        self.pointer=(point.x,point.y,self.owner.game.intro is not None);self.dragged=False
        self.window().makeFirstResponder_(self)

    def mouseDragged_(self,event):
        if not hasattr(self,'pointer') or self.pointer is None:return
        point=self.convertPoint_fromView_(event.locationInWindow(),None);x,y,intro=self.pointer;dx=point.x-x;dy=point.y-y
        if not self.dragged and max(abs(dx),abs(dy))>24:
            self.dragged=True;self.owner.input(('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>0 else 'up'))

    def mouseUp_(self,event):
        if not hasattr(self,'pointer') or self.pointer is None:return
        x,y,intro=self.pointer;self.pointer=None
        if not self.dragged:
            if intro:
                if self.owner.game.intro is not None:self.owner.input('select')
            else:
                left,top,scale=self.geometry;self.owner.game.tap((x-left)/scale,(y-top)/scale);self.owner.refresh()


class ContactButton(NSButton):
    def acceptsFirstResponder(self):return False
    def mouseDown_(self,event):
        self.contact=True;self.highlight_(True);self.owner.input(self.command)
        # Native tracking supplies visual feedback without a second action.
        try:objc.super(ContactButton,self).mouseDown_(event)
        finally:self.highlight_(False);self.contact=False


class Controller(NSObject):
    def applicationDidFinishLaunching_(self,notification):
        try:
            if not ensure_assets(DATA):
                alert=NSAlert.alloc().init();alert.setMessageText_('Import original resources / 导入原版资源')
                alert.setInformativeText_('The host does not include Nokia game data. Select a ZIP or folder containing your supported extracted assets. Import is only needed once.\n\n安装包不含诺基亚原版游戏数据。请选择包含已提取资源的 ZIP 或文件夹，只需导入一次。')
                alert.addButtonWithTitle_('Choose / 选择');alert.addButtonWithTitle_('Cancel / 取消')
                if alert.runModal()!=NSAlertFirstButtonReturn:NSApp.terminate_(None);return
                while True:
                    panel=NSOpenPanel.openPanel();panel.setCanChooseFiles_(True);panel.setCanChooseDirectories_(True);panel.setAllowsMultipleSelection_(False)
                    if panel.runModal()!=NSModalResponseOK:NSApp.terminate_(None);return
                    try:import_assets(panel.URL().path(),DATA);break
                    except Exception as error:
                        alert=NSAlert.alloc().init();alert.setMessageText_('Import failed / 导入失败');alert.setInformativeText_(str(error));alert.runModal()
            self.game=Session(DATA);self.failed=False;self.timer=None;self.current_sound=None
            self.window=NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(NSMakeRect(0,0,760,820),NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable,NSBackingStoreBuffered,False)
            self.window.setTitle_('Snake Xenzia');self.window.setDelegate_(self);self.window.setMinSize_((430,520))
            self.window.setReleasedWhenClosed_(False)
            self.content=Background.alloc().initWithFrame_(self.window.contentView().bounds());self.window.setContentView_(self.content)
            self.screen=Screen.alloc().initWithFrame_(NSMakeRect(0,240,760,530));self.screen.owner=self;self.screen.image=None;self.content.addSubview_(self.screen)
            self.header=NSTextField.labelWithString_('S N A K E   X E N Z I A');self.header.setAlignment_(NSTextAlignmentCenter);self.header.setFont_(NSFont.boldSystemFontOfSize_(19));self.content.addSubview_(self.header)
            self.buttons=[]
            for label,key in [('选择 / 暂停   Select','select'),('返回   Back','back'),('↑  2','up'),('←  4','left'),('●  5','select'),('→  6','right'),('↓  8','down')]:
                button=ContactButton.alloc().initWithFrame_(NSMakeRect(0,0,100,40));button.setTitle_(label);button.setBezelStyle_(NSBezelStyleRounded);button.setFont_(NSFont.systemFontOfSize_(16));button.owner=self;button.command=key;button.contact=False;button.setTarget_(self);button.setAction_('button:');self.content.addSubview_(button);self.buttons.append(button)
            self.create_menu();self.layout();self.refresh();self.window.center();self.window.makeKeyAndOrderFront_(None);self.window.makeFirstResponder_(self.screen)
            NSApp.activateIgnoringOtherApps_(True);self.schedule(1)
            if '--self-test' in sys.argv:NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(3,self,'selftest:',None,False)
        except Exception:self.error()

    @objc.python_method
    def create_menu(self):
        menu=NSMenu.alloc().init();appitem=NSMenuItem.alloc().init();menu.addItem_(appitem)
        appmenu=NSMenu.alloc().initWithTitle_('Snake Xenzia');appitem.setSubmenu_(appmenu)
        quit=NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('退出 Snake Xenzia','terminate:','q');appmenu.addItem_(quit)
        item=NSMenuItem.alloc().init();menu.addItem_(item);settings=NSMenu.alloc().initWithTitle_('游戏 / Game');item.setSubmenu_(settings)
        self.items={}
        for number,label,shortcut in [(10,'暂停 / Pause','p'),(11,'全屏 / Fullscreen','f'),(20,'屏幕方向键 / Direction pad',''),(21,'原版配色 / Original',''),(22,'白底黑色 / Light',''),(23,'黑底白色 / Dark',''),(30,'音效 / Sound',''),(31,'启动动画 / Opening animation',''),(32,'操作说明 / Help','')]:
            entry=NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(label,'command:',shortcut);entry.setTarget_(self);entry.setTag_(number);settings.addItem_(entry);self.items[number]=entry
        NSApp.setMainMenu_(menu);self.checks()

    @objc.python_method
    def checks(self):
        options=self.game.options
        for item,on in [(20,options['controls_visible']),(30,not options['muted']),(31,options['play_intro']),*[(21+i,options['color_mode']==mode) for i,mode in enumerate(('original','light','dark'))]]:self.items[item].setState_(1 if on else 0)

    @objc.python_method
    def layout(self):
        w,h=self.content.bounds().size;pad=188 if self.game.options['controls_visible'] else 0
        self.header.setFrame_(NSMakeRect(12,h-44,w-24,26));self.screen.setFrame_(NSMakeRect(0,74+pad,w,h-126-pad))
        self.buttons[0].setFrame_(NSMakeRect(16,24+pad,w/2-22,44));self.buttons[1].setFrame_(NSMakeRect(w/2+6,24+pad,w/2-22,44))
        for button,(col,row) in zip(self.buttons[2:],[(0,2),(-1,1),(0,1),(1,1),(0,0)]):
            button.setHidden_(not self.game.options['controls_visible']);button.setFrame_(NSMakeRect(w/2-54+col*118,20+row*56,108,46))

    def windowDidResize_(self,notification):
        if hasattr(self,'game'):self.layout()

    @objc.python_method
    def schedule(self,delay):
        if self.timer is not None:self.timer.invalidate()
        self.timer=NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(delay/1000,self,'tick:',None,False)
        from Foundation import NSRunLoop,NSRunLoopCommonModes
        NSRunLoop.mainRunLoop().addTimer_forMode_(self.timer,NSRunLoopCommonModes)

    def tick_(self,timer):
        if self.failed:return
        try:delay=self.game.tick();self.refresh();self.schedule(delay)
        except Exception:self.error()

    @objc.python_method
    def refresh(self):
        self.game.pixels();image=self.game.active.presentation(self.game.options['color_mode'])
        output=io.BytesIO();image.save(output,'PNG',compress_level=0);png=output.getvalue()
        self.screen.image=NSImage.alloc().initWithData_(NSData.dataWithBytes_length_(png,len(png)));self.screen.setNeedsDisplay_(True)
        for effect in json.loads(self.game.take_audio()):
            if self.current_sound:self.current_sound.stop()
            path=resource('audio/'+effect+'.wav')
            self.current_sound=NSSound.alloc().initWithContentsOfFile_byReference_(str(path),False);self.current_sound.play()

    @objc.python_method
    def input(self,key):
        if self.failed:return
        try:
            was=self.game.is_menu();self.game.key(key);self.refresh()
            if was and not self.game.is_menu():self.schedule(self.game.delay())
        except Exception:self.error()

    def command_(self,sender):
        item=sender.tag()
        try:
            if item==10:self.game.pause()
            elif item==11:self.window.toggleFullScreen_(None)
            elif item in (20,30,31):
                key={20:'controls_visible',30:'muted',31:'play_intro'}[item];self.game.configure(key,not self.game.options[key])
                if item==30 and self.current_sound and self.game.options[key]:self.current_sound.stop()
                self.layout()
            elif item in (21,22,23):self.game.configure('color_mode',('original','light','dark')[item-21])
            elif item==32:
                self.game.pause();alert=NSAlert.alloc().init();alert.setMessageText_('Snake Xenzia');alert.setInformativeText_('方向键 / WASD / 2 4 6 8：转向\nEnter / 5：选择或暂停\nEsc / P：返回；⌘F：全屏\n\n菜单 Level 调整速度，Game type 选择玩法。\n自动保存；通过 Continue 继续。\n启动动画在下次打开时生效。\n\n存档位置：'+str(DATA));alert.runModal()
            self.checks();self.refresh();self.window.makeFirstResponder_(self.screen)
        except Exception:self.error()

    def button_(self,sender):
        if not sender.contact:self.input(sender.command)

    def applicationDidResignActive_(self,notification):
        if hasattr(self,'game') and not self.failed:self.game.pause();self.refresh()

    def windowWillClose_(self,notification):NSApp.terminate_(None)
    def applicationShouldTerminateAfterLastWindowClosed_(self,app):return True
    def applicationShouldTerminate_(self,app):
        if hasattr(self,'game') and not self.failed:self.game.close()
        return NSTerminateNow

    def selftest_(self,timer):
        try:
            from test_portable import run
            result=run(DATA/'qa')
            rep=self.content.bitmapImageRepForCachingDisplayInRect_(self.content.bounds());self.content.cacheDisplayInRect_toBitmapImageRep_(self.content.bounds(),rep)
            rep.representationUsingType_properties_(NSBitmapImageFileTypePNG,{}).writeToFile_atomically_(str(DATA/'mac-window.png'),True)
            (DATA/'mac-test.json').write_text(json.dumps(result,indent=2));NSApp.terminate_(None)
        except Exception:self.error()

    @objc.python_method
    def error(self):
        logging.exception('Cocoa/game error');self.failed=True
        if self.timer is not None:self.timer.invalidate()
        alert=NSAlert.alloc().init();alert.setMessageText_('运行错误 / Game error');alert.setInformativeText_('已保留之前的自动存档。\n错误日志 / Error log:\n'+str(DATA/'game.log'));alert.runModal()


def main():
    app=NSApplication.sharedApplication();app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    controller=Controller.alloc().init();app.setDelegate_(controller);app.run()


if __name__=='__main__':main()
