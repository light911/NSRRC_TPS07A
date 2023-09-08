#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 16:46:13 2020

@author: admin
"""

from epics import caget
from workround import myepics
# from epics import caget,caput
import socket,time,signal,sys,os,copy,subprocess
# import multiprocessing as mp
from multiprocessing import Process, Queue, Manager
from epicsinit import epicsdev
import logsetup,requests
# import epicsfile
import Config
import EpicsConfig
import numpy as np
# from DetectorCoverV2 import MOXA

class Beamsize():
    def __init__(self,coverdhs,managerpar=None) :
#        super(self.__class__,self).__init__(parent)
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        #load config
        if managerpar == None:
            m = Manager()
            self.Par = m.dict()
            
        else:
            self.Par = managerpar
        
        self.Par.update(Config.Par)
        
        # self.Par['Queue']={}
        # self.Par.update({'Queue':{}})
        # print(f'TYPE:{type(self.Par)}')
        #set log
        self.logger = logsetup.getloger2('BeamSize',LOG_FILENAME='./log/Beamsize.txt',level = self.Par['Debuglevel'])
        self.logger.info("init BeamSize logging")
        self.logger.info("Logging show level = %s",self.Par['Debuglevel'])
        # self.logger.debug("Par Start=======")
        # self.logger.debug(self.Par)
        # self.logger.debug(f'TYPE:{type(self.Par)}')
        # self.logger.debug("Par End========")

        self.ca = myepics(self.logger)
        #
        
        #setup Beamsize par
        
        #list EPICS name
        self.MD3VerUsing = self.Par['EPICS_special']['BeamSize']['using']['MD3Ver']
        self.MD3HorUsing = self.Par['EPICS_special']['BeamSize']['using']['MD3Hor']
        self.Slit4VerOPUsing = self.Par['EPICS_special']['BeamSize']['using']['Slit4VerOP']
        self.Slit4HorOPUsing = self.Par['EPICS_special']['BeamSize']['using']['Slit4HorOP']
        self.DBPM5VerUsing = self.Par['EPICS_special']['BeamSize']['using']['DBPM5Ver']
        self.DBPM5HorUsing = self.Par['EPICS_special']['BeamSize']['using']['DBPM5Hor']
        self.DBPM6VerUsing = self.Par['EPICS_special']['BeamSize']['using']['DBPM6Ver']
        self.DBPM6HorUsing = self.Par['EPICS_special']['BeamSize']['using']['DBPM6Hor']
        self.SSUsing =  self.Par['EPICS_special']['BeamSize']['using']['SS']
        self.ApertureUsing = self.Par['EPICS_special']['BeamSize']['using']['Aperture']
        
        self.BeamSizeName = self.Par['EPICS_special']['BeamSize']['BeamSizeName']
        self.MD3YName = self.Par['EPICS_special']['BeamSize']['MD3YName']
        self.MD3VerName = self.Par['EPICS_special']['BeamSize']['MD3VerName']
        self.MD3HorName = self.Par['EPICS_special']['BeamSize']['MD3HorName']
        self.Slit4VerOPName = self.Par['EPICS_special']['BeamSize']['Slit4VerOPName']
        self.Slit4HorOPName = self.Par['EPICS_special']['BeamSize']['Slit4HorOPName']
        self.DBPM5VerName = self.Par['EPICS_special']['BeamSize']['DBPM5VerName']
        self.DBPM5HorName = self.Par['EPICS_special']['BeamSize']['DBPM5HorName']
        self.DBPM6VerName = self.Par['EPICS_special']['BeamSize']['DBPM6VerName']
        self.DBPM6HorName = self.Par['EPICS_special']['BeamSize']['DBPM6HorName']
        self.SSName = self.Par['EPICS_special']['BeamSize']['SSName']
        self.fakeDistanceName = self.Par['fakedistancename']
        self.ApertureName = self.Par['EPICS_special']['BeamSize']['ApertureName']
        self.DBPM6kxName = self.Par['EPICS_special']['BeamSize']['DBPM6kxName']
        self.DBPM6kyName = self.Par['EPICS_special']['BeamSize']['DBPM6kyName']
        
        self.MD3YMotor = self.Par['EPICS_special']['BeamSize']['MD3YMotor']
        self.MD3VerMotor = self.Par['EPICS_special']['BeamSize']['MD3VerMotor']
        self.MD3HorMotor = self.Par['EPICS_special']['BeamSize']['MD3HorMotor']
        self.Slit4VerOPMotor = self.Par['EPICS_special']['BeamSize']['Slit4VerOPMotor']
        self.Slit4HorOPMotor = self.Par['EPICS_special']['BeamSize']['Slit4HorOPMotor']
        self.DBPM5VerMotor = self.Par['EPICS_special']['BeamSize']['DBPM5VerMotor']
        self.DBPM5HorMotor = self.Par['EPICS_special']['BeamSize']['DBPM5HorMotor']
        self.DBPM6VerMotor = self.Par['EPICS_special']['BeamSize']['DBPM6VerMotor']
        self.DBPM6HorMotor = self.Par['EPICS_special']['BeamSize']['DBPM6HorMotor']
        self.SSMotor = self.Par['EPICS_special']['BeamSize']['SSMotor']
        self.DetYMotor = self.Par['EPICS_special']['BeamSize']['DetYMotor']
        self.ApertureMotor = self.Par['EPICS_special']['BeamSize']['ApertureMotor']
        self.DBPM6kxfactor = self.Par['EPICS_special']['BeamSize']['DBPM6kxfactor']
        self.DBPM6kyfactor = self.Par['EPICS_special']['BeamSize']['DBPM6kyfactor']
        
        self.MinDistance = self.Par['MinDistance']
        
        self.BeamSizeLists = []
        self.MD3YLists = []
        self.MD3VerLists = []
        self.MD3HorLists = []
        self.Slit4VerOPLists = []
        self.Slit4HorOPLists = []
        self.DBPM5VerLists = []
        self.DBPM5HorrLists = []
        self.DBPM6VerLists = []
        self.DBPM6HorLists = []
        self.SSLists = []
        self.ApertureLists = []

        self.DBPM6kxLists = []
        self.DBPM6kyLists = []
        #setup Feedback par
        self.FeedbackDCM = ''
        self.FeedbackHFM = ''
        self.FeedbackVFM = ''
        
        #other Info
        self.CurrentBeamsize = 0
        self.CurrentDetY = 0
        self.CurrentMD3Y = 0
        
        # self.epicsmotors = EpicsConfig.epicsmotors
        #update info
        self.updateINFO()
        self.Busy = False
        # self.cover = MOXA()
        self.cover = coverdhs

    

    def updateINFO(self):
        self.BeamSizeLists = self.ca.caget(self.BeamSizeName,format=float,array=True,debug=False)
        self.logger.debug(f'Update BeamSizeLists = {self.BeamSizeLists}')
        self.MD3YLists = self.ca.caget(self.MD3YName,format=float,array=True,debug=False)
        self.logger.debug(f'Update MD3YLists = {self.MD3YLists}')
        if self.SSUsing :
            self.SSLists =self.ca.caget(self.SSName,format=float,array=True,debug=False)
            self.logger.debug(f'Update SSLists = {self.SSLists}')
        if self.MD3VerUsing :
            self.MD3VerLists =self.ca.caget(self.MD3VerName,format=float,array=True,debug=False)
            self.logger.debug(f'Update MD3VerLists = {self.MD3VerLists}')
        if self.MD3HorUsing :
            self.MD3HorLists =self.ca.caget(self.MD3HorName,format=float,array=True,debug=False)
            self.logger.debug(f'Update MD3HorLists = {self.MD3HorLists}')
        if self.Slit4VerOPUsing :
            self.Slit4VerOPLists =self.ca.caget(self.Slit4VerOPName,format=float,array=True,debug=False)
            self.logger.debug(f'Update Slit4VerOPLists = {self.Slit4VerOPLists}')
        if self.Slit4HorOPUsing :
            self.Slit4HorOPLists =self.ca.caget(self.Slit4HorOPName,format=float,array=True,debug=False)
            self.logger.debug(f'Update Slit4HorOPLists = {self.Slit4HorOPLists}')
        if self.DBPM5VerUsing :
            self.DBPM5VerLists =self.ca.caget(self.DBPM5VerName,format=float,array=True,debug=False)
            self.logger.debug(f'Update DBPM5VerLists = {self.DBPM5VerLists}')
        if self.DBPM5HorUsing :
            self.DBPM5HorLists =self.ca.caget(self.DBPM5HorName,format=float,array=True,debug=False)
            self.logger.debug(f'Update DBPM5HorLists = {self.DBPM5HorLists}')
        if self.DBPM6VerUsing :
            self.DBPM6VerLists =self.ca.caget(self.DBPM6VerName,format=float,array=True,debug=False)
            self.logger.debug(f'Update DBPM6VerLists = {self.DBPM6VerLists}')
        if self.DBPM6HorUsing :
            self.DBPM5VerLists =self.ca.caget(self.DBPM6HorName,format=float,array=True,debug=False)
            self.logger.debug(f'Update DBPM5VerLists = {self.DBPM5VerLists}')
        if self.ApertureUsing :
            self.ApertureLists = self.ca.caget(self.ApertureName,format=int,array=True,debug=False)
            self.logger.debug(f'Update ApertureLists = {self.ApertureLists}')
        self.DBPM6kxLists =self.ca.caget(self.DBPM6kxName,format=float,array=True,debug=False)
        self.DBPM6kyLists =self.ca.caget(self.DBPM6kyName,format=float,array=True,debug=False)
        # self.CurrentBeamsize = 0
        self.CurrentDetY = self.ca.caget(self.DetYMotor,format=float,array=False,debug=False)
        self.logger.debug(f'Update CurrentDetY = {self.CurrentDetY}')
        self.CurrentMD3Y = self.ca.caget(self.MD3YMotor,format=float,array=False,debug=False)
        self.logger.debug(f'Update MD3YMotor = {self.CurrentMD3Y}')
    def report_current_beamsize(self):
        self.updateINFO()
        MD3YLists = self.MD3YLists.tolist()
        # MD3YLists = self.MD3YLists
        try:
            index = MD3YLists.index(int(self.CurrentMD3Y))
            beamsize = self.BeamSizeLists[index]
        except ValueError:
            self.logger.warn(f'MD3Y at :{self.CurrentMD3Y},not in list')
            self.logger.warn(f'i will replay beamsize 10 frist')
            beamsize = 10
        return beamsize
    def target(self,beamsize=50,Targetdistance=150,opencover=False,checkdis=False):
        self.Busy = True
        
        self.logger.info(f'Move beam size to {beamsize} with openvoer = {opencover},Targetdistance = {Targetdistance} with moveit = {checkdis}')
        requests.post(f'http://10.7.1.105/ptzpreset?camid=1&goto_preset={int(beamsize)}')
        current_dis = self.ca.caget(self.fakeDistanceName)
        #07a:Det:Dis.LLM,07a:Det:Dis.HLM
        disLLM = self.ca.caget(f'{self.fakeDistanceName}.LLM')
        disHLM = self.ca.caget(f'{self.fakeDistanceName}.HLM')
        if disLLM > Targetdistance:
            Targetdistance = disLLM
            self.logger.warning(f'Request distance :{Targetdistance} is lower than {disLLM},set to lowerest value')
        elif disHLM < Targetdistance:
            Targetdistance = disHLM
            self.logger.warning(f'Request distance :{Targetdistance} is higher than {disHLM},set to higest value')
        
        if beamsize == self.CurrentBeamsize and ((current_dis-Targetdistance <1) or not checkdis ):
            self.logger.debug(f'Asked for same beamsize ,not move(Current beamsize = {self.CurrentBeamsize})')
            self.opencover(opencover)
            self.wait_opencover(opencover)
        else:
            self.updateINFO()
            if beamsize in self.BeamSizeLists :
                index = np.where( self.BeamSizeLists == beamsize )[0][0]
                # print(type(index))
                movinglist = {}
                md3movinglist ={}
                self.logger.debug(f'Beam size : {beamsize} is in beam list index = {index}')
                
                movinglist[self.MD3YMotor] = self.MD3YLists[index]
                if self.SSUsing :
                    movinglist[self.SSMotor] = self.SSLists[index]
                if self.MD3VerUsing :
                    movinglist[self.MD3VerMotor] = self.MD3VerLists[index]
                if self.MD3HorUsing :
                    movinglist[self.MD3HorMotor] = self.MD3HorLists[index]
                if self.ApertureUsing :
                    # movinglist[self.ApertureMotor] = self.ApertureLists[index]
                    # md3movinglist[self.ApertureMotor] = self.ApertureLists[index]
                    #just move to pos
                    self.ca.caput(self.ApertureMotor,self.ApertureLists[index],int)

                if self.Slit4VerOPUsing :
                    movinglist[self.Slit4VerOPMotor] = self.Slit4VerOPLists[index]
                if self.Slit4HorOPUsing :
                    movinglist[self.Slit4HorOPMotor] = self.Slit4HorOPLists[index]
                if self.DBPM5VerUsing :
                    movinglist[self.DBPM5VerMotor] = self.DBPM5VerLists[index]
                if self.DBPM5HorUsing :
                    movinglist[self.DBPM5HorMotor] = self.DBPM5HorLists[index]
                if self.DBPM6VerUsing :
                    movinglist[self.DBPM6VerMotor] = self.DBPM6VerLists[index]                  
                if self.DBPM6HorUsing :
                    movinglist[self.DBPM6HorMotor] = self.DBPM6HorLists[index]
                self.logger.debug(f'movinglist = {movinglist}')
                
                #check MD3Y and DetY moving range
                detMove = movinglist[self.MD3YMotor] - self.CurrentMD3Y 
                self.logger.debug(f'detMove = {detMove}')        
                #check if safe to move both?
                #check DetY
                #case1 lower than DetYLLM,case2 lower than MinDistance in cinfig, case3 lower than 40mm (impossbilie)
                DetYLLM =  self.ca.caget(self.DetYMotor + ".LLM")
                if checkdis:
                    detDist = current_dis - Targetdistance
                    targetDetY = (self.CurrentDetY + detMove) - detDist
                else:
                    targetDetY = (self.CurrentDetY + detMove)
                # collisionDetY = targetDetY < DetYLLM or targetDetY < 40 or targetDetY < self.MinDistance
                collisionDetY = targetDetY < DetYLLM or targetDetY < 40 
                #check MD3Y
                MD3YHLM =  self.ca.caget(self.MD3YMotor + ".HLM")
                targetMD3Y = movinglist[self.MD3YMotor]
                collisionMD3Y = targetMD3Y > MD3YHLM
                self.logger.debug(f'CurrentDetY = {self.CurrentDetY}, DetYLLM = {DetYLLM},will move to {targetDetY} , will collisionDetY ={collisionDetY}') 
                self.logger.debug(f'CurrentMD3Y = {self.CurrentMD3Y}, MD3YHLM = {MD3YHLM},will move to {targetMD3Y} , will collisionMD3Y ={collisionMD3Y}') 
                MoveTogether = not collisionMD3Y and not collisionDetY
                self.logger.info(f'MoveTogether = {MoveTogether},since collisionMD3Y= {collisionMD3Y}, collisionDetY={collisionDetY}') 
                detDisMove = targetDetY - self.CurrentDetY
                #modify
                movinglist[self.DetYMotor] = targetDetY
                tempmovinglist = copy.deepcopy(movinglist)# allmotor
                

                if -0.005 < detMove < 0.005 and -0.1 < detDisMove < 0.1:
                    #no move
                    self.logger.info(f'Target MD3Y is the too closed to Current MD3Y value,nothing move')
                    self.opencover(opencover)
                    self.wait_opencover(opencover)
                    pass
                elif detMove < 0 and not MoveTogether:
                    #MD3Y move forward, move MD3Y Frist
                    self.logger.info(f'Moving MD3Y Frist! pervent collision') 
                    self.logger.debug(f'Set {self.MD3YMotor} move to {movinglist[self.MD3YMotor]}') 
                    t1 = time.time()
                    self.ca.caput(self.MD3YMotor,movinglist[self.MD3YMotor])
                    del movinglist[self.MD3YMotor]
                    
                    #wait for 5 sec md3 start move
                    self.logger.info('sleep for 3sec wait md3y move frist')
                    time.sleep(3)
                    self.logger.info('start to move rest motor') 
                    # while not self.check_allmotorstop([self.MD3YMotor]):
                    #     time.sleep(0.1)
                    # self.logger.info(f'Moving MD3Y Done! Start move other motor') 


                    #wait for limtes update
                    # time.sleep(0.2)


                    #need recheck collision,in case motor stop by abort
                    for motor in movinglist :
                        self.logger.debug(f'Set {motor} move to {movinglist[motor]}') 
                        self.ca.caput(motor,movinglist[motor])
                    time.sleep(0.1)    

                    #check all stop
                    # while not self.check_allmotorstop(movinglist.keys()):
                    #     time.sleep(0.1)
                    while not self.check_allmotorstop(tempmovinglist.keys()):
                        time.sleep(0.1)

                    self.opencover(opencover)
                    self.wait_opencover(opencover)
                    runtime = time.time() - t1
                    self.logger.info(f'Moving All MOTOR Done,take {runtime}sec') 
                elif detMove >0 and not MoveTogether:
                    #MD3Y move back, move DetY Frist
                    self.logger.info(f'Moving DetY Frist! pervent collision') 
                    self.logger.debug(f'Set {self.DetYMotor} move to {movinglist[self.DetYMotor]}') 
                    t1 = time.time()
                    

                    self.ca.caput(self.DetYMotor,movinglist[self.DetYMotor])
                    del movinglist[self.DetYMotor]

                    #wait for 5 sec dety start move
                    self.logger.info('sleep for 3sec wait dety move frist')
                    time.sleep(3)
                    self.logger.info('start to move rest motor') 

                    # while not self.check_allmotorstop([self.DetYMotor]):
                    #     time.sleep(0.1)
                    # self.logger.info(f'Moving DetY Done! Start move other motor') 

                    #wait for limtes update
                    # time.sleep(0.2)

                    #need recheck collision ,in case motor stop by abort
                    for motor in movinglist :
                        self.logger.debug(f'Set {motor} move to {movinglist[motor]}') 
                        print(self.ca.caput(motor,movinglist[motor]))
                    time.sleep(0.1)    

                    #check all stop
                    # while not self.check_allmotorstop(movinglist.keys()):
                    #     time.sleep(0.1)
                    while not self.check_allmotorstop(tempmovinglist.keys()):
                        time.sleep(0.1)
                    self.opencover(opencover)
                    self.wait_opencover(opencover)
                    runtime = time.time() - t1
                    self.logger.info(f'Moving All MOTOR Done,take {runtime}sec') 
                    pass
                elif MoveTogether and detMove != 0:
                    self.logger.info(f'Moving All MOTOR at the same time') 
                    self.opencover(opencover)
                    # movejob = movinglist
                    movinglist[self.DetYMotor] = targetDetY
                    # print(self.CurrentDetY + detMove)
                    t1 = time.time()
                    for motor in movinglist :
                        self.logger.debug(f'Set {motor} move to {movinglist[motor]}') 
                        print(self.ca.caput(motor,movinglist[motor]))
                    time.sleep(0.1)
                    while not self.check_allmotorstop(movinglist.keys()):
                        time.sleep(0.1)
                    self.wait_opencover(opencover)
                    runtime = time.time() - t1
                    self.logger.info(f'Moving All MOTOR Done,take {runtime}sec')
                elif MoveTogether and detMove == 0:
                    self.logger.info(f'Moving det MOTOR only') 
                    self.opencover(opencover)
                    # movejob = movinglist
                    del movinglist[self.MD3YMotor]
                    movinglist[self.DetYMotor] = targetDetY
                    # print(self.CurrentDetY + detMove)
                    t1 = time.time()
                    for motor in movinglist :
                        self.logger.debug(f'Set {motor} move to {movinglist[motor]}') 
                        print(self.ca.caput(motor,movinglist[motor]))
                    time.sleep(0.1)
                    while not self.check_allmotorstop(movinglist.keys()):
                        time.sleep(0.1)
                    self.wait_opencover(opencover)
                    runtime = time.time() - t1
                    self.logger.info(f'Moving All MOTOR Done,take {runtime}sec') 
                else:
                    #no move
                    self.logger.info(f'Something wired, i should not goto here') 
                    pass
                #check motor pos again,in case md3 ver or hor has some problem
                time.sleep(0.2)
                self.ca.caput('07a:MD3:SyncPM.PROC',1)
                time.sleep(0.1)
                #
                checkarray=[]
                for motor in tempmovinglist:
                    current_pos = self.ca.caget(f'{motor}.RBV',format=float,array=False,debug=False)
                    diff = abs(current_pos-tempmovinglist[motor])
                    if  diff<0.001:
                        checkarray.append(True)
                        self.logger.info(f' motor:{motor},current pos = {current_pos} diff is smaller than 0.001')
                    else:
                        self.logger.warning(f' motor:{motor},current pos = {current_pos} not in {tempmovinglist[motor]}')
                        checkarray.append(False)
                if all(checkarray):
                    self.logger.info('all motor in position')
                else:
                    self.logger.warning('some motor not in position,move again')
                    for motor in tempmovinglist :
                        try:
                            self.logger.debug(f'Set {motor} move to {tempmovinglist[motor]}') 
                            print(self.ca.caput(motor,tempmovinglist[motor]))
                        except Exception as e:
                            self.logger.warning(f'Error when give {motor} command')
                            self.logger.warning(f'Exception : {e}')
                            pass
                #update kx ky
                
                self.ca.caput(self.DBPM6kxfactor,self.DBPM6kxLists[index])
                self.ca.caput(self.DBPM6kyfactor,self.DBPM6kyLists[index])

            else:
                self.logger.warning(f'Beam size : {beamsize} ,not in beam list :{self.BeamSizeLists}')


            self.ca.caput('07a-ES:Beamsize',beamsize)
            self.Busy = False
            self.logger.info(f'End of moving beamsize:{beamsize}')
    def opencover(self,opencover=False):
            if opencover:
                self.logger.debug(f'Try to ask detector cover open')
                # self.opcoverP = Process(target=self.cover.OpenCover,name='open_cover')
                self.opcoverP = Process(target=self.cover.askforAction,args=('open',),name='open_cover')
                self.opcoverP.start()
                
            else:
                pass
    def wait_opencover(self,opencover=False):
            
            if opencover:
                self.logger.debug(f'waiting detector cover open')
                # self.opcoverP.join()
                self.opcoverP.join(5)
                self.logger.warning(f'self.opcoverP process {self.opcoverP.is_alive()=},{self.opcoverP.pid=},{self.opcoverP.sentinel=},{self.opcoverP.exitcode=}')
                if self.opcoverP.exitcode== None:
                    self.logger.warning(f'opcover P has problem kill it!')
                    self.opcoverP.kill()
                    #try to open again
                    self.logger.warning(f'Try to open it again!')
                    self.opcoverP = Process(target=self.cover.askforAction,args=('open',),name='open_cover')
                    self.opcoverP.start()
                    self.wait_opencover(opencover)
                    # self.opcoverP.join()
            else:
                pass
    def check_allmotorstop(self,motorlist):
        self.logger.debug(f'check_allmotorstop,{motorlist=}')
        if len(motorlist) == 0:
            return True
        statearray = []
        for motor in motorlist:
            # time.sleep(0.1)
            if self.ca.caget(f"{motor}.DMOV",int,False,False) == 1:
                statearray.append(True)
                # pos = self.ca.caget(f"{motor}")
                # self.logger.debug(f'{motor} pos at {pos}') 
            else:
                statearray.append(False)
                # pos = self.ca.caget(f"{motor}")
                # self.logger.debug(f'{motor} pos at {pos}') 
        self.logger.debug(f'check_allmotorstop,{statearray=}')
        return all(statearray)
    def check_allMD3motorstop(self,md3epicsname):
        '''
                      [ 0] ON
                      [ 1] OFF
                      [ 2] CLOSED
                      [ 3] OPEN
                      [ 4] READY
                      [ 5] BUSY
                      [ 6] MOVING
                      [ 7] RUNNING
                      [ 8] STARTED
                      [ 9] STOPPED
                      [10] UNKNOWN
                      [11] ALARM
                      [12] COMMUNICATION_ERROR
                      [13] FAULT
                      [14] OFFLINE


        Parameters
        ----------
        md3epicsname : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        self.logger.debug(f'check_allMD3motorstop,{md3epicsname=}')
        if len(md3epicsname) == 0:
            return True
        statearray = []
        for epicsname in md3epicsname:
            if self.ca.caget(epicsname) == 4:
                statearray.append(True)
            else:
                statearray.append(False)
        self.logger.debug(f'check_allMD3motorstop,{statearray=}')
        return all(statearray)
    
    def pipecaput(self,PV,value):
        self.logger.warning(f'caput PV={PV},value={value}')
        if type(value) is list:
            command = ['caput',str(PV)]
            for item in value:
                command.append(str(item))
        elif PV =="07a:md3:CurrentApertureDiameterIndex":
            command = ['caput',str(PV),str(int(value))]
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

    def quit(self,signum,frame):
        
        self.logger.debug(f"PID : {os.getpid()} DHS closed, Par= {self.Par} TYPE:{type(self.Par)}")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
        sys.exit()


def quit(signum,frame):
    print("EPICS Special DHS Main cloesd")
    # reciveQ = self.Par['Queue']['reciveQ']
    # sendQ = self.Par['Queue']['sendQ']
    # epicsQ = self.Par['Queue']['epicsQ']
    # reciveQ('exit')
    # sendQ.put("exit")
    # epicsQ.put("exit")
    
    sys.exit()
    pass


    
if __name__ == "__main__":
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    logger=logsetup.getloger2('Main')
    # m = Manager()
    # Par = m.dict()
    A = Beamsize()
    # A.target(30)
    A.target(0.5)
