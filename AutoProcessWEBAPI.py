#! /data/program/anaconda3_2/bin/python3
from flask import Flask,jsonify,request
from threading import Thread
from subprocess import Popen, PIPE, TimeoutExpired
from regex import E  
import requests,time,pathlib,re,h5py,os
app = Flask('AutoProcesswebServer')

Gdata = []#list for path,but start with None
ParData = []#list for ParData
@app.route('/', methods=['GET', 'POST'])
def welcome():
    return "Hello World!"
@app.route('/job', methods=['POST'])

def jobPOST():
    getdata = request.data #give you strig
    # print(request.data)
    # print('Header: ',request.headers)
    # if not Gdata:
    #     #fresh run, start job server
    #     Gdata = []
    #     p = Thread(target=runjob)
    #     p.start()

    if request.is_json:
        jsondata = request.get_json()
        filepath = jsondata['path']
        print(f'{jsondata=}\n{Gdata=}')
        #check if there has same path running?
        alreadRunning = False
        if len(Gdata)>=1:
            for item in Gdata:
                # if item['path'] == filepath:
                if item == filepath:
                    alreadRunning = True
        if alreadRunning:
            print('There has same path running!')
            for item in Gdata:
                print(f"path : {item}")
            ans = 'There has same path running!'
        else:
            Gdata.append(filepath)
            ParData.append(jsondata)
            ans = "OK,add job"
    else:
        
        print('not json')
        # print('Try covert data: ',request.get_json(True))
        ans = "Got : " + str(getdata)
    
    return ans

@app.route('/job', methods=['GET'])
def jobGET():
    ans = {}
    for i,a in enumerate(Gdata):
        ans[i]=a
        
    return  jsonify(ans)

def runjob():
    while True:
        if len(Gdata)>=1:
            t0=time.time()
            filepath = Gdata[0]
            par = ParData[0]
            command = []
            command.append('AutoProcess.py')
            ramfilepath=filepath.replace('/data','/mnt/proc_buffer')
            command.append(ramfilepath)

            
            file= pathlib.Path(ramfilepath)
            processfolder =  pathlib.Path(filepath).parent
            command.append('-processfolder')
            command.append(processfolder)
            #add this args in command
            args=['res','frame','i2s','symm','cell','indexframe']
            for arg in args:
                if arg in par:
                    command.append(f'-{arg}')
                    command.append(f'{par[arg]}')
            #arg for no par
            args=['noano']
            for arg in args:
                if arg in par:
                    command.append(f'-{arg}')
            print(f'Start to Process dateset : {filepath},the all datalist = {Gdata}')
            process = Popen(command, shell=False, stdin = PIPE, stdout = PIPE, stderr = PIPE)
            pid = process.pid
            # process.wait()
            logs, errs = process.communicate(timeout=600)
            print(f'End of Process dateset : {filepath}')
            # print(f'{logs.decode("utf-8")=},{errs.decode("utf-8")=}')

            print(f'log=\n{logs.decode("utf-8")}\nerr=\n{errs.decode("utf-8")=}')
            #done
            Gdata.pop(0)
            ParData.pop(0)
            
            processlog=f'{logs.decode("utf-8")}\n{errs.decode("utf-8")}'
            
            # good = process.stdout.readline()
            runtime=time.time() -t0
            print(f'Total Run time for {filepath} is {runtime}')
            # if good == b'False\n':
            #     print(f'Error for {filepath},{pid=},{runtime=}')
            #     processlog =process.stdout.readlines()
            #     print(processlog)
            # else:
            #     processlog =process.stdout.readlines()
            #     print(f'done for {filepath},{pid=},{runtime=}')
            # if process.returncode != 0:
            #     processlog=process.stderr.readlines()
            #     print(processlog)
            # else:
            #     pass
            #modify pathname in XDS.inp?
            #chmod right?
            # if 'processfolder' in par:
            
            with h5py.File(file,'r') as f:       
                filename = f['/entry/extrainfo']['filename'][()].decode("utf-8")
            processfolder = f"{processfolder}/_QuickProcess_{filename}_master"
            processlogPath=f'{processfolder}/processlog.txt'
            log=""
            try:
                # for item in processlog:
                #     log += item.decode("utf-8")
            
                with open(processlogPath,'w') as f:
                        f.write(processlog)
            except Exception as e:
                print(f'Error:{e}')
            try:
                xdsinppath = pathlib.Path(f"{processfolder}/XDS.INP")
                with open(xdsinppath,'r') as f:
                    xdsinp = f.read()
                xdsinp = re.sub("\/mnt\/proc_buffer","/data",xdsinp)

                with open(xdsinppath,'w') as f:
                    f.write(xdsinp)
            except Exception as e:
                print(f'Error:{e}')
            #remove raw data
            removerawdata(file,processfolder)
        else:   
            time.sleep(0.1)
def removerawdata(masterfile,processfolder):
    path = pathlib.Path(masterfile)
    removelist = []
    removelist.append(path)
    with h5py.File(path,'r') as f:
        # print(f['/entry/data/'].keys())
        filename = f['/entry/extrainfo']['filename'][()].decode("utf-8")
        uid = int(f['/entry/extrainfo']['uid'][()].decode("utf-8"))
        gid = int(f['/entry/extrainfo']['gid'][()].decode("utf-8"))
        print(filename)
        for key in f['/entry/data/'].keys():
            filepath = pathlib.Path(f"{path.parent}/{filename}_{key}.h5")
            removelist.append(filepath)
    try:
        for item in removelist:
            print(f'remove file : [{item}]')
            item.unlink(missing_ok=True)
    except Exception as e:
        print(f'Err:{e}')
    recursive_chown(processfolder,uid,gid)

def recursive_chown(path,uid,gid):
    for dirpath, dirnames, filenames in os.walk(path):
        os.chown(dirpath,uid,gid)
        for filename in filenames:
            try:
                os.chown(os.path.join(dirpath, filename),uid,gid)
                
                os.chmod(os.path.join(dirpath, filename), 0o700)
            except:
                pass
    # print(removelist)
if __name__ == '__main__':       
    # app.run(host='0.0.0.0', port=65000,threaded=False,processes=2)
    p = Thread(target=runjob)
    p.start()
    app.run(host='0.0.0.0', port=65001,threaded=True)
    # removerawdata('/mnt/proc_buffer/ins/ins01_lowdose4_d1440_4_0001_master.h5')