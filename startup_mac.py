"""Native Cocoa progress window for first-run resource preparation."""
import logging
import threading
import objc
from AppKit import *
from Foundation import NSObject, NSMakeRect
from auto_assets import obtain


class XenziaPreparation(NSObject):
    @objc.python_method
    def run(self, data):
        self.data = data
        self.finished = False
        self.success = False
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(NSMakeRect(0, 0, 480, 185), NSWindowStyleMaskTitled | NSWindowStyleMaskClosable, NSBackingStoreBuffered, False)
        self.window.setReleasedWhenClosed_(False)
        self.window.setTitle_('Snake Xenzia')
        self.window.setDelegate_(self)
        self.label = NSTextField.wrappingLabelWithString_('正在准备游戏… / Preparing game…')
        self.label.setFrame_(NSMakeRect(22, 103, 436, 55))
        self.bar = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(22, 72, 436, 18))
        self.bar.setIndeterminate_(False); self.bar.setMinValue_(0); self.bar.setMaxValue_(100)
        self.retry = NSButton.alloc().initWithFrame_(NSMakeRect(225, 17, 110, 34))
        self.retry.setTitle_('重试 / Retry'); self.retry.setBezelStyle_(NSBezelStyleRounded)
        self.retry.setTarget_(self); self.retry.setAction_('begin:')
        cancel = NSButton.alloc().initWithFrame_(NSMakeRect(345, 17, 110, 34))
        cancel.setTitle_('取消 / Cancel'); cancel.setBezelStyle_(NSBezelStyleRounded)
        cancel.setKeyEquivalent_('\x1b'); cancel.setTarget_(self); cancel.setAction_('cancel:')
        for view in (self.label, self.bar, self.retry, cancel): self.window.contentView().addSubview_(view)
        self.window.center(); self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        self.begin_(None)
        NSApp.runModalForWindow_(self.window)
        self.finished = True
        self.window.orderOut_(None); self.window.setDelegate_(None); self.window.close()
        return self.success

    def begin_(self, sender):
        self.retry.setHidden_(True)
        self.label.setStringValue_('正在准备游戏… / Preparing game…')
        self.bar.setDoubleValue_(0)
        def work():
            try:
                obtain(self.data, lambda message, percent: self.performSelectorOnMainThread_withObject_waitUntilDone_('event:', ['progress', message, percent], False))
                self.performSelectorOnMainThread_withObject_waitUntilDone_('event:', ['ready', '', 100], False)
            except Exception:
                logging.exception('First-run preparation failed')
                self.performSelectorOnMainThread_withObject_waitUntilDone_('event:', ['error', '', 0], False)
        threading.Thread(target=work, name='PrepareGame', daemon=True).start()

    def event_(self, event):
        if self.finished: return
        kind, message, percent = event
        if kind == 'progress':
            self.label.setStringValue_(message); self.bar.setDoubleValue_(percent)
        elif kind == 'ready':
            self.success = True; self.finished = True; NSApp.stopModal()
        else:
            self.label.setStringValue_('准备失败，请检查网络后重试。\nPreparation failed. Check your connection and retry.')
            self.retry.setHidden_(False)

    def cancel_(self, sender):
        self.finished = True; NSApp.stopModal()

    def windowShouldClose_(self, window):
        self.cancel_(None)
        return False


def prepare(data):
    return XenziaPreparation.alloc().init().run(data)
