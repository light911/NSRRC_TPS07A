from Eiger.DEiger2Client import DEigerClient
import time
det = DEigerClient('10.7.1.98')
# ans= det.detectorConfig('omega_start')
ans= det.fileWriterConfig('name_pattern')['value']#series_$id 

print(ans)
print(type(ans))
while True:
    ans= det.fileWriterConfig('name_pattern')['value']#test_0_0006
    print(ans)
    ans2= det.fileWriterStatus('state')['value']#ready,acquire
    print(ans2)
    ans2= det.detectorStatus('state')['value']#idle,configure,ready
    print(ans2)
    ans2=currentfile = det.fileWriterFiles()
    print(ans2)
    time.sleep(0.1)