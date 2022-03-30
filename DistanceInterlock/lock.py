#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  9 09:49:11 2021

@author: blctl
"""
import logging,sys,signal,time,os
#Logsetup should in root folder
#add export PYTHONPATH=/home/blctl/Desktop/NAS/Eddie/TPS07A/EpicsDHS:$PYTHONPATH
import logsetup
from multiprocessing import Process, Queue , Manager

from epicsinit import epicsdev
import Config
import EpicsConfig
from epics import caput,CAProcess

class DistanceInterlock():
     def __init__(self):
         # signal.signal(signal.SIGINT, quit)
         # signal.signal(signal.SIGTERM, quit)
         m = Manager()
         self.Par = m.dict()
         self.Par = Config.Par
         
         # if self.Par['Debug']:
         #     debuglevel = "DEBUG"
             
         # else :
         #     debuglevel = "INFO"
         
         self.Par['DetYmoving'] = False #True to ignore DetY setting request
         self.Par['MD3Ymoving'] = False #True to ignore MD3Y setting request
         self.Par['BSmoving'] = False #True to ignore BS setting request
         self.logger = logsetup.getloger2('DistanceInterlock',level =  self.Par['Debuglevel'])
         self.logger.info("init DistanceInterlock logging")
         self.logger.info("Logging show level = %s",self.Par['Debuglevel'])
         self.logger.debug("Par Start=======")
         self.logger.debug(self.Par)
         self.logger.debug("Par End========")
         
         self.initEPICS()
         # self.calDistance()

     def initEPICS(self):
         self.logger.info("register Epics Monitor item")
         self.epics = epicsdev(EpicsConfig.epicslist,self.Par)
         self.epics.register_observer(self)
         self.epics.setcallback()
         
     def calDistance(self):
         
         DetectorDistance = self.Par['EPICS']['DetY_RBV'] - self.Par['EPICS']['MD3Y_RBV'] + self.Par['EPICS']['DistanceOFF'] 
         caput(self.Par['fakedistancename'],DetectorDistance)
         p = CAProcess(target=self.epicsput, args=(self.Par['fakedistancename'],DetectorDistance,))
         # p = CAProcess(target=self.epicsput, args=({self.Par['fakedistancename']:DetectorDistance},))
         p.start()
         self.logger.debug(f"DetY:{self.Par['EPICS']['DetY_RBV']} ,MD3Y:{self.Par['EPICS']['MD3Y_RBV']} , DisOFF:{self.Par['EPICS']['DistanceOFF']}")
         self.logger.debug(f"Distance change to {DetectorDistance}")
         

     def notify(self, observable, *args, **kwargs):
         self.logger.debug("notify PID:%d",os.getpid())
         # self.logger.debug('Got %s %s', args, kwargs, 'From %s', observable)
         self.logger.debug(f'Got {args} {kwargs}')
         self.logger.debug(f'Current par {self.Par}')
         if args[0] == "UpdateDistance" :
             # self.calDistance()
             pass
         elif args[0] == "ChangeMD3Y" :
             #After moving should reset DetY limits
             self.logger.warning(f'got command: {args[0]}, arg:{args[1]}')
             self.logger.warning(f"MD3Y: {self.Par['EPICS']['MD3Y']}, MD3YRBV: {self.Par['EPICS']['MD3Y_RBV']}")
             # self.ChangeMD3Y()
             
         elif args[0] == "ChangeDetY" :
             #After moving should reset MD3Y limits
             self.logger.warning(f'got command: {args[0]}, arg:{args[1]}')
             self.logger.warning(f"DetY: {self.Par['EPICS']['DetY']}, MD3YRBV: {self.Par['EPICS']['DetY_RBV']}")
         elif args[0] == "ChangeBeamsize" :
             #TODO
             self.logger.warning(f'got command: {args[0]}, arg:{args[1]}')   
         elif args[0] == "ChangeMD3BS" :
             #not thing should do
             self.logger.warning(f'got command: {args[0]}, arg:{args[1]}')
         elif args[0] == "ChangeDetectorDistance" :
             #TODO
             self.logger.warning(f'got command: {args[0]}, arg:{args[1]}')
         else:
             self.logger.error(f'Unknow command: {args[0]}')
     # def ChangeMD3Y(self)
         # 07a:MD3:Y.DMOV
     def epicsput(self, *args, **kwargs):
         self.logger.debug(f'epicsput PID: {os.getpid()}')
         self.logger.debug(f'Got {args} {kwargs}')
         caput(args[0],args[1])
         
     def quit(self,signum,frame):
         self.logger.info("DistanceInterlock class Exit")
         self.logger.info("Par %s",self.Par)
         self.epics.clear_epics_callback()


def quit(signum,frame):
    print("Main cloesd")
    a.quit(signum,frame)
    sys.exit()
    pass                
         
         
if __name__ == "__main__":
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    logger=logsetup.getloger2('Main')
    # logger = logging.getLogger('Main')
    # logger.setLevel('DEBUG')
    # logger.addHandler(fh)
    # logger.addHandler(ch)
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    a = DistanceInterlock()
    while True:
        time.sleep(0.1)
        pass

    # print(logger.hasHandlers)
    pass