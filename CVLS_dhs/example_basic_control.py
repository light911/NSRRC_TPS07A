#!/usr/bin/env python3
"""
Basic control example for SCHOTT ColdVision Light Source

This example demonstrates basic operations:
- Connecting to the device
- Controlling master on/off
- Setting channel power levels
- Querying device status
"""

from cvls_control import CVLSController, Channel, ConnectionType
import time


def main():
    # 創建控制器實例 (使用網路連接)
    # Create controller instance (using Ethernet connection)
    controller = CVLSController(
        connection_type=ConnectionType.ETHERNET,
        host="10.7.1.111",  # 您的設備IP / Your device IP
        port=50811,
        timeout=2.0
    )

    # 連接到設備 / Connect to device
    if not controller.connect():
        print("無法連接到設備 / Failed to connect to device")
        return

    try:
        # 1. 獲取設備資訊 / Get device information
        print("\n=== 設備資訊 / Device Information ===")
        print(f"產品名稱 / Product: {controller.get_product_name()}")
        print(f"韌體版本 / Firmware: {controller.get_firmware_version()}")
        print(f"序號 / Serial: {controller.get_serial_number()}")

        # 2. 開啟主開關 / Turn on master switch
        print("\n=== 開啟主開關 / Turning on master switch ===")
        controller.master_on()
        time.sleep(0.5)

        # 3. 設定所有通道亮度為50% / Set all channels to 50% brightness
        print("\n=== 設定所有通道亮度為50% / Setting all channels to 50% ===")
        controller.set_all_channels_power(500)  # 0-1000, so 500 = 50%
        time.sleep(2)

        # 4. 獨立控制各通道 / Control individual channels
        print("\n=== 獨立控制各通道 / Controlling individual channels ===")
        controller.set_individual_powers(
            ch1=250,   # 25%
            ch2=500,   # 50%
            ch3=750,   # 75%
            ch4=1000   # 100%
        )
        time.sleep(2)

        # 5. 開啟/關閉個別通道 / Enable/disable individual channels
        print("\n=== 控制個別通道開關 / Controlling individual channel switches ===")
        print("關閉通道1和3 / Disabling channels 1 and 3")
        controller.set_output_enable(Channel.CHANNEL_1, False)
        controller.set_output_enable(Channel.CHANNEL_3, False)
        time.sleep(2)

        print("重新開啟通道1和3 / Re-enabling channels 1 and 3")
        controller.set_output_enable(Channel.CHANNEL_1, True)
        controller.set_output_enable(Channel.CHANNEL_3, True)
        time.sleep(2)

        # 6. 查詢當前狀態 / Query current status
        print("\n=== 當前狀態 / Current Status ===")
        print(f"LED溫度 / LED Temperature: {controller.get_led_temperature():.1f}°C")
        print(f"主板溫度 / Board Temperature: {controller.get_board_temperature():.1f}°C")
        print(f"輸入電壓 / Input Voltage: {controller.get_input_voltage():.2f}V")
        print(f"風扇轉速 / Fan Speed: {controller.get_fan_speed()} RPM")

        # 查詢各通道功率 / Query channel powers
        print("\n通道功率 / Channel Powers:")
        for ch in range(1, 5):
            power = controller.get_output_power(Channel(ch))
            enabled = controller.get_output_enable(Channel(ch))
            status = "開啟 / ON" if enabled else "關閉 / OFF"
            print(f"  通道 / Channel {ch}: {power}/1000 ({status})")

        # 7. 漸變效果示範 / Fade effect demonstration
        print("\n=== 漸變效果示範 / Fade effect demonstration ===")
        print("從0%漸變到100% / Fading from 0% to 100%")
        for power in range(0, 1001, 100):
            controller.set_all_channels_power(power)
            print(f"  亮度 / Brightness: {power/10:.0f}%")
            time.sleep(0.3)

        print("從100%漸變到0% / Fading from 100% to 0%")
        for power in range(1000, -1, -100):
            controller.set_all_channels_power(power)
            print(f"  亮度 / Brightness: {power/10:.0f}%")
            time.sleep(0.3)

        # 8. 關閉主開關 / Turn off master switch
        print("\n=== 關閉主開關 / Turning off master switch ===")
        controller.master_off()

        # 9. 獲取完整狀態 / Get complete status
        print("\n=== 完整狀態資訊 / Complete Status Information ===")
        status = controller.get_all_status()
        for key, value in status.items():
            print(f"{key}: {value}")

    except KeyboardInterrupt:
        print("\n\n程式被中斷 / Program interrupted")

    finally:
        # 確保關閉連接 / Ensure connection is closed
        controller.disconnect()
        print("\n程式結束 / Program finished")


if __name__ == "__main__":
    main()
