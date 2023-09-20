import requests,time

class EigerClient(object):
    """
    class DEigerClient provides a low level interface to the EIGER API
    """

    def __init__(self, host = '127.0.0.1', port = 80, verbose = False):
        """
        Create a client object to talk to the EIGER API.
        Args:
            host: hostname of the detector computer
            port: port usually 80 (http)
            verbose: bool value
            urlPrefix: String prepended to the urls. Should be None. Added for future convenience.
            user: "username:password". Should be None. Added for future convenience.
        """
    
        self.host = host
        self.port = port
        
    def detectorConfig(self,par:str):
        t0= time.time()
        urlPrefix = "/detector/api/1.8.0/config/"
        api_url = f'http://{self.host}:{self.port}/{urlPrefix}{par}'
        headers = {}
        mimeType = 'application/json; charset=utf-8'
        headers['Accept'] = mimeType
        data = ''
        response = requests.get(api_url, headers = headers)
        if response.status_code == 200:
            # 解析JSON响应并将其转换为字典
            response_dict = response.json()
            # print(f'detectorConfig {par} take {time.time()-t0}')
            return response_dict
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None
    def setDetectorConfig(self,par:str,value:str):
        t0= time.time()
        urlPrefix = "/detector/api/1.8.0/config/"
        api_url = f'http://{self.host}:{self.port}{urlPrefix}{par}'
        headers = {}
        mimeType = 'application/json; charset=utf-8'
        headers['Content-type'] = mimeType
        data = {}
        data['value']=value
        
        response = requests.put(api_url,json=data, headers = headers)
        if response.status_code == 200:
            # 解析JSON响应并将其转换为字典
            # print(response.headers)#{'content-type': 'application/json; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '39'}
            response_dict = response.json()
            # print(response_dict)           
            # print(f'setdetectorConfig {par=} {value=} {time.time()-t0}')
            return response_dict
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None

    def setFileWriterConfig(self,par:str,value:str):
        t0= time.time()
        urlPrefix = "/filewriter/api/1.8.0/config/"
        api_url = f'http://{self.host}:{self.port}{urlPrefix}{par}'
        headers = {}
        mimeType = 'application/json; charset=utf-8'
        headers['Content-type'] = mimeType
        data = {}
        data['value']=value
        # print(api_url,data)
        response = requests.put(api_url,json=data, headers = headers)
        if response.status_code == 200:
            # 解析JSON响应并将其转换为字典
            # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
            try:
                response_dict = response.json()
                # print(response_dict)
            except :
                print(response)
                     
            # print(f'setFileWriterConfig {par=} {value=} {time.time()-t0}')
            return True
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None
    def setMonitorConfig(self,par:str,value:str):
        t0= time.time()
        urlPrefix = "/monitor/api/1.8.0/config/"
        api_url = f'http://{self.host}:{self.port}{urlPrefix}{par}'
        headers = {}
        mimeType = 'application/json; charset=utf-8'
        headers['Content-type'] = mimeType
        data = {}
        data['value']=value
        # print(api_url,data)
        response = requests.put(api_url,json=data, headers = headers)
        if response.status_code == 200:
            # 解析JSON响应并将其转换为字典
            # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
            try:
                response_dict = response.json()
                # print(response_dict)
            except :
                print(response)
                     
            # print(f'setMonitorConfig {par=} {value=} {time.time()-t0}')
            return True
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None
    def setStreamConfig(self,par:str,value:str):
        t0= time.time()
        urlPrefix = "/stream/api/1.8.0/config/"
        api_url = f'http://{self.host}:{self.port}{urlPrefix}{par}'
        headers = {}
        mimeType = 'application/json; charset=utf-8'
        headers['Content-type'] = mimeType
        data = {}
        data['value']=value
        # print(api_url,data)
        response = requests.put(api_url,json=data, headers = headers)
        if response.status_code == 200:
            # 解析JSON响应并将其转换为字典
            # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
            try:
                response_dict = response.json()
                # print(response_dict)
            except :
                pass
                # print(response)
                     
            # print(f'setStreamConfig {par=} {value=} {time.time()-t0}')
            return True
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None
    def sendDetectorCommand(self,value:str):
        t0= time.time()
        urlPrefix = "/detector/api/1.8.0/command/"
        api_url = f'http://{self.host}:{self.port}{urlPrefix}{value}'
        headers = {}
        mimeType = 'application/json; charset=utf-8'
        headers['Content-type'] = mimeType
        # data = {}
        # data['value']=''
        # print(api_url)
        response = requests.put(api_url, data = '', headers = headers)
        if response.status_code == 200:
            # 解析JSON响应并将其转换为字典
            # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
            try:
                response_dict = response.json()
                # print(response_dict)
            except :
                print(response)
                     
            # print(f'sendDetectorCommand {value=} {time.time()-t0}')
            return True
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return None
###
def detectorConfig(par:str,host,port):
    t0= time.time()
    urlPrefix = "/detector/api/1.8.0/config/"
    api_url = f'http://{host}:{port}/{urlPrefix}{par}'
    headers = {}
    mimeType = 'application/json; charset=utf-8'
    headers['Accept'] = mimeType
    data = ''
    # print(api_url)
    response = requests.get(api_url, headers = headers)
    if response.status_code == 200:
        # 解析JSON响应并将其转换为字典
        response_dict = response.json()
        # print(response_dict)
        # print(response_dict['value'])
        # print(type(response_dict['value']))
        # print(f'detectorConfig {par} take {time.time()-t0}')
        return response_dict
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None
def setDetectorConfig(par:str,value:str,host,port):
    t0= time.time()
    urlPrefix = "/detector/api/1.8.0/config/"
    api_url = f'http://{host}:{port}{urlPrefix}{par}'
    headers = {}
    mimeType = 'application/json; charset=utf-8'
    headers['Content-type'] = mimeType
    data = {}
    data['value']=value
    
    response = requests.put(api_url,json=data, headers = headers)
    if response.status_code == 200:
        # 解析JSON响应并将其转换为字典
        # print(response.headers)#{'content-type': 'application/json; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '39'}
        response_dict = response.json()
        # print(response_dict)           
        # print(f'setdetectorConfig {par=} {value=} {time.time()-t0}')
        return response_dict
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None

