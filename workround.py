from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
import logsetup,time,subprocess
import threading
from epics import caput,CAProcess,caget
from epics import PV as EpicsPV
import json,re
import Config,numpy

# DBR_STRING 	0 	DBR_STS_FLOAT 	9 	DBR_TIME_LONG 	19 	DBR_CTRL_SHORT 	29
# DBR_INT 	1 	DBR_STS_ENUM 	10 	DBR_TIME_DOUBLE 	20 	DBR_CTRL_INT 	29
# DBR_SHORT 	1 	DBR_STS_CHAR 	11 	DBR_GR_STRING 	21 	DBR_CTRL_FLOAT 	30
# DBR_FLOAT 	2 	DBR_STS_LONG 	12 	DBR_GR_SHORT 	22 	DBR_CTRL_ENUM 	31
# DBR_ENUM 	3 	DBR_STS_DOUBLE 	13 	DBR_GR_INT 	22 	DBR_CTRL_CHAR 	32
# DBR_CHAR 	4 	DBR_TIME_STRING 	14 	DBR_GR_FLOAT 	23 	DBR_CTRL_LONG 	33
# DBR_LONG 	5 	DBR_TIME_INT 	15 	DBR_GR_ENUM 	24 	DBR_CTRL_DOUBLE 	34
# DBR_DOUBLE 	6 	DBR_TIME_SHORT 	15 	DBR_GR_CHAR 	25 	DBR_STSACK_STRING 	37
# DBR_STS_STRING 	7 	DBR_TIME_FLOAT 	16 	DBR_GR_LONG 	26 	DBR_CLASS_NAME 	38
# DBR_STS_SHORT 	8 	DBR_TIME_ENUM 	17 	DBR_GR_DOUBLE 	27 		
# DBR_STS_INT 	8 	DBR_TIME_CHAR 	18 	DBR_CTRL_STRING 	28 	

# A Type Code 	Primitive C Data Type 	Data Size
# DBR_CHAR 	    dbr_char_t 	            8 bit character
# DBR_SHORT 	dbr_short_t         	16 bit integer
# DBR_ENUM 	    dbr_enum_t 	             16 bit unsigned integer
# DBR_LONG 	    dbr_long_t 	          32 bit signed integer
# DBR_FLOAT 	dbr_float_t 	        32 bit IEEE floating point
# DBR_DOUBLE 	dbr_double_t    	64 bit IEEE floating point
# DBR_STRING 	dbr_string_t    	40 character string

class myepics():
    '''
    caget/caput with the same call convention as the old CLI-subprocess
    version, but backed by pyepics with a per-process PV cache: the channel
    is created once and reused, no fork + CA reconnect for every access.
    '''
    def __init__(self,logger=None) -> None:

        self.Par = Config.Par
        if not logger:
            self.logger = logsetup.getloger2('myepics',LOG_FILENAME='/home/blctl/Desktop/log/workround.txt',level = self.Par['Debuglevel'],bypassline=False)
        else:
            self.logger = logger
        #lazy PV cache: nothing connects before first use, so an instance
        #created before fork() is still safe in the child process
        self._pvcache = {}
        self._pvlock = threading.Lock()

    def _pv(self,name):
        name = str(name)
        with self._pvlock:
            pv = self._pvcache.get(name)
            if pv is None:
                pv = EpicsPV(name)
                self._pvcache[name] = pv
        if not pv.connected:
            pv.wait_for_connection(timeout=2)
        return pv
    def cainfo(self,PV):
        t0=time.time()
        command = ['cainfo',str(PV)]
        ans = subprocess.run(command,capture_output=True)
        result = ans.stdout.decode('utf-8')
        error = ans.stderr.decode('utf-8')       
        # self.logger.debug(f'{ans},result={result},error={error}')
        info = {}
        connected = re.search('State:(.[ ]*)(.*)',result).group(2)
        Host = re.search('Host:(.[ ]*)(.*)',result).group(2)
        Access = re.search('Access:(.[ ]*)(.*)',result).group(2)
        PVtype = re.search('Request type:(.[ ]*)(.*)',result).group(2)
        Host = re.search('Host:(.[ ]*)(.*)',result).group(2)
        Num = int(re.search('Element count:(.[ ]*)(.*)',result).group(2))

        if connected == 'connected':
            connect = True
        info['connect'] = connect
        info['Host'] = Host
        info['Access'] = Access
        info['PVtype'] = PVtype
        info['Num'] = Num
        info['Time'] = time.time() -t0
        
        return info
       

    def caput(self,PV,value,format=str,wait=False,timeout=1,debug=True):
        t0 = time.time()
        if type(PV) is list:
            self.logger.critical(f"ca.caput unsupport muti put!")
            return None
        try:
            if isinstance(value,list):
                if format == int or format == float:
                    value = [format(item) for item in value]
            elif format == int or format == float:
                value = format(value)
            elif isinstance(value,str):
                #the caput CLI converted numeric strings itself, keep that
                #('__EMPTY__' and other real strings stay strings)
                try:
                    value = float(value)
                except ValueError:
                    pass
            pv = self._pv(PV)
            state = pv.put(value, wait=wait, timeout=timeout)
        except Exception as e:
            self.logger.warning(f"Caput {PV} value {value} Fail={e}, take time {time.time()-t0}")
            return None
        if state == 1:
            if debug:
                self.logger.info(f'caput PV={PV},value={value} OK,wait={wait} take time {time.time()-t0}')
            return '1'
        self.logger.warning(f"Caput {PV} value {value} Fail,state={state}, take time {time.time()-t0}")
        return None

    def caget(self,PV,format='Auto',array=False,debug=False):
        t0 = time.time()
        try:
            if type(PV) is list:
                data = [self._caget_one(item,format,array) for item in PV]
            else:
                data = self._caget_one(PV,format,array)
        except Exception as e:
            self.logger.warning(f"caget {PV} fail={e}, take time {time.time()-t0}")
            return None
        if debug:
            self.logger.debug(f'caget {PV} = {data}, take time {time.time()-t0}')
        return data

    def _caget_one(self,name,format,array=False):
        pv = self._pv(name)
        if format == str and not array:
            value = pv.get(as_string=True, timeout=2)
        else:
            value = pv.get(timeout=2)
        if value is None:
            raise RuntimeError(f'PV {name} no response')
        if array:
            value = numpy.atleast_1d(value)
            if format == int:
                return value.astype(int)
            if format == float:
                return value.astype(float)
            if format == str:
                return [str(item) for item in value]
            return value
        if format == int:
            return int(value)
        if format == float:
            return float(value)
        if format == str:
            return str(value)
        #'Auto': native pyepics value (waveforms come back as numpy arrays)
        return value
