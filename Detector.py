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
# from epics import caput,CAProcess,caget
from epics import caput,caget,ca
import epics
from workround import myepics
import json
from pwd import getpwnam
# from DetectorCover import MOXA
from DetectorCoverV2 import MOXA
from EPICS_special import Beamsize
from ldapclient import ladpcleint
import math,requests,socket

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
        
        self.logger = logsetup.getloger2('Detector',LOG_FILENAME='./log/Detectorlog.txt',level = self.Par['Debuglevel'],bypassline=False)
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
        self.det = DEigerClient(self.detectorip,self.detectorport,verbose=False)
        self.det.setStreamConfig('header_detail','all')
        self.det.setStreamConfig('mode','enabled')
        self.det.setFileWriterConfig('mode','enabled')
        
        self.x_pixels_in_detector= int(self.det.detectorConfig('x_pixels_in_detector')['value'])
        self.y_pixels_in_detector= int(self.det.detectorConfig('y_pixels_in_detector')['value'])
        self.x_pixel_size= float(self.det.detectorConfig('x_pixel_size')['value'])
        self.y_pixel_size= float(self.det.detectorConfig('y_pixel_size')['value'])
        self.dbpm1 = dbpm07a("1")
        self.dbpm2 = dbpm07a("2")
        self.dbpm3 = dbpm07a("3")
        self.dbpm5 = dbpm07a("5")
        self.dbpm6 = dbpm07a("6")
        self.logger.warning(f'Eiger2X 16M DHS init Time: {time.time()-t0}')
    def updatefilestring(self):
        t0 = time.time()
        self.logger.info('Start updatefilestring')
        
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        masterfile = Filename + "_master.h5"
        masterpath = f'{self.directory }/{masterfile}'
        command=["","","","","",""]
        _check = True
        currentfile = self.det.fileWriterFiles()
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
            currentfile = self.det.fileWriterFiles()
        #wait for new file
        while len(currentfile) != 0:
            currentfile.remove(masterfile)
            filenum = len(currentfile)
            if filenum == 0:
                #wait for data
                pass
            else:
                dataname = f'{Filename}_data_{filenum:06}.h5'
                datapath = f'{self.directory }/{dataname}'
                command[0] = 'updatevalue'
                command[1] = 'lastImageCollected'
                command[2] = datapath
                command[3] = 'string'
                command[4] = 'normal'
                self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
            #['empty_1_0001_data_000001.h5', 'empty_1_0001_master.h5']
            time.sleep(0.2)
            currentfile = self.det.fileWriterFiles()
            
            
        #last update
        nimages = self.det.detectorConfig('nimages')['value']
        time.sleep(0.1)
        ntrigger = self.det.detectorConfig('ntrigger')['value']
        self.logger.debug(f'{nimages=},{ntrigger=}')
        totalframe = int(nimages) * int(ntrigger)
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
            beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(beamsize),distance,False,True),name='MoveBeamSize')
        else:
            distance = None
            beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(beamsize),150,False,False),name='MoveBeamSize')
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
        
        currentfile = self.det.fileWriterFiles()
        self.logger.info(f'Check for detector download data: file count :{currentfile}')
        # while type(currentfile) != type(None):
        try:
            while len(currentfile) != 0:
                self.logger.info(f'wait for detector download data: file count :{currentfile}')
                time.sleep(0.1)
                currentfile = self.det.fileWriterFiles()
        except Exception as e:
            self.logger.critical(f'Erro on monitor DCU file, error{e}')
        self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')
        #send to Autostra server if Frames <= 10
        if self.TotalFrames <= 10:
            url = 'http://10.7.1.107:65000/job'
            #/data/blctl/test/test_0_matser.h5

            masterfile =  self.directory + "/" + self.filename + '_'  + str(self.fileindex).zfill(4) +'_master.h5'
            # masterfile =  f'{self.directory}/{self.filename}_{str(self.fileindex).zfill(4)}_master.h5'
            data = {'path':masterfile}
            p = Process(target=self.sendtoAutostra,args=(url,data))
            p.start()
            pass
        # elif self.TotalFrames >= 20:
        if self.TotalFrames >= 20:
            #send to auto process
            url = 'http://10.7.1.108:65001/job'
            #/data/blctl/test/test_0_matser.h5

            masterfile =  self.directory + "/" + self.filename + '_'  + str(self.fileindex).zfill(4) +'_master.h5'
            masterfile.replace('/data','/mnt/proc_buffer')
            # masterfile =  f'{self.directory}/{self.filename}_{str(self.fileindex).zfill(4)}_master.h5'
            data = {'path':masterfile}
            p = Process(target=self.sendtoAutostra,args=(url,data))
            p.start()
            pass
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
    #                  0 \
    #                  0 \
    #                  $sessionId \
    #                  [lindex $args 0] \
    #                  $totalFrames \
    #                 $beam_size $attn]
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
        
        self.sessionId = command[17]
        self.fileindex = int(command[18])
        self.unknow = int(command[19]) #1
        self.beamsize = command[20] # 50
        self.atten = command[21] #0
        
        #  sscanf(commandBuffer.textInBuffe
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
        
        # htos_note changing_detector_mode
        toDcsscommand = ('htos_note','changing_detector_mode')
        self.sendQ.put(toDcsscommand)
        #beam size and distance has moved by dcss
        # _oscillationTime,_filename = self.basesetup(movebeasize=False)
        # raster=False,roi=False,beamwithdis=False,movebeasize=True
        args=(False,False,False,False,)
        detectorsetupP = Process(target=self.basesetup,args=args,name='Detector_Setup')
        detectorsetupP.start()
        _oscillationTime = self.TotalFrames * self.exposureTime
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        _filename = Filename + '.h5'
        self.checkandretryDetectorSetupProcess(detectorsetupP,args)
        
        
        self.logger.debug('start to updatefilestring check')
        monP = Process(target=self.updatefilestring,name='Monfile')
        monP.start()
        toDcsscommand = ('operupdate',command[0],self.operationHandle,'start_oscillation','shutter',str(_oscillationTime),_filename)
        self.sendQ.put(toDcsscommand)
        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.sendQ.put(toDcsscommand)
        self.logger.warning(f'detector_collect_shutterless take {time.time()-t0} sec')
        # command = ('operdone',) + command
        # self.sendQ.put(command)
    def mutiPosCollect(self,command):
        # ans =  [runIndex,filename,directory,userName,axisName,exposureTime,oscillationStart,detosc,TotalFrames,distance,wavelength,detectoroffX,detectoroffY,sessionId,fileindex,unknow,beamsize,atten]
        t0=time.time()
        self.operationHandle = command[1]
        self.runIndex = command[2]
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
        self.beamsize = command[18] # 50
        self.atten = command[19] #0
        # htos_note changing_detector_mode
        # toDcsscommand = ('htos_note','changing_detector_mode')
        toDcsscommand = 'htos_set_string_completed system_status normal {Changing detector mode and Beam Size} black #d0d000'
        self.sendQ.put(toDcsscommand)
        self.abort =False
        self.roi=False
        # _oscillationTime,_filename = self.basesetup(raster=False,roi=self.roi,beamwithdis=True)
        # _filename = _filename + '.h5'

        # _oscillationTime,_filename = self.basesetup(movebeasize=False)
        # raster=False,roi=False,beamwithdis=False,movebeasize=True
        args=(False,self.roi,True,True,)
        detectorsetupP = Process(target=self.basesetup,args=args,name='Detector_Setup')
        detectorsetupP.start()
        _oscillationTime = self.TotalFrames * self.exposureTime
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        _filename = Filename + '.h5'
        self.checkandretryDetectorSetupProcess(detectorsetupP,argstimeout=120)#need to move beam size take longer time
        
        
        self.logger.debug('start to updatefilestring check')
        monP = Process(target=self.updatefilestring,name='Monfile')
        monP.start()
        self.logger.warning(f'mutiPosCollect detector setup take {time.time()-t0} sec')

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
        if MD3state:
            
            state = caput(PVcollect,value)
        else:
            state = -1
        

        if state != 1:
            self.logger.critical(f"Caput {PVcollect} value {value} Fail!")
        time.sleep(0.5)
        Task = caget(LastTaskInfoPV)
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

        toDcsscommand = ('operdone',command[0],self.operationHandle)
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)

        #now not close cover in end of collect, control by bluice2
        # closecoverP = Process(target=self.cover.askforAction,args=('close',),name='mutiPosCollect_close_cover')
        # closecoverP.start()
        
        toDcsscommand = 'htos_set_string_completed system_status normal {Wating For Download Image} black #d0d000'
        self.sendQ.put(toDcsscommand)
        currentfile = self.det.fileWriterFiles()
        self.logger.info(f'Check for detector download data: file count :{currentfile}')
        try :
            if len(currentfile) != 0:
                check = True
            else:
                check = False
        except:
                check = True
        
        while check and not self.abort:
            self.logger.info(f'wait for detector download data: file count :{currentfile}')
            time.sleep(0.2)
            currentfile = self.det.fileWriterFiles()
            try :
                if len(currentfile) != 0:
                    check = True
                else:
                    check = False
            except:
                    check = True
        self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')
        
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
        self.runIndex = command[2]
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
        md3phase = float(caget(self.Par['collect']['md3modePV']))
        if md3phase != 2: 
            caput(self.Par['collect']['md3modePV'],2)
            time.sleep(0.1)
            pass

        # htos_note changing_detector_mode
        toDcsscommand = ('htos_note','changing_detector_mode')
        self.sendQ.put(toDcsscommand)

        # _oscillationTime,_filename = self.basesetup(raster=True,roi=self.roi,beamwithdis=True)
        # _filename = _filename + '.h5'
        # raster=False,roi=False,beamwithdis=False,movebeasize=True
        args=(True,self.roi,True,True,)
        detectorsetupP = Process(target=self.basesetup,args=args,name='Detector_Setup')
        detectorsetupP.start()
        # _oscillationTime = self.TotalFrames * self.exposureTime
        # Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        # _filename = Filename + '.h5'
        self.checkandretryDetectorSetupProcess(detectorsetupP,args,timeout=120)#need to move beam size take longer time
        
        
        self.logger.debug('start to updatefilestring check')
        monP = Process(target=self.updatefilestring,name='Monfile')
        monP.start()

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
        
        self.logger.info(f'try to resete detector')
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
    
    def basesetup(self,raster=False,roi=False,beamwithdis=False,movebeasize=True):
        t0 = time.time()
        ca.clear_cache()
        self.logger.debug(f'TotalFrames =  {self.TotalFrames},exposureTime = {self.exposureTime} ')
        self.logger.debug(f'oscillationStart =  {self.oscillationStart},framewidth = {self.detosc}')
        self.logger.debug(f'directory =  {self.directory},filename = {self.filename},fileindex={self.fileindex}')
        self.logger.debug(f'distance =  {self.distance},wavelength = {self.wavelength},detectoroffX={self.detectoroffX},detectoroffY={self.detectoroffY},beamsize={self.beamsize},atten={self.atten}')
        self.logger.debug(f'Unknow =  {self.unknow}')
        
        # self.det.setDetectorConfig('count_time',1-0.0000001) 
        # self.det.setDetectorConfig('frame_time',1)
        
        #move cryjet in
        askCryojetIn(self.Par['robot']['host'],self.Par['robot']['commandprot'])

        # old open cover, now move to beamsize
        # opcoverP = Process(target=self.cover.OpenCover,name='open_cover')
        # opcoverP.start()
        
        if raster or beamwithdis:
            # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,True,),name='MoveBeamSize')
            # beamsizeP.start()
            self.logger.debug(f'{raster=},{beamwithdis=}')
            self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,True)
            self.sendQ.put(('endmove','beamSize',str(self.beamsize),'normal'), block=False)
            self.sendQ.put(('updatevalue','currentBeamsize',str(self.beamsize),'string','normal'))
            framerate = 1 / self.exposureTime 
        else:
            #normal shutterless collect
            #check frame rate?
            # framerate = self.TotalFrames / self.exposureTime
            # beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            # beamsizeP = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            # beamsizeP = Thread(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            # beamsizeP.start()
            framerate = 1 / self.exposureTime
            if movebeasize:
                self.MoveBeamsize.target(float(self.beamsize),self.distance ,True,False)
                self.sendQ.put(('endmove','beamSize',str(self.beamsize),'normal'), block=False)
                self.sendQ.put(('updatevalue','currentBeamsize',str(self.beamsize),'string','normal'))
            else:
                #but we still need open cover
                self.MoveBeamsize.opencover(True)
                pass

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
            if self.det.detectorConfig('roi_mode')['value'] == "disabled":
                self.logger.debug(f'set detector roi_mode from disabled to 4M')
                self.det.setDetectorConfig('roi_mode','4M')
            framerate = 500 #debug #force to no using 2nd energy
            if framerate > 280:
                self.logger.debug(f'framerate =  {framerate},disable two threshold')
                if self.det.detectorConfig('threshold/difference/mode')['value'] == "enabled":
                    self.logger.debug(f'update detector threshold/difference/ to disabled')
                    self.det.setDetectorConfig('threshold/difference/mode','disabled')
                if self.det.detectorConfig('threshold/2/mode')['value'] == "enabled":
                    self.logger.debug(f'update detector threshold/2/mode to disabled')
                    self.det.setDetectorConfig('threshold/2/mode','disabled')
            else:
                self.logger.debug(f'framerate =  {framerate},enable two threshold')
                if self.det.detectorConfig('threshold/2/mode')['value'] == "disabled":
                    self.det.setDetectorConfig('threshold/2/mode','enabled')
                if self.det.detectorConfig('threshold/difference/mode')['value'] == "disabled":    
                    self.det.setDetectorConfig('threshold/difference/mode','enabled')
            
        else:
            framerate = 75 #force to no using 2nd energy
            if self.det.detectorConfig('roi_mode')['value'] == "4M":
                self.logger.debug(f'set detector roi_mode from 4M to disabled')
                self.det.setDetectorConfig('roi_mode','disabled')
            
            if framerate > 70:
                self.logger.debug(f'framerate =  {framerate},disable two threshold')
                if self.det.detectorConfig('threshold/difference/mode')['value'] == "enabled":
                    self.logger.debug(f'update detector threshold/difference/ to disabled')
                    self.det.setDetectorConfig('threshold/difference/mode','disabled')
                if self.det.detectorConfig('threshold/2/mode')['value'] == "enabled":
                    self.logger.debug(f'update detector threshold/2/mode to disabled')
                    self.det.setDetectorConfig('threshold/2/mode','disabled')
            else:
                self.logger.debug(f'framerate =  {framerate},enable two threshold')
                if self.det.detectorConfig('threshold/2/mode')['value'] == "disabled":
                    self.det.setDetectorConfig('threshold/2/mode','enabled')
                if self.det.detectorConfig('threshold/difference/mode')['value'] == "disabled":    
                    self.det.setDetectorConfig('threshold/difference/mode','enabled')
            # self.det.setDetectorConfig('threshold/2/mode','enabled')
            # self.det.setDetectorConfig('threshold/difference/mode','enabled')
        self.logger.debug(f'done for setting ROI and threshold')    
        self.logger.debug(f'ask setting some basic info to detector')    

        self.x_pixels_in_detector= int(self.det.detectorConfig('x_pixels_in_detector')['value'])
        # self.logger.warning(f'ask setting some basic info to detector_1') 
        self.y_pixels_in_detector= int(self.det.detectorConfig('y_pixels_in_detector')['value'])
        # detOmega = self.oscillationRange / self.TotalFrames
        # self.logger.warning(f'ask setting some basic info to detector_2') 
        dethor = float(caget(self.Par['collect']['dethorPV']))
        # self.logger.warning(f'ask setting some basic info to detector_3') 
        detver = float(caget(self.Par['collect']['detverPV']))
        # self.logger.warning(f'ask setting some basic info to detector_4') 
        beamx = int(self.x_pixels_in_detector/2 - dethor/self.x_pixel_size/1e3)
        
        beamy = int(self.y_pixels_in_detector/2 + detver/self.y_pixel_size/1e3)
        # self.logger.debug(f'beam x center =  {self.x_pixels_in_detector/2},dethor at {}dethor')
        # self.logger.warning(f'ask setting some basic info to detector_5') 
        
        self.det.setDetectorConfig('beam_center_x',beamx)
        # self.logger.warning(f'ask setting some basic info to detector_6') 
        self.det.setDetectorConfig('beam_center_y',beamy)
        # self.logger.warning(f'ask setting some basic info to detector_7') 
        
        self.det.setDetectorConfig('detector_distance',self.distance/1000)
        # self.logger.warning(f'ask setting some basic info to detector_8') 
        self.det.setDetectorConfig('omega_start',self.oscillationStart)
        # self.logger.warning(f'ask setting some basic info to detector_9') 
        self.det.setDetectorConfig('omega_increment',self.detosc)
        # self.logger.warning(f'ask setting some basic info to detector_10') 
        try:
            chi = float(caget(self.Par['collect']['chiPV']))
            phi = float(caget(self.Par['collect']['phiPV']))
        except:
            chi = 0
            phi = 0
        # self.logger.warning(f'ask setting some basic info to detector_11') 
        self.det.setDetectorConfig('chi_start',0)
        self.det.setDetectorConfig('chi_increment',chi)
        self.det.setDetectorConfig('phi_start',phi)
        self.det.setDetectorConfig('phi_increment',0)
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
            self.det.setDetectorConfig('trigger_mode','exts')##temp
            # self.det.setDetectorConfig('nimages',1)
            # self.det.setDetectorConfig('ntrigger',self.TotalFrames)
            self.det.setDetectorConfig('nimages',int(self.rasterinfo['y']))
            self.det.setDetectorConfig('ntrigger',int(self.rasterinfo['x']))
            # self.det.setDetectorConfig('count_time',self.exposureTime-0.0000001) 
            # self.det.setDetectorConfig('frame_time',self.exposureTime)
            self.det.setDetectorConfig('count_time',self.exposureTime) 
            self.det.setDetectorConfig('frame_time',self.exposureTime)
        else:
            self.det.setDetectorConfig('trigger_mode','exts')##temp
            self.det.setDetectorConfig('nimages',self.TotalFrames)
            self.det.setDetectorConfig('ntrigger',1)
            # self.det.setDetectorConfig('count_time',self.exposureTime-0.0000001) 
            self.det.setDetectorConfig('count_time',self.exposureTime) 
            self.det.setDetectorConfig('frame_time',self.exposureTime)
        self.logger.debug(f'done for setting trigger_mode/count time')
        # text = json.dumps(header_appendix)
        # self.det.setStreamConfig('header_appendix',text)
        
        # if self.runIndex == 0:
        #     self.det.setFileWriterConfig('nimages_per_file',0)
        # else :
        #     self.det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
        self.det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
        
        # print('Detector Energy',self.Par['EPICS']['Energy']['VAL']*1000)
        Energy = float(caget(self.Par['collect']['EnergyPV']))*1000
        self.logger.debug(f'ask photon_energy')
        ans = self.det.detectorConfig('photon_energy')
        detEn= float(ans['value'])
        self.logger.debug(f'Current detector energy={detEn}')
        # print(f'Current Energy:{Energy}, Current Detector setting energy={detEn}')
        if (abs(Energy-detEn)>10):#change if more than 10v
            self.det.setDetectorConfig('photon_energy',Energy)
            self.logger.info(f'Detector origin energy={detEn},now set to {Energy}')
        
    # print("Setting frame time",cam.setDetectorConfig('frame_time',exptime),exptime)
    

        
        
        
        self.logger.debug(f'Filename =  {Filename}')
        
        self.det.setMonitorConfig('mode',"enabled")
        self.det.setFileWriterConfig('mode','enabled')
        self.det.setFileWriterConfig('name_pattern',Filename)
        self.Par['Detector']['Filename'] = Filename
        self.Par['Detector']['Fileindex'] = self.fileindex
        self.Par['Detector']['nimages'] = self.TotalFrames
        # self.logger.warning(f'TYPE:{type(self.Par)}')
        
        #update to md3
        #wait md3 ready
        self.waitMD3Ready(30)
        self.logger.info(f'update to MD3 NumberOfFramesPV')
        NumberOfFramesPV = self.Par['collect']['NumberOfFramesPV']
        caput(NumberOfFramesPV,self.TotalFrames)
        write_headerP.join()
        text = que.get()
        self.det.setStreamConfig('header_appendix',text)

        self.logger.info(f'arm detector')
        self.det.sendDetectorCommand('arm')
        self.logger.info(f'done for arm detector')
        # self.det.sendDetectorCommand('trigger')
        
        #check cryjet in?

        self.logDetInfo()
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
    
    def write_header(self,raster,Filename,que:queue.Queue):
        self.logger.debug(f'ask for asking beamline info')

        #handle ecpis on mutiprocess problem
        """
        Clears global pyepics state and fixes the CA context
        such that forked subprocesses created with multiprocessing
        can safely use pyepics.
        """
        ca.clear_cache()
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

        Ebeamcurrent = caget(self.Par['collect']['EbeamPV'])
        gap = caget(self.Par['collect']['gapPV'])
        dbpm1flux = caget(self.Par['collect']['DBPM1PV'])
        dbpm2flux = caget(self.Par['collect']['DBPM2PV'])
        dbpm3flux = caget(self.Par['collect']['DBPM3PV'])
        dbpm5flux = caget(self.Par['collect']['DBPM5PV'])
        dbpm6flux = caget(self.Par['collect']['DBPM6PV'])
        sampleflux = caget(self.Par['collect']['samplefluxPV'])
        kappa = caget(self.Par['collect']['kappaPV'])
        #tps 07a only
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
        header_appendix['atten'] = self.atten
        header_appendix['fileindex'] = self.fileindex
        header_appendix['filename'] = Filename
        # header_appendix['uid'] = getpwnam(self.userName)[2]
        # header_appendix['gid'] = getpwnam(self.userName)[3]
        header_appendix['uid'] = uidNumber
        header_appendix['gid'] = gidNumber
        header_appendix['Ebeamcurrent'] = Ebeamcurrent
        header_appendix['gap'] = gap
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
        text = json.dumps(header_appendix)
        que.put(text)
        # self.det.setStreamConfig('header_appendix',text)
        self.logger.debug(f'done for asking beamline info')
    def logDetInfo(self):
        
    
        commands = ["count_time","frame_time",'detector_distance','nimages','ntrigger',
                'number_of_excluded_pixels','photon_energy','roi_mode',
                'threshold_energy','threshold/1/energy',
                'threshold/1/mode','threshold/2/energy','threshold/2/mode',
                'threshold/difference/mode','trigger_mode','wavelength',
                'beam_center_x','beam_center_y','auto_summation',
                'bit_depth_image','bit_depth_readout','compression',
                'omega_start','omega_increment','virtual_pixel_correction_applied']
        for command in commands:
            # unit = ""
            # url = "http://{}:{}/detector/api/1.8.0/config/{}".format(ip, port,command)
            # ans = requests.get(url)
            # darray = ans.json()["value"]
            ans = self.det.detectorConfig(command)
            value = ans['value']
            try:
                unit = ans['unit']
            except :
                unit =""
            self.logger.debug(f'{command} = {value} {unit}') 
    def waitMD3Ready(self,timeout=20):
        t0 = time.time()
        check = True
        init = True
        while check:
            # md3_state = caget('07a:md3:Status ',as_string=True)
            md3_state = caget('07a:md3:State ',as_string=True)
            if md3_state== 'Ready' or md3_state== 'READY':
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
        self.logger.info(f'MD3 is Ready')     
        return True    
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
            self.logger.critical(f'closecover P has problem kill it!')
            coverprocess.kill()
            #try to close again
            self.logger.warning(f'Try to close it again!')
            closecoverP = Process(target=self.cover.askforAction,args=(action,),name='close_cover')
            closecoverP.start()
            self.checkandretryCoverProcess(closecoverP,action)
        else:
            self.logger.warning(f'OK for {action} Cover!!')
        pass
    def checkandretryDetectorSetupProcess(self,detectorprocess:Process,args,timeout =10):
        
        detectorprocess.join(timeout)
        self.logger.warning(f'Setup detector process {detectorprocess.is_alive()=},{detectorprocess.pid=},{detectorprocess.sentinel=},{detectorprocess.exitcode=}')
        if detectorprocess.exitcode== None:
            self.logger.critical(f'detector process has problem kill it!')
            detectorprocess.kill()
            #try to close again
            self.logger.warning(f'Try to close it again!')
            detectorP = Process(target=self.basesetup,args=args,name='Detector_Setup')
            detectorP.start()
            self.checkandretryCoverProcess(detectorP,args,timeout)
        else:
            self.logger.info(f'OK for detector setup')
        pass
    def recheckandretryProcess(self,beamsizeP,raster,beamwithdis):
        beamsizeP.join(60)
        if beamsizeP.exitcode == None:
            self.logger.warning(f'beamsize P has problem kill it!')
            self.logger.warning(f'beamsize process {beamsizeP.is_alive()=},{beamsizeP.pid=},{beamsizeP.sentinel=},{beamsizeP.exitcode=}')
            beamsizeP.kill()
            self.logger.warning(f'Try to go beamsize again!')
            if raster or beamwithdis:
                beamsizeP2 = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,True,),name='MoveBeamSize')
                beamsizeP2.start()
                self.recheckandretryProcess(beamsizeP2,raster,beamwithdis)
                
            else:
                #check frame rate?
                # framerate = self.TotalFrames / self.exposureTime
                # beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
                beamsizeP2 = Process(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
                beamsizeP2.start()
                self.recheckandretryProcess(beamsizeP2,raster,beamwithdis)
    #todo rcheckandretryCoverProcess
class dbpm07a():
    def __init__(self,number) -> None:
        #DBPM1sum:Mean
        #DBPM1sum:Stability
        #DBPM1x:Mean
        #DBPM1x:Stability
        #DBPM1y:Mean
        #DBPM1y:Stability
        self.number=number
        self.genname()
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
                self.dbpminfo[key][key2]['value']=caget(self.dbpminfo[key][key2]['name'])
                
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
    
def askCryojetIn(host,port):
    try:
        # host = '10.7.1.3'
        # port = 10001
        command = 'movecryojetin'
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        sendToPLCCommand(client,command)
        ans = client.recv(4096).decode()
        print(f'Robot relay:{ans}')
    except Exception as e:
        print(f'Error on askCryoJetBack : {e}')
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
