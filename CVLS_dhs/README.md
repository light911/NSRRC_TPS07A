# SCHOTT ColdVision Light Source Python 控制庫
# SCHOTT ColdVision Light Source Python Control Library

這是一個用於控制 SCHOTT ColdVision Light Source (CV-LS) 的 Python 控制庫，支援透過網路、USB 或 UART 連接。

This is a Python control library for the SCHOTT ColdVision Light Source (CV-LS), supporting connection via Ethernet, USB, or UART.

## 功能特色 / Features

- ✅ 支援網路 (Ethernet/Telnet) 連接
- ✅ 支援 USB 和 UART 串列埠連接
- ✅ 控制 4 個獨立的 LED 通道
- ✅ 主開關控制（總開關）
- ✅ 獨立或統一的亮度控制 (0-1000)
- ✅ 查詢裝置狀態（溫度、電壓、風扇轉速等）
- ✅ 設定儲存與恢復
- ✅ Context manager 支援（自動連接/斷開）

---

- ✅ Ethernet (Telnet) connection support
- ✅ USB and UART serial connection support
- ✅ Control 4 independent LED channels
- ✅ Master switch control
- ✅ Individual or unified brightness control (0-1000)
- ✅ Query device status (temperature, voltage, fan speed, etc.)
- ✅ Settings save and restore
- ✅ Context manager support (automatic connect/disconnect)

## 安裝需求 / Requirements

### Python 版本 / Python Version
- Python 3.7 或更高版本 / Python 3.7 or higher

### 依賴套件 / Dependencies

基本網路連接（無需額外套件）：
For basic Ethernet connection (no additional packages needed):
```bash
# 只需要 Python 標準庫 / Only Python standard library required
```

如果使用 USB/UART 連接：
For USB/UART connection:
```bash
pip install pyserial
```

## 快速開始 / Quick Start

### 1. 基本連接與控制 / Basic Connection and Control

```python
from cvls_control import CVLSController, Channel

# 創建控制器（使用網路連接）
# Create controller (using Ethernet connection)
controller = CVLSController(host="10.7.1.111", port=50811)

# 連接到裝置
# Connect to device
controller.connect()

# 開啟主開關
# Turn on master switch
controller.master_on()

# 設定所有通道亮度為 50% (500/1000)
# Set all channels to 50% brightness
controller.set_all_channels_power(500)

# 關閉主開關
# Turn off master switch
controller.master_off()

# 斷開連接
# Disconnect
controller.disconnect()
```

### 2. 使用 Context Manager（推薦）/ Using Context Manager (Recommended)

```python
from cvls_control import CVLSController, Channel

# 自動連接和斷開
# Automatic connection and disconnection
with CVLSController(host="10.7.1.111") as controller:
    # 開啟裝置
    controller.master_on()

    # 設定亮度
    controller.set_all_channels_power(800)

    # 程式結束時會自動斷開連接
    # Connection automatically closes when exiting the block
```

### 3. 獨立控制各通道 / Individual Channel Control

```python
with CVLSController(host="10.7.1.111") as controller:
    controller.master_on()

    # 設定各通道不同亮度
    # Set different brightness for each channel
    controller.set_individual_powers(
        ch1=250,   # 25%
        ch2=500,   # 50%
        ch3=750,   # 75%
        ch4=1000   # 100%
    )

    # 關閉特定通道
    # Disable specific channels
    controller.set_output_enable(Channel.CHANNEL_1, False)
    controller.set_output_enable(Channel.CHANNEL_3, False)

    # 重新開啟
    # Re-enable
    controller.set_output_enable(Channel.CHANNEL_1, True)
    controller.set_output_enable(Channel.CHANNEL_3, True)
```

### 4. 查詢裝置狀態 / Query Device Status

