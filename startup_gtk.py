"""Responsive first-run resource preparation for the GTK host."""
import logging
import queue
import threading
from gi.repository import Gtk, GLib
from auto_assets import obtain


def prepare(application, data):
    window = Gtk.ApplicationWindow(application=application, title='Snake Xenzia')
    window.set_default_size(480, 170)
    window.set_resizable(False)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    content.set_border_width(22)
    label = Gtk.Label(label='正在准备游戏… / Preparing game…')
    label.set_line_wrap(True)
    bar = Gtk.ProgressBar()
    retry = Gtk.Button(label='重试 / Retry')
    content.pack_start(label, True, True, 0)
    content.pack_start(bar, False, False, 0)
    content.pack_start(retry, False, False, 0)
    window.add(content)
    events = queue.Queue()
    state = {'closed': False, 'success': False}
    loop = GLib.MainLoop()

    def worker():
        try:
            obtain(data, lambda message, percent: events.put(('progress', message, percent)))
            events.put(('ready', '', 100))
        except Exception:
            logging.exception('First-run preparation failed')
            events.put(('error', '', 0))

    def begin(*_):
        retry.hide()
        label.set_text('正在准备游戏… / Preparing game…')
        bar.set_fraction(0)
        threading.Thread(target=worker, name='PrepareGame', daemon=True).start()

    def poll():
        if state['closed']: return False
        while True:
            try: kind, message, percent = events.get_nowait()
            except queue.Empty: break
            if kind == 'progress':
                label.set_text(message)
                bar.set_fraction(percent / 100)
            elif kind == 'ready':
                state['success'] = True
                loop.quit()
            else:
                label.set_text('准备失败，请检查网络后重试。\nPreparation failed. Check your connection and retry.')
                retry.show()
        return True

    def closed(*_):
        state['closed'] = True
        loop.quit()
        return False

    retry.connect('clicked', begin)
    window.connect('delete-event', closed)
    window.show_all(); retry.hide()
    timer = GLib.timeout_add(50, poll)
    begin(); loop.run()
    state['closed'] = True
    GLib.source_remove(timer)
    window.destroy()
    return state['success']
