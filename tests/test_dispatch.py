#!/usr/bin/env python3
"""
Unit test for the reciver command dispatch (stage-3 refactor).

Builds a DCSDHS without __init__ (no EPICS, no sockets, no subprocess) and
feeds dcss commands straight into the handlers, then checks every command
lands in the right queue with the same payload as the old if/elif chain.

usage: uv run python tests/test_dispatch.py
"""
import sys
import os
import queue
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from EpicsDHS import DCSDHS

QUEUE_NAMES = ['reciveQ','sendQ','epicsQ','ControlQ','DetectorQ','attenQ','workroundQ','CVLSQ']


def makedhs():
    dhs = DCSDHS.__new__(DCSDHS)
    dhs.logger = logging.getLogger('dispatch-test')
    dhs.Par = {'operationRecord': [],
               'EPICS.DetDistance.DMOV': 1,
               'EPICS.DetDistance.RBV': 250.0,
               'EPICS.DetDistance.VAL': 250.0,
               'EPICS.Energy.DMOV': 0,
               'EPICS.Energy.RBV': 12.7,
               'EPICS.Energy.VAL': 13.0}
    dhs.Q = {'Queue': {name: queue.Queue() for name in QUEUE_NAMES}}
    dhs.epicsmotors = {
        'DetDistance': {'PVname':'07a:Det:Dis','dcssname':'detector_z','GUIname':'DetDistance'},
        'Energy':      {'PVname':'07a:E','dcssname':'energy','GUIname':'Energy'},
    }
    dhs._abort_timer = 0
    return dhs


def getall(q):
    items = []
    while not q.empty():
        items.append(q.get())
    return items


