"""Shared, single-thread-owned controller for the Android and Windows hosts."""
import json
import logging
import time
from pathlib import Path
from runtime import NokiaRuntime
from controls import TurnBuffer, DIRECTIONS
from asset_store import resource


class Session:
    def __init__(self, directory):
        self.data=Path(directory);self.data.mkdir(parents=True,exist_ok=True)
        self.state=self.data/'save.state';self.settings_file=self.data/'settings.json'
        try:self.options=json.loads(self.settings_file.read_text())
        except (OSError,ValueError):self.options={}
        if not isinstance(self.options,dict):self.options={}
        defaults={'muted':False,'color_mode':'original','controls_visible':True,'play_intro':False}
        self.options={key:self.options.get(key,value) for key,value in defaults.items()}
        if self.options['color_mode'] not in ('original','light','dark'):self.options['color_mode']='original'
        self.runtime=NokiaRuntime()
        if self.state.exists():
            try:self.runtime.restore(self.state)
            except Exception:
                logging.exception('Previous save could not be restored')
                self.state.replace(self.state.with_suffix('.previous'))
                self.runtime=NokiaRuntime()
        if not self.runtime.menu:self.runtime.key('back')
        self.intro=NokiaRuntime() if self.options['play_intro'] else None
        self.turns=TurnBuffer();self.last_save=time.monotonic();self.audio=[]
        self.effects=json.loads(resource('audio/effects.json').read_text())
        self.audio_sink=None
        self.runtime.sound_sink=self.sound
        if self.intro is not None:self.intro.sound_sink=self.sound

    @property
    def active(self):return self.intro if self.intro is not None else self.runtime

    def sounds(self,r):
        r.sounds.clear()

    def sound(self,command):
        effect=self.effects.get(','.join(map(str,command)))
        if effect and not self.options['muted']:
            name=effect['file'].split('.')[0]
            if self.audio_sink is not None:self.audio_sink(name)
            else:self.audio.append(name)

    def set_audio_sink(self,host):self.audio_sink=host.playEffect

    def take_audio(self):
        sounds=self.audio;self.audio=[]
        return json.dumps(sounds)

    def delay(self):return self.active.wait_ms()
    def is_menu(self):return bool(self.active.menu)
    def is_intro(self):return self.intro is not None
    def skip_intro(self):self.intro=None

    def tick(self):
        r=self.active
        if self.intro is not None:
            r.frame_for_display(realtime=True)
            if r.menu:self.intro=None
        elif not r.menu:
            r.frame_for_display(realtime=True);self.turns.sync(r)
        self.sounds(r)
        if time.monotonic()-self.last_save>15:self.save()
        return self.delay()

    def key(self,key):
        if self.intro is not None:self.intro=None;return
        if key in DIRECTIONS:self.turns.push(self.runtime,key)
        else:self.turns.reset();self.runtime.key(key)
        self.sounds(self.runtime)

    def tap(self,x,y):
        if self.intro is not None:self.intro=None;return
        r=self.runtime
        if not r.menu:return
        if not (0<=x<96 and 0<=y<65):return
        if r.overlay:
            if r.overlay['type']=='level':self.key('select' if y>52 and x<48 else 'back' if y>52 else 'right' if x>=48 else 'left')
            else:self.key('back' if y>52 else 'down')
        elif y>52:self.key('select' if x<48 else 'back')
        elif y>=15:
            menu=r.objs[r.menu];count=len(menu['items'])
            offset=max(0,min(menu['selected']-1,count-3))
            selected=offset+int((y-15)//12)
            if 0<=selected<count:menu['selected']=selected;self.key('select')

    def pixels(self,order='RGBA'):
        r=self.active;r.render_menu()
        return r.presentation(self.options['color_mode']).tobytes('raw',order)

    def configure(self,key,value):
        if key not in self.options:raise ValueError('Unknown option')
        if key=='color_mode':
            if value not in ('original','light','dark'):raise ValueError('Unknown colour')
        else:value=bool(value)
        self.options[key]=value
        if key=='play_intro' and not value:self.intro=None
        if key=='muted' and value:self.audio=[]
        temporary=self.settings_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.options));temporary.replace(self.settings_file)

    def settings(self):return json.dumps(self.options)

    def save(self):
        self.runtime.save(self.state);self.last_save=time.monotonic()

    def pause(self):
        if not self.runtime.menu:self.runtime.key('back')
        self.turns.reset();self.save()

    def close(self):self.pause()
