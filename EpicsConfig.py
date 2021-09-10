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
                'PVname':'07a:md3:BeamstopDistance',
                'PVID':'',
                'GUIname':'MD3BS',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"beamstop_z",
                'dcsstype':"motor",
                 },
            'DetDistance':{
                'PVname':'07a:Det:Dis',
                'PVID':'',
                'GUIname':'DetDistance',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV','LLM'],
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
            'Phi':{
                'PVname':'07a:md3:Phi',
                'PVID':'',
                'GUIname':'Phi',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"gonio_omega",
                'dcsstype':"motor",
                 },
            'Kappa':{
                'PVname':'07a:md3:Kappa',
                'PVID':'',
                'GUIname':'Kappa',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"gonio_kappa",
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
            'Energy':{
                'PVname':'07a:DCM:Energy',
                'PVID':'',
                'GUIname':'Energy',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.0005,
                'dcssname':"energy",
                'dcsstype':"motor",
                 },
            'SampleZ':{
                'PVname':'07a:md3:AlignmentY',
                'PVID':'',
                'GUIname':'SampleZ',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"sample_z",
                'dcsstype':"motor",
                 },
            'AlignZ':{
                'PVname':'07a:md3:AlignmentZ',
                'PVID':'',
                'GUIname':'AlignZ',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"align_z",
                'dcsstype':"motor",
                 },
            'AlignX':{
                'PVname':'07a:md3:AlignmentX',
                'PVID':'',
                'GUIname':'AlignX',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"align_x",
                'dcsstype':"motor",
                 },
            'SampleX':{
                'PVname':'07a:md3:CentringX',
                'PVID':'',
                'GUIname':'SampleX',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"sample_y",
                'dcsstype':"motor",
                 },
            'SampleY':{
                'PVname':'07a:md3:CentringY',
                'PVID':'',
                'GUIname':'SampleY',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"sample_x",
                'dcsstype':"motor",
                 },
            'cam_horz':{
                'PVname':'07a:md3:CentringTableVertical',
                'PVID':'',
                'GUIname':'cam_horz',
                "old_value":"0",
                'callbackitems':['DMOV','VAL','RBV'],
                "deadband":0.001,
                'dcssname':"cam_horz",
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
                            'dcsstype':"",
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
              "07a:md3:BeamPositionVertical":{
                            "PVname":"07a:md3:BeamPositionVertical",  
                            "PVID":"",#for uid object
                            "GUIname":"beam_pos_y",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"beam_pos_y",
                            'dcsstype':"par",
                            },
              "07a:md3:BeamPositionHorizontal":{
                            "PVname":"07a:md3:BeamPositionHorizontal",  
                            "PVID":"",#for uid object
                            "GUIname":"beam_pos_x",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"beam_pos_x",
                            'dcsstype':"par",
                            },
              "07a:md3:CoaxCamScaleX":{
                            "PVname":"07a:md3:CoaxCamScaleX",  
                            "PVID":"",#for uid object
                            "GUIname":"zoom_scale_x",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"zoom_scale_x",
                            'dcsstype':"par",
                            },
              "07a:md3:CoaxCamScaleY":{
                            "PVname":"07a:md3:CoaxCamScaleY",  
                            "PVID":"",#for uid object
                            "GUIname":"zoom_scale_y",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"zoom_scale_y",
                            'dcsstype':"par",
                            },
              "07a:md3:KappaIsEnabled":{
                            "PVname":"07a:md3:KappaIsEnabled",  
                            "PVID":"",#for uid object
                            "GUIname":"KappaEnabled",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"KappaEnabled",
                            'dcsstype':"par",
                            },
              "07a:md3:CurrentPhase":{
                            "PVname":"07a:md3:CurrentPhase",  
                            "PVID":"",#for uid object
                            "GUIname":"change_mode",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"change_mode",
                            'dcsstype':"change_mode",
                            },
              "07a:md3:CoaxialCameraZoomValue":{
                            "PVname":"07a:md3:CoaxialCameraZoomValue",  
                            "PVID":"",#for uid object
                            "GUIname":"camera_zoom",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"camera_zoom",
                            'dcsstype':"quickmotor",
                            }, 
              "07a:md3:LastTaskInfo":{
                            "PVname":"07a:md3:LastTaskInfo",  
                            "PVID":"",#for uid object
                            "GUIname":"LastTaskInfo",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"",
                            'dcsstype':"log",
                            }, 
              "07a:md3:startRasterScanEx":{
                            "PVname":"07a:md3:startRasterScanEx",  
                            "PVID":"",#for uid object
                            "GUIname":"startRasterScanEx",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"",
                            'dcsstype':"opertation",
                            }, 
             "07a:md3:startRasterScan":{
                            "PVname":"07a:md3:startRasterScan",  
                            "PVID":"",#for uid object
                            "GUIname":"startRasterScan",
                            "old_value":"0",
                            "camon":True,
                            "deadband":0,
                            'dcssname':"",
                            'dcsstype':"opertation",
                            }, 
             }


