"""Real-time clock regressions; no game resources or JIT execution needed."""
import unittest
from unittest import mock
from runtime import NokiaRuntime, HOST, UC_ARM_REG_R0


class HostTime:
    def __init__(self):self.now=123_000_000_000
    def ns(self):return self.now
    def seconds(self):return self.now/1_000_000_000
    def advance(self,ms):self.now+=int(ms*1_000_000)


class Registers:
    def __init__(self):self.values={}
    def reg_read(self,reg):return self.values.get(reg,0)
    def reg_write(self,reg,value):self.values[reg]=value
    def mem_read(self,address,size):return b'\x04' if size==1 else bytes(size)


class ClockTests(unittest.TestCase):
    def setUp(self):
        self.host=HostTime()
        for name,value in [('perf_counter_ns',self.host.ns),('perf_counter',self.host.seconds)]:
            patch=mock.patch('runtime.time.'+name,value);patch.start();self.addCleanup(patch.stop)
        # Exercise the production frame scheduler and the original clock API
        # hook while substituting only the engine and the amount of host work.
        self.r=r=NokiaRuntime.__new__(NokiaRuntime)
        r.clock=1000;r.delay=35;r.menu=None;r.state=r.app=r.gfx=0
        r._frame_start=r._clock_origin=r._next_deadline=None
        r.u=Registers();r.graphics=None;r.tracing=False
        self.work_ms=40;self.observed=[]
        r.call=self.work

    def read_clock(self):
        self.r.host_hook(self.r.u,HOST+15*16,2,None)
        return self.r.u.reg_read(UC_ARM_REG_R0)

    def work(self,*args,**kwargs):
        self.observed.append(self.read_clock())
        self.host.advance(self.work_ms)
        self.observed.append(self.read_clock())
        r=self.r
        r._next_deadline=self.host.seconds()+r.delay/1000 if r._frame_start is not None else None

    def test_display_and_late_callback_time_are_counted(self):
        r=self.r;r.frame(realtime=True);before=r.clock
        self.host.advance(160)  # display / save work or a late host callback
        r.frame(realtime=True)
        self.assertEqual(self.observed[-2:],[before+160,before+200])
        self.assertEqual(r.clock-before,200)
        self.host.advance(50)
        self.assertEqual(r.wait_ms(),1,'expired deadline must not add another interval')
        before=r.clock;r.frame(realtime=True)
        self.assertEqual(r.clock-before,90)

    def test_fractional_milliseconds_do_not_accumulate_drift(self):
        self.work_ms=0;r=self.r;r.delay=1;r.frame(realtime=True);before=r.clock
        for _ in range(100):
            self.host.advance(1.5);r.frame(realtime=True)
        self.assertEqual(r.clock-before,150)

    def test_menu_and_resume_do_not_count_paused_time(self):
        r=self.r;r.frame(realtime=True);before=r.clock;r.menu=object()
        self.host.advance(50_000);r.frame(realtime=True)
        self.assertEqual(r.clock,before)
        self.assertIsNone(r._clock_origin);self.assertIsNone(r._next_deadline)
        r.menu=None;r.frame(realtime=True)
        self.assertEqual(r.clock-before,r.delay+self.work_ms)

    def test_logical_frames_clear_host_timing(self):
        r=self.r;r.frame(realtime=True);before=r.clock
        self.host.advance(50_000);r.frame()
        self.assertEqual(r.clock-before,r.delay)
        self.assertEqual(self.observed[-2:],[r.clock,r.clock])
        self.assertIsNone(r._clock_origin);self.assertIsNone(r._next_deadline)
        before=r.clock;r.frame(realtime=True)
        self.assertEqual(r.clock-before,r.delay+self.work_ms)

    def test_clock_api_keeps_32_bit_wraparound(self):
        r=self.r;r.clock=0xfffffff0;r.frame(realtime=True)
        self.assertEqual(self.observed[-1],r.clock&0xffffffff)


if __name__=='__main__':unittest.main()
