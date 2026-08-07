# 2026-08-06 Raster 在偵測器尚未到位時就開始

**狀態:** 已修正並於 2026-08-07 09:24 實機驗證
**分支:** `fix/detector-distance-wait`(`2ca39f0`, `6b8fdca`)
**影響:** TPS 07A,使用者實驗(使用者與專案名稱不公開)

---

## 摘要

`Beamsize.target()` 在偵測器距離馬達(`07a:Det:Y`)還在移動時就回傳,
導致 Detector DHS 提早 arm 偵測器並回覆 `operdone`,DCSS 隨即下
`startRasterScan`。整段 raster 是在偵測器從約 350 mm 一路飛向 140 mm
的過程中收的,影像的距離資訊全部錯誤。

觸發條件:**偵測器先退開(換樣品/對心退到 350 mm),接著用「同一個 beamsize」
做近距離 raster**。當天符合此條件的 6 次 raster 全部中招。

---

## 影響範圍

當天 `Beamsize.txt` 出現 7 次 `Something wired, i should not goto here`,
每次 `07a:Det:Y` 都差 210~260 mm。其中 6 次是 raster,1 次是 `changeBeamSize`。

| 時間 | 資料夾 | 偵測器到位時間 |
|---|---|---|
| 10:34:41 | `<project>/sample-1/103415` | 未逐一查證(Det:Y 差 260 mm) |
| 11:07:24 | (`changeBeamSize`,非收數) | — |
| 11:48:22 | `<project>/sample-2/114805` | 未逐一查證(Det:Y 差 260 mm) |
| 13:23:58 | `<project>/sample-3/132303` | 13:24:42(operdone 後 35 s) |
| 13:32:38 | `<project>/sample-4/133223` | 13:33:22(operdone 後 35 s) |
| 13:39:35 | `<project>/sample-5/133810` | 13:40:18(operdone 後 35 s) |
| 13:49:25 | `<project>/sample-6/134912` | 13:50:09(operdone 後 35 s) |

這些 raster 的 hit map 與繞射資訊都是在錯誤的偵測器距離下取得的,**不可信任**。

---

## 時間軸(以 13:49 sample-6 為例)

| 時間 | 事件 |
|---|---|
| 13:47:37 | DCSS 下 `detector_z 350`(change_mode,換樣品/對心用) |
| 13:48:07 | `detector_z` 到 350 mm |
| 13:49:25.280 | DCSS 下 `detector_ratser_setup`,`distance=140` |
| 13:49:25.492 | `Beamsize.target(beamsize=10, dis=140)` 開始,`CurrentDetY=230.71`(=350 mm) |
| 13:49:25.557 | **`Something wired, i should not goto here`** — 未下移動命令,也未等待 |
| 13:49:25.859 | 後段複檢:`07a:Det:Y 230.71 not in 20.71` →「some motor not in position, move again」 |
| 13:49:25.949 | 補 `caput 07a:Det:Y = 20.712`,補完立刻 `End of moving beamsize`,**沒有等待** |
| 13:49:25.950 | `setup_beamsize_cover_distance` 回傳,**只花 0.566 秒** |
| 13:49:33.7 | MD3 Ready |
| 13:49:34.2 | arm detector 完成 → 回 `operdone` 給 DCSS |
| **13:49:35.886** | DCSS 下 **`startRasterScan` 30×31** — 此刻 `detector_z ≈ 311 mm` |
| **13:50:09.628** | `detector_z` 才到 **140 mm** |
| 13:50:12.491 | raster 結束 |

30×31 的 grid 幾乎全程在移動中收完,只有最後約 3 秒偵測器才在定位上。

---

## 根因

三個缺陷疊在一起,缺一不可。

### 1. 寫死的 40 mm 碰撞門檻(主因)

`EPICS_special.py` `Beamsize.target()`:

```python
collisionDetY = targetDetY < DetYLLM or targetDetY < 40
```

140 mm 距離對應的 `Det:Y` 約 20.7 mm,永遠 `< 40`,所以近距離時
`collisionDetY` 恆為 True → `MoveTogether` 恆為 False。

這個 40 出自舊校正(原註解:`#40 is measured at MD3Y = -6`)。以當時的
`Dis.OFF=137.28748`、`Dis.LLM=139.6` 計算,合法下限其實是 7~20 mm
(視 MD3Y 而定),40 早已與現況不符。

### 2. 分支沒有涵蓋「只改距離」的情況

`MoveTogether=False` 時,原本只處理 `detMove < 0` 與 `detMove > 0`。
這次 beamsize 沒變(10→10)所以 `detMove == 0.0`,而
`detDisMove == -210`(距離要變),四個 `elif` 全部不成立,掉進最後的
`else: pass` —— **既不下命令也不等待**。