def main():
    logging.basicConfig(level=logging.ERROR)

    #--- operation routing ---
    dhs = makedhs()
    dhs._cmd_start_operation(['stoh_start_operation','detector_collect_shutterless','1.2','a','b'])
    assert getall(dhs.Q['Queue']['DetectorQ']) == [('detector_collect_shutterless','1.2','a','b')]
    assert dhs.Par['operationRecord'] == [['detector_collect_shutterless','1.2','a','b']]

    dhs = makedhs()
    dhs._cmd_start_operation(['stoh_start_operation','startRasterScan','7.6','0.05','-0.2'])
    assert getall(dhs.Q['Queue']['epicsQ']) == [('startRasterScan','7.6','0.05','-0.2')]

    dhs = makedhs()
    dhs._cmd_start_operation(['stoh_start_operation','setBackLightColor','2.1','red'])
    assert getall(dhs.Q['Queue']['CVLSQ']) == [('setBackLightColor','2.1','red')]

    #accepted but not routed: recorded, no queue traffic
    dhs = makedhs()
    dhs._cmd_start_operation(['stoh_start_operation','detector_collect_image','1.3'])
    assert all(dhs.Q['Queue'][n].empty() for n in QUEUE_NAMES)
    assert dhs.Par['operationRecord'] == [['detector_collect_image','1.3']]

    #getMD2Motor: bypass with operdone reply, recorded
    dhs = makedhs()
    dhs._cmd_start_operation(['stoh_start_operation','getMD2Motor','1.1','change_mode'])
    assert getall(dhs.Q['Queue']['sendQ']) == [('operdone','getMD2Motor','1.1','change_mode')]
    assert dhs.Par['operationRecord'] == [['getMD2Motor','1.1','change_mode']]

    #unknown operation: not recorded, nothing queued
    dhs = makedhs()
    dhs._cmd_start_operation(['stoh_start_operation','noSuchOp','9.9'])
    assert all(dhs.Q['Queue'][n].empty() for n in QUEUE_NAMES)
    assert dhs.Par['operationRecord'] == []

    #--- motor move routing ---
    dhs = makedhs()
    dhs._cmd_start_motor_move(['stoh_start_motor_move','camera_zoom','5'])
    assert getall(dhs.Q['Queue']['epicsQ']) == [('stoh_start_motor_move','camera_zoom','5')]

    dhs = makedhs()
    dhs._cmd_start_motor_move(['stoh_start_motor_move','attenuation','30'])
    assert getall(dhs.Q['Queue']['attenQ']) == [('stoh_start_motor_move','attenuation','30')]

    #known motor, idle -> forwarded to epicsQ
    dhs = makedhs()
    dhs._cmd_start_motor_move(['stoh_start_motor_move','detector_z','300'])
    assert getall(dhs.Q['Queue']['epicsQ']) == [('stoh_start_motor_move','detector_z','300')]

    #known motor, moving -> warning, not forwarded
    dhs = makedhs()
    dhs._cmd_start_motor_move(['stoh_start_motor_move','energy','13000'])
    assert dhs.Q['Queue']['epicsQ'].empty()
    assert getall(dhs.Q['Queue']['sendQ']) == [('warning','Energy is already moving')]

    #unknown motor -> forwarded to epicsQ anyway (old behavior)
    dhs = makedhs()
    dhs._cmd_start_motor_move(['stoh_start_motor_move','no_such_motor','1'])
    assert getall(dhs.Q['Queue']['epicsQ']) == [('stoh_start_motor_move','no_such_motor','1')]

    #--- other commands ---
    dhs = makedhs()
    dhs._cmd_read_ion_chambers(['stoh_read_ion_chambers','1','0','i0'])
    assert getall(dhs.Q['Queue']['attenQ']) == [('stoh_read_ion_chambers','1','0','i0')]

    dhs = makedhs()
    dhs._cmd_set_shutter_state(['stoh_set_shutter_state','shutter','open'])
    assert getall(dhs.Q['Queue']['epicsQ']) == [('stoh_set_shutter_state','shutter','open')]

    dhs = makedhs()
    dhs._cmd_register_string(['stoh_register_string','currentBeamsize','currentBeamsize'])
    assert getall(dhs.Q['Queue']['DetectorQ']) == [('currentBeamsize','currentBeamsize')]

    dhs = makedhs()
    dhs._cmd_register_real_motor(['stoh_register_real_motor','detector_z','detector_z'])
    sent = getall(dhs.Q['Queue']['sendQ'])
    assert sent == ['htos_configure_device detector_z',
                    ('updatevalue','detector_z',250.0,'motor','Normal')]

    #pseudo motor energy: keV -> eV, moving -> updatevalue + startmove
    dhs = makedhs()
    dhs._cmd_register_pseudo_motor(['stoh_register_pseudo_motor','energy','standardVirtualMotor'])
    sent = getall(dhs.Q['Queue']['sendQ'])
    assert sent == [('updatevalue','energy',12700.0,'motor','Normal'),
                    ('startmove','energy',13000.0,'motor','Normal')]

    #--- abort: debounced, replays operationRecord as operdone ---
    dhs = makedhs()
    dhs.Par['operationRecord'] = [['detector_stop','1.17','']]
    dhs._cmd_abort_all(['stoh_abort_all','soft'])
    assert getall(dhs.Q['Queue']['epicsQ']) == [('stoh_abort_all','')]
    assert getall(dhs.Q['Queue']['DetectorQ']) == [('stoh_abort_all','')]
    assert getall(dhs.Q['Queue']['attenQ']) == [('stoh_abort_all','')]
    sent = getall(dhs.Q['Queue']['sendQ'])
    assert sent == [('operdone','detector_stop','1.17',''),
                    'htos_set_string_completed system_status normal {Abort!} black #d0d000']
    #second abort within 5 sec is ignored
    dhs._cmd_abort_all(['stoh_abort_all','soft'])
    assert all(dhs.Q['Queue'][n].empty() for n in QUEUE_NAMES)

    print("PASS: all dispatch routes behave like the old if/elif chain")


if __name__ == "__main__":
    main()
