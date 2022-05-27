from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
import logsetup,time,subprocess
from epics import caput,CAProcess,caget
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
    def __init__(self,logger=None) -> None:

        self.Par = Config.Par
        if not logger:
            self.logger = logsetup.getloger2('myepics',LOG_FILENAME='./log/workround.txt',level = self.Par['Debuglevel'])
        else:
            self.logger = logger
        pass
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
        # self.logger.warning(f'caput PV={PV},value={value}')
        command = ['caput','-w',f'{timeout}']
        if wait:
            command.append('-c')
        if type(PV) is list and type(value) is not list:
            # self.logger.critical(f"if PV is a list then value must a list!")
            self.logger.critical(f"ca.caput unsupport muti put!")
            return None
        elif type(PV) is not list and type(value) is list:
            #single PV, array value
            command.append('-a')
            
            command.append(str(PV))
            command.append(f'{len(value)}')
            
            for item in value:
                command.append(str(format(item)))
        elif type(PV) is not list and type(value) is not list:
            #single PV single value
            command.append(str(PV))
            command.append(str(format(value)))
        elif type(PV) is list and type(value) is list:
            #muti PV for muti value
            # ziplist = zip(PV,value)
            self.logger.critical(f"ca.caput unsupport muti put unsupport!")
            return None
        else:
            self.logger.critical(f"something wrong with {PV=},{value=}")
            return None

        ans = subprocess.run(command,capture_output=True)
        if debug:     
            self.logger.debug(f'caput result={ans}')
        result = ans.stdout.decode('utf-8')
        try:
            error = ans.stderr.decode('utf-8')
        except:
            error = ans.stderr
        
        if error == '':
            self.logger.warning(f'caput PV={PV},value={value} OK,wait={wait} take time {time.time()-t0}')
            return result
        else:
            self.logger.critical(f"Caput {PV} value {value} Fail={error}, take time {time.time()-t0}")
            # return False
            return None

    def caget(self,PV,format='Auto',array=False,debug=True):
        t0 = time.time()
        command = ['caget','-stF_']

        if type(PV) is list:
            for item in PV:
                command.append(str(item))
        else:
            command.append(str(PV))

        # command = ['caget','-stF_',str(PV)]
        ans = subprocess.run(command,capture_output=True)
        result = ans.stdout.decode('utf-8')
        try:
            error = ans.stderr.decode('utf-8')
        except:
            error = ans.stderr
        if debug:
            self.logger.debug(f'{ans},result={result},error={error}')
        
        if type(PV) is list:
            resultarray = result.split()
        
        if error == '':
            # auto select format
            if format == 'Auto':
                if type(PV) is list:
                    info = self.cainfo(str(PV[0]))
                else:    
                    info = self.cainfo(str(PV))
                # print(info['PVtype'])
                if info['Num'] > 1:
                    array = True
                if info['PVtype'] == 'DBR_CHAR' or info['PVtype'] == 'DBR_STRING':
                    format = str
                elif info['PVtype'] == 'DBR_INT' or info['PVtype'] == 'DBR_SHORT' or info['PVtype'] == 'DBR_ENUM' or info['PVtype'] == 'DBR_LONG':
                    format = int
                else:
                    format = float
            
            if type(PV) is list:
                resultarray = result.split()
                
                data = []
                for item in resultarray:
                    tempdata = self.returndata(array,item,format)
                    data.append(tempdata)
            else:
                data = self.returndata(array,result,format)


            if debug:
                self.logger.debug(f'caget {PV} ok, take time {time.time()-t0}')
            return data
            
        else:
            self.logger.critical(f"caget {PV} fail, take time {time.time()-t0}")
            # return None
            return None

    def returndata(self,array,result,format):
        if array:
            result_split = result.split("_")
            if format == str:
                data=[]
                for i,item in enumerate(result_split):
                    if i == 0:
                        pass
                    elif item == '':
                        pass
                    elif item == '\n':
                        pass
                    else:
                        data.append(item.rstrip())
            elif format == int:
                data=[]
                for i,item in enumerate(result_split):
                    if i == 0:
                        pass
                    elif item == '':
                        pass
                    elif item == '\n':
                        pass
                    else:
                        data.append(int(item))
                data = numpy.array(data)
            elif format == float:
                data=[]
                for i,item in enumerate(result_split):
                    if i == 0:
                        pass
                    elif item == '':
                        pass
                    elif item == '\n':
                        pass
                    else:
                        try:
                            data.append(float(item))
                        except:
                            
                            pass
                data = numpy.array(data)
            else:
                data = None
        else:
            data = format(result)
        return data
