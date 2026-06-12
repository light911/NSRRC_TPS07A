#!/usr/bin/env python3
"""
Advanced features demonstration for SCHOTT ColdVision Light Source

This example demonstrates:
- Continuous strobe mode (internal trigger)
- Triggered strobe mode (external trigger)
- Equalizer control (constant light output)
- Network configuration
- Advanced settings
"""

from cvls_control import CVLSController, Channel, ConnectionType
import time


def demo_continuous_strobe(controller):
    """示範連續閃爍模式 / Demonstrate continuous strobe mode"""
    print("\n" + "="*60)
    print("=== 連續閃爍模式示範 / Continuous Strobe Mode Demo ===")
    print("="*60)

    # 開啟主開關
    controller.master_on()
    controller.set_all_channels_power(800)

    # 啟用連續閃爍
    print("\n啟用連續閃爍，10 Hz / Enable continuous strobe at 10 Hz")
    controller.set_continuous_strobe_enable(True)
    controller.set_continuous_strobe_frequency(10)  # 10 Hz

    # 設定各通道的工作週期（占空比）
    print("設定各通道工作週期 / Set duty cycle for each channel")
    controller.set_continuous_strobe_duty_cycle(Channel.CHANNEL_1, 250)   # 25%
    controller.set_continuous_strobe_duty_cycle(Channel.CHANNEL_2, 500)   # 50%
    controller.set_continuous_strobe_duty_cycle(Channel.CHANNEL_3, 750)   # 75%
    controller.set_continuous_strobe_duty_cycle(Channel.CHANNEL_4, 1000)  # 100%

    # 設定相位偏移（讓通道錯開閃爍）
    print("設定相位偏移 / Set phase shifts")
    controller.set_continuous_strobe_phase_shift(Channel.CHANNEL_1, 0)
    controller.set_continuous_strobe_phase_shift(Channel.CHANNEL_2, 250)
    controller.set_continuous_strobe_phase_shift(Channel.CHANNEL_3, 500)
    controller.set_continuous_strobe_phase_shift(Channel.CHANNEL_4, 750)

    print(f"閃爍頻率 / Strobe frequency: {controller.get_continuous_strobe_frequency()} Hz")
    print("閃爍運行中，持續 3 秒... / Strobing for 3 seconds...")
    time.sleep(3)

    # 關閉連續閃爍
    print("關閉連續閃爍 / Disable continuous strobe")
    controller.set_continuous_strobe_enable(False)


def demo_triggered_strobe(controller):
    """示範觸發閃爍模式 / Demonstrate triggered strobe mode"""
    print("\n" + "="*60)
    print("=== 觸發閃爍模式示範 / Triggered Strobe Mode Demo ===")
    print("="*60)

    controller.master_on()
    controller.set_all_channels_power(1000)

    # 啟用觸發閃爍
    print("\n配置觸發閃爍模式 / Configure triggered strobe mode")
    controller.set_triggered_strobe_enable(True)

    # 設定各通道的延遲時間（微秒）
    print("設定觸發延遲 / Set trigger delays")
    controller.set_triggered_strobe_delay(Channel.CHANNEL_1, 0)       # 0 µs
    controller.set_triggered_strobe_delay(Channel.CHANNEL_2, 1000)    # 1 ms
    controller.set_triggered_strobe_delay(Channel.CHANNEL_3, 2000)    # 2 ms
    controller.set_triggered_strobe_delay(Channel.CHANNEL_4, 3000)    # 3 ms

    # 設定各通道的開啟時間（微秒）
    print("設定開啟時間 / Set on times")
    controller.set_triggered_strobe_on_time(Channel.CHANNEL_1, 100)   # 100 µs
    controller.set_triggered_strobe_on_time(Channel.CHANNEL_2, 200)   # 200 µs
    controller.set_triggered_strobe_on_time(Channel.CHANNEL_3, 300)   # 300 µs
    controller.set_triggered_strobe_on_time(Channel.CHANNEL_4, 500)   # 500 µs

    # 設定觸發邊緣（上升沿或下降沿）
    print("設定觸發邊緣為上升沿 / Set trigger edge to rising")
    for ch in [Channel.CHANNEL_1, Channel.CHANNEL_2, Channel.CHANNEL_3, Channel.CHANNEL_4]:
        controller.set_triggered_strobe_edge(ch, falling_edge=False)

    print("\n觸發閃爍已配置 / Triggered strobe configured")
    print("等待外部觸發訊號... / Waiting for external trigger signal...")
    print("（注意：需要硬體觸發訊號才會實際閃爍）")
    print("(Note: Hardware trigger signal required for actual strobing)")
    time.sleep(2)

    # 關閉觸發閃爍
    print("關閉觸發閃爍 / Disable triggered strobe")
    controller.set_triggered_strobe_enable(False)


def demo_equalizer(controller):
    """示範均衡器控制 / Demonstrate equalizer control"""
    print("\n" + "="*60)
    print("=== 均衡器控制示範 / Equalizer Control Demo ===")
    print("="*60)

    controller.master_on()
    controller.set_all_channels_power(500)

    # 配置均衡器
    print("\n配置均衡器 / Configure equalizer")
    controller.set_equalizer_startup_delay(5)  # 5 秒啟動延遲
    controller.set_equalizer_target(2048)      # 目標值 2048 (中間值)

    # 啟用均衡器
    print("啟用均衡器 / Enable equalizer")
    controller.set_equalizer_enable(True)

    print(f"啟動延遲 / Startup delay: {controller.get_equalizer_startup_delay()} 秒")
    print(f"目標值 / Target value: {controller.get_equalizer_target()}")

    # 監控均衡器狀態
    print("\n監控均衡器狀態 10 秒... / Monitoring equalizer for 10 seconds...")
    for i in range(10):
        stability = controller.get_equalizer_stability()
        current_output = controller.get_equalizer_current_output()
        power_output = controller.get_equalizer_power_output()

        stability_text = {
            0: "不穩定 / Non-stable",
            1: "已鎖定 / Locked",
            2: "等待延遲 / Waiting",
            4: "強度過低 / Intensity low",
            6: "強度過高 / Intensity high",
            8: "超出範圍(低) / Over range (low)",
            10: "超出範圍(高) / Under range (high)"
        }.get(stability, f"未知 / Unknown ({stability})")

        print(f"  [{i+1}] 狀態/Status: {stability_text}, "
              f"當前輸出/Current: {current_output}, 功率/Power: {power_output}")
        time.sleep(1)

    # 關閉均衡器
    print("\n關閉均衡器 / Disable equalizer")
    controller.set_equalizer_enable(False)