```python
with CVLSController(host="10.7.1.111") as controller:
    # 獲取裝置資訊
    # Get device information
    print(f"產品 / Product: {controller.get_product_name()}")
    print(f"韌體 / Firmware: {controller.get_firmware_version()}")
    print(f"序號 / Serial: {controller.get_serial_number()}")

    # 獲取溫度和電壓
    # Get temperature and voltage
    print(f"LED 溫度 / LED Temp: {controller.get_led_temperature():.1f}°C")
    print(f"主板溫度 / Board Temp: {controller.get_board_temperature():.1f}°C")
    print(f"輸入電壓 / Input Voltage: {controller.get_input_voltage():.2f}V")

    # 獲取通道狀態
    # Get channel status
    for ch in range(1, 5):
        power = controller.get_output_power(Channel(ch))
        enabled = controller.get_output_enable(Channel(ch))
        print(f"通道 / Channel {ch}: {power}/1000 ({'ON' if enabled else 'OFF'})")
```

### 5. USB/UART 連接 / USB/UART Connection

```python
from cvls_control import CVLSController, ConnectionType

# Windows
controller = CVLSController(
    connection_type=ConnectionType.USB,
    serial_port="COM3"
)

# Linux
controller = CVLSController(
    connection_type=ConnectionType.UART,
    serial_port="/dev/ttyUSB0"
)

controller.connect()
# ... 控制操作 / control operations ...
controller.disconnect()
```

## API 參考 / API Reference

### 類別 / Classes

#### `CVLSController`

主要的控制器類別 / Main controller class

**初始化參數 / Initialization Parameters:**
- `connection_type`: 連接類型 (ETHERNET, USB, UART) / Connection type
- `host`: IP 位址（網路連接） / IP address (for Ethernet)
- `port`: 連接埠號碼，預設 50811 / Port number, default 50811
- `serial_port`: 串列埠路徑（USB/UART） / Serial port path (for USB/UART)
- `timeout`: 通訊逾時（秒），預設 2.0 / Communication timeout (seconds), default 2.0

#### `Channel`

通道列舉 / Channel enumeration
- `Channel.COMMON` (0): 所有通道 / All channels
- `Channel.CHANNEL_1` (1): 通道 1 / Channel 1
- `Channel.CHANNEL_2` (2): 通道 2 / Channel 2
- `Channel.CHANNEL_3` (3): 通道 3 / Channel 3
- `Channel.CHANNEL_4` (4): 通道 4 / Channel 4

### 主要方法 / Main Methods

#### 連接管理 / Connection Management
- `connect()`: 連接到裝置 / Connect to device
- `disconnect()`: 斷開連接 / Disconnect from device

#### 基本 LED 控制 / Basic LED Control
- `master_on()`: 開啟主開關 / Turn on master switch
- `master_off()`: 關閉主開關 / Turn off master switch
- `set_output_enable(channel, enable)`: 設定通道開關 / Set channel enable/disable
- `get_output_enable(channel)`: 查詢通道開關狀態 / Query channel enable status
- `set_output_power(channel, power)`: 設定通道功率 (0-1000) / Set channel power (0-1000)
- `get_output_power(channel)`: 查詢通道功率 / Query channel power
- `set_all_channels_power(power)`: 設定所有通道功率 / Set all channels power
- `set_individual_powers(ch1, ch2, ch3, ch4)`: 設定各通道獨立功率 / Set individual channel powers

#### 裝置資訊 / Device Information
- `get_product_name()`: 獲取產品名稱 / Get product name
- `get_firmware_version()`: 獲取韌體版本 / Get firmware version
- `get_serial_number()`: 獲取序號 / Get serial number
- `get_model_serial()`: 獲取型號與序號 / Get model and serial number

#### 狀態查詢 / Status Query
- `get_led_temperature()`: 獲取 LED 溫度 (°C) / Get LED temperature (°C)
- `get_board_temperature()`: 獲取主板溫度 (°C) / Get board temperature (°C)
- `get_input_voltage()`: 獲取輸入電壓 (V) / Get input voltage (V)
- `get_fan_speed()`: 獲取風扇轉速 (RPM) / Get fan speed (RPM)
- `get_error_flags()`: 獲取錯誤標誌 / Get error flags
- `get_all_status()`: 獲取完整狀態資訊 / Get complete status information

