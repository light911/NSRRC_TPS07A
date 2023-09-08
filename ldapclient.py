import ldap
import signal,time,os
import Config
from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
import logsetup
from hmac import compare_digest as compare_hash
import crypt

class ladpcleint():
    def __init__(self,Par=None) :
        t0=time.time()
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        self.ldapserver = 'ldap://10.7.1.1'
        #load config
        self.m = Manager()
        if Par == None:
            self.Par = self.m.dict()
            self.Par.update(Config.Par)
        else:
            self.Par = Par
        self.logger = logsetup.getloger2('ladpcleint',level = self.Par['Debuglevel'],LOG_FILENAME='./log/Ladpcleintlog.txt')
        self.ldap = ldap.initialize(self.ldapserver)
        self.ldap.simple_bind_s("","")
    def getuserinfo(self,username):
        basedn = "dc=px,dc=nsrrc,dc=org,dc=tw"
        searchScope = ldap.SCOPE_SUBTREE
        searchFilter = f'(&(uid={username})(objectClass=posixAccount))'
        searchAttribute = ["uidNumber","gidNumber","userPassword"]

        # (basedn, searchScope, searchFilter, searchAttribute)
        # self.ldap.search_s("o=My Organisation, c=AU", ldap.SCOPE_SUBTREE, "objectclass=*")
        userdata = self.ldap.search_s(basedn, searchScope,searchFilter,searchAttribute)
        # print(userdata)
        # [('uid=andy,ou=People,dc=px,dc=nsrrc,dc=org,dc=tw', {'uid': [b'andy'], 'cn': [b'andy'], 'sn': [b'andy'], 'mail': [b'andy@px.nsrrc.org.tw'], 'objectClass': [b'person', b'organizationalPerson', b'inetOrgPerson', b'posixAccount', b'top', b'shadowAccount'], 'loginShell': [b'/bin/bash'], 'uidNumber': [b'10002'], 'gidNumber': [b'501'], 'homeDirectory': [b'/data/andy'], 'gecos': [b'andy'], 'shadowLastChange': [b'18781'], 'userPassword': [b'{crypt}$6$iFW5esdt$BZnOVOr5k2HuTIgXKFgIzRPXwNHI/g4vja5i9M7ROTXzkKnW3ZWSc9I8sK8L/SvDde6PSXvLig9PYeLn86pid0']})]
        # [('uid=andy,ou=People,dc=px,dc=nsrrc,dc=org,dc=tw', {'uidNumber': [b'10002'], 'gidNumber': [b'501'], 'userPassword': [b'{crypt}$6$iFW5esdt$BZnOVOr5k2HuTIgXKFgIzRPXwNHI/g4vja5i9M7ROTXzkKnW3ZWSc9I8sK8L/SvDde6PSXvLig9PYeLn86pid0']})]
        if len(userdata) > 1:
            self.logger.warning(f'return more than one data! data = {userdata}')
            uidNumber = int(userdata[0][1]['uidNumber'][0])
            gidNumber = int(userdata[0][1]['gidNumber'][0])
            passwd = userdata[0][1]['userPassword'][0].decode("utf-8")
            pos = passwd.find("}") + 1
            passwd = passwd[pos:]
        elif len(userdata) == 0:
            self.logger.warning(f'return None data! wrong username?user name ={username} data = {userdata}')
            uidNumber = int(-1)
            gidNumber = int(-1)
            passwd = ""
        else:
            # print(userdata[0][1])
            uidNumber = int(userdata[0][1]['uidNumber'][0])
            gidNumber = int(userdata[0][1]['gidNumber'][0])
            passwd = userdata[0][1]['userPassword'][0].decode("utf-8")
            pos = passwd.find("}") + 1
            passwd = passwd[pos:]
            # print(passwd.decode("utf-8"))
        return uidNumber,gidNumber,passwd
            
        pass
    def checkusr(self,username,passwd):
        a,b,cryptedpasswd = self.getuserinfo(username)
        # print(cryptedpasswd)
        try :
            ok = compare_hash(crypt.crypt(passwd, cryptedpasswd), cryptedpasswd)
        except:
            self.logger.info(f'user:{username} has username?')
            ok = False
        if ok:
            self.logger.info(f'user:{username} has correct passwd')
        else:
            self.logger.warning(f'user:{username} has incorrect passwd')
        return ok

    def quit(self,signum,frame):

        # self.logger.debug(f"PID : {os.getpid()} DHS closed, Par= {self.Par} TYPE:{type(self.Par)}")
        self.logger.debug(f"PID : {os.getpid()} DHS closed")
        # self.logger.info(f'PID : {os.getpid()} DHS closed') 
        self.logger.warning(f'm pid={self.m._process.ident}')
        self.m.shutdown()
        active_children = mp.active_children()
        self.logger.warning(f'active_children={active_children}')
        if len(active_children)>0:
            for item in active_children:
                self.logger.warning(f'Last try to kill {item.pid}')
                os.kill(item.pid,signal.SIGKILL)


if __name__ == "__main__":
    import pwd
    # print(pwd.getpwnam('blctl'))
    
    # a1 = crypt.crypt('a')
    # a2= crypt.crypt('a',a1)
    # print(compare_hash(a1,a2))
    # print(compare_hash('aaa','aaba'))
    l = ladpcleint()
    print(l.getuserinfo('blctl'))
    # l.checkusr('andy','22543')