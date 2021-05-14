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
            os.chown(os.path.join(dirpath, filename),uid,gid)
            
            os.chmod(os.path.join(dirpath, filename), 0o700)
        
def TransferData(det,saveedlist):
    currentfile = det.fileWriterFiles()
    fileDL = [i for i in currentfile if i not in saveedlist]
    # print(fileDL,len(fileDL))
    if len(fileDL) >0:
        header =json.loads(det.streamConfig('header_appendix')['value'])
        user = header['user']
        uid = header['uid']
        gid = header['gid']
        beamsize = header['beamsize']
        atten = header['atten']
        directory = header['directory']
        print(directory)
        # directory = '/home/blctl/Desktop/test12345'
        filename = header['filename']           
        for file in fileDL:
            logger.info(f'Download {file}')
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
                
            det.fileWriterSave(file,targetDir=directory)
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
                        #det.streamConfig('header_appendix')['value']
                    except Exception as e:
                        logger.warning(f'Exception : {e}')
            logger.info(f'Take time = {time.time()-t0}')
        recursive_chown(directory,uid,gid)
        
        saveedlist.extend(fileDL)
        # print(f'savelist={saveedlist}')
    
    return saveedlist




def Detectormon():
    det = DEigerClient(Par['Detector']['ip'])
    # state = det.detectorStatus('state')['value']
    # det.fileWriterSave('*','/tmp/backup')
    det.sendFileWriterCommand('clear')
    logger.warning('clear detector memory')
    det.setFileWriterConfig('nimages_per_file',10)
    det.fileWriterSave
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
            
            saveedlist =TransferData(det,saveedlist)

        elif state == 'ready':
            #check last time
            if TranferDone:
                pass
            else:
                #check last time
                logger.warning('Detector is ready,check data agaiin')
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