#### 設定管理 / Settings Management
- `save_settings()`: 儲存設定到非揮發性記憶體 / Save settings to non-volatile memory
- `restore_settings()`: 從記憶體恢復設定 / Restore settings from memory
- `factory_reset(preserve_network)`: 恢復原廠設定 / Restore factory defaults
- `reboot()`: 重新啟動裝置 / Reboot device

#### 連續閃爍控制 / Continuous Strobe Control
- `set_continuous_strobe_enable(enable)`: 啟用/停用連續閃爍 / Enable/disable continuous strobe
- `set_continuous_strobe_frequency(freq)`: 設定頻率 (6-20000 Hz) / Set frequency (6-20000 Hz)
- `set_continuous_strobe_duty_cycle(channel, duty)`: 設定工作週期 (0-1000) / Set duty cycle (0-1000)
- `set_continuous_strobe_phase_shift(channel, phase)`: 設定相位偏移 (0-1000) / Set phase shift (0-1000)
- `get_continuous_strobe_enable()`: 查詢連續閃爍狀態 / Query continuous strobe status
- `get_continuous_strobe_frequency()`: 查詢頻率 / Query frequency

#### 觸發閃爍控制 / Triggered Strobe Control
- `set_triggered_strobe_enable(enable)`: 啟用/停用觸發閃爍 / Enable/disable triggered strobe
- `set_triggered_strobe_delay(channel, delay_us)`: 設定延遲 (0-1000000 µs) / Set delay (0-1000000 µs)
- `set_triggered_strobe_on_time(channel, time_us)`: 設定開啟時間 (µs) / Set on time (µs)
- `set_triggered_strobe_edge(channel, falling)`: 設定觸發邊緣 / Set trigger edge
- `get_triggered_strobe_enable()`: 查詢觸發閃爍狀態 / Query triggered strobe status

#### 均衡器控制 / Equalizer Control
- `set_equalizer_enable(enable)`: 啟用/停用均衡器 / Enable/disable equalizer
- `set_equalizer_target(target)`: 設定目標光輸出 (0-4095) / Set target light output (0-4095)
- `set_equalizer_startup_delay(seconds)`: 設定啟動延遲 (0-500 秒) / Set startup delay (0-500 s)
- `get_equalizer_enable()`: 查詢均衡器狀態 / Query equalizer status
- `get_equalizer_stability()`: 獲取均衡器穩定性 / Get equalizer stability
- `get_equalizer_current_output()`: 獲取當前光輸出 / Get current light output
- `get_equalizer_power_output()`: 獲取功率輸出 / Get power output

#### 網路設定 / Network Configuration
- `get_network_ip_static()`: 獲取靜態 IP / Get static IP
- `set_network_ip_static(ip)`: 設定靜態 IP / Set static IP
- `get_network_dhcp()`: 查詢 DHCP 狀態 / Query DHCP status
- `set_network_dhcp(enable)`: 啟用/停用 DHCP / Enable/disable DHCP
- `get_network_hostname()`: 獲取主機名 / Get hostname
- `set_network_hostname(name)`: 設定主機名 / Set hostname
- `get_network_subnet_mask()`: 獲取子網路遮罩 / Get subnet mask
- `set_network_subnet_mask(mask)`: 設定子網路遮罩 / Set subnet mask
- `get_network_gateway()`: 獲取閘道 / Get gateway
- `set_network_gateway(gateway)`: 設定閘道 / Set gateway

