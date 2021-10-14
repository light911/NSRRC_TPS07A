
import time,signal,os

from pkg_resources import normalize_path
try:
    from Flux07A.Tools import Filiter,cal_thickness,cal_tr
except :
    from Tools import Filiter,cal_thickness,cal_tr

from epics import caput,caget_many,caget
from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
import time
import math
import Config
import logsetup
import itertools
import numpy as np
class atten():
    def __init__(self,Par=None) :
        t0=time.time()
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        
        #load config
        if Par == None:
            self.m = Manager()
            self.Par = self.m.dict()
            self.Par.update(Config.Par)
        else:
            self.Par = Par
        self.logger = logsetup.getloger2('AttenServer',level = self.Par['Debuglevel'],LOG_FILENAME='./log/AttenServerlog.txt')
        #load setup
        att1name = ['Empty','Al1', 'Al2', 'Al3', 'Al4', 'Al6', 'Al12', 'Al18', 'Al24', 'Al30', 'Al36', 'Al42']
        att1value = [0, 16.052693679414958, 31.98617601806601, 63.75486447916776, 54.71294562529552, 6.505859398108251, 13.106724387135548, 19.98271201114769, 26.090323136268182, 33.0917238361028, 39.76086328642271, 46.71063156488829]

        att2name = ['Empty','Al5', 'Al10', 'Al15', 'Al20', 'Al400um', 'Al000um', 'undef', 'undef', 'undef', 'undef', 'undef']
        att2value = [0, 63.480669734413006, 126.93444940545636, 189.93180093375332, 319.80269755922563, 392.7670154440273, 959.1729029219241, 3687.670936671478, 4601.065159489379, 3589.202407147577, 4601.065159489379, 4601.065159489379]

        att3name = ['Empty','Al200um', 'Al400um', 'Al500um', 'Al600um', 'Al800um', 'Al1000um', 'Al1500um', 'Cu150um', 'Pt15um', 'Au20um', 'Cu100um','Al2000um','Pt7um','Au10um','Cu50um']
        att3value = [0, 196.1458263890592, 392.7707556638277, 479.2556986963805, 559.1700901226709, 783.3908317736084, 959.7043970939069, 1439.1153018607538, 140.30347378411304, 16.322507422634313, 18.815959908455618, 97.14403236133096, 1939.42,7.02836, 6.998221388580689,48.199975534258705]

        att4name = ['Empty','Kapton1', 'Kapton2', 'Kapton3', 'Kapton4', 'undef', 'undef', 'undef', 'undef', 'undef', 'undef', 'undef']
        att4value = [0, 74.77030237764889, 154.43180662519237, 225.9627733954374, 306.984110909883, 0.3398692984101902, -4.536652975921299, -5.490523379312952, 0.2955899293484197, 0.09404629877134212, 4601.065159489379, 4601.065159489379]

        self.Al =Filiter("Al",logger=self.logger)
        self.Pt = Filiter("Pt",logger=self.logger)
        self.Au = Filiter("Au",logger=self.logger)
        self.Cu = Filiter("Cu",logger=self.logger)
        self.Kapton=Filiter("Kapton",logger=self.logger)
        #find all part
        prefix_name = '07a:ATT:'
        # self.selectPV={}
        # for i in range(1,5,1):#1234
        #     self.selectPV[i] = f'{prefix_name}{i:02}select'
        self.attinfo={}
        for i in range(1,5,1):#1234
            self.attinfo[i]={}
            for j  in range(1,19,1):#1~18
                namePV = f'{prefix_name}{i:02}name{j}'
                posPV = f'{prefix_name}{i:02}pos{j}'
                # name = caget(namePV)
                # pos = caget(posPV)
                name,pos = caget_many([namePV,posPV])


                if name == 'undef':
                    pass
                else:
                    namelist = locals()[f'att{i}name']
                    thicknesslist = locals()[f'att{i}value']
                    try:
                        index = namelist.index(name)
                    except ValueError:
                        thickness = -1
                    else:
                        thickness = thicknesslist[index]

                    info={}
                    info['name']=name
                    info['pos']=pos
                    info['thickness']=thickness
                    self.attinfo[i][j]=info
        self.energy = 0
        self.update_effect_al_thickness()
        # print(self.attinfo[3])
        self.att1_motor_PV='07a:ATT:01'
        self.att2_motor_PV='07a:ATT:02'
        self.att3_motor_PV='07a:ATT:03'
        self.att4_motor_PV='07a:ATT:04'

        self.logger.warning(f'Attenuation server init Time: {time.time()-t0}')

    def monitor(self,Que):
        self.AttenQ = Que['Queue']['attenQ']
        self.reciveQ = Que['Queue']['reciveQ']
        self.sendQ = Que['Queue']['sendQ']

        while True:
            
            command = self.AttenQ.get()
            if isinstance(command,str):
                if command == "exit" :
                    self.logger.warning("Atten Q get Exit")
                    break
                else:
                    self.logger.info(f"Unknow command:{command}")
                    pass
            elif isinstance(command,tuple) :
                if command[0] == "stoh_start_motor_move" :
                    # command[1] should be attenuation
                    self.sendQ.put(("startmove",command[1],command[2],"Normal"))
                    new_Attenuation = self.Target(float(command[2]),select='lower')
                    self.sendQ.put(('endmove',command[1] ,str(new_Attenuation),'normal'))
                    pass
                elif command[0] == 'stoh_abort_all':
                    new_Attenuation = self.get_cerrnt_atten()
                    self.sendQ.put(('endmove','attenuation' ,str(new_Attenuation),'normal'))
                    pass
                elif command[0] == 'stoh_register_real_motor':
                    new_Attenuation = self.get_cerrnt_atten()
                    self.sendQ.put(('endmove','attenuation' ,str(new_Attenuation),'normal'))
                elif command[0] == 'stoh_register_pseudo_motor':
                    new_Attenuation = self.get_cerrnt_atten()
                    self.sendQ.put(('endmove','attenuation' ,str(new_Attenuation),'normal'))
                elif command[0] == 'stoh_read_ion_chambers':
                    #stoh_read_ion_chambers time repeat ch1 [ch2 [ch3 [...]]]
                    if command[3] == 'i0':
                        dev='dbpm3'
                    else:
                        dev='dbpm3'
                    count,flux = self.read_flux(dev)
                    self.sendQ.put(('updatevalue',command[3] ,str(count),'ioncchamber',command[1]))
                else:
                    self.logger.warning(f'Unknow command : {command}')
            else:
                self.logger.warning(f'Unknow command : {command}')
                pass
    def read_flux(self,dev="dbpm3"):
        '''
        dev="dbpm3",dbpm5,dbpm6,sample
        '''
        if dev=="dbpm3":
            fluxPV = "07a-ES:DBPM3:Flux"
        elif dev == "dbpm5":
            fluxPV = "07a-ES:DBPM5:Flux"
        elif dev == "dbpm6":
            fluxPV = "07a-ES:DBPM6:Flux"
        elif dev == "sample":
            fluxPV = "07a-ES:Sample:Flux"
        else:
            fluxPV = "07a-ES:DBPM3:Flux"
        flux = caget(fluxPV)
        max = 1e14
        normalize_max = 1000000
        newcount = flux /max * normalize_max
        self.logger.info(f"Flux {dev} = {flux} , after normaliz = {newcount}")
        return newcount,flux

        pass
    def Target(self,ratio,requestedAttenuation=True,select='closest'):
        '''
        ratio = 0~100% if requestedAttenuation = True
        energy = kev
        select = closest, higher, lower

        return
        att1,att2,att3,att4,atten%
        '''
        t0=time.time()
        #ratio = transmission(0~1) if requestedAttenuation = False
        #ratio = requestedAttenuation(0~100%) if requestedAttenuation = True
        energy = self.update_effect_al_thickness()
        if requestedAttenuation:
            transmission = (100-ratio)/100
        else:
            transmission = ratio
        u,u1,u2,u3,u4,d= self.Al.get_mu_d(energy)
        if transmission <= 0:
            thickness = 99999999999
        else:
            thickness=math.log(transmission)/(-u*d*1e-4)
        # print("Target Thickness",thickness," um")
        
        BigGroup = {}#BigGroup[1]={althickness:index}
        keys = {}
        for item in self.attinfo:
            temp = {}
            for key in self.attinfo[item]:
                althickness = self.attinfo[item][key]['althickness']
                index = key
                temp[althickness] = index
            BigGroup[item] = temp
            a = sorted(BigGroup[item].keys())

            # print(a)
            try :
                a.remove(-1)
            except ValueError:
                pass
            keys[item]= a
        # print(keys)
        allist = list(itertools.product(keys[1],keys[2],keys[3],keys[4]))
        sumitem,sum = self.find_closed_value(allist,thickness,select)
        allist = list(itertools.product(keys[1],keys[2],keys[3]))
        sumitem2,sum2 = self.find_closed_value(allist,thickness,select)
        # sumdict={}
        # for item in allist:
        #     sumdict[sum(item)] = item
        # allthinckness = sorted(sumdict.keys())
        # allarray = np.array(allthinckness) 
        # print(allarray)
        # diff = allarray - thickness
        # index_min = np.argmin(abs(diff))
        # fitsum = allthinckness[index_min]

        # print(f'Target Thickness :{thickness},fit = {sumitem},fitsum={sum}')
        # print(f'Target Thickness :{thickness},fit = {sumitem2},fitsum={sum2}')
        # print(f'Time: {time.time()-t0}')
        
        

        att1_index = BigGroup[1][sumitem2[0]]
        att2_index = BigGroup[2][sumitem2[1]]
        att3_index = BigGroup[3][sumitem2[2]]

        att4_index = 18#force empty
        # print(f'{self.attinfo[1][att1_index]},{self.attinfo[2][att2_index]},{self.attinfo[3][att3_index]}')
        Fit_transmission= self.attinfo[1][att1_index]['tr'] * self.attinfo[2][att2_index]['tr'] * self.attinfo[3][att3_index]['tr'] 
        
        att1 = self.attinfo[1][att1_index]['pos']
        att2 = self.attinfo[2][att2_index]['pos']
        att3 = self.attinfo[3][att3_index]['pos']
        att4 = self.attinfo[4][att4_index]['pos']

        caput(self.att1_motor_PV,att1)
        caput(self.att2_motor_PV,att2)
        caput(self.att3_motor_PV,att3)
        caput(self.att4_motor_PV,att4)
        time.sleep(0.2)
        self.wait_all_motor_stop()
        self.logger.debug(f'move att1={att1},att2={att2},att3={att3},att4={att4}')
        self.logger.debug(f'Target_transmission = {transmission},Fit_transmission :{Fit_transmission},{self.attinfo[1][att1_index]["name"]},{self.attinfo[2][att2_index]["name"]},{self.attinfo[3][att3_index]["name"]}')
        self.logger.debug(f'take total time = {time.time()-t0} sec')
        Fit_Attenuation = (1 - Fit_transmission)*100
        return Fit_Attenuation

    def wait_all_motor_stop(self,timeout = 10):
        check = True
        t0 = time.time()
        checkPV = [f'{self.att1_motor_PV}.DMOV',f'{self.att2_motor_PV}.DMOV',f'{self.att3_motor_PV}.DMOV',f'{self.att4_motor_PV}.DMOV']
        while check:
            ans = caget_many(checkPV)
            if sum(ans) == 4 :
                check = False
                self.logger.debug(f'Moving done,take {time.time()-t0} sec')
            elif (time.time()-t0) > timeout:
                check = False
                self.logger.debug(f'Timeout after {timeout} sec')
            else:
                time.sleep(0.1)

            

    def find_closed_value(self,allist,findvalue,select = 'closest'):
        '''
        select = closest, higher, lower
        '''
        
        sumdict={}
        for item in allist:
            sumdict[sum(item)] = item
        allthinckness = sorted(sumdict.keys())
        allarray = np.array(allthinckness) 
        # print(allarray)
        diff = allarray - findvalue
        if select == 'closest':
            index_min = np.argmin(abs(diff))
        elif select == 'higher':
            index_min = np.where(diff >= 0, diff, np.inf).argmin()

            # index_min = diff.index(min([i for i in diff if i > 0]))
           

        elif select == 'lower':
            index_min = np.where(diff <= 0, diff, -np.inf).argmax()
            # index_min = diff.index(max([i for i in diff if i < 0]))
        # self.logger.warning(f"index_min={index_min}")
        fitsum = allthinckness[index_min]
        return sumdict[fitsum],fitsum


    def update_effect_al_thickness(self):
        energy = caget('07a:DCM:Energy')
        if abs(self.energy - energy) <0.01:
            pass
        else:
            self.energy = energy
            self.logger.debug(f'update effect al thickness @ {energy} kev')
            for item in self.attinfo:
                # print(self.attinfo[item])
                for itempos in self.attinfo[item]:
                    name = self.attinfo[item][itempos]['name']
                    thickness = self.attinfo[item][itempos]['thickness']
                    Element = name[0:2]
                    if Element == 'Al':
                        althickness = thickness
                        u,tr = cal_tr(Element,T=thickness,Energy=energy)
                    elif Element == 'Em':#Empty
                        althickness = 0
                        tr = 1
                    else:
                        if thickness == -1:#for data lose or undef
                            althickness=-1
                        else:
                            u,tr = cal_tr(Element,T=thickness,Energy=energy)
                            u,althickness = cal_thickness(tr, 'Al', energy)
                    self.attinfo[item][itempos]['althickness'] = althickness
                    self.attinfo[item][itempos]['tr'] = tr
        return energy

    def get_cerrnt_atten(self):
        
        energy = self.update_effect_al_thickness()
        #get attn pos
        attn1_pos = caget(self.att1_motor_PV)
        attn2_pos = caget(self.att2_motor_PV)
        attn3_pos = caget(self.att3_motor_PV)
        attn4_pos = caget(self.att4_motor_PV)
        althickness1,index1,info1 = self.check_attn_pos(attn1_pos,1)
        althickness2,index2,info2 = self.check_attn_pos(attn2_pos,2)
        althickness3,index3,info3 = self.check_attn_pos(attn3_pos,3)
        althickness4,index4,info4 = self.check_attn_pos(attn4_pos,4)
        name1 = info1['name']
        name2 = info2['name']
        name3 = info3['name']
        name4 = info4['name']
        tr1 = self.Al.cal_tr(althickness1, energy)
        tr2 = self.Al.cal_tr(althickness2, energy)
        tr3 = self.Al.cal_tr(althickness3, energy)
        tr4 = self.Al.cal_tr(althickness4, energy)
        transmission =  tr1*tr2*tr3*tr4
        # print(f'transmission={transmission}, with {tr1},{tr2},{tr3},{tr4}')
        self.logger.debug(f'transmission={transmission}, with {name1}:{tr1}, {name2}:{tr2}, {name3}:{tr3}, {name4}:{tr4}')
        Attenuation = (1-transmission)*100
        self.logger.info(f'Current Attenuation = {Attenuation}')
        return Attenuation

    def check_attn_pos(self,angle,attnum=1):
        info = self.attinfo[attnum]
        diffangle={}#{diff:index,,,....}
        for rot_pos_num in info:#rot_pos_num=1,2....18
            # print(rot_pos_num)
            index = rot_pos_num
            name = info[rot_pos_num]['name']
            setpos = info[rot_pos_num]['pos']
            # print(setpos)
            diff = abs(angle - setpos)
            
            diffangle[diff] = index
        # print(diffangle)
        minangle = min(diffangle.keys())
        
        selectinfo = info[diffangle[minangle]]
        
        selectindex = diffangle[minangle]
        setangle = info[diffangle[minangle]]['pos']
        name = info[diffangle[minangle]]['name']
        thickness = info[diffangle[minangle]]['thickness']
        althickness = info[diffangle[minangle]]['althickness']
        # print(minangle,setangle)

        if minangle > 1:
            self.logger.warning(f'[cal atten{attnum},angle ={angle}] minangle is smaller than 1,{minangle},cal may be wrong') 
        
        return althickness,selectindex,selectinfo
    def TargetFlux(self,flux):
        old_atten = self.get_cerrnt_atten()
        #open all filter
        self.Target(0)
        time.sleep(0.3)
        count,dbpm3 = self.read_flux(dev="dbpm3")
        count,sample = self.read_flux(dev="sample")
        if sample < 1e5:
            self.logger.warning('No beam!')
            self.logger.warning(f'Dbpm3 flux:{dbpm3:.4g} , sample flux = {sample:.4g}')
        elif flux > sample:
            self.logger.warning(f'Request flux:{flux:.4g} is higher than max flux{sample:.4g}')
            self.logger.warning('set atten to 0 %')
        else:
            ratio = flux/sample
            Fit_Attenuation = self.Target(ratio,False)
            time.sleep(0.3)
            count,newsample = self.read_flux(dev="sample")
            self.logger.warning(f'final flux:{newsample:.4g},Request flux:{flux:.4g},Full flux {sample:.4g},atten set to {Fit_Attenuation}')
        return
        pass
    def quit(self,signum,frame):

        self.logger.debug(f"PID : {os.getpid()} DHS closed, Par= {self.Par} TYPE:{type(self.Par)}")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
        self.logger.critical(f'm pid={self.m._process.ident}')
        self.m.shutdown()
        active_children = mp.active_children()
        self.logger.critical(f'active_children={active_children}')
        if len(active_children)>0:
            for item in active_children:
                self.logger.warning(f'Last try to kill {item.pid}')
                os.kill(item.pid,signal.SIGKILL)

if __name__ == "__main__":
    
    # DBPM = Filiter("Diamond")
    # Kapton=Filiter("Kapton")
    # Air = Filiter("Air")
    # Al = Filiter("Al")
    a = atten()
    print(a.TargetFlux(1e9))
    # print(a.get_cerrnt_atten())
    
