
from Tools import Filiter
from epics import caput,caget_many,caget
import time
import math

def TPS07AFlux(interval=0.2):
    count_pvlist=["07A-DBPM1:signals:sa.Sum","07A-DBPM2:signals:sa.Sum","07A-DBPM3:signals:sa.Sum","07A-DBPM5:signals:sa.Sum","07A-DBPM6:signals:sa.Sum"]
    pvputlist=["07a-ES:DBPM1:Flux","07a-ES:DBPM2:Flux","07a-ES:DBPM3:Flux","07a-ES:DBPM5:Flux","07a-ES:DBPM6:Flux"]
    dbpm123gain_pvlist=["07A-DBPM1:current_range","07A-DBPM2:current_range","07A-DBPM3:current_range"]
    fluxlist=['dbpm1','dbpm2','dbpm3','dbpm5','dbpm6']
    DBPM = Filiter("Diamond")
    Kapton=Filiter("Kapton")
    Air = Filiter("Air")
    Al = Filiter("Al")
    while True:
        count_list=caget_many(count_pvlist)
        dbpm123gain= caget_many(dbpm123gain_pvlist)
        energy = caget("07a:DCM:Energy.VAL")
        for i,count in enumerate(count_list):
            if i <3 :#DBPM1 2 3
                if int(dbpm123gain[i]) == int(1):
                    fullscale = 60*1e-9#60nA
                else:
                    fullscale = 2*math.pow(10,(int(dbpm123gain[i]-9)))
                # print(fullscale)
                current = count/131071*fullscale
                T=50
                
            else:
                #fix at 10uA
                current = count/1e5*1e-6
                T=20
            calflux=DBPM.cal_flux(current,T,energy)
            
            if current < 5e-10:
                calflux = 0
            fluxlist[i]=calflux

            print(f'put {pvputlist[i]} with {calflux} Current = {current} Energy={energy} Thinckness={T}um')
            caput(pvputlist[i],calflux)
        
        AirTr = Air.cal_tr(150000,energy)
        AlTr = Al.cal_tr(20,energy)
        KaptonTr = Kapton.cal_tr(50, energy)
        totalTr=AirTr*AlTr*KaptonTr
        calflux = fluxlist[4]*totalTr

        caput('07a-ES:Sample:Flux',calflux)
        print(f'put 07a-ES:Sample:Flux with {calflux:.3g} Current = {current} Energy={energy} Tr= {totalTr} Air Tr={AirTr} Al Tr={AlTr} Kapton Tr={KaptonTr}')
        print()

        time.sleep(interval)



if __name__ == "__main__":
    TPS07AFlux()
