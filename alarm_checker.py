#!/usr/bin/env python3
import configparser,signal,time,sys,os
from epics import PV
from typing import Dict, Any, Union
import logsetup

class pvmonitor():
    def __init__(self,parent=None):
        # super(self.__class__,self).__init__(parent)
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        # ca.initialize_libca()
        # self.Par = par
        self.logger = logsetup.getloger2('alarm_checker',LOG_FILENAME='/home/blctl/Desktop/log/alarm_checkerlog.txt',level='DEBUG',bypassline=False)
        self.logger.info("init alarm_checker logging")
        self.epicslist = load_config('CamonitorConfig.ini')
        self.init_update = True
    def setcallback(self):
        for item in self.epicslist:
            self.epicslist[item]["connected"] = False
            self.epicslist[item]["valueupdated"] = False
        for item in self.epicslist:
            self.epicslist[item]["PVID"] = PV(item,
                    connection_callback= self.onConnectionChange,
                    callback= self.onValueChange)
    def onConnectionChange(self,pvname=None, conn= None, **kws):
        self.logger.info(f'PV connection status changed:{pvname} {conn}')
        self.epicslist[pvname]["connected"] = True
    def onValueChange(self,pvname=None, value=None, host=None,timestamp=None, **kws):
        # self.logger.info(f'')
        self.epicslist[pvname]["valueupdated"] = True                     
        threshold_type = self.epicslist[pvname]['threshold_type']
        threshold_value = self.epicslist[pvname]['threshold_value']
        bypass_notify = self.epicslist[pvname]['bypass_notify']
        if self.init_update:
            self.epicslist[pvname]["old_value"] = value
            self.logger.info(f'{pvname} value changed: {value}')
            
                    
            if self.check_all_valueupdated() and self.check_all_connected():
                self.logger.debug("All value updaed")
                self.init_update = False
            else:
                info = {}
                self.logger.debug('Wait for connection All good')
                for item in self.epicslist:
                    info[ item ] = self.epicslist[item]['valueupdated']
                self.logger.debug('Current value updated state:%s',info)
        else:#after init what we do
                if bypass_notify == True:
                    self.logger.info(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                elif self.epicslist[pvname]["old_value"] == value:
                    self.logger.info(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                elif self.epicslist[pvname]['threshold_type'] == 'None':
                    self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                elif isinstance(threshold_value, float):  # 數值型比較
                    if threshold_type == "equal" and value == threshold_value:
                        # print(f"Warning: PV '{pvname}' value {value} equals the threshold!")
                        self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                    elif threshold_type == "greater" and value > threshold_value:
                        self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                        # print(f"Warning: PV '{pvname}' value {value} is greater than the threshold!")
                    elif threshold_type == "less" and value < threshold_value:
                        self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                        # print(f"Warning: PV '{pvname}' value {value} is less than the threshold!")
                    elif threshold_type == "diff" :
                        if abs(value - self.epicslist[pvname]["old_value"]) > threshold_value:
                            self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                        else:
                            pass
                        pass
                    else:
                        self.logger.info(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                elif isinstance(threshold_value, str):  # 字串型比較
                    if threshold_type == "equal" and str(value) == threshold_value:
                        self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                        # print(f"Warning: PV '{pvname}' value '{value}' matches the threshold '{threshold_value}'!")
                    elif threshold_type == "contains" and threshold_value in str(value):
                        self.logger.error(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                        # print(f"Warning: PV '{pvname}' value '{value}' contains '{threshold_value}'!")
                    else:
                        self.logger.info(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                else:
                    self.logger.info(f'{pvname} value changed: {self.epicslist[pvname]["old_value"]} -> {value}')
                self.epicslist[pvname]["old_value"] = value
    def check_all_connected(self):
        init = True
        for item in self.epicslist:
            init = init and self.epicslist[item]["connected"]
        return init
    
    def check_all_valueupdated(self):
        init = True
        for item in self.epicslist:
            init = init and self.epicslist[item]["valueupdated"]
        return init
    def clear_epics_callback(self):
        self.logger.info('Clear Epics callback')
        for item in self.epicslist:
            self.epicslist[item]["PVID"].disconnect()
    def quit(self,signum,frame):
        # ca.finalize_libca()
        self.clear_epics_callback()
        self.logger.debug(f"PID : {os.getpid()} alarm Checker closed")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
        sys.exit()    
    
# 讀取 config 檔案，支持數值或字串型的 PV 條件
def load_config(config_file: str) -> Dict[str, Dict[str, Union[str, float,bool]]]:
    config = configparser.ConfigParser()
    config.read(config_file)

    pv_config = {}
    for section in config.sections():
        pv_name = section
        threshold_value = config[section].get("threshold_value", None)
        threshold_type = config[section].get("threshold_type", 'None')
        bypass_notify = config[section].get("bypass_notify",False)
        if bypass_notify == 'True':
            bypass_notify = True
        else:
            bypass_notify = False
        # print(pv_name,bypass_notify,type(bypass_notify))
        # 嘗試將 threshold_value 轉為數字，如果是字串則保持不變
        try:
            threshold_value = float(threshold_value)
        except ValueError:
            threshold_value = None
            pass       
        pv_config[pv_name] = {
            "threshold_value": threshold_value,
            "threshold_type": threshold_type,
            "bypass_notify": bypass_notify
        }
    return pv_config

# 回調函數，當 PV 值變動時執行，根據數值或字串條件判斷
def pv_callback(pvname=None, value=None, **kwargs):
    config = pv_conditions.get(pvname, {})
    threshold_value = config.get("threshold_value")
    threshold_type = config.get("threshold_type")

    if threshold_value is None:
        return

    # 根據 threshold_value 的類型選擇不同的條件檢查
    if isinstance(threshold_value, float):  # 數值型比較
        if threshold_type == "equal" and value == threshold_value:
            print(f"Warning: PV '{pvname}' value {value} equals the threshold!")
        elif threshold_type == "greater" and value > threshold_value:
            print(f"Warning: PV '{pvname}' value {value} is greater than the threshold!")
        elif threshold_type == "less" and value < threshold_value:
            print(f"Warning: PV '{pvname}' value {value} is less than the threshold!")
    elif isinstance(threshold_value, str):  # 字串型比較
        if threshold_type == "equals" and str(value) == threshold_value:
            print(f"Warning: PV '{pvname}' value '{value}' matches the threshold '{threshold_value}'!")
        elif threshold_type == "contains" and threshold_value in str(value):
            print(f"Warning: PV '{pvname}' value '{value}' contains '{threshold_value}'!")

# 主監控函數
def monitor_pvs(config_file: str):
    global pv_conditions
    pv_conditions = load_config(config_file)

    pv_objects = {}
    for pv_name in pv_conditions.keys():
        pv = PV(pv_name, callback=pv_callback)
        pv_objects[pv_name] = pv

    print("Monitoring PVs. Press Ctrl+C to stop.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping monitoring.")

# 設定 config 檔案名稱
config_file = "config.ini"

# 開始監控
# monitor_pvs(config_file)
if __name__ == "__main__":
    Run=pvmonitor()
    Run.setcallback()
    try:
        # start = time.time()
        # while (time.time() - start) < 30:
        #     time.sleep(0.1)
        while True:
            time.sleep(1)
            pass
    except KeyboardInterrupt:
            Run.clear_epics_callback()

    