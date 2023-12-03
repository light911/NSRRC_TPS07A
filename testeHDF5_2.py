#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 30 09:05:21 2021

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
            # print(sep+'\t','-',key,':',obj.attrs[key])
            try:
                print(obj.asstr)
                h5py._hl.dataset.Dataset.
            except :
                pass
            data =[]
            # if obj.dtype == None:
                
            #     print(obj[0])
                
            if obj.shape == np.shape(1):
                # print('match this')
                data = obj[()]
                
            elif obj.shape == np.shape([0,0,0]):
                # data =[obj[[0]],obj[[1]],obj[[2]]]
                for i in range(3):
                    data.append(obj[i])
            elif obj.shape == np.shape([0,0]):
                for i in range(2):
                    data.append(obj[i])
            elif obj.shape == np.shape([0]):
                data = obj[0]
            else:
                data=None
            # data=obj[]
            
            print(sep+'\t','-',key,':','*',data,'*','(',obj.attrs[key],')')
        # for (name,value) in obj.attrs.items():
        
        #     print(sep+'\t','-',name,':',value)
    # return "a"

def h5dump(path,group='/'):
    """
    print HDF5 file metadata

    group: you can give a specific group, defaults to the root group
    """
    with h5py.File(path,'r') as f:
         descend_obj(f[group])

def read_hdf5(path):

    weights = {}

    keys = []
    with h5py.File(path, 'r') as f: # open file
        f.visit(keys.append) # append all keys to list
        for key in keys:
            if ':' in key: # contains data if ':' in key
                print(f[key].name)
                weights[f[key].name] = f[key].value
    return weights

# file="/home/blctl/Downloads/test2_0_0045_master.h5"
file="/home/blctl/Downloads/lys04_0_0005_master.h5"
h5dump(file)
# read_hdf5(file)