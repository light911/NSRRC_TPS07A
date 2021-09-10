#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 12 09:49:13 2021

@author: blctl
"""

Par={
    "Beamline":"TPS07A",
    "Debuglevel":"DEBUG",#ERROR,WARNING,INFO,DEBUG
    "MinDistance":149,
    "fakedistancename":"07a:Det:Dis",
    "calfactorname":'07a-ES:DetectorDistance:OFF',
    "minchangeGAP":0.006,#mm
    "minEVchangeGAP":0.01,#Kev
    'dcss':{'host':"10.7.1.1",
            'port':14242,
            'dhsname':"EPICS",
            'tcptimeout':0.1},
    'Energy':{'gapname':'SR-ID-IU22-07:getGap',
              'cvtE2Gapname':'07a:IU22:cvtE2Gap.VAL',
              'pre_convert_energy':'07a:IU22:cvtE2Gap.X',
              'evtogap':'07a:IU22:cvtE2Gap_able',
              },
    'Detector':{'ip':"10.7.1.98",
                'ip2':"192.168.31.98",
                'port':80,
                'nimages':0,
                'Filename':"Filename",
                'Fileindex':0,
                'nimages_per_file':1000,
                },
    'collect':{'start_oscillationPV':'07a:md3:startScanEx',
               'md3statePV':'07a:md3:State',
               'saveCentringPositionsPV':'07a:md3:saveCentringPositions',
               'LastTaskInfoPV':'07a:md3:LastTaskInfo',
               'NumberOfFramesPV':'07a:md3:ScanNumberOfFrames',
               'EnergyPV':'07a:DCM:Energy',
               'dethorPV':'07a:Det:Hor',
               'detverPV':'07a:Det:Ver'
               },
    'EPICS_special':{'BeamSize':{'BeamSizeName':'07a-ES:Table:Beamsize',
                                 'MD3YName':'07a-ES:Table:MD3Y',
                                 'MD3VerName':'07a-ES:Table:MD3Ver',
                                 'MD3HorName':'07a-ES:Table:MD3Hor',
                                 'Slit4VerOPName':'07a-ES:Table:Slit4VerOP',
                                 'Slit4HorOPName':'07a-ES:Table:Slit4HorOP',
                                 'DBPM5VerName':'07a-ES:Table:DBPM5Y',
                                 'DBPM5HorName':'07a-ES:Table:DBPM5X',
                                 'DBPM6VerName':'07a-ES:Table:DBPM6Y',
                                 'DBPM6HorName':'07a-ES:Table:DBPM6X',
                                 'SSName':'07a-ES:Table:2ndslit',
                                 'ApertureName':'07a-ES:Table:MD3Aperture',
                                 
                                 'MD3YMotor':'07a:MD3:Y',
                                 'MD3VerMotor':'07a:MD3:Ver',
                                 'MD3HorMotor':'07a:MD3:Hor',
                                 'Slit4VerOPMotor':'07a:Slits4:ZOpening',
                                 'Slit4HorOPMotor':'07a:Slits4:XOpening',
                                 'DBPM5VerMotor':'07a:DBPM5:Z',
                                 'DBPM5HorMotor':'07a:DBPM5:X',
                                 'DBPM6VerMotor':'07a:DBPM6:Z',
                                 'DBPM6HorMotor':'07a:DBPM6:X',
                                 'SSMotor':'07a:Slits3:XOpening',
                                 'DetYMotor':'07a:Det:Y',
                                 'ApertureMotor':'07a:md3:CurrentApertureDiameterIndex',
                                 
                                 'ApertureStatelist':['07a:md3:ApertureHorizontalState','07a:md3:ApertureVerticalState'],   
                                    
                                 'using':{'MD3Ver':True,
                                          'MD3Hor':True,
                                          'SS':True,
                                          'Aperture':False,
                                          'Slit4VerOP':False,
                                          'Slit4HorOP':False,
                                          'DBPM5Ver':False,
                                          'DBPM5Hor':False,
                                          'DBPM6Ver':False,
                                          'DBPM6Hor':False,
                                          },
                                 
                    },
            },
    }