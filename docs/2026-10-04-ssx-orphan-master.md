# 2026-10-04 SSX auto-repeat:master 檔留在 DCU、整串 run 沒有 data

**狀態:** 2026-10-04 03:21 已部署(DHS 03:21:46、epu TranferData 03:21:49 重啟),實機看過一次「被取代」路徑,**尚未 commit**(改動在 `fix/detector-distance-wait` 的工作目錄)
**影響:** TPS 07A,2026-10-04 02:42~02:44 SSX auto-repeat
- 0753 / 0765 / 0769 / 0771 的 master **沒被下載,留在 DCU 上**
- 0753~0773 在資料夾裡**全部只有 master、沒有任何 data 檔**(0752 只有 1 個 data 檔)
- 01:04~01:06 也出現過同樣每 ~3 秒一個 run 的連鎖

---

## 摘要

下載 server(epu 上的 `TranferData_EPU_RAM_NFS_HTTP.py`)和 DHS 的 `check_SSX_done()`
都用「filewriter 從 `acquire` 變回 `ready`」來判斷**自己這個 dataset** 結束了。
但 filewriter 的狀態是整台 DCU 共用的,不屬於任何一個 dataset。

SSX auto-repeat 連續收時,run N+1 的工作常在 run N 的 filewriter 還沒收尾前就開始,
於是把 **run N 的結束當成自己的結束**:

1. **下載 server** 以為 N+1 收完了,一個檔都沒拿就收工(`Allfile=[]`),再去刪一個還不存在的
   master(404)。master 隨後才寫出來,沒人去拿 → 孤兒檔。
2. **DHS** 的 checker 提早送 `ssx_state done`。GUI 的 auto-repeat 一看到 `done` 就送下一個 SSXCollect,
   而下一個 run 的 arm 會截斷目前這個 run → 下一個 checker 又錯判 → 循環。
   每個 run 只活約 3 秒、0 frame,這就是 0753~0773 沒有 data 的原因。

---

## 時間軸(0769)

| 時間 | 事件 |
|---|---|
| 02:43:47.739 | DHS 設 `name_pattern = sample_0769`,arm |
| 02:43:49.264 | arm 完成 |
| 02:43:49.324 | trigger;`ssx_state = collecting` |
| 02:43:49.326 | 0769 的 download job 送到 epu |
| 02:43:49.328 | `SSXStopCollect`(使用者在跟失控的 auto-repeat 搶)→ disarm |
| 02:43:49.709 | **0768** 的 filewriter acquire → ready |
| 02:43:49.725~.791 | epu 0769 worker 把它當成自己的結束:`Finish Download dataset sample_0769 , Allfile=[]` |
| 02:43:49.806 | 刪 `sample_0769_master.h5` → **`<Response [404]>`** |
| 之後 | 0769 master 寫出來,一直留在 DCU |

0771 更明顯:job 在 54.620 進來,0770 的狀態轉換在 55.04,0771 worker 在 55.080 就收工了
—— **0771 的 trigger 要到 57.385 才送出**。

0753、0765 同一個模式:job 都比前一個 run 的結束早到。

### 連鎖的證據

DHS 收到下一個 SSXCollect 的時間,幾乎都緊接在上一個 trigger 後 4~6 ms;
GUI 判斷要開下一個 run 用的 `done`,來自前面某個錯判的 checker:

```
02:43:49.324   trigger (0769)
02:43:49.890   DONE sent (checker of 0765)   ← 0765 早就被截斷了
02:43:49.930   SSXCollect idx=770
```

GUI 端的邏輯(`MeshbestServer/MestbestGUI.py` `check_ssx_data_download_done`):

```python
if self.bluiceData['string']['ssx_state']["txt"] == 'done':
    if self.SSXAutoRepeat.isChecked():
        self.SSX_StartCollect_clicked()
```

SSXCollect 是 nimages=50000(0.02 s → 1000 s)的 run,它只會在**下一個 run arm 時**被截斷。

---

## 根因

### 1. 下載 server:`TransferData()` 只看全域狀態

```python
if state == 'acquire':
    init = False
...
if state == 'ready':
    detabort = True        # 誰的 acquire→ready 都算,而且一旦設了就一直是 True
```

`name_pattern` 有讀出來(`currentfileWriterpatten`)但沒用。就算拿來比也救不了:
N+1 的 `name_pattern` 在 arm 前就設好了,那時 filewriter 還在收 N。

