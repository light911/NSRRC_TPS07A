#! /data/program/dials-v3-9-1/build/bin/python
##! /data/program/anaconda3_2/bin/python3
 

import pathlib,json
from pydoc import resolve
import numpy as np
import os,time,re,signal,argparse,pathlib,sys,math,shutil
from subprocess import Popen, PIPE, TimeoutExpired 
from yamtbx import util
from yamtbx.dataproc.pointless import Pointless as pp
from yamtbx.dataproc.xds.command_line.xds2mtz import xds2mtz
from yamtbx.util import xtal
from cctbx import crystal
class BaseFunction():
    def __init__(self) -> None:
        self.processfolder = pathlib.Path()#now directory = processfolder
        pass
    def savetojson(self,path=None):
        
        self.dictinfo={}
        infoitem = [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith("__")]
        for item in infoitem:
            # print(f'{item} : {type(getattr(self,item))}')
            if getattr(self,item) is self.dictinfo:
                pass
            elif type(getattr(self,item)) is str:
                self.dictinfo[item] = getattr(self,item)
                # print('str')
            elif type(getattr(self,item)) is int:
                self.dictinfo[item] = getattr(self,item)
                # print('int')
            elif type(getattr(self,item)) is float:
                self.dictinfo[item] = getattr(self,item)
                # print('float')
            elif type(getattr(self,item)) is type(True):
                self.dictinfo[item] = getattr(self,item)
                # print('Boolen')
            elif type(getattr(self,item)) is type(None):
                self.dictinfo[item] = getattr(self,item)
                # print('NONE')
            elif type(getattr(self,item)) is list:
                self.dictinfo[item] = getattr(self,item)
                # print('list')
            elif type(getattr(self,item)) is tuple:
                self.dictinfo[item] = getattr(self,item)
                # print('tuple')
            elif type(getattr(self,item)) is dict:
                self.dictinfo[item] = getattr(self,item)
                # print('dict')
            elif isinstance(getattr(self,item), pathlib.Path):
                self.dictinfo[item] = str(getattr(self,item))
            elif isinstance(getattr(self,item),np.int64) or \
                isinstance(getattr(self,item),np.int32) or \
                isinstance(getattr(self,item),np.int8):
                self.dictinfo[item] = int(getattr(self,item))    
            elif isinstance(getattr(self,item),np.float64) or \
                isinstance(getattr(self,item),np.float32) or \
                isinstance(getattr(self,item),np.float16) :
                self.dictinfo[item] = float(getattr(self,item))
            else:
                # print('nomatch')
                pass
        if path:
            with open(path, 'w') as f:
                # txt = json.dumps(self.dictinfo, indent = 4)
                # f.write(txt)
                json.dump(self.dictinfo,f, indent = 4)
        else:
            print(json.dumps(self.dictinfo, indent = 4))
        

        pass
class Pointless(BaseFunction):
    def __init__(self) -> None:
        super().__init__()
        self.XDSIN = None
        self.datapath = pathlib.Path()
        self.highres = None#5
        self.lowres = None#10
        self.inpfilename = 'pointless.inp'
        self.debug = True
        self.command = ''
    def geninp(self):
        self.t0 = time.time()
        
        Pointlessinp =""
        if self.processfolder.exists():
            pass
        else:
            self.processfolder.mkdir(mode=0o777,exist_ok=True,parents=True)
        self.inppath = pathlib.Path(f"{self.processfolder}/{self.inpfilename}")
        if self.XDSIN:
            Pointlessinp += f"XDSIN {self.XDSIN}"
            self.command += f"XDSIN {self.XDSIN}"
        if self.highres:
            Pointlessinp += f"\nRESOLUTION HIGH {self.highres}"
            self.command += f'\nRESOLUTION HIGH {self.highres}'
        if self.lowres:
            Pointlessinp += f"\nRESOLUTION LOW {self.lowres}"
            self.command += f'\nRESOLUTION HIGH {self.lowres}'
        # print(Pointlessinp,self.inppath,)
        with open(self.inppath,'w') as f:
             f.write(Pointlessinp)
    def run(self):
        # f = open(self.inppath,'w')
        command=['pointless']
        my_env = os.environ.copy()
        exitcode, output, err = util.call('pointless',stdin=self.command, wdir=self.processfolder)
        print(exitcode, output, err )
        # process = Popen(command, shell=False, stdin = PIPE, stdout = PIPE, stderr = PIPE,cwd=self.processfolder,env=my_env)
        # process = Popen(command, shell=False, stdin = self.command, stdout = PIPE, stderr = PIPE,cwd=self.processfolder,env=my_env)
        # while True:
        #     time.sleep(0.1)
        #     for line in iter(process.stdout.readline, b''):
        #         if self.debug:
        #             print(line.decode("utf-8"),end='')
        #         # self.readoutput(line.decode("utf-8"))
        #         # if "!!! ERROR !!! INSUFFICIENT PERCENTAGE (< 50%) OF INDEXED REFLECTIONS" in line.decode("utf-8"):
        #         #     self.indexfail = True
                    

                    
        #     if process.poll()==0:
        #         print(f"closed normal,take {time.time()-self.t0}")
                
        #         break
        #     elif process.poll()==1:
        #         processlogerr=process.stderr.readlines()
        #         log =""
        #         for item in processlogerr:
        #             log += item.decode("utf-8")
        #         print(f'{log}')
        #         print(f"bad,take {time.time()-self.t0}")
        #         break
        #     else:
        #         pass
