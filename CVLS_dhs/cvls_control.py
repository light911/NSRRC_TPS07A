"""
SCHOTT ColdVision Light Source Control Library

This library provides a Python interface for controlling the SCHOTT ColdVision
Light Source (CV-LS) via the Legacy Protocol.

Author: Auto-generated
Date: 2026-03-15
"""

import socket
import time
from typing import Optional
from enum import IntEnum
import logsetup

try:
    import serial
except ImportError:
    serial = None


class Channel(IntEnum):
    """LED channel enumeration"""
    COMMON = 0  # All channels
    CHANNEL_1 = 1
    CHANNEL_2 = 2
    CHANNEL_3 = 3
    CHANNEL_4 = 4


class ConnectionType(IntEnum):
    """Connection type enumeration"""
    ETHERNET = 0
    USB = 1
    UART = 2


#The unit at 07A is an RGBW model (A20980/RGBW): channel 1 red, 2 green,
#3 blue, 4 white. Colours are exclusive, only one channel is ever enabled.
COLOR_ORDER = ('red', 'green', 'blue', 'white')
COLOR_CHANNEL = {
    'red':   Channel.CHANNEL_1,
    'green': Channel.CHANNEL_2,
    'blue':  Channel.CHANNEL_3,
    'white': Channel.CHANNEL_4,
}


