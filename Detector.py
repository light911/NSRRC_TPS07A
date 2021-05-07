#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  3 14:26:34 2021

@author: blctl
"""
from multiprocessing import Process, Queue, Manager
import logsetup
from Eiger.DEiger2Client import DEigerClient

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
        
        self.detectorip = self.Par['Detector']['ip']
        self.detectorport = self.Par['Detector']['port']
        
        self.logger = logsetup.getloger2('DetectorDHS',level = self.Par['Debuglevel'])
        
        self.epicsQ = Q['Queue']['epicsQ']
        self.reciveQ = Q['Queue']['reciveQ']
        self.sendQ = Q['Queue']['sendQ']
        self.CommandQ = Q['Queue']['DetectorQ']
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
        try:
            getattr(self,command[0])(command)#ex.detector_collect_image
        except :
                self.logger.warning(f'unknow command for detector DHS: {command[0]}')
                self.logger.info(f'Full unknow command : {command}')


    #update each operation for diffenert detector    
    def detector_collect_image(self,command):
        # self.logger.info(f'Default action for {command[0]}:{command[1:]}')
        self.logger.info(f'command: {command[1:]}')
    def detector_collect_shutterless(self,command):
        #['stoh_start_operation', 'detector_collect_shutterless', '1.2', '0', 'test_0', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000000', '1.0', '1', '750.000080', '0.976226127404', '0.000071', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '3', '1', '50.000000', '0.0']
        # command: ('1.2', '0', 'test_0', '/data/blctl/test', 'blctl', 'gonio_phi', '0.1', '0.000009', '1.0', '1', '750.000240', '0.976226127404', '0.000187', '50.000000', '0', '0', 'PRIVATEA03F6ADA6F19A8DA1DEE6BFC325F4DCE', '9', '1', '50.000000', '0.0

        operationHandle = command[1]
        runIndex = int(command[1])
        filename = command[2]
        directory = command[3]
        userName = command[4]
        axisName = command[5]
        exposureTime = float(command[6])
        oscillationStart = float(command[7])
        oscillationRange =  float(command[8])
        distance = float(command[8])
        wavelength = float(command[9])
        detectoroffX = float(command[10])
        detectoroffY = float(command[11])
        sessionId = command[12]
        fileindex = int(command[12])
        adv = command[13] #1
        beamstopZ = command[14] # 50
        adf= command[15] #0
         
        # detectorMode = command[11]
        # reuseDark = command[12]
        sessionId = command[12]
        numberFrames = 0
        #  sscanf(commandBuffer.textInBuffe
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
    #add detector opration here
    def detector_collect_image(self,command):
        operationHandle = command[1]
        runIndex = command[1]
        filename = command[2]
        directory = command[3]
        userName = command[4]
        axisName = command[5]
        exposureTime = float(command[6])
        oscillationStart = float(command[7])
        oscillationRange =  float(command[8])
        distance = float(command[8])
        wavelength = float(command[9])
        detectorX = float(command[10])
        detectorY = float(command[11])
        detectorMode = command[11]
        reuseDark = command[12]
        sessionId = command[13]
        numberFrames = 0
        #  sscanf(commandBuffer.textInBuffer,
        # "%*s %20s %d %s %s %s %s %lf %lf %lf %lf %lf %lf %lf %d %d %s",
        # frame.operationHandle,
        # &frame.runIndex,
        # frame.filename,
        # frame.directory,
        # frame.userName,
        # frame.axisName,
        # &frame.exposureTime,
        # &frame.oscillationStart,
        # &frame.oscillationRange,
        # &frame.distance,
        # &frame.wavelength,
        # &frame.detectorX,
        # &frame.detectorY,
        # &frame.detectorMode,
        # &reuseDark,
        # frame.sessionId );
        # frame.numberFrames = 0;

        op_name = command[0]
        self.logger.info(f'command: {command[1:]}')
        pass
    
        
 # sscanf(commandBuffer.textInBuffer,
 #                       "%*s %20s %d %s %s %s %s %lf %lf %lf %lf %lf %lf %lf %d %d %s %lf %lf",
 #                       frame.operationHandle,
 #                       &frame.runIndex,
 #                       frame.filename,
 #                       frame.directory,
 #                       frame.userName,
 #                       frame.axisName,
 #                       &frame.exposureTime,
 #                       &frame.oscillationStart,
 #                       &frame.oscillationRange,
 #                       &frame.distance,
 #                       &frame.wavelength,
 #                       &frame.detectorX,
 #                       &frame.detectorY,
 #                       &frame.detectorMode,
 #                       &reuseDark,
 #                       frame.sessionId,
 #                       &frame.beamSize,
 #                       &frame.attn );
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
