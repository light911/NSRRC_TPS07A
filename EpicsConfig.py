# -*- coding: utf-8 -*-
"""
Created on Wed Dec 25 16:52:28 2019

@author: admin
"""

epicsmotors={
            'MD3Y':{
                'PVname':'07a:MD3:Y',
                'PVID':'',
                'GUIname':'MD3Y',
                "old_value":"0",
                'callbackitems':['DMOV','VAL'],
                "deadband":0.001,
                'dcssname':"",
                'dcsstype':""
                },
            'DetY':{
                'PVname':'07a:Det:Y',
                'PVID':'',
                'GUIname':'DetY',
                "old_value":"0",
                'callbackitems':['DMOV','VAL'],
                "deadband":0.001,
                'dcssname':"",
                'dcsstype':"",
                 },
            'MD3BS':{
                'PVname':'07a:md3:BeamstopX',
                'PVID':'',
                'GUIname':'MD3BS',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"",
                'dcsstype':"motor",
                 },
            'DetDistance':{
                'PVname':'07a:Det:Dis',
                'PVID':'',
                'GUIname':'DetDistance',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"detector_z",
                'dcsstype':"motor"
                 },
            'Omega':{
                'PVname':'07a:md3:Omega',
                'PVID':'',
                'GUIname':'Omega',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"gonio_phi",
                'dcsstype':"motor",
                 },
            'DetVer':{
                'PVname':'07a:Det:Ver',
                'PVID':'',
                'GUIname':'DetVer',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"detector_vert",
                'dcsstype':"motor",
                 },
            'DetHor':{
                'PVname':'07a:Det:Hor',
                'PVID':'',
                'GUIname':'DetHor',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"detector_horz",
                'dcsstype':"motor",
                 },

            }


epicslist={
              "07a-ES:Beamsize":{
                            "PVname":"07a-ES:Beamsize",  
                            "PVID":"",#for uid object
                            "GUIname":"Beamsize",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"",
                            'dcsstype':"motor",
                            },
              "07a:md3:FastShutterIsOpen":{
                            "PVname":"07a:md3:FastShutterIsOpen",  
                            "PVID":"",#for uid object
                            "GUIname":"shutter",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"shutter",
                            'dcsstype':"shutter",
                            },
             }


