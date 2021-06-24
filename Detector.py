#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  3 14:26:34 2021

@author: blctl
"""
from multiprocessing import Process, Queue, Manager
import logsetup,time
from Eiger.DEiger2Client import DEigerClient
from epics import caput,CAProcess,caget
import json
from pwd import getpwnam

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
    def stoh_abort_all(self,command):
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
        
    #add detector opration here
    
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
        
    def stoh_abort_all(self,command):    
        state = self.det.detectorStatus('state')
        if state == 'idle':
            pass
        elif state == 'acquire':
            self.det.sendDetectorCommand('disarm')
        else:
            self.det.sendDetectorCommand('abort')
    
    def basesetup(self):
        t0 = time.time()
        
        
        
        self.logger.debug(f'TotalFrames =  {self.TotalFrames},exposureTime = {self.exposureTime} ')
        self.logger.debug(f'oscillationStart =  {self.oscillationStart},framewidth = {self.detosc}')
        self.logger.debug(f'directory =  {self.directory},filename = {self.filename},fileindex={self.fileindex}')
        self.logger.debug(f'distance =  {self.distance},wavelength = {self.wavelength},detectoroffX={self.detectoroffX},detectoroffY={self.detectoroffY},beamsize={self.beamsize},atten={self.atten}')
        self.logger.debug(f'Unknow =  {self.unknow}')
        
        # detOmega = self.oscillationRange / self.TotalFrames
        dethor = float(caget(self.Par['collect']['dethorPV']))
        detver = float(caget(self.Par['collect']['detverPV']))
        beamx = int(self.x_pixels_in_detector/2 - dethor/self.x_pixel_size/1e3)
        beamy = int(self.y_pixels_in_detector/2 + detver/self.y_pixel_size/1e3)
        # self.logger.debug(f'beam x center =  {self.x_pixels_in_detector/2},dethor at {}dethor')
        
        
        self.det.setDetectorConfig('beam_center_x',beamx)
        self.det.setDetectorConfig('beam_center_y',beamy)
        self.det.setDetectorConfig('detector_distance',self.distance)
        self.det.setDetectorConfig('omega_start',self.oscillationStart)
        self.det.setDetectorConfig('omega_increment',self.detosc)
        self.det.setDetectorConfig('chi_start',0)
        self.det.setDetectorConfig('chi_increment',0)
        self.det.setDetectorConfig('phi_start',0)
        self.det.setDetectorConfig('phi_increment',0)
        self.det.setDetectorConfig('nimages',self.TotalFrames)
        self.det.setDetectorConfig('trigger_mode','exts')##temp
        
        #check frame rate?
        framerate = self.TotalFrames / self.exposureTime
        
        Filename = self.filename + "_" + str(self.fileindex).zfill(4)
        TotalTime = self.TotalFrames * self.exposureTime
        
        #detector mode
        
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
        
        header_appendix ={}
        header_appendix['user'] = self.userName
        header_appendix['directory'] = self.directory
        header_appendix['runIndex'] = self.runIndex
        header_appendix['beamsize'] = self.beamsize
        header_appendix['atten'] = self.atten
        header_appendix['fileindex'] = self.fileindex
        header_appendix['filename'] = Filename
        header_appendix['uid'] = getpwnam(self.userName)[2]
        header_appendix['gid'] = getpwnam(self.userName)[3]
        text = json.dumps(header_appendix)
        self.det.setStreamConfig('header_appendix',text)
        
        if self.runIndex == 0:
            self.det.setFileWriterConfig('nimages_per_file',0)
        else :
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
    
        self.det.setDetectorConfig('count_time',self.exposureTime-0.0000001) 
        self.det.setDetectorConfig('frame_time',self.exposureTime)
        
        
        
        self.logger.debug(f'Filename =  {Filename}')
        
        self.det.setMonitorConfig('mode',"enabled")
        self.det.setFileWriterConfig('mode','enabled')
        self.det.setFileWriterConfig('name_pattern',Filename)
        self.Par['Detector']['Filename'] = Filename
        self.Par['Detector']['Fileindex'] = self.fileindex
        self.Par['Detector']['nimages'] = self.TotalFrames
        self.logger.warning(f'TYPE:{type(self.Par)}')
        
        NumberOfFramesPV = self.Par['collect']['NumberOfFramesPV']
        caput(NumberOfFramesPV,self.TotalFrames)
        
        self.det.sendDetectorCommand('arm')
        # self.det.sendDetectorCommand('trigger')
        
        
        self.logDetInfo()
        t1 = time.time()
        
        self.logger.debug(f'setup time = {t1-t0},Detector energy={Energy}')
        return TotalTime,Filename
    
    def logDetInfo(self):
        
    
        commands = ["count_time","frame_time",'detector_distance','nimages',
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
