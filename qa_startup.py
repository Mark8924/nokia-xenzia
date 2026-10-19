"""GTK startup/intro integration checks with isolated settings and progress."""
import os,tempfile,json,time
from pathlib import Path

scratch=tempfile.TemporaryDirectory(prefix='nokia-intro-qa-')
os.environ['XDG_DATA_HOME']=scratch.name
from app import Game,Gtk,GLib,DATA,STATE
from runtime import NokiaRuntime
from qa_play import original_state,route


def remove_timer(w):
    if w.tick_source:GLib.source_remove(w.tick_source);w.tick_source=None


def close(w):
    w.close_game();w.destroy()
    while GLib.MainContext.default().pending():GLib.MainContext.default().iteration(False)


def body_components(image):
    points={(x,y) for y in range(65) for x in range(96) if max(image.getpixel((x,y)))<240}
    sizes=[]
    while points:
        todo=[points.pop()];size=0
        while todo:
            x,y=todo.pop();size+=1
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    q=x+dx,y+dy
                    if q in points:points.remove(q);todo.append(q)
        if size>=3:sizes.append(size)
    return sizes


def main():
    DATA.mkdir(parents=True)
    application=Gtk.Application(application_id='local.nokia.xenzia.startupqa')
    application.register(None)
    w=Game(application);remove_timer(w)
    assert not w.play_intro and w.intro_runtime is None and w.runtime.menu
    assert w.runtime.menu_labels()[0]=='New game'
    close(w)
    print('Default startup: direct menu PASS',flush=True)

    # A real in-game fixture, not just a menu snapshot or a fabricated score.
    r=NokiaRuntime();r.random.seed(265);r.key('back');r.activate(0)
    for step in range(120):
        field,s,f,head,food,body=original_state(r)
        path=route(head,food,body);assert path;r.key(path[0])
        for _ in range(4):r.frame(1)
        if r.word(r.state+8)>=3:break
    score=r.word(r.state+8)
    assert score>=3
    progress=original_state(r)[3:];r.save(STATE)
    (DATA/'settings.json').write_text(json.dumps({'muted':True,'color_mode':'dark','controls_visible':False}))
    w=Game(application);remove_timer(w)
    assert original_state(w.runtime)[3:]==progress
    w.intro_option.set_active(True)
    assert w.play_intro and w.intro_runtime is None,'enabling is for the next startup'
    close(w)

    w=Game(application);remove_timer(w)
    assert w.intro_runtime is not None and w.runtime.menu
    assert w.muted and w.color_mode=='dark' and not w.controls_visible
    w.last_save=0;w.tick();remove_timer(w)
    saved=NokiaRuntime();saved.restore(STATE)
    assert saved.word(saved.state+8)==score and original_state(saved)[3:]==progress
    close(w)
    saved=NokiaRuntime();saved.restore(STATE)
    assert saved.word(saved.state+8)==score and original_state(saved)[3:]==progress
    print('Intro enabled, autosave and close midway preserve real progress PASS',flush=True)

    w=Game(application);remove_timer(w);frames=set()
    for index in range(300):
        if w.intro_runtime is None:break
        frames.add(w.intro_runtime.image.tobytes())
        assert len(body_components(w.intro_runtime.image))<=1,('intro snake split into flashing fragments',index)
        w.tick();remove_timer(w)
    assert w.intro_runtime is None and w.runtime.menu
    assert len(frames)>10,('native intro did not animate',len(frames))
    assert w.runtime.word(w.runtime.state+8)==score and original_state(w.runtime)[3:]==progress
    close(w)
    print('Native intro animates and returns to saved menu PASS',index,'frames',len(frames),'unique',flush=True)

    w=Game(application);remove_timer(w);assert w.intro_runtime is not None
    w.input('select');remove_timer(w)
    assert w.intro_runtime is None and w.runtime.menu,'skip must not start Continue'
    close(w)
    w=Game(application);remove_timer(w);assert w.intro_runtime is not None
    w.intro_option.set_active(False);remove_timer(w)
    assert w.intro_runtime is None
    close(w)
    w=Game(application);remove_timer(w)
    assert not w.play_intro and w.intro_runtime is None and w.runtime.menu
    assert w.runtime.word(w.runtime.state+8)==score and original_state(w.runtime)[3:]==progress
    close(w)
    print('Skip, toggle-off and subsequent direct startup PASS',flush=True)


if __name__=='__main__':
    try:main()
    finally:scratch.cleanup()
