# 2026-09-23 Collect 卡死在低溫噴嘴 relay

**狀態:** 已修正,2026-09-23 16:36 起實機跑過成功路徑;失敗路徑目前只有合成測試
**分支:** `fix/detector-distance-wait`
**影響:** TPS 07A,2026-09-23 16:12~16:25 共 4 次 `detector_collect_shutterless` 完全卡住

---

## 摘要

`setup_beamsize_cover_distance()` 的第一行是 `askCryojetIn()`,它開一條 TCP 到
robot host(`10.7.1.3:10001`)要求把低溫噴嘴移進來。那個 socket **沒有設 timeout**。

當天 robot host 上的 `fakeserver.py` 壞掉之後,它照常 accept 連線卻永遠不回覆,
於是 `client.recv(4096)` 無限期阻塞,整個 DetectorQ worker 就停在那裡 ——
偵測器已經 arm 好了,但 cover 沒開,`operupdate` / `operdone` 也沒送出去,
DCSS 那端就一直掛著等,畫面上沒有任何錯誤訊息。

使用者連續重啟 EpicsDHS 三次都是同樣結果,因為真正壞掉的是另一台機器上的服務。

---

## 時間軸

| 時間 | 事件 |
|---|---|
| 16:12:12.285 | `fakeserver` 收到 `movecryojetin`,轉給 ISARA PLC |
| 16:12:12.288 | **`command Error:[Errno 104] Connection reset by peer`** — PLC 連線斷,`replayserver` worker 死亡 |
| 16:20:20 / 16:22:03 | 重啟 EpicsDHS 再試,`fakeserver` 只印 `Acepted connection`,沒有 `command client ask:` |
| 16:24:55 | 再次重啟 EpicsDHS |
| 16:25:17.198 | DCSS 下 `detector_collect_shutterless` handle `1.10` |
| 16:25:17.316 | `htos_note changing_detector_mode` 送出;`start to setup_beamsize_cover_distance` |
| 16:25:17.317 | `fakeserver` accept 了這條連線,fork 出 child pid 969313 |
| 16:25:19.976 | setup worker 那邊 `setup time = 2.66`,**偵測器已經 arm 完成** |
| — | `End to setup_beamsize_cover_distance` **永遠沒有出現** |
| 16:30 | 診斷:parent 停在 `recv()`,已卡 5 分鐘 |

`Detectorlog.txt` 的特徵非常乾淨:有 `start to setup_beamsize_cover_distance`,
沒有對應的 `End to ...`,中間夾著 setup worker 正常跑完的訊息。

---

## 定位方法

卡在哪一行不需要猜,`/proc` 就能直接讀出來:

```bash
# 1. 哪個行程、停在哪個 syscall
for t in /proc/62216/task/*; do echo "$t $(cat $t/syscall)"; done
#   /proc/62216/task/62216 syscall=45 0x4a ...     45 = recvfrom, 0x4a = fd 74

# 2. fd 74 是什麼
ss -tnp | grep 10.7.1.3:10001
#   ESTAB 10.7.1.4:36302 -> 10.7.1.3:10001  users:(("python",pid=62216,fd=74))
```

主執行緒停在 `recvfrom(fd=74)`,fd 74 就是連到 robot relay 的 socket,
對照原始碼只有 `askCryojetIn()` 這一處。

---

## 根因

### 1. 本端:`askCryojetIn()` 的 socket 沒有 timeout(本 repo 的缺陷)

```python
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((host, port))
sendToPLCCommand(client,command)
ans = client.recv(4096).decode()   # ← 對方不回就永遠停在這
```

移動低溫噴嘴是 collect 的**輔助動作**,卻因為沒有時間上限而能夠讓整條收數流程停擺。
而且例外是用 `print()` 而不是 logger,連錯誤都不會留在 `Detectorlog.txt` 裡。

### 2. 遠端:`fakeserver.py` 的 `replayserver` 死掉(不在本 repo)

`10.7.1.3:/home/blctl/Desktop/src/src/python/fakeserver.py`:

```python
# handle_client() - 每條連線一個
stateQ.put((item,backq))
replay = backq.get()        # ← 等 replayserver 回覆

# replayserver() - 全服務只有一個 worker
plcclient.send(toplc)
ans = plcclient.recv(4096)
```

`replayserver` 是 `stateQ` 唯一的消費者。16:12:12 跟 ISARA PLC 的連線被 reset 之後
這個 worker 就死了,之後每條進來的連線都只會被 accept、fork 出一個永遠卡在
`backq.get()` 的 child,既不讀指令也不回覆。

佐證:遠端 child 的 `/proc/969313/wchan` = `unix_stream_read_generic`(卡在
multiprocessing queue 的讀取),而且殘骸 child 的建立時間跟每次卡住的 collect 完全對得上 ——
969110→16:12:11、969204→16:20:20、969254→16:22:02、969313→16:25:16。

---

## 為什麼之前沒被發現

`movecryojetin` 平常 30~90 ms 就回來,relay 掛掉是相當罕見的狀態。
而 `fakeserver` 並不是整個死掉 —— 它還在 listen、還在 accept、log 還在長,
從外面看「服務是活的」,只有 `command client ask:` 這行不再出現。

本端這側同樣安靜:例外走 `print()`,卡住時連例外都沒有,log 就只是停在
`start to setup_beamsize_cover_distance` 不再前進。

---

## 修正

### `askCryojetIn()` 加上 timeout,並回報結果

- socket 進 `try` 之前先 `settimeout()`,同時涵蓋 connect / send / recv。
- 逾時上限走 Config:`Par['robot']['timeout']`(預設 5 秒),呼叫端用
  `.get('timeout',5)`,舊 Config 不會壞。
