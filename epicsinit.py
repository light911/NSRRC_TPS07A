# -*- coding: utf-8 -*-
"""
Created on Wed Dec 25 09:56:32 2019

@author: admin
TODO:update DisY uperlimits
"""

from epics import PV,Motor,ca,CAProcess,caget,caput
import numpy as np
import sys,time,os,signal
import logsetup
#from . import epicsfile
  
from multiprocessing import  Queue,Process
import queue
from PyQt5.QtCore import QObject,QThread,pyqtSignal,pyqtSlot,QMutex,QMutexLocker
import subprocess
#from PyQt5.QtCore import pyqtSignal


class epicsdev(QThread):
    # EpicsValueChange=pyqtSignal(str,str,str)
    # EpicsConnectChange=pyqtSignal(str,str)    
    def __init__(self,epicslist,par,Q,epicsmotors=None,parent=None):
        super(self.__class__,self).__init__(parent)
        # self.data=np.empty(0)
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        ca.initialize_libca()
        self.Par = par
        # if self.Par['Debug']:
        #     debuglevel = "DEBUG"
            
        # else :
        #     debuglevel = "INFO"
        
        
        self.logger = logsetup.getloger2('EPICS',level = self.Par['Debuglevel'])
        self.logger.info("init EPICS logging")
               
        
        
        self.epicslist = epicslist
        self.epicsmotors = epicsmotors
        self.Par['EPICS']={}
        self._observers = []
        self.epicsQ = Q['Queue']['epicsQ']
        self.reciveQ = Q['Queue']['reciveQ']
        self.sendQ = Q['Queue']['sendQ']
        self.controlQ = Q['Queue']['ControlQ']
        
        self.init_update=True
        #used to a Flag for update limits @motor start moving
        self.MD3Ystartmoving = False
        self.DetYstartmoving = False
        self.startRasterScanEx = {}
        self.startRasterScanEx['moving'] = False
        self.startRasterScanEx['id'] = ""
        self.startRasterScan = {}
        self.startRasterScan['moving'] = False
        self.startRasterScan['id'] = ""
        self.md3TaskBusy=False
        self.tempcommand=[]
        self.saveCentringPositionFlag_sample_z = False
        self.saveCentringPositionFlag_cam_horz = False
        # print(self.Par)

    def setMotor(self):
        # self.logger.info("EPICS set motor")
        
        for motor in self.epicsmotors:
            self.logger.info(f'EPICS set {motor}')
            self.epicsmotors[motor]['PVID'] = Motor(self.epicsmotors[motor]['PVname'])
            self.epicsmotors[motor]['GUIname'] = motor
            
        self.updateDetYlimits()
        self.updateMD3Ylimits()            
        self.initinfo()
        
        for motor in self.epicsmotors:
            for mon in self.epicsmotors[motor]['callbackitems']:
                self.epicsmotors[motor]['PVID'].set_callback(attr=mon,callback=self.onMotorValueChange)

    def onMotorValueChange(self,pvname=None, value=None, host=None,timestamp=None, **kws):
        '''
        pvname is fake one:  pv,field=self.findfield(pvname) to find true full pv name

        '''
        
        pv,field=self.findfield(pvname)
        guiname,dcssname,dcsstype= self.FindEpicsMotorInfo(pv,'PVname','GUIname','dcssname','dcsstype')
        command=["","","","","",""]
        # self.logger.debug(f'PV,GUI name: {pv},{guiname} ={value} ')
        # For RBV check within dead band
        if field == "RBV":
            self.Par['EPICS'][guiname]['RBV'] = value
            if abs(float(self.epicsmotors[guiname]["old_value"]) - float(value) ) < self.epicsmotors[guiname]["deadband"]:
                
                pass
            else:# from here RBV type and lager than deadband
                self.epicsmotors[guiname]["old_value"] = float(value)
                self.logger.debug(f'PV value changed: {pvname}={value} ')    
                # self.notify_observers('NormalUpdate',guiname,value)
                if dcsstype == "string" or dcsstype == "motor"  :
                    command[0]="updatevalue"
                    command[1]=dcssname
                    command[2]=value
                    command[3]=dcsstype
                    command[4]="normal"
                    if command[1] == "energy":
                        command[2] = value *1000
                    
                else:
                    #no dccstype or unknow type
                    command=["","","","","",""]
                    pass
                if command[0] != "":
                    #have somthing to send to dcss
                    self.sendQ.put((command[0],command[1],command[2],command[3],command[4]))
                    self.logger.debug(f'send command to dcss: {command} ')        
        elif field == "DMOV" :
            self.Par['EPICS'][guiname]['DMOV'] = value
            self.logger.debug(f'PV value changed: {pvname}={value} guiname={guiname}')
            #motor move done or moving
            if guiname == "MD3Y" or guiname == "DetY":
                
                if value == 1:
                    #move done
                    self.logger.warning(f'{guiname} is sopted! update limits to prevent collision')
                    if guiname == "MD3Y":
                        #MD3Y just moved should update DetY LLM
                        self.updateDetYlimits()
                    elif guiname == "DetY":
                        #DetY just moved should update MD3Y HLM
                       self.updateMD3Ylimits()
                    else:
                        pass 
                else:
                    #start moving
                    self.logger.warning(f'{guiname} is start moving! update limits to increase range')
                    # fakeDistanceLLM = self.epicsmotors['DetDistance']['PVID'].LLM
                    if guiname == "MD3Y":
                        #MD3Y start moving should update DetY LLM
                        self.MD3Ystartmoving = True
                        
                        
                    elif guiname == "DetY":
                        #DetY start moving should update MD3Y HLM
                        self.DetYstartmoving = True
                    else:
                        
                        pass 
                    pass
            elif guiname == "Energy":
                if value == 1:
                    #move done
                    self.logger.debug("Energy end of moing,Disable gap to energy")
                    #Disable = 1
                    self.caput(self.Par['Energy']['evtogap'],1)
                    # p = CAProcess(target=self.oldCAPUT, args=(self.Par['Energy']['evtogap'],1,))
                    # p.start()
                    # p.join()
                    pos = self.epicsmotors[guiname]['PVID'].get('RBV') * 1000
                    self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
            
            elif guiname == "cam_horz" or guiname == "SampleZ":
                if value == 1:
                    #move done
                    #saveCentringPositions
                    # phase = caget('07a:md3:CurrentPhase',as_string=True)
                    # print(self.Par["EPICS"])
                    phase =self.epicslist['07a:md3:CurrentPhase']["old_value"]
                    if  phase== 0 or phase== 2:#center or collect
                        PV = self.Par['collect']['saveCentringPositionsPV']
                        if self.saveCentringPositionFlag_sample_z:
                            self.saveCentringPositionFlag_sample_z = False
                            self.logger.debug("Save current pos for Center pos (sampleZ stop)")
                            self.caput(PV,'__EMPTY__')
                            # p = CAProcess(target=self.oldCAPUT, args=(PV,'__EMPTY__',))
                            # p.start()
                            # p.join()
                        elif self.saveCentringPositionFlag_cam_horz:
                            self.saveCentringPositionFlag_cam_horz = False
                            self.logger.debug("Save current pos for Center pos (cam_horz Stop)")
                            self.caput(PV,'__EMPTY__')
                            # p = CAProcess(target=self.oldCAPUT, args=(PV,'__EMPTY__',))
                            # p.start()
                            # p.join()
                        else:
                            pass
                    pos = self.epicsmotors[guiname]['PVID'].get('RBV')
                    self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
            else:
                if value == 1:
                    #move done
                    pos = self.epicsmotors[guiname]['PVID'].get('RBV')
                    self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
        elif field == "VAL" :
            self.Par['EPICS'][guiname][field] = value
            if guiname == "MD3Y" and self.MD3Ystartmoving :
                self.MD3Ystartmoving = False
                #MD3Y start moving should update DetY LLM
                self.updateDetYlimits(usingVAL=True)
            elif guiname == "DetY" and self.DetYstartmoving :
                self.DetYstartmoving = False
                #DetY start moving should update MD3Y HLM
                self.updateMD3Ylimits(usingVAL=True)
        elif field == "LLM" :
            if guiname == "DetDistance":
                self.updateDetYlimits()
                self.updateMD3Ylimits()        
        else:
            self.Par['EPICS'][guiname][field] = value
            self.logger.debug(f'PV value changed: {pvname}={value} ')
            
            
    def initinfo(self):
        temp = {}
        for motor in self.epicsmotors:
            mid = self.epicsmotors[motor]['PVID']
            detailinfo = {'VAL':mid.VAL,
                          'RBV':mid.RBV,
                          'DMOV':mid.DMOV,
                          'HLM':mid.HLM,
                          'LLM':mid.LLM,
                          'OFF':mid.OFF,
                          }

            temp[motor]=detailinfo
        self.Par['EPICS'] = temp
        self.logger.debug(f"PID : {os.getpid()} EPICS initINFO, Par= {self.Par} TYPE:{type(self.Par)}")
        # self.logger.warning(f"PID : {os.getpid()} EPICS initINFO, Par= {self.Par} TYPE:{type(self.Par)}")
        pass
        
    def findfield(self,PVname=""):
        '''
        Parameters
        ----------
        PVname : TYPE, 
            DESCRIPTION. The default is "".

        Returns PVname,field
        -------
        TYPE
            DESCRIPTION.
        TYPE
            DESCRIPTION.

        '''
        a = PVname.split('.')
        if len(a) == 1:
            return None
        else:
            return a[0],a[-1]
        
    def setcallback(self):
        for item in self.epicslist:
            self.logger.info(f'EPICS set {item}')
            self.epicslist[item]["connected"] = False
            self.epicslist[item]["valueupdated"] = False
        for item in self.epicslist:
            if self.epicslist[item]["camon"] == True:
                self.epicslist[item]["PVID"] = PV(item,
                      connection_callback= self.onConnectionChange,
                      callback= self.onValueChange)
    
    def onConnectionChange(self,pvname=None, conn= None, **kws):
        '''
            pvname is full pv ex: 07a-ES:Beamsize

        '''
        guiname =self.epicslist[pvname]["GUIname"]
        dcssname =self.epicslist[pvname]["dcssname"]
        self.logger.info('PV connection status changed: %s %s' % (pvname,  repr(conn)))
        self.epicslist[pvname]["connected"] = repr(conn)
        # print('PV connection status changed: %s %s' % (pvname,  repr(conn)))
        # self.EpicsConnectChange.emit(guiname,repr(conn))
        if self.check_all_connected():
            self.logger.info('PV connection All good')
        else:
            self.logger.info('Wait for connection All good')
            info ={}
            for item in self.epicslist:
                info[ self.epicslist[item]['GUIname'] ] = self.epicslist[item]['connected']
            self.logger.debug('Current connected state:%s',info)
    
    def onValueChange(self,pvname=None, value=None, host=None,timestamp=None, **kws):
        guiname = self.epicslist[pvname]["GUIname"]
        dcssname = self.epicslist[pvname]["dcssname"]
        dcsstype = self.epicslist[pvname]["dcsstype"]
        self.Par['EPICS'][guiname] = value
        self.epicslist[pvname]["valueupdated"] = True
        
        if dcsstype == "par":
            if guiname == 'zoom_scale_x' or guiname == 'zoom_scale_y' :
                value = value *1000
            
            #par just update value and endmove
            self.sendQ.put(('endmove',dcssname,value,'normal'))
        elif dcsstype == "change_mode" :
                      # [ 0] Centring
                      # [ 1] BeamLocation
                      # [ 2] DataCollection
                      # [ 3] Transfer
                      # [ 4] Unknown
            # value = int(value)
            if value == 4:
                self.sendQ.put(('updatevalue',dcssname,value,"motor","normal"))
            else:
                self.sendQ.put(('endmove',dcssname,value,'normal'))
        elif dcsstype == "quickmotor" :   
            self.sendQ.put(('endmove',dcssname,value,'normal'))
        elif dcsstype == 'log':
            
            if value[6] == "1":
                self.md3TaskBusy = False
                # when job done recover command
                
                if len(self.tempcommand) >0:
                    time.sleep(0.1)
                    for command in self.tempcommand:
                         self.logger.warning(f"Recover {command}(pervious sicne MD3 busy)")
                         self.epicsQ.put(command)
                    self.tempcommand=[]
                    
            else:
                self.md3TaskBusy =True
                
            self.logger.info(f'TASK: {value}')
            self.logger.debug(f'job={value[0]},state={value[6]},self.startRasterScanEx={self.startRasterScanEx["moving"]}')
            if self.startRasterScanEx['moving'] :
                # start
                # ['Raster Scan', '8', '2021-07-23 14:12:28.47', 'null', 'null', 'null', 'null']
                # end
                # ['Raster Scan', '8', '2021-07-23 14:12:28.47', '2021-07-23 14:12:41.972', 'org.embl.dev.pmac.PmacDiagnosticInfo@77', 'null', '1'] 
                
                if value[0] == 'Raster Scan' and value[6] == "1":
                    self.startRasterScanEx['moving'] = False
                    opid = self.startRasterScanEx['id']
                    self.sendQ.put(('operdone','startRasterScanEx',opid,'normal'))
            if self.startRasterScan['moving'] :
                # start
                # ['Raster Scan', '8', '2021-07-23 14:12:28.47', 'null', 'null', 'null', 'null']
                # end
                # ['Raster Scan', '8', '2021-07-23 14:12:28.47', '2021-07-23 14:12:41.972', 'org.embl.dev.pmac.PmacDiagnosticInfo@77', 'null', '1'] 
                
                if value[0] == 'Raster Scan' and value[6] == "1":
                    self.startRasterScan['moving'] = False
                    opid = self.startRasterScan['id']
                    self.sendQ.put(('operdone','startRasterScan',opid,'normal'))
        #for other            
        if self.init_update:
            self.epicslist[pvname]["old_value"] = value
            self.logger.debug('PV value changed: %s=%s ' % ( guiname, value))
            
                    
            if self.check_all_valueupdated() and self.check_all_connected():
                self.logger.debug("All value updaed")
                self.notify_observers('UpdateDistance')
                self.init_update = False
            else:
                info = {}
                self.logger.debug('Wait for connection All good')
                for item in self.epicslist:
                    info[ self.epicslist[item]['GUIname'] ] = self.epicslist[item]['valueupdated']
                self.logger.debug('Current value updated state:%s',info)
        else:#after init what we do
            try:
                state = abs(self.epicslist[pvname]["old_value"] - value ) < self.epicslist[pvname]["deadband"]
            except :
                state = True
            if state :
                
                # self.logger.debug('Not update due to deadband')
                # self.logger.debug(f"GUI:{guiname}, det:{abs(self.epicslist[pvname]['old_value'] - value )}")
                pass
            else :#everthing is fine 
                # self.logger.debug('PV value changed: %s=%s ' % ( guiname, value))
                self.logger.debug(f'PV value changed: {guiname}={value} ')
                if guiname == "shutter":
                    self.sendQ.put(('updatevalue',dcssname,value,dcsstype,"normal"))
                self.epicslist[pvname]["old_value"] = value
                
                
                    
                    
    #notify observer not used, keep it for ref
    #man dhs need register after active calss
    # self.epics = epicsdev(EpicsConfig.epicslist,self.Par)
    # self.epics.register_observer(self)
    # for event use self.notify_observers send it
    # self.notify_observers('ChangeMD3BS',value)
    def register_observer(self, observer):
        self._observers.append(observer)
        self.logger.debug("Epics register PID:%d",os.getpid())
        # self.logger.debug("Register",observer)
        
    def notify_observers(self, *args, **kwargs):
        for observer in self._observers:
            observer.notify(self, *args, **kwargs)
        self.logger.debug(f"Epics notify_observers PID:{os.getpid()} {args},{kwargs}",)
    
   
    
    
    def check_all_connected(self):
        init = True
        for item in self.epicslist:
            init = init and self.epicslist[item]["connected"]
        return init
    
    def check_all_valueupdated(self):
        init = True
        for item in self.epicslist:
            init = init and self.epicslist[item]["valueupdated"]
        return init
    
    def clear_epics_callback(self):
        self.logger.info('Clear Epics callback')
        for item in self.epicslist:
            if self.epicslist[item]["camon"] == True:
                self.epicslist[item]["PVname"].disconnect()
    
    def clear_epics_Motor_callback(self):
        self.logger.info('Clear Epics Motor callback')
        for motor in self.epicsmotors:
            for mon in self.epicsmotors[motor]['callbackitems']:
                self.epicsmotors[motor]['PVID'].clear_callback(attr=mon)
         # self.clear_callback(attr='DMOV')
         
    def FindEpicsMotorInfo(self,target,name='PVname',*args):
        '''
         ex: guiname, = self.FindEpicsMotorInfo(detector_z,'dcssname','GUIname')

        Parameters
        ----------
        target : Search txt
            DESCRIPTION.
        name : Search [item]
            DESCRIPTION. The default is 'PVname'.
        *args : return *[item's key]
            DESCRIPTION.

        Returns
        -------
        ans : TYPE list
            DESCRIPTION.

        '''
        ans=[]
        try:
            for pvname in self.epicsmotors:
                # self.logger.debug(f'PV,GUI name: {pvname}, {self.epicsmotors[pvname][name]} = {target} ')
                if self.epicsmotors[pvname][name] == target :
                    # self.logger.debug(f'GOT ans PV,GUI name: {pvname}, {self.epicsmotors[pvname][name]} = {target}, arg= {args}')
                    for arg in args:
                        ans.append(self.epicsmotors[pvname][arg])
                        # print(ans)
        except :
            ans = [None]
        
        return ans
    
    def epcisMon(self) :
        self.logger.warning(f'Epics MON Start at {os.getpid()}')
        while True:
            try:
                command = self.epicsQ.get(block=False)
            except  queue.Empty:
                time.sleep(0.05)
                command = None
                pass
            except Exception as e: 
                self.logger.critical(f'Has error on get Epics Queue , Error ={e}')
                command = None
           
                
            if isinstance(command,str):
                if command == "exit" :
                    self.clear_epics_callback()
                    self.clear_epics_Motor_callback()
                    break
                else:
                    pass
                    #may be from reviceQ (DCSS),update or move some thing for it
            elif isinstance(command,type(None)):
                pass
                    
            #from reviceQ (DCSS),update or move some thing for it
            elif isinstance(command,tuple):
                if command[0] == "stoh_start_motor_move" :
                    #stoh_start_motor_move motorName destination
                    # check is value higher or lower limits?
                    #command[1]= dcss motor name,command[2]=target position
                    #pvanme=self.findepicsinfo(command[1],"PVname")
                    
                    # self.findepicsinfo(command[1],"PVname").value = float(command[2])
                    try :
                        PVID,dcsstype,PVname,deadband = self.FindEpicsMotorInfo(command[1],'dcssname','PVID','dcsstype','PVname','deadband')
                    except :
                        self.logger.debug("dcssname can not find in EPICS Motor")
                        dcsstype = ""
                        try:
                            PVID,dcsstype,PVname,deadband = self.FindEpicsListInfo(command[1],'dcssname','PVID','dcsstype','PVname','deadband')
                        except:
                            dcsstype = ""
                            self.logger.debug("dcssname can not find in EPICS List")
                            
                    self.logger.debug(f"command stoh_start_motor_move PVID={PVID},dcsstype={dcsstype},PVname={PVname},deadband={deadband}")                    
                    
                    if dcsstype == 'motor':  #only in epicsmotors is dcsstype = motor      
                        TargetPos = float(command[2])
                        if command[1] == 'energy':
                            TargetPos = TargetPos / 1000
                        
                        
                        if PVID.within_limits(TargetPos):
                            if command[1] == 'energy':
                                #Enable energy to gap(07a:IU22:cvtE2Gap_able)
                                newenergy = TargetPos
                                C_energy = PVID.RBV
                                N_gap = float(caget(self.Par['Energy']['cvtE2Gapname']))#old gap output
                                C_gap = float(caget(self.Par['Energy']['gapname']))#current gap
                                if abs(C_gap - N_gap) > self.Par['minchangeGAP'] or abs(C_energy - newenergy) > self.Par['minEVchangeGAP']:
                                    self.logger.debug(f"det detGap {abs(C_gap - N_gap)} is higher than {self.Par['minchangeGAP']},or {abs(C_energy - newenergy)} > {self.Par['minEVchangeGAP']} change gap setting")
                                    #Enalble = 0
                                    ring_state = caget("TPS:OPStatus") 
                                    self.logger.warning(f"{ring_state=}")
                                    if caget("TPS:OPStatus") == 0:
                                        self.logger.warning(f"ring closed")
                                    else:
                                        self.caput(self.Par['Energy']['evtogap'],0)

                                    # p = CAProcess(target=self.oldCAPUT, args=(self.Par['Energy']['evtogap'],0,))
                                    # p.start()
                                    # p.join()
                                else:
                                    self.logger.debug(f"det detGap {abs(C_gap - N_gap)} is small than {self.Par['minchangeGAP']},and  {abs(C_energy - newenergy)} > {self.Par['minEVchangeGAP']},NO chane gap setting")
                                    #Disable = 1
                                    self.caput(self.Par['Energy']['evtogap'],1)
                                    # p = CAProcess(target=self.oldCAPUT, args=(self.Par['Energy']['evtogap'],1,))
                                    # p.start()
                                    # p.join()
                            
                            if abs(TargetPos - PVID.RBV) < deadband:
                                pos = PVID.RBV
                                dcssname = command[1]
                                if dcssname == 'energy':
                                    pos = pos *1000
                                self.logger.debug(f"{dcssname} move to {TargetPos}, but moving step smaller than deadband ={deadband},Just reply moving complete")
                                self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
                                
                            else:
                                #move motor part
                                if command[1] == 'gonio_phi' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'sample_z' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'sample_x' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'sample_y' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'cam_horz' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'align_z' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'align_x' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'cam_horz' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'gonio_kappa' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                elif command[1] == 'gonio_omega' and self.md3TaskBusy :
                                    self.tempcommand.append(command)
                                    self.logger.warning(f"{command} has paused sicne MD3 busy")
                                else:
                                    # send command to move
                                    if command[1] == 'sample_z':
                                        self.saveCentringPositionFlag_sample_z = True
                                    elif command[1] == 'cam_horz':
                                        self.saveCentringPositionFlag_cam_horz = True
                                    self.sendQ.put(("startmove",command[1],command[2],"Normal"))
                                    state = PVID.move(TargetPos)
                                    self.logger.debug(f"Motor ={command[1]} moving state = {state}")
                        else:
                            LLM = PVID.LLM
                            HLM = PVID.HLM
                            pos = PVID.RBV
                            dcssname = command[1]
                            warningTXT = f'Motor {command[1]} TargetPOS:{command[2]} is out of limits {LLM} to {HLM}'
                            self.sendQ.put(("warning",warningTXT))
                            self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
                                            
                        pass
                    elif dcsstype == "change_mode":
                            self.sendQ.put(("startmove",command[1],command[2],"Normal"))
                            value = int(float(command[2]))
                            self.caput(PVname,value)
                            # p = CAProcess(target=self.CAPUT, args=(PVname,float(command[2]),))
                            # p.start()
                            # p.join()
                    elif dcsstype == "quickmotor":
                            self.sendQ.put(("startmove",command[1],command[2],"Normal"))
                            if command[1] == 'camera_zoom':
                                value = int(float(command[2]))
                            else:
                                value = command[2]
                            self.caput(PVname,value)
                            # p = CAProcess(target=self.oldCAPUT, args=(PVname,float(command[2]),))
                            # p.start()
                            # p.join()
                            self.sendQ.put(('endmove',command[1],command[2],'normal'))#bug??
                    else:
                        pos = command[2]
                        dcssname = command[1]
                        warningTXT = f'Unable find {dcssname} in config file'
                        self.sendQ.put(("warning",warningTXT))
                        self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
                        pass
                    
                   
                elif command[0] == "stoh_register_shutter" or command[0] == 'stoh_set_shutter_state':
                    #['stoh_register_shutter', 'shutter', 'closed'
                    dcssname = command[1]
                    Tartgetstate = command[2]
                    PVID, = self.FindEpicsListInfo(dcssname,'dcssname','PVID')
                    if Tartgetstate == 'open':
                        state = 1
                    else:
                        state = 0
                    PVID.put(state)
                    
                elif command[0] == "startRasterScanEx":
                    self.startRasterScanEx['moving'] = True
                    self.startRasterScanEx['id'] = command[1]
                    PVname, = self.FindEpicsListInfo(command[0],'GUIname','PVname')
                    # temp =list(command)
                    # temp.pop(0)#del startRasterScanEx
                    # temp.pop(0)#del client id
                    value =[]
                    
                    value.append(float(command[2]))
                    value.append(float(command[3]))
                    value.append(float(command[4]))
                    value.append(float(command[5]))
                    value.append(float(command[6]))
                    value.append(float(command[7]))
                    value.append(float(command[8]))
                    value.append(float(command[9]))
                    value.append(int(command[10]))
                    value.append(int(command[11]))
                    value.append(float(command[12]))
                    value.append(int(command[13]))
                    value.append(int(command[14]))
                    value.append(int(command[15]))
                    # temp = np.array(numtemp)
                    # startRasterScanEx
                    # double omega_range,
                    # double line_range, ver?
                    # double total_uturn_range, hor?
                    # double start_omega,
                    # double start_y,
                    # double start_z,
                    # double start_cx,
                    # double start_cy,
                    # int number_of_lines,
                    # int frames_per_lines,
                    # double exposure_time,
                    # boolean invert_direction,
                    # boolean use_centring_table,
                    # boolean shutterless

                    # print(type(PVname),PVname)
                    # print(type(value),len(value),value)
                    # self.CAPUT(PVname,temp)
                
                    p = CAProcess(target=self.oldCAPUT , args=(PVname,value,))
                    p.start()
                    p.join()        
                    
                elif command[0] == "startRasterScan":
                    # ['startRasterScan', '7.6', '0.05', '-0.2', '2', '5', '0', '269.999792', '0.5', '0', '']
                    self.startRasterScan['moving'] = True
                    self.startRasterScan['id'] = command[1]
                    PVname, = self.FindEpicsListInfo(command[0],'GUIname','PVname')
                    # temp =list(command)
                    # temp.pop(0)#del startRasterScan
                    # temp.pop(0)#del client id
                    value =[]
                    
                    value.append(float(command[2]))
                    value.append(float(command[3]))
                    value.append(int(command[4]))
                    value.append(int(command[5]))
                    value.append(int(command[6]))
                    
                    ScanStartAngle = float(command[7]) #not using now
                    ScanExposureTime = float(command[8])
                    ScanRange = float(command[9])
                    # startRasterScan
                    # vertical_range (double): vertical range of the grid      should be X
                    # horizontal_range (double): horizontal range of the grid  should be Y
                    # number_of_lines (int) : number of horizontal lines of scan
                    # number_of_frames (int): number of frame trigger issued for the detector
                    # invert_direction (Boolean): flag to enable passes in the reverse direction
                    
                    # ScanStartAngle,
                    # ScanExposureTime, (a line)
                    # ScanRange

                    # print(type(PVname),PVname)
                    # print(type(value),len(value),value)
                    # self.CAPUT(PVname,temp)
                    p1 = CAProcess(target=self.oldCAPUT , args=('07a:md3:ScanExposureTime',ScanExposureTime,))
                    p1.start()
                    # p1.join() 
                    time.sleep(0.1)
                    p2 = CAProcess(target=self.oldCAPUT , args=('07a:md3:ScanRange',ScanRange,))
                    p2.start()
                    # p2.join() 
                    time.sleep(0.1)
                    p3 = CAProcess(target=self.oldCAPUT , args=('07a:md3:ScanStartAngle',ScanStartAngle,))
                    p3.start()
                    # p3.join() 
                    time.sleep(0.5)
                    p = CAProcess(target=self.oldCAPUT , args=(PVname,value,))
                    p.start()
                    p.join()   

                elif command[0] == "stoh_abort_all" :
                    
                    for m in self.epicsmotors:
                        dcssname =self.epicsmotors[m]['dcssname']
                        if dcssname != "" :
                            self.epicsmotors[m]['PVID'].stop()
                            self.logger.warning(f"{dcssname} STOP!")
                            pos = self.epicsmotors[m]['PVID'].RBV
                            if dcssname == "energy" :
                                pos = pos*1000
                            self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
                    
                    self.caput('07a:md3:abort','__EMPTY__')
                    # p = CAProcess(target=self.oldCAPUT, args=('07a:md3:abort','__EMPTY__',))
                    # p.start()
                    # p.join()        
                    
                    
                    for dev in self.epicslist:
                        dcssname = self.epicslist[dev]['dcssname']
                        dcsstype = self.epicslist[dev]['dcsstype']
                        if dcssname != "" :
                            if dcsstype == 'shutter':
                                pass
                            elif dcsstype == 'change_mode':
                                pos = caget(dev)
                                self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
                            elif dcsstype == 'log':
                                pass
                            
                            else:
                                pos = caget(dev)
                                if dcssname == 'zoom_scale_x' or dcssname == 'zoom_scale_y':
                                    pos =pos *1000
                                
                                self.sendQ.put(('endmove',dcssname,pos,'normal'), block=False)
                    self.md3TaskBusy=False    
                else:
                    self.logger.warning(f'EPICSQ Get unkown command:{command}')
                    pass
            else:
                pass
        pass

    def FindEpicsListInfo(self,target,name='PVname',*args):
        '''
         ex: guiname = self.FindEpicsListInfo(detector_z,'dcssname','GUIname')

        Parameters
        ----------
        target : Search txt
            DESCRIPTION.
        name : Search [item]
            DESCRIPTION. The default is 'PVname'.
        *args : return *[item's key]
            DESCRIPTION.

        Returns
        -------
        ans : TYPE
            DESCRIPTION.

        '''
        ans=[]
        try:
            for item in self.epicslist:
                # self.logger.debug(f'PV,GUI name: {item}, {self.epicsmotors[pvname][name]} = {target} ')
                if self.epicslist[item][name] == target :
                    # self.logger.debug(f'GOT ans PV,GUI name: {item}, {self.epicslist[item][name]} = {target}, arg= {args}')
                    for arg in args:
                        ans.append(self.epicslist[item][arg])
                        # print(ans)
        except :
            ans = [None]
        
        return ans
    def CAPUT(self,PV,value):
        ca.initialize_libca()
        self.logger.warning(f'caput PV={PV},value={value}')
        chid = ca.create_channel(PV, connect=False, callback=None, auto_cb=True)
        print(f'caput chid={chid}')
        state = ca.put(chid,value, wait=True,timeout=1, callback=None, callback_data=None)
        if state != 1:
            self.logger.critical(f"Caput {PV} value {value} Fail!")
        print(f'ca put state={state}')
        time.sleep(0.1)
    def oldCAPUT(self,PV,value):   
        
        self.logger.warning(f'caput PV={PV},value={value}')
        state = caput(PV,value)
        if state != 1:
            self.logger.critical(f"Caput {PV} value {value} Fail!")
        print(f'ca put state={state}')
        time.sleep(0.1)
        
    def caput(self,PV,value):
        self.logger.warning(f'caput PV={PV},value={value}')
        command = ['caput',str(PV),str(value)]
        ans = subprocess.run(command,capture_output=True)
        result = ans.stdout.decode('utf-8')
        error = ans.stderr.decode('utf-8')       
        self.logger.debug(f'{ans}')
        if error == '':
            print(f'caput PV={PV},value={value} OK!')
            return True
        else:
            self.logger.critical(f"Caput {PV} value {value} Fail={error}")
            return False
        # print(ans)
    #Detector distance interolck
    def updateMD3Ylimits(self,usingVAL=False) :
        #usingVAL = True for just start moving
        MD3YPVID, = self.FindEpicsMotorInfo('MD3Y','GUIname','PVID')
        DisPVID, = self.FindEpicsMotorInfo('DetDistance','GUIname','PVID')
        DetYPVID, = self.FindEpicsMotorInfo('DetY','GUIname','PVID')
        if usingVAL:
            DetYPOS = DetYPVID.VAL
        else:
            DetYPOS = DetYPVID.RBV
        NewMD3YHLM = DetYPOS + DisPVID.OFF - DisPVID.LLM
        oldHLM = MD3YPVID.HLM
        if NewMD3YHLM < 200:
            # MD3YPVID.HLM = NewMD3YHLM
            # state = MD3YPVID.put('HLM', NewMD3YHLM, wait=True, timeout=1)
            # print(f'state={state}')
            self.caput('07a:MD3:Y.HLM',NewMD3YHLM)
            # p = CAProcess(target=self.oldCAPUT, args=('07a:MD3:Y.HLM',NewMD3YHLM,))
            # p.start()
            # p.join()
            self.logger.warning(f'New High limits cal for MD3Y is :{NewMD3YHLM} and updated(old limits is {oldHLM})')
            if usingVAL :
                self.logger.warning(f'New High limits cal baseon DetYPVID.VAL={DetYPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
            else:
                self.logger.warning(f'New High limits cal baseon DetYPVID.RBV={DetYPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
        else:
            # MD3YPVID.HLM = 200
            # MD3YPVID.put('HLM', 200, wait=True, timeout=1)
            self.caput('07a:MD3:Y.HLM',200.1)
            # p = CAProcess(target=self.oldCAPUT, args=('07a:MD3:Y.HLM',200.1,))
            # p.start()
            # p.join()
            self.logger.warning(f'New High limits cal for MD3Y is :{NewMD3YHLM} Higher than 200,updated to 200.1(old limits is {oldHLM})')
            if usingVAL :
                self.logger.warning(f'New High limits cal baseon DetYPVID.VAL={DetYPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
            else:
                self.logger.warning(f'New High limits cal baseon DetYPVID.RBV={DetYPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
        # ca.poll()
        self.logger.warning(f'recheck MD3Y HLM is :{MD3YPVID.HLM}')
        
    def updateDetYlimits(self,usingVAL=False):
        #usingVAL = True for just start moving
        MD3YPVID, = self.FindEpicsMotorInfo('MD3Y','GUIname','PVID')
        DisPVID, = self.FindEpicsMotorInfo('DetDistance','GUIname','PVID')
        DetYPVID, = self.FindEpicsMotorInfo('DetY','GUIname','PVID')
        #MD3Y just moved should update DetY LLM
        # print(f'{type(MD3YPVID.RBV)},{type(DisPVID.OFF)},{type(DisPVID.LLM)}')
        if usingVAL :
            MD3YPOS = MD3YPVID.VAL
        else :
            MD3YPOS = MD3YPVID.RBV
        NewDetYLLM = MD3YPOS - DisPVID.OFF + DisPVID.LLM
        oldLLM = DetYPVID.LLM
        # self.logger.debug(f'New limits cal for DetY is :{NewDetYLLM}')
        #40 is measured at MD3Y = -6, Lowest limit for  
        if 40 < NewDetYLLM :
            # DetYPVID.LLM = NewDetYLLM
            # state = DetYPVID.put('LLM', NewDetYLLM, wait=True, timeout=1)
            # print(f'state={state}')
            self.caput('07a:Det:Y.LLM',NewDetYLLM)
            # p = CAProcess(target=self.oldCAPUT, args=('07a:Det:Y.LLM',NewDetYLLM,))
            # p.start()
            # p.join()
            self.logger.warning(f'New Low limits cal for DetY is :{NewDetYLLM} and updated(old limits is {oldLLM})')
            if usingVAL:
                self.logger.warning(f'New Low limits cal baseon MD3YPVID.VAL={MD3YPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
            else:
                self.logger.warning(f'New Low limits cal baseon MD3YPVID.RBV={MD3YPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
        else:
            # DetYPVID.LLM = 40
            # DetYPVID.put('LLM', 40, wait=True, timeout=1)
            self.caput('07a:Det:Y.LLM',NewDetYLLM)
            # p = CAProcess(target=self.oldCAPUT, args=('07a:Det:Y.LLM',40,))
            # p.start()
            # p.join()
            self.logger.warning(f'New Low limits cal for DetY is :{NewDetYLLM} lower than 40,updated to 40(old limits is {oldLLM})')
            if usingVAL:
                self.logger.warning(f'New Low limits cal baseon MD3YPVID.VAL={MD3YPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
            else:
                self.logger.warning(f'New Low limits cal baseon MD3YPVID.RBV={MD3YPOS}, DisPVID.OFF={DisPVID.OFF}, DisPVID.LLM={DisPVID.LLM}')
        # ca.poll()    
        self.logger.warning(f'recheck DetY LLM is :{DetYPVID.LLM}')
        
        
    def quit(self,signum,frame):
        ca.finalize_libca()
        self.logger.debug(f"PID : {os.getpid()} EPICS initDHS closed, Par= {self.Par} TYPE:{type(self.Par)}")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
        sys.exit()    
    
if __name__ == "__main__":
    import EpicsConfig
    par={"Debuglevel":"DEBUG"}
    Run=epicsdev(EpicsConfig.epicslist,par,EpicsConfig.epicsmotors)
    # Run.epicslist=epicsfile.epicslist
    # Run.setcallback()
    Run.setMotor()
    
    try:
        start = time.time()
        while (time.time() - start) < 30:
            time.sleep(0.1)
    except KeyboardInterrupt:
            Run.clear_epics_Motor_callback()
    Run.clear_epics_Motor_callback()
    
    # t0 = time.time()
    # while time.time()-t0 < 10:
    #     time.sleep(0.01)
    # print(Run.par)
    # Run.clear_epics_callback()