### 3. 補救機制不等待

底部的位置複檢發現 `Det:Y` 不到位後,補下 `caput` 就直接往下走到
`End of moving beamsize`,沒有任何 `check_allmotorstop`。
於是 `target()` 在 0.57 秒內回傳,而 `Det:Y` 還有 210 mm 要走。

### 附帶發現:`updateDetYlimits` 的死分支

`epicsinit.py` `updateDetYlimits()` 裡:

```python
if 40 < NewDetYLLM :
    self.caput('07a:Det:Y.LLM', NewDetYLLM)
    ...'and updated'
else:
    self.caput('07a:Det:Y.LLM', NewDetYLLM)   # 原意是夾到 40
    ...'lower than 40,updated to 40'          # 訊息說謊
```

兩支寫入同一個值,判斷式對結果毫無影響,只有 log 文字不同,而 else 那句是錯的。
對照隔壁 `updateMD3Ylimits()` 的 `self.caput('07a:MD3:Y.HLM', 200.1)`
就知道這是漏改。**實測所有呼叫都走 else**(`NewDetYLLM` 為 7.31 / 20.31,
永遠 < 40),`recheck DetY LLM` 顯示實際寫入的是 20.31 而非 40 ——
也就是 40 這個下限**從來沒有生效過**。

> ⚠️ 不要用「把 else 改回 `caput 40`」的方式修。那會把 `Det:Y` 的 LLM 硬拉到 40,
> 使 ~159 mm 以下的距離全部走不了,140 mm 收數會當場失效。

---

## 為什麼之前沒被發現

`Something wired` 這條路徑只有在「偵測器已退開 + beamsize 不變 + 近距離收數」
三者同時成立時才會走到。平常 beamsize 有變(`detMove != 0`)就會落到會等待的
分支;偵測器沒退開時 `detDisMove ≈ 0`,則走最前面的「nothing move」分支。
而且它的 log 等級是 `INFO`,訊息又寫成像是不會發生的樣子,在大量 log 中不顯眼。

---

## 修正

### `2ca39f0` Wait for the detector distance move before arming for raster

- **`EPICS_special.py`** — 移除寫死的 `targetDetY < 40`,`collisionDetY`
  只保留 `targetDetY < DetYLLM`。`DetYLLM` 由距離內鎖
  (`epicsinit.updateDetYlimits`)依 `MD3Y + Dis.OFF + Dis.LLM` 維護,
  已經代表真實最小距離,是唯一經過校正的判斷依據。
- **`EPICS_special.py`** — 新增 `elif detMove == 0 and detDisMove != 0`
  分支(只移動距離),行為比照 `MoveTogether and detMove == 0`,並且會
  `check_allmotorstop` 等到馬達停止才回傳。
- **`epicsinit.py`** — 移除 `updateDetYlimits` 的死分支,只留一次 caput
  與一則正確的 log。
- **`epicsinit.py`** — 兩支 limit 更新的 log 加上 `move START(target)` /
  `move END(readback)` 標示,讓閱讀者知道該次更新是移動開始還是結束時算的。
  原有的 `MD3YPVID.VAL=` / `RBV=` 等字串保留,舊的 grep 不受影響。

### `6b8fdca` Flag the distance-only branch as unreachable and unsafe to move in

驗證後發現真正生效的是移除 `< 40`,新加的分支並未執行(見下節),因此為它
補上註解與警告,並把 log 等級提到 `warning`。

---

## 驗證(2026-08-07 09:24)

重現當天的故障情境:先 `changeBeamSize 10 350`(偵測器退到 350 mm、
beamsize 100→10),再下 `detector_ratser_setup distance=140`,beamsize 不變。

| | 修正前 08-06 13:49 | 修正後 08-07 09:24 |
|---|---|---|
| `setup_beamsize_cover_distance` 耗時 | **0.566 s** | **40.948 s** |
| `detector_ratser_setup` 總耗時 | 9.01 s | 40.98 s |
| 偵測器到 140 mm | 13:50:09.6 | 09:25:40.003 |
| `operdone` 送出 | 13:49:34.3(早 35 s) | 09:25:40.413(晚 0.4 s) |
| `startRasterScan` | 13:49:35.9,偵測器在 **311 mm** | 09:25:40.8,偵測器**已在 140 mm** |

`arm detector` 在 09:25:01.97 就完成,但 `operdone` 壓到 09:25:40.413 才送出,
表示 `_run_basesetup` 正確等到 arm 與距離移動**兩者都完成**。

### 一個重要的細節

