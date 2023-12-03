from Eiger.DEiger2Client import DEigerClient
import json

det = DEigerClient('10.7.1.98')
header =json.loads(det.streamConfig('header_appendix')['value'])
print(json.dumps(header, indent=1))

#P13_1_0001_master.h5
#P13_1_0001_data_000001.h5
#P13_1_0001_data_000002.h5
{
 "user": "afa",
 "directory": "/data/afa/20230922_07A/IBC-101/P13",
 "runIndex": 1,
 "beamsize": "30.000000",
 "atten": "0.000000",
 "fileindex": 1,
 "filename": "P13_1_0001",
 "uid": 10061,
 "gid": 501,
 "Ebeamcurrent": 503.47,
 "gap": 7.591,
 "dbpm1flux": 23460500000000.0,
 "dbpm2flux": 18461200000000.0,
 "dbpm3flux": 13360000000000.0,
 "dbpm5flux": 12600600000000.0,
 "dbpm6flux": 9986030000000.0,
 "sampleflux": 8787620000000.0,
 "kappa": -8.31485e-09,
 "dbpm1_sum_Mean": 50190.4,
 "dbpm1_sum_Stability": 0.0602,
 "dbpm1_x_Mean": 149.134,
 "dbpm1_x_rms": 5.667688535999999,
 "dbpm1_y_Mean": -146.701,
 "dbpm1_y_rms": 3.459502982,
 "dbpm2_sum_Mean": 39495.8,
 "dbpm2_sum_Stability": 0.0604,
 "dbpm2_x_Mean": 60.869,
 "dbpm2_x_rms": 0.004930389,
 "dbpm2_y_Mean": -158.545,
 "dbpm2_y_rms": 4.1017176950000005,
 "dbpm3_sum_Mean": 28587.1,
 "dbpm3_sum_Stability": 0.1612,
 "dbpm3_x_Mean": 29.689700000000002,
 "dbpm3_x_rms": 3.0252022918,
 "dbpm3_y_Mean": 72.48310000000001,
 "dbpm3_y_rms": 2.6675955293,
 "dbpm5_sum_Mean": 1751400.0,
 "dbpm5_sum_Stability": 0.1973,
 "dbpm5_x_Mean": 61.989599999999996,
 "dbpm5_x_rms": 0.5229442656,
 "dbpm5_y_Mean": 12.706299999999999,
 "dbpm5_y_rms": 0.5877044939,
 "dbpm6_sum_Mean": 1388180.0,
 "dbpm6_sum_Stability": 0.2,
 "dbpm6_x_Mean": 8.01131,
 "dbpm6_x_rms": 0.28715739564,
 "dbpm6_y_Mean": 1.13208,
 "dbpm6_y_rms": 0.26159538600000004
}

def caldatanum(totalimage:int,nimages_per_file:int=1000):
    index = 1
    current_number = index * nimages_per_file
    while current_number < totalimage:
        # print(current_number)
        if current_number % nimages_per_file == 0:
            index += 1
        current_number = index * nimages_per_file
    print(index)
    return index
def genDatasetNames(totalimage:int,nimages_per_file:int=1000,Filename:str='Test'):
    maxfileset = totalimage // nimages_per_file
    if  totalimage % nimages_per_file ==0:
        maxfileset = maxfileset -1
    maxfileset += 1
    datalist = []
    for i in range(maxfileset):
        filenum = i + 1
        dataname = f'{Filename}_data_{filenum:06}.h5'
        datalist.append(dataname)
    # print(datalist)
    return datalist
# 輸入例子1
input_example =[5000,3000,1800,800,1000,3000]
for item in input_example:
    print(f"輸入數字: {item}")
    caldatanum(item)
    b = genDatasetNames(item)
a = []
a.append('master')
a.extend(b)
print(a)

a = [1, 2,  4, 5]
b = [3, 4, 5, 6, 7]
c = [4, 5, 8, 9]

# 将列表 a 和 b 转换为集合
set_a = set(a)
set_b = set(b)

# 将列表 c 转换为集合
set_c = set(c)

# 使用集合的差集操作来找到在 a 和 b 中都存在，但不在 c 中的元素
result = set_a.intersection(set_b) - set_c

# 将结果转换回列表
result_list = list(result)

print(result_list)