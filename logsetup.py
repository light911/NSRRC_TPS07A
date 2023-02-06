#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr  9 14:35:20 2021

@author: blctl
for colored log
https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
"""
import logging,time
from logging import handlers #this is need for tun in term
import coloredlogs
import psycopg
# from datetime import datetime
import datetime

def getloger(logname='Main',LOG_FILENAME='log.txt',level = 'INFO'):
    logger=logging.getLogger(logname)
    # fotmatterstr = '%(asctime)s - %(name)s - %(levelname)s -%(funcName)s - %(message)s'
    fotmatterstr = " %(asctime)s - %(name)s - %(levelname)s -%(funcName)s- %(message)s (%(filename)s:%(lineno)d)"
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



def getloger2(logname='Main',LOG_FILENAME='./log/log.txt',level = 'INFO',bypassdb=False):
    logger=logging.getLogger(logname)
    #fotmatterstr = '%(asctime)s - %(name)s - %(levelname)s -%(funcName)s - %(message)s'
    fotmatterstr = " %(asctime)s - %(name)s - %(levelname)s -%(funcName)s - %(message)s (%(filename)s:%(lineno)d)"
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
    else:
        loglevel = logging.INFO
    ch.setLevel(loglevel)
    ch.setFormatter(CustomFormatter())
    logger.setLevel(logging.DEBUG)
    logger.addHandler(filehandler)
    logger.addHandler(ch)

    if bypassdb:
        pass
    else:
        try:
            db_tbl_log='log'#Table name in DB
            from dbloginstr import loginstr
            #print(loginstr())
            conn = psycopg.connect(loginstr())
            log_cursor = conn.cursor()
            logdb = LogDBHandler(conn, log_cursor, db_tbl_log,loginstr())
            logger.addHandler(logdb)
            #print(logdb)
        except:
            pass

    
    
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
    
class LogDBHandler(logging.Handler):
    '''
    Customized logging handler that puts logs to the database.
    psycopg required
    '''
    def __init__(self, sql_conn, sql_cursor, db_tbl_log,loginstr=''):
        logging.Handler.__init__(self)
        self.sql_cursor = sql_cursor
        self.sql_conn = sql_conn
        self.db_tbl_log = db_tbl_log
        self.loginstr = loginstr
        self.sql_conn.autocommit = True

    def emit(self, record):
        # Set current time
        # tm = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.localtime(record.created))
        # tm = time.strftime("%Y-%m-%d %H:%M:%S.%f", time.localtime(record.created))
        tm = datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")
        # Clear the log message so it can be put to db via sql (escape quotes)
        self.log_msg = f'{record.msg}'
        if len(self.log_msg)>4990:
            self.log_msg = self.log_msg[:4990]
        self.log_msg = self.log_msg.strip()
        self.log_msg = self.log_msg.replace('\x00','')
        self.log_msg = self.log_msg.replace('\'','\'\'')
        # Make the SQL insert
        # sql = 'INSERT INTO ' + self.db_tbl_log + ' (log_level, ' + \
        #     'log_levelname, log, created_at, created_by) ' + \
        #     'VALUES (' + \
        #     ''   + str(record.levelno) + ', ' + \
        #     '\'' + str(record.levelno) + '\', ' + \
        #     '\'' + str(self.log_msg) + '\', ' + \
        #     '(convert(datetime2(7), \'' + tm + '\')), ' + \
        #     '\'' + str(record.name) + '\')'
        sql = f"INSERT INTO {self.db_tbl_log} (time,log_level,log_levelname,dhs ,function ,log ,file,line)\
            values (TIMESTAMP '{tm}',{record.levelno},'{record.levelname}','{record.name}','{record.funcName}',\'{self.log_msg}\','{record.filename}',{record.lineno});"
        try:
            self.sql_cursor.execute(sql)
            # self.sql_conn.commit()
        # If error - print it out on screen. Since DB is not working - there's
        # no point making a log about it to the database :)
        except psycopg.OperationalError as error :
            print(error.args)
            
            if error.args[0] == 'the connection is lost':
                try:
                    self.sql_conn = psycopg.connect(self.loginstr)
                    self.sql_cursor = self.sql_conn.cursor()
                    self.sql_cursor.execute(sql)
                except Exception as e:
                    print(f'{e}')
                    print('Reconnect to DB fail!')
        except Exception as e:
            print(f'{sql}')
            print(f'{e}')
            print('CRITICAL DB ERROR! Logging to database not possible!')


    
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