class QuickXDS(BaseFunction):
    def __init__(self) -> None:
        super().__init__()
        self.datapath =  pathlib.Path()
        self.res = None
        self.imagetoindex = None
        self.imagetoprocess= None
        self.ano = True
        self.symm = None
        self.cell = None
        self.processState = None
        self.errormsg = ''
        self.runtime = -1
        self.msg_empty = True
        self.strategy = {}
        self.logout = None
        self.debug = False
        self.snippets = {}
        self.error_table = {}
        self.table = {}
        self.result = {}
        self.indexfail = False
        pass
    def genscript(self,bypassindex=False):
        self.t0 = time.time()
        if self.processfolder.exists():
            pass
        else:
            self.processfolder.mkdir(mode=0o777,exist_ok=True,parents=True)
        os.chdir(self.processfolder)
        # print(f"{self.datapath}")
        # command=['generate_XDS.INP',self.datapath]
        my_env = os.environ.copy()
        my_env["PATH"] = "/data/program/hdf5/bin/:" + my_env["PATH"]#using pyenv has problem h5dump seem not work?
        # print(f'{my_env}')
        # print(shutil.which("h5dump"))
        command=['/data/program/XDStools/generate_XDS.INP',self.datapath]
        process = Popen(command, shell=False, stdin = PIPE, stdout = PIPE, stderr = PIPE,cwd=self.processfolder,env=my_env)
        # command=f"/bin/bash -x generate_XDS.INP {self.datapath}"
        # process = Popen(command, shell=True, stdin = PIPE, stdout = PIPE, stderr = PIPE,cwd=self.processfolder)
        state = process.wait()
        print(f'done for XDS.inp with state: {state}')
        # print(f'{process.returncode}')
        # print(process.stdout.readlines())
        if process.returncode != 0:
            print(process.stdout.readlines())
            # print(process.stderr.readlines())#this id empty for this scrpit
            self.xdsinppath = None
            return 1
        else:
            print(process.stdout.readlines())
            self.xdsinppath = self.processfolder / 'XDS.INP'
        # print(self.processfolder)
        # print(self.xdsinppath)
        # time.sleep(0.5)#wait for file?
        with open(self.xdsinppath,'r') as f:
            xdsinp = f.read()
        #modify txt
        if not self.ano:
            print("change FRIEDEL'S_LAW=True")
            xdsinp = re.sub("FRIEDEL'S_LAW=FALSE","FRIEDEL'S_LAW=TRUE",xdsinp)
        if self.symm and self.cell:
            
            xdsinp = re.sub("SPACE_GROUP_NUMBER=0",f"SPACE_GROUP_NUMBER={self.symm}",xdsinp)
            xdsinp = re.sub("UNIT_CELL_CONSTANTS= 70 80 90 90 90 90",f"UNIT_CELL_CONSTANTS={self.cell}",xdsinp)
        if self.imagetoindex:
            xdsinp = re.sub("SPOT_RANGE=(.*)",f"SPOT_RANGE=1 {self.imagetoindex}",xdsinp)
        if self.imagetoprocess:
            xdsinp = re.sub("DATA_RANGE=(.*)",f"DATA_RANGE=1 {self.imagetoprocess}",xdsinp)
        else:
            ans = re.search("DATA_RANGE=1 (.*)",xdsinp)
            # print(ans)
            self.imagetoprocess = int(ans[1])
            
            # sys.exit()

        if self.res:
            xdsinp = re.sub("INCLUDE_RESOLUTION_RANGE=50 0",f"INCLUDE_RESOLUTION_RANGE=50 {self.res}",xdsinp)
        if bypassindex:
            xdsinp = re.sub("\nJOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT",f"\n!JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nJOB= DEFPIX INTEGRATE CORRECT",xdsinp)
        with open(self.xdsinppath,'w') as f:
             f.write(xdsinp)
        print(f'done for update XDS.INP,take {time.time()-self.t0}')
    def run(self,backup=True):
        self.jsonlogpath = self.processfolder / 'xds.json'
        os.chdir(self.processfolder)
        
        command=['xds_par']
        process = Popen(command, shell=False, stdin = PIPE, stdout = PIPE, stderr = PIPE,cwd=self.processfolder)
        print(process.poll())
        while True:
            print(process.poll())

            time.sleep(0.1)
            for line in iter(process.stdout.readline, b''):
                if self.debug:
                    print(line.decode("utf-8"),end='')
                self.readoutput(line.decode("utf-8"))
                if "!!! ERROR !!! INSUFFICIENT PERCENTAGE (< 50%) OF INDEXED REFLECTIONS" in line.decode("utf-8"):
                    self.indexfail = True
                    if self.errormsg == '':
                        self.errormsg = 'INSUFFICIENT PERCENTAGE (< 50%) OF INDEXED REFLECTIONS!\nIt may result from one or more additional crystals contributing to the diffraction patterns\nHowever, we still try to process it'
                    else:
                        self.errormsg += '\nINSUFFICIENT PERCENTAGE (< 50%) OF INDEXED REFLECTIONS!\nIt may result from one or more additional crystals contributing to the diffraction patterns\n However, we still try to process it'

                    
            if process.poll()==0:
                print(f"closed normal,take {time.time()-self.t0}")
                self.processState = 0
                self.savetojson(self.jsonlogpath)
                break
            elif process.poll()==1:
                processlogerr=process.stderr.readlines()
                log =""
                for item in processlogerr:
                    log += item.decode("utf-8")
                print(f'{log}')
                self.errormsg += f'\n{log}'
                print(f"bad,take {time.time()-self.t0}")
                self.processState = 1
                self.savetojson(self.jsonlogpath)
                break
            else:
                pass
        if self.indexfail:
            self.genscript(bypassindex = True)
            self.indexfail = False
            self.run()
        else:
            self.readCORRECT(backup)
    
    def readoutput(self,msg):
        ans = re.search('SPACE GROUP NUMBER(.*)',msg)
        if ans:
            self.process_SGn=int(ans.group(1))
            self.process_SG = self.get_SG(self.process_SGn)
            print(f'Space Group = {self.process_SG}')
            self.savetojson(self.jsonlogpath)

        ans = re.search('UNIT CELL PARAMETERS(.*)',msg)
        if ans:
            self.process_CELL=ans.group(1).split()
            print(f'UNIT CELL = {self.process_CELL}')
            self.savetojson(self.jsonlogpath)
        
        ans = re.search('SPACE_GROUP_NUMBER=(.[ 0-9]*)',msg)
        if ans:
            self.process_SGn=int(ans.group(1))
            self.process_SG = self.get_SG(self.process_SGn)
            print(f'Space Group = {self.process_SG}')
            self.savetojson(self.jsonlogpath)
            # print(msg)

        ans = re.search('UNIT_CELL_CONSTANTS=(.[0-9 .]*)',msg)
        if ans:
            self.process_CELL=ans.group(1).split()
            print(f'UNIT CELL = {self.process_CELL}')
            self.savetojson(self.jsonlogpath)
            # print(msg)

        ans = re.search("\*\*\*\*\* (.*) \*\*\*\*\*",msg)
        if ans:
            if len(ans.group(1)) < 10:
                self.RunState = ans.group(1)
                print(f'Run state = {self.RunState}')
                self.savetojson(self.jsonlogpath)

        ans = re.search("PROCESSING OF IMAGES(.*)\.\.\.(.*)",msg)
        if ans:
            self.RunImage = ans.group(2)
            print(f'Current image = {self.RunImage}')
            self.savetojson(self.jsonlogpath)
        ans = re.search("INSUFFICIENT PERCENTAGE \(< 50%\) OF INDEXED REFLECTIONS",msg)
        if ans:
            print('INSUFFICIENT PERCENTAGE (< 50%) OF INDEXED REFLECTIONS')
            
    def readCORRECT(self,backup:False=False):
        self.error_table = {}
        self.table = {}
        if backup:
            file = self.processfolder/'CORRECT.LP'
            if file.exists():
                shutil.copyfile(self.processfolder/'CORRECT.LP',self.processfolder/'CORRECT.fullres')
            else:
                if self.errormsg =='':
                    add = ''
                else:
                    add = '\n'
                self.errormsg += f'{add}Unable find CORRECT.LP file, maybe has problem on previous step'
                return
        # print(self.processfolder/'CORRECT.LP')
        with open(self.processfolder/'CORRECT.LP','r') as f:
            # print(self.processfolder/'CORRECT.LP')
            lines = f.readlines()
            reading = ""
            for i,l in enumerate(lines):
                # print(l)
                # if reading == "":
                #     pass
                # else:
                #     print(reading)
                if l.startswith(" FRIEDEL'S_LAW="):
                    self.anomalous_flag = "FALSE" in l
                elif "SELECTED SPACE GROUP AND UNIT CELL FOR THIS DATA SET" in l:
                    reading = "selected_symmetry"
                elif reading == "selected_symmetry":
                    reading = ""
                    pass
                elif  "CRYSTAL MOSAICITY (DEGREES)" in l:
                    # print(l.split()[-1])
                    self.process_MOS = float(l.split()[-1])
                elif "a        b          ISa" in l:
                    reading = "ISa"
                    self.snippets["ISa"] = l
                elif reading == "ISa":
                    a, b, ISa = map(float, l.split())
                    reading = ""
                    self.a_b_ISa = a, b, ISa
                    self.snippets["ISa"] += l
                elif "RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR  NUMBER ACCEPTED REJECTED" in l:
                    reading = "error_table"
                elif reading == "error_table":
                    if l.startswith(" ***"):
                        reading = ""
                        continue
                    if len(l.split()) < 3: continue
                    
                    sp = self.errortable_split(l)
                    # print(sp[0])
                    # Note that the last line is about overall data
                    self.error_table.setdefault("dmax", []).append(float(sp[0]))
                    self.error_table.setdefault("dmin", []).append(float(sp[1]))
                    self.error_table.setdefault("ios", []).append(self.safe_float(sp[2]))
                    self.error_table.setdefault("chisq", []).append(self.safe_float(sp[3]))
                    self.error_table.setdefault("r_merge", []).append(self.safe_float(sp[4]))
                    self.error_table.setdefault("number", []).append(int(sp[6]))
                    self.error_table.setdefault("nacc", []).append(int(sp[7]))
                    self.error_table.setdefault("nrej", []).append(int(sp[8]))
                elif 'STATISTICS OF SAVED DATA SET "XDS_ASCII.HKL"' in l:
                    reading = "stats_all"
                    continue
                elif "SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION" in l:
                    self.snippets["table1"] = l
                    if reading == "stats_all":
                        key = "all"
                        self.table[key] = {}
                        for ll in lines[i+1:i+4]: self.snippets["table1"] += ll
                        for ll in lines[i+4:i+4+10]:
                            self.snippets["table1"] += ll
                            sp = self.table_split(ll)
                            assert len(sp) == 14
                            self.table[key].setdefault("dmin", []).append(float(sp[0]) if sp[0]!="total" else None)
                            self.table[key].setdefault("redundancy", []).append(float(sp[1])/float(sp[2]) if float(sp[2]) > 0 else 0)
                            # self.table[key].setdefault("cmpl", []).append(float(sp[4][:-1]))
                            self.table[key].setdefault("cmpl", []).append(float(sp[4]))
                            # self.table[key].setdefault("r_merge", []).append(float(sp[5][:-1]))
                            self.table[key].setdefault("r_merge", []).append(float(sp[5]))
                            self.table[key].setdefault("i_over_sigma", []).append(float(sp[8]))
                            # self.table[key].setdefault("r_meas", []).append(self.safe_float(sp[9][:-1]))
                            self.table[key].setdefault("r_meas", []).append(self.safe_float(sp[9]))
                            self.table[key].setdefault("cc_half", []).append(float(sp[10].replace("*","")))
                            self.table[key].setdefault("cc_ano", []).append(float(sp[11].replace("*","")))
                            self.table[key].setdefault("sig_ano", []).append(float(sp[12]))
                            if sp[0]=="total": # in case less than 9 shells
                                break
        # print(self.error_table)
        self.highres_tableios=self.table['all']["i_over_sigma"][-2]
        # self.process_res,self.process_ios=self.resolution_based_on_ios_of_error_table(1)
        self.process_res,self.process_ios=self.resolution_based_on_ios_of_table(1.9)
        self.savetojson(self.jsonlogpath)
        print(f'{self.a_b_ISa=},{self.process_res=},{self.process_ios=}')
        print(f'{self.highres_tableios=}')
        # print(f"{self.table['all']=}")
        # self.savetojson()
            # txt = f.read()


        # ans = re.search('CRYSTAL MOSAICITY \(DEGREES\)(.*)',txt)
        # if ans:
        #     self.processMOS = float(ans.group(1))
        #     print(f'process MOS={self.processMOS}')
        
        # self.get_ISa(txt)
        
        
        
        # a=
        # b=
        # Isa
    def table_split(self,l):
        # TODO need to change behavior by version?
        assert l[50] == l[61] == l[71] == l[98] == "%"
        return list(map(lambda x:x.strip(),
                (l[:9], # RESOLUTION LIMIT
                    l[9:21], l[21:29], l[29:39], # NUMBER OF REFLECTIONS: OBSERVED  UNIQUE  POSSIBLE
                    l[39:50], # COMPLETENESS
                    l[51:61], l[62:71], # R-FACTOR: observed  expected
                    l[72:81], # COMPARED
                    l[81:89], # I/SIGMA
                    l[89:98], # R-meas 
                    l[99:107], # CC(1/2)
                    l[108:114], # AnomalCorr
                    l[115:123], # SigAno 
                    l[123:] # Nano
                )))

    def safe_float(self,v):
        try:
            return float(v)
        except ValueError:
            return float("nan")

    def errortable_split(self,l):
        # TODO need to change behavior by version?
        return list(map(lambda x:x.strip(),
               (l[:9], l[9:17], l[17:26], l[26:33], l[33:43], l[43:53], l[53:61], l[61:69], l[69:77])))

    def get_ISa(self,txt):
        ans = re.search('     a        b          ISa',txt)
        start=ans.end(0)+1
        ans2 = re.search('\n',txt[ans.end(0)+1:])
        end = ans.end(0)+1 + ans2.start(0)
        # print(ans2)
        a = txt[start:end].split()[0]
        b = txt[start:end].split()[1]
        if not (a == "4.000E+00" and b == "1.000E-04"):
            self.processISa = float(txt[start:end].split()[2])
        else:
            self.processISa = None
        print(f'ISa = {self.processISa}')

    def get_SG(self,num):
        lib = [(1, 'P 1'), (2, 'P -1'), (3, 'P 1 2 1'), (3, 'P 1 1 2'), (3, 'P 2 1 1'), (4, 'P 1 21 1'), (4, 'P 1 1 21'), (4, 'P 21 1 1'), (5, 'C 1 2 1'), (5, 'A 1 2 1'), (5, 'I 1 2 1'), (5, 'A 1 1 2'), (5, 'B 1 1 2'), (5, 'I 1 1 2'), (5, 'B 2 1 1'), (5, 'C 2 1 1'), (5, 'I 2 1 1'), (6, 'P 1 m 1'), (6, 'P 1 1 m'), (6, 'P m 1 1'), (7, 'P 1 c 1'), (7, 'P 1 n 1'), (7, 'P 1 a 1'), (7, 'P 1 1 a'), (7, 'P 1 1 n'), (7, 'P 1 1 b'), (7, 'P b 1 1'), (7, 'P n 1 1'), (7, 'P c 1 1'), (8, 'C 1 m 1'), (8, 'A 1 m 1'), (8, 'I 1 m 1'), (8, 'A 1 1 m'), (8, 'B 1 1 m'), (8, 'I 1 1 m'), (8, 'B m 1 1'), (8, 'C m 1 1'), (8, 'I m 1 1'), (9, 'C 1 c 1'), (9, 'A 1 n 1'), (9, 'I 1 a 1'), (9, 'A 1 a 1'), (9, 'C 1 n 1'), (9, 'I 1 c 1'), (9, 'A 1 1 a'), (9, 'B 1 1 n'), (9, 'I 1 1 b'), (9, 'B 1 1 b'), (9, 'A 1 1 n'), (9, 'I 1 1 a'), (9, 'B b 1 1'), (9, 'C n 1 1'), (9, 'I c 1 1'), (9, 'C c 1 1'), (9, 'B n 1 1'), (9, 'I b 1 1'), (10, 'P 1 2/m 1'), (10, 'P 1 1 2/m'), (10, 'P 2/m 1 1'), (11, 'P 1 21/m 1'), (11, 'P 1 1 21/m'), (11, 'P 21/m 1 1'), (12, 'C 1 2/m 1'), (12, 'A 1 2/m 1'), (12, 'I 1 2/m 1'), (12, 'A 1 1 2/m'), (12, 'B 1 1 2/m'), (12, 'I 1 1 2/m'), (12, 'B 2/m 1 1'), (12, 'C 2/m 1 1'), (12, 'I 2/m 1 1'), (13, 'P 1 2/c 1'), (13, 'P 1 2/n 1'), (13, 'P 1 2/a 1'), (13, 'P 1 1 2/a'), (13, 'P 1 1 2/n'), (13, 'P 1 1 2/b'), (13, 'P 2/b 1 1'), (13, 'P 2/n 1 1'), (13, 'P 2/c 1 1'), (14, 'P 1 21/c 1'), (14, 'P 1 21/n 1'), (14, 'P 1 21/a 1'), (14, 'P 1 1 21/a'), (14, 'P 1 1 21/n'), (14, 'P 1 1 21/b'), (14, 'P 21/b 1 1'), (14, 'P 21/n 1 1'), (14, 'P 21/c 1 1'), (15, 'C 1 2/c 1'), (15, 'A 1 2/n 1'), (15, 'I 1 2/a 1'), (15, 'A 1 2/a 1'), (15, 'C 1 2/n 1'), (15, 'I 1 2/c 1'), (15, 'A 1 1 2/a'), (15, 'B 1 1 2/n'), (15, 'I 1 1 2/b'), (15, 'B 1 1 2/b'), (15, 'A 1 1 2/n'), (15, 'I 1 1 2/a'), (15, 'B 2/b 1 1'), (15, 'C 2/n 1 1'), (15, 'I 2/c 1 1'), (15, 'C 2/c 1 1'), (15, 'B 2/n 1 1'), (15, 'I 2/b 1 1'), (16, 'P 2 2 2'), (17, 'P 2 2 21'), (17, 'P 21 2 2'), (17, 'P 2 21 2'), (18, 'P 21 21 2'), (18, 'P 2 21 21'), (18, 'P 21 2 21'), (19, 'P 21 21 21'), (20, 'C 2 2 21'), (20, 'A 21 2 2'), (20, 'B 2 21 2'), (21, 'C 2 2 2'), (21, 'A 2 2 2'), (21, 'B 2 2 2'), (22, 'F 2 2 2'), (23, 'I 2 2 2'), (24, 'I 21 21 21'), (25, 'P m m 2'), (25, 'P 2 m m'), (25, 'P m 2 m'), (26, 'P m c 21'), (26, 'P c m 21'), (26, 'P 21 m a'), (26, 'P 21 a m'), (26, 'P b 21 m'), (26, 'P m 21 b'), (27, 'P c c 2'), (27, 'P 2 a a'), (27, 'P b 2 b'), (28, 'P m a 2'), (28, 'P b m 2'), (28, 'P 2 m b'), (28, 'P 2 c m'), (28, 'P c 2 m'), (28, 'P m 2 a'), (29, 'P c a 21'), (29, 'P b c 21'), (29, 'P 21 a b'), (29, 'P 21 c a'), (29, 'P c 21 b'), (29, 'P b 21 a'), (30, 'P n c 2'), (30, 'P c n 2'), (30, 'P 2 n a'), (30, 'P 2 a n'), (30, 'P b 2 n'), (30, 'P n 2 b'), (31, 'P m n 21'), (31, 'P n m 21'), (31, 'P 21 m n'), (31, 'P 21 n m'), (31, 'P n 21 m'), (31, 'P m 21 n'), (32, 'P b a 2'), (32, 'P 2 c b'), (32, 'P c 2 a'), (33, 'P n a 21'), (33, 'P b n 21'), (33, 'P 21 n b'), (33, 'P 21 c n'), (33, 'P c 21 n'), (33, 'P n 21 a'), (34, 'P n n 2'), (34, 'P 2 n n'), (34, 'P n 2 n'), (35, 'C m m 2'), (35, 'A 2 m m'), (35, 'B m 2 m'), (36, 'C m c 21'), (36, 'C c m 21'), (36, 'A 21 m a'), (36, 'A 21 a m'), (36, 'B b 21 m'), (36, 'B m 21 b'), (37, 'C c c 2'), (37, 'A 2 a a'), (37, 'B b 2 b'), (38, 'A m m 2'), (38, 'B m m 2'), (38, 'B 2 m m'), (38, 'C 2 m m'), (38, 'C m 2 m'), (38, 'A m 2 m'), (39, 'A b m 2'), (39, 'B m a 2'), (39, 'B 2 c m'), (39, 'C 2 m b'), (39, 'C m 2 a'), (39, 'A c 2 m'), (40, 'A m a 2'), (40, 'B b m 2'), (40, 'B 2 m b'), (40, 'C 2 c m'), (40, 'C c 2 m'), (40, 'A m 2 a'), (41, 'A b a 2'), (41, 'B b a 2'), (41, 'B 2 c b'), (41, 'C 2 c b'), (41, 'C c 2 a'), (41, 'A c 2 a'), (42, 'F m m 2'), (42, 'F 2 m m'), (42, 'F m 2 m'), (43, 'F d d 2'), (43, 'F 2 d d'), (43, 'F d 2 d'), (44, 'I m m 2'), (44, 'I 2 m m'), (44, 'I m 2 m'), (45, 'I b a 2'), (45, 'I 2 c b'), (45, 'I c 2 a'), (46, 'I m a 2'), (46, 'I b m 2'), (46, 'I 2 m b'), (46, 'I 2 c m'), (46, 'I c 2 m'), (46, 'I m 2 a'), (47, 'P m m m'), (48, 'P n n n'), (49, 'P c c m'), (49, 'P m a a'), (49, 'P b m b'), (50, 'P b a n'), (50, 'P n c b'), (50, 'P c n a'), (51, 'P m m a'), (51, 'P m m b'), (51, 'P b m m'), (51, 'P c m m'), (51, 'P m c m'), (51, 'P m a m'), (52, 'P n n a'), (52, 'P n n b'), (52, 'P b n n'), (52, 'P c n n'), (52, 'P n c n'), (52, 'P n a n'), (53, 'P m n a'), (53, 'P n m b'), (53, 'P b m n'), (53, 'P c n m'), (53, 'P n c m'), (53, 'P m a n'), (54, 'P c c a'), (54, 'P c c b'), (54, 'P b a a'), (54, 'P c a a'), (54, 'P b c b'), (54, 'P b a b'), (55, 'P b a m'), (55, 'P m c b'), (55, 'P c m a'), (56, 'P c c n'), (56, 'P n a a'), (56, 'P b n b'), (57, 'P b c m'), (57, 'P c a m'), (57, 'P m c a'), (57, 'P m a b'), (57, 'P b m a'), (57, 'P c m b'), (58, 'P n n m'), (58, 'P m n n'), (58, 'P n m n'), (59, 'P m m n'), (59, 'P n m m'), (59, 'P m n m'), (60, 'P b c n'), (60, 'P c a n'), (60, 'P n c a'), (60, 'P n a b'), (60, 'P b n a'), (60, 'P c n b'), (61, 'P b c a'), (61, 'P c a b'), (62, 'P n m a'), (62, 'P m n b'), (62, 'P b n m'), (62, 'P c m n'), (62, 'P m c n'), (62, 'P n a m'), (63, 'C m c m'), (63, 'C c m m'), (63, 'A m m a'), (63, 'A m a m'), (63, 'B b m m'), (63, 'B m m b'), (64, 'C m c a'), (64, 'C c m b'), (64, 'A b m a'), (64, 'A c a m'), (64, 'B b c m'), (64, 'B m a b'), (65, 'C m m m'), (65, 'A m m m'), (65, 'B m m m'), (66, 'C c c m'), (66, 'A m a a'), (66, 'B b m b'), (67, 'C m m a'), (67, 'C m m b'), (67, 'A b m m'), (67, 'A c m m'), (67, 'B m c m'), (67, 'B m a m'), (68, 'C c c a'), (68, 'C c c b'), (68, 'A b a a'), (68, 'A c a a'), (68, 'B b c b'), (68, 'B b a b'), (69, 'F m m m'), (70, 'F d d d'), (71, 'I m m m'), (72, 'I b a m'), (72, 'I m c b'), (72, 'I c m a'), (73, 'I b c a'), (73, 'I c a b'), (74, 'I m m a'), (74, 'I m m b'), (74, 'I b m m'), (74, 'I c m m'), (74, 'I m c m'), (74, 'I m a m'), (75, 'P 4'), (76, 'P 41'), (77, 'P 42'), (78, 'P 43'), (79, 'I 4'), (80, 'I 41'), (81, 'P -4'), (82, 'I -4'), (83, 'P 4/m'), (84, 'P 42/m'), (85, 'P 4/n'), (86, 'P 42/n'), (87, 'I 4/m'), (88, 'I 41/a'), (89, 'P 4 2 2'), (90, 'P 4 21 2'), (91, 'P 41 2 2'), (92, 'P 41 21 2'), (93, 'P 42 2 2'), (94, 'P 42 21 2'), (95, 'P 43 2 2'), (96, 'P 43 21 2'), (97, 'I 4 2 2'), (98, 'I 41 2 2'), (99, 'P 4 m m'), (100, 'P 4 b m'), (101, 'P 42 c m'), (102, 'P 42 n m'), (103, 'P 4 c c'), (104, 'P 4 n c'), (105, 'P 42 m c'), (106, 'P 42 b c'), (107, 'I 4 m m'), (108, 'I 4 c m'), (109, 'I 41 m d'), (110, 'I 41 c d'), (111, 'P -4 2 m'), (112, 'P -4 2 c'), (113, 'P -4 21 m'), (114, 'P -4 21 c'), (115, 'P -4 m 2'), (116, 'P -4 c 2'), (117, 'P -4 b 2'), (118, 'P -4 n 2'), (119, 'I -4 m 2'), (120, 'I -4 c 2'), (121, 'I -4 2 m'), (122, 'I -4 2 d'), (123, 'P 4/m m m'), (124, 'P 4/m c c'), (125, 'P 4/n b m'), (126, 'P 4/n n c'), (127, 'P 4/m b m'), (128, 'P 4/m n c'), (129, 'P 4/n m m'), (130, 'P 4/n c c'), (131, 'P 42/m m c'), (132, 'P 42/m c m'), (133, 'P 42/n b c'), (134, 'P 42/n n m'), (135, 'P 42/m b c'), (136, 'P 42/m n m'), (137, 'P 42/n m c'), (138, 'P 42/n c m'), (139, 'I 4/m m m'), (140, 'I 4/m c m'), (141, 'I 41/a m d'), (142, 'I 41/a c d'), (143, 'P 3'), (144, 'P 31'), (145, 'P 32'), (146, 'R 3'), (147, 'P -3'), (148, 'R -3'), (149, 'P 3 1 2'), (150, 'P 3 2 1'), (151, 'P 31 1 2'), (152, 'P 31 2 1'), (153, 'P 32 1 2'), (154, 'P 32 2 1'), (155, 'R 3 2'), (156, 'P 3 m 1'), (157, 'P 3 1 m'), (158, 'P 3 c 1'), (159, 'P 3 1 c'), (160, 'R 3 m'), (161, 'R 3 c'), (162, 'P -3 1 m'), (163, 'P -3 1 c'), (164, 'P -3 m 1'), (165, 'P -3 c 1'), (166, 'R -3 m'), (167, 'R -3 c'), (168, 'P 6'), (169, 'P 61'), (170, 'P 65'), (171, 'P 62'), (172, 'P 64'), (173, 'P 63'), (174, 'P -6'), (175, 'P 6/m'), (176, 'P 63/m'), (177, 'P 6 2 2'), (178, 'P 61 2 2'), (179, 'P 65 2 2'), (180, 'P 62 2 2'), (181, 'P 64 2 2'), (182, 'P 63 2 2'), (183, 'P 6 m m'), (184, 'P 6 c c'), (185, 'P 63 c m'), (186, 'P 63 m c'), (187, 'P -6 m 2'), (188, 'P -6 c 2'), (189, 'P -6 2 m'), (190, 'P -6 2 c'), (191, 'P 6/m m m'), (192, 'P 6/m c c'), (193, 'P 63/m c m'), (194, 'P 63/m m c'), (195, 'P 2 3'), (196, 'F 2 3'), (197, 'I 2 3'), (198, 'P 21 3'), (199, 'I 21 3'), (200, 'P m -3'), (201, 'P n -3'), (202, 'F m -3'), (203, 'F d -3'), (204, 'I m -3'), (205, 'P a -3'), (206, 'I a -3'), (207, 'P 4 3 2'), (208, 'P 42 3 2'), (209, 'F 4 3 2'), (210, 'F 41 3 2'), (211, 'I 4 3 2'), (212, 'P 43 3 2'), (213, 'P 41 3 2'), (214, 'I 41 3 2'), (215, 'P -4 3 m'), (216, 'F -4 3 m'), (217, 'I -4 3 m'), (218, 'P -4 3 n'), (219, 'F -4 3 c'), (220, 'I -4 3 d'), (221, 'P m -3 m'), (222, 'P n -3 n'), (223, 'P m -3 n'), (224, 'P n -3 m'), (225, 'F m -3 m'), (226, 'F m -3 c'), (227, 'F d -3 m'), (228, 'F d -3 c'), (229, 'I m -3 m'), (230, 'I a -3 d')]
        a = None
        for n,name in lib:
            if num == n:
                a = name
                return a
                break
        return a    
    def resolution_based_on_ios_of_error_table(self, min_ios):
        # If all ios is less than min_ios, can't decide resolution.
        if "ios" not in self.error_table or max(self.error_table["ios"]) < min_ios:
            return float("nan")

        flag_last = False
        index = -1
        for dmin, ios in zip(self.error_table["dmin"], self.error_table["ios"]):
            # print(dmin,ios)
            if ios <= min_ios:
                # print(f'*******{ios}<={min_ios}')
                return temp
            else:
                temp = (dmin,ios)
            # print(dmin,ios)
            # if flag_last:
            #     return dmin
            # if ios <= min_ios:
            #     print(f'*******{ios}<={min_ios}')
            #     flag_last = True
            #     continue

        return (self.error_table["dmin"][-1],self.error_table["ios"][-1]) # the last

    def resolution_based_on_ios_of_table(self, min_ios):
        temp=(50,0)
        iostable = self.table['all']["i_over_sigma"][:-1]
        restable = self.table['all']["dmin"][:-1]
        # print(iostable)
        # print(restable)
        for dmin, ios in zip(restable,iostable):
            # print(dmin, ios)
            if ios <= min_ios:
                return temp
            else:
                temp = (dmin,ios)
        return (restable[-1],iostable[-1])
        pass
    def runnewres(self,res):
        shutil.copyfile(self.processfolder / 'XDS.INP',self.processfolder / 'XDSINP.BAK')
        with open(self.xdsinppath,'r') as f:
            xdsinp = f.read()

        xdsinp = re.sub("INCLUDE_RESOLUTION_RANGE=(.*)",f"INCLUDE_RESOLUTION_RANGE=30 {res}",xdsinp)
        xdsinp = re.sub("\nJOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT",f"\n!JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT\nJOB= CORRECT",xdsinp)
        #or force intergate
        xdsinp = re.sub("\nJOB= DEFPIX INTEGRATE CORRECT",f"\n!JOB= DEFPIX INTEGRATE CORRECT\nJOB= CORRECT",xdsinp)
        xdsinp = re.sub("SPACE_GROUP_NUMBER=(.*)",f"SPACE_GROUP_NUMBER={self.process_SGn}",xdsinp)
        cell = f'{self.process_CELL[0]} {self.process_CELL[1]} {self.process_CELL[2]} {self.process_CELL[3]} {self.process_CELL[4]} {self.process_CELL[5]}'
        xdsinp = re.sub("UNIT_CELL_CONSTANTS=(.*)",f"UNIT_CELL_CONSTANTS={cell}",xdsinp)
        with open(self.xdsinppath,'w') as f:
             f.write(xdsinp)
        self.run(False)
        pass
