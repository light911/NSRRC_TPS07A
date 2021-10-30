import requests
import json
import time

class MOXA():
    def __init__(self) -> None:
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
    
    def initcover(self):
        self.set_do_state(self.DO_ReleaseCover,1)
        self.set_do_state(self.DO_CloseCover,0)
        self.set_do_state(self.DO_OpenCover,0)
        #closed cover
        self.set_do_state(self.DO_CloseCover,1)

    def OpenCover(self):
        t0=time.time()
        self.set_do_state(self.DO_CloseCover,0)
        self.set_do_state(self.DO_OpenCover,0)
        self.set_do_state(self.DO_OpenCover,1)
        self.wait_for_state('open')
        # time.sleep(0.1)
        self.set_do_state(self.DO_OpenCover,0)
        print(f'Total time = {time.time()-t0}')
    
    
    def CloseCover(self):
        t0=time.time()
        self.set_do_state(self.DO_OpenCover,0)
        self.set_do_state(self.DO_CloseCover,0)
        self.set_do_state(self.DO_CloseCover,1)
        self.wait_for_state('close')
        # time.sleep(0.1)
        self.set_do_state(self.DO_CloseCover,0)
        print(f'Total time = {time.time()-t0}')

    def wait_for_state(self,wait='open',timeout=5,interval=0.2):
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
            print("Open!")
        elif DI[self.DI_CoverisClosed] == 1:
            print("Closed!")
        else:
            print("Unkonw!")

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
        print(distr)
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



if __name__ == "__main__":
    t0 = time.time()
    header={'Accept': 'vdn.dac.v1','Content-Type':'application/json'}
    ip='10.7.1.205'
    di_url = f'http://{ip}/api/slot/0/io/di'
    do_url = f'http://{ip}/api/slot/0/io/do/1/doStatus'
    io = MOXA()
    # io.show_current_state()
    # io.CloseCover()
    # io.initcover()
    io.OpenCover()
    # while True:
    #     io.show_di_state()
    #     time.sleep(0.1)
    # io.show__single_do_state()
    # io.set_do_state(0,1)
    