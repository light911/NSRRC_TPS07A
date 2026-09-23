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
from multiprocessing.connection import wait as mp_wait
import multiprocessing as mp
from threading import Thread
from epicsinit import epicsdev
import logsetup
# import epicsfile
import Config
import EpicsConfig,requests,math
import Detector
from Flux07A.AttenServer import atten
from DetectorCoverV2 import MOXA
from CVLS_dhs.cvls_control import CVLSController
class DCSDHS():
    def __init__(self,par:dict=None,m:Manager=None) :
#        super(self.__class__,self).__init__(parent)
        #set before installing the handler: SIGINT can fire any time after this.
        #only this pid may run quit(); forked workers inherit the handler but
        #must ignore it (ctrl+c hits the whole process group). keep the manager
        #pid so the shutdown SIGKILL sweep can spare it and let __main__ shut it
        #down cleanly.
        self._shutting_down = False
        self._main_pid = os.getpid()
        self._manager_pid = m._process.pid if m is not None else None
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
        self.logger = logsetup.getloger2('EPICSDHS',LOG_FILENAME='/home/blctl/Desktop/log/EpicsLog.txt',level = self.Par['Debuglevel'],bypassline=False)
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
        self.Q['Queue']['CVLSQ'] = Queue()
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
        self.coverP_ = None
        if bypasscover == False:
            self.cover.bypass = False
            self.coverP_ = Process(target=self.cover.run,name='Cover_server')
            self.coverP_.start()
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
        self.CVLS_ = Process(target=self.CVLSserver, args=(self.Par,self.Q,))
        self.CVLS_.start()

        self.workroundmd3moving_ = Process(target=self.workroundmd3moving, args=(self.Par,self.Q,))
        self.workroundmd3moving_.start()
        time.sleep(3)

    def checkservers(self):
        '''restart dead service processes. a queue must never lose its only
        consumer: a libca callback crash in epicsPVP would otherwise leave
        every zoom/motor/abort command unserved forever'''
        services = {
            'epcisPV_':            (self.epicsPVP,           (self.Par,self.Q,self.cover,)),
            'Atten_':              (self.Attenserver,        (self.Par,self.Q,)),
            'CVLS_':               (self.CVLSserver,         (self.Par,self.Q,)),
            'workroundmd3moving_': (self.workroundmd3moving, (self.Par,self.Q,)),
        }
        if self.coverP_ is not None:
            services['coverP_'] = (self.cover.run, ())
        for attr,(target,args) in services.items():
            #shutdown in progress: dead children are intentional, do not revive
            if self._shutting_down:
                return
            proc = getattr(self,attr)
            if not proc.is_alive():
                #CRITICAL also pushes a LINE notify
                self.logger.critical(f'Service process {attr} (pid={proc.pid}, exitcode={proc.exitcode}) died! restarting it')
                newproc = Process(target=target, args=args, name=attr)
                newproc.start()
                setattr(self,attr,newproc)

    def serve_forever(self):
        #connect -> handshake -> session -> close -> reconnect
        #flat loop: the old initconnection()/run() called each other recursively,
        #leaking one stack frame and one socket per DCSS reconnect
        while True:
            if self.connect_dcss():
                self.run_session()
            try:
                self.client.close()
            except Exception as e:
                self.logger.warning(f'close DCSS socket fail: {e}')
            self.logger.warning('DCSS session ended, reconnect in 1 sec')
            time.sleep(1)

    def connect_dcss(self):
        '''connect to DCSS and do the handshake, return True when ready'''
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
        try:
            ans = self.client.recv(4096)
            index = ans.decode().find('\x00')
            if ans[0:index].decode() == "stoc_send_client_type" :
                self.logger.debug("dcss ans correct!")
            else:
                self.logger.debug("dcss ans NOT correct!")
            echo="htos_client_is_hardware "+ self.dhsname
            self.logger.info ("Answer to DCSS:%s" % (echo))
            command = self.ansDHS(echo)
            self.client.sendall(command.encode())
        except Exception as e:
            self.logger.warning(f'DCSS handshake fail: {e}')
            return False
        return True

    def run_session(self) :
        '''one DCSS session: workers run until the connection dies'''
        self.Par['operationRecord'][:] = []#clear operationRecord

        reciver_ = Process(target=self.reciver, args=(self.Par,self.Q,self.client,), name='reciver')
        sender_ = Process(target=self.sender, args=(self.Par,self.Q,self.client,), name='sender')
        Detector_ = Process(target=self.detector, args=(self.Par,self.Q,self.client,self.cover), name='detector')

        workers = (reciver_, sender_, Detector_)
        for w in workers:
            w.start()

        #the session is over as soon as ANY worker process dies: the reciver
        #breaks on a dead socket and forwards 'exit' to the others, so at
        #least one worker always exits promptly even if a sibling gets stuck
        mp_wait([w.sentinel for w in workers])
        self.logger.warning('a session worker died, tear down this DCSS session')

        #repeat the exits in case the reciver crashed before sending them
        for qname in ('sendQ','DetectorQ'):
            try:
                self.Q['Queue'][qname].put('exit')
            except Exception:
                pass

        #bounded join: a worker can hang at interpreter exit (queue feeder
        #flush / non-daemon child join) -- the old unbounded join here blocked
        #the reconnect forever until a manual ctrl+c (2026-07-13 incident:
        #workers got 'exit' at 13:22:59 but the session never ended)
        deadline = time.time() + 10
        for w in workers:
            w.join(max(0.1, deadline - time.time()))
        for w in workers:
            if not w.is_alive():
                continue
            self.logger.warning(f'{w.name} still alive after session end, SIGKILL it and its children')
            #SIGKILL, not terminate(): skip interpreter teardown so libca
            #children cannot segfault; reap descendants (setup worker, cover,
            #CAProcess) too -- the next session re-forks fresh ones
            for pid in self._descendant_pids(w.pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            w.kill()
            w.join(5)

        #drain leftovers so the next session cannot eat a stale 'exit'
        #(the extra 'Send Q get Exit' right after a reconnect was exactly that)
        for qname in ('reciveQ','sendQ','DetectorQ'):
            q = self.Q['Queue'][qname]
            while True:
                try:
                    q.get(block=False)
                except Exception:
                    break
    #no used
    # def CVLScontrol(self,Par,Q,tcpclient):
    #     reciveQ = Q['Queue']['reciveQ']
    #     sendQ = Q['Queue']['sendQ']
    #     epicsQ = Q['Queue']['epicsQ']
    #     ContrlQ = Q['Queue']['ControlQ']
    #     DetctorQ = Q['Queue']['DetectorQ']
    #     CvlsQ = Q['Queue']['CVLSQ']
    #     CVLS = CVLSController(Par,Q)
    #     CVLS.run()
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
                return True
            else:
                self.logger.info(f'MD3 is busy:{md3_state}')  
            if (time.time()-t0)>timeout:
                self.logger.info(f'MD3 is busy:{md3_state} and timeout reach')     
                return False
            time.sleep(0.1)
        self.logger.info(f'MD3 is Ready')     
        return True    
    def cal_post_tri_time(self,post_tri_time,scan_range,exposure_time,start_angle,nimages):
        single_exposure_time = exposure_time / nimages
        scanspeed = scan_range/exposure_time
        addrangetimes = math.ceil(post_tri_time/single_exposure_time)
        # delaytime = addrangetimes * single_exposure_time - exposure_time
        new_start_angle =  start_angle - (scanspeed * single_exposure_time * addrangetimes)
        new_scanrange = scan_range + (scanspeed * single_exposure_time * addrangetimes)
        new_exposure_time = exposure_time + (single_exposure_time * addrangetimes)
        true_start_angle = new_start_angle + post_tri_time * scanspeed
        self.logger.warning(f'{addrangetimes=},{single_exposure_time=}')
        self.logger.warning(f'new_scanrange={new_scanrange},new_exposure_time={new_exposure_time},new_start_angle={new_start_angle},true_start_angle={true_start_angle}')
        return new_scanrange,new_exposure_time,new_start_angle,nimages,true_start_angle
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
        # nimages = int(Par['Detector']['nimages'])
        nimages = self.ca.caget('07a-ES:timing:nimage',format=int)
        Timeout = 60 + exposure_time #for 2ms 2deg exp. this time need more(~42sec)
        
        LastTaskInfoPV = Par['collect']['LastTaskInfoPV']
        PV = Par['collect']['start_oscillationPV']
        NumberOfFramesPV = Par['collect']['NumberOfFramesPV']

        post_tri_timePV = self.Par['collect']['post_tri_timePV']
        post_tri_time = self.ca.caget(post_tri_timePV,format=float)
        if post_tri_time == 0 :
            pass
        elif post_tri_time > 0:
            new_scanrange,new_exposure_time,new_start_angle,nimages,delaytime = self.cal_post_tri_time(post_tri_time,scan_range,exposure_time,start_angle,nimages)
            scan_range = new_scanrange
            exposure_time = new_exposure_time
            start_angle = new_start_angle
            
            pass


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
        #recive message from dcss, decode it and dispatch to a handler
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        DetctorQ = Q['Queue']['DetectorQ']
        msg = ""
        self._abort_timer = time.time()
        handlers = {
            "stoh_abort_all":             self._cmd_abort_all,
            "stoh_start_motor_move":      self._cmd_start_motor_move,
            "stoh_set_shutter_state":     self._cmd_set_shutter_state,
            "stoh_start_oscillation":     self._cmd_start_oscillation,
            "stoh_register_operation":    self._cmd_ignore,
            "stoh_start_operation":       self._cmd_start_operation,
            "stoh_read_ion_chambers":     self._cmd_read_ion_chambers,
            "stoh_register_string":       self._cmd_register_string,
            "stoh_register_real_motor":   self._cmd_register_real_motor,
            "stoh_configure_real_motor":  self._cmd_ignore,
            "stoh_register_shutter":      self._cmd_register_shutter,
            "stoh_register_pseudo_motor": self._cmd_register_pseudo_motor,
        }
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
            except socket.timeout:
                # self.logger.debug ("socket.timeout")
                pass

            except socket.error:
                # Something else happened, handle error, exit, etc.
                self.logger.warning ("Error for socket error")
                sendQ.put("exit")
                DetctorQ.put("exit")
                break
            except Exception as e:
                self.logger.warning (f"Error on socket: {e}")

            else:
                if len(data) == 0:
                    self.logger.warning ("orderly shutdown on DCSS server end")
                    sendQ.put("exit")
                    DetctorQ.put("exit")
                    break
                else:
                    # got a message do something :)
                    # self.logger.debug (f'recive {data}' )
                    # self.logger.debug (f'after decode = {data.decode()}')
                    msg = msg + data.decode()
                    index = msg.find('\x00')
                    while index != -1:
                        processdata=msg[0:index]
                        msg = msg [index+1:]
                        command = self.processrecvice(processdata).split(" ")
                        self.logger.debug(f"Got message from dcss : {command}")
                        handler = handlers.get(command[0])
                        if handler:
                            handler(command)
                        else:
                            self.logger.warning(f"Unknown command:{command[0]}")
                        index = msg.find('\x00')
                    self.logger.debug(f'Remind str = {msg}')

#dcss command handlers, they run inside the reciver process
    def _cmd_ignore(self,command):
        #stoh_register_operation / stoh_configure_real_motor : nothing to do
        pass

    def _cmd_abort_all(self,command):
        #dcss may repeat abort, only react once per 5 sec
        if time.time() - self._abort_timer < 5:
            return
        self._abort_timer = time.time()
        sendQ = self.Q['Queue']['sendQ']
        self.logger.warning(f"Got {command}")
        self.Q['Queue']['epicsQ'].put(("stoh_abort_all",''))
        self.Q['Queue']['DetectorQ'].put(("stoh_abort_all",''))
        self.Q['Queue']['attenQ'].put(("stoh_abort_all",''))
        for item in self.Par['operationRecord']:
            operdoneCommand = ['operdone'] + list(item)
            self.logger.info(f"send {item} for opdone")
            sendQ.put(tuple(operdoneCommand))
        toDcsscommand = 'htos_set_string_completed system_status normal {Abort!} black #d0d000'
        sendQ.put(toDcsscommand)

    def _drop_operation_record(self,handle):
        #operationRecord entries are 'operationName operationHandle [arg ...]'
        #and exist so abort_all can complete whatever is still outstanding. Once
        #an operation has been reported completed it must come off the list.
        removeitem = None
        for item in self.Par['operationRecord']:
            if item[1] == handle:
                removeitem = item
        if removeitem:
            self.logger.debug(f'remove {removeitem} from operationRecord')
            self.Par['operationRecord'].remove(removeitem)

    def _cmd_start_motor_move(self,command):
        #stoh_start_motor_move motorName destination
        epicsQ = self.Q['Queue']['epicsQ']
        sendQ = self.Q['Queue']['sendQ']
        if command[1] == 'camera_zoom':
            epicsQ.put(("stoh_start_motor_move",command[1],command[2]))
        elif command[1] == 'attenuation':
            self.Q['Queue']['attenQ'].put(("stoh_start_motor_move",command[1],command[2]))
        elif command[1] == 'FluoDetectorBack':
            PV = '07a:md3:FluoDetectorIsBack'
            state = self.ca.caput(PV,int(float(command[2])))
            sendQ.put(('endmove',command[1],command[2],'normal'), block=False)
        elif command[1] == 'robotmove':
            #fake one
            sendQ.put(('endmove',command[1],command[2],'normal'), block=False)
        else:
            GUIname = None
            try:
                GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
                MoveDone = self.Par[f'EPICS.{GUIname}.DMOV']
                if MoveDone:
                    # not move
                    epicsQ.put(("stoh_start_motor_move",command[1],command[2]),timeout=1)
                    # time.sleep(0.05)
                else:
                    sendQ.put(('warning',f"{GUIname} is already moving"))
            except Exception as e:
                #not in the motor list, let epicsQ try anyway (old behavior)
                self.logger.warning(f"command : {command} has problem ({e})")
                self.logger.debug(f"GUIname = {GUIname}")
                epicsQ.put(("stoh_start_motor_move",command[1],command[2]),timeout=1)

    def _cmd_set_shutter_state(self,command):
        #stoh_set_shutter_state shutterName state (state is open or closed.)
        self.Q['Queue']['epicsQ'].put((command[0],command[1],command[2]))

    def _cmd_start_oscillation(self,command):
        #stoh_start_oscillation motorName shutter deltaMotor deltaTime startAngle
        #thread instead of fork: forking the CA-connected reciver per scan is
        #expensive and unsafe with libca
        self.logger.info(f'Ask MD3 to start oscillation')
        t = Thread(target=self.start_oscillation, args=(self.Par,self.Q,command), daemon=True)
        t.start()

    #operation name -> queue that executes it (None = accepted but nothing to do)
    OPERATION_ROUTES = {
        "detector_collect_image":       None,
        "detector_collect_shutterless": "DetectorQ",
        "detector_ratser_setup":        "DetectorQ",
        "detector_transfer_image":      None,
        "detector_oscillation_ready":   None,
        "detector_stop":                "DetectorQ",
        "detector_reset_run":           None,
        "detector_close_cover":         "DetectorQ",
        "detector_open_cover":          "DetectorQ",
        "changeBeamSize":               "DetectorQ",
        "displayBeamSize":              "DetectorQ",
        "overlapBeamImage":             "DetectorQ",
        "mutiPosCollect":               "DetectorQ",
        "SSXCollect":                   "DetectorQ",
        "SSXStopCollect":               "DetectorQ",
        "startRasterScanEx":            "epicsQ",
        "startRasterScan":              "epicsQ",
        "startScan4DEx":                "epicsQ",
        "centerLoop":                   "epicsQ",
        "setBackLightColor":            "CVLSQ",
        "switchSampleEnvironment":      "CVLSQ",
    }

    def _cmd_start_operation(self,command):
        #stoh_start_operation operationName operationHandle [arg1 [arg2 [...]]]
        #operationHandle format: clientNumber.operationCounter
        sendQ = self.Q['Queue']['sendQ']
        opname = command[1]
        if opname == "getMD2Motor":
            #bypass it, just reply operation completed
            #['stoh_start_operation', 'getMD2Motor', '1.2', 'change_mode']
            sendQ.put(('operdone',command[1],command[2],command[3]))
            command.pop(0)
        elif opname in self.OPERATION_ROUTES:
            qname = self.OPERATION_ROUTES[opname]
            self.logger.warning(f"{opname} operation from dcss : {command}")
            command.pop(0)
            if qname:
                self.Q['Queue'][qname].put(tuple(command))
        else:
            self.logger.warning(f"Unkonw operation from dcss : {command}")
            return
        #need record operation id for abort return correct state
        self.logger.debug(f"Add op {command} to operationRecord")
        self.Par['operationRecord'].append(command)

    def _cmd_read_ion_chambers(self,command):
        #stoh_read_ion_chambers time repeat ch1 [ch2 [ch3 [...]]]
        self.Q['Queue']['attenQ'].put(tuple(command))

    def _cmd_register_string(self,command):
        if command[1] == 'currentBeamsize':
            command.pop(0)
            self.Q['Queue']['DetectorQ'].put(tuple(command))
        elif command[1] == 'backlight_status':
            #dcss just (re)registered the string, so push what the light is
            #really doing instead of leaving bluice on the config default
            self.Q['Queue']['CVLSQ'].put(("report_status",))

    def _cmd_register_real_motor(self,command):
        #['stoh_register_real_motor', 'detector_z', 'detector_z']
        #report current state: position update, plus move_started when moving
        #(sending move_completed here triggers an abort on dcss, so don't)
        sendQ = self.Q['Queue']['sendQ']
        if command[1] == 'attenuation':
            self.Q['Queue']['attenQ'].put(("stoh_register_real_motor",command[1]))
            return
        GUIname = None
        try:
            GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
            MoveDone = self.Par[f'EPICS.{GUIname}.DMOV']
            Pos = self.Par[f'EPICS.{GUIname}.RBV']
            TargetPos = self.Par[f'EPICS.{GUIname}.VAL']
            sendQ.put(f'htos_configure_device {command[1]}')#not in our version
            sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
            if not MoveDone:
                sendQ.put(('startmove',command[1],TargetPos,'motor','Normal'))
        except Exception as e:
            self.logger.warning(f"command : {command} has problem ({e})")
            self.logger.debug(f"GUIname = {GUIname}")

    def _cmd_register_shutter(self,command):
        #['stoh_register_shutter', 'shutter', 'closed', 'shutter\n']
        self.Q['Queue']['epicsQ'].put((command[0],command[1],command[2]))

    def _cmd_register_pseudo_motor(self,command):
        #stoh_register_pseudo_motor energy standardVirtualMotor
        sendQ = self.Q['Queue']['sendQ']
        if command[1] == 'attenuation':
            self.Q['Queue']['attenQ'].put(("stoh_register_pseudo_motor",command[1]))
            return
        GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
        MoveDone = self.Par[f'EPICS.{GUIname}.DMOV']
        Pos = self.Par[f'EPICS.{GUIname}.RBV']
        TargetPos = self.Par[f'EPICS.{GUIname}.VAL']
        if command[1] == 'energy':
            Pos = Pos*1000
            TargetPos = TargetPos*1000
        sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
        if not MoveDone:
            sendQ.put(('startmove',command[1],TargetPos,'motor','Normal'))
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
                            #same bookkeeping the operdone branch does, else an
                            #abort would complete this handle a second time
                            self._drop_operation_record(command[4])
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
                        self._drop_operation_record(command[2])
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
    def CVLSserver(self,Par,Q):
        c = CVLSController(Par,Q)
        c.monitor(Q)
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


    def _descendant_pids(self,root_pid):
        #walk /proc to collect every descendant pid of root_pid (linux only).
        #mp.active_children() only sees direct children, so it leaks grandchildren
        #(cover's asking_state, Detector's CAProcess) on shutdown.
        children = {}
        for entry in os.listdir('/proc'):
            if not entry.isdigit():
                continue
            try:
                with open(f'/proc/{entry}/stat') as f:
                    #comm may contain ')'; ppid is the field right after the last ')'
                    ppid = int(f.read().rsplit(')',1)[1].split()[1])
            except (OSError,IndexError,ValueError):
                continue
            children.setdefault(ppid,[]).append(int(entry))
        out,stack = [],[root_pid]
        while stack:
            for child in children.get(stack.pop(),[]):
                out.append(child)
                stack.append(child)
        return out

    def quit(self,signum,frame):
        #ctrl+c is delivered to the whole process group, so every forked worker
        #runs this handler. only the supervisor pid may shut down; a child that
        #ran the full quit would cross-kill its siblings, tear down the shared
        #Manager, and sys.exit() through libca teardown -- exactly the
        #FileNotFoundError / exitcode -9 cascade we are fixing. children just
        #ignore the signal and wait to be drained or killed by us.
        if os.getpid() != self._main_pid:
            return
        #stop the supervisor from reviving children we are about to kill
        self._shutting_down = True
        self.logger.error(f'EPICS DHS Offline')
        #ask the queue-driven workers to stop cleanly first
        for q in ('reciveQ','sendQ','epicsQ','ControlQ','DetectorQ','attenQ','CVLSQ'):
            try:
                self.Q['Queue'][q].put('exit')
            except Exception:
                pass
        try:
            self.client.close()
        except Exception:
            pass
        #let workers drain 'exit' while the Manager is still alive
        time.sleep(1)
        #SIGKILL is the safe way to drop the libca/HTTP children (no interpreter
        #teardown -> no fork+libca segfault); reap the whole tree, not just direct
        #children, so cover/asking_state/CAProcess grandchildren go too. spare the
        #Manager so __main__ can shut it down cleanly.
        for pid in self._descendant_pids(os.getpid()):
            if pid == self._manager_pid:
                continue
            self.logger.warning(f'Last try to kill {pid}')
            try:
                os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.logger.debug(f"PID : {os.getpid()} DHS closed")
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
    p2 = Process(target=dhstest.serve_forever)

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
    response = None
    try:
        jsondata={}
        jsondata['beamline'] = beamline
        jsondata['msg'] = msg
        jsondata['nosound'] = nosound
        jsondata['stickerPackageId'] = stickerPackageId
        jsondata['stickerId'] = stickerId
        response = requests.post(server , json=jsondata, timeout=2)
        # print(response)
    except Exception as e:
        print(e)
    return response
    
if __name__ == "__main__":
    #everything here relies on fork semantics (children inherit Par proxy,
    #Queues and the DCSS socket); python 3.14 changes the linux default,
    #so pin it explicitly
    mp.set_start_method('fork')

    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    print(f'main PID = {os.getpid()}')
    m = Manager()
    Par = m.dict()
    EpicsDHS = DCSDHS(Par,m)
    print ("start*****************************")
    p = Process(target=EpicsDHS.serve_forever)

    p.start()
    ToLineNotify(beamline='TPS07A',msg="EPICS DHS Started",nosound=True)
    print('*************************')

    #supervise: respawn dead service processes while the DCSS loop runs
    while p.is_alive() and not EpicsDHS._shutting_down:
        time.sleep(2)
        if EpicsDHS._shutting_down:
            break
        EpicsDHS.checkservers()

    print ("end")
    ToLineNotify(beamline='TPS07A',msg="EPICS DHS Closed",nosound=True)

    try:
        m.shutdown()
    except Exception:
        pass