
import psycopg,time
import datetime
conn = psycopg.connect("host=10.7.1.108 port=5432  dbname=tps07a user=dhslogger password=dhslogger01234")
conn.autocommit(True)

cur = conn.cursor()
cur.execute("insert into log (time,log_level,log_levelname,dhs ,function ,log ,file,line) \
    values (TIMESTAMP '2022-07-20 12:35:00.340',1,'DEBUG','EPICSDHS','reciver','Got message from dcss : []','EpicsDHS.py',330)")
# conn.commit()
# conn.close()