#  SPACE GROUP NUMBER    199
#  UNIT CELL PARAMETERS     78.801    78.801    78.801  90.000  90.000  90.000

                    # PROCESSING OF IMAGES        1 ...      50


#      a        b          ISa
#  5.814E-01  3.749E-02    6.77
#  ***** INTEGRATE *****
#  ***** CORRECT ***** 

#  THE DATA COLLECTION STATISTICS REPORTED BELOW ASSUMES:
#  SPACE_GROUP_NUMBER=  197
#  UNIT_CELL_CONSTANTS=    78.42    78.42    78.42  90.000  90.000  90.000

def pointlessjob(integrate_hkl,root,decilog,xs_prior=None):
    #from kamo #Author: Keitaro Yamashita
    #integrate_hkl = xdsin or hklin?
    #root=process folder
    #decilog = logpath
    # xs_prior = crystal.symmetry(params.cell_prior.cell, params.cell_prior.sgnum)
    
    worker = pp()
    pointless_integrate = worker.run_for_symm(xdsin=integrate_hkl, 
                                            logout=os.path.join(root, "pointless_integrate.log"))
    if "symm" in pointless_integrate:
        symm = pointless_integrate["symm"]
        print(type(symm.space_group_info()))
        print(" pointless using INTEGRATE.HKL suggested", symm.space_group_info(), file=decilog)
        if xs_prior:
            if xtal.is_same_space_group_ignoring_enantiomorph(symm.space_group(), xs_prior.space_group()):
                print(" which is consistent with given symmetry.", file=decilog)
            elif xtal.is_same_laue_symmetry(symm.space_group(), xs_prior.space_group()):
                print(" which has consistent Laue symmetry with given symmetry.", file=decilog)
            else:
                print(" which is inconsistent with given symmetry.", file=decilog)

        sgnum = symm.space_group_info().type().number()
        # cell = []
        cell =["%.2f"%x for x in symm.unit_cell().parameters()]
        # cell = " ".join(["%.2f"%x for x in symm.unit_cell().parameters()])
        # modify_xdsinp(xdsinp, inp_params=[("SPACE_GROUP_NUMBER", "%d"%sgnum),
        #                                 ("UNIT_CELL_CONSTANTS", cell)])

        # in pointless_integrate
        # ret["symm"] = crystal.symmetry(unit_cell=best_cell, space_group_symbol=best_symm,
        #                                assert_is_compatible_unit_cell=False)
        return pointless_integrate,sgnum,cell
    else:
        print(" pointless failed.", file=decilog)
        return None,None,None
