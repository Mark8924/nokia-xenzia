"""Win32 first-run progress window; no console or resource file picker."""
import ctypes as C
from ctypes import wintypes as W
import logging
import queue
import threading
from auto_assets import obtain


def prepare(data, u, k, WC, PROC, api):
    events = queue.Queue()
    state = {'done': False, 'success': False, 'running': False}
    controls = {}
    api(u, 'SetWindowTextW', W.BOOL, W.HWND, W.LPCWSTR)
    api(u, 'SendMessageW', C.c_ssize_t, W.HWND, W.UINT, C.c_size_t, C.c_ssize_t)
    try: u.SetProcessDpiAwarenessContext(C.c_void_p(-4))
    except Exception: pass
    try: dpi = u.GetDpiForSystem() / 96
    except Exception: dpi = 1
    common = C.WinDLL('comctl32')
    common.InitCommonControls()

    def begin():
        state['running'] = True
        u.ShowWindow(controls['retry'], 0)
        u.SetWindowTextW(controls['label'], '正在准备游戏… / Preparing game…')
        u.SendMessageW(controls['bar'], 0x402, 0, 0)
        def worker():
            try:
                obtain(data, lambda message, percent: events.put(('progress', message, percent)))
                events.put(('ready', '', 100))
            except Exception:
                logging.exception('First-run preparation failed')
                events.put(('error', '', 0))
        threading.Thread(target=worker, name='PrepareGame', daemon=True).start()

    def dispatch(hwnd, message, wparam, lparam):
        if message == 0x113:
            while True:
                try: kind, text, percent = events.get_nowait()
                except queue.Empty: break
                if kind == 'progress':
                    u.SetWindowTextW(controls['label'], text)
                    u.SendMessageW(controls['bar'], 0x402, percent, 0)
                elif kind == 'ready':
                    state['success'] = True; state['done'] = True
                    u.KillTimer(hwnd, 1); u.DestroyWindow(hwnd)
                    return 0
                else:
                    state['running'] = False
                    u.SetWindowTextW(controls['label'], '准备失败，请检查网络后重试。\nPreparation failed. Check your connection and retry.')
                    u.ShowWindow(controls['retry'], 5)
            return 0
        if message == 0x111:
            if wparam & 0xffff == 1:
                if not state['running']: begin()
            else:
                state['done'] = True; u.DestroyWindow(hwnd)
            return 0
        if message == 0x10:
            state['done'] = True; u.KillTimer(hwnd, 1); u.DestroyWindow(hwnd)
            return 0
        return u.DefWindowProcW(hwnd, message, wparam, lparam)

    callback = PROC(dispatch)
    wc = WC(); wc.proc = callback; wc.instance = k.GetModuleHandleW(None)
    wc.name = 'SnakeXenziaPreparation'; wc.background = C.c_void_p(6)
    wc.cursor = u.LoadCursorW(None, C.c_void_p(32512))
    if not u.RegisterClassW(C.byref(wc)): raise C.WinError(C.get_last_error())
    width, height = int(520 * dpi), int(240 * dpi)
    x = (u.GetSystemMetrics(0) - width) // 2
    y = (u.GetSystemMetrics(1) - height) // 2
    hwnd = u.CreateWindowExW(0, wc.name, 'Snake Xenzia', 0x00ca0000, x, y, width, height, None, None, wc.instance, None)
    if not hwnd: raise C.WinError(C.get_last_error())
    def child(kind, text, x, y, width, height, identifier=0):
        return u.CreateWindowExW(0, kind, text, 0x50000000, int(x * dpi), int(y * dpi), int(width * dpi), int(height * dpi), hwnd, C.c_void_p(identifier), wc.instance, None)
    controls['label'] = child('STATIC', '正在准备游戏… / Preparing game…', 22, 22, 465, 58)
    controls['bar'] = child('msctls_progress32', '', 22, 92, 465, 20)
    controls['retry'] = child('BUTTON', '重试 / Retry', 250, 142, 110, 34, 1)
    child('BUTTON', '取消 / Cancel', 375, 142, 110, 34, 2)
    u.SendMessageW(controls['bar'], 0x406, 0, 100)
    u.SetTimer(hwnd, 1, 50, None); u.ShowWindow(hwnd, 5); u.UpdateWindow(hwnd)
    begin()
    message = W.MSG()
    while not state['done'] and u.GetMessageW(C.byref(message), None, 0, 0) > 0:
        u.TranslateMessage(C.byref(message)); u.DispatchMessageW(C.byref(message))
    return state['success']
