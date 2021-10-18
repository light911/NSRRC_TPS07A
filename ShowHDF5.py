#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 12 16:35:29 2021

@author: blctl
"""

import h5py
import numpy as np
import argparse,sys



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


if __name__ == "__main__":
    
    # par = argparse.ArgumentParser()
    # par.add_argument("-folder",type=str,help="Raw data folder")
    # par.add_argument("-key",type=str,help="The string to  login bluice")
    # par.add_argument("-user",type=str,help="Current user name")
    # par.add_argument("-stra",type=str,help="The strategy for determine collect par.")
    # par.add_argument("-beamline",type=str,help="Beamline")
    # par.add_argument("-passwd",type=str,help="The string to  login bluice")
    # par.add_argument("-base64passwd",type=str,help="The string to  login bluice")
    # args=par.parse_args()
    path = sys.argv[1]
    h5dump(path)
