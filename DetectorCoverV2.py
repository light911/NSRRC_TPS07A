import requests,signal,sys,os
import json
import time
from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
from enum import Enum,auto
import logsetup
import Config

class State(Enum):
    Staring = auto()
    Reading = auto()
    Opening = auto()
    Closing = auto()

class MOXA():
    def __init__(self,m:Manager=None) -> None:
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        if not m:
            self.m = Manager()
        else:
            self.m = m
        self.Par = self.m.dict()
        self.Par.update(Config.Par)
        self.Par['Coverstate'] = None
        #set log
        self.logger = logsetup.getloger2('CoverDHS',LOG_FILENAME='./log/CoverLog.txt',level = self.Par['Debuglevel'],bypassline=False)
        self.logger.info("init CoverDHS logging")
        self.logger.info("Logging show level = %s",self.Par['Debuglevel'])
        


        #set some par
        self.ip='10.7.1.205'
        self.header={'Accept': 'vdn.dac.v1','Content-Type':'application/json'}
        self.di_url = f'http://{self.ip}/api/slot/0/io/di'
        self.do_url = f'http://{self.ip}/api/slot/0/io/do'
        #channel setup
        self.DO_CloseCover= 0
        self.DO_OpenCover= 1
        self.DO_ReleaseCover= 2

        self.DI_CoverisClosed = 0
        self.DI_Coverisopen = 1
        self.DI_Ready = 2
        #for outside reading
        self.Coverstate=None
        self.stop = False
        self.state = State.Staring
        # self.Par['stateQ'] = Queue()
        # self.Par['commandQ'] = Queue()
        # self.Par['returnQ'] = Queue()
        self.Q={}
        self.Q['stateQ'] = Queue()
        self.Q['commandQ'] = Queue()
        self.bypass = False
        
    def run(self):
        # _asking_state = Process(target=self.asking_state, args=(self.Par,),name = 'cover_server_run')
        _asking_state = Process(target=self.asking_state, args=(self.Par,),name = 'asking_state_server')
        _asking_state.start()
        #update state
        stateQ = self.Q['stateQ']
        
        while not self.stop:
            command = stateQ.get(block=True)
            if isinstance(command,str):
                if command == "exit" :
                    self.stop = True
            elif isinstance(command,tuple) :
                pass
                if command[0] == 'Coverstate':
                    # if self.Coverstate != command[1]:
                    #     self.logger.info(f'Update Coverstate form {self.Coverstate} to {command[1]}')
                    # self.Coverstate = command[1]
                    pass
                elif command[0] == 'Getstate':
                    # returnQ.put(('Getstate',self.Coverstate))
                    pass
            else:
                pass

    
    def asking_state(self,Par):
        # stateQ = Q['stateQ']
        commandQ = self.Q['commandQ']
        while not self.stop:
            try:
                command = commandQ.get(block=False)
            except:
                command = None
            if isinstance(command,str):
                if command == "exit" :
                    self.stop = True
            elif isinstance(command,tuple) :
                self.logger.info(f'{command}')
                if command[0] == "DO_OpenCover":
                    self.set_do_state(self.DO_OpenCover,command[1])
                elif command[0] == "DO_CloseCover":
                    self.set_do_state(self.DO_CloseCover,command[1])
                else:
                    self.logger.warning(f'Unknow command :{command}')
                newstate = self.Coverstate
            else:
                pass
                ans = self.show_current_state()
                if ans == 'Open':
                    newstate = True
                    # stateQ.put(('Coverstate',True))
                    Par['Coverstate'] = True
                elif ans == 'Closed':
                    newstate = False
                    # self.logger.warning(f'{type(Par)},{Par=}')
                    # stateQ.put(('Coverstate',False))
                    Par['Coverstate'] = False
                else:
                    newstate = None
                    # stateQ.put(('Coverstate',None))
                    Par['Coverstate'] = None
            
            if self.Coverstate != newstate:
                self.logger.info(f'Update Coverstate form {self.Coverstate} to {newstate}')
            self.Coverstate = newstate
            time.sleep(0.2)#update rate

    def askforAction(self,action = 'open',timeout=5):
        self.logger.info(f'Got ask for {action} cover')
        t0 = time.time()       
        commandQ = self.Q['commandQ']
        stop = False
        settingflag = True
        while not stop:
            # stateQ.put(('Getstate'))
            # command = returnQ.get(block=True)
            # a,Coverstate = command
            Coverstate = self.Par['Coverstate']
            if self.bypass:#not used yet
                pass
                stop = True
                if action == 'open':
                    self.Par['Coverstate'] = True
                else:
                    self.Par['Coverstate'] = False

            else:
                if Coverstate == True and action == 'open':
                    # print('already open')
                    self.logger.info(f'Cover already open, Done for command')
                    # self.set_do_state(self.DO_OpenCover,0)
                    commandQ.put(('DO_OpenCover',0))
                    stop = True
                elif Coverstate == False and action == 'close':
                    self.logger.info(f'Cover already close, Done for command')
                    # self.set_do_state(self.DO_CloseCover,0)
                    commandQ.put(('DO_CloseCover',0))
                    stop = True
                    pass
                elif action == 'close':
                    if settingflag:
                        #need set DO
                        self.logger.info('Try to close')
                        t0=time.time()
                        # print("DO_OpenCover 0" )
                        # self.set_do_state(self.DO_OpenCover,0)
                        # time.sleep(0.1)
                        # # print("DO_CloseCover 0" )
                        # self.set_do_state(self.DO_CloseCover,0)
                        # time.sleep(0.1)
                        # print("DO_CloseCover 1" )
                        # self.set_do_state(self.DO_CloseCover,1)
                        commandQ.put(('DO_CloseCover',1))
                        settingflag = False#already setting, now check
                    #setDI to close
                elif action == 'open':
                    if settingflag:
                        self.logger.info(f'Try to open cover')
                        t0=time.time()
                        # print("DO_CloseCover 0" )
                        # self.set_do_state(self.DO_CloseCover,0)
                        # time.sleep(0.1)
                        # # print("DO_OpenCover 0" )
                        # self.set_do_state(self.DO_OpenCover,0)
                        # time.sleep(0.1)
                        # print("DO_OpenCover 1" )
                        # self.set_do_state(self.DO_OpenCover,1)
                        commandQ.put(('DO_OpenCover',1))
                        settingflag = False#already setting, now check
                else:
                    pass
            if (time.time()-t0) > timeout:
                # self.set_do_state(self.DO_CloseCover,0)
                # self.set_do_state(self.DO_OpenCover,0)
                commandQ.put(('DO_CloseCover',0))
                commandQ.put(('DO_OpenCover',0))
                self.logger.critical(f"Detector Cover operation Timeout! in {timeout} sec, {action=},{Coverstate=}")
                stop = True
            
        #done for command
        self.logger.info(f'Total time for {action} = {time.time()-t0}')
        # self.set_do_state(self.DO_CloseCover,0)
        # self.set_do_state(self.DO_OpenCover,0)
    def askforAction_old(self,action = 'open',timeout=5):
        self.logger.info(f'Got ask for {action} cover')
        t0 = time.time()
        stateQ = self.Q['stateQ']
        returnQ = self.Q['returnQ']
        stop = False
        settingflag = True
        while not stop:
            # stateQ.put(('Getstate'))
            # command = returnQ.get(block=True)
            # a,Coverstate = command
            Coverstate = self.Par['Coverstate']

            if Coverstate == True and action == 'open':
                # print('already open')
                self.logger.info(f'Cover already open, Done for command')
                self.set_do_state(self.DO_OpenCover,0)
                stop = True
            elif Coverstate == False and action == 'close':
                self.logger.info(f'Cover already close, Done for command')
                self.set_do_state(self.DO_CloseCover,0)
                stop = True
                pass
            elif action == 'close':
                if settingflag:
                    #need set DO
                    self.logger.info('Try to close')
                    t0=time.time()
                    # print("DO_OpenCover 0" )
                    # self.set_do_state(self.DO_OpenCover,0)
                    # time.sleep(0.1)
                    # # print("DO_CloseCover 0" )
                    # self.set_do_state(self.DO_CloseCover,0)
                    # time.sleep(0.1)
                    # print("DO_CloseCover 1" )
                    self.set_do_state(self.DO_CloseCover,1)
                    settingflag = False#already setting, now check
                #setDI to close
            elif action == 'open':
                if settingflag:
                    self.logger.info(f'Try to open cover')
                    t0=time.time()
                    # print("DO_CloseCover 0" )
                    # self.set_do_state(self.DO_CloseCover,0)
                    # time.sleep(0.1)
                    # # print("DO_OpenCover 0" )
                    # self.set_do_state(self.DO_OpenCover,0)
                    # time.sleep(0.1)
                    # print("DO_OpenCover 1" )
                    self.set_do_state(self.DO_OpenCover,1)
                    settingflag = False#already setting, now check
            else:
                pass
            if (time.time()-t0) > timeout:
                self.set_do_state(self.DO_CloseCover,0)
                self.set_do_state(self.DO_OpenCover,0)
                self.logger.warning(f"Timeout! in {timeout} sec")
                stop = True
            
        #done for command
        self.logger.info(f'Total time for {action} = {time.time()-t0}')
        # self.set_do_state(self.DO_CloseCover,0)
        # self.set_do_state(self.DO_OpenCover,0)   


    def initcover(self):
        self.set_do_state(self.DO_ReleaseCover,1)
        self.set_do_state(self.DO_CloseCover,0)
        self.set_do_state(self.DO_OpenCover,0)
        #closed cover
        self.set_do_state(self.DO_CloseCover,1)

    def OpenCover(self):
        t0=time.time()
        print("DO_CloseCover 0" )
        self.set_do_state(self.DO_CloseCover,0)
        time.sleep(0.1)
        print("DO_OpenCover 0" )
        self.set_do_state(self.DO_OpenCover,0)
        time.sleep(0.1)
        print("DO_OpenCover 1" )
        self.set_do_state(self.DO_OpenCover,1)
        time.sleep(0.1)
        self.wait_for_state('open')
        time.sleep(0.1)
        self.set_do_state(self.DO_OpenCover,0)
        print(f'Total time = {time.time()-t0}')
    
    
    def CloseCover(self):
        t0=time.time()
        print("DO_OpenCover 0" )
        self.set_do_state(self.DO_OpenCover,0)
        time.sleep(0.1)
        print("DO_CloseCover 0" )
        self.set_do_state(self.DO_CloseCover,0)
        time.sleep(0.1)
        print("DO_CloseCover 1" )
        self.set_do_state(self.DO_CloseCover,1)
        time.sleep(0.1)
        self.wait_for_state('close')
        time.sleep(0.1)
        
        self.set_do_state(self.DO_CloseCover,0)
        print(f'Total time = {time.time()-t0}')

    def wait_for_state2(self,wait='open',timeout=5,interval=0.1):
        t0 = time.time()
        wating = True
        while wating:
            if wait == 'open':
                if self.Coverstate == True:
                    self.logger.info(f"In position! cover is {wait}, take {time.time()-t0} sec")
                    wating = False
                    return
            elif wait == 'close':
                if self.Coverstate == False:
                    self.logger.info(f"In position! cover is {wait}, take {time.time()-t0} sec")
                    wating = False
                    return
            else:
                pass
                time.sleep(interval)


            if (time.time()-t0) > timeout:
                self.set_do_state(self.DO_CloseCover,0)
                self.set_do_state(self.DO_OpenCover,0)
                self.logger.warning(f"Timeout! in {timeout} sec")
                wating = False
                
    def wait_for_state(self,wait='open',timeout=5,interval=0.4):
        t0 = time.time()
        wating = True
        while wating:
            DI = self.show_di_state()
            if wait == 'open':
                channel = self.DI_Coverisopen 
            elif wait == 'close':
                channel = self.DI_CoverisClosed 
            else:
                pass
            if DI[channel] == 1:
                print(f"In position! cover is {wait}, take {time.time()-t0} sec")
                wating = False
            elif (time.time()-t0) > timeout:
                self.set_do_state(self.DO_CloseCover,0)
                self.set_do_state(self.DO_OpenCover,0)
                print(f"Timeout! in {timeout} sec")
                wating = False
            else:
                time.sleep(interval)

    def show_current_state(self):
        DI = self.show_di_state()
        if DI[self.DI_Coverisopen] == 1:
            # print("Open!")
            return 'Open'
        elif DI[self.DI_CoverisClosed] == 1:
            # print("Closed!")
            return 'Closed'
        else:
            # print("Unkonw!")
            return 'Unkonw'

    def show_di_state(self):
        t0 = time.time()
        r = requests.get(self.di_url,headers=self.header)
        ans = r.json()
        distates = ans['io']['di']
        # print(ans['io']['di'])
        distr = ''
        DI = {}
        for item in distates:
            DI[item['diIndex']] = item['diStatus']
            distr = distr + " " + str(item['diStatus'])
        # print(distr)
        r.close()
        # print(f'time={time.time()-t0}')
        # print(DI)
        return DI
    def show_do_state(self):
        t0 = time.time()
        r = requests.get(self.do_url,headers=self.header)
        ans = r.json()
        distates = ans['io']['do']
        print(ans['io']['do'])
        DO = {}
        
        for item in distates:
            DO[item['doIndex']] = item['doStatus']
        print(DO)
        r.close()
        print(f'time={time.time()-t0}')
        return DO
    def show__single_do_state(self,channel=0):
        t0 = time.time()
        url = f'{self.do_url}/{channel}/doStatus'
        r = requests.get(url,headers=self.header)
        ans = r.json()
        print(ans)
        DOstate = ans['io']['do'][str(channel)]['doStatus']
        # print(DOstate)
        r.close()
        print(f'time={time.time()-t0}')
        
        return DOstate
    def set_do_state(self,channel=0,state=0):
        t0 = time.time()
        url = f'{self.do_url}/{channel}/doStatus'

        # PutData = '{"slot": 0, "io": {"do": {"CHANNEL": {"doStatus": STATE}}}}'
        # PutData = PutData.replace("CHANNEL",str(channel))
        # PutData = PutData.replace("STATE",str(state))
        # {'slot': 0, 'io': {'do': {'0': {'doStatus': 0}}}}
        PutData = {}
        PutData['slot']=0
        PutData['io']={}
        PutData['io']['do']={}
        PutData['io']['do'][str(channel)]={}
        PutData['io']['do'][str(channel)]['doStatus']=state
        PutData['doStatus']=state
        # print(type(PutData),PutData)
        # print(json.dumps(PutData))
        header = self.header.copy()
        # header['Content-Length']=str(len(json.dumps(PutData)))
        # header['Content-Length']=str(len(PutData))
        # print(header)
        r = requests.put(url,headers=header,json=PutData )
        r.close()
        # print(requests.request.headers)

        # ans = r.json()
        # print(r)
        
        # distates = ans['io']['do']
        # print(ans['io']['do'])
        # DO = {}
        # for item in distates:
        #     DO[item['doIndex']] = item['doStatus']
        # print(DO)
        # print(f'time={time.time()-t0}')
        # return DO
    def quit(self,signum,frame):
        stateQ=self.Q['stateQ']
        commandQ=self.Q['commandQ']
        stateQ.put('exit')
        commandQ.put('exit')
        time.sleep(1)
        self.m.shutdown()
        active_children = mp.active_children()
        self.logger.warning(f'active_children={active_children}')
        if len(active_children)>0:
            for item in active_children:
                self.logger.warning(f'Last try to kill {item.pid}')
                os.kill(item.pid,signal.SIGKILL)
        # sys.exit()
        pass


