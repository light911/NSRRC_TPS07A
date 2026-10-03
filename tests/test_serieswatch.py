#!/usr/bin/env python3
"""
Unit test for following ONE filewriter series (Eiger/serieswatch.py) and the
SSX end-of-collect check built on it (Detector.check_SSX_done).

Replays the 2026-10-04 SSX auto-repeat timelines against a fake DCU (no
detector, no EPICS, no cover): the previous run's acquire->ready must not end
this run, an abort whose 'acquire' fell between two polls must still end, a run
armed and waiting for its trigger must not, a run ended by a newer collect must
leave the cover and ssx_state alone, and a download that stalls must warn.

usage: .venv/bin/python tests/test_serieswatch.py
"""
import sys
import os
import time
import queue
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Eiger.serieswatch import SeriesWatch
import Detector as DetectorModule

OWN = 'sample_0769'
PREV = 'sample_0768'


class FakeDCU:
    '''scripted DCU: script = [(from_sec, fwstate, files, detstate, name_pattern)]'''
    script = []
    t0 = 0.0

    def __init__(self, *args, **kwargs):
        pass

    def _now(self):
        elapsed = time.time() - FakeDCU.t0
        row = FakeDCU.script[0]
        for r in FakeDCU.script:
            if r[0] <= elapsed:
                row = r
        return row

    def fileWriterStatus(self, param):
        return {'value': self._now()[1]}

    def fileWriterFiles(self):
        return list(self._now()[2])

    def detectorStatus(self, param):
        return {'value': self._now()[3]}

    def fileWriterConfig(self, param):
        return {'value': self._now()[4]}


class FakeCover:
    def askforAction(self, action):
        pass


def makedet(stall=0.6):
    det = DetectorModule.Eiger2X16M.__new__(DetectorModule.Eiger2X16M)
    det.logger = logging.getLogger('serieswatch-test')
    det.Par = {'SeriesWatch': {'master_timeout': 1.0, 'download_stall_timeout': stall}}
    det.detectorip = 'fake'
    det.detectorport = 80
    det.filename = 'sample'
    det.fileindex = 769
    det.TotalFrames = 50000
    det.directory = '/data/test'
    det.sendQ = queue.Queue()
    det.cover = FakeCover()
    det.errorcount = 0
    return det


def run_check(script, stall=0.6):
    '''run check_SSX_done on a script, return what it sent to dcss'''
    FakeDCU.script = script
    FakeDCU.t0 = time.time()
    det = makedet(stall)
    det.check_SSX_done()
    sent = []
    while not det.sendQ.empty():
        sent.append(det.sendQ.get())
    return sent


def has_done(sent):
    return ('updatevalue', 'ssx_state', 'done', 'string', 'normal') in sent


def watch_only():
    '''SeriesWatch alone, one poll at a time'''
    busy = lambda: 'ready'
    idle = lambda: 'idle'
    #previous run finishing: not ours whatever the state
    w = SeriesWatch(OWN + '_master.h5')
    assert not w.update('acquire', [PREV + '_master.h5'], busy)
    assert not w.update('ready', [PREV + '_master.h5'], idle)
    #ours shows up, acquire, ready -> over
    assert not w.update('acquire', [OWN + '_master.h5'], busy)
    assert w.update('ready', [OWN + '_master.h5'], busy)
    #armed, master there, waiting for the trigger: never over while detector busy
    w = SeriesWatch(OWN + '_master.h5')
    for _ in range(50):
        assert not w.update('ready', [OWN + '_master.h5'], busy)
    #aborted, acquire missed between polls: over once the detector is idle
    assert w.update('ready', [OWN + '_master.h5'], idle)
    #detstate is only asked when it matters
    w = SeriesWatch(OWN + '_master.h5')
    def boom():
        raise AssertionError('detstate asked too early')
    assert not w.update('ready', [], boom)
    assert not w.update('acquire', [OWN + '_master.h5'], boom)
    assert w.update('ready', [OWN + '_master.h5'], boom)
    #master overdue
    w = SeriesWatch(OWN + '_master.h5')
    w.t0 -= 61
    assert w.master_overdue(60)
    w.update('ready', [OWN + '_master.h5'], busy)
    assert not w.master_overdue(60)


def main():
    logging.basicConfig(level=logging.WARNING)
    DetectorModule.DEigerClient = FakeDCU
    watch_only()

    om = OWN + '_master.h5'
    pm = PREV + '_master.h5'

    #--- 0769: previous run's tail (acquire->ready) arrives first, our master later ---
    t = time.time()
    sent = run_check([
        (0.0, 'acquire', [pm], 'ready', OWN),
        (0.3, 'ready', [pm], 'ready', OWN),          #old code ended here
        (0.6, 'acquire', [om], 'ready', OWN),
        (0.9, 'ready', [om], 'idle', OWN),           #our series really over
        (1.2, 'ready', [], 'idle', OWN),             #server took it
    ])
    took = time.time() - t
    assert took >= 1.2, f'ended on the previous run ({took:.2f}s)'
    assert has_done(sent), sent

    #--- aborted right after arm, our 'acquire' never seen ---
    sent = run_check([
        (0.0, 'ready', [], 'ready', OWN),
        (0.2, 'ready', [om], 'idle', OWN),
        (0.5, 'ready', [], 'idle', OWN),
    ])
    assert has_done(sent), sent

    #--- armed and waiting for the trigger, then a normal run ---
    t = time.time()
    sent = run_check([
        (0.0, 'ready', [om], 'ready', OWN),          #must not count as over
        (0.8, 'acquire', [om], 'acquire', OWN),
        (1.0, 'ready', [om], 'idle', OWN),
        (1.2, 'ready', [], 'idle', OWN),
    ])
    assert time.time() - t >= 1.2
    assert has_done(sent), sent

    #--- ended by the next collect (auto-repeat): no 'done', no status, no cover ---
    sent = run_check([
        (0.0, 'acquire', [om], 'acquire', OWN),
        (0.2, 'ready', [om], 'ready', 'sample_0770'),
        (0.4, 'ready', [], 'ready', 'sample_0770'),
    ])
    assert not has_done(sent), sent
    assert not any(isinstance(s, str) and 'system_status' in s for s in sent), sent

    #--- server lost the dataset: warn the user and move on ---
    sent = run_check([
        (0.0, 'acquire', [om], 'acquire', OWN),
        (0.2, 'ready', [om], 'idle', OWN),
    ], stall=0.5)
    warns = [s for s in sent if s[0] == 'warning']
    assert len(warns) == 1 and len(warns[0][1]) <= 190 and om in warns[0][1], sent
    assert has_done(sent), sent

    print("PASS: SSX end-of-collect follows only its own series")


if __name__ == "__main__":
    main()