class CVLSController:
    """
    Controller class for SCHOTT ColdVision Light Source

    Supports connection via Ethernet (Telnet), USB, or UART and provides
    methods to control LED channels, query device status, and manage settings.
    """

    def __init__(self, Par=None, Q=None,
                 connection_type: ConnectionType = ConnectionType.ETHERNET,
                 host: str = "10.7.1.111", port: int = 50811,
                 serial_port: Optional[str] = None, timeout: float = 2.0):
        """
        Initialize CV-LS controller

        Args:
            Par: EpicsDHS shared config dict; host/port come from Par['CVLS']
            Q: EpicsDHS queue dict (CVLSQ/reciveQ/sendQ)
            connection_type: Type of connection (ETHERNET, USB, or UART)
            host: IP address for Ethernet connection (default: 10.7.1.111)
            port: Port number for Ethernet connection (default: 50811)
            serial_port: Serial port path for USB/UART (e.g., '/dev/ttyUSB0', 'COM3')
            timeout: Communication timeout in seconds (default: 2.0)
        """
        self.Par = Par
        self.Q = Q
        self.max_power = 1000
        self.sendQ = Q['Queue']['sendQ'] if Q is not None else None
        self.epicsQ = Q['Queue']['epicsQ'] if Q is not None else None
        if Par is not None:
            host = Par['CVLS']['host']
            port = Par['CVLS']['commandprot']
            self.max_power = Par['CVLS'].get('max_power', 1000)
        self.connection_type = connection_type
        self.host = host
        self.port = port
        self.serial_port = serial_port
        self.timeout = timeout
        self.socket = None
        self.serial = None
        self.connected = False
        level = Par['Debuglevel'] if Par is not None else 'DEBUG'
        self.logger = logsetup.getloger2('CVLSController',LOG_FILENAME='/home/blctl/Desktop/log/CVLSControllerlog.txt',level = level,bypassline=False)
        self.logger.info("init CVLSController logging")
        self.connect()

    def connect(self) -> bool:
        """
        Establish connection to the CV-LS device

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.connection_type == ConnectionType.ETHERNET:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self.socket.connect((self.host, self.port))
                self.connected = True
                print(f"Connected to CV-LS at {self.host}:{self.port}")

            elif self.connection_type in [ConnectionType.USB, ConnectionType.UART]:
                if serial is None:
                    raise ImportError("pyserial library not installed. Install with: pip install pyserial")

                if not self.serial_port:
                    raise ValueError("Serial port must be specified for USB/UART connection")

                self.serial = serial.Serial(
                    port=self.serial_port,
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=self.timeout
                )
                self.connected = True
                print(f"Connected to CV-LS on {self.serial_port}")

            # Verify connection by querying product name
            product = self.get_product_name()
            if product:
                print(f"Device: {product}")
                #&L#,# and &I#,# are silently ignored while the driver is in
                #single channel mode, which would make colour selection look
                #like it worked and do nothing. Pin it to quad every connect.
                self.set_single_channel_mode(False)
                return True
            else:
                self.disconnect()
                return False

        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False
    def monitor(self,Que):
        """Main loop to keep connection alive and handle communication"""
        self.logger.warning('CVLSController MON start!')
        self.CommandQ = Que['Queue']['CVLSQ']
        self.reciveQ = Que['Queue']['reciveQ']
        self.sendQ = Que['Queue']['sendQ']
        self.epicsQ = Que['Queue']['epicsQ']
        #get the real state out before anyone asks, so backlight_status is never
        #left showing the placeholder from the dcss config file
        self.publish_status()

        while True:
            command = self.CommandQ.get()
            self.logger.info(f'CVLSController got str command: {command}')
            if isinstance(command,str):
                if command == "exit" :
                    self.logger.warning('CVLSController DHS Get Exit Command!')
                    self.exit()
                    break
                else:
                    self.logger.debug(f'CVLSController got str command: {command}')
                    pass
                    #may be from reviceQ (DCSS),update or move some thing for it
                    
            #from reviceQ (DCSS),update or move some thing for it
            elif isinstance(command,tuple):
                # self.HandleCommand(command)
                if command[0] == "setBackLightColor" :
                    # this is a op
                    self.set_back_light_color(command)
                elif command[0] == "switchSampleEnvironment" :
                    pass
                elif command[0] == "set_intensity" :
                    #internal request, not a dcss operation
                    self.set_intensity(command)
                elif command[0] == "report_status" :
                    #dcss (re)registered backlight_status and wants the live
                    #values, not the placeholder from the config file
                    self.publish_status()
                elif command[0] == "master_off" :
                    self.master_off()
                    self.publish_status()
                elif command[0] == "master_on" :
                    self.master_on()
                    self.publish_status()
                else:
                    self.logger.warning(f'CVLSController DHS Get undefine Command! {command}')
            else:
                self.logger.warning('CVLSController DHS Get undefine Command! {command}')

    # Back Light Operation (dcss setBackLightColor)

    def _intensity_to_power(self, intensity):
        """Map a 0-100 bluice intensity onto a raw 0-max_power channel power"""
        power = int(round(float(intensity) * self.max_power / 100.0))
        return max(0, min(power, 1000))

    def _power_to_intensity(self, power):
        """Inverse of _intensity_to_power, for reporting back to bluice"""
        if not self.max_power:
            return 0
        return int(round(float(power) * 100.0 / self.max_power))

    def _operation_done(self, opname, handle, *args):
        """Complete an operation normally, optionally echoing arguments back"""
        self.sendQ.put(('operdone', opname, handle) + tuple(str(a) for a in args))

    def _operation_failed(self, opname, handle, reason):
        """
        Complete an operation with a failed status.

        The 'operdone' route in EpicsDHS hardcodes the status to normal, so a
        real failure has to go out through the operation_completed route, which
        sends the status we pass here. Keep the reason to plain words, it is
        concatenated straight into the dcss message.
        """
        self.logger.warning(f'{opname} {handle} failed: {reason}')
        self.sendQ.put(
            ('updatevalue', opname, f'failed {reason}', 'operation_completed', handle))

    def read_state(self):
        """
        Read back what the light is actually doing.

        Returns (colour, intensity, master, powers), where colour names the one
        enabled channel ('off' when none are, 'mixed' if something outside this
        code turned on more than one), master is 'on'/'off' and powers holds the
        raw per-channel values in COLOR_ORDER. Returns None if the device does
        not answer, so callers can tell "dark" from "not talking to us".
        """
        master = self.get_output_enable(Channel.COMMON)
        if master is None:
            return None

        powers = []
        enabled = []
        for name in COLOR_ORDER:
            channel = COLOR_CHANNEL[name]
            power = self.get_output_power(channel)
            state = self.get_output_enable(channel)
            if power is None or state is None:
                return None
            powers.append(power)
            if state:
                enabled.append(name)

        if not enabled:
            colour = 'off'
        elif len(enabled) == 1:
            colour = enabled[0]
        else:
            colour = 'mixed'

        #intensity describes the live channel; with none lit there is no live
        #channel, so report the brightest one to keep the slider somewhere sane
        if colour in COLOR_CHANNEL:
            intensity = self._power_to_intensity(powers[COLOR_ORDER.index(colour)])
        else:
            intensity = self._power_to_intensity(max(powers))

        return colour, intensity, ('on' if master else 'off'), powers

    def publish_status(self):
        """
        Push backlight_status to dcss as
        "<colour> <intensity> <master> <red> <green> <blue> <white>"

        The four trailing fields are the per-colour intensities, so bluice can
        restore the slider to the level each colour was last used at instead of
        dragging one intensity across every colour change. They are intensities
        rather than raw power on purpose: max_power lives here, and bluice
        should not need a second copy of it to read this string.
        """
        state = self.read_state()
        if state is None:
            contents = 'unknown 0 disconnected 0 0 0 0'
        else:
            colour, intensity, master, powers = state
            per_colour = [str(self._power_to_intensity(p)) for p in powers]
            contents = '{} {} {} {}'.format(
                colour, intensity, master, ' '.join(per_colour))
        self.logger.debug(f'publish backlight_status: {contents}')
        self.sendQ.put(
            ('updatevalue', 'backlight_status', contents, 'string', 'normal'))

        #the CV-LS lives in its own process, so anything outside it (centerLoop
        #checking the light is white) reads the state from the shared Par dict
        if self.Par is not None:
            colour, intensity, master = contents.split()[0:3]
            self.Par['CVLS.color'] = colour
            self.Par['CVLS.intensity'] = int(intensity)
            self.Par['CVLS.master'] = master

    def apply_color(self, colour, intensity):
        """
        Drive the channels for a colour at an intensity, master enable untouched.

        Returns True when every command was acknowledged. Assumes the arguments
        have already been validated.
        """
        #The MD3 front light is white, so it follows the back light: a colour
        #other than white means a dark room experiment and the front light has
        #to go dark with it. Asked for first so it goes out promptly, and done
        #by the epics process because this one has no channel access.
        if self.epicsQ is not None:
            self.epicsQ.put(("set_front_light", 1 if colour == 'white' else 0))

        ok = True
        if colour == 'off':
            #leave the powers alone so each colour keeps the level it was last
            #used at when it is switched back on
            for name in COLOR_ORDER:
                ok &= self.set_output_enable(COLOR_CHANNEL[name], False)
            return ok

        channel = COLOR_CHANNEL[colour]
        ok &= self.set_output_power(channel, self._intensity_to_power(intensity))
        #drop the other colours before lighting this one so two are never on
        #together, even briefly
        for name in COLOR_ORDER:
            if name != colour:
                ok &= self.set_output_enable(COLOR_CHANNEL[name], False)
        ok &= self.set_output_enable(channel, True)
        return ok

    def set_intensity(self, command):
        """
        ('set_intensity', colour, intensity) -- the same effect as the operation
        but raised from inside the DHS, so there is no handle to report against.
        Used by centerLoop to force the auto center brightness.
        """
        try:
            colour = str(command[1]).strip().lower()
            intensity = float(command[2])
        except (IndexError, ValueError):
            self.logger.warning(f'CVLS bad set_intensity {command}')
            return
        if colour != 'off' and colour not in COLOR_CHANNEL:
            self.logger.warning(f'CVLS bad set_intensity colour {colour}')
            return
        if not 0 <= intensity <= 100:
            self.logger.warning(f'CVLS bad set_intensity level {intensity}')
            return

        self.logger.info(f'set_intensity {colour} {intensity}%')
        self.apply_color(colour, intensity)
        self.publish_status()

    def set_back_light_color(self, command):
        """
        setBackLightColor <colour> <intensity>

        colour is one of red/green/blue/white/off and intensity is 0-100, applied
        to the selected channel only. The master enable (&L0) is deliberately left
        alone: it follows the MD3 phase, so a colour and intensity picked here
        survive a phase change and come back with the light.

        command arrives as (opname, handle, colour, intensity) -- EpicsDHS strips
        the leading 'stoh_start_operation' before queueing it.
        """
        handle = command[1]
        try:
            colour = str(command[2]).strip().lower()
            intensity = float(command[3])
        except (IndexError, ValueError):
            self._operation_failed('setBackLightColor', handle,
                                   f'bad arguments {list(command[2:])}')
            return

        if colour != 'off' and colour not in COLOR_CHANNEL:
            self._operation_failed('setBackLightColor', handle,
                                   f'unknown colour {colour}')
            return
        if not 0 <= intensity <= 100:
            self._operation_failed('setBackLightColor', handle,
                                   f'intensity {intensity} outside 0-100')
            return

        self.logger.info(f'setBackLightColor {colour} {intensity}%')
        ok = self.apply_color(colour, intensity)

        if ok:
            self._operation_done('setBackLightColor', handle, colour, intensity)
        else:
            self._operation_failed('setBackLightColor', handle,
                                   'CV-LS did not answer')
        #report either way: on a partial failure the readback is what is true
        self.publish_status()

    def exit(self):
        """Clean shutdown for the monitor loop 'exit' command"""
        try:
            self.disconnect()
        except Exception as e:
            self.logger.warning(f'CVLS disconnect on exit fail: {e}')

    def disconnect(self):
        """Close connection to the CV-LS device"""
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.serial:
            self.serial.close()
            self.serial = None
        self.connected = False
        print("Disconnected from CV-LS")

    def _send_command(self, command: str) -> Optional[str]:
        """
        Send command to device and receive response

        Args:
            command: Command string without terminator

        Returns:
            Response string or None if error
        """
        if not self.connected:
            print("Not connected to device")
            return None

        try:
            # Add command start and terminator
            full_command = f"&{command}\r"

            if self.connection_type == ConnectionType.ETHERNET:
                self.socket.sendall(full_command.encode('ascii'))
                response = self.socket.recv(1024).decode('ascii').strip()

            else:  # USB or UART
                self.serial.write(full_command.encode('ascii'))
                self.serial.flush()
                time.sleep(0.05)  # Small delay for device processing
                response = self.serial.read(self.serial.in_waiting).decode('ascii').strip()

            # Check for negative acknowledgement
            if response.startswith('&n'):
                print(f"Device error: {response}")
                return None

            return response

        except Exception as e:
            print(f"Communication error: {e}")
            return None

    # Device Information Methods

    def get_product_name(self) -> Optional[str]:
        """Get product name"""
        response = self._send_command("Q")
        if response and response.startswith("&q"):
            return response[2:]
        return None

    def get_firmware_version(self) -> Optional[str]:
        """Get firmware version"""
        response = self._send_command("F?")
        if response and response.startswith("&f"):
            return response[2:]
        return None

    def get_serial_number(self) -> Optional[str]:
        """Get device serial number"""
        response = self._send_command("Z?")
        if response and response.startswith("&z"):
            return response[2:]
        return None

    def get_model_serial(self) -> Optional[str]:
        """Get device model and serial number"""
        response = self._send_command("ZF?")
        if response and response.startswith("&zf"):
            return response[3:]
        return None

    # LED Control Methods

    def set_output_enable(self, channel: Channel = Channel.COMMON, enable: bool = True) -> bool:
        """
        Enable or disable LED output

        Args:
            channel: Channel to control (COMMON or CHANNEL_1-4)
            enable: True to enable, False to disable

        Returns:
            True if successful
        """
        value = 1 if enable else 0
        response = self._send_command(f"L{channel},{value}")
        return response is not None

    def get_output_enable(self, channel: Channel = Channel.COMMON) -> Optional[bool]:
        """
        Query LED output enable status

        Args:
            channel: Channel to query

        Returns:
            True if enabled, False if disabled, None if error
        """
        response = self._send_command(f"L{channel},?")
        if response and response.startswith(f"&l{channel},"):
            value = response.split(',')[1]
            return value == '1'
        return None

    def set_output_power(self, channel: Channel = Channel.COMMON, power: int = 0) -> bool:
        """
        Set LED output power

        Args:
            channel: Channel to control (COMMON or CHANNEL_1-4)
            power: Power level (0-1000)

        Returns:
            True if successful
        """
        if not 0 <= power <= 1000:
            print("Power must be between 0 and 1000")
            return False

        response = self._send_command(f"I{channel},{power}")
        return response is not None

    def get_output_power(self, channel: Channel = Channel.COMMON) -> Optional[int]:
        """
        Query LED output power

        Args:
            channel: Channel to query

        Returns:
            Power level (0-1000) or None if error
        """
        response = self._send_command(f"I{channel},?")
        if response and response.startswith(f"&i{channel},"):
            try:
                power = int(response.split(',')[1])
                return power
            except ValueError:
                pass
        return None

    # Master Control Methods

    def master_on(self) -> bool:
        """
        Turn on master output (all channels)

        Returns:
            True if successful
        """
        ok = self.set_output_enable(Channel.COMMON, True)
        if ok:
            self.logger.info('CVLS master ON')
        else:
            self.logger.warning('CVLS master ON fail')
        return ok

    def master_off(self) -> bool:
        """
        Turn off master output (all channels)

        Returns:
            True if successful
        """
        ok = self.set_output_enable(Channel.COMMON, False)
        if ok:
            self.logger.info('CVLS master OFF')
        else:
            self.logger.warning('CVLS master OFF fail')
        return ok

    def set_all_channels_power(self, power: int) -> bool:
        """
        Set power for all channels simultaneously

        Args:
            power: Power level (0-1000)

        Returns:
            True if successful
        """
        return self.set_output_power(Channel.COMMON, power)

    def set_individual_powers(self, ch1: int = 0, ch2: int = 0,
                             ch3: int = 0, ch4: int = 0) -> bool:
        """
        Set individual channel powers

        Args:
            ch1: Channel 1 power (0-1000)
            ch2: Channel 2 power (0-1000)
            ch3: Channel 3 power (0-1000)
            ch4: Channel 4 power (0-1000)

        Returns:
            True if all successful
        """
        success = True
        success &= self.set_output_power(Channel.CHANNEL_1, ch1)
        success &= self.set_output_power(Channel.CHANNEL_2, ch2)
        success &= self.set_output_power(Channel.CHANNEL_3, ch3)
        success &= self.set_output_power(Channel.CHANNEL_4, ch4)
        return success

    # Status Query Methods

    def get_led_temperature(self) -> Optional[float]:
        """
        Get LED PCB temperature in Celsius

        Returns:
            Temperature in °C or None if error
        """
        response = self._send_command("?LT")
        if response and response.startswith("&?lt"):
            try:
                temp = float(response[4:])
                return temp
            except ValueError:
                pass
        return None

    def get_board_temperature(self) -> Optional[float]:
        """
        Get main board temperature in Celsius

        Returns:
            Temperature in °C or None if error
        """
        response = self._send_command("?BT")
        if response and response.startswith("&?bt"):
            try:
                temp = float(response[4:])
                return temp
            except ValueError:
                pass
        return None

    def get_input_voltage(self) -> Optional[float]:
        """
        Get input voltage

        Returns:
            Voltage in V or None if error
        """
        response = self._send_command("?VI")
        if response and response.startswith("&?vi"):
            try:
                voltage = float(response[4:])
                return voltage
            except ValueError:
                pass
        return None

    def get_fan_speed(self) -> Optional[int]:
        """
        Get fan speed in RPM

        Returns:
            Fan speed in RPM or None if error
        """
        response = self._send_command("?G")
        if response and response.startswith("&?g"):
            try:
                speed = int(response[3:])
                return speed
            except ValueError:
                pass
        return None

    def get_error_flags(self) -> Optional[int]:
        """
        Get system error flags

        Returns:
            Error flags as integer (Bit 0=Fan, Bit 1=LED Temp, Bit 8=Any Fault)
        """
        response = self._send_command("C?")
        if response and response.startswith("&c"):
            try:
                flags = int(response[2:])
                return flags
            except ValueError:
                pass
        return None

    def get_all_status(self) -> dict:
        """
        Get comprehensive device status

        Returns:
            Dictionary with all status information
        """
        status = {
            'product': self.get_product_name(),
            'firmware': self.get_firmware_version(),
            'serial': self.get_serial_number(),
            'led_temp': self.get_led_temperature(),
            'board_temp': self.get_board_temperature(),
            'input_voltage': self.get_input_voltage(),
            'fan_speed': self.get_fan_speed(),
            'error_flags': self.get_error_flags(),
            'master_enable': self.get_output_enable(Channel.COMMON),
            'common_power': self.get_output_power(Channel.COMMON),
            'ch1_enable': self.get_output_enable(Channel.CHANNEL_1),
            'ch1_power': self.get_output_power(Channel.CHANNEL_1),
            'ch2_enable': self.get_output_enable(Channel.CHANNEL_2),
            'ch2_power': self.get_output_power(Channel.CHANNEL_2),
            'ch3_enable': self.get_output_enable(Channel.CHANNEL_3),
            'ch3_power': self.get_output_power(Channel.CHANNEL_3),
            'ch4_enable': self.get_output_enable(Channel.CHANNEL_4),
            'ch4_power': self.get_output_power(Channel.CHANNEL_4),
        }
        return status

    # Settings Management

    def save_settings(self) -> bool:
        """
        Save current settings to non-volatile memory

        Returns:
            True if successful
        """
        response = self._send_command("S")
        return response is not None

    def restore_settings(self) -> bool:
        """
        Restore settings from non-volatile memory

        Returns:
            True if successful
        """
        response = self._send_command("T")
        return response is not None

    def factory_reset(self, preserve_network: bool = True) -> bool:
        """
        Restore factory defaults

        Args:
            preserve_network: If True, preserve network settings

        Returns:
            True if successful
        """
        command = "O2" if preserve_network else "O"
        response = self._send_command(command)
        return response is not None

    def reboot(self) -> bool:
        """
        Reboot the device

        Returns:
            True if command sent successfully
        """
        response = self._send_command("O4")
        if response:
            self.disconnect()
            return True
        return False

    # Continuous Strobe Control Methods

    def set_continuous_strobe_enable(self, enable: bool = True) -> bool:
        """
        Enable or disable continuous strobe mode

        Args:
            enable: True to enable, False to disable

        Returns:
            True if successful
        """
        value = 1 if enable else 0
        response = self._send_command(f"RM{value}")
        return response is not None

    def get_continuous_strobe_enable(self) -> Optional[bool]:
        """
        Query continuous strobe enable status

        Returns:
            True if enabled, False if disabled, None if error
        """
        response = self._send_command("RM?")
        if response and response.startswith("&rm"):
            return response[3:] == '1'
        return None

    def set_continuous_strobe_frequency(self, frequency: int) -> bool:
        """
        Set continuous strobe frequency

        Args:
            frequency: Frequency in Hz (6-20000)

        Returns:
            True if successful
        """
        if not 6 <= frequency <= 20000:
            print("Frequency must be between 6 and 20000 Hz")
            return False

        response = self._send_command(f"RF{frequency}")
        return response is not None

    def get_continuous_strobe_frequency(self) -> Optional[int]:
        """
        Query continuous strobe frequency

        Returns:
            Frequency in Hz or None if error
        """
        response = self._send_command("RF?")
        if response and response.startswith("&rf"):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    def set_continuous_strobe_duty_cycle(self, channel: Channel, duty_cycle: int) -> bool:
        """
        Set continuous strobe duty cycle for a channel

        Args:
            channel: Channel to control (CHANNEL_1-4)
            duty_cycle: Duty cycle (0-1000)

        Returns:
            True if successful
        """
        if not 0 <= duty_cycle <= 1000:
            print("Duty cycle must be between 0 and 1000")
            return False

        response = self._send_command(f"RD{channel},{duty_cycle}")
        return response is not None

    def get_continuous_strobe_duty_cycle(self, channel: Channel) -> Optional[int]:
        """
        Query continuous strobe duty cycle

        Args:
            channel: Channel to query

        Returns:
            Duty cycle (0-1000) or None if error
        """
        response = self._send_command(f"RD{channel},?")
        if response and response.startswith(f"&rd{channel},"):
            try:
                return int(response.split(',')[1])
            except (ValueError, IndexError):
                pass
        return None

    def set_continuous_strobe_phase_shift(self, channel: Channel, phase_shift: int) -> bool:
        """
        Set continuous strobe phase shift for a channel

        Args:
            channel: Channel to control (CHANNEL_1-4)
            phase_shift: Phase shift (0-1000)

        Returns:
            True if successful
        """
        if not 0 <= phase_shift <= 1000:
            print("Phase shift must be between 0 and 1000")
            return False

        response = self._send_command(f"RP{channel},{phase_shift}")
        return response is not None

    def get_continuous_strobe_phase_shift(self, channel: Channel) -> Optional[int]:
        """
        Query continuous strobe phase shift

        Args:
            channel: Channel to query

        Returns:
            Phase shift (0-1000) or None if error
        """
        response = self._send_command(f"RP{channel},?")
        if response and response.startswith(f"&rp{channel},"):
            try:
                return int(response.split(',')[1])
            except (ValueError, IndexError):
                pass
        return None

    # Triggered Strobe Control Methods

    def set_triggered_strobe_enable(self, enable: bool = True) -> bool:
        """
        Enable or disable triggered strobe mode

        Args:
            enable: True to enable, False to disable

        Returns:
            True if successful
        """
        value = 1 if enable else 0
        response = self._send_command(f"PM{value}")
        return response is not None

    def get_triggered_strobe_enable(self) -> Optional[bool]:
        """
        Query triggered strobe enable status

        Returns:
            True if enabled, False if disabled, None if error
        """
        response = self._send_command("PM?")
        if response and response.startswith("&pm"):
            return response[3:] == '1'
        return None

    def set_triggered_strobe_delay(self, channel: Channel, delay_us: int) -> bool:
        """
        Set triggered strobe delay for a channel

        Args:
            channel: Channel to control (CHANNEL_1-4)
            delay_us: Delay in microseconds (0-1000000)

        Returns:
            True if successful
        """
        if not 0 <= delay_us <= 1000000:
            print("Delay must be between 0 and 1000000 microseconds")
            return False

        response = self._send_command(f"PD{channel},{delay_us}")
        return response is not None

    def get_triggered_strobe_delay(self, channel: Channel) -> Optional[int]:
        """
        Query triggered strobe delay

        Args:
            channel: Channel to query

        Returns:
            Delay in microseconds or None if error
        """
        response = self._send_command(f"PD{channel},?")
        if response and response.startswith(f"&pd{channel},"):
            try:
                return int(response.split(',')[1])
            except (ValueError, IndexError):
                pass
        return None

    def set_triggered_strobe_on_time(self, channel: Channel, on_time_us: int) -> bool:
        """
        Set triggered strobe on time for a channel

        Args:
            channel: Channel to control (CHANNEL_1-4)
            on_time_us: On time in microseconds (0-1000000)

        Returns:
            True if successful
        """
        if not 0 <= on_time_us <= 1000000:
            print("On time must be between 0 and 1000000 microseconds")
            return False

        response = self._send_command(f"PO{channel},{on_time_us}")
        return response is not None

    def get_triggered_strobe_on_time(self, channel: Channel) -> Optional[int]:
        """
        Query triggered strobe on time

        Args:
            channel: Channel to query

        Returns:
            On time in microseconds or None if error
        """
        response = self._send_command(f"PO{channel},?")
        if response and response.startswith(f"&po{channel},"):
            try:
                return int(response.split(',')[1])
            except (ValueError, IndexError):
                pass
        return None

    def set_triggered_strobe_edge(self, channel: Channel, falling_edge: bool = False) -> bool:
        """
        Set triggered strobe trigger edge

        Args:
            channel: Channel to control (CHANNEL_1-4)
            falling_edge: True for falling edge, False for rising edge

        Returns:
            True if successful
        """
        value = 1 if falling_edge else 0
        response = self._send_command(f"PJ{channel},{value}")
        return response is not None

    def get_triggered_strobe_edge(self, channel: Channel) -> Optional[bool]:
        """
        Query triggered strobe trigger edge

        Args:
            channel: Channel to query

        Returns:
            True if falling edge, False if rising edge, None if error
        """
        response = self._send_command(f"PJ{channel},?")
        if response and response.startswith(f"&pj{channel},"):
            return response.split(',')[1] == '1'
        return None

    # Equalizer Control Methods

    def set_equalizer_enable(self, enable: bool = True) -> bool:
        """
        Enable or disable the light equalizer

        Args:
            enable: True to enable, False to disable

        Returns:
            True if successful
        """
        value = 1 if enable else 0
        response = self._send_command(f"E{value}")
        return response is not None

    def get_equalizer_enable(self) -> Optional[bool]:
        """
        Query equalizer enable status

        Returns:
            True if enabled, False if disabled, None if error
        """
        response = self._send_command("E?")
        if response and response.startswith("&e"):
            return response[2:] == '1'
        return None

    def set_equalizer_target(self, target: int) -> bool:
        """
        Set equalizer target light output value

        Args:
            target: Target value (0-4095, hex format)

        Returns:
            True if successful
        """
        if not 0 <= target <= 4095:
            print("Target must be between 0 and 4095")
            return False

        response = self._send_command(f"EE{target:03X}")
        return response is not None

    def get_equalizer_target(self) -> Optional[int]:
        """
        Query equalizer target value

        Returns:
            Target value or None if error
        """
        response = self._send_command("EE?")
        if response and response.startswith("&ee"):
            try:
                return int(response[3:], 16)
            except ValueError:
                pass
        return None

    def get_equalizer_current_output(self) -> Optional[int]:
        """
        Get current equalizer light feedback value (averaged)

        Returns:
            Current light output value or None if error
        """
        response = self._send_command("EV?")
        if response and response.startswith("&ev"):
            try:
                return int(response[3:], 16)
            except ValueError:
                pass
        return None

    def get_equalizer_power_output(self) -> Optional[int]:
        """
        Get current equalizer power output

        Returns:
            Power output value (0-4095) or None if error
        """
        response = self._send_command("ED?")
        if response and response.startswith("&ed"):
            try:
                return int(response[3:], 16)
            except ValueError:
                pass
        return None

    def get_equalizer_stability(self) -> Optional[int]:
        """
        Get equalizer stability status

        Returns:
            Stability status:
            0 = non stable
            1 = Locked (stable)
            2 = Waiting for delay to start
            4 = intensity low
            6 = intensity high
            8 = over range (intensity too low to maintain stability)
            10 = under range (intensity too high to maintain stability)
        """
        response = self._send_command("ES?")
        if response and response.startswith("&es"):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    def set_equalizer_startup_delay(self, delay_seconds: int) -> bool:
        """
        Set equalizer startup delay

        Args:
            delay_seconds: Delay in seconds (0-500)

        Returns:
            True if successful
        """
        if not 0 <= delay_seconds <= 500:
            print("Delay must be between 0 and 500 seconds")
            return False

        response = self._send_command(f"EI{delay_seconds:03d}")
        return response is not None

    def get_equalizer_startup_delay(self) -> Optional[int]:
        """
        Query equalizer startup delay

        Returns:
            Delay in seconds or None if error
        """
        response = self._send_command("EI?")
        if response and response.startswith("&ei"):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    # Network Configuration Methods

    def get_network_ip_static(self) -> Optional[str]:
        """
        Get static IP address

        Returns:
            IP address string or None if error
        """
        response = self._send_command("AIS?")
        if response and response.startswith("&ais"):
            # Convert from xxx:xxx:xxx:xxx to standard format
            ip = response[4:].replace(':', '.')
            return ip
        return None

    def set_network_ip_static(self, ip_address: str) -> bool:
        """
        Set static IP address

        Args:
            ip_address: IP address in standard format (e.g., "192.168.1.100")

        Returns:
            True if successful
        """
        response = self._send_command(f"AIS{ip_address}")
        return response is not None

    def get_network_dhcp(self) -> Optional[bool]:
        """
        Query DHCP enable status

        Returns:
            True if DHCP enabled, False if disabled, None if error
        """
        response = self._send_command("AM?")
        if response and response.startswith("&am"):
            return response[3:] == '1'
        return None

    def set_network_dhcp(self, enable: bool = True) -> bool:
        """
        Enable or disable DHCP

        Args:
            enable: True to enable DHCP, False to disable

        Returns:
            True if successful
        """
        value = 1 if enable else 0
        response = self._send_command(f"AM{value}")
        return response is not None

    def get_network_hostname(self) -> Optional[str]:
        """
        Get network hostname

        Returns:
            Hostname string or None if error
        """
        response = self._send_command("AH?")
        if response and response.startswith("&ah"):
            return response[3:]
        return None

    def set_network_hostname(self, hostname: str) -> bool:
        """
        Set network hostname

        Args:
            hostname: Hostname string (no spaces)

        Returns:
            True if successful
        """
        if ' ' in hostname:
            print("Hostname cannot contain spaces")
            return False

        response = self._send_command(f"AH{hostname}")
        return response is not None

    def get_network_subnet_mask(self) -> Optional[str]:
        """
        Get static subnet mask

        Returns:
            Subnet mask string or None if error
        """
        response = self._send_command("ASS?")
        if response and response.startswith("&ass"):
            mask = response[4:].replace(':', '.')
            return mask
        return None

    def set_network_subnet_mask(self, subnet_mask: str) -> bool:
        """
        Set static subnet mask

        Args:
            subnet_mask: Subnet mask in standard format (e.g., "255.255.255.0")

        Returns:
            True if successful
        """
        response = self._send_command(f"ASS{subnet_mask}")
        return response is not None

    def get_network_gateway(self) -> Optional[str]:
        """
        Get static gateway IP

        Returns:
            Gateway IP string or None if error
        """
        response = self._send_command("AGS?")
        if response and response.startswith("&ags"):
            gateway = response[4:].replace(':', '.')
            return gateway
        return None

    def set_network_gateway(self, gateway: str) -> bool:
        """
        Set static gateway IP

        Args:
            gateway: Gateway IP in standard format

        Returns:
            True if successful
        """
        response = self._send_command(f"AGS{gateway}")
        return response is not None

    # Advanced Control Methods

    def set_single_channel_mode(self, enable: bool = False) -> bool:
        """
        Set single or quad channel operation mode

        Args:
            enable: True for single channel mode, False for quad channel mode

        Returns:
            True if successful
        """
        value = 1 if enable else 0
        response = self._send_command(f"B{value}")
        return response is not None

    def get_single_channel_mode(self) -> Optional[bool]:
        """
        Query channel operation mode

        Returns:
            True if single channel, False if quad channel, None if error
        """
        response = self._send_command("B?")
        if response and response.startswith("&b"):
            return response[2:] == '1'
        return None

    def set_knob_mode(self, mode: int) -> bool:
        """
        Set front knob function mode

        Args:
            mode: 0=Common, 1-4=Channel 1-4, 5=Demo Mode

        Returns:
            True if successful
        """
        if not 0 <= mode <= 5:
            print("Mode must be between 0 and 5")
            return False

        response = self._send_command(f"N{mode}")
        return response is not None

    def get_knob_mode(self) -> Optional[int]:
        """
        Query front knob function mode

        Returns:
            Mode (0=Common, 1-4=Channel, 5=Demo) or None if error
        """
        response = self._send_command("N?")
        if response and response.startswith("&n"):
            try:
                return int(response[2:])
            except ValueError:
                pass
        return None

    def set_front_controls_lockout(self, locked: bool = True) -> bool:
        """
        Lock or unlock front panel controls (switch and knob)

        Args:
            locked: True to lock, False to unlock

        Returns:
            True if successful
        """
        value = 1 if locked else 0
        response = self._send_command(f"HLF{value}")
        return response is not None

    def get_front_controls_lockout(self) -> Optional[bool]:
        """
        Query front controls lockout status

        Returns:
            True if locked, False if unlocked, None if error
        """
        response = self._send_command("HLF?")
        if response and response.startswith("&hlf"):
            return response[4:] == '1'
        return None

    def set_multiport_lockout(self, locked: bool = True) -> bool:
        """
        Lock or unlock multiport analog controls

        Args:
            locked: True to lock, False to unlock

        Returns:
            True if successful
        """
        value = 1 if locked else 0
        response = self._send_command(f"HLM{value}")
        return response is not None

    def get_multiport_lockout(self) -> Optional[bool]:
        """
        Query multiport lockout status

        Returns:
            True if locked, False if unlocked, None if error
        """
        response = self._send_command("HLM?")
        if response and response.startswith("&hlm"):
            return response[4:] == '1'
        return None

    def get_light_feedback_raw(self) -> Optional[int]:
        """
        Get raw light feedback sensor value

        Returns:
            Raw sensor value (0-4096) or None if error
        """
        response = self._send_command("?I")
        if response and response.startswith("&?i"):
            try:
                return int(response[3:])
            except ValueError:
                pass
        return None

    # Context manager support

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False