def setFileWriterConfig(par:str,value:str,host,port):
    t0= time.time()
    urlPrefix = "/filewriter/api/1.8.0/config/"
    api_url = f'http://{host}:{port}{urlPrefix}{par}'
    headers = {}
    mimeType = 'application/json; charset=utf-8'
    headers['Content-type'] = mimeType
    data = {}
    data['value']=value
    # print(api_url,data)
    response = requests.put(api_url,json=data, headers = headers)
    if response.status_code == 200:
        # 解析JSON响应并将其转换为字典
        # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
        try:
            response_dict = response.json()
            # print(response_dict)
        except :
            print(response)
                    
        # print(f'setFileWriterConfig {par=} {value=} {time.time()-t0}')
        return True
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None
def setMonitorConfig(par:str,value:str,host,port):
    t0= time.time()
    urlPrefix = "/monitor/api/1.8.0/config/"
    api_url = f'http://{host}:{port}{urlPrefix}{par}'
    headers = {}
    mimeType = 'application/json; charset=utf-8'
    headers['Content-type'] = mimeType
    data = {}
    data['value']=value
    # print(api_url,data)
    response = requests.put(api_url,json=data, headers = headers)
    if response.status_code == 200:
        # 解析JSON响应并将其转换为字典
        # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
        try:
            response_dict = response.json()
            # print(response_dict)
        except :
            print(response)
                    
        # print(f'setMonitorConfig {par=} {value=} {time.time()-t0}')
        return True
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None
def setStreamConfig(par:str,value:str,host,port):
    t0= time.time()
    urlPrefix = "/stream/api/1.8.0/config/"
    api_url = f'http://{host}:{port}{urlPrefix}{par}'
    headers = {}
    mimeType = 'application/json; charset=utf-8'
    headers['Content-type'] = mimeType
    data = {}
    data['value']=value
    # print(api_url,data)
    response = requests.put(api_url,json=data, headers = headers)
    if response.status_code == 200:
        # 解析JSON响应并将其转换为字典
        # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
        try:
            response_dict = response.json()
            # print(response_dict)
        except :
            pass
            # print(response)
                    
        # print(f'setStreamConfig {par=} {value=} {time.time()-t0}')
        return True
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None
def sendDetectorCommand(value:str,host,port):
    t0= time.time()
    urlPrefix = "/detector/api/1.8.0/command/"
    api_url = f'http://{host}:{port}{urlPrefix}{value}'
    headers = {}
    mimeType = 'application/json; charset=utf-8'
    headers['Content-type'] = mimeType
    # data = {}
    # data['value']=''
    # print(api_url)
    response = requests.put(api_url, data = '', headers = headers)
    if response.status_code == 200:
        # 解析JSON响应并将其转换为字典
        # print(response.headers)#{'content-type': 'text/plain; charset=utf-8', 'date': 'Mon, 18 Sep 2023 13:39:57 GMT', 'content-length': '0'}
        try:
            response_dict = response.json()
            # print(response_dict)
        except :
            print(response)
                    
        # print(f'sendDetectorCommand {value=} {time.time()-t0}')
        return True
    else:
        print(f"请求失败，状态码：{response.status_code}")
        return None



if __name__ == "__main__":
    det = EigerClient('10.7.1.98')
    # print(det.detectorConfig('roi_mode')['value'])
    # print('init ask')
    # det.detectorConfig('roi_mode')['value']
    # print('setting')
    # det.setDetectorConfig('roi_mode','4M')
    # det.detectorConfig('roi_mode')['value']
    # det.setFileWriterConfig('mode','enabled')
    # det.setMonitorConfig('mode',"enabled")
    # det.setStreamConfig('header_appendix','asd')
    # det.sendDetectorCommand('disarm')
    det.setDetectorConfig('photon_energy',12700)
    # det.detectorConfig('photon_energy')