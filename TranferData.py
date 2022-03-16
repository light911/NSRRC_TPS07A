#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 13 15:03:07 2021

@author: blctl
"""

from Eiger.DEiger2Client import DEigerClient
import Config
import time,os
import json
from pathlib import Path
import logsetup
import h5py

Par = Config.Par

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
        
def TransferData(det,saveedlist):
    currentfile = det.fileWriterFiles()
    
    try :
        fileDL = [i for i in currentfile if i not in saveedlist]
    except :
        fileDL = []
        
    # print(fileDL,len(fileDL))
    if len(fileDL) >0:
        header =json.loads(det.streamConfig('header_appendix')['value'])
        user = header['user']
        uid = header['uid']
        gid = header['gid']
        beamsize = header['beamsize']
        atten = header['atten']
        directory = header['directory'].replace('/data','/tps2gs/tps2ces/tps2nfs')
        # print(directory)
        # directory   /tps2gs/tps2ces/tps2nfs
        # directory = '/home/blctl/Desktop/test12345'
        filename = header['filename']           
        for file in fileDL:
           
            t0=time.time()
            #mkdir folder
            Path(directory).mkdir(mode= 0o700,parents=True, exist_ok=True)
            fullpath = directory + "/" + file
            if Path(fullpath).exists() :
                overwriteFolder= directory + '/OVERWRITE_OLD'
                logger.warning(f'File {fullpath} is exist! Move to OVERWRITE_OLD')
                Path(overwriteFolder).mkdir(parents=True, exist_ok=True)
                movepath = overwriteFolder+ "/" + file
                Path(fullpath).replace(movepath)
            
            logger.info(f'Download {file} to {header["directory"]}')
            det.fileWriterSave(file,targetDir=directory)
            targetPath = os.path.join(directory,file)
            filesize = os.stat(targetPath).st_size * 9.5367431640625e-7
            mastername = filename + "_master.h5"
            if file == mastername:
                targetPath = os.path.join(directory,file)
                logger.info(f'add Header info')
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
                        logger.warning(f'Exception : {e}')
            runtime=time.time()-t0
            speed = filesize/runtime
            logger.info(f'Take time = {runtime}, File size = {filesize} MB, speed = {speed} MB/sec')
        recursive_chown(directory,uid,gid)
        
        saveedlist.extend(fileDL)
        # print(f'savelist={saveedlist}')
    
    return saveedlist

def savecurrentdata(det):
    
    currentfile = det.fileWriterFiles()
    
    
    try:
        if len(currentfile) >0:
            timestr = time.strftime("%Y%m%d-%H%M%S") + '_backup'
            floder = '/data/tmp/' + timestr
            logger.warning(f'Ther has file on detector!Move it to  {floder}')
            directory = floder.replace('/data','/tps2gs/tps2ces/tps2nfs')
            Path(directory).mkdir(parents=True, exist_ok=True)
            for file in currentfile:
                det.fileWriterSave(file,targetDir=directory)
    except :
        pass
    
def Detectormon():
    det = DEigerClient(Par['Detector']['ip2'])
    savecurrentdata(det)
    # state = det.detectorStatus('state')['value']
    # det.fileWriterSave('*','/tmp/backup')
    det.sendFileWriterCommand('clear')
    logger.warning('clear detector memory')
    # det.setFileWriterConfig('nimages_per_file',10)
    TranferDone= True
    saveedlist=[]
    while True:
        # t0=time.time()
        # state = det.detectorStatus('state')['value']
        state = det.fileWriterStatus('state')['value']
        
        # print(f'Run time = {time.time()-t0}') #0.001sec
        if state == 'acquire':
            if TranferDone:
                Tstart = time.time()
                logger.warning('Detector start to acquire!')
            TranferDone= False
            
            saveedlist = TransferData(det,saveedlist)

        elif state == 'ready':
            #check last time
            if TranferDone:
                pass
            else:
                #check last time
                logger.warning('Detector is ready,check data again')
                time.sleep(0.1)
                TransferData(det,saveedlist)
                saveedlist=[]
                TranferDone = True
                logger.info(f'Total time={time.time()-Tstart}')
                det.sendFileWriterCommand('clear')
                logger.warning('clear detector memory')
                pass
        elif state == 'error':
            pass
        elif state == 'disabled':
            
            pass
        else:
            print(state)
        
        time.sleep(0.01)

Detectormon()