- 改用呼叫端傳進來的 logger,失敗才會留在 `Detectorlog.txt`。
- 加 `finally: client.close()`,原本失敗時會漏 fd。
- 回傳 `(ok, detail)` 取代原本的 `None`。

### 失敗時主動告訴 DCSS

collect **照常進行**(少移一次低溫噴嘴不值得砍掉一整批資料),但一定要讓使用者知道:

```python
cryo_ok,cryo_detail = askCryojetIn(host,port,...,self.logger)
if not cryo_ok:
    warn = f'Cryojet NOT moved in: robot relay {host}:{port} did not answer ({cryo_detail[:60]}). Check the cryojet before trusting this dataset.'
    self.sendQ.put(('warning',warn[:190]))
```

`('warning',...)` 是 `EpicsDHS.sender()` 裡本來就有、但一直沒人用的分支,
會送出 `htos_note Warning ...`。

**為什麼用 `htos_note` 而不是 `system_status` 紅字:**
`dcss_hardware_client.c` 的 `htos_note()` 是 `forward_to_broadcast_queue(message)`,
整句原樣廣播給所有 BlueIce client 並留在它的 log 裡。而 `system_status` 在每條
collect 路徑上一兩秒內就會被下一個狀態(`Changing detector mode` / `Ready`)蓋掉,
閃一下就消失的紅字反而像雜訊。

**長度限制:** dcss 把 hardware client 的訊息讀進 `char message[201]`
(`dcss_hardware_client.c:149`),整句必須壓在 200 字元內。正常訊息 157 字元沒問題,
但例外文字一長(例如 `ConnectionResetError: [Errno 104] ...`)會衝到 255 字元。
所以夾的是**例外文字**那半(`cryo_detail[:60]`)而不是夾尾巴,否則
「Check the cryojet」這句會先被砍掉。

---

## 驗證

### 實機(2026-09-23,relay 已修復後)

重啟 `fakeserver` 與 EpicsDHS 之後,三次 collect 都正常完成,成功路徑有留下紀錄:

```
16:36:22,952 - Detector - INFO -askCryojetIn - Robot relay:movecryojetin take 0.0789 sec
16:37:13,192 - Detector - INFO -askCryojetIn - Robot relay:movecryojetin take 0.0895 sec
16:44:34,314 - Detector - INFO -askCryojetIn - Robot relay:movecryojetin take 0.0721 sec
```

`(True, 'movecryojetin')`,耗時 0.07~0.09 秒,遠低於 5 秒上限。

### 合成測試(失敗路徑)

失敗路徑沒辦法在線上重現(不會為了測試去弄壞 relay),改用假 server 驗證:

| 情境 | 結果 |
|---|---|
| accept 後永不回覆(= 當天的 relay) | 2.00 s 返回,`(False,'TimeoutError: timed out')` |
| 封包黑洞 `192.0.2.1`(connect 卡住) | 2.00 s 返回 |
| 無路由 | 立即返回 |
| 正常回覆 | `(True,'movecryojetin')` |

警告經 `sender()` 格式化後:

```
htos_note Warning Cryojet NOT moved in: robot relay 10.7.1.3:10001 did not answer
(TimeoutError: timed out). Check the cryojet before trusting this dataset.
```

157 字元,在 dcss 的 200 字元上限內。

---

## 未處理事項

### 1. `fakeserver.py` 的 `replayserver` 沒有重生機制(建議優先處理)

本次修正只讓 DHS 不被拖死,**遠端的缺陷完全沒有動到**。`replayserver` 一旦因為
PLC 連線異常而死亡,整台 relay 就永久性地變成「accept 但不回應」,而且沒有任何
自我修復,只能靠人重啟。那支程式不在本 repo,需要另外處理。

至少應該:worker 用迴圈包起來、PLC 連線斷掉時重連、`handle_client` 的
`backq.get()` 加上 timeout。

### 2. 其他對外 socket 可能有同樣的問題

`askCryojetIn` 應該不是唯一一個沒設 timeout 的對外連線。值得掃一遍:

```bash
grep -n "socket.socket" *.py
```

每一處都要問:對方不回覆時,會不會擋住收數流程?

### 3. BlueIce 上的實際顯示尚未確認

警告文字只驗證到送出格式正確,還沒有在 BlueIce 畫面上實際看過長什麼樣子。
下次 relay 真的出問題時(或刻意用假 relay 測)再確認。

---

## 診斷用的 log 位置

| 檔案 | 用途 |
|---|---|
| `/home/blctl/Desktop/log/Detectorlog.txt` | `start to` / `End to setup_beamsize_cover_distance`、`Robot relay:`、`askCryojetIn failed` |
| `/home/blctl/Desktop/log/EpicsLog.txt` | DCSS 往來訊息、`detector_collect_shutterless` 進來的時間 |
| `10.7.1.3:/home/blctl/Desktop/src/src/python/log/isarafakeserverLog.txt` | relay 側,**關鍵指紋在這裡** |

> `EpicsLog.txt` 內含 NUL bytes,`grep` 會當成 binary 而無輸出,需加 `-a`。

**relay 是否已死的判斷方式** —— 看 `isarafakeserverLog.txt` 有沒有
`Acepted connection` 卻沒有後續的 `command client ask:`:

```bash
grep -a "Acepted connection\|command client ask" isarafakeserverLog.txt | tail -20
```

本端佐證:

```bash
ss -tnp | grep 10.7.1.3:10001                       # 有殘留的 ESTAB
for t in /proc/<pid>/task/*; do echo "$t $(cat $t/syscall)"; done | grep " 45 "
grep -a "start to setup_beamsize_cover_distance" Detectorlog.txt | tail -1
grep -a "End to setup_beamsize_cover_distance" Detectorlog.txt | tail -1   # 兩者時間不成對就是卡住了
```
