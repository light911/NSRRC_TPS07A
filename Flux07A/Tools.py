#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 25 15:10:17 2021

@author: blctl
"""
import xraylib
import math,time
import logging
from epics import caput,caget_many,caget



class Filiter():
        
    def __init__(self,setElement="Diamond",debug=False,logger=None):
        '''
        
        Parameters
        ----------
        setElement : TYPE, optional
            DESCRIPTION. The default is "Diamond". 
        debug : TYPE, optional
            DESCRIPTION. The default is False. Output debug message

        Returns
        -------
        None.

        '''
        if logger == None:
            try :
                import logsetup
                if debug:
                    Debuglevel = 'DEBUG'
                else:
                    Debuglevel = 'INFO'
                self.logger = logsetup.getloger2('FiliterServer',level = Debuglevel)
            except:
                #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                # formatter = logging.Formatter('%(name)s - %(message)s')
                FORMAT = '%(asctime)s - %(name)s - %(message)s'
                if debug:
                    print("Enable Debug mode")
                    logging.basicConfig(level=logging.DEBUG,format = FORMAT)
                else:
                    logging.basicConfig(level=logging.INFO,format = FORMAT)
                
                # logging.Formatter('%(name)s - %(message)s')
                self.logger = logging.getLogger('FiliterLog')
        else:
            self.logger=logger

        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # # add formatter to ch
        # ch.setFormatter(formatter)
        # self.logger.addHandler(ch)
            
        # self.logger.info("HIIIII")
        self.elementN = 13
        self.electronpair = 0
        self._element = setElement
        self.element  = setElement
        
        
       

        
    @property
    def element(self):
        return(self._element)
    
    @element.setter
    def element(self,newElement):
        # print("event!")
         
       # self.logger.info("Hi")
        self._element = newElement
        if newElement == "Al" :
            self.elementN = 13
        elif newElement == "Pt" :
            self.elementN = 78
        elif newElement == "Au" :
            self.elementN = 79       
        elif newElement == "Cu" :
            self.elementN = 29       
        elif newElement == "Ti" :
            self.elementN = 22       
        elif newElement == "Diamond" :
            self.elementN = 6     
            self.electronpair = 13.25
        elif newElement == "C" :
            self.elementN = 6     
            self.electronpair = 13.25
        elif newElement == "Be" :
            self.elementN = 4
        elif newElement == "N" :
            self.elementN = 7
            self.electronpair = 36#36
        elif newElement == "Si" :
            self.elementN = 14 
            self.electronpair = 3.66
        elif newElement == "W" :
            self.elementN = 74
        elif newElement == "Ta" :
            self.elementN = 73
        elif newElement == "Mo" :
            self.elementN = 42 
        elif newElement == "Air":
            # xraylib.GetCompoundDataNISTByName("Air, Dry (near sea level)")
            self.elementN = 0
            self.electronpair = 34.4
        elif newElement == "Kapton":
            
            self.elementN = 0
            
        
        else:
            self.logger.error("%s is unkonw element",newElement)
            self.logger.debug("Element set to = %s",newElement)
        self.logger.debug(f'Set {newElement},elementN = {self.elementN} , electronpair = {self.electronpair}')
   
    def cal_tr(self,T=10,Energy=12.7 ) :
        '''
        Parameters
        ----------
        T : thickness , um
            DESCRIPTION. The default is 10.
        Energy : TYPE, Kev
            DESCRIPTION. The default is 12.7kev.
 
        Returns
        -------
        None.
 
        '''
        # self.logger.debug("Element = %s",self.element)
        # self.logger.info("Hi")
        
        #total atten 
        u,u1,u2,u3,u4,d=self.get_mu_d(Energy)
            
 
       
        Tr=math.exp(-u*d*T*1e-4)
        # Tr2=math.exp(-ue*d*T*1e-4)
        # Tr3=math.exp(-uu*d*T*1e-4)
  
        # self.logger.debug("Density = %f",d)
        # self.logger.debug("Energy = %f",Energy)
        # self.logger.debug("Thickness = %f um",T)
        # self.logger.debug("Total atten cross section = %f",u)
        # self.logger.debug("photoionization cross section = %f",u1)
        # self.logger.debug("Compton scattering cross section = %f",u2)
        # self.logger.debug("Rayleigh scattering cross section = %f",u3)
        # self.logger.debug("Mass energy-abs cross section = %f",u4)
        # self.logger.debug("Transmission = %F",Tr)
        return Tr
        # print(Tr2)
        # print(Tr3)
    def cal_flux(self,Current,T=10,Energy=12.7):
        '''
        Parameters
        ----------
        T : thickness , um
            DESCRIPTION. The default is 10.
        Energy : TYPE, Kev
            DESCRIPTION. The default is 12.7kev.
 
        Returns
        -------
        None.
 
        '''
        # self.logger.debug("Element = %s",self.element)
        #total atten 
        u,u1,u2,u3,u4,d=self.get_mu_d(Energy)

        flux = Current / (Energy*1000/self.electronpair)/(1-math.exp(-1*u*d*T*1e-4))/1.6e-19
        flux2 = Current / (Energy*1000/self.electronpair)/(1-math.exp(-1*(u1+u2)*d*T*1e-4))/1.6e-19
        flux3 = Current / (Energy*1000/self.electronpair)/(1-math.exp(-1*(u1)*d*T*1e-4))/1.6e-19
        Tr=math.exp(-u*d*T*1e-4)
        # self.logger.debug("Density = %f",d)
        # self.logger.debug("Energy = %f",Energy)
        # self.logger.debug("Thickness = %f um",T)
        # self.logger.debug("Total atten cross section = %f",u)
        # self.logger.debug("photoionization cross section = %f",u1)
        # self.logger.debug("Compton scattering cross section = %f",u2)
        # self.logger.debug("Rayleigh scattering cross section = %f",u3)
        # self.logger.debug("Mass energy-abs cross section = %f",u4)
        # self.logger.debug("Transmission = %f",Tr)
        # self.logger.debug("electronpair = %f",self.electronpair)
        # self.logger.debug("Flux(Total atten cross section) = %g",flux)
        # self.logger.debug("Flux(Total less elastic cross section) = %g",flux2)
        # self.logger.debug("Flux(photoionization cross section) = %g",flux3)
        return flux
    def get_mu_d(self,Energy):
        if self.element == "Diamond" :
            u= xraylib.CS_Total_CP("C",Energy)#
            u1= xraylib.CS_Photo_CP("C",Energy)#photoionization
            u2= xraylib.CS_Compt_CP("C",Energy)#Compton scattering
            u3= xraylib.CS_Rayl_CP("C",Energy)#Rayleigh scattering
            u4= xraylib.CS_Energy_CP("C",Energy)#Mass energy-abs
            d = 3.51
        elif self.element == "Air" :
            temp = xraylib.GetCompoundDataNISTByName("Air, Dry (near sea level)")
            u= xraylib.CS_Total_CP("Air, Dry (near sea level)",Energy)
            u1= xraylib.CS_Photo_CP("Air, Dry (near sea level)",Energy)#photoionization
            u2= xraylib.CS_Compt_CP("Air, Dry (near sea level)",Energy)#Compton scattering
            u3= xraylib.CS_Rayl_CP("Air, Dry (near sea level)",Energy)#Rayleigh scattering
            u4= xraylib.CS_Energy_CP("Air, Dry (near sea level)",Energy)#Mass energy-abs
            d = temp['density']
            # Elements = temp['Elements']
            # massFractions = temp['massFractions']
        elif self.element == "Kapton" :
            temp = xraylib.GetCompoundDataNISTByName("Kapton Polyimide Film")
            u= xraylib.CS_Total_CP("Kapton Polyimide Film",Energy)
            u1= xraylib.CS_Photo_CP("Kapton Polyimide Film",Energy)#photoionization
            u2= xraylib.CS_Compt_CP("Kapton Polyimide Film",Energy)#Compton scattering
            u3= xraylib.CS_Rayl_CP("Kapton Polyimide Film",Energy)#Rayleigh scattering
            u4= xraylib.CS_Energy_CP("Kapton Polyimide Film",Energy)#Mass energy-abs
            d = temp['density']
        else :      
            u= xraylib.CS_Total_CP(self.element,Energy)
            u1= xraylib.CS_Photo_CP(self.element,Energy)#photoionization
            u2= xraylib.CS_Compt_CP(self.element,Energy)#Compton scattering
            u3= xraylib.CS_Rayl_CP(self.element,Energy)#Rayleigh scattering
            u4= xraylib.CS_Energy_CP(self.element,Energy)#Mass energy-abs
            d = xraylib.ElementDensity(self.elementN)
        return u,u1,u2,u3,u4,d
    def cal_thickness(self,ratio,Energy,requestedAttenuation=False):
        #ratio = transmission(0~1) if requestedAttenuation = False
        #ratio = requestedAttenuation(0~100%) if requestedAttenuation = True
        if requestedAttenuation:
            transmission = (100-ratio)/100
        else:
            transmission = ratio
        u,u1,u2,u3,u4,d=self.get_mu_d(Energy)
        # Tr=math.exp(-u*d*T*1e-4)
        # print(transmission)
        thickness=math.log(transmission)/(-u*d*1e-4)
        return thickness

def cal_thickness_for_atten(file="cal_thickness_for_atten.txt"):
    
    f = open(file, 'a')
    N = Filiter("N")
    Al =Filiter("Al")
    Pt = Filiter("Pt")
    Au = Filiter("Au")
    Cu = Filiter("Cu")
    DBPM = Filiter("Diamond")
    Kapton=Filiter("Kapton")
    Diamond=Filiter("Diamond")
    attebasename = "07a:ATT:XXnameY"#07a:ATT:03name11
    selectcommandbase = "07a:ATT:XXselect"
    allname = []
    numsets = ("01","02","03","04")
    for numset in numsets:
        # attpv=attebasename.replace("XX",numset)
        templist = []
        for subnum in range(1,13):
            attpv=attebasename.replace("XX",numset)
            attpv=attpv.replace("Y",str(subnum))
            name = caget(attpv)
            templist.append(name)
            # print(f'attpv={attpv},name={name}')
        allname.append(templist)
    # print(allname)

    att1namelist=allname[0]
    att2namelist=allname[1]
    att3namelist=allname[2]
    att4namelist=allname[3]
    
    _command = ""
    Energy = caget ("07a:DCM:Energy.VAL")
    for numset in numsets:
        command = selectcommandbase.replace("XX",numset)
        caput(command,0)
        time.sleep(2)
        #cal base line
        flux,ebeam,ic1flux= caget_many(["07A-DBPM5:signals:sa.Sum","SR-DI-DCCT:BeamCurrent","07a-XBPM2:CurMD:FI2"])
        emptyflux = flux/ebeam
        emptyic1flux = ic1flux/ebeam*-1
        DBPMcurrent = flux/1e5*1e-6
        ic1Current = ic1flux *-1
        emptyDBPM5flux=DBPM.cal_flux(DBPMcurrent,20,Energy)
        emptyic1calflux = N.cal_flux(ic1Current,58000,Energy)

        f.write(f"{command}\tFullname\temptyflux\tattenflux\tebeam\tRatio\tRatio By ic1\tempty ic1 calflux\temptyDBPM5flux\tic1flux\tDBPM5Flux\tEnergy\tu\tthickness_byic1\tthickness\n")
        print(f"{command}\tFullname\temptyflux\tattenflux\tebeam\tRatio\tRatio By ic1\tempty ic1 calflux\temptyDBPM5flux\tic1flux\tDBPM5Flux\tEnergy\tu\tthickness_byic1\tthickness")
        templtlist=[]
        tempnamelist=[]
        for subnum in range(1,12):
            caput(command,subnum)
            time.sleep(2)
            flux,ebeam,ic1= caget_many(["07A-DBPM5:signals:sa.Sum","SR-DI-DCCT:BeamCurrent","07a-XBPM2:CurMD:FI2"])
            ic1Current = ic1 * -1
            attenflux = flux/ebeam
            ic1flux = ic1Current/ebeam
            tr= attenflux/emptyflux
            tr_byic1 = ic1flux/emptyic1flux
            DBPMcurrent = flux/1e5*1e-6
            DBPM5flux=DBPM.cal_flux(DBPMcurrent,20,Energy)
            ic1calflux = N.cal_flux(ic1Current,58000,Energy)
            print(f"tr={tr}")
            print(f"tr_byic1={tr_byic1}")
            if tr<=0 :
                tr=0.0000001
            if tr_byic1<=0 :
                tr_byic1=0.0000001
            Element = caget(command,as_string=True)[0:2]
            Fullname = caget(command,as_string=True)
            print(f"Finaltr={tr}")
            print(f"Final tr_byic1={tr_byic1}")
            print(f"Element={Element}")
            
            u,thickness = cal_thickness(tr,Element,Energy)
            u,thickness_byic1 = cal_thickness(tr_byic1,Element,Energy)

            f.write(f"{subnum}\t{Fullname}\t{emptyflux}\t{attenflux}\t{ebeam:.2f}\t{tr}\t{tr_byic1}\t{emptyic1calflux:.3g}\t{emptyDBPM5flux:.3g}\t{ic1calflux:.3g}\t{DBPM5flux:.3g}\t{Energy:.4f}\t{u}\t{thickness_byic1:.2f}\t{thickness:.2f}\n")
            print(f"{subnum}\t{Fullname}\t{emptyflux}\t{attenflux}\t{ebeam:.2f}\t{tr}\t{tr_byic1}\t{emptyic1calflux:.3g}\t{emptyDBPM5flux:.3g}\t{ic1calflux:.3g}\t{DBPM5flux:.3g}\t{Energy:.4f}\t{u}\t{thickness_byic1:.2f}\t{thickness:.2f}")
            templtlist.append(thickness)
            tempnamelist.append(Fullname)
            #retuen to empty
            caput(command,0)
        f.write(f"{command}:\n{tempnamelist}\n{templtlist}\n")
    f.close()

def cal_thickness(tr,Element,Energy):
    Al =Filiter("Al")
    Pt = Filiter("Pt")
    Au = Filiter("Au")
    Cu = Filiter("Cu")
    Kapton=Filiter("Kapton")
    if Element == "Al":
        u,u1,u2,u3,u4,d= Al.get_mu_d(Energy)
        thickness = Al.cal_thickness(tr,Energy)
    elif Element == "Pt":
        u,u1,u2,u3,u4,d= Pt.get_mu_d(Energy)
        thickness = Pt.cal_thickness(tr,Energy)
    elif Element == "Au":
        u,u1,u2,u3,u4,d= Au.get_mu_d(Energy)
        thickness = Au.cal_thickness(tr,Energy)
    elif Element == "Ka":
        u,u1,u2,u3,u4,d= Kapton.get_mu_d(Energy)
        thickness = Kapton.cal_thickness(tr,Energy)
    elif Element == "Cu":
        u,u1,u2,u3,u4,d= Cu.get_mu_d(Energy)
        thickness = Cu.cal_thickness(tr,Energy)
    else:
        print(f'Unknow element {Element} using Al')
        u,u1,u2,u3,u4,d= Al.get_mu_d(Energy)
        thickness = Al.cal_thickness(tr,Energy)
    return u,thickness

def cal_tr(Element,T=10,Energy=12.7 ) :
    Al =Filiter("Al")
    Pt = Filiter("Pt")
    Au = Filiter("Au")
    Cu = Filiter("Cu")
    Kapton=Filiter("Kapton")
    Diamond=Filiter("Diamond")
    if Element == "Al":
        u,u1,u2,u3,u4,d= Al.get_mu_d(Energy)
    elif Element == "Pt":
        u,u1,u2,u3,u4,d= Pt.get_mu_d(Energy)
    elif Element == "Au":
        u,u1,u2,u3,u4,d= Au.get_mu_d(Energy)
    elif Element == "Ka":
        u,u1,u2,u3,u4,d= Kapton.get_mu_d(Energy)
    elif Element == "Cu":
        u,u1,u2,u3,u4,d= Cu.get_mu_d(Energy)
    else:
        print(f'Unknow element {Element} using Al')
        u,u1,u2,u3,u4,d= Al.get_mu_d(Energy)
       
    Tr=math.exp(-u*d*T*1e-4)
    return u,Tr


def TPS07A_atten(Energy=12.7):
    # 07a:ATT:01select:
    ['Al1', 'Al2', 'Al3', 'Al4', 'Al6', 'Al12', 'Al18', 'Al24', 'Al30', 'Al36', 'Al42']
    att1=[16.052693679414958, 31.98617601806601, 63.75486447916776, 54.71294562529552, 6.505859398108251, 13.106724387135548, 19.98271201114769, 26.090323136268182, 33.0917238361028, 39.76086328642271, 46.71063156488829]
    # 07a:ATT:02select:
    ['Al5', 'Al10', 'Al15', 'Al20', 'Al400um', 'Al000um', 'Pos. 5', 'Pos. 4', 'Pos. 3', 'Pos. 2', 'Pos. 1']
    [63.480669734413006, 126.93444940545636, 189.93180093375332, 319.80269755922563, 392.7670154440273, 959.1729029219241, 3687.670936671478, 4601.065159489379, 3589.202407147577, 4601.065159489379, 4601.065159489379]
    # 07a:ATT:03select:
    ['Al200um', 'Al400um', 'Al500um', 'Al600um', 'Al800um', 'Al1000um', 'Al1500um', 'Cu150um', 'Pt15um', 'Au20um', 'Cu100um','Al2000um']
    [196.1458263890592, 392.7707556638277, 479.2556986963805, 559.1700901226709, 783.3908317736084, 959.7043970939069, 1439.1153018607538, 140.30347378411304, 16.322507422634313, 18.815959908455618, 97.14403236133096,1939.42]
    # 07a:ATT:04select:
    ['Kapton1', 'Kapton2', 'Kapton3', 'Kapton4', 'Pos5', 'Pos6', 'Pos7', 'Pos8', 'Pos9', 'Pos10', 'Pos11']
    [74.77030237764889, 154.43180662519237, 225.9627733954374, 306.984110909883, 0.3398692984101902, -4.536652975921299, -5.490523379312952, 0.2955899293484197, 0.09404629877134212, 4601.065159489379, 4601.065159489379]
    Data={}
    temp={}
    for i,item in enumerate(att1):
        temp[item]=i+1
    print(sorted(temp.keys()))
    print(temp)
    



if __name__ == "__main__":
    # signal.signal(signal.SIGINT, quit)
    # signal.signal(signal.SIGTERM, quit)
    Al =Filiter("Al",True)
    Pt = Filiter("Pt")
    Au = Filiter("Au")
    Cu = Filiter("Cu")
    Kapton=Filiter("Kapton")
    Diamond=Filiter("Diamond")
    Be = Filiter("Be")
    N = Filiter("N")
    DBPM1=Filiter("Diamond")
    DBPM2=Filiter("Diamond")
    DBPM3=Filiter("Diamond")
    DBPM5=Filiter("Diamond")
    DBPM6=Filiter("Diamond")
    Air = Filiter("Air")
    # Al.element="Al"
    # print(Al.elementN)
    # print(Al.cal_tr(10,12.7))
    # print(Diamond.cal_tr(200,12.7))
    # print(Be.cal_tr(250,12.7))
    # print(Diamond.cal_tr(400,12.4)*Be.cal_tr(250,12.4))
    # print(Diamond.cal_flux(1e-6,20,12.7))
    # print(N.electronpair)
    # print(N.cal_flux(1e-6,57.15*1e3,12.7))
    # print(Diamond.cal_flux(1e-6,20,12.7))
    print(Air.cal_tr(150000,12.7))
    Kapton.cal_tr(50,12.7)
    energy=12.7
    AirTr = Air.cal_tr(0,energy)
    AlTr = Al.cal_tr(40,energy)
    KaptonTr = Kapton.cal_tr(100, energy)
    totalTr=AirTr*AlTr*KaptonTr
    print(totalTr,AirTr,AlTr,KaptonTr)
    # Air.cal_tr(170*1e3,energy)
    # print(Al.cal_thickness(0.25230,12.7))
    # print(Al.cal_thickness(0.22759,12.4))
    # print(Al.cal_thickness(0.4304,15))
    # print(Al.cal_thickness(0.13812,12.7))
    # print(Pt.cal_thickness(0.00435,15))
    # print(Pt.cal_thickness(0.000143,14))
    # print(Au.cal_thickness(0.00277,15))
    # print(Au.cal_thickness(0.00341,12.7))
    # # cal_thickness_for_atten('cal_thickness_for_atten_20210928.txt')
    # print(Al.cal_thickness(1.64529e-2,15))
    # # TPS07A_atten()
    # print(Al.cal_thickness(6.0827e-7,12.7))
    # print(Cu.cal_thickness(6.0827e-7,12.7))
    # print(Cu.cal_tr(97.144,12.7))
    # print(Al.cal_thickness(0.01549,12.7))
    # energy =8
    # dbpm6flux=8.77e10
    # samplebase = Al.cal_tr(20,energy)*Kapton.cal_tr(50, energy)*Air.cal_tr(600000,energy)
    # # Flbase = Cu.cal_tr(97.144,energy)*Al.cal_tr(392,energy)
    # # Flbase = Cu.cal_tr(97.144,energy)*Al.cal_tr(959,energy)*Al.cal_tr(63.75,energy)
    # Flbase = Al.cal_tr(559,energy)*Al.cal_tr(126.9,energy)
    # distance = Air.cal_tr(150000,energy)
    # print(f"cal flux = {dbpm6flux*Flbase*samplebase*distance:g}")
    # # print(Air.cal_tr(600000,12.7))
    # print(Al.cal_thickness(4.868e-5,8))
    # print(Al.cal_tr(732.6,energy)*dbpm6flux)
    # print(Al.cal_thickness(0.01549,12.7))
    
    # print(cal_thickness(0.01549,'Al',12.7))
    print(Cu.cal_thickness(6.512614607e-3,12.7))
    # print(Au.cal_thickness(0.1181811,12.7))