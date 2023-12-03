from Eiger.DEiger2Client import DEigerClient
det = DEigerClient('10.7.1.98')
ans= det.detectorConfig('omega_start')
print(ans)
print(type(ans))