### 2. 下載 server:收工時無條件刪 master

不管有沒有下載到 master,`monitor_and_download_file` 收尾時都會發 DELETE。
master 還沒出現時就 404,出現之後就再也沒人處理。

### 3. DHS:`check_SSX_done()` 同樣的判斷,外加

- 第一段等待是**沒有 sleep 的 busy loop**,一直打 DCU。
- 等下載那段吃到例外(`Error on monitor DCU file, error'value'`)就跳出,
  然後印「All data in detector is downloaded」,**實際上檔案還在**。
- 等下載**沒有 timeout**:0769/0771 的 checker 在事故後一直每 0.1 s 輪詢,
  直到 DHS 重啟。
- 被下一個 run 截斷的 checker 照樣關 cover(0771 因此在 `wait_opencover` 多等了 2.8 s)、
  照樣送 `done`。
- 第二段用 `self.det`(fork 前父行程的 HTTP client)。

---

## 修正

### 新增 `Eiger/serieswatch.py`:兩邊共用的「只認自己 series」

關鍵事實:**master 檔在 arm 時就建立**(0774:arm 完成 31.286 → master 下載 31.639 → trigger 31.835)。
所以「自己的 master 出現在 DCU 上」就代表 filewriter 已經在處理自己這個 series。

`SeriesWatch.update(fwstate, files, detstate)` 的判斷:

1. 還沒看到自己的 master → 不管 filewriter 在做什麼,都不是自己的,繼續等。
2. 看到 master 之後又看到 `acquire` → 之後的 `ready` 就是自己結束。
3. 看到 master 但沒看到 `acquire`(很快被 abort,`acquire` 剛好落在兩次輪詢之間)→
   filewriter `ready` **且 detector 已離開 configure/ready/acquire** 才算結束。

第 3 點故意**不用時間 grace**:一般 collect arm 完可能要等 MD3 好幾秒才 trigger,
這段 detector 是 `ready`,不會被誤判。`detstate` 是 callable,只有走到第 3 點才多打一次 HTTP。

### 下載 server(`TranferData_EPU_RAM_NFS_HTTP.py`)

- `TransferData()` 改用 `SeriesWatch`,拿掉 `init` / `detabort`。
- master 超過 `master_timeout`(60 s)都沒出現 → 放棄這個 dataset,記 WARNING。
- `monitor_and_download_file` 收尾:**NFS 和 EPU 兩邊都拿到 master 才刪**;
  否則記 `... was not downloaded (NFS=...,EPU=...), leave it on DCU`。
  留在 DCU 上的檔,下次重啟 server 時 `savecurrentdata` 會存到 `/data/tmp/<時間>_backup`。

⚠ 這個檔是**所有 collect 類型共用**的下載流程(一般 collect、raster、multi-position 都走這裡),
不只 SSX。

### DHS(`Detector.py` `Eiger2X16M.check_SSX_done`)

- 等 series 結束改用 `SeriesWatch`,每 0.1 s 輪詢;讀 DCU 出錯就記 WARNING 重試,不再當成成功。
- **被下一個 run 取代的判斷**:series 結束時 `name_pattern` 已經不是自己 →
  不關 cover、不送 `Wating For Download Image` / `ssx_state done` / `Ready`。
  這是切斷 auto-repeat 連鎖的地方。
- 等下載改成**以進展計時**:連續 `download_stall_timeout`(300 s)沒有任何檔案被拿走 →
  CRITICAL log + `htos_note Warning SSX <檔名>: nothing downloaded for 300s, still on DCU: ... Check TranferData on epu.`
  (壓在 190 字元內,dcss 是 `char[201]`),然後照常收尾。
- `wait for detector download data` 只在清單變化時印,不再每 0.1 s 一行。
- 全程用自己的 `DEigerClient`,不再借用 `self.det`。

### Config(`Config.py`)

```python
'SeriesWatch':{'master_timeout':60,           #sec
               'download_stall_timeout':300,  #sec, DHS only
               },
```

兩邊都用 `.get(..., 預設值)` 讀,舊 Config 不會壞。

---

## 驗證

### 已完成

