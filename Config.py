#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 12 09:49:13 2021

@author: blctl
"""

Par={
    "Beamline":"TPS07A",
    "Debuglevel":"DEBUG",#ERROR,WARNING,INFO,DEBUG
    "MinDistance":400,
    "fakedistancename":"07a-ES:DetectorDistance",
    "calfactorname":'07a-ES:DetectorDistance:OFF',
    'dcss':{'host':"10.7.1.1",
            'port':14242,
            'dhsname':"EPICS",
            'tcptimeout':0.02},
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
                                    
                                 
                                    
                                    
                                 'using':{'MD3Ver':True,
                                          'MD3Hor':True,
                                          'SS':True,
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