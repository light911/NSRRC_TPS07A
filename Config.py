#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 12 09:49:13 2021

@author: blctl
"""

Par={
    "Beamline":"TPS07A",
    "Debuglevel":"DEBUG",#ERROR,WARNING,INFO,DEBUG
    "MinDistance":139,
    "fakedistancename":"07a:Det:Dis",
    "calfactorname":'07a-ES:DetectorDistance:OFF',
    "minchangeGAP":0.006,#mm
    "minEVchangeGAP":0.01,#Kev
    "bypasscover":False,#False 
    "robot":{'host':"10.7.1.3",
             'commandprot':10001,
             #sec. bound for the cryojet relay round trip (see askCryojetIn).
             #normal reply is ~30 ms; without a bound a dead relay hangs collect.
             'timeout':5
            },
    "CVLS":{'host':"10.7.1.111",#SCHOTT ColdVision Light Source
             'commandprot':50811,
             #bluice sends back light intensity as 0-100%, which maps linearly
             #onto 0-max_power raw channel power. The hardware accepts up to
             #1000 but the beamline runs the light around 30-50, so a low
             #ceiling keeps the whole slider travel usable. Raise it if samples
             #need more light.
             'max_power':100,
             #auto center matches the sample against a background reference
             #image taken under white light at a fixed brightness, so centerLoop
             #forces this intensity (0-100%) before it runs and refuses to run
             #under any colour but white. Retune this only when the background
             #image calibration is redone at a different level.
             'autocenter_intensity':30,
             #the MD3 front light is white. Asking for a colour other than white
             #means a dark room experiment lit by something that will not excite
             #the sample, and a white front light would defeat that, so the front
             #light follows the back light: on for white, off for every other
             #colour. Set to '' on a beamline that has no such PV to skip it.
             'frontlight_pv':'07a:md3:FrontLightFactor'
            },
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
                'ip2':"10.7.3.98",#remove 192.168.31.98
                'port':80,
                'nimages':0,
                'Filename':"Filename",
                'Fileindex':0,
                'nimages_per_file':1000,
                'timeout':60#this should longer than prepare md3 sync detector
                },
    'collect':{'start_oscillationPV':'07a:md3:startScanEx',
               'md3statePV':'07a:md3:State',
               'saveCentringPositionsPV':'07a:md3:saveCentringPositions',
               'LastTaskInfoPV':'07a:md3:LastTaskInfo',
               'NumberOfFramesPV':'07a:md3:ScanNumberOfFrames',
               'EnergyPV':'07a:DCM:Energy',
               'dethorPV':'07a:Det:Hor',
               'detverPV':'07a:Det:Ver',
               'EbeamPV':'SR-DI-DCCT:BeamCurrent',
               'gapPV':'SR-ID-IU22-07:getGap',
               'DBPM1PV':'07a-ES:DBPM1:Flux',
               'DBPM2PV':'07a-ES:DBPM2:Flux',
               'DBPM3PV':'07a-ES:DBPM3:Flux',
               'DBPM5PV':'07a-ES:DBPM5:Flux',
               'DBPM6PV':'07a-ES:DBPM6:Flux',
               'samplefluxPV':'07a-ES:Sample:Flux',
               'DBPM1ssPV':'07a-ES:DBPM1sum:Stability',
               'DBPM2ssPV':'07a-ES:DBPM2sum:Stability',
               'DBPM3ssPV':'07a-ES:DBPM3sum:Stability',
               'DBPM5ssPV':'07a-ES:DBPM5sum:Stability',
               'DBPM6ssPV':'07a-ES:DBPM6sum:Stability',
               'chiPV':'07a:md3:ChiPosition',
               'phiPV':'07a:md3:PhiPosition',
               'kappaPV':'07a:md3:KappaPosition',
               'md3modePV':'07a:md3:CurrentPhase',
               'TimeToNextInjPV':'TPS:TimeToNextInjSec',
               'safeTimeInj':3,# 0 for inactive , neg for want to hit injection,pos for not hit injection
               'post_tri_timePV':'07a-ES:timing:post_tri_time',
               'shutter_delayPV':'07a:beamline:timing:delay:shutter',
               'detector_delayPV':'07a:beamline:timing:delay:detector',
               'SSXtriggerPV':'07a:beamline:timing:trigger',
               'SSXtrigerwidthPV':'07a:beamline:timing:trigger:width',
               'laser_init_statePV':'07a:beamline:timing:laser:initial_state',
               'laser_timing_arrayPV':'07a:beamline:timing:laser:pulse_timing',
               'last_detector_countPV':'07a:beamline:timing:info:last_detector_count',
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
                                 'DBPM6kxName':'07a-ES:Table:DBPM6kx',
                                 'DBPM6kyName':'07a-ES:Table:DBPM6ky',
                                 'SSName':'07a-ES:Table:2ndslit',
                                 'ApertureName':'07a-ES:Table:MD3Aperture',
                                 'CurrentBeamsize':'07a-ES:Beamsize',
                                 'SampleFluxlist':'07a-ES:Table:SampleFluxlist',
                                 'Energyatrecord':'07a-ES:Table:Energy',
                                 'Ebeamatrecord':'07a-ES:Table:Ebeam',
                                 'MD3YMotor':'07a:MD3:Y',
                                 'MD3VerMotor':'07a:MD3:Ver',
                                 'MD3HorMotor':'07a:MD3:Hor',
                                 'Slit4VerOPMotor':'07a:Slits4:ZOpening',
                                 'Slit4HorOPMotor':'07a:Slits4:XOpening',
                                 'DBPM5VerMotor':'07a:DBPM5:Z',
                                 'DBPM5HorMotor':'07a:DBPM5:X',
                                 'DBPM6VerMotor':'07a:DBPM6:Z',
                                 'DBPM6HorMotor':'07a:DBPM6:X',
                                 'DBPM6kxfactor':'07A-DBPM6:dsp:kx',
                                 'DBPM6kyfactor':'07A-DBPM6:dsp:ky',
                                 'BeamSizeX': '07a-ES:Table:BeamsizeX',
                                 'BeamSizeY': '07a-ES:Table:BeamsizeY',
                                 'SSMotor':'07a:2ndSlits:XOpening',
                                 'DetYMotor':'07a:Det:Y',
                                 'ApertureMotor':'07a:md3:CurrentApertureDiameterIndex',
                                 
                                 'ApertureStatelist':['07a:md3:ApertureHorizontalState','07a:md3:ApertureVerticalState'],   
                                    
                                 'using':{'MD3Ver':True,
                                          'MD3Hor':True,
                                          'SS':True,
                                          'Aperture':True,
                                          'Slit4VerOP':False,
                                          'Slit4HorOP':False,
                                          'DBPM5Ver':True,
                                          'DBPM5Hor':False,
                                          'DBPM6Ver':False,
                                          'DBPM6Hor':False,
                                          },
                                 
                    },
            },
    }