- `tests/test_serieswatch.py`:假 DCU 依時間軸重播,直接跑真正的 `check_SSX_done`,全部通過:

  | 情境 | 期望 |
  |---|---|
  | 0769:前一個 run 的 acquire→ready 先到,自己的 master 後到 | 不在前一個 run 結束時收工 |
  | arm 後馬上 abort,沒看到 acquire | detector idle 後結束 |
  | arm 完等 trigger 很久(filewriter ready、detector ready) | 不結束 |
  | 被下一個 run 取代 | 不送 `done`、不送 system_status、不關 cover |
  | 下載停滯 | 送一次 ≤190 字元的 warning,然後照常收尾 |

  另外有 `SeriesWatch` 單獨的逐步檢查(含 `detstate` 只在需要時才被呼叫、`master_overdue`)。
- `tests/test_dispatch.py` 照常通過;改過的檔案都 `py_compile` 過。
- epu 上用它自己的 python 能 import `Eiger.serieswatch` 與新的 `Config.Par['SeriesWatch']`。

```bash
.venv/bin/python tests/test_serieswatch.py
```

> 在 spec07a 上 `uv run` 會卡住無輸出,跑測試請直接用 `.venv/bin/python`。

### 實機觀察(部署後)

- 03:21:51 epu 重啟時 `savecurrentdata` 把 0753/0765/0769/0771 四個孤兒 master 存到
  epu `/data/tmp/20261004-032151_backup/`(各 148 MB,root 擁有),DCU 已清空。尚未搬回使用者目錄。
- **0815 / 0816:被取代路徑實際發生並正確處理。** DCSS 在 03:36:23 和 03:36:24(只差 1.3 s,
  0815 還在 setup)各送來一個 SSXCollect —— 這是 GUI 端送出的(連按兩次,或 GUI 自己),跟 DHS 無關。
  0816 arm 截斷了 0815,0815 的 checker 記下 `sample_0815 was ended by a newer collect`,
  **沒有送 `done`,所以沒有再連鎖**;使用者 03:37:17 按 Stop,0816 的 checker 送 `done` 收尾。
  兩個 run 的檔案都下載了,epu 沒有 `Allfile=[]` / 404 / WARNING。
- 0817(03:52 起的 1000 s 正常 run)下載速度 ~500 MB/s,邊收邊下載,DCU 上只留當下那個檔。
- **0816 只有 master、沒有 data**(0815 有 1 個 504 MB 的 data 檔)。這跟 0753~0773 一樣:
  被截斷的第一個 run 有 data,緊接著的第二個 run 沒有。推測是第一個 run 的 timing gate
  (`trigger:width` = 1000010)還沒結束,第二個 trigger 沒有作用,要等 Stop 把 width 設成 1 才結束。
  **未驗證**,要看 timing 系統。

### 尚未驗證(要實機)

- **filewriter 在 arm 之後、trigger 之前的狀態**:設計不依賴它,但沒實測過。
- **abort / disarm 後 detector state 會回到 `idle`**(第 3 點的前提)。如果停在別的狀態,
  `SeriesWatch` 會把 `DETECTOR_BUSY` 以外的都當成「不忙」;如果 abort 後卡在 `ready`,
  worker 會等到下一個 series 結束或 DHS/server 重啟 —— 只是延遲,不會丟資料。
- BlueIce 上 stall 警告的實際顯示。

---

## 部署步驟(找沒人在收的時段)

**順序重要:先 DHS,再 epu。**
現在 DHS 裡還有 0769/0771 的舊 checker 在等 master。如果先重啟 epu,`savecurrentdata` + `clear`
會把 master 清掉,舊 checker 醒來就會送 `done` / `Ready`,auto-repeat 開著的話會多跑一輪。

1. 確認沒有在收數據、**GUI 的 SSX auto-repeat 關掉**。
2. 重啟 EpicsDHS(順便清掉舊 checker)。
3. 重啟 epu 的 TranferData(`RunTranferDataEPU`,root 身分)。**會中斷正在下載的 dataset。**
4. 救孤兒 master:重啟時會存到 epu 的 `/data/tmp/<時間>_backup/`,
   要的話搬回 `/data/<user>/<date>_07A/<project>/` 並 chown 給該使用者。
   注意:0769/0771 本來就沒有 data 檔,master 只剩 metadata 價值。
5. 確認 DCU 清空:

   ```bash
   curl -s http://10.7.1.98/filewriter/api/1.8.0/files/    # spec07a 連不到 10.7.4.98
   ```

### 部署後的實機測試

1. **一般 collect 先測**(server 改動影響所有 collect 類型):一次 `detector_collect_shutterless`、
   一次 raster,確認檔案完整、DCU 清空、epu log 沒有新的 WARNING。
