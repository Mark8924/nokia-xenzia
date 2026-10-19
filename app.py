#!/usr/bin/env python3
"""GTK host for the unmodified Nokia RH-93 Snake Xenzia application."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo
import time
import logging
import os
import json
import signal
from pathlib import Path
from runtime import NokiaRuntime
from controls import TurnBuffer,DIRECTIONS
from asset_store import ensure_assets

DATA = Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'nokia-xenzia'
STATE = DATA/'save.state'


class Game(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title='Snake Xenzia')
        from sound import TonePlayer
        self.set_default_size(820, 850)
        self.set_size_request(420, 600)
        self.set_icon_from_file(str(Path(__file__).parent/'assets/icon.png'))
        self.runtime = NokiaRuntime()
        try:settings=json.loads((DATA/'settings.json').read_text())
        except (OSError,ValueError):settings={}
        if not isinstance(settings,dict):settings={}
        self.muted=settings.get('muted',False)
        self.color_mode=settings.get('color_mode','original')
        if self.color_mode not in ('original','light','dark'):self.color_mode='original'
        self.controls_visible=settings.get('controls_visible',True)
        self.play_intro=bool(settings.get('play_intro',False))
        self.player=TonePlayer()
        self.turns=TurnBuffer()
        self.tick_source=None
        self.last_save = time.monotonic()
        self.dead = False
        self.dirty = True
        if STATE.exists():
            try:
                self.runtime.restore(STATE)
                if not self.runtime.menu:
                    self.runtime.key('back')
            except Exception:
                logging.exception('Could not restore previous game')
                STATE.rename(STATE.with_suffix('.previous'))
                self.runtime = NokiaRuntime()
        # The saved session always remains separate from the disposable intro.
        # Even closing midway through the animation must save the real progress.
        if not self.runtime.menu:self.runtime.key('back')
        self.intro_runtime=NokiaRuntime() if self.play_intro else None

        header = Gtk.HeaderBar(title='Snake Xenzia', subtitle='Nokia 1110i · 原版程序')
        header.set_show_close_button(True)
        self.set_titlebar(header)
        info = Gtk.Button.new_from_icon_name('help-about-symbolic', Gtk.IconSize.BUTTON)
        info.set_tooltip_text('操作说明')
        info.connect('clicked', self.help)
        header.pack_end(info)
        preferences=Gtk.MenuButton()
        preferences.add(Gtk.Image.new_from_icon_name('emblem-system-symbolic',Gtk.IconSize.BUTTON))
        preferences.set_tooltip_text('设置')
        popover=Gtk.Popover.new(preferences)
        options=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        options.set_border_width(14)
        self.intro_option=Gtk.CheckButton(label='启动时播放开场动画')
        self.intro_option.set_active(self.play_intro)
        self.intro_option.set_tooltip_text('每次打开软件时播放原版开场；不勾选则直接进入菜单')
        self.intro_option.connect('toggled',self.toggle_intro)
        options.pack_start(self.intro_option,False,False,0)
        popover.add(options);options.show_all()
        preferences.set_popover(popover)
        header.pack_end(preferences)
        self.audio=Gtk.ToggleButton()
        self.audio.set_active(not self.muted)
        self.audio.set_label('音效')
        self.audio.set_tooltip_text('开关原机采样音色的游戏音效')
        self.audio.connect('toggled', self.toggle_audio)
        header.pack_end(self.audio)
        colors=Gtk.ComboBoxText()
        for key,label in [('original','跟随原版'),('light','白底黑色'),('dark','黑底白色')]:colors.append(key,label)
        colors.set_active_id(self.color_mode)
        colors.set_tooltip_text('配色；只改变显示，保留原版灰度边缘')
        colors.connect('changed',self.change_colors)
        header.pack_end(colors)
        controls=Gtk.ToggleButton(label='方向键')
        controls.set_active(self.controls_visible)
        controls.set_tooltip_text('显示／隐藏屏幕方向键；实体键盘始终可用')
        controls.connect('toggled',self.toggle_controls)
        header.pack_end(controls)
        full = Gtk.Button.new_from_icon_name('view-fullscreen-symbolic', Gtk.IconSize.BUTTON)
        full.set_tooltip_text('全屏 / F11')
        full.connect('clicked', lambda *_: self.toggle_fullscreen())
        header.pack_start(full)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)
        self.add(box)
        self.screen = Gtk.DrawingArea()
        self.screen.set_hexpand(True)
        self.screen.set_vexpand(True)
        self.screen.set_can_focus(True)
        self.screen.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                               Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.TOUCH_MASK)
        self.screen.connect('draw', self.draw)
        self.screen.connect('button-press-event', self.press)
        self.screen.connect('button-release-event', self.release)
        box.pack_start(self.screen, True, True, 0)

        soft = Gtk.Box(spacing=12)
        self.button(soft, '选择 / 暂停', 'select')
        self.button(soft, '返回', 'back')
        box.pack_start(soft, False, False, 0)

        grid = Gtk.Grid(column_spacing=10, row_spacing=8, halign=Gtk.Align.CENTER)
        self.controls=grid
        self.direction_gestures=[]
        for label, key, x, y in [('2  ↑','up',1,0), ('4  ←','left',0,1),
                                 ('6  →','right',2,1), ('8  ↓','down',1,2)]:
            button = Gtk.Button(label=label)
            button.set_size_request(116, 46)
            button.set_can_focus(False)
            if key in DIRECTIONS:
                # Game controls should act at contact, not after finger-up.
                # GestureMultiPress handles touch and mouse without duplicate
                # emulated pointer clicks, while GTK keeps its normal styling.
                gesture=Gtk.GestureMultiPress.new(button)
                gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
                gesture.set_button(1)
                def contact(*_,b=button,k=key):
                    b._direction_contact=True
                    self.input(k)
                def released(*_,b=button):
                    def clear():b._direction_contact=False;return False
                    GLib.idle_add(clear)
                gesture.connect('pressed',contact)
                gesture.connect('released',released)
                gesture.connect('cancel',released)
                button.connect('clicked',lambda b,k=key:None if getattr(b,'_direction_contact',False) else self.input(k))
                self.direction_gestures.append(gesture)
            else:button.connect('clicked', lambda _, k=key: self.input(k))
            grid.attach(button, x, y, 1, 1)
        box.pack_start(grid, False, False, 0)
        hint = Gtk.Label(label='方向键 / WASD / 2 4 6 8　·　Enter 选择　·　Esc 暂停　·　自动保存')
        hint.get_style_context().add_class('dim-label')
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 0)
        self.connect('key-press-event', self.key_event)
        self.connect('delete-event', self.close_game)
        self.connect('focus-out-event', self.focus_out)
        self.quit_source=GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,signal.SIGTERM,self.terminate)
        self.full = False
        self.pointer = None
        self.pointer_started_intro=False
        self.show_all()
        self.controls.set_visible(self.controls_visible)
        self.screen.grab_focus()
        self.tick_source=GLib.timeout_add(1, self.tick)
        if os.environ.get('NOKIA_QA_CAPTURE'):
            GLib.timeout_add(4500,self.capture_own_window)

    def capture_own_window(self):
        # Renders only this application's widgets, never another desktop window.
        surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,self.get_allocated_width(),self.get_allocated_height())
        self.draw_to_surface(surface)
        surface.write_to_png(os.environ['NOKIA_QA_CAPTURE'])
        return False

    def draw_to_surface(self,surface):
        Gtk.Widget.draw(self,cairo.Context(surface))

    def button(self, parent, label, key):
        b = Gtk.Button(label=label)
        b.set_size_request(160, 46)
        b.set_can_focus(False)
        b.connect('clicked', lambda *_: self.input(key))
        parent.pack_start(b, True, True, 0)

    def toggle_fullscreen(self):
        self.full = not self.full
        self.fullscreen() if self.full else self.unfullscreen()

    def input(self, key):
        try:
            if self.intro_runtime is not None:
                self.finish_intro()
                return
            was_menu=bool(self.runtime.menu)
            if key in DIRECTIONS:self.turns.push(self.runtime,key)
            else:
                self.turns.reset()
                self.runtime.key(key)
            if was_menu and not self.runtime.menu:
                # Do not inherit the menu's up-to-200ms idle polling timer.
                if self.tick_source:GLib.source_remove(self.tick_source)
                self.tick_source=GLib.timeout_add(max(5,min(1000,self.runtime.delay)),self.tick)
            self.dirty = True
            self.screen.queue_draw()
        except Exception:
            self.fail()

    def key_event(self, widget, event):
        name = Gdk.keyval_name(event.keyval)
        key = {'Up':'up','Down':'down','Left':'left','Right':'right',
               'w':'up','s':'down','a':'left','d':'right','W':'up','S':'down','A':'left','D':'right',
               '2':'up','8':'down','4':'left','6':'right','KP_2':'up','KP_8':'down','KP_4':'left','KP_6':'right',
               'Return':'select','KP_Enter':'select','5':'select','KP_5':'select','space':'select',
               'Escape':'back','p':'back','P':'back','BackSpace':'back'}.get(name)
        if key:
            self.input(key)
            return True
        if name == 'F11':
            self.toggle_fullscreen()
            return True
        return False

    def geometry(self):
        w, h = self.screen.get_allocated_width(), self.screen.get_allocated_height()
        scale = max(1, int(min((w-16)/96, (h-16)/65)))
        return (w-96*scale)/2, (h-65*scale)/2, scale

    def draw(self, widget, cr):
        if self.dead:
            return False
        r = self.intro_runtime if self.intro_runtime is not None else self.runtime
        r.render_menu()
        x, y, s = self.geometry()
        cr.set_source_rgb(.83, .84, .85)
        cr.paint()
        cr.set_source_rgb(.22, .23, .24)
        cr.rectangle(x-5, y-5, 96*s+10, 65*s+10)
        cr.fill()
        buf = bytearray(r.presentation(self.color_mode).tobytes('raw', 'BGRX'))
        surface = cairo.ImageSurface.create_for_data(buf, cairo.FORMAT_RGB24, 96, 65, 96*4)
        cr.save()
        cr.translate(x, y)
        cr.scale(s, s)
        cr.set_source_surface(surface)
        cr.get_source().set_filter(cairo.FILTER_NEAREST)
        cr.rectangle(0, 0, 96, 65)
        cr.fill()
        cr.restore()
        return False

    def press(self, widget, event):
        if event.button != 1:
            return False
        self.pointer = (event.x, event.y)
        self.pointer_started_intro=self.intro_runtime is not None
        return True

    def release(self, widget, event):
        if not self.pointer:
            return False
        x0, y0 = self.pointer
        self.pointer = None
        if self.pointer_started_intro:
            self.pointer_started_intro=False
            if self.intro_runtime is not None:self.input('select')
            return True
        dx, dy = event.x-x0, event.y-y0
        if max(abs(dx), abs(dy)) > 24:
            self.input(('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('down' if dy>0 else 'up'))
        elif self.runtime.menu:
            x, y, s = self.geometry()
            px, py = (event.x-x)/s, (event.y-y)/s
            if 0 <= px < 96 and 0 <= py < 65:
                if self.runtime.overlay:
                    self.input('back' if py>52 else 'down')
                elif py>52:
                    self.input('select' if px<48 else 'back')
                elif py>=15:
                    ob=self.runtime.objs[self.runtime.menu]
                    n=len(ob['items'])
                    selected=ob['selected']
                    offset=max(0,min(selected-1,n-3))
                    sel=offset+int((py-15)//12)
                    if 0<=sel<n:
                        ob['selected']=sel
                        self.input('select')
        return True

    def tick(self):
        self.tick_source=None
        if self.dead:
            return False
        try:
            r=self.intro_runtime if self.intro_runtime is not None else self.runtime
            if self.intro_runtime is not None:
                r.frame_for_display(realtime=True)
                if r.menu:self.intro_runtime=None
                self.screen.queue_draw()
            elif not r.menu:
                # A newly presented host frame invalidates the entire tiny
                # 96x65 canvas. Ask the original game to repaint all pixels;
                # retaining a phone's partially damaged backbuffer here leaves
                # old antialiased edges on a desktop canvas.
                r.frame_for_display(realtime=True)
                self.turns.sync(r)
                self.screen.queue_draw()
            if not self.muted:
                for command in r.sounds:self.player.play(command)
            r.sounds.clear()
            if time.monotonic()-self.last_save>15:
                self.runtime.save(STATE)
                self.last_save=time.monotonic()
            active=self.intro_runtime if self.intro_runtime is not None else self.runtime
            self.tick_source=GLib.timeout_add(max(5,min(1000,active.delay)) if not active.menu else 200,self.tick)
        except Exception:
            self.fail()
        return False

    def focus_out(self, *_):
        if not self.runtime.menu and self.runtime.word(self.runtime.state):
            GLib.idle_add(self.pause_for_focus)
        return False

    def toggle_audio(self, button):
        self.muted=not button.get_active()
        if self.muted:self.player.stop()
        self.save_settings()

    def change_colors(self, combo):
        self.color_mode=combo.get_active_id() or 'original'
        self.save_settings()
        self.screen.queue_draw()

    def toggle_controls(self, button):
        self.controls_visible=button.get_active()
        self.controls.set_visible(self.controls_visible)
        self.save_settings()
        self.screen.grab_focus()

    def toggle_intro(self, button):
        self.play_intro=button.get_active()
        self.save_settings()
        if not self.play_intro and self.intro_runtime is not None:self.finish_intro()

    def finish_intro(self):
        self.intro_runtime=None
        if self.tick_source:GLib.source_remove(self.tick_source)
        self.tick_source=GLib.timeout_add(1,self.tick)
        self.screen.queue_draw()

    def save_settings(self):
        DATA.mkdir(parents=True,exist_ok=True)
        path=DATA/'settings.json';temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'muted':self.muted,'color_mode':self.color_mode,'controls_visible':self.controls_visible,'play_intro':self.play_intro}))
        temporary.replace(path)

    def pause_for_focus(self):
        if not self.dead and not self.runtime.menu:
            self.input('back')
        return False

    def close_game(self, *_):
        if not self.dead:
            try:
                if not self.runtime.menu:
                    self.runtime.key('back')
                self.runtime.save(STATE)
            except Exception:
                logging.exception('Saving game')
        self.dead = True
        # Drop gesture references while their buttons are still alive; leaving
        # them for Python finalization after Gtk destroys widgets warns in GTK3.
        for gesture in self.direction_gestures:gesture.reset()
        self.direction_gestures.clear()
        self.player.close()
        if self.tick_source:GLib.source_remove(self.tick_source);self.tick_source=None
        if self.quit_source:GLib.source_remove(self.quit_source);self.quit_source=None
        return False

    def terminate(self):
        self.quit_source=None
        self.close_game()
        self.destroy()
        return False

    def fail(self):
        logging.exception('Game runtime error')
        self.dead = True
        self.player.close()
        dialog = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.ERROR,
                                  buttons=Gtk.ButtonsType.CLOSE, text='游戏运行中出现错误')
        dialog.format_secondary_text('已有存档保留。详细记录在 ~/.local/share/nokia-xenzia/game.log。')
        dialog.run()
        dialog.destroy()
        self.destroy()

    def help(self, *_):
        self.pause_for_focus()
        dialog=Gtk.MessageDialog(transient_for=self,buttons=Gtk.ButtonsType.CLOSE,text='Snake Xenzia')
        dialog.format_secondary_text(
            '运行 Nokia 1110i（RH-93，7.02）固件中的原版游戏程序。\n'
            '蛇、食物、碰撞、计分、速度与迷宫均由原程序计算和绘制。\n'
            '原机字体已提取；手机菜单系统由本地运行层提供。\n\n'
            '方向键、WASD 或 2/4/6/8 控制，也可点方向按钮或在屏幕上滑动。\n'
            'Enter / 5 选择；Esc / P 暂停与返回；F11 全屏。\n'
            'Level：速度等级；Classic：经典；Modern：迷宫；Campaign：闯关。\n'
            '顶栏可切换正反色、显示／隐藏方向键及开关音效。\n'
            '齿轮设置中可勾选“启动时播放开场动画”；播放时点屏幕或按键可跳过。\n'
            '退出及游玩中自动保存，下次可 Continue。')
        dialog.run()
        dialog.destroy()


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=DATA/'game.log',level=logging.WARNING,
                        format='%(asctime)s %(levelname)s %(message)s')
    application=Gtk.Application(application_id='local.nokia.xenzia')
    def activate(app):
        if app.get_active_window():
            app.get_active_window().present();return
        if not ensure_assets(DATA):
            from startup_gtk import prepare
            if not prepare(app, DATA):
                app.quit();return
        Game(app)
    application.connect('activate',activate)
    application.run()


if __name__=='__main__':
    main()
