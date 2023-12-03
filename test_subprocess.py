#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 20 06:29:35 2021

@author: blctl
"""

import subprocess

def caput(PV,value):
    command = ['caput',str(PV),str(value)]
    ans = subprocess.run(command,capture_output=True)
    
   
    reslut = ans.stdout.decode('utf-8')
    error = ans.stderr.decode('utf-8')
    print(reslut)
    if error == '':
        print('ok')
    else:
        print(f'fail:{error}')
    print(ans)
if __name__ == "__main__":
    PV = '07a:md3:CurrentPhase'
    value = 0
    caput(PV,value)
    
    # PV = '07a:md3:Omega'
    # value = 180
    # caput(PV,value)
    
    
    # PV = '07a:md3:abort'
    # value = '__EMPTY__'
    # caput(PV,value)