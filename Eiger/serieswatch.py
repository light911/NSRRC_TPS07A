#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tell when the Eiger filewriter is done with ONE series (dataset).

Shared by the DHS (Detector.check_SSX_done) and the transfer server on epu
(TranferData_EPU_RAM_NFS_HTTP.TransferData), which both used to take "the
filewriter went acquire -> ready" as "my dataset is over".

The filewriter state belongs to the whole DCU, not to a dataset. When collects
run back to back (SSX auto-repeat) the job for run N+1 starts while the
filewriter is still finishing run N, so that acquire -> ready is run N's. On
2026-10-04 that is how 0753/0765/0769/0771 were given up with nothing
downloaded: their master files were written a moment later and stayed on the
DCU, and the DHS sent ssx_state 'done' early, which made the GUI auto-repeat
start the next run and cut the current one short.

The master file of a series is created when the detector is armed, so the
filewriter is on our series only once our master has shown up. From then on a
'ready' filewriter means our series is over - if we saw it in 'acquire' after
that. A series aborted right after arm can go through 'acquire' between two
polls; for that case 'ready' also counts once the detector itself has left
configure/ready/acquire (nothing can produce frames any more). No timing
guesses: a collect that is armed but waits long for its trigger keeps the
detector 'ready', so it is never taken as over.
"""
import time

#detector states in which a series can still produce frames
DETECTOR_BUSY = ('configure','ready','acquire')


class SeriesWatch:
    def __init__(self, masterfile):
        self.masterfile = masterfile
        self.t0 = time.time()
        self.master_seen = False
        self.acquire_seen = False

    def update(self, fwstate, files, detstate):
        '''
        feed one poll of the DCU, return True once our series is over.
        fwstate: filewriter state, files: filewriter file list,
        detstate: callable returning the detector state (only called when the
        answer depends on it, it costs one more HTTP request)
        '''
        if not self.master_seen and self.masterfile in files:
            self.master_seen = True
        if not self.master_seen:
            #whatever the filewriter is doing, it is not our series yet
            return False
        if fwstate == 'acquire':
            self.acquire_seen = True
            return False
        if fwstate != 'ready':
            return False
        if self.acquire_seen:
            return True
        return detstate() not in DETECTOR_BUSY

    def master_overdue(self, timeout):
        '''our master never showed up within timeout sec (series never started)'''
        return not self.master_seen and time.time() - self.t0 > timeout
