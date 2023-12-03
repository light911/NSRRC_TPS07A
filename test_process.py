from multiprocessing import Process, Queue, Manager
import multiprocessing as mp
import time

def blockP(a):
    print('start!')
    t0=time.time()
    run = True
    while run:
        print(f'{time.time()-t0}')
        time.sleep(1)
        if (time.time()-t0) >10:
            run = False
    print('end!')
if __name__ == "__main__":
    closecoverP = Process(target=blockP,args=('close',),name='stop_close_cover')
    closecoverP.start()
    time.sleep(1)
    closecoverP.join(5)
    if closecoverP.exitcode== None:
        closecoverP.kill()
