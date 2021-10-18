#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  3 14:26:34 2021

@author: blctl
"""
from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
import logsetup,time
from Eiger.DEiger2Client import DEigerClient
from epics import caput,CAProcess,caget
import json
from pwd import getpwnam
from DetectorCover import MOXA
from EPICS_special import Beamsize
from ldapclient import ladpcleint
import math

class Detector():
    def __init__(self,Par,Q) :
                
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
        self.Par = {}
        self.Par = Par
        self.sendQ = Queue()
        self.CommandQ = Queue()
        
        self.logger = logsetup.getloger2('Detector',level = self.Par['Debuglevel'])
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
        self.cover = MOXA()
        self.MoveBeamsize = Beamsize()
        self.ladp = ladpcleint()
        # self.logger.warning(f'Detector {self.CommandQ}')
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
    def __init__(self,Par,Q) :
        super().__init__(Par,Q)#get Detector att
        self.roi_mode = False
        self.trigger_mode ="ints"
        self.det = DEigerClient(self.detectorip,self.detectorport,verbose=False)
        self.det.setStreamConfig('header_detail','all')
        self.det.setStreamConfig('mode','enabled')
        
        self.x_pixels_in_detector= int(self.det.detectorConfig('x_pixels_in_detector')['value'])
        self.y_pixels_in_detector= int(self.det.detectorConfig('y_pixels_in_detector')['value'])
        self.x_pixel_size= float(self.det.detectorConfig('x_pixel_size')['value'])
        self.y_pixel_size= float(self.det.detectorConfig('y_pixel_size')['value'])

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
                
            time.sleep(0.1)
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
            time.sleep(0.1)
            currentfile = self.det.fileWriterFiles()
            
            
        #last update
        nimages = int(self.det.detectorConfig('nimages')['value'])
        ntrigger = int(self.det.detectorConfig('ntrigger')['value'])
        totalframe = nimages * ntrigger
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
    def changeBeamSize(self,command):
        #just for easy put beam size here
        beamsize = command[2]
        opid =command[1]
        #arg1 = beamsize , Targetdistance, opencover,checkdis
        #set checkdis to tru will make change distance to Targetdistance
        beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(beamsize),150,False,False),name='MoveBeamSize')
        beamsizeP.start()
        beamsizeP.join()
        self.logger.warning(f'proc {command}')
        toDcsscommand = ('operdone',) + tuple(command)
        self.sendQ.put(toDcsscommand,timeout=1)

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
        closecoverP = Process(target=self.cover.CloseCover,name='stop_close_cover')
        closecoverP.start()
        self.logger.info(f'command: {command[1:]}')
        
        currentfile = self.det.fileWriterFiles()
        self.logger.info(f'Check for detector download data: file count :{currentfile}')
        # while type(currentfile) != type(None):
        while len(currentfile) != 0:
            self.logger.info(f'wait for detector download data: file count :{currentfile}')
            time.sleep(0.1)
            currentfile = self.det.fileWriterFiles()
        self.logger.info(f'All data in detector is downloaded: file count :{currentfile}')
        
        closecoverP.join()
        toDcsscommand = ('operdone',) + tuple(command)
        self.sendQ.put(toDcsscommand,timeout=1)
        
        
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

        self.operationHandle = command[1]
        self.runIndex = int(command[2])
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
        _oscillationTime,_filename = self.basesetup()
        _filename = _filename + '.h5'
        
        
        toDcsscommand = ('operupdate',command[0],self.operationHandle,'start_oscillation','shutter',str(_oscillationTime),_filename)
        self.sendQ.put(toDcsscommand)
        # command = ('operdone',) + command
        # self.sendQ.put(command)
        
    def detector_ratser_setup(self,command):
    #    ('detector_ratser_setup', '1.24', '1', 'test_1', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000009', '1.0', '10', '750.000060', '0.976226127404', '0.000231', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '1', '10', '50.000000', '0.0')
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
        if command[20] == "1":
            self.roi = True
        else:
            self.roi = False
        self.rasterinfo={}
        self.rasterinfo['x']= int(command[21])
        self.rasterinfo['y']= int(command[22])
        #  sscanf(commandBuffer.textInBuffe
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
        
        # htos_note changing_detector_mode
        toDcsscommand = ('htos_note','changing_detector_mode')
        self.sendQ.put(toDcsscommand)
        _oscillationTime,_filename = self.basesetup(raster=True,roi=self.roi)
        _filename = _filename + '.h5'

        toDcsscommand = f"htos_operation_completed {command[0]} {self.operationHandle} normal"
        self.logger.info(f'send command to dcss: {toDcsscommand}')
        self.sendQ.put(toDcsscommand)
                

        
    def stoh_abort_all(self,command):    
        closecoverP = Process(target=self.cover.CloseCover,name='abort_close_cover')
        closecoverP.start()
        state = self.det.detectorStatus('state')
        if state == 'idle':
            pass
        elif state == 'acquire':
            self.det.sendDetectorCommand('disarm')
        elif state == 'ready':
            self.det.sendDetectorCommand('disarm')
        else:
            self.det.sendDetectorCommand('abort')
    
    def basesetup(self,raster=False,roi=False):
        t0 = time.time()

        

        
        self.logger.debug(f'TotalFrames =  {self.TotalFrames},exposureTime = {self.exposureTime} ')
        self.logger.debug(f'oscillationStart =  {self.oscillationStart},framewidth = {self.detosc}')
        self.logger.debug(f'directory =  {self.directory},filename = {self.filename},fileindex={self.fileindex}')
        self.logger.debug(f'distance =  {self.distance},wavelength = {self.wavelength},detectoroffX={self.detectoroffX},detectoroffY={self.detectoroffY},beamsize={self.beamsize},atten={self.atten}')
        self.logger.debug(f'Unknow =  {self.unknow}')
        
        # self.det.setDetectorConfig('count_time',1-0.0000001) 
        # self.det.setDetectorConfig('frame_time',1)
        


        # old open cover, now move to beamsize
        # opcoverP = Process(target=self.cover.OpenCover,name='open_cover')
        # opcoverP.start()
        
        if raster:
            beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,True,),name='MoveBeamSize')
            beamsizeP.start()
            framerate = 1 / self.exposureTime 
        else:
            #check frame rate?
            # framerate = self.TotalFrames / self.exposureTime
            beamsizeP = CAProcess(target=self.MoveBeamsize.target,args=(float(self.beamsize),self.distance ,True,False),name='MoveBeamSize')
            beamsizeP.start()
            framerate = 1 / self.exposureTime
            
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        TotalTime = self.TotalFrames * self.exposureTime
        # framerate = 75 #debug 
        #detector mode
        # roi = True
        if roi:
            if self.det.detectorConfig('roi_mode')['value'] == "disabled":
                self.logger.debug(f'set detector roi_mode from disabled to 4M')
                self.det.setDetectorConfig('roi_mode','4M')
            
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
        
        self.x_pixels_in_detector= int(self.det.detectorConfig('x_pixels_in_detector')['value'])
        self.y_pixels_in_detector= int(self.det.detectorConfig('y_pixels_in_detector')['value'])
        # detOmega = self.oscillationRange / self.TotalFrames
        dethor = float(caget(self.Par['collect']['dethorPV']))
        detver = float(caget(self.Par['collect']['detverPV']))
        beamx = int(self.x_pixels_in_detector/2 - dethor/self.x_pixel_size/1e3)
        beamy = int(self.y_pixels_in_detector/2 + detver/self.y_pixel_size/1e3)
        # self.logger.debug(f'beam x center =  {self.x_pixels_in_detector/2},dethor at {}dethor')
        
        
        self.det.setDetectorConfig('beam_center_x',beamx)
        self.det.setDetectorConfig('beam_center_y',beamy)
        self.det.setDetectorConfig('detector_distance',self.distance/1000)
        self.det.setDetectorConfig('omega_start',self.oscillationStart)
        self.det.setDetectorConfig('omega_increment',self.detosc)
        self.det.setDetectorConfig('chi_start',0)
        self.det.setDetectorConfig('chi_increment',0)
        self.det.setDetectorConfig('phi_start',0)
        self.det.setDetectorConfig('phi_increment',0)
        
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
        if raster:
            header_appendix['raster_X']=self.rasterinfo['x']
            header_appendix['raster_Y']=self.rasterinfo['y']
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
        
        text = json.dumps(header_appendix)
        self.det.setStreamConfig('header_appendix',text)
        
        # if self.runIndex == 0:
        #     self.det.setFileWriterConfig('nimages_per_file',0)
        # else :
        #     self.det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
        self.det.setFileWriterConfig('nimages_per_file',int(self.Par['Detector']['nimages_per_file']))
        
        # print('Detector Energy',self.Par['EPICS']['Energy']['VAL']*1000)
        Energy = float(caget(self.Par['collect']['EnergyPV']))*1000
        ans = self.det.detectorConfig('photon_energy')
        detEn= float(ans['value'])
        print(f'Current Energy:{Energy}, Current Detector setting energy={detEn}')
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
        NumberOfFramesPV = self.Par['collect']['NumberOfFramesPV']
        caput(NumberOfFramesPV,self.TotalFrames)
        
        self.det.sendDetectorCommand('arm')
        # self.det.sendDetectorCommand('trigger')
        
        
        self.logDetInfo()
        # self.cover.wait_for_state(wait='open',timeout=3)
        beamsizeP.join()
        t1 = time.time()
        self.logger.info('start to check')
        monP = Process(target=self.updatefilestring,name='Monfile')
        monP.start()
        self.logger.debug(f'setup time = {t1-t0},Detector energy={Energy}')
        return TotalTime,Filename
    
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
        
if __name__ == "__main__":
    import Config
    Par = Config.Par
    #setup for Queue
    Q={'Queue':{}}
    Q['Queue']['reciveQ'] = Queue() 
    Q['Queue']['sendQ'] = Queue() 
    Q['Queue']['epicsQ'] = Queue()
    Q['Queue']['ControlQ'] = Queue()
    Q['Queue']['DetectorQ'] = Queue()
    test = Eiger2X16M(Par,Q)
    p = Process(target=test.CommandMon)
    p.start()
    
    # print(test.detectorip)
    # print(test.Par)
    # Q['Queue']['DetectorQ'].put(('test','1234'))
    Q['Queue']['DetectorQ'].put(('detector_collect_image','213'))
    # Q['Queue']['DetectorQ'].put(('test2','21333'))
    Q['Queue']['DetectorQ'].put(('detector_collect_imageHS','21333'))
    Q['Queue']['DetectorQ'].put('exit')