class workroundmd3moving():
    def __init__(self,Q = None,logger=None) -> None:
        self.Par = Config.Par
        if not logger:
            self.logger = logsetup.getloger2('fixmd3moving',LOG_FILENAME='/home/blctl/Desktop/log/fixmd3moving.txt',level = self.Par['Debuglevel'],bypassline=False)
        else:
            self.logger = logger
        pass
        self.mon = ['07a:md3:Omega','07a:md3:CentringX','07a:md3:CentringY','07a:md3:AlignmentY']
        # self.mon = ['07a:md3:Omega','07a:md3:CentringX','07a:md3:CentringY']
        self.difth = [1e-2,1e-4,1e-4,1e-4]
        self.stateanme = []
        self.TruePosname = []
        for item in self.mon:
                self.stateanme.append(f'{item}State')
                self.TruePosname.append(f'{item}Position')
        self.ca = myepics(self.logger)
        if not Q:
            self.Q = Q['Queue']['workroundQ']
        else:
            self.Q = Queue()
        self.logger.info('workround DHS start')
        pass
        self.logger.warning(f'init done for workroundmd3moving')
    def run(self,checktime = 0.1):
        oldvalue = self.ca.caget(self.TruePosname,float)
        oldstate = self.ca.caget(self.stateanme,str,debug = False)
        # slitstop = self.ca.caget('07a:Slits3:XOpening.DMOV',int,False,False)#1 for stop
        slittimer = time.time()
        time.sleep(checktime)
        counter = 0
        counterlist=[]
        for item in  self.mon:
            counterlist.append(0)
        Exception_counter = 0
        while True:
            # todo exit code
            #workround md3 motor
            targetvalue = self.ca.caget(self.mon,float,debug = False)           
            currentvalue = self.ca.caget(self.TruePosname,float,debug = False)            
            state = self.ca.caget(self.stateanme,str,debug = False)
            
            # print(targetvalue)
            # print(value)
            # print(state)
            diff = []
            
            try:
                for x,y in zip(targetvalue,currentvalue):
                    diff.append(x-y)
                # print(diff)

                for i,item in enumerate(zip(state,oldstate)):
                    if item[0] == 'MOVING' and item[1] =='MOVING':
                        #compare with last time it is still moving
                        counterlist[i] = counterlist[i] + 1

                        # if MOVING state too long,0.1sec * 50 = 5sec
                        if counterlist[i] >= 50:
                            # if MOVING state too long,0.1sec * 50 = 5sec
                            pass
                            diffwithold = abs(oldvalue[i]-currentvalue[i])
                            if diffwithold < self.difth[i]:
                                self.logger.debug(f"MD3 {self.mon[i]} state is {item}, but diffenert with old vlaue is {diffwithold},maybe not moving?check Tartget value")
                                diffwithtarget = abs(targetvalue[i]-currentvalue[i])
                                
                                if diffwithtarget > self.difth[i]:
                                    if caget('07a:md3:Status') == 'Scanning':
                                        pass
                                        pass
                                        counterlist[i] = 0
                                    elif caget('07a:md3:Status') == 'Setting Transfer phase':
                                        pass
                                        counterlist[i] = 0
                                    else:
                                        # counter += 1
                                        self.logger.warning(f'MD3 {self.mon[i]}:{targetvalue[i]=},{currentvalue[i]=},{diffwithtarget=}>{self.difth[i]}, {diffwithold=},state={item}goto target')
                                        self.logger.error(f'Try to fix MD3 {self.mon[i]} problem')
                                        self.ca.caput(self.TruePosname[i],targetvalue[i])
                                        counterlist[i] = 0
                                

                                else:
                                    self.logger.debug(f'{targetvalue[i]=},{currentvalue[i]=},{diffwithtarget=}<{self.difth[i]} not goto target')
                    else:
                        pass
                        counterlist[i] = 0
                        #Motor chagne state, reset counter
                oldvalue = currentvalue
                oldstate = state
                Exception_counter = 0
            except Exception as e:
                Exception_counter += 1
                if Exception_counter ==5:
                    self.logger.critical(f'MD3 workaround program has error,and happen 5 time:{e},maybe MD3 server is down')
                    pass
                else:
                    self.logger.warning(f'MD3 workaround program has error:{e}')
                #when md3 has problem
                #'NoneType' object is not iterable
            
            # #work round 07a:Slits3:XOpening moving problem
            # if self.ca.caget('07a:Slits3:XOpening.DMOV',int,False,False) == 1:
            #     #stop restart timer 
            #     slittimer = time.time()
            #     pass
            # else:
            #     #moving check moving time
            #     time_to_last_stop = time.time() - slittimer
            #     if time_to_last_stop > 10:#moving larger 10 sec
            #         self.logger.info(f'07a:Slits3:XOpening {time_to_last_stop=} moiving time larger 10 sec,we need more check..')
            #         #check Diffenert in VAL and RBV
            #         if abs(self.ca.caget('07a:Slits3:XOpening.VAL',float,False,False) - self.ca.caget('07a:Slits3:XOpening.RBV',float,False,False)) < 0.001:                       
            #             #in position check moving again
            #             self.logger.error('slit3 in postion but still moving, We will try to STOP 07a:Slits3:XPlus and 07a:Slits3:XMinus')
            #             self.ca.caput('07a:Slits3:XPlus.STOP',1)
            #             self.ca.caput('07a:Slits3:XMinus.STOP',1)
                
            #         else:
            #             self.logger.info(f'slits not in postion,we will not do any thing')
            
            
            # here for if Tranfer mode too long
            if caget('07a:md3:Status') == 'Setting Transfer phase':
                if counter == 0:
                    TransfermodeTimer = time.time()
                    # self.logger.warning(f'Try to fix MD3 {self.mon[i]} problem,but now in Setting Transfer phase we do not move at frist try')
                    counter += 1
                else:
                    
                    Transfermoderuntime = time.time() - TransfermodeTimer
                    #If Transfermode take longer than 25 sec
                    if Transfermoderuntime > 25:
                        self.logger.error(f'In Setting Transfer phase too long(25sec), we try abort it,and set it again')
                        #reset counter
                        counter = 0
                        self.ca.caput('07a:md3:abort','__EMPTY__')
                        time.sleep(1)
                        self.ca.caput('07a:md3:CurrentPhase',3)
            else:
                #not in Tranfer mode
                counter = 0
            
            time.sleep(checktime)
            
            
if __name__ == "__main__":
    # ca = myepics()
    # # ca.cainfo('07a:md3:Omega')
    # # ans = ca.caget('07a:md3:Omega',float)
    # # ans = ca.caget(['07a:md3:Omega','07a:md3:CentringTableVertical'],float)
    # # ans = ca.caget('07a-ES:Table:MD3Y',float,True)
    # # ans = ca.caget('07a:md3:LastTaskInfo')
    # # ans = ca.caget('07a:md3:LastTaskInfo',str,True)
    # # ans = ca.caget('fsdfsdf')
    # # ans = ca.caput('07a:md3:CapillaryVertical',0)
    # ans = ca.caget('07a-ES:Table:DBPM6X')
    # # ans = ca.caput('07a-ES:Table:DBPM6Y',[0,0,0,0])
    # print(ans,type(ans))

    test= workroundmd3moving()
    test.run()

    pass