if __name__ == "__main__":
    t0 = time.time()
    header={'Accept': 'vdn.dac.v1','Content-Type':'application/json'}
    ip='10.7.1.205'
    di_url = f'http://{ip}/api/slot/0/io/di'
    do_url = f'http://{ip}/api/slot/0/io/do/1/doStatus'
    io = MOXA()
    # io.run()
    # print(io.Par['Coverstate'])
    IOP = Process(target=io.run,name='Cover server')
    IOP.start()
    # time.sleep(0.5)
    # print(io.Par['Coverstate'])
    askforactionP = Process(target=io.askforAction,args=('open',),name='askforaction')
    askforactionP.start()
    # io.askforAction('close')
    time.sleep(10)
    askforaction2P = Process(target=io.askforAction,args=('close',),name='askforaction')
    askforaction2P.start()
    askforaction2P.join()
    # io.askforAction('close')
    # io.askforAction('open')
    # io.askforAction('close')
    # askforactionP = Process(target=io.askforAction,args=('open',),name='askforaction')
    # askforactionP.start()
    # askforactionP.join()
    # print(io.Coverstate)
    # p2 = Process(target=io.askforAction,args=('close',),name='askforaction')
    # p2.start()
    # p2.join()
    # print(io.Coverstate)
    

    # io.show_current_state()
    # io.CloseCover()
    # io.initcover()
    # io.OpenCover()
    # while True:
    #     io.show_di_state()
    #     time.sleep(0.1)
    # io.show__single_do_state()
    # io.set_do_state(0,1)
    io.quit(True,0)
    
    