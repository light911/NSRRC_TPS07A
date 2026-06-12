# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a project for interfacing with the SCHOTT ColdVision Light Source (CV-LS), a programmable fiber-optic LED illumination device. The CV-LS supports remote control via multiple interfaces including Ethernet, USB, and UART using both Legacy and Binary protocols.

## Hardware Communication Protocol

The CV-LS device uses a Legacy Protocol with the following characteristics:

**Command Structure:**
- All commands start with `&` and end with `\r` (carriage return)
- Format: `&<command><value>\r`
- Query format: Use `?` to query current values (e.g., `&i?` to query LED power)
- The device discards all characters until receiving `&`, then processes on `\r`

**Connection Methods:**
- **Ethernet (Legacy Protocol):** Telnet on port 50811, IP 10.7.1.111 (static) or DHCP
- **Ethernet (Binary Protocol):** Port 5000, IP 10.7.1.111 (static) or DHC

**Error Handling:**
- Invalid command: `&nXpY` where X = valid chars, p = error position, Y = invalid char
- Invalid parameter: `&nXpYYY` where YYY = invalid parameter received

## Key Device Capabilities

**LED Control:**
- Up to 4 independent channels (or single channel mode)
- Power control: 0-1000 (decimal) or 0-0x7FF (hex)
- Output enable/disable per channel
- Front panel knob and switch control with lockout options

**Operating Modes:**
- **Continuous:** Constant illumination with power control
- **Continuous Strobe:** Internal trigger, 6-20000 Hz, adjustable duty cycle and phase shift
- **Triggered Strobe:** External trigger, microsecond precision delay and on-time control

**Advanced Features:**
- **Equalizer:** Maintains constant light output despite LED aging (with feedback sensor)
- **Temperature Monitoring:** Board and LED temperature sensors with status reporting
- **Multi-interface Control:** Front panel, Multiport analog/digital, network, USB, UART

## Common Command Examples

```python
# Query device identification
"&Q\r"          # Product name
"&F?\r"         # Firmware version
"&ZF?\r"        # Model:Serial number

# LED power control
"&I0,500\r"     # Set common power to 500 (0-1000)
"&I1,750\r"     # Set channel 1 power to 750
"&I0,?\r"       # Query common power setting

# LED enable/disable
"&L0,1\r"       # Enable common output
"&L1,0\r"       # Disable channel 1
"&L0,?\r"       # Query common enable status

# Temperature monitoring
"&?LT\r"        # Get LED PCB temperature (°C)
"&?BT\r"        # Get main board temperature (°C)

# Network configuration
"&AIS?\r"       # Query static IP address
"&AM?\r"        # Query DHCP status
"&AH<name>\r"   # Set hostname

# Settings persistence
"&S\r"          # Save current settings to non-volatile memory
"&T\r"          # Restore settings from non-volatile memory
"&O\r"          # Restore all factory defaults
"&O2\r"         # Restore factory defaults (preserve network settings)
"&O4\r"         # Reboot system
```

## Development Guidelines

**Protocol Implementation:**
- Always terminate commands with `\r`
- Parse responses starting from `&` character
- Implement timeout handling (device may not respond to invalid commands immediately)
- For query commands, parse the response format `&<cmd><value>`
- Handle negative acknowledgements (`&n`) for error reporting

**Connection Management:**
- For socket connections, only one client can connect at a time
- Use kick commands (`&ALK` for legacy, `&ABK` for binary) to forcefully disconnect users if needed
- Implement reconnection logic for network interruptions

**Value Formats:**
- Legacy commands often use hex values (e.g., `&I#` uses 0-FF)
- CV-LS commands use decimal values (e.g., `&I#,#` uses 0-1000)
- Temperature values are floating-point in Celsius
- Network addresses use "xxx:xxx:xxx:xxx" format in responses (also accepts standard dotted notation)

**State Management:**
- Settings are volatile unless explicitly saved with `&S`
- Query all relevant states on connection to synchronize with device
- Track which interface last modified settings using `&M?` command

## Testing and Debugging

**Verify Communication:**
```python
# Simple ping test
"&Q\r"  # Should return "&qSCHOTT ColdVision Light Source"

# Check system health
"&C?\r"     # Error flags (Bit 0=Fan, Bit 1=LED Temp, Bit 8=Any Fault)
"&?GS\r"    # Fan status
"&?LM\r"    # LED thermistor status (1=Good, 2=Warning, 3=Error)
```

**Common Pitfall:**
- Not all commands support the query format without `?` - check programming guide for backwards compatibility notes
- Some return values are zero-padded for backwards compatibility
- Channel numbers are 1-4 for individual channels, 0 for common/all channels

## Reference Documentation

Complete command reference and detailed specifications are in:
- `doc/schott-coldvision-cv-ls-programming guide-en.pdf`

For additional resources, firmware updates, and example code, visit:
- https://www.schott.com/products/coldvision-fiber-optic-illumination/downloads
