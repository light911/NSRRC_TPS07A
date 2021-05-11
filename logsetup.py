#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  9 14:35:20 2021

@author: blctl
for colored log
https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
"""
import logging
from logging import handlers #this is need for tun in term
import coloredlogs

def getloger(logname='Main',LOG_FILENAME='log.txt',level = 'INFO'):
    logger=logging.getLogger(logname)
    fotmatterstr = '%(asctime)s - %(name)s - %(levelname)s -%(funcName)s - %(message)s'
    formatter = logging.Formatter(fotmatterstr)
    # logging.basicConfig(stream=sys.stdout, level=logging.INFO,format = fotmatterstr)
    # logging.basicConfig(level=logging.DEBUG,format = fotmatterstr)
    
    filehandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=20000000, backupCount=10)
    filehandler.setFormatter(formatter)
    
    
    filehandler.setLevel(logging.DEBUG)
    
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    if level == "INFO":
        loglevel = logging.INFO
    elif level == "DEBUG":
        loglevel = logging.DEBUG
    elif level == "ERROR":
        loglevel = logging.ERROR
    elif level == "WARNING":
        loglevel = logging.WARNING        
    else:
        loglevel = logging.INFO
    ch.setLevel(loglevel)
    ch.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(filehandler)
    logger.addHandler(ch)
    coloredlogs.install(fmt=fotmatterstr,level=logging.INFO,logger=logger)
    return logger



def getloger2(logname='Main',LOG_FILENAME='log.txt',level = 'INFO'):
    logger=logging.getLogger(logname)
    fotmatterstr = '%(asctime)s - %(name)s - %(levelname)s -%(funcName)s - %(message)s'
    formatter = logging.Formatter(fotmatterstr)
    # logging.basicConfig(stream=sys.stdout, level=logging.INFO,format = fotmatterstr)
    # logging.basicConfig(level=logging.DEBUG,format = fotmatterstr)
    
    filehandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=200000, backupCount=10)
    filehandler.setFormatter(formatter)
    
    
    filehandler.setLevel(logging.DEBUG)
    
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    
    if level == "INFO":
        loglevel = logging.INFO
    elif level == "DEBUG":
        loglevel = logging.DEBUG
    elif level == "ERROR":
        loglevel = logging.ERROR
    else:
        loglevel = logging.INFO
    ch.setLevel(loglevel)
    ch.setFormatter(CustomFormatter())
    logger.setLevel(logging.DEBUG)
    logger.addHandler(filehandler)
    logger.addHandler(ch)
    # coloredlogs.install(fmt=fotmatterstr,level=logging.INFO,logger=logger)
    return logger


class CustomFormatter(logging.Formatter):
    
    def setcolor(Format,text,color):
        reset = "\x1b[0m"
        reformat =Format.replace(text,color + text + reset)
        
        return reformat
        
    
    
    """Logging Formatter to add colors and count warning / errors"""

    grey = "\x1b[38;21m"
    lightgray ="\x1b[1;30m"
    # yellow = "\x1b[33;21m"
    yellow = "\x1b[33m"
    # red = "\x1b[31;21m"
    red = "\x1b[1;31m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32m"
    darkblue="\x1b[34m"
    reset = "\x1b[0m"
    format = " %(asctime)s - %(name)s - %(levelname)s -%(funcName)s- %(message)s (%(filename)s:%(lineno)d)"
    format = setcolor(format,'%(asctime)s',green)
    format = setcolor(format,'%(name)s',darkblue)
    debugformat = setcolor(format,'%(levelname)s',lightgray)
    debugformat = setcolor(debugformat,'%(message)s',lightgray)
    
    infoformat = setcolor(format,'%(levelname)s',grey)
    infoformat = setcolor(infoformat,'%(message)s',grey)
    
    
    waringformat = setcolor(format,'%(levelname)s',yellow)
    waringformat = setcolor(waringformat,'%(message)s',yellow)
    
    errorformat = setcolor(format,'%(levelname)s',red)
    errorformat = setcolor(errorformat,'%(message)s',red)
    
    CRITICALformat = setcolor(format,'%(levelname)s',bold_red)
    CRITICALformat = setcolor(CRITICALformat,'%(message)s',bold_red)
    # debugformat = green + "%(asctime)s" + reset + " - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    
    
    FORMATS = {
        logging.DEBUG: debugformat,
        logging.INFO: infoformat,
        logging.WARNING: waringformat,
        logging.ERROR: errorformat,
        logging.CRITICAL: CRITICALformat
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
    

    
if __name__ == "__main__":
    # fh,ch=logsetup()
    # logger = logging.getLogger('Main2')
    # logsetup(logger)
    # logger.setLevel(logging.DEBUG)
    # print(logger.hasHandlers())
    # logger.addHandler(fh)
    logger = getloger('Main2')
    
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    
    # create logger with 'spam_application'
    logger2 = getloger2('Main3')
    logger2.setLevel(logging.DEBUG)
    
    # create console handler with
    logger2.debug("debug message")
    logger2.info("info message")
    logger2.warning("warning message")
    logger2.error("error message")
    logger2.critical("critical message")