def demo_network_settings(controller):
    """示範網路設定 / Demonstrate network settings"""
    print("\n" + "="*60)
    print("=== 網路設定查詢 / Network Settings Query ===")
    print("="*60)

    print(f"\n主機名 / Hostname: {controller.get_network_hostname()}")
    print(f"DHCP 啟用 / DHCP enabled: {controller.get_network_dhcp()}")
    print(f"靜態 IP / Static IP: {controller.get_network_ip_static()}")
    print(f"子網路遮罩 / Subnet mask: {controller.get_network_subnet_mask()}")
    print(f"閘道 / Gateway: {controller.get_network_gateway()}")

    print("\n注意：修改網路設定後需要重新啟動裝置")
    print("Note: Device reboot required after network settings change")

    # 示範如何修改主機名（不實際執行）
    # Example of changing hostname (not executed)
    # new_hostname = "CVLS_Lab01"
    # controller.set_network_hostname(new_hostname)
    # controller.save_settings()
    # controller.reboot()


def demo_advanced_controls(controller):
    """示範進階控制 / Demonstrate advanced controls"""
    print("\n" + "="*60)
    print("=== 進階控制設定 / Advanced Control Settings ===")
    print("="*60)

    # 查詢當前設定
    print("\n當前設定 / Current settings:")
    print(f"單通道模式 / Single channel mode: {controller.get_single_channel_mode()}")
    print(f"旋鈕模式 / Knob mode: {controller.get_knob_mode()}")
    print(f"前面板鎖定 / Front panel locked: {controller.get_front_controls_lockout()}")
    print(f"多埠鎖定 / Multiport locked: {controller.get_multiport_lockout()}")

    # 示範鎖定前面板控制
    print("\n鎖定前面板控制 / Lock front panel controls")
    controller.set_front_controls_lockout(True)
    print("前面板已鎖定 / Front panel locked")
    time.sleep(1)

    print("解鎖前面板控制 / Unlock front panel controls")
    controller.set_front_controls_lockout(False)
    print("前面板已解鎖 / Front panel unlocked")

    # 取得光感測器原始值
    raw_feedback = controller.get_light_feedback_raw()
    print(f"\n光感測器原始值 / Raw light feedback: {raw_feedback}")


def main():
    """主程式 / Main program"""
    print("="*60)
    print("SCHOTT ColdVision 進階功能示範")
    print("SCHOTT ColdVision Advanced Features Demo")
    print("="*60)

    # 創建控制器
    controller = CVLSController(
        connection_type=ConnectionType.ETHERNET,
        host="10.7.1.111",
        port=50811,
        timeout=2.0
    )

    # 連接到裝置
    if not controller.connect():
        print("無法連接到裝置 / Failed to connect to device")
        return

    try:
        # 顯示選單
        while True:
            print("\n" + "="*60)
            print("選擇示範項目 / Select demo:")
            print("="*60)
            print("1. 連續閃爍模式 / Continuous Strobe Mode")
            print("2. 觸發閃爍模式 / Triggered Strobe Mode")
            print("3. 均衡器控制 / Equalizer Control")
            print("4. 網路設定查詢 / Network Settings Query")
            print("5. 進階控制設定 / Advanced Control Settings")
            print("6. 全部示範 / All Demos")
            print("0. 離開 / Exit")
            print("="*60)

            choice = input("\n請選擇 / Enter choice (0-6): ").strip()

            if choice == '1':
                demo_continuous_strobe(controller)
            elif choice == '2':
                demo_triggered_strobe(controller)
            elif choice == '3':
                demo_equalizer(controller)
            elif choice == '4':
                demo_network_settings(controller)
            elif choice == '5':
                demo_advanced_controls(controller)
            elif choice == '6':
                demo_continuous_strobe(controller)
                time.sleep(1)
                demo_triggered_strobe(controller)
                time.sleep(1)
                demo_equalizer(controller)
                time.sleep(1)
                demo_network_settings(controller)
                time.sleep(1)
                demo_advanced_controls(controller)
            elif choice == '0':
                break
            else:
                print("無效選擇 / Invalid choice")

            # 確保關閉所有特殊模式
            controller.set_continuous_strobe_enable(False)
            controller.set_triggered_strobe_enable(False)
            controller.set_equalizer_enable(False)
            controller.master_off()

    except KeyboardInterrupt:
        print("\n\n程式被中斷 / Program interrupted")

    except Exception as e:
        print(f"\n錯誤 / Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 關閉所有特殊模式並斷開連接
        print("\n清理並關閉... / Cleaning up and closing...")
        controller.set_continuous_strobe_enable(False)
        controller.set_triggered_strobe_enable(False)
        controller.set_equalizer_enable(False)
        controller.master_off()
        controller.disconnect()
        print("程式結束 / Program finished")


if __name__ == "__main__":
    main()
