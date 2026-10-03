#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  3 14:26:34 2021

@author: blctl
"""
import queue
from multiprocessing import Process, Queue, Manager
from threading import Thread
import multiprocessing as mp

import logsetup,time,subprocess
from Eiger.DEiger2Client import DEigerClient
from Eiger.serieswatch import SeriesWatch
# from epics import caput,CAProcess,caget
from epics import caput,caget,ca,CAProcess,cainfo
import epics
import json,re
from pwd import getpwnam
# from DetectorCover import MOXA
from DetectorCoverV2 import MOXA
from EPICS_special import Beamsize
from ldapclient import ladpcleint
import math,requests,socket
from workround import myepics
import traceback,sys
from myeigerclient import EigerClient,setDetectorConfig,setMonitorConfig,sendDetectorCommand,detectorConfig,setFileWriterConfig
import concurrent.futures
import numpy as np
import datetime
import faulthandler,os,gc
# from TranferData_EPU_RAM_NFS_HTTP import genDatasetNames

# socket timeout (sec) for the DHS control/status DEigerClient. These calls are
# all sub-second normally (slowest single call ~1s for arm), so a stuck DCU
# request that blocks longer is a hang -> fail fast and let DEigerClient's retry
# loop reconnect, instead of blocking basesetup until the 30s watchdog kills it.
# (kept << the 30s checkandretryDetectorSetupProcess timeout; do NOT use for the
# TranferData download clients, which need the long default.)
DET_HTTP_TIMEOUT = 15

# feature flag: route detector basesetup through a long-lived "setup worker"
# forked once at CommandMon start (before any CA channel exists -> clean fork,
# empty inherited PV cache) instead of fork-per-collect. Kills the root of both
# the -11 PV-finalizer segfault and the -None fork-while-multithreaded deadlock.
# Default OFF: behaviour is identical to the old per-collect CAProcess path
# until this is flipped and the DHS restarted.
USE_SETUP_WORKER = True

def genDatasetNames(totalimage:int,nimages_per_file:int=1000,Filename:str='Test'):
    maxfileset = totalimage // nimages_per_file
    if  totalimage % nimages_per_file ==0:
        maxfileset = maxfileset -1
    maxfileset += 1
    datalists = []
    for i in range(maxfileset):
        filenum = i + 1
        dataname = f'{Filename}_data_{filenum:06}.h5'
        datalists.append(dataname)
    # print(datalist)
    return datalists
def generate_timestamp_string(fmt='%Y%m%d%H%M%S'):
    """
    根據當前時間產生數字文字

    Args:
        fmt (str): 時間格式，預設為 '%Y%m%d%H%M%S' (例如: 20250226143052)
                   可選格式:
                   - '%Y%m%d%H%M%S' -> 20250226143052
                   - '%Y%m%d%H%M%S%f' -> 20250226143052123456 (含微秒)
                   - '%Y%m%d' -> 20250226
                   - '%H%M%S' -> 143052

    Returns:
        str: 時間數字字串
    """
    return datetime.datetime.now().strftime(fmt)

class Detector():
    def __init__(self,Par,Q,coverdhs=None) :
                
        self.detectorip = ""
        self.detectorport = 80
        self.beam_center_x = 0
        self.beam_center_y = 0
        self.detector_distance = 1000
        self.omega_start = 0
        self.omega_increment = 0
        self.chi_start = 0
        self.chi_increment = 0
        self.phi_start = 0
        self.phi_increment = 0
        self.nimages = 1
        self.pixel_szie = (None, None)       
        # self.Par = {}
        self.Par = Par
        # self.sendQ = Queue()
        # self.CommandQ = Queue()
        
        self.logger = logsetup.getloger2('Detector',LOG_FILENAME='/home/blctl/Desktop/log/Detectorlog.txt',level = self.Par['Debuglevel'],bypassline=False)
        self.logger.info("init Detector logging")
        
        self.detectorip = self.Par['Detector']['ip']
        self.detectorport = self.Par['Detector']['port']
        
        # self.logger = logsetup.getloger2('DetectorDHS',level = self.Par['Debuglevel'])
        
        self.epicsQ = Q['Queue']['epicsQ']
        self.reciveQ = Q['Queue']['reciveQ']
        self.sendQ = Q['Queue']['sendQ']
        self.CommandQ = Q['Queue']['DetectorQ']
        self.state = False
        
        self.operationHandle = ""
        self.runIndex = int()
        self.filename = ""
        self.directory = ""
        self.userName = ""
        self.axisName = ""
        self.exposureTime = float()
        self.oscillationStart = float()
        self.oscillationRange =  float()
        self.distance = float()
        self.wavelength = float()
        self.detectoroffX = float()
        self.detectoroffY = float()
        self.sessionId = ""
        self.fileindex = int()
        self.TotalFrames = int() 
        self.beamsize = "" 
        self.atten = ""
        if not coverdhs:
            self.cover = MOXA()
            time.sleep(1)
            coverP = Process(target=self.cover.run,name='Cover_server')
            coverP.start()
        else:
            self.cover = coverdhs
        print('start beamsize')

        self.MoveBeamsize = Beamsize(self.cover,self.Par)
        self.ladp = ladpcleint()
        # self.logger.warning(f'Detector {self.CommandQ}')
        self.collecting = False
        self.ca = myepics(self.logger)
        self.abort = False
    def CommandMon(self) :
        self.logger.warning('Detector MON start!')
        if USE_SETUP_WORKER:
            #clean fork point: __init__ created no CA channel yet (myepics/dbpm
            #are lazy), so the parent has no libca threads here -> safe one-time
            #fork, and the worker inherits an empty PV cache.
            self._start_setup_worker()
        while True:
            command = self.CommandQ.get()
            if isinstance(command,str):
                if command == "exit" :
                    self.logger.warning('Detector DHS Get Exit Command!')
                    self.exit()
                    break
                else:
                    self.logger.debug(f'CommandMon got str command: {command}')
                    pass
                    #may be from reviceQ (DCSS),update or move some thing for it
                    
            #from reviceQ (DCSS),update or move some thing for it
            elif isinstance(command,tuple):
                self.HandleCommand(command)
            else:
                self.logger.warning('Detector DHS Get undefine Command! {command}')
      
                    
    def exit(self):
        #exit
        print('Detector class EXIT')
        #stop the long-lived setup worker (non-daemon, so it won't die on its own)
        worker = getattr(self,'setupWorker',None)
        if worker is not None and worker.is_alive():
            try:
                self.setupReqQ.put('exit')
                worker.join(2)
                if worker.is_alive():
                    worker.kill()
            except Exception as e:
                self.logger.warning(f'stop setup worker fail: {e}')
        pass
    
    def HandleCommand(self,command):
        self.logger.debug(f'HandleCommand:{command}')
        getattr(self,command[0])(command)#ex.detector_collect_image
        # try:
            # getattr(self,command[0])(command)#ex.detector_collect_image
        # except Exception as e:
        #     self.logger.warning(f'Error:{e}')
        #     self.logger.warning(f'unknow command for detector DHS: {command[0]}')
        #     self.logger.info(f'Full unknow command : {command}')


    #update each operation for diffenert detector    
    def detector_collect_image(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
   
    def detector_transfer_image(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
    def detector_oscillation_ready(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
    def detector_stop(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
    def detector_reset_run(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
    def detector_ratser_setup(self,command):
        self.logger.info(f'command: {command[1:]}')
    def stoh_abort_all(self,command):
        self.logger.info(f'command: {command[1:]}')
    def changeBeamSize(self,command):
        self.logger.info(f'command: {command[1:]}')
    def test(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
           # if ( strcmp(operationName, "detector_collect_imageHS") == 0 ||
           #      strcmp(operationName, "detector_collect_shutterless") == 0 ||
           #      strcmp(operationName, "detector_transfer_imageHS") == 0 ||
           #      strcmp(operationName, "detector_oscillation_readyHS") == 0 ||
               # strcmp(operationName, "detector_stopHS") == 0 )


    
class Eiger2X16M(Detector):
    def __init__(self,Par,Q,coverdhs=None) :
        t0= time.time()
        super().__init__(Par,Q,coverdhs)#get Detector att
        self.roi_mode = False
        self.trigger_mode ="ints"
        self.det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)
        self.det.setStreamConfig('header_detail','all')
        self.det.setStreamConfig('mode','enabled')
        self.det.setFileWriterConfig('mode','enabled')
        self.det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
        # self.det.setFileWriterConfig('format','hdf5 nexus v2024.2 nxmx') #other choich: hdf5 nexus legacy nxmx
        self.det.setFileWriterConfig('format','hdf5 nexus legacy nxmx')
        self.det.setDetectorConfig('flux_type','flux_time_integrated')# '','flux','flux_area_integrated','flux_time_integrated','flux_area_and_time_integrated'
        self.det.setDetectorConfig('instrument_name','NSRRC BEAMLINE TPS 07A')
        self.det.setDetectorConfig('source_name','NSRRC')
        # self.det.setDetectorConfig('omega_axis',[0,-1,0])
        self.det.setDetectorConfig('omega_axis',[0,1,0])
        self.det.setDetectorConfig('transformation_order',['omega'])
        self.det.setDetectorConfig('chi_increment',0)
        self.det.setDetectorConfig('phi_increment',0)
        self.x_pixels_in_detector= int(self.det.detectorConfig('x_pixels_in_detector')['value'])
        self.y_pixels_in_detector= int(self.det.detectorConfig('y_pixels_in_detector')['value'])
        self.x_pixel_size= float(self.det.detectorConfig('x_pixel_size')['value'])
        self.y_pixel_size= float(self.det.detectorConfig('y_pixel_size')['value'])
        self.ca = myepics(self.logger)
        self.dbpm1 = dbpm07a("1",self.ca)
        self.dbpm2 = dbpm07a("2",self.ca)
        self.dbpm3 = dbpm07a("3",self.ca)
        self.dbpm5 = dbpm07a("5",self.ca)
        self.dbpm6 = dbpm07a("6",self.ca)
        
        self.errorcount = 0
        #setup worker plumbing (only used when USE_SETUP_WORKER). Queues are
        #cheap; create them unconditionally so references always exist.
        self.setupReqQ = Queue()
        self.setupRespQ = Queue()
        self.setupWorker = None
        #header the worker hands back for the parent's exactly-once /tranfer POST
        self._setup_header = None
        self.logger.warning(f'Eiger2X 16M DHS init Time: {time.time()-t0}')
    def updatefilestring(self):
        t0 = time.time()
        self.logger.info('Start updatefilestring')
        totalframe = self.TotalFrames
        expctedlist =[]
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        masterfile = Filename + "_master.h5"
        expctedlist.append(masterfile)
        expctedlist.extend(genDatasetNames(self.TotalFrames,1000,Filename))
        #det = self.det
        det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        masterfile = Filename + "_master.h5"
        masterpath = f'{self.directory }/{masterfile}'
        command=["","","","","",""]
        _check = True
        currentfile = det.fileWriterFiles()
        while _check:
            if masterfile in currentfile:
                command[0] = 'updatevalue'
                command[1] = 'lastMasterCollected'
                command[2] = masterpath
                command[3] = 'string'
                command[4] = 'normal'
                self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
                _check = False
            if (time.time()-t0) > 60:
                return False
                
            time.sleep(0.2)
            currentfile = det.fileWriterFiles()

        # #wait for new file
        # while len(currentfile) != 0:
        #     currentfile.remove(masterfile)
        #     filenum = len(currentfile)
        #     if filenum == 0:
        #         #wait for data
        #         pass
        #     else:
        #         dataname = f'{Filename}_data_{filenum:06}.h5'
        #         datapath = f'{self.directory }/{dataname}'
        #         command[0] = 'updatevalue'
        #         command[1] = 'lastImageCollected'
        #         command[2] = datapath
        #         command[3] = 'string'
        #         command[4] = 'normal'
        #         self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
        #     #['empty_1_0001_data_000001.h5', 'empty_1_0001_master.h5']
        #     time.sleep(0.2)
        #     currentfile = det.fileWriterFiles()
        t0 = time.time()
        try:
            # while len(currentfile) != 0:
            while bool(set(currentfile) & set(expctedlist)):
                self.logger.info(f'wait for detector download data: file count :{set(currentfile) & set(expctedlist)}')
                time.sleep(0.2)
                currentfile = self.det.fileWriterFiles()
                # filenum = len(currentfile)-1
                # # dataname = f'{Filename}_data_{filenum:06}.h5'
                # dataname = f'{Filename}_master.h5'
                # datapath = f'{self.directory }/{dataname}'
                # command[0] = 'updatevalue'
                # command[1] = 'lastImageCollected'
                # command[2] = datapath
                # command[3] = 'string'
                # command[4] = 'normal'
                # self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
                if (time.time()-t0) > 60:
                    self.logger.info(f'wait for detector download data timeout!')
                    return False
        except Exception as e:
            self.logger.info(f'Error on monitor DCU file, error: {e}')
        self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')
            
            
        #last update
        # nimages = det.detectorConfig('nimages')['value']
        # time.sleep(0.1)
        # ntrigger = det.detectorConfig('ntrigger')['value']
        # self.logger.debug(f'{nimages=},{ntrigger=}')
        # totalframe = int(nimages) * int(ntrigger)
        time.sleep(0.5)
        lastnum = math.ceil(totalframe/1000)
        dataname = f'{Filename}_data_{lastnum:06}.h5'
        datapath = f'{self.directory }/{dataname}'
        command[0] = 'updatevalue'
        command[1] = 'lastImageCollected'
        command[2] = datapath
        command[3] = 'string'
        command[4] = 'normal'
        self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
        self.logger.info('End of monitor file for image server')


    #add detector opration here
    def currentBeamsize(self,command):
        #stoh_register_string currentBeamsize
        beamsize = self.MoveBeamsize.report_current_beamsize()
        self.sendQ.put(('updatevalue','currentBeamsize',beamsize,'string','normal'))

    def changeBeamSize(self,command):
        #just for easy put beam size here
        beamsize = command[2]
        opid =command[1]
        if len(command)>=4:
            #want to move distance too
            distance = float(command[3])
            beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(beamsize),distance,False,True,False),name='MoveBeamSize')
        else:
            distance = None
            beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(beamsize),150,False,False,False),name='MoveBeamSize')
        #arg1 = beamsize , Targetdistance, opencover,checkdis
        #set checkdis to true will make change distance to Targetdistance
        # beamsizeP = Process(target=self.MoveBeamsize.target,args=(float(beamsize),150,False,False),name='MoveBeamSize')
        # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(beamsize),150,False,False),name='MoveBeamSize')
        self.logger.debug(f'Start process for{command}') #proc ('changeBeamSize', '1.3853', '100.000000', '399.999160') 
        beamsizeP.start()
        beamsizeP.join()
        self.logger.debug(f'End process for{command}') #proc ('changeBeamSize', '1.3853', '100.000000', '399.999160') 
        #self.logger.warning(f'proc {command}') #proc ('changeBeamSize', '1.3853', '100.000000', '399.999160') 
        toDcsscommand = ('operdone',) + tuple(command)
        self.sendQ.put(toDcsscommand,timeout=1)
        #update beam size in dcss
        self.sendQ.put(('endmove','beamSize',beamsize,'normal'), block=False)
        self.sendQ.put(('updatevalue','currentBeamsize',beamsize,'string','normal'))

    def overlapBeamImage(self,command):
        overlap = command[2]
        opid =command[1]
        caput('07a-ES:MD3image:OverlapBeam',int(overlap))
        self.logger.warning(f'proc {command}')
        toDcsscommand = ('operdone',) + tuple(command)
        self.sendQ.put(toDcsscommand,timeout=1)

    def displayBeamSize(self,command):
        beamsize = command[2]
        opid =command[1]
        caput('07a-ES:Beamsize',float(beamsize))
        self.logger.warning(f'proc {command}')
        toDcsscommand = ('operdone',) + tuple(command)
        self.sendQ.put(toDcsscommand,timeout=1)

    def detector_stop(self,command):
        #check detector data is clear
        t0 = time.time()
        self.logger.info(f'close cover after got detector stop ({command}) ')
        # closecoverP = Process(target=self.cover.CloseCover,name='stop_close_cover')
        closecoverP = Process(target=self.cover.askforAction,args=('close',),name='stop_close_cover')
        closecoverP.start()
        self.logger.info(f'command: {command[1:]}')
        toDcsscommand = 'htos_set_string_completed system_status normal {Wating For Download Image} black #d0d000'
        self.sendQ.put(toDcsscommand)

        expctedlist =[]
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        masterfile = Filename + "_master.h5"
        expctedlist.append(masterfile)
        expctedlist.extend(genDatasetNames(self.TotalFrames,1000,Filename))

        currentfile = self.det.fileWriterFiles()
        self.logger.info(f'Check for detector download data: file count :{currentfile}')
        # while type(currentfile) != type(None):
        # TODO: add a timeout to this wait loop. No timeout today -> if the DCU
        #   never clears the expected files (download/transfer stuck) the whole
        #   Detector command monitor blocks here and stops serving any further
        #   command (new collect / abort), so DCSS gets no response. (seen
        #   2026-06-26 16:52-16:57: stuck ~4.5 min on test_0_0058_*.h5)
        #   Plan: derive the timeout from fileWriter + detector state plus the
        #   expected download time; on timeout, break out AND send a message to
        #   DCSS so the user knows it bailed. (remaining details TBD)
        try:
            # while len(currentfile) != 0:
            while bool(set(currentfile) & set(expctedlist)):
                self.logger.info(f'wait for detector download data: file count :{set(currentfile) & set(expctedlist)}')
                time.sleep(0.1)
                currentfile = self.det.fileWriterFiles()
        except Exception as e:
            self.logger.critical(f'Error on monitor DCU file, error{e}')
        self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')


        #now active in Download Server
        # #send to Autostra server if Frames <= 10
        # if self.TotalFrames <= 10:
        #     url = 'http://10.7.1.107:65000/job'
        #     #/data/blctl/test/test_0_matser.h5

        #     masterfile =  self.directory + "/" + self.filename + '_'  + str(self.fileindex).zfill(4) +'_master.h5'
        #     # masterfile =  f'{self.directory}/{self.filename}_{str(self.fileindex).zfill(4)}_master.h5'
        #     data = {'path':masterfile}
        #     p = Process(target=self.sendtoAutostra,args=(url,data))
        #     p.start()
        #     pass
        # # elif self.TotalFrames >= 20:
        # if self.TotalFrames >= 20:
        #     #send to auto process
        #     url = 'http://10.7.1.108:65001/job'
        #     #/data/blctl/test/test_0_matser.h5

        #     masterfile =  self.directory + "/" + self.filename + '_'  + str(self.fileindex).zfill(4) +'_master.h5'
        #     masterfile.replace('/data','/mnt/proc_buffer')
        #     # masterfile =  f'{self.directory}/{self.filename}_{str(self.fileindex).zfill(4)}_master.h5'
        #     data = {'path':masterfile}
        #     p = Process(target=self.sendtoAutostra,args=(url,data))
        #     p.start()
        #     pass


        #kill it if timeout?
        #check closecoverP state
        self.checkandretryCoverProcess(closecoverP,'close')
        # closecoverP.join(5)
        # self.logger.warning(f'closecoverP process {closecoverP.is_alive()=},{closecoverP.pid=},{closecoverP.sentinel=},{closecoverP.exitcode=}')
        # if closecoverP.exitcode== None:
        #     self.logger.warning(f'closecover P has problem kill it!')
        #     closecoverP.kill()
        #     #try to close again
        #     self.logger.warning(f'Try to close it again!(without process')
        #     self.cover.askforAction('close')
        #     # closecoverP2 = Process(target=self.cover.askforAction,args=('close',),name='stop_close_cover')
        #     # closecoverP2.start()
        #     # closecoverP2.join(5)
        #     # self.logger.warning(f'closecoverP process {closecoverP2.is_alive()=},{closecoverP2.pid=},{closecoverP2.sentinel=},{closecoverP2.exitcode=}')
        #     # if closecoverP2.exitcode == None:
        #     #     self.logger.warning(f'Still fail to closed cover')
        #     # else:
        #     #     self.logger.warning(f'OK for close Cover!!')

        toDcsscommand = 'htos_set_string_completed system_status normal Ready black #00a040'
        self.sendQ.put(toDcsscommand)
        self.logger.info(f'Done for detector stop ({command}) ')
        toDcsscommand = ('operdone',) + tuple(command)
        self.sendQ.put(toDcsscommand,timeout=1)
        
    def sendtoAutostra(self,url,data):
        response = requests.post(url , json=data)
        print(f'send to {url}')
        print(response.text)

        pass
    def detector_close_cover(self,command):
        operationHandle = command[1]
        closecoverP = Process(target=self.cover.askforAction,args=('close',),name='dcssoperation_close_cover')
        closecoverP.start()
        self.checkandretryCoverProcess(closecoverP,'close')
        # toDcsscommand = f"htos_operation_completed {command[0]} {operationHandle} normal"
        # self.logger.info(f'send command to dcss: {toDcsscommand}')
        # self.sendQ.put(toDcsscommand)
        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)
        pass
    def detector_open_cover(self,command):
        operationHandle = command[1]
        self.MoveBeamsize.opencover(True)
        self.MoveBeamsize.wait_opencover(True)
        # toDcsscommand = f"htos_operation_completed {command[0]} {operationHandle} normal"
        
        # self.sendQ.put(toDcsscommand)
        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)
        pass
    def cal_post_tri_time(self,post_tri_time,scan_range,exposure_time,start_angle,nimages):
        single_exposure_time = exposure_time / nimages
        scanspeed = scan_range/exposure_time
        addrangetimes = math.ceil(post_tri_time/single_exposure_time)
        new_start_angle =  start_angle - (scanspeed * single_exposure_time * addrangetimes)
        new_scanrange = scan_range + (scanspeed * single_exposure_time * addrangetimes)
        new_exposure_time = exposure_time + (single_exposure_time * addrangetimes)
        true_start_angle = new_start_angle + post_tri_time * scanspeed
        self.logger.warning(f'{addrangetimes=},{single_exposure_time=}')
        self.logger.warning(f'new_scanrange={new_scanrange},new_exposure_time={new_exposure_time},new_start_angle={new_start_angle},true_start_angle={true_start_angle}')
        return new_scanrange,new_exposure_time,new_start_angle,nimages,true_start_angle
        pass
    #---- setup worker (USE_SETUP_WORKER) -------------------------------------
    #per-collect self.* that basesetup/write_header read. The worker's self is a
    #snapshot from the startup fork, so these are snapshotted in the parent AFTER
    #parse+post_tri compute (e.g. oscillationStart is adjusted) and re-applied on
    #the worker's self before each basesetup. getattr default None: rasterinfo is
    #only set on raster paths and only read when raster=True.
    _SETUP_ATTRS = ('operationHandle','runIndex','filename','directory','userName',
                    'axisName','exposureTime','oscillationStart','detosc','TotalFrames',
                    'distance','wavelength','detectoroffX','detectoroffY','detmode',
                    'sessionId','fileindex','unknow','beamsize','atten','rasterinfo')

    def _start_setup_worker(self):
        #fork the long-lived setup worker. MUST be called before the parent
        #creates any CA channel: no libca threads yet -> clean fork, and the
        #inherited myepics PV cache is empty -> no orphan-PV finalizer segfault.
        #Not daemonic: basesetup spawns child Processes (sendtoAutostra etc.).
        self.setupWorker = CAProcess(target=self.setup_worker_loop,name='Detector_SetupWorker')
        self.setupWorker.start()
        self.logger.warning(f'setup worker started pid={self.setupWorker.pid}')

    def setup_worker_loop(self):
        #long-lived: run one basesetup at a time, mirroring the old per-collect
        #child. basesetup calls sys.exit(-1) on its own errors, so SystemExit is
        #caught here to keep the worker alive and report failure instead.
        #Forked clean (empty PV cache) so GC stays on; enable faulthandler once
        #(_fp lives for the whole loop, so its fd stays open) to still capture any
        #unexpected native crash.
        try:
            _fp = open('/home/blctl/Desktop/log/faulthandler.txt','a')
            _fp.write(f'\n===== setup worker start pid={os.getpid()} {datetime.datetime.now()} =====\n')
            _fp.flush()
            faulthandler.enable(file=_fp, all_threads=True)
        except Exception as e:
            self.logger.warning(f'worker faulthandler enable failed: {e}')
        self.logger.warning('setup worker loop start')
        while True:
            req = self.setupReqQ.get()
            if req == 'exit':
                self.logger.warning('setup worker got exit')
                break
            try:
                for k,v in req['attrs'].items():
                    setattr(self,k,v)
                #cleared before each run so a failed setup never returns a stale
                #header from a previous collect. basesetup sets it once the header
                #is built (worker mode does NOT POST /tranfer itself).
                self._setup_header = None
                self.basesetup(*req['args'])
                #hand the header back so the PARENT POSTs /tranfer exactly once:
                #retries are parent-controlled -> no duplicate; only on success
                #-> no phantom job. see _run_basesetup / _notify_download_server.
                self.setupRespQ.put({'id':req['id'],'ok':True,'err':None,'header':getattr(self,'_setup_header',None)})
            except SystemExit as e:
                self.setupRespQ.put({'id':req['id'],'ok':False,'err':f'basesetup sys.exit {e.code}','header':None})
            except Exception as e:
                self.logger.critical(f'setup worker basesetup error: {e}')
                self.setupRespQ.put({'id':req['id'],'ok':False,'err':str(e),'header':None})

    def _send_setup_request(self,args):
        reqid = time.time()
        attrs = {a:getattr(self,a,None) for a in self._SETUP_ATTRS}
        self.setupReqQ.put({'id':reqid,'args':args,'attrs':attrs})
        return reqid

    def _wait_setup_result(self,reqid,args,timeout=30):
        #mirror checkandretryDetectorSetupProcess: wait for the worker's result;
        #on timeout (worker hung) kill+respawn and retry once; on a reported
        #failure the worker is still alive so just resend once.
        #returns (ok, header): header is the write_header appendix the parent
        #POSTs to /tranfer exactly once on success (None on any failure).
        attempt = 1
        while attempt <= 2:
            try:
                resp = self.setupRespQ.get(timeout=timeout)
            except queue.Empty:
                self.logger.critical(f'setup worker timeout ({timeout}s), kill+respawn (attempt {attempt})')
                try:
                    self.setupWorker.kill()
                except Exception as e:
                    self.logger.warning(f'kill setup worker fail: {e}')
                self._start_setup_worker()
                attempt += 1
                if attempt > 2:
                    return False, None
                reqid = self._send_setup_request(args)
                continue
            if resp.get('id') != reqid:
                self.logger.warning('setup resp id mismatch, ignoring stale result')
                continue
            if resp.get('ok'):
                self.logger.info('setup worker OK')
                return True, resp.get('header')
            self.logger.critical(f"setup worker reported fail: {resp.get('err')} (attempt {attempt})")
            attempt += 1
            if attempt > 2:
                return False, None
            reqid = self._send_setup_request(args)
            continue
        return False, None

    def _run_basesetup(self,args,beamsize_args,timeout):
        #shared setup launch for every collect type. Worker mode: hand basesetup
        #to the long-lived worker and run setup_beamsize in the parent in parallel
        #(same DCU||motor overlap as before), then wait for the result. Old mode:
        #per-collect CAProcess + checkandretry. beamsize_args = this collect type's
        #setup_beamsize_cover_distance args. self.* the worker needs must already
        #be set on self before calling (snapshotted in _send_setup_request).
        if USE_SETUP_WORKER:
            reqid = self._send_setup_request(args)
            self.logger.debug('start to setup_beamsize_cover_distance')
            self.setup_beamsize_cover_distance(*beamsize_args)
            self.logger.debug('End to setup_beamsize_cover_distance')
            #ok only if the worker actually finished basesetup (armed). callers
            #MUST honor False and abort: on failure the detector is not armed.
            #the /tranfer notify is sent HERE (parent), exactly once, only on
            #success -> no duplicate on worker retry, no phantom job on failure.
            ok, header = self._wait_setup_result(reqid,args,timeout)
            if ok and header:
                self._notify_download_server(header)
            return ok
        else:
            #CAProcess: child uses CA, must not inherit the parent's dead libca state
            detectorsetupP = CAProcess(target=self.basesetup,args=args,name='Detector_Setup')
            detectorsetupP.start()
            self.logger.debug('start to setup_beamsize_cover_distance')
            self.setup_beamsize_cover_distance(*beamsize_args)
            self.logger.debug('End to setup_beamsize_cover_distance')
            self.checkandretryDetectorSetupProcess(detectorsetupP,args,timeout)
            #old path has no success signal; preserve prior behavior (proceed)
            return True

    def _setup_failed(self,command):
        #detector setup did not complete (worker timed out twice, e.g. MD3 stuck):
        #the detector is not armed and the download/transfer server was never told
        #about this dataset. do NOT proceed as if it succeeded. surface it in DCSS
        #(red status) and close the operation so DCSS unblocks instead of hanging.
        self.logger.critical(f'detector setup FAILED, abort collect {command[0]} handle={self.operationHandle}')
        self.sendQ.put('htos_set_string_completed system_status normal {Detector setup FAILED} white #d00000')
        self.sendQ.put(('operdone',command[0],self.operationHandle))

    def _notify_download_server(self,header):
        #tell the download/transfer server (10.7.1.108:64444) a dataset is coming.
        #runs in the PARENT: use a Thread, NOT a Process — the parent holds live CA
        #channels and forking here risks the orphan-PV finalizer segfault (see the
        #reason the setup worker is forked early). short POST timeout keeps
        #CommandMon responsive if the server is down; a lost notify is non-fatal.
        def _post():
            try:
                url = 'http://10.7.1.108:64444/tranfer'
                r = requests.post(url,json=header,timeout=5)
                self.logger.info(f'notify download server: {r.status_code} {r.text}')
            except Exception as e:
                self.logger.warning(f'Notify Download server has error {e}')
        Thread(target=_post,daemon=True,name='NotifyDownload').start()

    def _get_uid_gid(self,username):
        #same rule as write_header: blctl is a local account, real users are in LDAP
        if username == 'blctl':
            pw = getpwnam(username)
            return pw[2],pw[3]
        uidNumber,gidNumber,passwd = self.ladp.getuserinfo(username)
        return uidNumber,gidNumber

    def save_sample_snapshot(self,timeout=None):
        #save a picture of the sample as it is RIGHT NOW, but only if MD3 is
        #still in center mode (CurrentPhase = Centring). that is the only phase
        #where the backlight is on and the sample is in the camera view, so a
        #collect starting from there is the last chance to record what the user
        #is about to shoot. any other phase -> do nothing, return False.
        #
        #the DHS runs as blctl and cannot hand a file to the data owner, and the
        #image lives on the MD3image DHS, so the work is done by the transfer
        #server on epu (root): we POST path/filename/uid/gid, it grabs the JPEG,
        #writes it, chowns+chmods it and answers OK. blocking on purpose (the
        #caller wants the photo taken before the sample is moved/exposed) but
        #ALWAYS bounded by the timeout: a snapshot is nice-to-have and must never
        #delay or fail a data collection, so every failure is logged and returns
        #False and the caller simply carries on.
        #returns True only when the server confirmed the file was written.
        t0 = time.time()
        try:
            cfg = self.Par['SampleSnapshot']
            md3phase = self.ca.caget(self.Par['collect']['md3modePV'],format=str)
            #caget returns None when the PV does not answer -> not Centring -> skip
            if str(md3phase).strip() != cfg['phase']:
                self.logger.info(f'sample snapshot: MD3 phase is {md3phase}, not {cfg["phase"]}, skip')
                return False
            if timeout is None:
                timeout = cfg['timeout']
            try:
                uid,gid = self._get_uid_gid(self.userName)
            except Exception as e:
                #unknown user: still save the picture, the server just leaves it root-owned
                self.logger.warning(f'sample snapshot: can not get uid/gid of {self.userName}: {e}')
                uid,gid = None,None
            #same base name as the dataset (filename_0001.h5 -> filename_0001.jpg)
            #so the photo sits next to the data it belongs to
            snapname = self.filename + "_" + str(self.fileindex).zfill(4) + '.jpg'
            job = {'directory':self.directory,
                   'filename':snapname,
                   'user':self.userName,
                   'uid':uid,
                   'gid':gid,
                   'source':cfg['source'],
                   'md3phase':str(md3phase).strip(),
                   }
            self.logger.info(f'sample snapshot: ask {cfg["url"]} for {self.directory}/{snapname}')
            r = requests.post(cfg['url'],json=job,timeout=(3,timeout))
            ok = (r.status_code == 200 and r.text.startswith('OK'))
            if ok:
                self.logger.info(f'sample snapshot: {r.text} take {time.time()-t0} sec')
            else:
                self.logger.warning(f'sample snapshot: server said {r.status_code} {r.text}')
            return ok
        except Exception as e:
            self.logger.warning(f'sample snapshot failed (collect continues): {e}, take {time.time()-t0} sec')
            return False

    def detector_collect_shutterless(self,command):
    #    ('detector_collect_shutterless', '1.24', '1', 'test_1', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000009', '1.0', '10', '750.000060', '0.976226127404', '0.000231', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '1', '10', '50.000000', '0.0')
    #['stoh_start_operation', 'detector_collect_shutterless', '1.2', '0', 'test_0', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000000', '1.0', '1', '750.000080', '0.976226127404', '0.000071', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '3', '1', '50.000000', '0.0']
    # command: ('1.2', '0', 'test_0', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000009', '1.0', '1', '750.000240', '0.976226127404', '0.000187', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '9', '1', '50.000000', '0.0
    #['stoh_start_operation', 'detector_collect_shutterless', '1.16', '1', 'test_1', '/data/blctl/test', 'blctl', 'gonio_phi', '0.10', '45.000018', '0.30', '10', '799.999800', '0.976226127404', '0.000187', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '1', '10', '50.000000', '0.0']
    # set operationHandle [start_waitable_operation detector_collect_shutterless \
    #                  $darkCacheNumber \
    #                  $filename \
    #                  $directory \
    #                  $userName \
    #                  $motor \
    #                  $time \
    #                  $startAngle \
    #                  $delta \
    #                  $totalFrames \
    #                  [set $gMotorDistance] \
    #                  $wavelength \
    #                  [set $gMotorHorz] \
    #                  [set $gMotorVert] \
    #                  0 \detector mode
    #                  0 \
    #                  $sessionId \
    #                  [lindex $args 0] \
    #                  $totalFrames \
    #                  $beam_size \
    #                  $attn]\
    #
        t0 = time.time()
        
        self.operationHandle = command[1]
        self.runIndex = int(command[2])
        self.filename = command[3]
        self.directory = command[4]
        self.userName = command[5]
        self.axisName = command[6]
        self.exposureTime = float(command[7])
        self.oscillationStart = float(command[8])
        
        self.detosc =  float(command[9])  
        # self.detosc =  0
        self.TotalFrames = int(command[10]) #1
        self.distance = float(command[11])
        self.wavelength = float(command[12])
        self.detectoroffX = float(command[13])
        self.detectoroffY = float(command[14])
        self.detmode = int(command[15])
        self.sessionId = command[17]
        self.fileindex = int(command[18])
        self.unknow = int(command[19]) #1
        self.beamsize = command[20] # 50
        self.atten = command[21] #0
        # print("##########")
        # print(self.detmode)
        # print("##########")
        #  sscanf(commandBuffer.textInBuffe
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
        #still in center mode when the collect arrived? then this is the last
        #moment the sample is lit and in view -> record it before anything moves.
        #no-op (and no cost) in every other MD3 phase, and never fatal: see
        #save_sample_snapshot. must stay AFTER the command parsing above (it
        #needs directory/filename/fileindex/userName) and BEFORE the setup below.
        #DISABLED 2026-08-12, not tested yet (users on the beamline): DCSS very
        #likely switches Centring -> DataCollection before it sends this command,
        #so from here the snapshot would almost never fire. Plan is a dedicated
        #DCSS operation that asks for it while the sample is still centered;
        #re-enable this line (or drop it) once that is settled.
        # self.save_sample_snapshot()
        self.ca.caput('07a-ES:timing:nimage',self.TotalFrames,format=int)
        scan_range =  self.TotalFrames * self.detosc
        post_tri_timePV = self.Par['collect']['post_tri_timePV']
        shutter_delayPV = self.Par['collect']['shutter_delayPV']
        detector_delayPV = self.Par['collect']['detector_delayPV']
        post_tri_time = self.ca.caget(post_tri_timePV,format=float)
        if post_tri_time == 0 :
            self.ca.caput(shutter_delayPV,0,format=float)
            self.ca.caput(detector_delayPV,0,format=float)
            pass
        elif post_tri_time > 0:
            _oscillationTime = self.TotalFrames * self.exposureTime
            new_scanrange,new_exposure_time,new_start_angle,nimages,true_start_angle = self.cal_post_tri_time(post_tri_time,scan_range,_oscillationTime,self.oscillationStart,self.TotalFrames)
            delaytimeus = int(post_tri_time * 1e6)
            self.oscillationStart = true_start_angle
            if delaytimeus <= 10000:#delay short than 10ms may have problem for shutter tri early, set shutter to 0(fastest)
                self.logger.warning(f'post_tri_time is too short, can not tri early, set to 0')
                # delaytimeus = 0
                shutterdelayus = 0
            else:
                shutterdelayus = int((post_tri_time -0.01)* 1e6)#shutter tri early 10ms
            self.logger.warning(f'{delaytimeus=},{shutterdelayus=}')
            self.ca.caput(shutter_delayPV,shutterdelayus,format=int)
            self.ca.caput(detector_delayPV,delaytimeus,format=int)
            pass

        
        # htos_note changing_detector_mode
        toDcsscommand = ('htos_note','changing_detector_mode')
        if self.runIndex==0:
            collectype= 'test image'
        elif self.runIndex<40:
            collectype= 'Normal dataset'
        else:
            collectype= 'Normal dataset'
        self.sendQ.put(toDcsscommand)
        #beam size and distance has moved by dcss
        # _oscillationTime,_filename = self.basesetup(movebeasize=False)
        # raster=False,roi=False,beamwithdis=False,movebeasize=True
        #detmode 0 = one energy 16M
        #detmode 1 = one energy ROI (4M)
        #detmode 2 = two energy 16M
        #detmode 3 = two energy ROI (4M)
        if self.detmode == 0 or self.detmode == 2:
            roi = False
            pass
        elif self.detmode == 1 or self.detmode == 3:
            roi = True
            pass
        args=(False,roi,False,False,None,collectype,)
        #watchdog (60s) must stay > basesetup's internal worst case
        #(waitMD3Ready 15s + write_header join 30s); was 30s and equal to the
        #MD3 wait, which killed the worker before it could notify /tranfer.
        if not self._run_basesetup(args,(False,False,False,False,False),60):
            self._setup_failed(command)
            return
        _oscillationTime = self.TotalFrames * self.exposureTime
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        _filename = Filename + '.h5'
        
        


        #make sure cover is opend
        self.MoveBeamsize.wait_opencover(True)
        # handle injection
        safeTimeInj= self.Par['collect']['safeTimeInj']
        TimeToNextInjPV = self.Par['collect']['TimeToNextInjPV']
        if collectype == 'test image':
            pass
        elif safeTimeInj== 0:
            #do notthing
            pass
        elif safeTimeInj >0 :
            #wait until injection
            toDcsscommand = 'htos_set_string_completed system_status normal {Wating For injection} black #d0d000'
            self.sendQ.put(toDcsscommand)
            while True:
                TimeToNextInj = self.ca.caget(TimeToNextInjPV,format=float)
                if _oscillationTime > 240 - safeTimeInj:
                    self.logger.info(f'Data collect time :{_oscillationTime} > 240 - {safeTimeInj} pass for collect, ther is no way to not hit injection')
                    break
                elif TimeToNextInj > safeTimeInj+_oscillationTime:
                    self.logger.info(f'TimeToNextInj:{TimeToNextInj} > {safeTimeInj}+{_oscillationTime} pass for collect')
                    break
            pass
        elif safeTimeInj <0 :
            #want to hit injection
            toDcsscommand = 'htos_set_string_completed system_status normal {Wating For injection} black #d0d000'
            self.sendQ.put(toDcsscommand)
            while True:
                TimeToNextInj = self.ca.caget(TimeToNextInjPV,format=float)
                if TimeToNextInj < abs(safeTimeInj):
                    self.logger.info(f'TimeToNextInj:{TimeToNextInj} < {abs(safeTimeInj)} pass for collect')
                    break
            
            pass

        toDcsscommand = ('operupdate',command[0],self.operationHandle,'start_oscillation','shutter',str(_oscillationTime),_filename)
        self.sendQ.put(toDcsscommand)
        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.sendQ.put(toDcsscommand)
        self.logger.warning(f'detector_collect_shutterless take {time.time()-t0} sec')
        self.logger.debug('start to updatefilestring check')
        monP = CAProcess(target=self.updatefilestring,name='Monfile')
        monP.start()
        # command = ('operdone',) + command
        # self.sendQ.put(command)
    def SSXCollect(self,command):
        self.logger.info(f'Got SSXCollect OP :{command}')
        # #htos_set_string_completed strname status arguments
        # echo = "htos_set_string_completed " + str(command[1]) + " " + str(command[4]) + " " + str(command[2])
        # echo = "htos_set_string_completed " + "tps_current" + " " + "normal" + " 500"
        # command 0:command 1:motorname 2:position 3:type 4:state
        toDcsscommand = ('updatevalue','ssx_state','setup','string','normal')
        self.sendQ.put(toDcsscommand)
        # parlist = []
        # filename = self.SSX_Prefix.text() 2
        # directory = self.SSX_Directory.text() 3
        # userName = self.user  4
        # exposureTime = self.SSX_Time.value()  5
        # oscillationStart = 0  6
        # detosc = 0    7
        # TotalFrames = self.SSX_NumberFrames.value()   8
        # distance = self.SSX_Distance.value()  9
        # wavelength = 1/self.bluiceData['motor']['energy']['pos']*12398    10
        # detectoroffX = self.bluiceData['motor']['detector_vert']['pos']   11
        # detectoroffY = self.bluiceData['motor']['detector_horz']['pos']   12
        # fileindex = 0 13
        # detmode = self.SSX_DetectorMode.currentIndex()    14
        # beamsize = 1  15
        # atten = self.SSX_Attenuation.value()  16
        # LaserInitialState = self.SSX_LaserInitialState.currentIndex() 17
        # SSX_LassrTimeArray_1 = self.SSX_LassrTimeArray_1.value()  18
        # SSX_LassrTimeArray_2 = self.SSX_LassrTimeArray_2.value()  19
        # SSX_PeakSearchAlgorithm = self.SSX_PeakSearchAlgorithm.currentIndex() 20
        # SSX_PeakSearch_threshold = self.SSX_PeakSearch_threshold.value()  21
        # SSX_PeakSearch_minsnr = self.SSX_PeakSearch_minsnr.value()    22
        # SSX_PeakSearch_min_pix_count = self.SSX_PeakSearch_min_pix_count.value()  23
        # SSX_PeakSearch_max_pix_count = self.SSX_PeakSearch_max_pix_count.value()  24
        # SSX_PeakSearch_local_bg_radius = self.SSX_PeakSearch_local_bg_radius.value()  25
        # SSX_PeakSearch_min_res = self.SSX_PeakSearch_min_res.value()  26
        # SSX_PeakSearch_max_res = self.SSX_PeakSearch_max_res.value()  27
        # SSX_PeakSearch_min_snr_biggest_pix = self.SSX_PeakSearch_min_snr_biggest_pix.value()  28
        # SSX_PeakSearch_min_snr_peak_pix = self.SSX_PeakSearch_min_snr_peak_pix.value()    29
        # SSX_PeakSearch_min_sig = self.SSX_PeakSearch_min_sig.value()  30
        # runIndex = int(105) #105 for SSX collect ,view1 =101 view2 =102   31
        # SSXautoreapeat = int(self.SSX_AutoRepeat.isChecked())  32
        self.operationHandle = command[1]
        self.filename = command[2]
        self.directory = command[3]
        self.userName = command[4]
        self.exposureTime = float(command[5])
        self.oscillationStart = float(command[6])
        self.detosc =  float(command[7])  
        self.TotalFrames = int(command[8])
        self.distance = float(command[9])
        self.wavelength = float(command[10])
        self.detectoroffX = float(command[11])
        self.detectoroffY = float(command[12])
        self.fileindex = int(command[13])
        self.detmode = int(command[14])
        self.beamsize = command[15]
        self.atten = command[16]
        LaserInitialState = int(command[17])
        SSX_LassrTimeArray_1 = float(command[18])
        SSX_LassrTimeArray_2 = float(command[19])
        SSX_PeakSearchAlgorithm = int(command[20])
        SSX_PeakSearch_threshold = int(command[21])
        SSX_PeakSearch_minsnr = float(command[22])
        SSX_PeakSearch_min_pix_count = float(command[23])
        SSX_PeakSearch_max_pix_count = float(command[24])
        SSX_PeakSearch_local_bg_radius = float(command[25])
        SSX_PeakSearch_min_res = float(command[26])
        SSX_PeakSearch_max_res = float(command[27])
        SSX_PeakSearch_min_snr_biggest_pix = float(command[28])
        SSX_PeakSearch_min_snr_peak_pix = float(command[29])
        SSX_PeakSearch_min_sig = float(command[30])
        self.runIndex = command[31]#for raster =101 or102 105 fir SSX
        self.SSXautoreapeat = int(command[32]) #we desicde not use it for now, control by GUI
        #setup MD3 mode
        #move md3 phase inadvance,we will wait at detectorsetup again
        # md3phase = float(self.ca.caget(self.Par['collect']['md3modePV']))
        md3phase = self.ca.caget(self.Par['collect']['md3modePV'],format=str)
        #strip(): the old CLI caget returned 'DataCollection\n', pyepics is clean
        if str(md3phase).strip() != 'DataCollection':
            self.ca.caput(self.Par['collect']['md3modePV'],2)
            time.sleep(0.1)
            pass
        #setup timeing
        post_tri_timePV = self.Par['collect']['post_tri_timePV']
        shutter_delayPV = self.Par['collect']['shutter_delayPV']
        detector_delayPV = self.Par['collect']['detector_delayPV']
        SSXtriggerPV = self.Par['collect']['SSXtriggerPV']
        SSXtrigerwidthPV = self.Par['collect']['SSXtrigerwidthPV']
        laser_init_statePV = self.Par['collect']['laser_init_statePV']
        laser_timing_arrayPV = self.Par['collect']['laser_timing_arrayPV']
        self.ca.caput(post_tri_timePV,0)
        self.ca.caput(shutter_delayPV,0)
        self.ca.caput(detector_delayPV,10000)#TODO detector tri delay 10ms(10000) for SSX, but laser should delay 10ms as will.
        if self.TotalFrames == 0:
            self.TotalFrames = 10800000
        _oscillationTime = self.TotalFrames * self.exposureTime * 1e3 + 10#sec to ms
        
        self.ca.caput(SSXtrigerwidthPV,_oscillationTime)
        self.ca.caput(laser_init_statePV,LaserInitialState)
        #modify SSX Laser timing to compensate the delay of shutter and detector
        if LaserInitialState == 1:
            #initial state is on, add 10ms at SSX_LassrTimeArray_1 to tri laser with detector
            self.ca.caput(laser_init_statePV,0)#change to 0 to tri laser at the beginning of collect, but add 10ms delay for laser to tri with detector and shutter
            SSX_LassrTimeArray_2 = SSX_LassrTimeArray_2 - 0.01
            laser_timing_array = [0.01*1000000,SSX_LassrTimeArray_1*1000000,SSX_LassrTimeArray_2*1000000,
                                0,0,0,0,0,0,0]#sec to usec
        else:
            #initial state is off, tri laser at the beginning of collect, but add 10ms delay for laser to tri with detector and shutter
            #TODO
            laser_timing_array = [SSX_LassrTimeArray_1*1000000,SSX_LassrTimeArray_2*1000000,
                                0,0,0,0,0,0,0,0]#sec to usec
        
        #07a:beamline:timing:laser:pulse_timing is a long waveform (time_long,
        #count 10), so every element has to be an int. The sec->usec maths above
        #produces floats, and pyepics then refuses the whole put with "'float'
        #object cannot be interpreted as an integer" -- myepics.caput logs that and
        #returns None, so the laser timing silently keeps its previous value while
        #the collect carries on. Truncation is exact here: the times arrive as
        #seconds with 2 decimals, and int() matches round() over that whole range.
        laser_timing_array = [int(v) for v in laser_timing_array]
        self.logger.info(f'SSX Laser timing array: {laser_timing_array}')
        self.ca.caput(laser_timing_arrayPV,laser_timing_array)
        #setup peaksearch server
        
        #setup and arm detector
        # htos_note changing_detector_mode
        toDcsscommand = ('htos_note','changing_detector_mode')
        self.sendQ.put(toDcsscommand)
        collectype= 'SSXCollect'
        #detmode 0 = one energy 16M
        #detmode 1 = one energy ROI (4M)
        #detmode 2 = Highspeed 16M
        #detmode 3 = Highspeed (4M)
        if self.detmode == 0 or self.detmode == 2:
            roi = False
            pass
        elif self.detmode == 1 or self.detmode == 3:
            roi = True
            pass
        # raster,roi=False,beamwithdis,movebeasize=True,detconn=None,collectype='test image')
        args=(False,roi,False,False,None,collectype,)

        #SSX: no cryojet (fixed target at room temperature, movecryojet=False).
        #movebeasize=False so bypassslit never reaches MoveBeamsize.target here;
        #it is kept True to match the other SSX paths.
        #movedistance=True: SSX is started straight from the GUI, not through
        #DCSS moveMotorsForRun, so nobody else moves detector_z for it.
        if not self._run_basesetup(args,(False,False,False,False,True,False,True),60):
            self._setup_failed(command)
            return
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        _filename = Filename + '.h5'



        #make sure cover is opend
        self.MoveBeamsize.wait_opencover(True)
        


        # tri peak search?

        #before we open shutter make sure mode again
        md3phase = self.ca.caget(self.Par['collect']['md3modePV'],format=str)
        #strip(): the old CLI caget returned 'DataCollection\n', pyepics is clean
        if str(md3phase).strip() != 'DataCollection':
            self.logger.critical(f'SSX Collect Fail: MD3 not in DataCollection mode')
            pass
        else:
            #trigger collect
            toDcsscommand = ('updatevalue','ssx_state','collecting','string','normal')
            self.sendQ.put(toDcsscommand)
            self.ca.caput(SSXtriggerPV,1)
            # finish data collect if detector back to idle
            monP = CAProcess(target=self.check_SSX_done,name='check_SSX_done')
            monP.start()

        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)
        pass
    def SSXStopCollect(self,command):
        self.operationHandle = command[1]
        self.logger.info(f'Got SSXStopCollect OP :{command}')
        toDcsscommand = ('updatevalue','ssx_state','stop','string','normal')
        self.sendQ.put(toDcsscommand)
        #stop detector frist
        self.logger.info(f'try to reset detector')
        state = self.det.detectorStatus('state')
        self.abort = True
        if state == 'idle':
            pass
        elif state == 'acquire':
            self.det.sendDetectorCommand('disarm')
        elif state == 'ready':
            self.det.sendDetectorCommand('disarm')
        else:
            self.det.sendDetectorCommand('abort')
        self.logger.info(f'try to close detector cover')
        closecoverP = Process(target=self.cover.askforAction,args=('close',),name='abort_close_cover')
        closecoverP.start()
        #force stop trigger
        SSXtrigerwidthPV = self.Par['collect']['SSXtrigerwidthPV']
        # SSXtriggerPV = self.Par['collect']['SSXtriggerPV']
        # self.ca.caput(SSXtriggerPV,1)#usless
        self.ca.caput(SSXtrigerwidthPV,1)
        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)
        pass

    def check_SSX_done(self):
        #runs in its own CAProcess forked right after the trigger, so self.filename/
        #fileindex/TotalFrames are this run's even after the GUI auto-repeat has
        #started the next run in the parent. several of these can be alive at once,
        #all looking at the same DCU.
        det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)
        watchPar = self.Par.get('SeriesWatch',{})
        master_timeout = watchPar.get('master_timeout',60)
        stall_timeout = watchPar.get('download_stall_timeout',300)
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        masterfile = Filename + "_master.h5"
        #wait for the end of OUR series. a bare acquire->ready may be the previous
        #run finishing (see Eiger/serieswatch.py)
        series = SeriesWatch(masterfile)
        while True:
            try:
                state = det.fileWriterStatus('state')['value']
                currentfile = det.fileWriterFiles()
                if series.update(state,currentfile,lambda: det.detectorStatus('state')['value']):
                    break
            except Exception as e:
                self.logger.warning(f'check_SSX_done: cannot read DCU state for {Filename}, retry: {e}')
                time.sleep(0.5)
            if series.master_overdue(master_timeout):
                self.logger.warning(f'{masterfile} never showed up on the DCU in {master_timeout} sec, take {Filename} as aborted')
                break
            time.sleep(0.1)
        #a newer collect sets name_pattern before it arms. if that happened this run
        #was ended by the next one (auto-repeat): the cover and the status belong to
        #the new run now, and a 'done' from here would make the GUI auto-repeat
        #start yet another run on top of it.
        try:
            superseded = det.fileWriterConfig('name_pattern')['value'] != Filename
        except Exception as e:
            self.logger.warning(f'check_SSX_done: cannot read name_pattern ({e}), take {Filename} as the current run')
            superseded = False
        #collect id done
        command=["","","","","",""]
        totalframe = self.TotalFrames
        lastnum = math.ceil(totalframe/1000)
        dataname = f'{Filename}_data_{lastnum:06}.h5'
        datapath = f'{self.directory }/{dataname}'
        command[0] = 'updatevalue'
        command[1] = 'lastImageCollected'
        command[2] = datapath
        command[3] = 'string'
        command[4] = 'normal'
        self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
        #send detector stop?
        #check detector data is clear

        if superseded:
            self.logger.warning(f'{Filename} was ended by a newer collect, leave cover and ssx_state to it')
            closecoverP = None
        else:
            self.logger.info(f'close cover after got detector stop ({command}) ')
            # closecoverP = Process(target=self.cover.CloseCover,name='stop_close_cover')
            closecoverP = Process(target=self.cover.askforAction,args=('close',),name='stop_close_cover')
            closecoverP.start()

            toDcsscommand = 'htos_set_string_completed system_status normal {Wating For Download Image} black #d0d000'
            self.sendQ.put(toDcsscommand)

        expctedlist =[]
        expctedlist.append(masterfile)
        expctedlist.extend(genDatasetNames(self.TotalFrames,1000,Filename))

        #wait for the transfer server to take our files off the DCU. bounded by
        #progress, not by total time: a long run downloads for minutes, but nothing
        #leaving the DCU for stall_timeout means the server lost this dataset.
        remain = None
        tprogress = time.time()
        while True:
            try:
                currentfile = det.fileWriterFiles()
            except Exception as e:
                self.logger.warning(f'check_SSX_done: cannot read DCU files for {Filename}, retry: {e}')
                currentfile = None
            if currentfile is not None:
                _remain = set(currentfile) & set(expctedlist)
                if not _remain:
                    self.logger.info(f'All data of {Filename} is downloaded: file on DCU :{currentfile}')
                    break
                if _remain != remain:
                    self.logger.info(f'wait for detector download data: {sorted(_remain)}')
                    remain = _remain
                    tprogress = time.time()
            if time.time() - tprogress > stall_timeout:
                warn = f'SSX {Filename}: nothing downloaded for {stall_timeout}s, still on DCU: {",".join(sorted(remain or []))[:80]}. Check TranferData on epu.'
                self.logger.critical(warn)
                #htos_note: dcss reads it into char[201]
                self.sendQ.put(('warning',warn[:190]))
                break
            time.sleep(0.1)
        if superseded:
            self.logger.info(f'Done for check_SSX_done of superseded {Filename} ({command}) ')
            return
        self.checkandretryCoverProcess(closecoverP,'close')
        toDcsscommand = ('updatevalue','ssx_state','done','string','normal')
        self.sendQ.put(toDcsscommand)
        toDcsscommand = 'htos_set_string_completed system_status normal Ready black #00a040'
        self.sendQ.put(toDcsscommand)
        self.logger.info(f'Done for check_SSX_done ({command}) ')

    def mutiPosCollect(self,command):
        # ans =  [runIndex,filename,directory,userName,axisName,exposureTime,oscillationStart,detosc,TotalFrames,distance,wavelength,detectoroffX,detectoroffY,sessionId,fileindex,unknow,beamsize,atten]
        t0=time.time()
        det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)
        self.operationHandle = command[1]
        self.runIndex = command[2]# will be 0
        self.filename = command[3]
        self.directory = command[4]
        self.userName = command[5]
        self.axisName = command[6]
        self.exposureTime = float(command[7])
        self.oscillationStart = float(command[8])
        
        self.detosc =  float(command[9])
        self.TotalFrames = int(command[10]) #1
        self.distance = float(command[11])
        self.wavelength = float(command[12])
        self.detectoroffX = float(command[13])
        self.detectoroffY = float(command[14])
        

        self.sessionId = command[15]
        self.fileindex = int(command[16])# will be 1
        self.unknow = int(command[17]) #1
        self.beamsize = command[18] # 50
        self.atten = command[19] #0
        # htos_note changing_detector_mode
        # toDcsscommand = ('htos_note','changing_detector_mode')
        if self.exposureTime > 200:
            warningTXT = f"epicsedhs say expouse time ={self.exposureTime} > 200 sec?"
            self.sendQ.put(("warning",warningTXT))
            toDcsscommand = ('operdone',command[0],self.operationHandle)
            self.logger.info(f'send command to dcss: {toDcsscommand}')
            self.sendQ.put(toDcsscommand)
            return
        toDcsscommand = 'htos_set_string_completed system_status normal {Changing detector mode and Beam Size} black #d0d000'
        self.sendQ.put(toDcsscommand)
        self.abort =False
        self.roi=False
        # _oscillationTime,_filename = self.basesetup(raster=False,roi=self.roi,beamwithdis=True)
        # _filename = _filename + '.h5'
        collectype='MutiPostion'
        # _oscillationTime,_filename = self.basesetup(movebeasize=False)
        # raster=False,roi=False,beamwithdis=False,movebeasize=True
        args=(False,self.roi,True,True,None,collectype,)
        
        if not self._run_basesetup(args,(False,self.roi,True,True,False),60):#need to move beam size take longer time
            self._setup_failed(command)
            return
        _oscillationTime = self.TotalFrames * self.exposureTime
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        _filename = Filename + '.h5'
        
        
        self.logger.warning(f'mutiPosCollect detector setup take {time.time()-t0} sec')
        #make sure cover is opend
        self.MoveBeamsize.wait_opencover(True)
        
        self.logger.warning(f"Setup for MD3 scan")
        #tri md3
        #List of scan parameter values, comma separated: Int,double,double,double,intframe_number (int):
        #frame ID just for logging purpose. It is different from ScanNumberOfFrames which is used in the detector multi-triggering inside scan_range.
        #start_angle (double): angle (deg) at which the shutter opens and omega speed is stable 
        #scan_range (double): omega relative move angle (deg) before closing the shutter
        #exposure_time (double): exposure time (sec) to control shutter command
        #number_of_passes (int): number of moves forward and reverse between start angle and end angle.
        scan_range = float(self.TotalFrames*self.detosc)
        exposure_time = float(self.exposureTime*self.TotalFrames)
        start_angle = float(self.oscillationStart)
        fileindex = int(self.fileindex)
        number_of_passes = int(1)
        nimages = int(self.TotalFrames)
        Timeout = 30 + exposure_time
        
        
        LastTaskInfoPV = self.Par['collect']['LastTaskInfoPV']
        PVcollect = self.Par['collect']['start_oscillationPV']
        NumberOfFramesPV = self.Par['collect']['NumberOfFramesPV']
        
        value = [fileindex,start_angle,scan_range,exposure_time,number_of_passes]
        self.logger.warning(f"MD3 Expouse Scan Start,with start_angle:{start_angle},scan_range:{scan_range},exposure_time:{exposure_time}, number_of_passes:{number_of_passes}  ")
        toDcsscommand = 'htos_set_string_completed system_status normal {Wait for MD3 Scaning} black #d0d000'
        self.sendQ.put(toDcsscommand)
        timeStart=time.time()
        
        
        MD3state = self.waitMD3Ready()
        caput(NumberOfFramesPV,1)# control by detector
        #save current pos for collect
        sendPV = self.Par['collect']['saveCentringPositionsPV']
        caput(sendPV,'__EMPTY__')
        if MD3state:
            
            state = caput(PVcollect,value)
        else:
            state = -1
        

        if state != 1:
            self.logger.critical(f"Caput {PVcollect} value {value} Fail!")
        
        self.logger.debug('start to updatefilestring check')
        monP = CAProcess(target=self.updatefilestring,name='Monfile')
        monP.start()

        time.sleep(0.5)
        Task = self.ca.caget(LastTaskInfoPV)#TODO check
        # print(Task)
        t0 = time.time()
        while str(Task[6]) == "null":
            time.sleep(0.2)
            Task = caget(LastTaskInfoPV)
            # print(Task[6])
            t1 = time.time()
            if (t1-t0) > Timeout:
                 self.logger.critical(f"Wait for MD3 scan job Timeout{Timeout},Current state = {Task})")
                 break
             
        # ans = 
        # sendQ.put(('operdone',))
        runtime = time.time() - timeStart
        self.logger.warning(f"MD3 Expouse Scan Done,take {runtime},with PV put state={state},Result ID = {Task[6]}")
        # self.logger.warning(f"fileindex:{fileindex},nimages:{nimages},Par:{Par}")
        # closecoverP = Process(target=self.cover.CloseCover,name='mutiPosCollect_close_cover')

        # #notify dcss we collect done,later we will download file,but dcss can to something
        # toDcsscommand = f"htos_operation_completed {command[0]} {self.operationHandle} normal"
        # self.logger.info(f'send command to dcss: {toDcsscommand}')
        # self.sendQ.put(toDcsscommand)

        # toDcsscommand = ('operdone',command[0],self.operationHandle)
        # self.logger.info(f'send command to dcss: {toDcsscommand}')
        # self.sendQ.put(toDcsscommand)

        #now not close cover in end of collect, control by bluice2
        # closecoverP = Process(target=self.cover.askforAction,args=('close',),name='mutiPosCollect_close_cover')
        # closecoverP.start()
        
        ############################
        # toDcsscommand = 'htos_set_string_completed system_status normal {Wating For Download Image} black #d0d000'
        # self.sendQ.put(toDcsscommand)

        # expctedlist =[]
        # Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        # masterfile = Filename + "_master.h5"
        # expctedlist.append(masterfile)
        # expctedlist.extend(genDatasetNames(self.TotalFrames,1000,Filename))
        
        # currentfile = det.fileWriterFiles()
        # self.logger.info(f'Check for detector download data: current file :{currentfile}')
        # self.logger.info(f'Check for detector download data: expcted file :{expctedlist}')
        # try:
        #     # while len(currentfile) != 0:
        #     while bool(set(currentfile) & set(expctedlist)):
        #         self.logger.info(f'wait for detector download data: file :{set(currentfile) & set(expctedlist)}')
        #         time.sleep(0.1)
        #         currentfile = self.det.fileWriterFiles()
        # except Exception as e:
        #     self.logger.critical(f'Error on monitor DCU file, error{e}')
        # self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')
        ###########################
        # try :
        #     if len(currentfile) != 0:
        #         check = True
        #     else:
        #         check = False
        # except:
        #         check = True
        
        # while check and not self.abort:
        #     self.logger.info(f'wait for detector download data: file count :{currentfile}')
        #     time.sleep(0.2)
        #     currentfile = det.fileWriterFiles()
        #     try :
        #         if len(currentfile) != 0:
        #             check = True
        #         else:
        #             check = False
        #     except:
        #             check = True


        # self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')
        
        #now not close cover in end of collect, control by bluice2
        # self.logger.info(f'Check cover is cloesd,current code is {closecoverP.exitcode}')
        # self.checkandretryCoverProcess(closecoverP,'close')

        # closecoverP.join(5)
        # self.logger.warning(f'closecoverP process {closecoverP.is_alive()=},{closecoverP.pid=},{closecoverP.sentinel=},{closecoverP.exitcode=}')
        # if closecoverP.exitcode== None:
        #     self.logger.warning(f'closecover P has problem kill it!')
        #     closecoverP.kill()
        #     #try to close again
        #     self.logger.warning(f'Try to close it again!')
        #     self.cover.askforAction('close')
        #     # closecoverP2 = Process(target=self.cover.askforAction,args=('close',),name='mutiPosCollect_close_cover')
        #     # closecoverP2.start()
        #     # closecoverP2.join(5)
        #     # self.logger.warning(f'closecoverP process {closecoverP2.is_alive()=},{closecoverP2.pid=},{closecoverP2.sentinel=},{closecoverP2.exitcode=}')
        #     # if closecoverP2.exitcode == None:
        #     #     self.logger.warning(f'Still fail to closed cover')
        #     # else:
        #     #     self.logger.warning(f'OK for close Cover!!')

        # htos_set_string_completed
        

        #for update bluiceUI
        # toDcsscommand = f"htos_operation_completed detector_stop {self.operationHandle} normal"
        # toDcsscommand = f"htos_set_string_completed detector_status Ready normal"
        
        toDcsscommand = f'htos_set_string_completed system_status normal Ready black #00a040'
        self.sendQ.put(toDcsscommand)

        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)

    def detector_ratser_setup(self,command):
    #    ('detector_ratser_setup', '1.24', '1', 'test_1', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000009', '1.0', '10', '750.000060', '0.976226127404', '0.000231', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '1', '10', '50.000000', '0.0')
    #['stoh_start_operation', 'detector_collect_shutterless', '1.2', '0', 'test_0', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000000', '1.0', '1', '750.000080', '0.976226127404', '0.000071', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '3', '1', '50.000000', '0.0']
    # command: ('1.2', '0', 'test_0', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000009', '1.0', '1', '750.000240', '0.976226127404', '0.000187', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '9', '1', '50.000000', '0.0
    #['stoh_start_operation', 'detector_collect_shutterless', '1.16', '1', 'test_1', '/data/blctl/test', 'blctl', 'gonio_phi', '0.10', '45.000018', '0.30', '10', '799.999800', '0.976226127404', '0.000187', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '1', '10', '50.000000', '0.0']
    #('detector_ratser_setup', '16.0', '101', 'RasterScanview1', '/data/blctl/20211019_07A/', 'blctl', 'gonio_phi', '0.01', '119.999996', '0.0', '36', '599.9839', '7.874087724013369e-05', '0.0', '0.948142', 'no', '0', '1', '50.0', '0.0', '1', '6', '6', '')
    # set operationHandle [start_waitable_operation detector_collect_shutterless \
    #                  $darkCacheNumber \
    #                  $filename \
    #                  $directory \
    #                  $userName \
    #                  $motor \
    #                  $time \
    #                  $startAngle \
    #                  $delta \
    #                  $totalFrames \
    #                  [set $gMotorDistance] \
    #                  $wavelength \
    #                  [set $gMotorHorz] \
    #                  [set $gMotorVert] \
    #                  0 \
    #                  0 \
    #                  $sessionId \
    #                  [lindex $args 0] \
    #                  $totalFrames \
    #                 $beam_size $attn]
    # return [runIndex,filename,directory,userName,axisName,exposureTime,oscillationStart,detosc,TotalFrames,distance,wavelength
    # ,detectoroffX,detectoroffY,sessionId,fileindex,unknow,beamsize,atten,roi,numofX,numofY,uid,gid,gridsizex,gridsizey]
        t0=time.time()
        self.operationHandle = command[1]
        self.runIndex = command[2]#for raster =101 or102
        self.filename = command[3]
        self.directory = command[4]
        self.userName = command[5]
        self.axisName = command[6]
        self.exposureTime = float(command[7])
        self.oscillationStart = float(command[8])
        
        self.detosc =  float(command[9])
        self.TotalFrames = int(command[10]) #1
        self.distance = float(command[11])
        self.wavelength = float(command[12])
        self.detectoroffX = float(command[13])
        self.detectoroffY = float(command[14])
        

        self.sessionId = command[15]
        self.fileindex = int(command[16])
        self.unknow = int(command[17]) #1
        #for raster scan we using smaller beam size 
        #20211029 change now take par from operation
        # tempbeamsize = float(command[18])
        # table={100:90,90:80,80:70,70:60,60:50,50:40,40:30,30:20,20:10,10:5,5:1}

        # self.beamsize = table[tempbeamsize]
        self.beamsize = command[18]
        self.atten = command[19] #0
        if command[20] == "1":
            self.roi = True
        else:
            self.roi = False
        self.rasterinfo={}
        self.rasterinfo['x']= int(command[21])
        self.rasterinfo['y']= int(command[22])
        self.rasterinfo['gridsizex'] = float(command[25])
        self.rasterinfo['gridsizey'] = float(command[26])
        #  sscanf(commandBuffer.textInBuffe
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
        #move md3 phase inadvance
        # md3phase = float(self.ca.caget(self.Par['collect']['md3modePV']))
        md3phase = self.ca.caget(self.Par['collect']['md3modePV'],format=str)
        #strip(): the old CLI caget returned 'DataCollection\n', pyepics is clean
        if str(md3phase).strip() != 'DataCollection':
            self.ca.caput(self.Par['collect']['md3modePV'],2)
            time.sleep(0.1)
            pass

        # htos_note changing_detector_mode
        toDcsscommand = ('htos_note','changing_detector_mode')
        self.sendQ.put(toDcsscommand)
        collectype= 'Raster'
        # _oscillationTime,_filename = self.basesetup(raster=True,roi=self.roi,beamwithdis=True)
        # _filename = _filename + '.h5'
        # raster=False,roi=False,beamwithdis=False,movebeasize=True
        args=(True,self.roi,True,True,None,collectype,)
        
        #raster: raster=True -> basesetup reads self.rasterinfo (set earlier at
        #~line 1243, so it is captured by _send_setup_request)
        if not self._run_basesetup(args,(True,self.roi,True,True,False),120):#need to move beam size take longer time
            self._setup_failed(command)
            return


        self.logger.debug('start to updatefilestring check')
        monP = CAProcess(target=self.updatefilestring,name='Monfile')
        monP.start()
        #make sure cover is opend
        self.MoveBeamsize.wait_opencover(True)
        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)
        self.logger.warning(f'detector_ratser_setup take {time.time()-t0} sec')
        
    def stoh_abort_all(self,command):    
        # if self.cover.show_current_state=="Closed":
        #     pass
        # else:
        #     closecoverP = Process(target=self.cover.CloseCover,name='abort_close_cover')
        #     closecoverP.start()
        
        self.logger.info(f'try to reset detector')
        state = self.det.detectorStatus('state')
        self.abort = True
        if state == 'idle':
            pass
        elif state == 'acquire':
            self.det.sendDetectorCommand('disarm')
        elif state == 'ready':
            self.det.sendDetectorCommand('disarm')
        else:
            self.det.sendDetectorCommand('abort')
        self.logger.info(f'try to close detector cover')
        closecoverP = Process(target=self.cover.askforAction,args=('close',),name='abort_close_cover')
        closecoverP.start()
    
    def basesetup_old(self,raster=False,roi=False,beamwithdis=False,movebeasize=True,detconn=None):
        try:
            t0 = time.time()
            # ca.clear_cache()
            # if detconn == None:
            #     pass
            # else:
            #     #newconnect
            #     # self.det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)
            #     self.det = detconn
            #make a new conn,avoid mutiprocess problem
            # det = DEigerClient(self.detectorip,self.detectorport,verbose=True)
            det = EigerClient(self.detectorip,self.detectorport)
            self.logger.debug(f'TotalFrames =  {self.TotalFrames},exposureTime = {self.exposureTime} ')
            self.logger.debug(f'oscillationStart =  {self.oscillationStart},framewidth = {self.detosc}')
            self.logger.debug(f'directory =  {self.directory},filename = {self.filename},fileindex={self.fileindex}')
            self.logger.debug(f'distance =  {self.distance},wavelength = {self.wavelength},detectoroffX={self.detectoroffX},detectoroffY={self.detectoroffY},beamsize={self.beamsize},atten={self.atten}')
            self.logger.debug(f'Unknow =  {self.unknow}')
            framerate = 1 / self.exposureTime 
    
            # self.det.setDetectorConfig('count_time',1-0.0000001) 
            # self.det.setDetectorConfig('frame_time',1)
            

            #move outside by setup_beamsize_cover_distance
            # #move cryjet in
            # askCryojetIn(self.Par['robot']['host'],self.Par['robot']['commandprot'])

            # # old open cover, now move to beamsize
            # # opcoverP = Process(target=self.cover.OpenCover,name='open_cover')
            # # opcoverP.start()
            
            # if raster or beamwithdis:
            #     # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,True,),name='MoveBeamSize')
            #     # beamsizeP.start()
            #     self.logger.debug(f'{raster=},{beamwithdis=}')
            #     self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,True)
            #     self.sendQ.put(('endmove','beamSize',str(self.beamsize),'normal'), block=False)
            #     self.sendQ.put(('updatevalue','currentBeamsize',str(self.beamsize),'string','normal'))
            #     framerate = 1 / self.exposureTime 
            # else:
            #     #normal shutterless collect
            #     #check frame rate?
            #     # framerate = self.TotalFrames / self.exposureTime
            #     # beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            #     # beamsizeP = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            #     # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            #     # beamsizeP.start()
            #     framerate = 1 / self.exposureTime
            #     if movebeasize:
            #         self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,False)
            #         self.sendQ.put(('endmove','beamSize',str(self.beamsize),'normal'), block=False)
            #         self.sendQ.put(('updatevalue','currentBeamsize',str(self.beamsize),'string','normal'))
            #     else:
            #         #but we still need open cover
            #         self.MoveBeamsize.opencover(True)
            #         pass

            self.logger.debug(f'setting Detector')
            Filename = self.filename + "_" + str(self.fileindex).zfill(4)
            TotalTime = self.TotalFrames * self.exposureTime
            que = queue.Queue()
            write_headerP = Thread(target=self.write_header,args=(raster,Filename,que,),name='write_header')
            # que = Queue()
            # write_headerP = Process(target=self.write_header,args=(raster,Filename,que,),name='write_header')
            write_headerP.start()
            # framerate = 75 #debug 
            #detector mode
            # roi = True
            self.logger.debug(f'ask setting ROI and threshold')    
            if roi:
                if det.detectorConfig('roi_mode')['value'] == "disabled":
                    self.logger.debug(f'set detector roi_mode from disabled to 4M')
                    det.setDetectorConfig('roi_mode','4M')
                framerate = 500 #debug #force to no using 2nd energy
                if framerate > 280:
                    self.logger.debug(f'framerate =  {framerate},disable two threshold')
                    if det.detectorConfig('threshold/difference/mode')['value'] == "enabled":
                        self.logger.debug(f'update detector threshold/difference/ to disabled')
                        det.setDetectorConfig('threshold/difference/mode','disabled')
                    if det.detectorConfig('threshold/2/mode')['value'] == "enabled":
                        self.logger.debug(f'update detector threshold/2/mode to disabled')
                        det.setDetectorConfig('threshold/2/mode','disabled')
                else:
                    self.logger.debug(f'framerate =  {framerate},enable two threshold')
                    if det.detectorConfig('threshold/2/mode')['value'] == "disabled":
                        det.setDetectorConfig('threshold/2/mode','enabled')
                    if det.detectorConfig('threshold/difference/mode')['value'] == "disabled":    
                        det.setDetectorConfig('threshold/difference/mode','enabled')
                
            else:
                framerate = 75 #force to no using 2nd energy
                if det.detectorConfig('roi_mode')['value'] == "4M":
                    self.logger.debug(f'set detector roi_mode from 4M to disabled')
                    det.setDetectorConfig('roi_mode','disabled')
                
                if framerate > 70:
                    self.logger.debug(f'framerate =  {framerate},disable two threshold')
                    if det.detectorConfig('threshold/difference/mode')['value'] == "enabled":
                        self.logger.debug(f'update detector threshold/difference/ to disabled')
                        det.setDetectorConfig('threshold/difference/mode','disabled')
                    if det.detectorConfig('threshold/2/mode')['value'] == "enabled":
                        self.logger.debug(f'update detector threshold/2/mode to disabled')
                        det.setDetectorConfig('threshold/2/mode','disabled')
                else:
                    self.logger.debug(f'framerate =  {framerate},enable two threshold')
                    if det.detectorConfig('threshold/2/mode')['value'] == "disabled":
                        det.setDetectorConfig('threshold/2/mode','enabled')
                    if det.detectorConfig('threshold/difference/mode')['value'] == "disabled":    
                        det.setDetectorConfig('threshold/difference/mode','enabled')
                # self.det.setDetectorConfig('threshold/2/mode','enabled')
                # self.det.setDetectorConfig('threshold/difference/mode','enabled')
            self.logger.debug(f'done for setting ROI and threshold')    
            self.logger.debug(f'ask setting some basic info to detector')    
            
            
            # detOmega = self.oscillationRange / self.TotalFrames
            
            dethor = float(self.ca.caget(self.Par['collect']['dethorPV']))
            # self.logger.warning(f'ask setting some basic info to detector_3') 
            detver = float(self.ca.caget(self.Par['collect']['detverPV']))
            # self.logger.warning(f'ask setting some basic info to detector_4') 
            beamx = int(self.x_pixels_in_detector/2 - dethor/self.x_pixel_size/1e3)
            
            beamy = int(self.y_pixels_in_detector/2 + detver/self.y_pixel_size/1e3)
            # self.logger.debug(f'beam x center =  {self.x_pixels_in_detector/2},dethor at {}dethor')
            # self.logger.warning(f'ask setting some basic info to detector_5') 
            
            det.setDetectorConfig('beam_center_x',beamx)
            # self.logger.warning(f'ask setting some basic info to detector_6') 
            det.setDetectorConfig('beam_center_y',beamy)
            # self.logger.warning(f'ask setting some basic info to detector_7') 
            
            det.setDetectorConfig('detector_distance',self.distance/1000)
            # self.logger.warning(f'ask setting some basic info to detector_8') 
            det.setDetectorConfig('omega_start',self.oscillationStart)
            # self.logger.warning(f'ask setting some basic info to detector_9') 
            det.setDetectorConfig('omega_increment',self.detosc)
            # self.logger.warning(f'ask setting some basic info to detector_10') 
            try:
                chi = float(self.ca.caget(self.Par['collect']['chiPV']))
                phi = float(self.ca.caget(self.Par['collect']['phiPV']))
            except:
                chi = 0
                phi = 0
            # self.logger.warning(f'ask setting some basic info to detector_11') 
            det.setDetectorConfig('chi_start',0)
            det.setDetectorConfig('chi_increment',chi)
            det.setDetectorConfig('phi_start',phi)
            det.setDetectorConfig('phi_increment',0)
            self.logger.debug(f'done for setting some basic info to detector')    

            # self.logger.debug(f'ask for asking beamline info')
            # #get user info
            # #user blctl not in ladp database
            # if self.userName=='blctl':
            #     uidNumber = getpwnam(self.userName)[2]
            #     gidNumber = getpwnam(self.userName)[3]
            # else:
            #     uidNumber,gidNumber,passwd = self.ladp.getuserinfo(self.userName)

            # Ebeamcurrent = caget(self.Par['collect']['EbeamPV'])
            # gap = caget(self.Par['collect']['gapPV'])
            # dbpm1flux = caget(self.Par['collect']['DBPM1PV'])
            # dbpm2flux = caget(self.Par['collect']['DBPM2PV'])
            # dbpm3flux = caget(self.Par['collect']['DBPM3PV'])
            # dbpm5flux = caget(self.Par['collect']['DBPM5PV'])
            # dbpm6flux = caget(self.Par['collect']['DBPM6PV'])
            # sampleflux = caget(self.Par['collect']['samplefluxPV'])
            # kappa = caget(self.Par['collect']['kappaPV'])
            # #tps 07a only
            # self.dbpm1.update()
            # self.dbpm2.update()
            # self.dbpm3.update()
            # self.dbpm5.update()
            # self.dbpm6.update()
            
            
            
            
            # header_appendix ={}
            # header_appendix['user'] = self.userName
            # header_appendix['directory'] = self.directory
            # header_appendix['runIndex'] = self.runIndex
            # header_appendix['beamsize'] = self.beamsize
            # header_appendix['atten'] = self.atten
            # header_appendix['fileindex'] = self.fileindex
            # header_appendix['filename'] = Filename
            # # header_appendix['uid'] = getpwnam(self.userName)[2]
            # # header_appendix['gid'] = getpwnam(self.userName)[3]
            # header_appendix['uid'] = uidNumber
            # header_appendix['gid'] = gidNumber
            # header_appendix['Ebeamcurrent'] = Ebeamcurrent
            # header_appendix['gap'] = gap
            # header_appendix['dbpm1flux'] = dbpm1flux
            # header_appendix['dbpm2flux'] = dbpm2flux
            # header_appendix['dbpm3flux'] = dbpm3flux
            # header_appendix['dbpm5flux'] = dbpm5flux
            # header_appendix['dbpm6flux'] = dbpm6flux
            # header_appendix['sampleflux'] = sampleflux
            # header_appendix['kappa'] = kappa
            # for name,value in self.dbpm1.getneedvalue():
            #     header_appendix[name] = value
            # for name,value in self.dbpm2.getneedvalue():
            #     header_appendix[name] = value
            # for name,value in self.dbpm3.getneedvalue():
            #     header_appendix[name] = value
            # for name,value in self.dbpm5.getneedvalue():
            #     header_appendix[name] = value
            # for name,value in self.dbpm6.getneedvalue():
            #     header_appendix[name] = value
            # self.logger.debug(f'done for asking beamline info')
            self.logger.debug(f'ask for setting trigger_mode/count time')
            if raster:
                # header_appendix['raster_X']=self.rasterinfo['x']
                # header_appendix['raster_Y']=self.rasterinfo['y']
                # header_appendix['grid_width']=self.rasterinfo['gridsizex']
                # header_appendix['grid_height']=self.rasterinfo['gridsizey']
                
                # self.det.setDetectorConfig('trigger_mode','exte')##temp
                det.setDetectorConfig('trigger_mode','exts')##temp
                # self.det.setDetectorConfig('nimages',1)
                # self.det.setDetectorConfig('ntrigger',self.TotalFrames)
                det.setDetectorConfig('nimages',int(self.rasterinfo['y']))
                det.setDetectorConfig('ntrigger',int(self.rasterinfo['x']))
                # self.det.setDetectorConfig('count_time',self.exposureTime-0.0000001) 
                # self.det.setDetectorConfig('frame_time',self.exposureTime)
                det.setDetectorConfig('count_time',self.exposureTime) 
                det.setDetectorConfig('frame_time',self.exposureTime)
            else:
                det.setDetectorConfig('trigger_mode','exts')##temp
                det.setDetectorConfig('nimages',self.TotalFrames)
                det.setDetectorConfig('ntrigger',1)
                # self.det.setDetectorConfig('count_time',self.exposureTime-0.0000001) 
                det.setDetectorConfig('count_time',self.exposureTime) 
                det.setDetectorConfig('frame_time',self.exposureTime)
            self.logger.debug(f'done for setting trigger_mode/count time')
            # text = json.dumps(header_appendix)
            # self.det.setStreamConfig('header_appendix',text)
            
            # if self.runIndex == 0:
            #     self.det.setFileWriterConfig('nimages_per_file',0)
            # else :
            #     self.det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
            #0.1sec setup time move to init
            # det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
            
            # print('Detector Energy',self.Par['EPICS']['Energy']['VAL']*1000)
            Energy = float(self.ca.caget(self.Par['collect']['EnergyPV']))*1000
            self.logger.debug(f'ask photon_energy')
            ans = det.detectorConfig('photon_energy')
            detEn= float(ans['value'])
            self.logger.debug(f'Current detector energy={detEn}')
            # print(f'Current Energy:{Energy}, Current Detector setting energy={detEn}')
            if (abs(Energy-detEn)>10):#change if more than 10v
                det.setDetectorConfig('photon_energy',Energy)
                self.logger.info(f'Detector origin energy={detEn},now set to {Energy}')
            
        # print("Setting frame time",cam.setDetectorConfig('frame_time',exptime),exptime)
        

            
            
            
            self.logger.debug(f'Filename =  {Filename}')
            
            det.setMonitorConfig('mode',"enabled")
            det.setFileWriterConfig('mode','enabled')
            det.setFileWriterConfig('name_pattern',Filename)
            self.Par['Detector']['Filename'] = Filename
            self.Par['Detector']['Fileindex'] = self.fileindex
            self.Par['Detector']['nimages'] = self.TotalFrames
            # self.logger.warning(f'TYPE:{type(self.Par)}')
            
            #update to md3
            #wait md3 ready
            self.waitMD3Ready(30)
            self.logger.info(f'update to MD3 NumberOfFramesPV {self.TotalFrames}')
            NumberOfFramesPV = self.Par['collect']['NumberOfFramesPV']
            # caput(NumberOfFramesPV,self.TotalFrames)
            self.ca.caput(NumberOfFramesPV,self.TotalFrames)
            write_headerP.join()
            text = que.get()
            det.setStreamConfig('header_appendix',text)
            # det.setStreamConfig('image_appendix',text)

            self.logger.info(f'arm detector')
            det.sendDetectorCommand('arm')
            self.logger.info(f'done for arm detector')
            # self.det.sendDetectorCommand('trigger')
            
            #check cryjet in?

            self.logDetInfo(det)
            # self.cover.wait_for_state(wait='open',timeout=3)
            # self.logger.info(f'Check beamsize and cover is done')
            # # self.logger.info(f'beamsize process {beamsizeP.is_alive()=},{beamsizeP.pid=},{beamsizeP.sentinel=},{beamsizeP.exitcode=}')
            # self.logger.info(f'beamsize process {beamsizeP.is_alive()=}')

            # beamsizeP.join()
            # beamsizeP.join(5)
            # # currentbeamsize=self.MoveBeamsize.report_current_beamsize()
            # # current_dis = self.ca.caget('07a:Det:Dis')
            # # diff_dis = abs(current_dis-self.distance)
            # checkneed = False
            # if beamsizeP.exitcode == None:
            #     #just wait longer time
            #     checkneed = True
            #     # #check beamsize /cover/distance if in position not need to join so long time
            #     # detDMOV = self.ca.caget('07a:Det:Y.DMOV',int,False)
            #     # md3yDMOV = self.ca.caget('07a:MD3:Y.DMOV',int,False)
            #     # if self.cover.Par['Coverstate'] == True and detDMOV == 1 and md3yDMOV == 1:
            #     #     #in postion

            #     #     self.logger.warning(f'cover/beamsize/distance are in position,but BeamsizeP not ready, just kill it(should not happen)')
            #     #     beamsizeP.kill()
            #     # else:
            #     #     #need wait more
            #     #     checkneed = True
            #     #     pass
            
            # else:
            #     self.logger.info(f'beamsizeP done!')

            # self.logger.warning(f'{checkneed=}')
            # if checkneed:   
            #     beamsizeP.join(60)#1um beam to 100um take 39sec,100um to 1um semm loger
            #     if beamsizeP.exitcode == None:
            #         self.logger.warning(f'beamsize P has problem kill it!')
            #         self.logger.warning(f'beamsize process {beamsizeP.is_alive()=},{beamsizeP.pid=},{beamsizeP.sentinel=},{beamsizeP.exitcode=}')
            #         beamsizeP.kill()
            #         self.logger.warning(f'Try to go beamsize again!this time without new process')

            #         if raster or beamwithdis:
            #             self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,True)    
            #         else:
                        
            #             self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,False)
                        
            #     else:
            #         self.logger.info(f'beamsizeP done!after wait')
                        

            t1 = time.time()
            # we wait baseset can be a process, so take it outide here
            # self.logger.debug('start to updatefilestring check')
            # monP = Process(target=self.updatefilestring,name='Monfile')
            # monP.start()
            self.logger.info(f'setup time = {t1-t0},Detector energy={Energy}')
            return TotalTime,Filename
        except Exception as e:
            error_class = e.__class__.__name__ #取得錯誤類型
            detail = e.args[0] #取得詳細內容
            cl, exc, tb = sys.exc_info() #取得Call Stack
            lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
            fileName = lastCallStack[0] #取得發生的檔案名稱
            lineNum = lastCallStack[1] #取得發生的行號
            funcName = lastCallStack[2] #取得發生的函數名稱
            errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)
            self.logger.warning(f'Setup detector has error {errMsg}')
            sys.exit(-1)#for mutiprocess
            
    def basesetup(self,raster=False,roi=False,beamwithdis=False,movebeasize=True,detconn=None,collectype='test image'):
        #mutithread version
        #Old per-collect fork path only: that child is short-lived and forks from
        #a CA-active parent, so it hits the -11 PV-finalizer-during-GC segfault
        #(cyclic GC runs PV.__del__ -> ca.clear_subscription from a no-CA-context
        #thread). gc.disable() stops it; faulthandler dumps any crash. The setup
        #worker is forked once from a clean state with an empty PV cache -> no
        #orphan PVs, so GC must stay ON (long-lived process) and faulthandler is
        #enabled once in setup_worker_loop instead.
        if not USE_SETUP_WORKER:
            gc.disable()
            try:
                _fault_fp = open('/home/blctl/Desktop/log/faulthandler.txt','a')
                _fault_fp.write(f'\n===== basesetup pid={os.getpid()} {datetime.datetime.now()} '
                                f'file={self.filename}_{str(self.fileindex).zfill(4)} =====\n')
                _fault_fp.flush()
                faulthandler.enable(file=_fault_fp, all_threads=True)
            except Exception as _fe:
                self.logger.warning(f'faulthandler setup failed: {_fe}')
        try:
            t0 = time.time()
            if detconn is not None:
                det = detconn
            else:
                #own client: basesetup runs in a forked child, and sharing the
                #parent's persistent HTTP connection desyncs request/response
                #pairing when both sides talk to the DCU at the same time
                #(GET then receives the list reply of a previous PUT ->
                #"list indices must be integers" errors)
                det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)
            self.logger.debug(f'TotalFrames =  {self.TotalFrames},exposureTime = {self.exposureTime} ')
            self.logger.debug(f'oscillationStart =  {self.oscillationStart},framewidth = {self.detosc}')
            self.logger.debug(f'directory =  {self.directory},filename = {self.filename},fileindex={self.fileindex}')
            self.logger.debug(f'distance =  {self.distance},wavelength = {self.wavelength},detectoroffX={self.detectoroffX},detectoroffY={self.detectoroffY},beamsize={self.beamsize},atten={self.atten}')
            # self.logger.debug(f'Unknow =  {self.unknow}')
            framerate = 1 / self.exposureTime 
            TotalTime = self.TotalFrames * self.exposureTime
            with concurrent.futures.ThreadPoolExecutor() as executor:
                self.logger.debug(f'setting Detector')
                Filename = self.filename + "_" + str(self.fileindex).zfill(4)
                que = queue.Queue()
                write_headerP = Thread(target=self.write_header,args=(raster,Filename,que,collectype,),name='write_header')
                
                write_headerP.start()
                #ask detector current setting
                detinfo={}
                infolist = ['roi_mode','threshold/difference/mode','threshold/2/mode','trigger_mode',\
                            'nimages','ntrigger','count_time','frame_time','photon_energy',\
                            'beam_center_x','beam_center_y',\
                            'detector_distance','omega_start','omega_increment','chi_start','phi_start']
                futuresinfo = []
                for item in infolist:
                    futuresinfo.append(executor.submit(detectorConfig,item,self.detectorip,self.detectorport))
                for future in concurrent.futures.as_completed(futuresinfo):                  
                    index = futuresinfo.index(future)
                    value = future.result()['value']
                    detinfo[infolist[index]] = value
                    self.logger.debug(f'{infolist[index]} = {value},type = {type(value)} take {time.time()-t0} sec ')
                    # 2023-09-21 16:00:47,111 - Detector - DEBUG -basesetup- threshold/difference/mode = disabled,type = <class 'str'> take 0.06989383697509766 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,121 - Detector - DEBUG -basesetup- y_pixels_in_detector = 4362,type = <class 'int'> take 0.08010458946228027 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,124 - Detector - DEBUG -basesetup- omega_start = 180.00001,type = <class 'float'> take 0.08339810371398926 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,129 - Detector - DEBUG -basesetup- photon_energy = 12700.0,type = <class 'float'> take 0.08796453475952148 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,130 - Detector - DEBUG -basesetup- roi_mode = disabled,type = <class 'str'> take 0.08909392356872559 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,131 - Detector - DEBUG -basesetup- threshold/2/mode = disabled,type = <class 'str'> take 0.08966827392578125 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,131 - Detector - DEBUG -basesetup- x_pixels_in_detector = 4148,type = <class 'int'> take 0.09022378921508789 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,132 - Detector - DEBUG -basesetup- trigger_mode = exts,type = <class 'str'> take 0.09073901176452637 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,132 - Detector - DEBUG -basesetup- count_time = 0.0079999,type = <class 'float'> take 0.09122562408447266 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,133 - Detector - DEBUG -basesetup- beam_center_x = 2100.0,type = <class 'float'> take 0.09171748161315918 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,133 - Detector - DEBUG -basesetup- beam_center_y = 2287.0,type = <class 'float'> take 0.09219741821289062 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,134 - Detector - DEBUG -basesetup- ntrigger = 1,type = <class 'int'> take 0.09267640113830566 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,134 - Detector - DEBUG -basesetup- detector_distance = 0.40000032,type = <class 'float'> take 0.0931541919708252 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,135 - Detector - DEBUG -basesetup- nimages = 1,type = <class 'int'> take 0.09371614456176758 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,135 - Detector - DEBUG -basesetup- frame_time = 0.008,type = <class 'float'> take 0.09426331520080566 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,136 - Detector - DEBUG -basesetup- omega_increment = 1.0,type = <class 'float'> take 0.0947885513305664 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,136 - Detector - DEBUG -basesetup- phi_start = 0.0,type = <class 'float'> take 0.0952756404876709 sec  (Detector.py:1203)
                    # 2023-09-21 16:00:47,137 - Detector - DEBUG -basesetup- chi_start = 3.381953e-09,type = <class 'float'> take 0.09580540657043457 sec  (Detector.py:1203)
                print(f'time = { time.time()-t0}')
                #somthing not easy to asynchronously
                self.logger.debug(f'ask setting ROI and frist threshold')
                if roi:
                    # if det.detectorConfig('roi_mode')['value'] == "disabled":
                    if detinfo['roi_mode'] == "disabled":
                        self.logger.debug(f'set detector roi_mode from disabled to 4M')
                        det.setDetectorConfig('roi_mode','4M')
                    framerate = 500 #debug #force to no using 2nd energy
                    if framerate > 280:
                        self.logger.debug(f'framerate =  {framerate},disable two threshold')
                        if detinfo['threshold/difference/mode'] == "enabled":
                            self.logger.debug(f'update detector threshold/difference/ to disabled')
                            det.setDetectorConfig('threshold/difference/mode','disabled')
                        if detinfo['threshold/2/mode'] == "enabled":
                            self.logger.debug(f'update detector threshold/2/mode to disabled')
                            det.setDetectorConfig('threshold/2/mode','disabled')
                    else:
                        self.logger.debug(f'framerate =  {framerate},enable two threshold')
                        if detinfo['threshold/2/mode'] == "disabled":
                            det.setDetectorConfig('threshold/2/mode','enabled')
                        if detinfo['threshold/difference/mode'] == "disabled":    
                            det.setDetectorConfig('threshold/difference/mode','enabled')
                    
                else:
                    framerate = 75 #force to no using 2nd energy
                    if detinfo['roi_mode'] == "4M":
                        self.logger.debug(f'set detector roi_mode from 4M to disabled')
                        det.setDetectorConfig('roi_mode','disabled')
                    
                    if framerate > 70:
                        self.logger.debug(f'framerate =  {framerate},disable two threshold')
                        if detinfo['threshold/difference/mode'] == "enabled":
                            self.logger.debug(f'update detector threshold/difference/ to disabled')
                            det.setDetectorConfig('threshold/difference/mode','disabled')
                        if detinfo['threshold/2/mode'] == "enabled":
                            self.logger.debug(f'update detector threshold/2/mode to disabled')
                            det.setDetectorConfig('threshold/2/mode','disabled')
                    else:
                        self.logger.debug(f'framerate =  {framerate},enable two threshold')
                        if detinfo['threshold/2/mode'] == "disabled":
                            det.setDetectorConfig('threshold/2/mode','enabled')
                        if detinfo['threshold/difference/mode'] == "disabled":    
                            det.setDetectorConfig('threshold/difference/mode','enabled')
                self.logger.debug(f'done for setting ROI and threshold')    
                self.logger.debug(f'ask for setting trigger_mode/count time')
                if raster:               
                    # self.det.setDetectorConfig('trigger_mode','exte')##temp
                    # if detinfo['trigger_mode'] != 'exts':
                    det.setDetectorConfig('trigger_mode','exts')##temp
                    # if detinfo['nimages'] != int(self.rasterinfo['y']):
                    det.setDetectorConfig('nimages',int(self.rasterinfo['y']))
                    # if detinfo['ntrigger'] != int(self.rasterinfo['x']):
                    det.setDetectorConfig('ntrigger',int(self.rasterinfo['x']))
                    # if detinfo['count_time'] != self.exposureTime:
                    det.setDetectorConfig('count_time',self.exposureTime) 
                    # if detinfo['frame_time'] != self.exposureTime:
                    det.setDetectorConfig('frame_time',self.exposureTime)
                    
                else:
                    # if detinfo['trigger_mode'] != 'exts':
                    det.setDetectorConfig('trigger_mode','exts')##temp
                    # if detinfo['nimages'] != int(self.TotalFrames):
                    det.setDetectorConfig('nimages',self.TotalFrames)
                    # if detinfo['ntrigger'] != int(1):
                    det.setDetectorConfig('ntrigger',1)
                    # if detinfo['count_time'] != self.exposureTime:
                    det.setDetectorConfig('count_time',self.exposureTime) 
                    # if detinfo['frame_time'] != self.exposureTime:
                    det.setDetectorConfig('frame_time',self.exposureTime)
                    
                self.logger.debug(f'done for setting trigger_mode/count time')
                print(f'time = { time.time()-t0}')
                Energy = float(self.ca.caget(self.Par['collect']['EnergyPV']))*1000
                self.logger.debug(f'ask photon_energy')
                # ans = det.detectorConfig('photon_energy')
                detEn= detinfo['photon_energy']
                self.logger.debug(f'Current detector energy={detEn},DCm energy ={Energy}')
                # print(f'Current Energy:{Energy}, Current Detector setting energy={detEn}')
                if (abs(Energy-detEn)>0.5):#change if more than 0.5v
                    det.setDetectorConfig('photon_energy',Energy)
                    self.logger.info(f'Detector origin energy={detEn},now set to {Energy}')

                #has been ask in header but ROI maybe change it
                self.x_pixels_in_detector= int(det.detectorConfig('x_pixels_in_detector')['value'])
                self.y_pixels_in_detector= int(det.detectorConfig('y_pixels_in_detector')['value'])
                dethor = float(self.ca.caget(self.Par['collect']['dethorPV']))
                detver = float(self.ca.caget(self.Par['collect']['detverPV']))
                beamx = int(self.x_pixels_in_detector/2 - dethor/self.x_pixel_size/1e3)
                beamy = int(self.y_pixels_in_detector/2 + detver/self.y_pixel_size/1e3)
                try:
                    chi = float(self.ca.caget(self.Par['collect']['chiPV']))
                    phi = float(self.ca.caget(self.Par['collect']['phiPV']))
                except:
                    chi = 0
                    phi = 0

                self.logger.debug(f'ask setting some basic info to detector')
                #something can be set frist
                # however seem not DCU can't do it parallel,setting matbe not 
            # with concurrent.futures.ThreadPoolExecutor() as executor:
            # with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = []
                tstart = time.time()
                if int(detinfo['beam_center_x']) != beamx:
                    self.logger.debug(f'{detinfo["beam_center_x"]=} != {beamx} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'beam_center_x',beamx,self.detectorip,self.detectorport))
                if int(detinfo['beam_center_y']) != beamy:
                    self.logger.debug(f'{detinfo["beam_center_y"]=} != {beamy} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'beam_center_y',beamy,self.detectorip,self.detectorport))
                if detinfo['detector_distance'] != self.distance/1000:
                    self.logger.debug(f'{detinfo["detector_distance"]=} != {self.distance/1000} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'detector_distance',self.distance/1000,self.detectorip,self.detectorport))
                if detinfo['omega_start'] == None:
                    self.logger.debug(f'{detinfo["omega_start"]=} != {self.oscillationStart} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'omega_start',self.oscillationStart,self.detectorip,self.detectorport))
                    pass
                elif round(detinfo['omega_start'],3) != round(self.oscillationStart,3):
                    self.logger.debug(f'{detinfo["omega_start"]=} != {self.oscillationStart} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'omega_start',self.oscillationStart,self.detectorip,self.detectorport))
                if detinfo['omega_increment'] == None:
                    self.logger.debug(f'{detinfo["omega_increment"]=} != {self.detosc} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'omega_increment',self.detosc,self.detectorip,self.detectorport))
                elif round(detinfo['omega_increment'],3) != round(self.detosc,3):
                    self.logger.debug(f'{detinfo["omega_increment"]=} != {self.detosc} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'omega_increment',self.detosc,self.detectorip,self.detectorport))
                if detinfo['chi_start'] == None:
                    self.logger.debug(f'{detinfo["chi_start"]=} != {chi} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'chi_start',chi,self.detectorip,self.detectorport))
                elif round(detinfo['chi_start'],3) != round(chi,3):
                    self.logger.debug(f'{detinfo["chi_start"]=} != {chi} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'chi_start',chi,self.detectorip,self.detectorport))
                
                # futures.append(executor.submit(setDetectorConfig, 'chi_increment',0,self.detectorip,self.detectorport))
                if detinfo['phi_start'] == None:
                    self.logger.debug(f'{detinfo["phi_start"]=} != {phi} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'phi_start',phi,self.detectorip,self.detectorport))
                elif round(detinfo['phi_start']) != round(phi,3):
                    self.logger.debug(f'{detinfo["phi_start"]=} != {phi} update detector')
                    futures.append(executor.submit(setDetectorConfig, 'phi_start',phi,self.detectorip,self.detectorport))
                # futures.append(executor.submit(setDetectorConfig, 'phi_increment',0,self.detectorip,self.detectorport))
                
                futures.append(executor.submit(setMonitorConfig, 'mode',"enabled",self.detectorip,self.detectorport))
               
                futures.append(executor.submit(setFileWriterConfig, 'mode',"enabled",self.detectorip,self.detectorport))

                for future in concurrent.futures.as_completed(futures):
                    #surface setDetectorConfig/setMonitor/setFileWriter failures
                    #instead of silently arming with the wrong settings
                    future.result()
                    # print(time.time()-tstart,future.result())
                self.logger.debug(f'done for setting some basic info to detector now = {time.time()-t0}') 
                    
                print(f'time = { time.time()-t0}')
                self.logger.debug(f'Filename =  {Filename}')
                det.setFileWriterConfig('name_pattern',Filename)
                self.Par['Detector']['Filename'] = Filename
                self.Par['Detector']['Fileindex'] = self.fileindex
                self.Par['Detector']['nimages'] = self.TotalFrames
            
                
                #update to md3
                #wait md3 ready. keep this STRICTLY shorter than the setup-worker
                #watchdog (_run_basesetup timeout): if they are equal, a stuck MD3
                #makes this wait burn the whole watchdog budget and the worker gets
                #killed right before it can arm + POST the /tranfer notify, so the
                #dataset is never announced to the download/transfer server.
                self.waitMD3Ready(15)
                self.logger.info(f'update to MD3 NumberOfFramesPV {self.TotalFrames}')
                NumberOfFramesPV = self.Par['collect']['NumberOfFramesPV']
                # caput(NumberOfFramesPV,self.TotalFrames)
                self.ca.caput(NumberOfFramesPV,self.TotalFrames)
                print(f'time = { time.time()-t0}')
                write_headerP.join(30)
                if write_headerP.is_alive():
                    raise TimeoutError('write_header thread did not finish in 30s')
                try:
                    header_appendix = que.get(timeout=5)
                except queue.Empty:
                    raise RuntimeError('write_header produced no header (queue empty)')
                if header_appendix is None:
                    raise RuntimeError('write_header failed (see earlier log)')
                header_appendix['TotalFrames'] = self.TotalFrames
                header_appendix['stream_name'] = generate_timestamp_string()
                #worker mode: stash it so setup_worker_loop can return it to the
                #parent, which POSTs /tranfer exactly once on success (below is
                #only used by the legacy non-worker path).
                self._setup_header = header_appendix
                text = json.dumps(header_appendix)
                print(f'after get header que time = { time.time()-t0}')
                det.setStreamConfig('header_appendix',text)
                det.setStreamConfig('image_appendix',text)
                print(f'after set streamconfig time = { time.time()-t0}')

                self.logger.info(f'arm detector')
                det.sendDetectorCommand('arm')
                self.logger.info(f'done for arm detector')
                print(f'time = { time.time()-t0}')
            # self.det.sendDetectorCommand('trigger')
            
            #check cryjet in?

            self.logDetInfo(det)
            t1 = time.time()
            
            # we wait baseset can be a process, so take it outide here
            # self.logger.debug('start to updatefilestring check')
            # monP = Process(target=self.updatefilestring,name='Monfile')
            # monP.start()

            #Notify Download server.
            #worker mode: the PARENT sends this (see _run_basesetup) exactly once
            #on success, so DON'T send it here or a worker retry would duplicate.
            #legacy non-worker mode: no parent hand-back, so send from the child.
            if not USE_SETUP_WORKER:
                try:
                    url = 'http://10.7.1.108:64444/tranfer'
                    # response = requests.post(url , json=header_appendix)
                    p = Process(target=self.sendtoAutostra,args=(url,header_appendix))
                    p.start()
                except Exception as e:
                    self.logger.warning(f'Notify Download server has error {e}')

            self.logger.info(f'setup time = {t1-t0}')
            # return TotalTime,Filename
        except Exception as e:
            error_class = e.__class__.__name__ #取得錯誤類型
            detail = e.args[0] #取得詳細內容
            cl, exc, tb = sys.exc_info() #取得Call Stack
            lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
            fileName = lastCallStack[0] #取得發生的檔案名稱
            lineNum = lastCallStack[1] #取得發生的行號
            funcName = lastCallStack[2] #取得發生的函數名稱
            errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)
            self.logger.warning(f'Setup detector has error {errMsg},{e}')
            sys.exit(-1)#for mutiprocess
    def setup_beamsize_cover_distance(self,raster=False,roi=False,beamwithdis=False,movebeasize=True,bypassslit=False,movecryojet=True,movedistance=False):
        t0=time.time()
        #move cryjet in
        #movecryojet False: this collect type does not use the cryojet at all
        #(SSX runs a fixed target at room temperature), so asking the robot to
        #move it in is a pointless round trip to another machine -- and one that
        #can only report problems the user cannot act on.
        host,port = self.Par['robot']['host'],self.Par['robot']['commandprot']
        cryo_ok,cryo_detail = (True,'skipped')
        if movecryojet:
            cryo_ok,cryo_detail = askCryojetIn(host,port,self.Par['robot'].get('timeout',5),self.logger)
        else:
            self.logger.info('cryojet move skipped for this collect type')
        if not cryo_ok:
            #the collect goes on (a missing cryojet move is not worth killing a
            #dataset over) but the user MUST be told: an un-cooled sample decays
            #fast, and before the timeout was added this failure was invisible.
            #htos_note is forwarded verbatim to every BlueIce client and stays in
            #its log, unlike system_status which the next status update wipes
            #within a second.
            #dcss reads a hardware-client message into char[201], so the whole
            #note must stay under that: clamp the exception text (and the result)
            #instead of letting a chatty errno truncate the actionable half.
            warn = f'Cryojet NOT moved in: robot relay {host}:{port} did not answer ({cryo_detail[:60]}). Check the cryojet before trusting this dataset.'
            self.sendQ.put(('warning',warn[:190]))

        # old open cover, now move to beamsize
        # opcoverP = Process(target=self.cover.OpenCover,name='open_cover')
        # opcoverP.start()
        
        if raster or beamwithdis:
            # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,True,),name='MoveBeamSize')
            # beamsizeP.start()
            self.logger.debug(f'{raster=},{beamwithdis=}')
            self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,True,bypassslit)
            # self.sendQ.put(('endmove','beamSize',str(self.beamsize),'normal'), block=False)
            self.sendQ.put(('updatevalue','currentBeamsize',str(self.beamsize),'string','normal'))
            
        else:
            #normal shutterless collect
            #check frame rate?
            # framerate = self.TotalFrames / self.exposureTime
            # beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            # beamsizeP = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            # beamsizeP.start()
            
            if movebeasize:
                self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,False,bypassslit)
                # self.sendQ.put(('endmove','beamSize',str(self.beamsize),'normal'), block=False)
                self.sendQ.put(('updatevalue','currentBeamsize',str(self.beamsize),'string','normal'))
            else:
                #but we still need open cover
                self.MoveBeamsize.opencover(True)
                if movedistance:
                    self.move_distance_and_wait(self.distance)
                pass
        self.logger.info(f'setup  = {time.time()-t0}')
    def move_distance_and_wait(self,target,timeout=180):
        #move detector_z the same way DCSS does (caput the 07a:Det:Dis soft
        #motor; the distance interlock drives Det:Y from it) and block until it
        #stops, so the detector is in place before the collect is triggered.
        disPV = self.Par['fakedistancename']
        detYPV = self.MoveBeamsize.DetYMotor
        current = self.ca.caget(f'{disPV}.RBV',format=float)
        disLLM = self.ca.caget(f'{disPV}.LLM',format=float)
        disHLM = self.ca.caget(f'{disPV}.HLM',format=float)
        if disLLM is not None and target < disLLM:
            self.logger.warning(f'Request distance {target} lower than LLM {disLLM}, use LLM')
            target = disLLM
        elif disHLM is not None and target > disHLM:
            self.logger.warning(f'Request distance {target} higher than HLM {disHLM}, use HLM')
            target = disHLM
        if current is not None and abs(current-target) < 0.1:
            self.logger.info(f'distance already at {current} (target {target}), not move')
            return True
        self.logger.info(f'move distance {current} -> {target}')
        t0 = time.time()
        self.ca.caput(disPV,target)
        #DMOV may still read 1 for a moment after the put (motor not started
        #yet), so only trust DMOV=1 once RBV is at target or after a 2s grace.
        while time.time()-t0 < timeout:
            time.sleep(0.1)
            rbv = self.ca.caget(f'{disPV}.RBV',format=float)
            stopped = self.MoveBeamsize.check_allmotorstop([disPV,detYPV])
            if stopped and rbv is not None and abs(rbv-target) < 0.1:
                self.logger.info(f'distance in position {rbv}, take {time.time()-t0:.1f}s')
                return True
            if stopped and time.time()-t0 > 2:
                self.logger.warning(f'distance stopped at {rbv}, not at target {target}')
                return False
        self.logger.critical(f'distance move timeout ({timeout}s), still not at {target}')
        return False
    def write_header(self,raster,Filename,que:queue.Queue,collectype):
        #wrapper: guarantee the consumer's que.get() always receives something.
        #write_header runs in a Thread, so if header building raises the thread
        #just dies and que stays empty -> basesetup would block on que.get()
        #forever. Push a None sentinel on failure so the consumer fails fast
        #(and the setup process exits -> watchdog retries) instead of hanging.
        try:
            self._write_header_impl(raster,Filename,que,collectype)
        except Exception as e:
            self.logger.warning(f'write_header failed, push sentinel: {e}')
            que.put(None)

    def _write_header_impl(self,raster,Filename,que:queue.Queue,collectype):
        self.logger.debug(f'ask for asking beamline info')

        #handle ecpis on mutiprocess problem,but not work
        """
        Clears global pyepics state and fixes the CA context
        such that forked subprocesses created with multiprocessing
        can safely use pyepics.
        """
        # ca.clear_cache()
        # # Clear global pyepics state variables
        # ca._cache.clear()

        # # The old context is copied directly from the old process
        # # in systems with proper fork() implementations
        # ca.detach_context()
        # ca.create_context()

        #get user info
        #user blctl not in ladp database
        if self.userName=='blctl':
            uidNumber = getpwnam(self.userName)[2]
            gidNumber = getpwnam(self.userName)[3]
        else:
            uidNumber,gidNumber,passwd = self.ladp.getuserinfo(self.userName)

        Ebeamcurrent = self.ca.caget(self.Par['collect']['EbeamPV'],format=float)
        gap = self.ca.caget(self.Par['collect']['gapPV'],format=float)
        dbpm1flux = self.ca.caget(self.Par['collect']['DBPM1PV'],format=float)
        dbpm2flux = self.ca.caget(self.Par['collect']['DBPM2PV'],format=float)
        dbpm3flux = self.ca.caget(self.Par['collect']['DBPM3PV'],format=float)
        dbpm5flux = self.ca.caget(self.Par['collect']['DBPM5PV'],format=float)
        dbpm6flux = self.ca.caget(self.Par['collect']['DBPM6PV'],format=float)
        sampleflux = self.ca.caget(self.Par['collect']['samplefluxPV'],format=float)
        kappa = self.ca.caget(self.Par['collect']['kappaPV'],format=float)
        #update beamsize for current beamsize
        try:
            CurrentBeamsizePV = self.Par['EPICS_special']['BeamSize']['CurrentBeamsize']
            BeamSizeNamePV = self.Par['EPICS_special']['BeamSize']['BeamSizeName']
            currentbeamsize = self.ca.caget(CurrentBeamsizePV,format=float)
            BeamSizeNamelist = self.ca.caget(BeamSizeNamePV,array=True,format=float)
            # print(BeamSizeNamelist,currentbeamsize)
            beamsizeindex = np.where(BeamSizeNamelist == currentbeamsize)
            beamsizeindex = int(beamsizeindex[0][0])
            SampleSizeXPV = self.Par['EPICS_special']['BeamSize']['BeamSizeX']
            SampleSizeYPV = self.Par['EPICS_special']['BeamSize']['BeamSizeY']
            SampleSizeXlist = self.ca.caget(SampleSizeXPV,array=True,format=float)
            SampleSizeYlist = self.ca.caget(SampleSizeYPV,array=True,format=float)
            SampleSizeX = float(SampleSizeXlist[beamsizeindex])
            SampleSizeY = float(SampleSizeYlist[beamsizeindex])
            # txt = epics.cainfo(SampleSizeXPV, print_out=False)
            # flux_timestamp = re.search(r'.*timestamp.*\((.*)\)', txt)[1]
            #tps 07a only
        except Exception as e:
            self.logger.warning(f'Fail to get Sample Size info, error{e}')
            SampleSizeX = float(currentbeamsize)
            SampleSizeY = float(currentbeamsize)
        self.dbpm1.update()
        self.dbpm2.update()
        self.dbpm3.update()
        self.dbpm5.update()
        self.dbpm6.update()
        
        
        
        
        header_appendix ={}
        header_appendix['user'] = self.userName
        header_appendix['directory'] = self.directory
        header_appendix['runIndex'] = self.runIndex
        header_appendix['beamsize'] = self.beamsize
        header_appendix['beamsizeHor'] = SampleSizeX
        header_appendix['beamsizeVer'] = SampleSizeY
        # header_appendix['timestamp_record_beamprofile'] = flux_timestamp
        header_appendix['atten'] = self.atten
        header_appendix['fileindex'] = self.fileindex
        header_appendix['filename'] = Filename
        # header_appendix['uid'] = getpwnam(self.userName)[2]
        # header_appendix['gid'] = getpwnam(self.userName)[3]
        header_appendix['uid'] = uidNumber
        header_appendix['gid'] = gidNumber
        header_appendix['Ebeamcurrent'] = Ebeamcurrent
        header_appendix['gap'] = gap
        header_appendix['collectype'] = collectype
        header_appendix['dbpm1flux'] = dbpm1flux
        header_appendix['dbpm2flux'] = dbpm2flux
        header_appendix['dbpm3flux'] = dbpm3flux
        header_appendix['dbpm5flux'] = dbpm5flux
        header_appendix['dbpm6flux'] = dbpm6flux
        header_appendix['sampleflux'] = sampleflux
        header_appendix['kappa'] = kappa
        for name,value in self.dbpm1.getneedvalue():
            header_appendix[name] = value
        for name,value in self.dbpm2.getneedvalue():
            header_appendix[name] = value
        for name,value in self.dbpm3.getneedvalue():
            header_appendix[name] = value
        for name,value in self.dbpm5.getneedvalue():
            header_appendix[name] = value
        for name,value in self.dbpm6.getneedvalue():
            header_appendix[name] = value
        pass
        if raster:
            header_appendix['raster_X']=self.rasterinfo['x']
            header_appendix['raster_Y']=self.rasterinfo['y']
            header_appendix['grid_width']=self.rasterinfo['gridsizex']
            header_appendix['grid_height']=self.rasterinfo['gridsizey']
        else:
            pass
        # text = json.dumps(header_appendix)
        que.put(header_appendix)
        # self.det.setStreamConfig('header_appendix',text)
        self.logger.debug(f'done for asking beamline info')
    def logDetInfo(self,det:DEigerClient=None):
        t0 = time.time()
        if det == None:
            det = self.det
        commands = ["count_time","frame_time",'detector_distance','nimages','ntrigger',
                'photon_energy','roi_mode',
                'threshold_energy','threshold/1/energy',
                'threshold/1/mode','threshold/2/energy','threshold/2/mode',
                'threshold/difference/mode','trigger_mode','wavelength',
                'beam_center_x','beam_center_y','auto_summation',
                'bit_depth_image','bit_depth_readout','compression',
                'omega_start','omega_increment','virtual_pixel_correction_applied']
        # detectorConfig number_of_excluded_pixels take 0.11530303955078125
        #take too long we remove it
        #ProcessPoolExecutor take 0.2sec mote to start
        with concurrent.futures.ThreadPoolExecutor() as executor:           
        # with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            for item in commands:
                # futures.append(executor.submit(det.detectorConfig,item))
                futures.append(executor.submit(detectorConfig,item,self.detectorip,self.detectorport))
            for future in concurrent.futures.as_completed(futures):                  
                index = futures.index(future)
                value = future.result()['value']
                try:
                    unit = future.result()['unit']
                except :
                    unit =""
                self.logger.debug(f'{commands[index]} = {value} {unit} take {time.time()-t0} sec ') 
        # for command in commands:
        #     ans = det.detectorConfig(command)
        #     value = ans[# for command in commands:
        #     ans = det.detectorConfig(command)
        #     value = ans['value']
        #     try:
        #         unit = ans['unit']
        #     except :
        #         unit =""
        #     self.logger.debug(f'{command} = {value} {unit}') ]
        #     try:
        #         unit = ans['unit']
        #     except :
        #         unit =""
        #     self.logger.debug(f'{command} = {value} {unit}') 
        print(f'Get logDetInfo take time = {time.time()-t0} sec')
    def waitMD3Ready(self,timeout=20):
        t0 = time.time()
        check = True
        init = True
        while check:
            # md3_state = caget('07a:md3:Status ',as_string=True)
            md3_state = self.ca.caget('07a:md3:State',format = str)
            # print(md3_state)
            if md3_state== 'Ready' or md3_state== 'READY' or md3_state== 'READY\n':
                self.logger.info(f'MD3 is Ready')
                return True 
                check = False
            else:
                if init:
                    self.logger.debug(f'MD3 is busy:{md3_state}')
                    init = False
                # self.logger.info(f'MD3 is busy:{md3_state}')  
            if (time.time()-t0)>timeout:
                self.logger.info(f'MD3 is busy:{md3_state} and timeout reach')     
                return False
            time.sleep(0.2)
    def pipecaput(self,PV,value):
        self.logger.warning(f'caput PV={PV},value={value}')
        if type(value) is list:
            command = ['caput',str(PV)]
            for item in value:
                command.append(str(item))
        else:
            command = ['caput',str(PV),str(value)]
        ans = subprocess.run(command,capture_output=True)
        result = ans.stdout.decode('utf-8')
        error = ans.stderr.decode('utf-8')       
        self.logger.debug(f'{ans},result={result},error={error}')
        if error == '':
            print(f'caput PV={PV},value={value} OK!')
            # return True
            return 1
        else:
            self.logger.critical(f"Caput {PV} value {value} Fail={error}")
            # return False
            return 0
    def checkandretryCoverProcess(self,coverprocess,action):
        
        coverprocess.join(5)
        self.logger.warning(f'{action} coverP process {coverprocess.is_alive()=},{coverprocess.pid=},{coverprocess.sentinel=},{coverprocess.exitcode=}')
        if coverprocess.exitcode== None:
            if self.errorcount == 0: 
                self.logger.critical(f'closecover P has problem kill it!')
                self.errorcount = self.errorcount + 1
            else:
                self.logger.warning(f'closecover P has problem kill it!')
            coverprocess.kill()
            #try to close again
            self.logger.warning(f'Try to close it again!')
            closecoverP = Process(target=self.cover.askforAction,args=(action,),name='close_cover')
            closecoverP.start()
            self.checkandretryCoverProcess(closecoverP,action)
        else:
            self.logger.warning(f'OK for {action} Cover!!')
            self.errorcount == 0
        pass
    def checkandretryDetectorSetupProcess(self,detectorprocess:Process,args,timeout =10):
        
        detectorprocess.join(timeout)
        self.logger.warning(f'Setup detector process {detectorprocess.is_alive()=},{detectorprocess.pid=},{detectorprocess.sentinel=},{detectorprocess.exitcode=}')
        if detectorprocess.exitcode != 0 :
            if self.errorcount == 0: 
                self.logger.critical(f'detector process has problem kill it!')
                self.errorcount = self.errorcount + 1
            else:
                self.logger.warning(f'detector process has problem kill it! Count={self.errorcount}')
            detectorprocess.kill()
            #try to close again
            self.logger.warning(f'Try to resetup detector again!')
            self.det = DEigerClient(self.detectorip,self.detectorport,verbose=False,connectionTimeout=DET_HTTP_TIMEOUT)#ask for new client
            # time.sleep(0.2)
            a = list(args)
            a[-2] = self.det
            b = tuple(a)
            detectorP = CAProcess(target=self.basesetup,args=b,name='Detector_Setup')
            detectorP.start()
            # 2nd try short timeout
            self.checkandretryDetectorSetupProcess(detectorP,args,timeout=5)
        else:
            self.logger.info(f'OK for detector setup')
            self.errorcount = 0
        pass
    def recheckandretryProcess(self,beamsizeP,raster,beamwithdis,bypassslit):
        beamsizeP.join(60)
        if beamsizeP.exitcode == None:
            self.logger.warning(f'beamsize P has problem kill it!')
            self.logger.warning(f'beamsize process {beamsizeP.is_alive()=},{beamsizeP.pid=},{beamsizeP.sentinel=},{beamsizeP.exitcode=}')
            beamsizeP.kill()
            self.logger.warning(f'Try to go beamsize again!')
            if raster or beamwithdis:
                beamsizeP2 = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,True,bypassslit,),name='MoveBeamSize')
                beamsizeP2.start()
                self.recheckandretryProcess(beamsizeP2,raster,beamwithdis,bypassslit)
                
            else:
                #check frame rate?
                # framerate = self.TotalFrames / self.exposureTime
                # beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
                beamsizeP2 = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False,bypassslit),name='MoveBeamSize')
                beamsizeP2.start()
                self.recheckandretryProcess(beamsizeP2,raster,beamwithdis,bypassslit)
    #todo rcheckandretryCoverProcess
class dbpm07a():
    def __init__(self,number,ca=None) -> None:
        #DBPM1sum:Mean
        #DBPM1sum:Stability
        #DBPM1x:Mean
        #DBPM1x:Stability
        #DBPM1y:Mean
        #DBPM1y:Stability
        self.number=number
        self.genname()
        if ca == None:
            self.ca=myepics()
        else:
            self.ca=ca
    def genname(self):
        tmp = "07a-ES:DBPMsum:Mean"
        namelist = ['Mean','Stability']
        poslist = ['sum','x','y']
        self.dbpminfo = {}


        for pos in poslist:
            self.dbpminfo[pos]={}
            for item in namelist:
                self.dbpminfo[pos][item]={}
                temp = f"07a-ES:DBPM{self.number}{pos}:{item}"
                self.dbpminfo[pos][item]['name'] = temp

    def update(self):
        
        for key in self.dbpminfo:
            
            for key2 in self.dbpminfo[key]:
                self.dbpminfo[key][key2]['value']=self.ca.caget(self.dbpminfo[key][key2]['name'],format=float)
                
        # print(self.dbpminfo)    
        pass
    def getneedvalue(self):
        ans = []
        for key in self.dbpminfo:           
            for key2 in self.dbpminfo[key]:
                if key == 'sum':
                    temp = (f'dbpm{self.number}_{key}_{key2}',self.dbpminfo[key][key2]['value'])
                else:#x/y
                    if key2 == "Stability":#change to rms um
                        newvalue = self.dbpminfo[key]["Stability"]['value']*self.dbpminfo[key]["Mean"]['value']/100/1000
                        temp = (f'dbpm{self.number}_{key}_rms',newvalue)
                    else:#Mean,using um
                        temp = (f'dbpm{self.number}_{key}_{key2}',self.dbpminfo[key][key2]['value']/1000)

                ans.append(temp)
        # print(ans)
        return ans
    
def askCryojetIn(host,port,timeout=5,logger=None):
    #moving the cryojet in is a best-effort side action, it must NEVER be able
    #to stall a collect. the relay (fakeserver.py on the robot host) can accept
    #the TCP connection and then answer nothing: its replayserver worker dies
    #when the ISARA PLC link drops, and from then on every client blocks in
    #backq.get() inside handle_client. with no timeout this recv() froze the
    #whole DetectorQ worker on the FIRST line of setup_beamsize_cover_distance
    #(2026-09-23 16:25): the detector was armed, but the cover never opened and
    #DCSS never got operupdate/operdone, so the collect hung with no error.
    #timeout covers connect/send/recv; a normal relay reply takes ~30 ms.
    #returns (ok,detail): ok False means the cryojet was NOT moved in, so the
    #caller must tell DCSS instead of collecting silently with it still out.
    _info = logger.info if logger is not None else print
    _warn = logger.warning if logger is not None else print
    t0 = time.time()
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        # host = '10.7.1.3'
        # port = 10001
        command = 'movecryojetin'
        client.connect((host, port))
        sendToPLCCommand(client,command)
        ans = client.recv(4096).decode()
        _info(f'Robot relay:{ans} take {time.time()-t0} sec')
        return True,ans.strip()
    except Exception as e:
        #log it, do not raise: the collect goes on without the cryojet move
        _warn(f'askCryojetIn failed (collect continues): {e}, take {time.time()-t0} sec')
        return False,f'{type(e).__name__}: {e}'
    finally:
        try:
            client.close()
        except Exception:
            pass
def sendToPLCCommand(sockclient:socket.socket,command):
    if type(command)==str:
        #check is there has \r in the end
        if command[-1:] == '\r':
            CommandInByte = bytes(command,'utf-8')#or use str.encode()?
        else:
            CommandInByte = bytes(command+'\r','utf-8')
            # CommandInByte = f'{command}\r'.encode()
    elif type(command)==bytes:
        CommandInByte = command
    else:
        # CommandInByte = b''#no command
        pass
    sockclient.send(CommandInByte)
if __name__ == "__main__":
    # import Config
    # Par = Config.Par
    # #setup for Queue
    # Q={'Queue':{}}
    # Q['Queue']['reciveQ'] = Queue() 
    # Q['Queue']['sendQ'] = Queue() 
    # Q['Queue']['epicsQ'] = Queue()
    # Q['Queue']['ControlQ'] = Queue()
    # Q['Queue']['DetectorQ'] = Queue()
    # test = Eiger2X16M(Par,Q)
    # p = Process(target=test.CommandMon)
    # p.start()
    
    # # print(test.detectorip)
    # # print(test.Par)
    # # Q['Queue']['DetectorQ'].put(('test','1234'))
    # Q['Queue']['DetectorQ'].put(('detector_collect_image','213'))
    # # Q['Queue']['DetectorQ'].put(('test2','21333'))
    # Q['Queue']['DetectorQ'].put(('detector_collect_imageHS','21333'))
    # Q['Queue']['DetectorQ'].put('exit')
    temp = dbpm07a("5")
    temp.update()
    temp.getneedvalue()
    # print(temp.dbpminfo)
