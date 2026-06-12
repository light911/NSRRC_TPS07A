# EpicsDHS — TPS 07A EPICS Distributed Hardware Server

DCSS/BluIce 與 EPICS beamline 硬體之間的橋接程式(DHS)。
接收 DCSS 的 `stoh_*` 命令,轉換成 EPICS caput/caget 與 MD3、Eiger 偵測器、
衰減片、偵測器護蓋、CVLS 光源的操作,並把馬達位置、狀態回報給 DCSS。

## 環境與啟動

專案用 [uv](https://docs.astral.sh/uv/) 管理,Python 釘在 **3.12.x**
(`ldapclient.py` 使用的 `crypt` 模組在 3.13 被移除,不可升)。

```bash
./start_dhs.sh          # 正式啟動(venv 不存在時會自動 uv sync 建立)
```

- 相依套件定義在 `pyproject.toml`,版本鎖在 `uv.lock`。
- pyenv 的 `.python-version`(miniforge)與 uv 並存,uv 會忽略它(印一行警告,無害)。
- 主機需有 EPICS base 的 CLI 工具(`caget`/`caput`/`cainfo`)在 PATH —
  目前只剩 `myepics.cainfo()` 和零星舊路徑使用,但仍是執行環境的一部分。
- `dbloginstr.py`(PostgreSQL log 連線字串)**不進版控**,部署新機器要手動補。

## 行程架構

`EpicsDHS.py` 是入口,`__main__` 用 fork 啟動多個子行程,跨行程溝通靠
`multiprocessing.Queue` 與 Manager dict(`Par`):

```
main ─┬─ Manager(Par dict)
      ├─ Cover_server          DetectorCoverV2.MOXA(護蓋控制)
      ├─ epicsPVP              epicsinit.epicsdev:EPICS PV/Motor 監看 + epicsQ 消費者
      ├─ Attenserver           Flux07A.AttenServer.atten:attenQ 消費者
      ├─ workroundmd3moving    workround:MD3 馬達卡死自救 watchdog
      └─ serve_forever         DCSS 連線生命週期(連線→交握→session→重連)
            └─ 每個 session fork:
                 ├─ reciver    收 DCSS 命令,dispatch 到各 queue
                 ├─ sender     sendQ 消費者,組 htos_* 訊息回 DCSS
                 └─ detector   Detector.Eiger2X16M:DetectorQ 消費者
```

Queue 對應:`epicsQ`(馬達/scan/shutter)、`DetectorQ`(收數據/護蓋/beamsize)、
`attenQ`(衰減/ion chamber)、`sendQ`(回 DCSS)、`CVLSQ`(背光/環境切換,
**目前無消費者**,CVLScontrol 行程尚未啟用)。

DCSS 命令的路由表在 `EpicsDHS.py` 的 `OPERATION_ROUTES`
(操作名 → queue),新增 DCSS 操作在表裡加一行即可。

## 共用狀態(Par)

`Par` 是 Manager DictProxy。**巢狀 dict 寫入不會跨行程同步**,所以馬達狀態用
扁平 key:

```python
Par[f'EPICS.{GUIname}.RBV']   # 由 epicsinit callback 寫入
Par[f'EPICS.{GUIname}.DMOV']
Par[f'EPICS.{GUIname}.VAL']
```

讀寫都必須用這個格式,不要寫 `Par['EPICS'][name][field]`(改的是本地複本)。

## EPICS 存取

統一走 `workround.myepics`(pyepics + 每行程 lazy PV 快取):

```python
from workround import myepics
ca = myepics(logger)
ca.caget('07a:md3:State', format=str)            # 'READY'(乾淨字串,無 \n)
ca.caget([pv1, pv2], format=float)               # list of float
ca.caget('07a:md3:LastTaskInfo')                 # 'Auto':numpy array
ca.caput(pv, value)                              # 成功回傳 truthy,失敗 None
```

注意:
- PV 快取是 lazy 的 — **instance 可以在 fork 前建立,但不要在 fork 前呼叫
  caget/caput**(libca context 跨 fork 不安全;需要在子行程用 CA 就在子行程內呼叫)。
- 事件型的延遲/等待用 `threading.Thread/Timer`,不要 `multiprocessing.Process`
  — 從持有 libca 的行程 fork 既慢(成本隨 RSS 增加)又不安全。
- **絕對不要在 CA monitor callback 裡直接做 caput/caget** — put 會卡在發送
  緩衝區不 flush(動態限位曾因此沒送到 IOC,擋掉 raster scan 的 distance
  同步移動)。`epicsdev.caput` 已自動把 put 轉送到專屬 worker 執行緒,callback
  裡一律呼叫它,不要呼叫 `epics.caput`。
- 舊的 CLI subprocess 版 caget 會回傳帶 `\n` 的字串,pyepics 版是乾淨的;
  比較字串時一律用 `.strip()` 防呆。

## 日誌

`logsetup.getloger2()` 每個行程各自掛三個 handler:

| Handler | 等級 | 說明 |
|---|---|---|
| RotatingFileHandler | DEBUG | `/home/blctl/Desktop/log/*.txt`,20MB × 10 輪替 |
| Console | Config `Debuglevel`(INFO) | 彩色輸出 |
| LogDBHandler → PostgreSQL | DEBUG | **經 QueueListener 背景執行緒寫入**,不阻塞 CA callback |

LINE 通知(ERROR/CRITICAL)有 2 秒 timeout。
DB 的 `log` 表只進不出,**需要定期清理或分區**,否則 INSERT 會越來越慢。

## 測試

```bash
.venv/bin/python tests/test_dispatch.py      # DCSS 命令路由(離線,不碰 EPICS)
.venv/bin/python tests/smoke_connection.py   # 假 DCSS 連線/交握/重連(離線)
```

## 2026-06 重構摘要

| Commit | 內容 |
|---|---|
| `9646e1f` | DB log 背景化、LINE timeout、`Par['EPICS']` 扁平 key 修正、repo 清理、收編 CVLS_dhs |
| `dfccb83` | uv 管理、`serve_forever` 重連迴圈(取代遞迴)、明確 fork start method |
| `071142f` | reciver dispatch 表格化、oscillation 改 thread、`tests/` |
| `ee06b40` | myepics/epicsdev 全面改 pyepics + PV 快取、fork→thread、雜項 bug 修正 |

背景:長時間運轉後 PV 回應(如 zoom)變慢 + 記憶體成長。主因是
(1) 每筆 DEBUG log 在 CA callback 裡同步寫 PostgreSQL;
(2) 每個事件 fork 子行程 + 所有 caget/caput 都是 subprocess
(workroundmd3moving 一項就是每秒 ~30 次 fork)。

## 部署驗收清單

重構後第一次上線,依序確認:

1. `./start_dhs.sh` 啟動,BluIce 連線正常
2. **zoom 切換**(Timer + pyepics caput 路徑)
3. 馬達移動 + 移動中再下指令(會回 "already moving",這是修好 `Par` 同步後才生效的行為)
4. **raster scan / 4D scan**(caputarray)、**change_mode 切相位**(數字字串轉換)
5. **abort**、**換能量**(gap 連動)
6. SSX 收數據(`DataCollection` 相位比較)
7. 模擬 DCSS 重啟:應看到 "DCSS session ended, reconnect in 1 sec" 後自動接回
8. 跑 1-2 週觀察:zoom 是否不再隨時間變慢、`ps` 各子行程 RSS 是否持平

## 已知事項 / TODO

- `CVLSQ` 尚無消費者:`CVLScontrol` 行程在 `run_session` 未啟用,
  `setBackLightColor`/`switchSampleEnvironment` 會堆積在 queue。
- `Detector.py` 仍有大量 Process-per-action 模式(護蓋、setup),屬下一階段。
- DB `log` 表 retention 尚未設定。
- `operationRecord` 只在 operdone handle 配對成功時移除,長期可能殘留。
