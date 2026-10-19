"""GTK New game, short focus transitions and held-select regression check."""
import os,tempfile,time
from types import SimpleNamespace
from pathlib import Path
scratch=tempfile.TemporaryDirectory(prefix='xenzia-input-qa-')
os.environ['XDG_DATA_HOME']=scratch.name
from app import Game,Gtk,GLib,DATA


def drain(seconds=.13):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)
        time.sleep(.001)


def main():
    DATA.mkdir(parents=True,exist_ok=True)
    app=Gtk.Application(application_id='local.nokia.xenzia.inputqa');app.register(None)
    w=Game(app)
    if w.tick_source:GLib.source_remove(w.tick_source);w.tick_source=None
    w.is_active=lambda:True
    for iteration in range(10):
        # Touch the actual menu hit test, from both fresh and paused menus.
        labels=w.runtime.menu_labels();i=labels.index('New game')
        w.runtime.objs[w.runtime.menu]['selected']=0
        left,top,scale=w.geometry()
        point=SimpleNamespace(button=1,x=left+20*scale,y=top+(20+12*i)*scale)
        w.press(w.screen,point);w.release(w.screen,point)
        assert not w.runtime.menu,('New game did not enter play',iteration)
        # A transient focus-out while the app is regaining focus must not
        # schedule a stale pause which turns New game into Continue.
        w.focus_out();w.focus_in();drain()
        assert not w.runtime.menu,('stale focus pause',iteration)
        w.focus_out();drain()
        assert not w.runtime.menu,'active window must not be auto-paused'
        w.input('back')
    w.input('select');assert not w.runtime.menu
    w.is_active=lambda:False;w.focus_out();drain();assert w.runtime.menu
    assert 'Continue' in w.runtime.menu_labels(),'genuine focus loss should still pause'
    w.is_active=lambda:True
    event=SimpleNamespace(keyval=0xff0d,hardware_keycode=36)
    w.key_event(w,event);assert not w.runtime.menu
    w.key_event(w,event);assert not w.runtime.menu,'held Enter must not immediately pause'
    w.key_release(w,event);w.key_event(w,event);assert w.runtime.menu
    w.close_game();w.destroy();drain(.02)
    print('10 New game menu taps, transient focus recovery, genuine auto-pause and held-key filtering PASS',flush=True)


if __name__=='__main__':
    try:main()
    finally:scratch.cleanup()
