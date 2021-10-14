#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 25 15:10:17 2021

@author: blctl
"""
import xraylib
import math
import logging



class Filiter():
        
    def __init__(self,setElement="Diamond",debug=False):
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
        else:
            self.logger.error("%s is unkonw element",newElement)
            self.logger.debug("Element set to = %s",newElement)
   
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
        self.logger.debug("Element = %s",self.element)
        # self.logger.info("Hi")
        
        #total atten 
        if self.element == "Diamond" :
            u= xraylib.CS_Total_CP("C",Energy)
            d = 3.51
        else :      
            u= xraylib.CS_Total_CP(self.element,Energy)
            d = xraylib.ElementDensity(self.elementN)
 
       
        Tr=math.exp(-u*d*T*1e-4)
        # Tr2=math.exp(-ue*d*T*1e-4)
        # Tr3=math.exp(-uu*d*T*1e-4)
  
        self.logger.debug("Density = %f",d)
        self.logger.debug("Energy = %f",Energy)
        self.logger.debug("Thickness = %f um",T)
        self.logger.debug("Corss = %f",u)
        self.logger.debug("Transmission = %F",Tr)
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
        self.logger.debug("Element = %s",self.element)
        #total atten 
        if self.element == "Diamond" :
            u= xraylib.CS_Total_CP("C",Energy)#
            u1= xraylib.CS_Photo_CP("C",Energy)#photoionization
            u2= xraylib.CS_Compt_CP("C",Energy)#Compton scattering
            u3= xraylib.CS_Rayl_CP("C",Energy)#Rayleigh scattering
            d = 3.51
        else :      
            u= xraylib.CS_Total_CP(self.element,Energy)
            u1= xraylib.CS_Photo_CP(self.element,Energy)#photoionization
            u2= xraylib.CS_Compt_CP(self.element,Energy)#Compton scattering
            u3= xraylib.CS_Rayl_CP(self.element,Energy)#Rayleigh scattering

            
            d = xraylib.ElementDensity(self.elementN)
        flux = Current / (Energy*1000/self.electronpair)/(1-math.exp(-1*u*d*T*1e-4))/1.6e-19
        flux2 = Current / (Energy*1000/self.electronpair)/(1-math.exp(-1*(u1+u2)*d*T*1e-4))/1.6e-19
        flux3 = Current / (Energy*1000/self.electronpair)/(1-math.exp(-1*(u1)*d*T*1e-4))/1.6e-19
        Tr=math.exp(-u*d*T*1e-4)
        self.logger.debug("Density = %f",d)
        self.logger.debug("Energy = %f",Energy)
        self.logger.debug("Thickness = %f um",T)
        self.logger.debug("Total atten cross section = %f",u)
        self.logger.debug("photoionization cross section = %f",u1)
        self.logger.debug("Compton scattering cross section = %f",u2)
        self.logger.debug("Rayleigh scattering cross section = %f",u3)
        self.logger.debug("Transmission = %f",Tr)
        self.logger.debug("electronpair = %f",self.electronpair)
        self.logger.debug("Flux(Total atten cross section) = %g",flux)
        self.logger.debug("Flux(Total less elastic cross section) = %g",flux2)
        self.logger.debug("Flux(photoionization cross section) = %g",flux3)
        return flux




if __name__ == "__main__":
    # signal.signal(signal.SIGINT, quit)
    # signal.signal(signal.SIGTERM, quit)
    Al=Filiter("Al",True)
    Diamond=Filiter("Diamond")
    Be = Filiter("Be")
    N = Filiter("N")
    DBPM1=Filiter("Diamond")
    DBPM2=Filiter("Diamond")
    DBPM3=Filiter("Diamond")
    DBPM5=Filiter("Diamond")
    DBPM6=Filiter("Diamond")
    # Al.element="Al"
    # print(Al.elementN)
    # print(Al.cal_tr(10,12.7))
    # print(Diamond.cal_tr(200,12.7))
    # print(Be.cal_tr(250,12.7))
    # print(Diamond.cal_tr(400,12.4)*Be.cal_tr(250,12.4))
    # print(Diamond.cal_flux(1e-6,20,12.7))
    # print(N.electronpair)
    # print(N.cal_flux(1e-6,57.15*1e3,12.7))
    print(Diamond.cal_flux(1e-6,20,12.7))