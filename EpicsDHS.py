#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 16:46:13 2020

@author: admin
"""

from epics import caput,CAProcess,caget
from workround import myepics,workroundmd3moving
import socket,time,signal,sys,os,subprocess
# import multiprocessing as mp
from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
from epicsinit import epicsdev
import logsetup
# import epicsfile
import Config
import EpicsConfig,requests
import Detector
from Flux07A.AttenServer import atten
from DetectorCoverV2 import MOXA

class DCSDHS():
    def __init__(self,par:dict=None,m:Manager=None) :
#        super(self.__class__,self).__init__(parent)
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        #load config
        # save self.m in  Manager() not work with spawn
        # if m == None:
        #     self.m = Manager()
        # else:
        #     self.m = m
        # self.Par = m.dict()
        
        self.Par = par

        # print(f'TYPE:{type(self.Par)}')
        self.Par.update(Config.Par)
        self.Par['operationRecord'] = m.list([])#init operationRecord make it list proxy
        # print(f'TYPE:{type(self.Par)}')
        
        #set log
        self.logger = logsetup.getloger2('EPICSDHS',LOG_FILENAME='./log/EpicsLog.txt',level = self.Par['Debuglevel'],bypassline=False)
        self.logger.info(f'EPICS DCSDHS PID = {os.getpid()}')
        self.logger.info("init EPICSDHS logging")
        self.logger.info("Logging show level = %s",self.Par['Debuglevel'])
        # self.logger.debug("Par Start=======")
        # self.logger.debug(self.Par)
        # self.logger.debug(f'TYPE:{type(self.Par)}')
        # self.logger.debug("Par End========")
        
        #setup dcss par
        self.host = self.Par['dcss']['host']
        self.port = self.Par['dcss']['port']
        self.dhsname = self.Par['dcss']['dhsname']
        self.tcptimeout = self.Par['dcss']['tcptimeout']
        
        self.epicsmotors = EpicsConfig.epicsmotors
        #setup for Queue
        self.Q={'Queue':{}}
        self.Q['Queue']['reciveQ'] = Queue() 
        self.Q['Queue']['sendQ'] = Queue() 
        self.Q['Queue']['epicsQ'] = Queue()
        self.Q['Queue']['ControlQ'] = Queue()
        self.Q['Queue']['DetectorQ'] = Queue()
        self.Q['Queue']['attenQ'] = Queue()
        self.Q['Queue']['workroundQ'] = Queue()
        # self.Q={'Queue':{}}
        # self.Q['Queue']['reciveQ'] = self.m.Queue() 
        # self.Q['Queue']['sendQ'] = self.m.Queue() 
        # self.Q['Queue']['epicsQ'] = self.m.Queue()
        # self.Q['Queue']['ControlQ'] = self.m.Queue()
        # self.Q['Queue']['DetectorQ'] = self.m.Queue()
        # self.Q['Queue']['attenQ'] = self.m.Queue()
        # self.Q['Queue']['workroundQ'] = self.m.Queue()
        #setup for tcp
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(self.tcptimeout)
        bypasscover = self.Par['bypasscover']
        self.cover = MOXA(m)
        if bypasscover == False: 
            self.cover.bypass = False   
            coverP = Process(target=self.cover.run,name='Cover_server')
            coverP.start()
            self.logger.warning(f'Detector Cover Fuction Enable')
        else:
            self.cover.bypass = True
            self.logger.warning(f'Byass detector Cover function!')
        
        self.preserver()
        # time.sleep(2)
        # self.logger.debug("Par After epicsPV Start=======")
        # self.logger.debug(self.Par)
        # self.logger.debug(f'TYPE:{type(self.Par)}')
        # self.logger.debug("Par End========")
        self.ca=myepics(self.logger)

    def preserver(self):
        self.epcisPV_ = Process(target=self.epicsPVP, args=(self.Par,self.Q,self.cover,))
        self.epcisPV_.start()
        self.Atten_ = Process(target=self.Attenserver, args=(self.Par,self.Q,))
        self.Atten_.start()
        
        self.workroundmd3moving_ = Process(target=self.workroundmd3moving, args=(self.Par,self.Q,))
        self.workroundmd3moving_.start()
        time.sleep(3)

    def initconnection(self):
        
        self.logger.info("try to connect")
        trytime=0
        while True:
            try:
                #setup for tcp
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.settimeout(self.tcptimeout)
                self.logger.info("try to Connect to %s:%d" % (self.host, self.port))
                self.client.connect((self.host, self.port))
                
                
            except Exception as e:
                self.client.close()
                self.logger.debug(f'fail connect to {self.host} {self.port} Error ={e}')
                if trytime == 0:
                    # self.logger.debug(f'fail connect to {self.host} {self.port}')
                    self.logger.warning("connection to DCSS fail, I wait 1 sec then try again until sucess...")
                    trytime =1
                else:
                    self.logger.debug("connection fail wait 1 sec then try again")
                    
                time.sleep(1)
                continue
            break
        
        self.logger.info("DCSS connection success")
        ans = self.client.recv(4096)
        index = ans.decode().find('\x00')
#        print (f'DCSS answer:{ans}')
#        print (f'len:{len(ans)}')
        if ans[0:index].decode() == "stoc_send_client_type" :
            self.logger.debug("dcss ans correct!")
            echo="htos_client_is_hardware "+ self.dhsname
        else:
            self.logger.debug("dcss ans NOT correct!")
            echo="htos_client_is_hardware "+ self.dhsname
        self.logger.info ("Answer to DCSS:%s" % (echo))
        command = self.ansDHS(echo)
        self.client.sendall(command.encode())
        self.run()

    def run(self) :
        # self.logger.debug('Creat sub Process')
        self.Par['operationRecord'][:] = []#clear operationRecord
        # self.logger.debug(f'TYPE:{type(self.Par)}')
        
        reciver_ = Process(target=self.reciver, args=(self.Par,self.Q,self.client,))
        sender_ = Process(target=self.sender, args=(self.Par,self.Q,self.client,))
        Detector_ = Process(target=self.detector, args=(self.Par,self.Q,self.client,self.cover))
        # epcisPV_ = Process(target=self.epicsPV, args=(self.Par,Q,self.client,))
        # control_ = Process(target=self.controlCenter, args=(self.Par,self.Q,self.client,))
        
        
        # epcisPV_.start()
        # time.sleep(1)
        # control_.start()
        reciver_.start()
        sender_.start()
        Detector_.start()
        
        reciver_.join()
        sender_.join()
        Detector_.join()
        # epcisPV_.join()
        # control_.join()
        self.initconnection()
        
    def detector(self,Par,Q,tcpclient,coverdhs):
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        DetctorQ = Q['Queue']['ControlQ']
        # self.logger.warning(f'TYPE:{type(Par)}')
        DET = Detector.Eiger2X16M(Par,Q,coverdhs)
        DET.CommandMon()
    def waitMD3Ready(self,timeout=10):
        t0 = time.time()
        check = True
        while check:
            # md3_state = caget('07a:md3:Status ',as_string=True)
            # md3_state = caget('07a:md3:State ',as_string=True)
            md3_state = self.ca.caget('07a:md3:State',format = str)
            if md3_state== 'Ready' or md3_state== 'READY'or md3_state== 'READY\n':
                check = False
            else:
                self.logger.info(f'MD3 is busy:{md3_state}')  
            if (time.time()-t0)>timeout:
                self.logger.info(f'MD3 is busy:{md3_state} and timeout reach')     
                return False
            time.sleep(0.1)
        self.logger.info(f'MD3 is Ready')     
        return True    
    def start_oscillation(self,Par,Q,command):
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        ContrlQ = Q['Queue']['ControlQ']
        DetctorQ = Q['Queue']['DetectorQ']
        # self.logger.warning(f'TYPE:{type(Par)}')
        #stoh_start_oscillation gonio_phi shutter 3.0 1.0 45.000018
        #stoh_start_oscillation motorName shutter deltaMotor deltaTime startAngle
        #
        #List of scan parameter values, comma separated: Int,double,double,double,intframe_number (int):
        #frame ID just for logging purpose. It is different from ScanNumberOfFrames which is used in the detector multi-triggering inside scan_range.
        #start_angle (double): angle (deg) at which the shutter opens and omega speed is stable 
        #scan_range (double): omega relative move angle (deg) before closing the shutter
        #exposure_time (double): exposure time (sec) to control shutter command
        #number_of_passes (int): number of moves forward and reverse between start angle and end angle.
        scan_range = float(command[3])
        # scan_range = 0
        exposure_time = float(command[4])
        start_angle = float(command[5])
        fileindex = int(Par['Detector']['Fileindex'])
        number_of_passes = int(1)
        nimages = int(Par['Detector']['nimages'])
        Timeout = 30 + exposure_time
        
        LastTaskInfoPV = Par['collect']['LastTaskInfoPV']
        PV = Par['collect']['start_oscillationPV']
        NumberOfFramesPV = Par['collect']['NumberOfFramesPV']
        

        value = [fileindex,start_angle,scan_range,exposure_time,number_of_passes]
        self.logger.warning(f"MD3 Expouse Scan Start,with start_angle:{start_angle},scan_range:{scan_range},exposure_time:{exposure_time}, number_of_passes:{number_of_passes}  ")
        timeStart=time.time()
        # caput(NumberOfFramesPV,nimages) #has some problem on managers.DictProxy

        MD3state = self.waitMD3Ready()
        if MD3state:
            # state = caput(PV,value)
            # state = self.pipecaput(PV,value)
            state = self.ca.caput(PV,value)
        else:
            state = -1

        # if state != 1:
        #     self.logger.critical(f"Caput {PV} value {value} Fail!")

        # state = caput(PV,value)
        # if state != 1:
        #     self.logger.critical(f"Caput {PV} value {value} Fail!")
        # ca.initialize_libca()
        
        # chid = ca.create_channel(PV, connect=False, callback=None, auto_cb=True)
        
        # state = ca.put(chid,value, wait=True,timeout=1, callback=None, callback_data=None)
        # if state != 1:
        #     self.logger.critical(f"Caput {PV} value {value} Fail!")
        # print(caget(LastTaskInfoPV))
        time.sleep(0.5)
        Task = caget(LastTaskInfoPV)
        # print(Task)
        t0 = time.time()
        while str(Task[6]) == "null":
            time.sleep(0.1)
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
        
    def reciver(self,Par,Q,tcpclient) :
        #recive message from dcss
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        ContrlQ = Q['Queue']['ControlQ']
        DetctorQ = Q['Queue']['DetectorQ']
        AttenQ = Q['Queue']['attenQ']
        msg = ""
        abort_timeer = time.time()
        while True:
            #check command
            try:
                command = reciveQ.get(block=False)
                if isinstance(command,str):
                    if command == "exit" :
                        break
                else:
                    pass
            except:
                pass
            #recive data
            try:
                data = self.client.recv(40960)
#                print(f'data:{data}')
            except socket.timeout:
                # self.logger.debug ("socket.timeout")
                pass

            except socket.error:
                # Something else happened, handle error, exit, etc.
                self.logger.warning ("Error for socket error")
                sendQ.put("exit")
                # epicsQ.put("exit")
                DetctorQ.put("exit")
                break
            except Exception as e:
                self.logger.warning ("Error on socket: {e}")
                
            else:
                if len(data) == 0:
                    self.logger.warning ("orderly shutdown on DCSS server end")
                    sendQ.put("exit")
                    # epicsQ.put("exit")
                    DetctorQ.put("exit")
                    break
                else:
                    # got a message do something :)
                    self.logger.debug (f'recive {data}' )
                    self.logger.debug (f'after decode = {data.decode()}')
                    msg = msg + data.decode()
                    index = msg.find('\x00')
                    while index != -1:
                        
#                        print(f'msg:{msg.encode()}')
#                        print(f'index:{index}')
                        processdata=msg[0:index]
                        
                        msg = msg [index+1:]
                        # print(f'new msg:{msg}')

                        command = self.processrecvice(processdata).split(" ")
                        self.logger.debug(f"Got message from dcss : {command}")
                        if command[0] == "stoh_abort_all" and time.time()-abort_timeer >5:
                            abort_timeer = time.time()
                            self.logger.warning(f"Got {command}")
                            epicsQ.put(("stoh_abort_all",''))
                            DetctorQ.put(("stoh_abort_all",''))
                            AttenQ.put(("stoh_abort_all",''))
                            # self.logger.warning(f"debug {self.Par['operationRecord']=}")
                            for item in self.Par['operationRecord']:
                                operdoneCommand = ['operdone']
                                for command in item:
                                    operdoneCommand.append(command)
                                self.logger.info(f"send {item} for opdone")
                                sendQ.put(tuple(operdoneCommand))#('operdone',command[0],command[1],command[3])
                            toDcsscommand = 'htos_set_string_completed system_status normal {Abort!} black #d0d000'
                            sendQ.put(toDcsscommand)
                            pass
                        elif command[0] == "stoh_start_motor_move":
                            #"stoh_start_motor_move motorName destination
                            
                            #check motor state
                            if command[1] == 'camera_zoom':
                                epicsQ.put(("stoh_start_motor_move",command[1],command[2]))
                            elif command[1] == 'attenuation':
                                AttenQ.put(("stoh_start_motor_move",command[1],command[2]))
                            elif command[1] == 'FluoDetectorBack':
                                #todo
                                PV = '07a:md3:FluoDetectorIsBack'
                                # state = self.pipecaput(PV,int(float(command[2])))
                                state = self.ca.caput(PV,int(float(command[2])))
                                
                                # if state != 1:
                                #     self.logger.critical(f"Caput {PV} value {command[2]} Fail!")

                                sendQ.put(('endmove',command[1],command[2],'normal'), block=False)
                                pass
                            elif command[1] == 'robotmove':
                                pass#fake one
                                sendQ.put(('endmove',command[1],command[2],'normal'), block=False)
                            else:
                                try:
                                    GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
                                    MoveDone = self.Par['EPICS'][GUIname]['DMOV']
                                    Pos = self.Par['EPICS'][GUIname]['RBV']
                                    TargetPos = self.Par['EPICS'][GUIname]['VAL']
                                    if MoveDone:
                                        # not move
                                        epicsQ.put(("stoh_start_motor_move",command[1],command[2]),timeout=1)
                                        time.sleep(0.05)
                                    else:
                                        sendQ.put(('warning',f"{GUIname} is already moving"))
                                        
                                except :
                                    #todo if not inthe list
                                    self.logger.warning(f"command : {command} has problem")
                                    self.logger.debug(f"GUIname = {GUIname},Par: {self.Par} ")
                                    epicsQ.put(("stoh_start_motor_move",command[1],command[2]),timeout=1)
                            
                            
                            
                            # epicsQ.put(("stoh_start_motor_move",command[1],command[2]))
                            
                            pass
                        elif command[0] == "stoh_set_shutter_state":
                            #stoh_set_shutter_state shutterName state (state is open or closed.)
                            epicsQ.put((command[0],command[1],command[2]))
                            pass
                        elif command[0] == "stoh_start_oscillation":
                            #stoh_start_oscillation gonio_phi shutter 3.0 1.0 45.000018
                            #stoh_start_oscillation motorName shutter deltaMotor deltaTime startAngle
                            self.logger.info(f'Ask MD3 to start oscillation')
                            p = Process(target=self.start_oscillation, args=(self.Par,self.Q,command))
                            p.start()
                            pass
                        elif command[0] == "stoh_register_operation":
                            
                            pass
                        elif command[0] == "stoh_start_operation":
                            #stoh_start_operation operationName operationHandle [arg1 [arg2 [arg3 [...]]]]
                            #operationName is the name of the operation to be started.
                            #operationHandle is a unique handle currently constructed by calling the create_operation_handle procedure in BLU-ICE. This currently creates a handle in the following format:
                            #clientNumber.operationCounter
                            #where clientNumber is the number provided to the BLU-ICE by DCSS via the stog_login_complete message. DCSS will reject an operation message if the clientNumber does not match the client. The operationCounter is a number that the client should increment with each new operation that is started.
                            #arg1 [arg2 [arg3 [...]]] is the list of arguments that should be passed to the operation. It is recommended that the list of arguments continue to follow the general format of the DCS message structure (space separated tokens). However, this requirement can only be enforced by the writer of the operation handlers.

                            unknownFlag = False
                            pass
                            if command[1] == "detector_collect_image" :
                                command.pop(0)
                                pass
                            elif command[1] == "detector_collect_shutterless" :
                                command.pop(0)
                                # print(command)
                                DetctorQ.put(tuple(command))
                            elif command[1] == "detector_ratser_setup" :
                                command.pop(0)
                                # print(command)
                                DetctorQ.put(tuple(command))
                            elif command[1] == "detector_transfer_image" :
                                command.pop(0)
                                pass
                            elif command[1] == "detector_oscillation_ready" :
                                command.pop(0)
                                pass
                            elif command[1] == "detector_stop" :
                                # ['stoh_start_operation', 'detector_stop', '1.17', '']
                                command.pop(0)
                        
                                DetctorQ.put(tuple(command))
                                
                                # command = command[1:-1]
                                # newcommand = ('operdone',) + tuple(command)
                                
                                # sendQ.put(newcommand)
                            elif command[1] == "detector_reset_run" :
                                command.pop(0)
                                pass
                            elif command[1] == "detector_oscillation_ready" :
                                command.pop(0)
                                pass
                            elif command[1] == "getMD2Motor" :
                                #bypass it
                                #['stoh_start_operation', 'getMD2Motor', '1.1', 'CurrentApertureDiameterIndex']
                                #['stoh_start_operation', 'getMD2Motor', '1.2', 'change_mode']
                                sendQ.put(('operdone',command[1],command[2],command[3]))
                                command.pop(0)
                                 # self.logger.warning(f"operation from dcss : {command}")
                            elif command[1] == "startRasterScanEx" :
                                # ['stoh_start_operation', 'startRasterScanEx', '2.5', '1', '0.2', '0.1', '90', '-1.51537', '-0.00978', '1.45155', '0.57271', '10', '10', '0.1', '1', '1', '1']
                                self.logger.warning(f"startRasterScanEx operation from dcss : {command}")
                                command.pop(0)
                                epicsQ.put(tuple(command))
                            elif command[1] == "startRasterScan" :
                                # ['stoh_start_operation', 'startRasterScanEx', '2.5', '1', '0.2', '0.1', '90', '-1.51537', '-0.00978', '1.45155', '0.57271', '10', '10', '0.1', '1', '1', '1']
                                # ['stoh_start_operation', 'startRasterScan', '7.6', '0.05', '-0.2', '2', '5', '0', '269.999792', '0.5', '0', '']
                                self.logger.warning(f"startRasterScan operation from dcss : {command}")
                                command.pop(0)
                                epicsQ.put(tuple(command))
                            elif command[1] == "startScan4DEx" :
                                #['stoh_start_operation', 'startScan4DEx', '1.855', '0.00', '1.0', '0.2', '-0.013060', '-1.080313', '-0.027390', '-1.251581', '0.576619', '-0.013060', '-1.017883', '-0.027390', '-1.295141', '0.684219']                                  
                                self.logger.warning(f"startScan4DEx operation from dcss : {command}")
                                command.pop(0)
                                epicsQ.put(tuple(command))
                            elif command[1] == "centerLoop":
                                # ['stoh_start_operation', 'centerLoop', '116.2', '']
                                self.logger.warning(f"centerLoop operation from dcss : {command}")
                                command.pop(0)
                                epicsQ.put(tuple(command))                                  
                                
                            elif command[1] == "changeBeamSize":
                                self.logger.warning(f"changeBeamSize operation from dcss : {command}")
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                                pass
                            elif command[1] == "displayBeamSize":
                                self.logger.warning(f"displayBeamSize operation from dcss : {command}")
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                                pass
                            elif command[1] == "overlapBeamImage":
                                self.logger.warning(f"overlapBeamImage operation from dcss : {command}")
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                                pass
                            elif command[1] == "mutiPosCollect":
                                self.logger.warning(f"mutiPosCollect operation from dcss : {command}")
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                                pass
                            
                            elif command[1] == "detector_close_cover":
                                self.logger.warning(f"detector_close_cover operation from dcss : {command}")
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                                pass
                            elif command[1] == "detector_open_cover":
                                self.logger.warning(f"detector_open_cover operation from dcss : {command}")
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                                pass
                            else:
                                 self.logger.warning(f"Unkonw operation from dcss : {command}")
                                 unknownFlag = True

                            if unknownFlag:
                                pass
                            else:
                                #need record operation id for abort return correct state
                                self.logger.debug(f"Add op {command} to operationRecord")
                                self.Par['operationRecord'].append(command)
                                self.logger.debug(f"after add {self.Par['operationRecord'][:]=}")

                        elif command[0] == "stoh_read_ion_chambers":
                            #stoh_read_ion_chambers time repeat ch1 [ch2 [ch3 [...]]]
                            AttenQ.put(tuple(command))
                            pass
                        elif command[0] == "stoh_register_string":
                            if command[1] == 'currentBeamsize':
                                command.pop(0)
                                DetctorQ.put(tuple(command))
                            pass
                        elif command[0] == "stoh_register_real_motor":
                            #['stoh_register_real_motor', 'detector_z', 'detector_'z] 
                            #should update current motor state
                            #if not move report move htos_motor_move_completed and POS(VAL or RBV?
                            #if moving report htos_motor_move_started with VAL
                            #note if send move_completed seem will have abort on dcss so goback to update
                            if command[1] == 'attenuation':
                                AttenQ.put(("stoh_register_real_motor",command[1]))
                            elif command[1] == 'attenuation':
                                pass
                            else:
                                
                                try:
                                    GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
                                    MoveDone = self.Par['EPICS'][GUIname]['DMOV']
                                    Pos = self.Par['EPICS'][GUIname]['RBV']
                                    TargetPos = self.Par['EPICS'][GUIname]['VAL']
                                    # sendQ.put(f'htos_send_configuration {GUIname}')#not in our version
                                    #  htos_configure_device 
                                    # stoh_configure_real_motor detector_z EPICS detector_z 400.000000 900.100000 139.000000 78.740000 1000 350 -238 1 1 0 0 0 0 
                                    sendQ.put(f'htos_configure_device {command[1]}')#not in our version
                                    sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                                    if MoveDone:
                                        # self.logger.warning(f'motor {command[1]} at {Pos}')
                                        # sendQ.put(('endmove',command[1],Pos,'Normal'))
                                        # sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                                        pass
                                    else:
                                        # sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                                        sendQ.put(('startmove',command[1],TargetPos,'motor','Normal'))
                                except :
                                    self.logger.warning(f"command : {command} has problem")
                                    self.logger.debug(f"GUIname = {GUIname},Par: {self.Par} ")
                            


                                
                            # epicsQ.put((command[0],))
                            pass
                        elif command[0] == "stoh_configure_real_motor":
                            #ex ['stoh_configure_real_motor', 'gonio_phi', 'EPICS', 'gonio_phi', '119.000000', '1000.000000', '-1000.000000', '2500.000000', '325000', '50', '625', '0', '0', '0', '0', '0', '0']
                            # stoh_configure_real_motor
                            
                            # The format of the message is                            
                            # stoh_configure_real_motor motoName position upperLimit lowerLimit scaleFactor speed acceleration backlash lowerLimitOn upperLimitOn motorLockOn backlashOn reverseOn
                            # where                            
                            #     motor is the name of the motor to configure                            
                            #     position is the scaled position of the motor                            
                            #     upperLimit is the upper limit for the motor in scaled units                            
                            #     lowerLimit is the lower limit for the motor in scaled units                            
                            #     scaleFactor is the scale factor relating scaled units to steps for the motor                            
                            #     speed is the slew rate for the motor in steps/sec                            
                            #     acceleration is the acceleration time for the motor in seconds                            
                            #     backlash	is the backlash amount for the motor in steps                            
                            #     lowerLimitOn is a boolean (0 or 1) indicating if the lower limit is enabled                            
                            #     upperLimitOn is a boolean (0 or 1) indicating if the upper limit is enabled                            
                            #     motorLockOn	is a boolean (0 or 1) indicating if the motor is software locked                            
                            #     backlashOn is a boolean (0 or 1) indicating if backlash correction is enabled                            
                            #     reverseOn is a boolean (0 or 1) indicating if the motor direction is reversed                            
                            # This command requests that the hardware server change the configuration of a real motor. 
                            pass
                        
                        elif command[0] == "stoh_register_shutter":
                            #['stoh_register_shutter', 'shutter', 'closed', 'shutter\n']
                            epicsQ.put((command[0],command[1],command[2]))
                        elif command[0] == "stoh_register_pseudo_motor" :
                            #stoh_register_pseudo_motor energy standardVirtualMotor
                            if command[1] == 'attenuation':
                                AttenQ.put(("stoh_register_pseudo_motor",command[1]))
                            else:
                                GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
                                MoveDone = self.Par['EPICS'][GUIname]['DMOV']
                                Pos = self.Par['EPICS'][GUIname]['RBV']
                                TargetPos = self.Par['EPICS'][GUIname]['VAL']
                                if command[1] == 'energy':
                                    Pos = Pos*1000
                                    TargetPos = TargetPos*1000
                                    # print(f'Pos={Pos},TargetPos={TargetPos}')
                                if MoveDone:
                                    # sendQ.put(('endmove',command[1],Pos,'Normal'))
                                    sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                                else:
                                    sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                                    sendQ.put(('startmove',command[1],TargetPos,'motor','Normal'))
                        else:
                            self.logger.warning(f"Unknown command:{command[0]}")
                            # print(f'Unknown command:{command[0]}')
                        index = msg.find('\x00')
                    self.logger.debug(f'Remind str = {msg}')    
    def processrecvice(self,string):
        '''
        ex"           46            0 stoh_register_string tps_current tps_current\n\x00"
        ex"          20            0 stoh_abort_all soft"
        '''
        # print (f'process str:{string}')
        index = string.find("0")
        if index != -1:
            length = int(string[0:13])
            zeroindex = string.find("0",13)
            ans = string[zeroindex+2:zeroindex+length+1]
            # print (f'0 index@{index} length:{length}')
            # print (f'after process str:{ans} length:{len(ans)}')
            # print (ans.encode())
        else:
            ans=""
            # print(ans)
        return ans
                        
    def sender(self,Par,Q,tcpclient) :
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        while True:
            try:
                command = sendQ.get()
                if isinstance(command,str):
                    if command == "exit" :
                        self.logger.warning("Send Q get Exit")
                        break
                    else:
                        self.logger.info(f"Send direct command to dcss:{command}")
                        todcss = self.toDCSScommand(command)
                        tcpclient.sendall(todcss.encode())
                        
                elif isinstance(command,tuple) :
                    #command 0:command 1:motorname 2:position 3:type 4:state
                    echo = ""
                    if command[0] == "updatevalue" :
                        if command[3] == "motor":
                            #htos_update_motor_position motorname postion status
                            echo = "htos_update_motor_position " + str(command[1]) + " " +str(command[2]) + " " + str(command[4])
                        elif command[3]  == "ioncchamber" :
                            #htos_report_ion_chambers time ch1 counts1 [ch2 counts2 [ch3 counts3 [chN countsN]]]
                            # self.sendQ.put(('updatevalue',command[3] ,str(count),'ioncchamber',command[1]))
                            echo = "htos_report_ion_chambers " + str(command[4]) + " " + str(command[1]) + " " + str(command[2])  
                        elif command[3]  == "operation_update" :
                            #htos_operation_update operationName operationHandle arguments
                            echo = "htos_operation_update " + str(command[1]) + " " + str(command[2])
                        elif command[3] == "operation_completed" :   
                            #htos_operation_completed operationName operationHandle status arguments
                            echo = "htos_operation_completed " + str(command[1]) + " " + str(command[4])+ " " + str(command[2])
                        elif command[3] == "string" :
                            #htos_set_string_completed strname status arguments
                            echo = "htos_set_string_completed " + str(command[1]) + " " + str(command[4]) + " " + str(command[2])
                            if str(command[1]) == "TPSstate":
                                print(echo)
                        elif command[3] == "shutter" :
                            #form: self.sendQ.put(('updatevalue',dcssname,value,dcsstype))
                            #to: htos_report_shutter_state shutterName state
                            if command[2] == 1 :
                                state = "open"
                            else:
                                state = "closed"
                            echo = "htos_report_shutter_state " + str(command[1]) + " " + state
                        elif command[3] == "string" :
                            #htos_set_string_completed strname status arguments
                            echo = "htos_set_string_completed " + str(command[1]) + " " + str(command[4]) + " " + str(command[2])
                            # if str(command[1]) == "TPSstate":
                            #     print(echo)
                            
                        else :
                            self.logger.info (f'unkonw command type:{command[3]}')
                            
                    elif command[0] == "startmove" :
                        #htos_motor_move_started motorName position
                        echo = "htos_motor_move_started " + str(command[1]) + " " +str(command[2])
                        self.logger.info(f"{command[1]} startmove to {command[2]} ")
                        
                    elif command[0] == "endmove" :
                        #htos_motor_move_completed motorName position completionStatus
                        #Normal indicates that the motor finished its commanded move successfully.
                        #aborted indicates that the motor move was aborted.
                        #moving indicates that the motor was already moving.
                        #cw_hw_limit indicates that the motor hit the clockwise hardware limit.
                        #ccw_hw_limit indicates that the motor hit the counter-clockwise hardware limit.
                        #both_hw_limits indicates that the motor cable may be disconnected.
                        #unknown indicates that the motor completed abnormally, but the DHS software or the hardware controller does not know why.
                        echo = "htos_motor_move_completed " + str(command[1]) + " " +str(command[2]) + " " +str(command[3])
                        self.logger.info(f"{command[1]} move completed at {command[2]} with {command[3]} ")
                    elif command[0] == "warning" :
                        #htos_note Warning XXXX
                        echo = "htos_note Warning " + str(command[1])
                    elif command[0] == "htos_note" :
                        echo = "htos_note " + str(command[1])
                    elif command[0] == "operdone" :
                        #command[1] = operationName
                        #command[2] = operationHandle
                        #htos_operation_completed operationName operationHandle status arguments
                        # command2=command[1]
                        # print(command2)
                        args=""
                        
                        argslist = list(command)
                        if len(argslist) > 3:
                            argslist = argslist[3:]
                            for a in argslist:
                                # print(a)
                                args = args + " " + a
                        else:
                            print('no args add')
                            # args = ""
                    
                        echo = "htos_operation_completed " + str(command[1]) + " " + str(command[2])+ " " + "normal" + args
                        # REMOVE operation id form list
                        removeitem = None
                        for item in self.Par['operationRecord']:
                            #operation command 
                            # operationName operationHandle [arg1 [arg2 [arg3 [...]]]]
                            if item[1] == command[2]:
                                removeitem = item
                        if removeitem:
                            self.logger.debug(f'remove {removeitem} from operationRecord')
                            self.Par['operationRecord'].remove(removeitem)
                        # self.logger.warning(f"{removeitem=},{command=},{self.Par['operationRecord'][:]=}")
                    elif command[0] == "operupdate" :
                        #command[1] = operationName
                        #command[2] = operationHandle
                        #htos_operation_update operationName operationHandle arguments
                        # command2=command[1]
                        # print(command2)
                        args=""
                        
                        argslist = list(command)
                        if len(argslist) > 3:
                            argslist = argslist[3:]
                            for a in argslist:
                                # print(a)
                                args = args + " " + a
                        else:
                            print('no args add')
                            # args = ""
                    
                        echo = "htos_operation_update " + str(command[1]) + " " + str(command[2]) + args
                        # print('==',echo,'==')
                    else:
                        self.logger.info(f'Unknow commad:{command[0]}')
                    #send to dcss    
                    if echo == "":
                        pass
                    else:
                        todcss = self.toDCSScommand(echo)
                        #print(f'todcss:{todcss.encode()}')
                        #print(len(todcss.encode()))
                        self.logger.debug(f"Send message to dcss : {todcss}")
                        self.client.sendall(todcss.encode()) 
                    
                else:
                    pass
                    self.logger.warning(f'sender recive unknow type {type(command),{command}}')
            except Exception as e:
                self.logger.error(f"send process has error {e}")

        pass
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
            self.logger.error(f"Caput {PV} value {value} Fail={error}")
            # return False
            return 0

    def epicsPVP(self,Par,Q,coverdhs) :
        self.logger.info(f'start for EPICS dev')
        #init epics
        pass
        self.epicsPV=epicsdev(EpicsConfig.epicslist,Par,Q,EpicsConfig.epicsmotors,coverdhs=coverdhs)

        # set motor and PV allback
        self.epicsPV.setMotor()
        self.epicsPV.setcallback()
        self.epicsPV.epcisMon()
        self.epicsPV.clear_epics_Motor_callback()
        self.epicsPV.clear_epics_callback()
    def Attenserver(self,Par,Q):
        a = atten(Par)
        a.monitor(Q)
    def workroundmd3moving(self,Par,Q):
        b = workroundmd3moving(Q=Q,logger=None)
        b.run()
#some Tools        
    def ansDHS(self,command):
        addNumber = 200 - len(command)
        addText=""
        for i in range(addNumber):
            addText = addText + '\x00'
        returnANS = command + addText
    #    print(len(command))
    #    print(addNumber)
    #    print(returnANS)
    #    print(len(returnANS))
        return returnANS
        
        
    def toDCSScommand(self,command):
        index = len(command)+1
        command = self.addspace(index)+"            0 "+ command +"\x00"
        return command
    
    def addspace(self,number):
        addspaceN=0
        addspaceN = 12-len(str(number))
        ans=""
        for x in range(addspaceN):
            ans = ans + " "
        ans = ans + str(number)
        return ans

    def FindEpicsMotorInfo(self,target,name='PVname',*args):
        '''
         ex: guiname = self.FindEpicsMotorInfo(detector_z,'dcssname','GUIname')

        Parameters
        ----------
        target : TYPE
            DESCRIPTION.
        name : TYPE, optional
            DESCRIPTION. The default is 'PVname'.
        *args : TYPE
            DESCRIPTION.

        Returns
        -------
        ans : TYPE
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


    def quit(self,signum,frame):
        self.logger.critical(f'EPICS DHS Offline')
        self.Q['Queue']['reciveQ'].put('exit')
        self.Q['Queue']['sendQ'].put('exit')
        self.Q['Queue']['epicsQ'].put('exit')
        self.Q['Queue']['ControlQ'].put('exit')
        self.Q['Queue']['DetectorQ'].put('exit')
        self.Q['Queue']['attenQ'].put('exit')
        self.client.close()
        
        # self.logger.debug(f"PID : {os.getpid()} DHS closed, Par= {self.Par}")
        self.logger.debug(f"PID : {os.getpid()} DHS closed")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
        # self.logger.critical(f'm pid={self.m._process.ident}')
        # self.m.shutdown()
        active_children = mp.active_children()
        if len(active_children)>0:
            for item in active_children:
                self.logger.warning(f'Last try to kill {item.pid}')
                os.kill(item.pid,signal.SIGKILL)
        sys.exit()
####test section
def serverTCP(port):
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(('127.0.0.1', port))
    serversocket.listen(1)
    print("setup done for TCPserver")
    return serversocket

def wait_For_Conn(server):
    print("wait for connect")
    client, addr = server.accept()
    ip,port = addr
    print('get a client from:',ip,':',port)
    pp = Process(target=handleEachClient,args=(client,))
    pp.start()
    pp.join()
    client.close()
    
def handleEachClient(client):
    print("hihi")
    read_buff = ''
    client.sendall(b'stoc_send_client_type')
    read_buff = client.recv(200)
    
    print(f'server recive: {read_buff}')
    time.sleep(1)
    client.sendall(b'testt')
    read_buff = ''
    while True:
        read_a_char = client.recv(1).decode('utf-8')
        if read_a_char != '\n':
            read_buff += read_a_char
        else:
            print(read_buff)
            client.sendall(('server echo ' + read_buff + '\n').encode('utf-8'))
            read_buff = ''
            ###
            
def test():
    print("strat!")
    port= 14241
    server = serverTCP(port)
    dhstest = DCSDHS()
    dhstest.host = "127.0.0.1"
    dhstest.port = port
    p = Process(target=wait_For_Conn,args=(server,))
    p.start()
    print("sleep 2sec")
    time.sleep(2)
    print("start test dhs")
    p2 = Process(target=dhstest.run)

    p2.start()
    p2.join()
    p.join()
    server.close()
    print ("end")


def quit(signum,frame):
    print("EPICS DHS Main cloesd")
    ToLineNotify(beamline='TPS07A',msg="EPICS DHS Main cloesd",nosound=False)
    # reciveQ = self.Par['Queue']['reciveQ']
    # sendQ = self.Par['Queue']['sendQ']
    # epicsQ = self.Par['Queue']['epicsQ']
    # reciveQ('exit')
    # sendQ.put("exit")
    # epicsQ.put("exit")
    # ToLineNotify("Test","beep~",False,stickerPackageId=446,stickerId=2005)
    sys.exit()
    pass

# def EpicsDHS(m):
    
#     #par load from config.py & EpicsConfig.py
#     EpicsDHS = DCSDHS(m)
#     p = Process(target=EpicsDHS.initconnection)

#     p.start()
#     p.join()
#     print ("end")
def ToLineNotify(beamline:str=None,msg:str=None,nosound:bool=False,stickerPackageId:int=None,stickerId:int=None,server='http://172.19.7.199:40000/job'):
    try:
        jsondata={}
        jsondata['beamline'] = beamline
        jsondata['msg'] = msg
        jsondata['nosound'] = nosound
        jsondata['stickerPackageId'] = stickerPackageId
        jsondata['stickerId'] = stickerId
        response = requests.post(server , json=jsondata)
        # print(response)
    except Exception as e:
        print(e)
    return response
    
if __name__ == "__main__":
    # mp.set_forkserver_preload()
    # mp.set_start_method('forkserver')
    # mp.set_start_method('spawn')
    # mp.set_start_method('fork')
    
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    # logger=logsetup.getloger2('Main')
    print(f'main PID = {os.getpid()}')
    m = Manager()
    Par = m.dict()
    # EpicsDHS(m)
    # self.logger.critical(f'm pid={self.m._process.ident}')
    EpicsDHS = DCSDHS(Par,m)
    print ("start*****************************")
    p = Process(target=EpicsDHS.initconnection)

    p.start()
    ToLineNotify(beamline='TPS07A',msg="EPICS DHS Started",nosound=True)
    print('*************************')
    
    while p.is_alive():
        time.sleep(0.1)
        pass

    print ("end")
    ToLineNotify(beamline='TPS07A',msg="EPICS DHS Closed",nosound=True)

    m.shutdown()