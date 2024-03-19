#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 13 15:03:07 2021

@author: blctl
"""

from multiprocessing import Process,Queue,Manager
from Eiger.DEiger2Client import DEigerClient
import Config
import time,os,re
import json
from pathlib import Path
import pathlib
import logsetup
import h5py
from subprocess import Popen, PIPE, TimeoutExpired  
import requests
from flask import Flask,jsonify,request,Response
Par = Config.Par
rsyncP=[]
logger = logsetup.getloger2('TransferData',LOG_FILENAME='TransferDataLOG.txt',level = Par['Debuglevel'])
m = Manager()
ProcessFile = m.list()
def check_file_lock(file_path):
    try:
        # 使用 os.O_WRONLY 和 os.O_CREAT 标志尝试以写模式创建文件
        # os.O_EXCL 标志确保如果文件已被锁定，则抛出 FileExistsError 异常
        fd = os.open(file_path, os.O_WRONLY)
        os.close(fd)  # 关闭文件描述符
        return False  # 文件没有被锁定
    # except FileExistsError:
    #     return True   # 文件被锁定
    except Exception as e:
        logger.warning(f'Checking file lock exception = {e}')
        return True
def recursive_chown(path,uid,gid):
    for dirpath, dirnames, filenames in os.walk(path):
        os.chown(dirpath,uid,gid)
        for filename in filenames:
            try:
                os.chown(os.path.join(dirpath, filename),uid,gid)
                
                os.chmod(os.path.join(dirpath, filename), 0o700)
            except:
                pass
        
def TransferData(det:DEigerClient,saveedlist,saveedpath,datareturn:Queue,header,expctedlist:list,toNFS=True):
    '''
    expctedlist: expcted file list gen by header
    '''
    t0 = time.time()
    init = True
    detabort = False
    needtoDL = expctedlist
    Autoprocess = False
    bypassDownload = False
    user = header['user']
    uid = header['uid']
    gid = header['gid']
    beamsize = header['beamsize']
    atten = header['atten']
    runIndex =  int(header['runIndex'])
    TotalFrames = header['TotalFrames']
    fileindex = header['fileindex']   
    directory = header['directory']
    filename = header['filename']
    if toNFS:
        log = "NFS"
        ramdirectory = header['directory']
        Path(ramdirectory).mkdir(mode= 0o700,parents=True, exist_ok=True)
        os.chown(ramdirectory,uid,gid)
    else:
        log = "EPU"
        ramdirectory = header['directory'].replace('/data','/mnt/proc_buffer')
        # data to ram
        # raster runindex = 101 or 102
        # mutipostion fileindex = 0, runIndex=1
        # normal dataset runIndex 1~16
        # test image runIndex = 0 
        if TotalFrames >= 20 and runIndex < 40 and fileindex != 0:
            Path(ramdirectory).mkdir(mode= 0o700,parents=True, exist_ok=True)
            Autoprocess = True
            pass
        else:
            bypassDownload = True#skip download
            Autoprocess = False
    while True:
        #when we got all except file or, fileWriterStatus from acquire to Ready Break loop
        state = det.fileWriterStatus('state')['value']
        currentfileWriterpatten = det.fileWriterConfig('name_pattern')['value']#series_$id , test_0_0003
        #make sure collect is started,
        # dhs   detectorstat                       filewriter
        # arm   idle->configure->READY->acquire-ilde  ready=>acquire->ready
        if state == 'acquire':
            init = False
        #when we got all except file or, fileWriterStatus from acquire to Ready Break loop
        if init :
            pass
        else:
            if state == 'ready':
                #fileWriterStatus from acquire to ready
                #if there is no file to downlaod may be detector abort
                detabort = True

        currentfile = det.fileWriterFiles()#['test_0_0008_data_000001.h5', 'test_0_0008_master.h5']

        if len(needtoDL) >0:
            # check frist item can we found on detector?
            if needtoDL[0] in currentfile:
                file = needtoDL.pop(0)
                fullpath = directory + "/" + file
                if Path(fullpath).exists() and toNFS:
                    overwriteFolder= directory + '/OVERWRITE_OLD'
                    logger.warning(f'{log}: File {fullpath} is exist! Move to OVERWRITE_OLD')
                    Path(overwriteFolder).mkdir(parents=True, exist_ok=True)
                    movepath = overwriteFolder+ "/" + file
                    Path(fullpath).replace(movepath)
                    recursive_chown(overwriteFolder,uid,gid)
                t0=time.time()                    
                logger.info(f'{log}: Download {file} to {ramdirectory}')
                if bypassDownload:
                    pass
                    filesize=0
                    targetPath = os.path.join(ramdirectory,file)
                else:
                    det.fileWriterSave(file,targetDir=ramdirectory)
                    targetPath = os.path.join(ramdirectory,file)
                    filesize = os.stat(targetPath).st_size * 9.5367431640625e-7
                mastername = filename + "_master.h5"
                if file == mastername and not bypassDownload:
                    targetPath = os.path.join(ramdirectory,file)
                    logger.info(f'{log}: add Header info')
                    # time.sleep(0.2) #make sure file ok on raid
                    tcheck_lock0 = time.time()
                    _flag = True
                    while  check_file_lock(targetPath):
                        if _flag:
                            _flag=False
                            logger.warning(f'{log}: master file is locked, we need wait more time.')
                        time.sleep(0.2)
                    logger.info(f'{log}: finish check file lock on master file, take {time.time()-tcheck_lock0} sec')
                    with h5py.File(targetPath,'r+') as f:
                        try:
                            f['/entry/instrument/beam'].create_group(u'attenuator')
                            f['/entry/instrument/beam/attenuator'].create_dataset(u'attenuator_transmission', data=float(atten))
                            f['/entry/instrument/beam/'].create_dataset(u'name', data=b'NSRRC BEAMLINE TPS 07A')
                            f['/entry/instrument/beam/'].create_dataset(u'incident_beam_size', data=float(beamsize))
                            f['/entry/'].create_group(u'extrainfo')
                            for data in header:
                                name = data
                                value = bytes(str(header[data]), encoding='utf-8')
                                f['/entry/extrainfo/'].create_dataset(name, data=value)    
                            #det.streamConfig('header_appendix')['value']
                            #modify some header
                            f['/entry/sample/transformations/omega'].attrs['vector'] = [0,1,0]#for DIALS
                            distance = f['/entry/instrument/detector/detector_distance'][()]
                            dis = f['/entry/instrument/detector/transformations/translation']
                            dis[()]=distance# DIALS use for cal res?
                            dis.attrs['vector'] = [0,0,-1]

                        except Exception as e:
                            logger.warning(f'{log}: Exception : {e}')
                runtime=time.time()-t0
                speed = filesize/runtime
                logger.info(f'{log}: Take time = {runtime}, File size = {filesize} MB, speed = {speed} MB/sec')
                #rsync to nfs
                # rsync(targetPath,targetPath.replace('/mnt/proc_buffer','/data'))
                saveedpath.append(targetPath)
                
                # #final remove it on DCU
                # # NFS is slowest, so after NFS download delete it
                # # or using Queue info to control ?
                # if toNFS:
                #     ans =re.match("(.*)_master.h5",file)
                #     if ans:
                #         #not to delete master file
                #         # we will delete it on main process
                #         pass
                #     else:
                #         logger.info(f'{log}: try to remove {file} on DCU')
                #         requests.delete(f'http://10.7.1.98/data/{file}')
                
                datareturn.put(['download',file])
                if toNFS:
                    logger.info(f'{log}: start to recursive_chown')
                    if fileindex == 0:
                        # mutiposition
                        logger.info(f'{log}: mutiposition data,change single data set')
                        try:
                            # os.chown(ramdirectory,uid,gid)
                            os.chown(fullpath,uid,gid)
                            os.chmod(fullpath, 0o700)
                        except:
                            logger.info(f'{log}: has problem when chown {fullpath}')
                        pass
                    else:
                        #normal dataset 
                        try:
                            # os.chown(ramdirectory,uid,gid)
                            os.chown(fullpath,uid,gid)
                            os.chmod(fullpath, 0o700)
                        except:
                            logger.info(f'{log}: has problem when chown {fullpath}')
                        pass
                        #maybe slow....
                        # recursive_chown(ramdirectory,uid,gid)
                    logger.info(f'{log}: Done for recursive_chown')
            elif detabort:
                logger.info(f'{log}: There still has some file need to download, but not found in fileWriter. and fileWriter is ready(no new file will generate)')
                #detect no file and fileWriter ready,maybe detector abort
                break           
            else:
                # my file not on detector wait more time
                time.sleep(0.1)
                pass
            
            # print(f'savelist={saveedlist}')
        else:
            #not thing in needtoDL
            break
    datareturn.put(['jobdone'])

    
    #for ram start autoproesss, raid run Autostra
    # raster runindex = 101 or 102
    # mutipostion fileindex = 0, runIndex=1
    # normal dataset runIndex 1~16
    # test image runIndex = 0 
    if toNFS:
        # ramdirectory = header['directory']
        # Autostra
        #TODO
        if runIndex == 0:
            url = 'http://10.7.1.107:65000/job'
            masterfile =  ramdirectory + "/" + filename +'_master.h5'
            data = {'path':masterfile}
            # response = requests.post(url , json=data)
            # logger.info(f'{log}: Send command to Autostra. {response=}')
            p = Process(target=sendtoAutostra,args=(url,data))
            p.start()
        pass
    elif bypassDownload:
        pass
    elif Autoprocess:
        #TODO
        #not raster
        #not mutipos (fileindex==0)
        #send to auto process
        url = 'http://10.7.1.108:65001/job'

        #/data/blctl/test/test_0_matser.h5

        masterfile =  directory + "/" + filename +'_master.h5'
        # masterfile.replace('/data','/mnt/proc_buffer')
        # masterfile =  f'{self.directory}/{self.filename}_{str(self.fileindex).zfill(4)}_master.h5'
        data = {'path':masterfile}
        p = Process(target=sendtoAutostra,args=(url,data))
        p.start()
        # response = requests.post(url , json=data)
        # logger.info(f'{log}: Send command to Autoprocess. {response=}')
        pass
    # logger.info(f'{log}: {datareturn} send,{(saveedlist,saveedpath)}')
    return saveedlist,saveedpath
def rsync(source,target):
    command=['rsync','-avWh','--no-compress',source,target]
    p = Popen(command, shell=False, stdin = PIPE, stdout = PIPE, stderr = PIPE)
    rsyncP.append(p)

def savecurrentdata(det):
    
    currentfile = det.fileWriterFiles()
    
    
    try:
        if len(currentfile) >0:
            timestr = time.strftime("%Y%m%d-%H%M%S") + '_backup'
            floder = '/data/tmp/' + timestr
            logger.warning(f'Ther has file on detector!Move it to  {floder}')
            # directory = floder.replace('/data','/tps2gs/tps2ces/tps2nfs')
            directory = floder
            Path(directory).mkdir(parents=True, exist_ok=True)
            for file in currentfile:
                logger.info(f'Download {file} to {floder}')
                det.fileWriterSave(file,targetDir=directory)
    except :
        pass
    
def Detectormon():#not used
    os.nice(-15)
    detforNFS = DEigerClient('192.168.31.98')
    detforEPU = DEigerClient('10.7.1.98')
    det = DEigerClient('10.7.1.98')
    NFSQ = Queue()
    EPUQ = Queue()
    savecurrentdata(detforEPU)
    det.sendFileWriterCommand('clear')
    logger.warning('clear detector memory')
    TranferDone= True
    saveedlistNFS=[]
    saveedpathNFS=[]
    saveedlistEPU=[]
    saveedpathEPU=[]
    while True:
        try:
            state = det.fileWriterStatus('state')['value']
        except Exception as e:
            logger.critical(f'Erro on getting state: {e}')
        if state == 'acquire':
            if TranferDone:
                Tstart = time.time()
                logger.warning('Detector start to acquire!')
            TranferDone= False
            NFSp = Process(target=TransferData,args=(detforNFS,saveedlistNFS,saveedpathNFS,NFSQ,True,))
            EPUp = Process(target=TransferData,args=(detforEPU,saveedlistEPU,saveedpathEPU,EPUQ,False,))
            NFSp.start()
            EPUp.start()
            EPUp.join()
            NFSp.join()
            try:
                saveedlistEPU,saveedpathEPU = EPUQ.get(timeout=1)
                saveedlistNFS,saveedpathNFS = NFSQ.get(timeout=1)#this two list(EPU NFS )should br the same
            except Exception as e:
                logger.critical(f'Process has problem, we not get Queue')
            #delete what we download? but not master file move to nfs download to remove
            # for item in saveedlistEPU:
            #     ans =re.match("(.*)_master.h5",item)
            #     if ans:
            #         pass
            #     else:
            #         logger.info(f'try to remove {item} on DCU')
            #         requests.delete(f'http://10.7.1.98/data/{item}')
        elif state == 'ready':
            #check last time
            if TranferDone:
                pass
            else:
                #check last time
                logger.warning('Detector is ready,check data again')
                time.sleep(0.2)
                NFSp = Process(target=TransferData,args=(detforNFS,saveedlistNFS,saveedpathNFS,NFSQ,True,))
                EPUp = Process(target=TransferData,args=(detforEPU,saveedlistEPU,saveedpathEPU,EPUQ,False,))
                NFSp.start()
                EPUp.start()
                EPUp.join()
                NFSp.join()
                try:
                    saveedlistEPU,saveedpathEPU = EPUQ.get()#
                    saveedlistNFS,saveedpathNFS = NFSQ.get()#this two list(EPU NFS )should br the same
                except Exception as e:
                    logger.critical(f'Process has process, we not get Queue')

                # if len(saveedpath) <=1 :
                #     logger.warning('saveedpath not correct!try again')
                #     time.sleep(0.5)
                #     saveedlist,saveedpath = TransferData(det,saveedlist,saveedpath)
                TranferDone = True
                logger.info(f'Total Tranfer time from DCU ={time.time()-Tstart}')
                # logger.info(f'Check rsync state')
                #check rsync P
                # notok = True
                # while notok:
                #     notok = False
                #     oklist=[]
                #     for p in rsyncP:
                #         state = p.poll()
                #         if state == 0:
                #             #stop normally
                #             logger.debug(f'rsync process:{p.stdout.read()}')
                #             oklist.append(p)
                #             pass
                #         elif state == 1:
                #             logger.warning(f'rsync process:{p.stderr.read()}')
                #         else:
                #             notok = True
                #     for ok in oklist:
                #         rsyncP.remove(ok)

                logger.info(f'Total Finish all job ={time.time()-Tstart}')
                det.sendFileWriterCommand('clear')
                logger.warning('clear detector memory')
                logger.warning(f'{saveedpathEPU=}')
                logger.warning(f'{saveedpathNFS=}')
                
                #active Autoprocess by detector stop
                #remove image less than 19(which will not clean by autoprocess)
                
                for item in saveedpathEPU:
                    ans =re.match("(.*)_master.h5",item)
                    # print(f'{item=},{ans=}')
                    if ans:
                        masterfile = item

                try:               
                    removerawdata(masterfile)
                except Exception as e:
                    print(f'Error:{e}')
                saveedlistNFS=[]
                saveedpathNFS=[]
                saveedlistEPU=[]
                saveedpathEPU=[]
                pass
        elif state == 'error':
            logger.warning('fileWriterStatus state = error.try to reset it')
            error = det.fileWriterStatus('error')['value']
            logger.warning(f'Error = {error}')
            det.sendFileWriterCommand("initialize")
            det.setFileWriterConfig('mode','enabled')
            pass
        elif state == 'disabled':
            logger.warning('fileWriterStatus state = disabled.try to enabled it')
            det.sendFileWriterCommand("initialize")
            det.setFileWriterConfig('mode','enabled')
            pass
        else:
            print(state)
        
        time.sleep(0.1)

def sendtoAutostra(url,data):
    response = requests.post(url , json=data)
    print(response.text)

    pass
def removerawdata(masterfile):#not used
    remove = False
    path = pathlib.Path(masterfile)
    removelist = []
    removelist.append(path)
    with h5py.File(path,'r') as f:
        # print(f['/entry/data/'].keys())
        nimage= f['/entry/instrument/detector/detectorSpecific/nimages'][()]
        filename = f['/entry/extrainfo']['filename'][()].decode("utf-8") 
        runIndex = float(f['/entry/extrainfo']['runIndex'][()].decode("utf-8"))
        fileindex = int(f['/entry/extrainfo']['fileindex'][()].decode("utf-8"))
        if runIndex >= 40:
            #raster
            remove = True
        print(f'{fileindex=}')
        if fileindex == 0:
            # mutiposition
            remove = True
        if int(nimage)<=19:
            remove=True
        for key in f['/entry/data/'].keys():
            filepath = pathlib.Path(f"{path.parent}/{filename}_{key}.h5")
            removelist.append(filepath)
    # print(f'{remove}')
    if remove:
        for item in removelist:
            print(f'remove file : [{item}]')
            item.unlink(missing_ok=True)
def genDatasetNames(totalimage:int,nimages_per_file:int=1000,Filename:str='Test'):
    maxfileset = totalimage // nimages_per_file
    if  totalimage % nimages_per_file ==0:
        maxfileset = maxfileset -1
    maxfileset += 1
    datalists = []
    for i in range(maxfileset):
        filenum = i + 1
        dataname = f'{Filename}_data_{filenum:06}.h5'
        datalists.append(dataname)
    # print(datalist)
    return datalists
app = Flask('TranferDataServer')

@app.route('/', methods=['GET', 'POST'])
def welcome():
    return "Hello World!"

@app.route('/tranfer', methods=['POST'])
def jobPOST():
    getdata = request.data #give you strig
    #check if there has same file downloading?
    alreadRunning = False
    if request.is_json:
        header = request.get_json()
        filename = header['filename']   
        runIndex =  header['runIndex']
        TotalFrames = header['TotalFrames']
        logger.warning(f'Server got ask download:{filename=} ,{runIndex=},{TotalFrames=}')    
        logger.debug(f'{header=}')    
        if len(ProcessFile)>=1:
            for item in ProcessFile:
                if item == filename:
                    alreadRunning = True
        if alreadRunning:
            logger.warning('There has same file ({filename})downloading!')
            logger.debug(f'Current {ProcessFile[:]=}')
            # for item in ProcessFile:
            #     print(f"path : {item}")
            ans = 'There has same file ({filename})downloading!'
        else:
            ProcessFile.append(filename)
            logger.debug(f'Add job, Current {ProcessFile[:]=}')
            p = Process(target=monitor_and_download_file,args=(header,ProcessFile))
            p.start()
            ans = "OK,add job"
    else:       
        logger.warning('not json')
        # print('Try covert data: ',request.get_json(True))
        ans = "Got : " + str(getdata)
    return ans

# @app.route('/job', methods=['GET'])
# def jobGET():
    pass
    # ans = {}
    # for i,a in enumerate(datalist):
    #     ans[i]=a
        
    # return  jsonify(ans)
# Detectormon()
def requestsdelete(command):
    logger.debug(f'{command=}')
    logger.debug(requests.delete(command))
def monitor_and_download_file(header,ProcessFile: list):
    filename = header['filename']
    fileindex = header['fileindex']
    TotalFrames = header['TotalFrames']
    detforNFS = DEigerClient('192.168.31.98')
    detforEPU = DEigerClient('10.7.1.98')
    NFSQ = Queue()
    EPUQ = Queue()
    saveedlistNFS=[]
    saveedpathNFS=[]
    saveedlistEPU=[]
    saveedpathEPU=[]
    
    #except file 
    datalist =[]
    masterfile = filename + "_master.h5"
    datalist.append(masterfile)
    datalist.extend(genDatasetNames(TotalFrames,1000,filename)) 
    NFSp = Process(target=TransferData,args=(detforNFS,saveedlistNFS,saveedpathNFS,NFSQ,header,datalist,True,))
    EPUp = Process(target=TransferData,args=(detforEPU,saveedlistEPU,saveedpathEPU,EPUQ,header,datalist,False,))
    NFSp.start()
    EPUp.start()
    NFSjobdone = False
    EPUjobdone = False
    delfilelist=[]
    while True:
        #check filewrite state
        try:
            state = detforEPU.fileWriterStatus('state')['value']
        except Exception as e:
            logger.critical(f'Erro on getting state: {e}')
        if state == 'error' :
            logger.warning('fileWriterStatus state = error.try to reset it')
            error = detforEPU.fileWriterStatus('error')['value']
            logger.warning(f'Error = {error}')
            detforEPU.sendFileWriterCommand("initialize")
            detforEPU.setFileWriterConfig('mode','enabled')
        elif state == 'disabled':
            logger.warning('fileWriterStatus state = disabled.try to enabled it')
            detforEPU.sendFileWriterCommand("initialize")
            detforEPU.setFileWriterConfig('mode','enabled')

        # time.sleep(0.1)
        try:
            NFSanswer = NFSQ.get(block=False,timeout=0.1)
        except:
            NFSanswer = None
        try:
            EPUanswer = EPUQ.get(block=False,timeout=0.1)
        except:
            EPUanswer = None
        if NFSanswer:
            #list [0] = state, other is data
            if NFSanswer[0] == 'download':
                logger.debug(f'Got NFS Q download {NFSanswer[1]}')
                saveedlistNFS.append(NFSanswer[1])
            elif NFSanswer[0] == 'jobdone':
                logger.debug(f'Got NFS Q jobdone')
                NFSjobdone = True
            elif NFSanswer[0] == 'detabort':
                NFSjobdone = True
                pass
            else:
                logger.warning(f'unknow result {NFSanswer}')
            pass
        if EPUanswer:
            #list [0] = state, other is data
            if EPUanswer[0] == 'download':
                logger.debug(f'Got EPU Q download {EPUanswer[1]}')
                saveedlistEPU.append(EPUanswer[1])
            elif EPUanswer[0] == 'jobdone':
                logger.debug(f'Got EPU Q jobdone')
                EPUjobdone = True
            elif EPUanswer[0] == 'detabort':
                EPUjobdone = True
                pass
            else:
                logger.warning(f'unknow result {EPUanswer}')
            pass
        
        #del file on detector
        # 将列表 a 和 b 转换为集合
        set_a = set(saveedlistNFS)
        set_b = set(saveedlistEPU)
        #排除
        set_c = set(delfilelist)

        filetodel = list(set_a.intersection(set_b) - set_c)
        # print(filetodel)
        # print(set_a)
        # print(set_b)
        # print(set_c)
        # print(set_a.intersection(set_b))
        
        if filetodel:
            for file in filetodel:
                if file == masterfile:
                    #bypass master file
                    pass
                else:
                    logger.info(f'Try to remove {file} on DCU')
                    # ansfordel = requests.delete(f'http://10.7.1.98/data/{file}')
                    command = f'http://10.7.1.98/data/{file}'
                    p1 = Process(target=requestsdelete,args=(command,))
                    p1.start()
                    
            delfilelist.extend(filetodel)
        #state check
        if EPUjobdone and NFSjobdone:
            logger.debug(f'Both EPU and NFS jobdone.')
            break
    logger.info(f'Try to remove {masterfile} on DCU')
    
    # requests.delete(f'http://10.7.1.98/data/{masterfile}')
    command = f'http://10.7.1.98/data/{masterfile}'
    p2 = Process(target=requestsdelete,args=(command,))
    p2.start()
    ProcessFile.remove(filename)
    logger.info(f'Finish Download dataset {filename} , Allfile={saveedlistNFS}')
    logger.debug(f'After download dataset Current {ProcessFile[:]=}')
    pass
if __name__ == '__main__':       
    # app.run(host='0.0.0.0', port=65000,threaded=False,processes=2)
    det = DEigerClient('10.7.1.98')
    savecurrentdata(det)
    det.sendFileWriterCommand('clear')
    logger.warning('clear detector memory')
    
    try:
        os.nice(-15)
    except Exception as e:
        logger.warning(f'Fail to setting nice,Error = {e}')
    app.run(host='0.0.0.0', port=64444,threaded=True)