def convttomtz(xdsin,mztout):
    xdsconvtxt = ""
    xdsconvtxt += f'INPUT_FILE = {xdsin}\n'
    xdsconvtxt += f'OUTPUT_FILE = {mztout} CCP4_I+F \n'
    xdsconvtxt += f"FRIEDEL'S_LAW=FALSE"

def quit(signum,frame):
    pass

if __name__ == '__main__':
    t0=time.time()
    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)
    par = argparse.ArgumentParser()
    #for test
    # par.add_argument("file",type=pathlib.Path,help="master file path",nargs='?',default=path)
    par.add_argument("file",type=pathlib.Path,help="master file path")
    
    par.add_argument("-frame",type=int,help="Number of frame for XDS to process")
    par.add_argument("-indexframe",type=int,help="Number of frame for XDS to index")
    par.add_argument("-res",type=float,help="Resolution for XDS")
    par.add_argument("-noano",help="tell MOSFLM/BEST/STRATEGY turn off anomalous",action='store_true')
    par.add_argument("-symm",type=str,help="space group for XDS")
    par.add_argument("-cell",type=str,help="cell for XDS usage '78 78 78 90 90 90'")
    par.add_argument("-debug",help="Show debug info",action='store_true')
    par.add_argument("-processfolder",type=pathlib.Path,help="process folder")
    par.add_argument("-test",help="test",action='store_true')
    
    args=par.parse_args()
    
    
    # print(directory)
    xds = QuickXDS()
    
    # print(processfloder)
    # print(xds.processfolder)
    xds.datapath = args.file.resolve()
    if args.noano:
        xds.ano = False
    if args.symm and args.cell:
        xs_prior = crystal.symmetry(unit_cell=args.cell,space_group_symbol=args.symm)
        xds.sym = xs_prior.space_group_number()
        xds.cell=args.cell
    elif args.symm:
        xs_prior = crystal.symmetry(space_group_symbol=args.symm)
        xds.symm = xs_prior.space_group_number()
    elif args.cell:
        xs_prior = crystal.symmetry(unit_cell=args.cell)
        xds.cell = args.cell
    else:
        xs_prior = None
    
    if args.res:
        xds.res=args.res
    if args.debug:
        xds.debug = True
    if args.indexframe:
        xds.imagetoindex = args.indexframe
    if args.frame:
        xds.imagetoprocess = args.frame
    if args.processfolder:
        directory = args.processfolder.resolve()
    else:
        directory = args.file.parent.resolve()
    filename = args.file.stem
    processfloder = directory / f"_QuickProcess_{filename}"
    xds.processfolder = processfloder

    #cleanup old file
    initCORRECT = processfloder / 'CORRECT.bak'
    COLSPOT = processfloder / 'COLSPOT.LP'
    CORRECT = processfloder / 'CORRECT.LP'
    IDXREF = processfloder / 'IDXREF.LP'
    INTEGRATE = processfloder / 'INTEGRATE.LP'
    xdsjoblog = processfloder / 'xds.json'
    pointlessjoblog = processfloder / 'pointless_integrate.log'
    Pstop = processfloder / 'done.txt'
    xjoblog = processfloder / 'logfile.log'
    ctrujoblog = processfloder / 'ctruncate.log'

    initCORRECT.unlink(missing_ok=True)
    COLSPOT.unlink(missing_ok=True)
    CORRECT.unlink(missing_ok=True)
    IDXREF.unlink(missing_ok=True)
    INTEGRATE.unlink(missing_ok=True)
    ctrujoblog.unlink(missing_ok=True)
    xjoblog.unlink(missing_ok=True)
    Pstop.unlink(missing_ok=True)
    xdsjoblog.unlink(missing_ok=True)
    pointlessjoblog.unlink(missing_ok=True)
    
    if args.test:
        # print(xs_prior.show_summary())
        # print(xs_prior.space_group_number())
        # print(xs_prior.space_group_info())
        # p=Pointless()
        # p.XDSIN = args.file
        # p.datapath = os.curdir
        
        # p.geninp()
        # p.run()
        # sys.exit()
        # p1 = pp()
        file = str(directory/'INTEGRATE.HKL')
        folder = str(directory)
        # logout = str(processfloder/"pointless.log")
        log = str(directory/"dcilog.log")
        # # print(logout)
        t0=time.time()
        # ans = p1.run_for_symm(hklin = file,logout=logout)
        with open (log,'w') as f:
            pointless_integrate,sgnum,cell = pointlessjob(integrate_hkl=file,root=folder,decilog=f)
        print(pointless_integrate,f'\nRuntime={time.time()-t0}')
        symm = pointless_integrate["symm"]
        # sgname = symm.space_group_info().type().lookup_symbol().replace(' ', '')
        # sgname = symm.space_group_info().change_hand()#from 41212 to 43212
        sgname = symm.inverse_hand()
        print(f'{sgname}')

        sys.exit()
    xds.genscript()
    xds.run()
    time_xdsdone = time.time()
    #pointless
    INTEGRATEfile = processfloder/'INTEGRATE.HKL'
    if INTEGRATEfile.exists():
        pass
    else:
        with open(xds.jsonlogpath,'r') as f:
            xdsdata = json.load(f)
        with open(xds.jsonlogpath,'w') as f:
            xdsdata["RunState"] = f'Fail for Autoprocess, Total Runtime={time.time()-t0}'
            json.dump(xdsdata,f, indent = 4)
        print(f'Fail for Autoprocess, Total Runtime={time.time()-t0}')
        doneflagpath = processfloder / 'done.txt'
        with open(doneflagpath,'w') as f:
            f.close
        sys.exit()


    with open(xds.jsonlogpath,'r') as f:
        xdsdata = json.load(f)

    with open(xds.jsonlogpath,'w') as f:
        xdsdata["RunState"] = 'POINTLESS'
        json.dump(xdsdata,f, indent = 4)
        
        


    file = str(processfloder/'INTEGRATE.HKL')
    folder = str(processfloder)
    log = str(processfloder/"dcilog.log")
    with open (log,'w') as f:
        pointless_integrate,sgnum,cell = pointlessjob(integrate_hkl=file,root=folder,decilog=f)
    xds.process_SGn = sgnum
    xds.process_CELL = cell
    time_pointlessdone = time.time()
    #res cut
    i = 0
    
    CORRECTfile = processfloder/'CORRECT.LP'
    if CORRECTfile.exists():
        rescut = True
    else:
        with open(xds.jsonlogpath,'r') as f:
            xdsdata = json.load(f)
        with open(xds.jsonlogpath,'w') as f:
            xdsdata["RunState"] = f'Fail for Autoprocess, Total Runtime={time.time()-t0}'
            json.dump(xdsdata,f, indent = 4)
        print(f'Fail for Autoprocess, Total Runtime={time.time()-t0}')
        doneflagpath = processfloder / 'done.txt'
        with open(doneflagpath,'w') as f:
            f.close
        sys.exit()
    while rescut:
        i += 1
        
        if xds.highres_tableios >= 1.9 and i ==1:
            #frist run res is ok but we want change space group
            print("Run:",i)
            print(f'new res:{xds.process_res}')
            xds.runnewres(xds.process_res)
            pass
        elif xds.highres_tableios >= 1.9:
            break 
        elif i == 6:
            break
        elif xds.process_res == 50:
            print("Unable to cut res")
            break
        else:
            print("Run:",i)
            print(f'new res:{xds.process_res}')
            xds.runnewres(xds.process_res)
    time_xdsresdone = time.time()
    #convert MTZ
    with open(xds.jsonlogpath,'r') as f:
        xdsdata = json.load(f)
    with open(xds.jsonlogpath,'w') as f:
        xdsdata["RunState"] = 'convert To MTZ and run xtriage'
        xdsdata["XDSdone"] = True
        json.dump(xdsdata,f, indent = 4)
    worker = pp()
    symm = pointless_integrate["symm"]
    sgname = symm.space_group_info().type().lookup_symbol().replace(' ', '')
    sg = symm.space_group_info().type().lookup_symbol()

    file = str(processfloder/'XDS_ASCII.HKL')
    t1=time.time()
    xds2mtz(file, dir_name=folder,
            run_xtriage=True, run_ctruncate=True,
            dmin=None, dmax=None, force_anomalous=True,
            with_multiplicity=True,
            flag_source=None, add_flag=True,
            space_group=sg)
    print(f'Convert XDS_ASCII.HKL({sgname}) to MTZ,Runtime={time.time()-t1}')
    mtzfile = pathlib.Path(processfloder/'XDS_ASCII.mtz')
   
    if mtzfile.exists():
        newmtzfile = mtzfile.rename(f'{filename}_{sgname}.mtz')
   
    # t0=time.time()
    # worker.run_copy(f'{filename}_{sgname}',folder,xdsin = file)
    
    # print(f'Convert XDS_ASCII.HKL({sgname}) to MTZ,Runtime={time.time()-t0}')
    if crystal.symmetry.is_identical_symmetry(symm,symm.inverse_hand()):

        pass
    else:
        sgname2 = symm.inverse_hand().space_group_info().type().lookup_symbol().replace(' ', '')
        sg2 = symm.inverse_hand().space_group_info().type().lookup_symbol()
        sgnum2 = symm.inverse_hand().space_group_info().type().number()
        # worker.run_copy(f'{filename}_{sgname}',folder,xdsin = file)
        # exitcode, output, err = util.call('pointless',f'-copy hklout {filename}_{sgname}', f'SPACEGROUP {sg}',
        #                                     wdir=folder)
        
        t2 = time.time()
        xds2mtz(file, dir_name=folder,
            run_xtriage=False, run_ctruncate=True,
            dmin=None, dmax=None, force_anomalous=True,
            with_multiplicity=True,
            flag_source=str(newmtzfile), add_flag=True,
            space_group=sg2)
        if mtzfile.exists():
            newmtzfile = mtzfile.rename(f'{filename}_{sgname2}.mtz')
        # exitcode, output, err = util.call('pointless',f'{file}',f'SPACEGROUP {sg}\nhklout {filename}_{sgname}\nwavelength 1\n',
        #                                     wdir=folder)

        print(f'Convert XDS_ASCII.HKL({sgname2}) to MTZ,Runtime={time.time()-t2}')
        # print(exitcode,output,err)
    
    
    print(f'Time for first xds run ={time_xdsdone-t0}')
    print(f'Time for pointless run ={time_pointlessdone-time_xdsdone}')
    print(f'Time for res.cut run ={time_xdsresdone-time_pointlessdone}')
    
    print(f'Time for convert to MTZ ={time.time()-time_xdsresdone}')
    print(f'Done for Autoprocess, Total Runtime={time.time()-t0}')

    with open(xds.jsonlogpath,'r') as f:
        xdsdata = json.load(f)
    with open(xds.jsonlogpath,'w') as f:
        xdsdata["RunState"] = f'Done for Autoprocess, Total Runtime={time.time()-t0}'
        json.dump(xdsdata,f, indent = 4)
    doneflagpath = processfloder / 'done.txt'
    with open(doneflagpath,'w') as f:
        f.close