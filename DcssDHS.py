#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 16:46:13 2020

@author: admin
"""

# from epics import PV
import socket,time,signal,sys,os
# import multiprocessing as mp
from multiprocessing import Process, Queue, Manager
from epicsinit import epicsdev
import logsetup
# import epicsfile
import Config
import EpicsConfig

class DCSDHS():
    def __init__(self,managerpar=None) :
#        super(self.__class__,self).__init__(parent)
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        #load config
        # if managerpar == None:
        m = Manager()
        self.Par = m.dict()
        # else:
            # self.Par = managerpar
        print(f'TYPE:{type(self.Par)}')
        self.Par.update(Config.Par)
        print(f'TYPE:{type(self.Par)}')
        # self.Par['Queue']={}
        # self.Par.update({'Queue':{}})
        # print(f'TYPE:{type(self.Par)}')
        #set log
        self.logger = logsetup.getloger2('EPICSDHS',level = self.Par['Debuglevel'])
        self.logger.info("init EPICSDHS logging")
        self.logger.info("Logging show level = %s",self.Par['Debuglevel'])
        self.logger.debug("Par Start=======")
        self.logger.debug(self.Par)
        self.logger.debug(f'TYPE:{type(self.Par)}')
        self.logger.debug("Par End========")
        
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
        #setup for tcp
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(self.tcptimeout)
        
        self.epcisPV_ = Process(target=self.epicsPV, args=(self.Par,self.Q,self.client,))
        self.epcisPV_.start()
        time.sleep(1)
        
    def initconnection(self):
        
        self.logger.info("try to connect")
        trytime=0
        while True:
            try:
                self.client.connect((self.host, self.port))
                self.logger.info("try to Connect to %s:%d" % (self.host, self.port))
                
            except:
                if trytime == 0:
                    self.logger.debug(f'fail connect to {self.host} {self.port}')
                    self.logger.critical("connection to DCSS fail, I wait 1 sec then try again until sucess...")
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
#        print("RUN")
        #creat reciver, sender ,PV process
        self.logger.debug('Creat sub Process')
        # self.Par['Queue']['reciveQ'] = Queue() 
        # self.Par['Queue']['sendQ'] = Queue() 
        # self.Par['Queue']['epicsQ'] = Queue()
        # self.Par['Queue']['ControlQ'] = Queue()
        # Q={'Queue':{}}
        # Q['Queue']['reciveQ'] = Queue() 
        # Q['Queue']['sendQ'] = Queue() 
        # Q['Queue']['epicsQ'] = Queue()
        # Q['Queue']['ControlQ'] = Queue()
        # self.Par.update(temp)
        self.logger.debug(f'TYPE:{type(self.Par)}')
        
        reciver_ = Process(target=self.reciver, args=(self.Par,self.Q,self.client,))
        sender_ = Process(target=self.sender, args=(self.Par,self.Q,self.client,))
        # epcisPV_ = Process(target=self.epicsPV, args=(self.Par,Q,self.client,))
        # control_ = Process(target=self.controlCenter, args=(self.Par,self.Q,self.client,))
        
        
        # epcisPV_.start()
        # time.sleep(1)
        # control_.start()
        reciver_.start()
        sender_.start()
        
        reciver_.join()
        sender_.join()
        # epcisPV_.join()
        # control_.join()
        self.initconnection()
        
    def controlCenter(self,Par,Q,tcpclient):
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        ContrlQ = Q['Queue']['ControlQ']
        
    def reciver(self,Par,Q,tcpclient) :
        #recive message from dcss
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        ContrlQ = Q['Queue']['ControlQ']
        msg = ""
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
                data = self.client.recv(4096)
#                print(f'data:{data}')
            except socket.timeout:
                pass

            except socket.error:
                # Something else happened, handle error, exit, etc.
                self.logger.critical ("Error for socket error")
                sendQ.put("exit")
                epicsQ.put("exit")
                break
            else:
                if len(data) == 0:
                    self.logger.critical ("orderly shutdown on DCSS server end")
                    sendQ.put("exit")
                    epicsQ.put("exit")
                    break
                else:
                    # got a message do something :)
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
                        if command[0] == "stoh_abort_all":
                            epicsQ.put(("stoh_abort_all",''))
                            pass
                        elif command[0] == "stoh_start_motor_move":
                            #"stoh_start_motor_move motorName destination
                            epicsQ.put(("stoh_start_motor_move",command[1],command[2]))
                            pass
                        elif command[0] == "stoh_set_shutter_state":
                            #stoh_set_shutter_state shutterName state (state is open or closed.)
                            epicsQ.put((command[0],command[1],command[2]))
                            pass
                        elif command[0] == "stoh_start_oscillation":
                            #stoh_start_oscillation motorName shutter deltaMotor deltaTime
                            pass
                        elif command[0] == "stoh_start_operation":
                            #stoh_start_operation operationName operationHandle [arg1 [arg2 [arg3 [...]]]]
                            #operationName is the name of the operation to be started.
                            #operationHandle is a unique handle currently constructed by calling the create_operation_handle procedure in BLU-ICE. This currently creates a handle in the following format:
                            #clientNumber.operationCounter
                            #where clientNumber is the number provided to the BLU-ICE by DCSS via the stog_login_complete message. DCSS will reject an operation message if the clientNumber does not match the client. The operationCounter is a number that the client should increment with each new operation that is started.
                            #arg1 [arg2 [arg3 [...]]] is the list of arguments that should be passed to the operation. It is recommended that the list of arguments continue to follow the general format of the DCS message structure (space separated tokens). However, this requirement can only be enforced by the writer of the operation handlers.
                            pass
                        elif command[0] == "stoh_read_ion_chambers":
                            #stoh_read_ion_chambers time repeat ch1 [ch2 [ch3 [...]]]
                            pass
                        elif command[0] == "stoh_register_string":
                            pass
                        elif command[0] == "stoh_register_real_motor":
                            #['stoh_register_real_motor', 'detector_z', 'detector_'z] 
                            #should update current motor state
                            #if not move report move htos_motor_move_completed and POS(VAL or RBV?
                            #if moving report htos_motor_move_started with VAL
                            #note if send move_completed seem will have abort on dcss so goback to update
                            GUIname, = self.FindEpicsMotorInfo(command[1],'dcssname','GUIname')
                            MoveDone = self.Par['EPICS'][GUIname]['DMOV']
                            Pos = self.Par['EPICS'][GUIname]['RBV']
                            TargetPos = self.Par['EPICS'][GUIname]['VAL']

                            if MoveDone:
                                # sendQ.put(('endmove',command[1],Pos,'Normal'))
                                sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                            else:
                                sendQ.put(('updatevalue',command[1],Pos,'motor','Normal'))
                                sendQ.put(('startmove',command[1],TargetPos,'motor','Normal'))
                                
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
                        else:
                            print(f'Unknown command:{command[0]}')
                        index = msg.find('\x00')
                        
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
            print (ans.encode())
        else:
            ans=""
            print(ans)
        return ans
                        
    def sender(self,Par,Q,tcpclient) :
        reciveQ = Q['Queue']['reciveQ']
        sendQ = Q['Queue']['sendQ']
        epicsQ = Q['Queue']['epicsQ']
        while True:
            
            command = sendQ.get()
            if isinstance(command,str):
                if command == "exit" :
                    break
                else:
                    tcpclient.sendall(command.encode())
            elif isinstance(command,tuple) :
                #command 0:command 1:motorname 2:position 3:type 4:state
                echo = ""
                if command[0] == "updatevalue" :
                    if command[3] == "motor":
                        #htos_update_motor_position motorname postion status
                        echo = "htos_update_motor_position " + str(command[1]) + " " +str(command[2]) + " " + str(command[4])
                    elif command[3]  == "ioncchamber" :
                        #htos_report_ion_chambers time ch1 counts1 [ch2 counts2 [ch3 counts3 [chN countsN]]]
                        echo = "htos_report_ion_chambers " + str(command[1]) + " " + str(command[2])  
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
                        
                    else :
                        self.logger.info (f'unkonw command type:{command[3]}')
                        
                elif command[0] == "startmove" :
                    #htos_motor_move_started motorName position
                    echo = "htos_motor_move_started " + str(command[1]) + " " +str(command[2])
                    
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
                elif command[0] == "warning" :
                    #htos_note Warning XXXX
                    echo = "htos_note Warning " + str(command[1])

                else:
                    self.logger.info(f'Unknow commad:{command[0]}')
                #send to dcss    
                
                todcss = self.toDCSScommand(echo)
                #print(f'todcss:{todcss.encode()}')
                #print(len(todcss.encode()))
                self.logger.debug(f"Send message to dcss : {todcss}")
                self.client.sendall(todcss.encode()) 
                
            else:
                pass
        pass

    def epicsPV(self,Par,Q,tcpclient) :
        #init epics

        self.epicsPV=epicsdev(EpicsConfig.epicslist,Par,Q,EpicsConfig.epicsmotors)

        #set motor and PV allback
        self.epicsPV.setMotor()
        self.epicsPV.setcallback()
        self.epicsPV.epcisMon()
        self.epicsPV.clear_epics_Motor_callback()
        self.epicsPV.clear_epics_callback()
        
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
        
        self.logger.debug(f"PID : {os.getpid()} DHS closed, Par= {self.Par} TYPE:{type(self.Par)}")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
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
    # reciveQ = self.Par['Queue']['reciveQ']
    # sendQ = self.Par['Queue']['sendQ']
    # epicsQ = self.Par['Queue']['epicsQ']
    # reciveQ('exit')
    # sendQ.put("exit")
    # epicsQ.put("exit")
    
    sys.exit()
    pass

def EpicsDHS(par=None):
    
    #par load from config.py & EpicsConfig.py
    EpicsDHS = DCSDHS(par)
    p = Process(target=EpicsDHS.initconnection)

    p.start()
    p.join()
    print ("end")

    
if __name__ == "__main__":
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    logger=logsetup.getloger2('Main')
    # m = Manager()
    # Par = m.dict()
    EpicsDHS()