實際生效的不是新加的分支。移除 `< 40` 之後:

```
CurrentDetY = 230.713, DetYLLM = 20.31236, will move to 20.7119, collisionDetY = False
MoveTogether = True
```

`MoveTogether` 變 True,於是走既有的 `elif MoveTogether and detMove == 0`
(log 為 `Moving det MOTOR only`),該分支本來就會等待。**新加的
`detMove == 0 and detDisMove != 0` 分支完全沒有被執行到。**

現在要進到新分支,必須 `detMove == 0` 且 `MoveTogether == False`,也就是
`collisionDetY` 或 `collisionMD3Y` 真的成立 —— 那是真實的內鎖違規,
無條件移動並不正確。目前的行為是 caput 被 EPICS 軟極限擋下、馬達不動、
`check_allmotorstop` 立即返回、底部複檢報 `not in position`:不會卡死,
但也不會讓上層知道 setup 失敗。已在該處留下 `TODO(review)`。

另外注意餘裕只有約 0.4 mm(`targetDetY 20.7119` vs `DetYLLM 20.31236`)。
若日後調整距離內鎖的 `Dis.LLM`,`collisionDetY` 有可能翻為 True。

---

## 未處理事項

### 1. 位置複檢的容差過嚴(建議優先處理)

底部複檢用 `diff < 0.001` 判定到位,但這比幾顆馬達實際能停到的精度還嚴。
單一份 `Beamsize.txt`(約一天)中 `some motor not in position` 觸發 **52 次**,
上一份 50 次,拆解後:

| motor | 次數 | 差值 |
|---|---|---|
| `07a:MD3:Hor` | 38 | 0.0011 ~ 0.0036 mm |
| `07a:Det:Y` | 13 | 6 筆 0.0010~0.0021 mm ／ 7 筆 **210~260 mm** |
| `07a:MD3:Y` | 7 | 0.0011 ~ 0.0023 mm |

那 7 筆 210/260 mm 就是本次事件;**其餘 51 筆全是 1~4 µm 的假警報**。

因此**不應該在修容差之前替這個補救機制加上等待與重試** —— 它一天觸發約 50 次,
幾乎全是假警報,加上等待只會讓每次 setup 變慢,而 `MD3:Hor` 永遠收斂不到
0.001,重試次數必定用光後噴錯。

建議順序:

1. 修容差 —— 改成 0.01 mm(假警報最大 0.0036,真失敗 210 mm,可乾淨切開),
   或每顆馬達讀自己的 `.RDBD` 當門檻。
2. 容差修好後,再替補救機制加上 `check_allmotorstop` 等待、重新驗證、有限次重試。
3. 重試用盡仍不到位時,讓 `target()` 回傳 False 並往上傳到
   `Detector._run_basesetup`,走既有的 `_setup_failed()`(送 DCSS 紅字 +
   `operdone`,不會卡住)。目前 `target()` 的回傳值在所有呼叫端都被忽略,
   這步會動到全部 collect type 的路徑。

### 2. 新分支該移動還是該中止

見上節,`TODO(review)` 已標在 `EPICS_special.py`。

### 3. 尚未驗證的情境

**退開後改用不同 beamsize 做近距離 raster**(`detMove != 0` 且
`MoveTogether == False`),會走 `detMove < 0` / `detMove > 0` 兩支。
那兩支本來就有等待,理論上沒問題,但未實測。
驗法:在 350 mm 時把 beamsize 從 10 換成 50,再開 140 mm 的 raster,
確認 `setup =` 同樣拉長到數十秒。

---

## 診斷用的 log 位置

| 檔案 | 用途 |
|---|---|
| `/home/blctl/Desktop/log/Beamsize.txt` | `Beamsize.target()` 走哪條分支、各馬達目標與到位狀況 |
| `/home/blctl/Desktop/log/Detectorlog.txt` | `detector_ratser_setup` 起訖、`setup = ` 耗時、arm、`operdone` |
| `/home/blctl/Desktop/log/EpicsLog.txt` | DCSS 往來訊息、`startRasterScan`、`detector_z` 位置回報 |
| `/home/blctl/Desktop/log/epicsdevlog.txt` | `updateDetYlimits` / `updateMD3Ylimits` 的極限計算 |

> `EpicsLog.txt` 內含 NUL bytes,`grep` 會當成 binary 而無輸出,需加 `-a`。

有用的搜尋字串:

```bash
grep -a "Something wired\|Moving det MOTOR only\|some motor not in position" Beamsize.txt
grep -a "setup  = \|arm detector\|send command to dcss" Detectorlog.txt
grep -a "startRasterScan\|detector_z move completed" EpicsLog.txt
```