#### 進階控制 / Advanced Controls
- `set_single_channel_mode(enable)`: 設定單/四通道模式 / Set single/quad channel mode
- `get_single_channel_mode()`: 查詢通道模式 / Query channel mode
- `set_knob_mode(mode)`: 設定旋鈕模式 (0-5) / Set knob mode (0-5)
- `get_knob_mode()`: 查詢旋鈕模式 / Query knob mode
- `set_front_controls_lockout(locked)`: 鎖定/解鎖前面板 / Lock/unlock front panel
- `get_front_controls_lockout()`: 查詢前面板鎖定 / Query front panel lockout
- `set_multiport_lockout(locked)`: 鎖定/解鎖多埠 / Lock/unlock multiport
- `get_multiport_lockout()`: 查詢多埠鎖定 / Query multiport lockout
- `get_light_feedback_raw()`: 獲取光感測器原始值 / Get raw light feedback

## 範例程式 / Example Scripts

### 基本控制範例 / Basic Control Example

執行基本控制範例：
Run the basic control example:

```bash
python example_basic_control.py
```

這個範例會示範：
This example demonstrates:
- 連接到裝置 / Connecting to device
- 控制主開關 / Controlling master switch
- 設定通道亮度 / Setting channel brightness
- 查詢裝置狀態 / Querying device status
- 漸變效果 / Fade effects

### 進階功能範例 / Advanced Features Example

執行進階功能範例：
Run the advanced features example:

```bash
python example_advanced_features.py
```

這個範例提供互動式選單，示範：
This example provides an interactive menu demonstrating:
- 連續閃爍模式（內部觸發，6-20000 Hz）
- Continuous strobe mode (internal trigger, 6-20000 Hz)
- 觸發閃爍模式（外部觸發，微秒級精度）
- Triggered strobe mode (external trigger, microsecond precision)
- 均衡器控制（維持恆定光輸出）
- Equalizer control (constant light output)
- 網路設定查詢與修改
- Network configuration query and modification
- 進階控制設定（鎖定、模式切換等）
- Advanced control settings (lockout, mode switching, etc.)

## 注意事項 / Notes

1. **網路連接 / Network Connection**
   - 預設 IP: 10.7.1.111（可在 CLAUDE.md 中查看）
   - Default IP: 10.7.1.111 (see CLAUDE.md)
   - 預設埠 / Default port: 50811
   - 使用 Legacy Protocol（Telnet）
   - Uses Legacy Protocol (Telnet)

2. **功率範圍 / Power Range**
   - 範圍 / Range: 0-1000
   - 0 = 0%, 500 = 50%, 1000 = 100%

3. **通道索引 / Channel Indexing**
   - 使用 `Channel.COMMON` (0) 可同時控制所有通道
   - Use `Channel.COMMON` (0) to control all channels simultaneously
   - 個別通道為 1-4 / Individual channels are 1-4

4. **錯誤處理 / Error Handling**
   - 所有方法都會返回 None 或 False 表示錯誤
   - All methods return None or False to indicate errors
   - 檢查返回值以確保命令成功執行
   - Check return values to ensure commands executed successfully

## 故障排除 / Troubleshooting

### 無法連接 / Cannot Connect
```python
# 檢查網路連接 / Check network connection
import socket
try:
    sock = socket.socket()
    sock.settimeout(2)
    sock.connect(("10.7.1.111", 50811))
    print("網路連接正常 / Network connection OK")
    sock.close()
except Exception as e:
    print(f"網路連接失敗 / Network connection failed: {e}")
```

### 查看裝置回應 / View Device Response
```python
# 啟用除錯模式（修改 _send_command 方法來顯示原始回應）
# Enable debug mode (modify _send_command method to show raw responses)
```

## 授權 / License

本專案僅供內部使用。請參考 SCHOTT ColdVision 官方文件以了解裝置使用限制。

This project is for internal use only. Please refer to SCHOTT ColdVision official documentation for device usage restrictions.

## 參考資料 / References

- 完整的 API 說明請參考 `doc/schott-coldvision-cv-ls-programming guide-en.pdf`
- For complete API documentation, see `doc/schott-coldvision-cv-ls-programming guide-en.pdf`
- 裝置規格與更多範例：https://www.schott.com/products/coldvision-fiber-optic-illumination/downloads
- Device specifications and more examples: https://www.schott.com/products/coldvision-fiber-optic-illumination/downloads