2. **SSX 短 run + auto-repeat**:frame 數設小(例如 500),auto-repeat 開,跑 2~3 輪:
   - 每一輪都應該收滿 frame 數才開下一輪(不再是每 3 秒一輪)。
   - 每輪都有完整的 data 檔,DCU 最後是空的。
3. **SSX 跑到一半按 Stop**:該 run 的 master + 已收到的 data 都有下載,auto-repeat 停下。
4. **連按兩次 Start**(刻意讓第二個 run 截斷第一個):DHS log 應出現
   `<prefix>_XXXX was ended by a newer collect, leave cover and ssx_state to it`,
   兩個 run 的檔案都要被下載。

### 部署後要看的 log

| 位置 | 正常 | 異常 / 要注意 |
|---|---|---|
| epu `/root/log/TransferDataLOG.txt` | `Finish Download dataset X , Allfile=[...有檔...]` | `never showed up on the DCU`、`was not downloaded ... leave it on DCU` |
| `Detectorlog.txt` | `All data of X is downloaded` | `was ended by a newer collect`(SSX 被截斷)、`nothing downloaded for`(CRITICAL)、`cannot read DCU` |

### 回退

改動都還沒 commit,回退就是還原這幾個檔再重啟 DHS / epu:

```bash
git checkout -- Detector.py Config.py TranferData_EPU_RAM_NFS_HTTP.py
rm Eiger/serieswatch.py tests/test_serieswatch.py
```

---

## 未處理事項

### 1. 孤兒掃描(建議下一步)

修正之後,server 放棄的 master 會留在 DCU 上,但要等**下次重啟 server** 才會被存起來。
應該在 job 收尾時比對 DCU 上的檔案與最近的 job(server 手上有它們的 header 與目錄),
不屬於任何進行中 job 的檔案就自動補下載,至少要發警告。

### 2. GUI 的 auto-repeat 只靠 `ssx_state == 'done'`

DHS 這邊修好之後連鎖會斷,但 GUI 本身仍會把任何一個(包含過期的)`done` 當成目前這個 run 的 `done`。
另外 GUI 送 operation 的 handle 一直是 `12.0`:`self.bluiceCounter += self.bluiceCounter`
從 0 開始永遠是 0。兩個都在 `MeshbestServer/MestbestGUI.py`,沒有動。

### 3. 其他 collect 路徑等下載也沒有 timeout

`Detector.py` 一般 collect 的等下載迴圈(`while bool(set(currentfile) & set(expctedlist))`)
同樣沒有 timeout,程式裡已經有一段 TODO 註記(2026-06-26 卡過 4.5 分鐘)。
可以照 `check_SSX_done` 的「以進展計時」做法處理。

### 4. 下載 server 的其他小問題(沒動)

- `monitor_and_download_file` 主迴圈沒有 sleep(`Queue.get(block=False)`),會一直打 DCU。
- `TransferData()` 迴圈裡的 HTTP 呼叫沒有 try:例外會讓 worker 死掉,永遠不送 `jobdone`,
  monitor 就一直等。

---

## 診斷指紋

以後遇到「某個 dataset 少了 master / 少了檔案」,先查這幾項:

```bash
# epu:收工時一個檔都沒拿,刪 master 又 404
ssh root@epu 'grep -n "Allfile=\[\]\|Response \[404\]" /root/log/TransferDataLOG.txt | tail'

# DCU 上的殘檔
curl -s http://10.7.1.98/filewriter/api/1.8.0/files/

# DHS:checker 宣稱下載完,但列出的清單裡還有檔案
grep -n "All data in detector is downloaded\|Error on monitor DCU" /home/blctl/Desktop/log/Detectorlog.txt | tail
```

連鎖的指紋:`Got SSXCollect OP` 每 ~3 秒一個,而且緊接在上一個 trigger(`timing:trigger,value=1`)後幾 ms;
NAS 上那串 run 只有 master、沒有 data。

| 檔案 | 用途 |
|---|---|
| `/home/blctl/Desktop/log/Detectorlog.txt` | SSXCollect / trigger / `check_SSX_done` 的時間 |
| epu `/root/log/TransferDataLOG.txt` | 每個 job 的下載、收工、刪檔結果 |
| epu `/data/tmp/<時間>_backup/` | server 重啟時從 DCU 救下來的殘檔(01:08 那次救了 0263/0301/0349/0360,代表以前就發生過) |