class workroundmd3moving():
    def __init__(self,Q = None,logger=None) -> None:
        self.Par = Config.Par
        if not logger:
            self.logger = logsetup.getloger2('fixmd3movig',LOG_FILENAME='./log/fixmd3movig.txt',level = self.Par['Debuglevel'])
        else:
            self.logger = logger
        pass
        self.mon = ['07a:md3:Omega','07a:md3:CentringX','07a:md3:CentringY','07a:md3:AlignmentY']
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
        pass
        self.logger.warning(f'init done for workroundmd3moving')
    def run(self,checktime = 3):
        oldvalue = self.ca.caget(self.TruePosname,float)
        oldstate = self.ca.caget(self.stateanme,str,debug = False)
        slitstop = self.ca.caget('07a:Slits3:XOpening.DMOV',int,False,False)#1 for stop
        slittimer = time.time()
        time.sleep(checktime)
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
            for x,y in zip(targetvalue,currentvalue):
                diff.append(x-y)
            # print(diff)

            for i,item in enumerate(zip(state,oldstate)):
                if item[0] == 'MOVING' and item[1] =='MOVING':
                    #compare with last time
                    diffwithold = abs(oldvalue[i]-currentvalue[i])
                    if diffwithold < self.difth[i]:
                        self.logger.debug(f"MD3 {self.mon[i]} state is {item}, but diffenert with old vlaue is {diffwithold},maybe not moving?check Tartget value")
                        diffwithtarget = abs(targetvalue[i]-currentvalue[i])
                        
                        if diffwithtarget > self.difth[i]:
                            self.logger.warning(f'MD3 {self.mon[i]}:{targetvalue[i]=},{currentvalue[i]=},{diffwithtarget=}>{self.difth[i]}, {diffwithold=},state={item}goto target')
                            self.ca.caput(self.TruePosname[i],targetvalue[i])
                        else:
                            self.logger.debug(f'{targetvalue[i]=},{currentvalue[i]=},{diffwithtarget=}<{self.difth[i]} not goto target')
            oldvalue = currentvalue
            oldstate = state
            #work round 07a:Slits3:XOpening moving problem
            if self.ca.caget('07a:Slits3:XOpening.DMOV',int,False,False) == 1:
                #stop restart timer 
                slittimer = time.time()
                pass
            else:
                #moving check moving time
                time_to_last_stop = time.time() - slittimer
                if time_to_last_stop > 10:#moving larger 10 sec
                    self.logger.info(f'07a:Slits3:XOpening {time_to_last_stop=} moiving time larger 10 sec,we need more check..')
                    #check Diffenert in VAL and RBV
                    if abs(self.ca.caget('07a:Slits3:XOpening.VAL',float,False,False) - self.ca.caget('07a:Slits3:XOpening.RBV',float,False,False)) < 0.001:                       
                        #in position check moving again
                        self.logger.warning('slit in postion but still moving, We will try to STOP 07a:Slits3:XPlus and 07a:Slits3:XMinus')
                        self.ca.caput('07a:Slits3:XPlus.STOP',1)
                        self.ca.caput('07a:Slits3:XMinus.STOP',1)
                    else:
                        self.logger.info(f'slits not in postion,we will not do any thing')
            
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