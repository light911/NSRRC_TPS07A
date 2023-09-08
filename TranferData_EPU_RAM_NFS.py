#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 13 15:03:07 2021

@author: blctl
"""

from multiprocessing import Process,Queue
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
Par = Config.Par
rsyncP=[]
logger = logsetup.getloger2('TransferData',LOG_FILENAME='TransferDataLOG.txt',level = Par['Debuglevel'])

def recursive_chown(path,uid,gid):
    for dirpath, dirnames, filenames in os.walk(path):
        os.chown(dirpath,uid,gid)
        for filename in filenames:
            try:
                os.chown(os.path.join(dirpath, filename),uid,gid)
                
                os.chmod(os.path.join(dirpath, filename), 0o700)
            except:
                pass
        
def TransferData(det,saveedlist,saveedpath,datareturn:Queue,toNFS=True):
   
    currentfile = det.fileWriterFiles()
    if toNFS:
        log = "NFS"
    else:
        log = "EPU"
    try :
        fileDL = [i for i in currentfile if i not in saveedlist]
    except :
        fileDL = []
    # logger.info(f'{log}:{saveedlist=},{fileDL=}')    
    # print(fileDL,len(fileDL))
    if len(fileDL) >0:
        header =json.loads(det.streamConfig('header_appendix')['value'])
        user = header['user']
        uid = header['uid']
        gid = header['gid']
        beamsize = header['beamsize']
        atten = header['atten']
        #directory = header['directory'].replace('/data','/tps2gs/tps2ces/tps2nfs')
        #directory = header['directory'].replace('/data','/mnt/data_buffer')
        directory = header['directory']
        if toNFS:
            ramdirectory = header['directory']
        else:
            ramdirectory = header['directory'].replace('/data','/mnt/proc_buffer')
        # print(directory)
        # directory   /tps2gs/tps2ces/tps2nfs
        # directory = '/home/blctl/Desktop/test12345'
        filename = header['filename']           
        for file in fileDL:
           
            # t0=time.time()
            #mkdir folder
            Path(directory).mkdir(mode= 0o700,parents=True, exist_ok=True)
            if not toNFS:
                Path(ramdirectory).mkdir(mode= 0o700,parents=True, exist_ok=True)

            fullpath = directory + "/" + file
            if Path(fullpath).exists() and toNFS:
                overwriteFolder= directory + '/OVERWRITE_OLD'
                logger.warning(f'{log}: File {fullpath} is exist! Move to OVERWRITE_OLD')
                Path(overwriteFolder).mkdir(parents=True, exist_ok=True)
                movepath = overwriteFolder+ "/" + file
                Path(fullpath).replace(movepath)
            t0=time.time()
            logger.info(f'{log}: Download {file} to {header["directory"]}')
            det.fileWriterSave(file,targetDir=ramdirectory)
            
            targetPath = os.path.join(ramdirectory,file)
            filesize = os.stat(targetPath).st_size * 9.5367431640625e-7
            mastername = filename + "_master.h5"
            if file == mastername:
                targetPath = os.path.join(ramdirectory,file)
                logger.info(f'{log}: add Header info')
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

                        # disgeo = f['/entry/instrument/detector/geometry/translation/distances']
                        # disgeo_data=disgeo[()]#
                        # beam1=disgeo_data[0]*-0.075
                        # beam2=disgeo_data[1]*0.075
                        # # beam1 = int(beam1*1000)/1000
                        # # beam2 = int(beam2*1000)/1000
                        # disgeo[()] = [beam1,beam2,-1000*distance]#for DIALS [-0.1555,0.163575,-150]



                    except Exception as e:
                        logger.warning(f'{log}: Exception : {e}')
            runtime=time.time()-t0
            speed = filesize/runtime
            logger.info(f'{log}: Take time = {runtime}, File size = {filesize} MB, speed = {speed} MB/sec')
            #rsync to nfs
            # rsync(targetPath,targetPath.replace('/mnt/proc_buffer','/data'))
            saveedpath.append(targetPath)
            #final remove it on DCU
            if toNFS:
                ans =re.match("(.*)_master.h5",file)
                if ans:
                    #not to delete master file
                    pass
                else:
                    logger.info(f'{log}: try to remove {file} on DCU')
                    requests.delete(f'http://10.7.1.98/data/{file}')
        recursive_chown(ramdirectory,uid,gid)
        saveedlist.extend(fileDL)
        
        # print(f'savelist={saveedlist}')
    datareturn.put((saveedlist,saveedpath))
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
    
def Detectormon():
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

def removerawdata(masterfile):
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
Detectormon()
