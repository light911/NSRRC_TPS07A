#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 16:35:29 2021

@author: blctl
"""

import h5py
import numpy as np

def descend_obj(obj,sep='\t',find=None):
    """
    Iterate through groups in a HDF5 file and prints the groups and datasets names and datasets attributes
    """
    # print(type(obj))
    if type(obj) in [h5py._hl.group.Group,h5py._hl.files.File]:
        for key in obj.keys():
            # print(sep,'-',key,':',obj[key])
            if find:
                if key == find:
                    
                    print('here')
                    print(f'key = {key}')
                    print(obj[key])
                    print(obj.keys())
                    
                    # return obj[key]
                    
            else:
                print(sep,'-',key,':',obj[key])
            descend_obj(obj[key],sep=sep+'\t',find=find)
            
    elif type(obj)==h5py._hl.dataset.Dataset:
        for key in obj.attrs.keys():
            print(sep+'\t','-',key,':',obj.attrs[key])
            
    # return "a"

def h5dump(path,group='/'):
    """
    print HDF5 file metadata

    group: you can give a specific group, defaults to the root group
    """
    with h5py.File(path,'r') as f:
         descend_obj(f[group])


file="/home/blctl/Downloads/test2_0_0045_master.h5"
with h5py.File(file,'r+') as f:
    h5py.File
    # print("ANS=",descend_obj(f,find="beam"))
    # print(f['/entry/instrument/beam/'].create_dataset(u'name', data='NSRRC BEAMLINE TPS 07A',dtype='a23'))
    try:
        
        # print(f['/entry/instrument/beam'].create_group(u'ATTENUATOR'))
        print(f['/entry/instrument/beam'].create_group(u'attenuator'))
        print(f['/entry/instrument/beam/attenuator'].create_dataset(u'attenuator_transmission', data=0.95))
        # print(f['entry/instrument/beam/'])
        # print(f['/entry/instrument/beam'].create_group(u'beamline'))
        # print(f['/entry/instrument/beam/beamline'].create_dataset(u'attenuator_transmission', data=213123))
        # mydata=b'NSRRC BEAMLINE TPS 07A'
        print(f['/entry/instrument/beam/'].create_dataset(u'name', data=b'NSRRC BEAMLINE TPS 07A'))
        #det.streamConfig('header_appendix')['value']
    except Exception as e:
        print(e)
        # print(f['/entry/definition'])
        # print(f['/entry/instrument/detector/sensor_material'])
        # print(f['/entry/instrument/beam/name'])
        
        pass
    # print(descend_obj(f))
# with h5py.File(file,'r') as f:
#     f[]
# with h5py.File('/home/blctl/Downloads/test2_0_0045_master.h5', 'r') as f:
    # for key in f.keys():
        
    #     print(key)
    #     print(f[key])
    #     for key2 in f[key].attrs.keys():
    #         print(f'--{key2}={f[key].attrs[key2]}')
    #     for key3 in f[key].keys():
    #         print(f[key][key3])
    # while True:
    #     for key in f.keys():
            
    
