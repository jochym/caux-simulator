"""
NexStar Telescope Emulation Core

This module provides the `NexStarScope` class which emulates the behavior
of a Celestron mount's Motor Controllers (MC) and other devices on the AUX bus.
It handles motion physics, command processing, and state management.
"""

import struct
import random
import logging
from math import pi, sin, radians, tan
from collections import deque
from typing import List, Tuple, Dict, Any, Optional, Union, Deque

try:
    from . import nse_logging as nselog
except ImportError:
    import nse_logging as nselog  # type: ignore

logger = logging.getLogger(__name__)

# ID tables from Celestron AUX Protocol
targets = {
    "ANY": 0x00,
    "MB": 0x01,  # Main Board
    "HC": 0x04,  # Hand Controller
    "UKN1": 0x05,
    "HC+": 0x0D,
    "AZM": 0x10,  # Azimuth / RA Motor
    "ALT": 0x11,  # Altitude / Dec Motor
    "APP": 0x20,  # Software Application
    "GPS": 0xB0,
    "UKN2": 0xB4,
    "WiFi": 0xB5,
    "BAT": 0xB6,
    "CHG": 0xB7,
    "LIGHT": 0xBF,
}
trg_names = {value: key for key, value in targets.items()}

commands = {
    "MC_GET_POSITION": 0x01,
    "MC_GOTO_FAST": 0x02,
    "MC_SET_POSITION": 0x04,
    "MC_GET_MODEL": 0x05,
    "MC_SET_POS_GUIDERATE": 0x06,
    "MC_SET_NEG_GUIDERATE": 0x07,
    "MC_LEVEL_START": 0x0B,
    "MC_SET_POS_BACKLASH": 0x10,
    "MC_SET_NEG_BACKLASH": 0x11,
    "MC_LEVEL_DONE": 0x12,
    "MC_SLEW_DONE": 0x13,
    "MC_GOTO_SLOW": 0x17,
    "MC_SEEK_DONE": 0x18,
    "MC_SEEK_INDEX": 0x19,
    "MC_SET_MAXRATE": 0x20,
    "MC_GET_MAXRATE": 0x21,
    "MC_ENABLE_MAXRATE": 0x22,
    "MC_MAXRATE_ENABLED": 0x23,
    "MC_MOVE_POS": 0x24,
    "MC_MOVE_NEG": 0x25,
    "MC_ENABLE_CORDWRAP": 0x38,
    "MC_DISABLE_CORDWRAP": 0x39,
    "MC_SET_CORDWRAP_POS": 0x3A,
    "MC_POLL_CORDWRAP": 0x3B,
    "MC_GET_CORDWRAP_POS": 0x3C,
    "MC_GET_POS_BACKLASH": 0x40,
    "MC_GET_NEG_BACKLASH": 0x41,
    "MC_GET_AUTOGUIDE_RATE": 0x47,
    "MC_GET_APPROACH": 0xFC,
    "MC_SET_APPROACH": 0xFD,
    "SIM_GET_SKY_POSITION": 0xFF,
    "GET_VER": 0xFE,
}
cmd_names = {value: key for key, value in commands.items()}

# Commands that trigger an immediate ACK (return same command)
ACK_CMDS = [0x02, 0x04, 0x06, 0x24]

# Slew rates mapping (index 0-9 to deg/sec)
RATES = {
    0: 0.0,
    1: 0.008 / 360,  # ~2x sidereal
    2: 0.017 / 360,  # ~4x sidereal
    3: 0.033 / 360,  # ~8x sidereal
    4: 0.067 / 360,  # ~16x sidereal
    5: 0.133 / 360,  # ~32x sidereal
    6: 0.5 / 360,  # 0.5 deg/s
    7: 1.0 / 360,  # 1.0 deg/s
    8: 2.0 / 360,  # 2.0 deg/s
    9: 4.0 / 360,  # 4.0 deg/s (Max for Evolution)
}


def decode_command(cmd: bytes) -> Tuple[int, int, int, int, bytes, int]:
    """Decodes a raw AUX packet into its components."""
    return (cmd[3], cmd[1], cmd[2], cmd[0], cmd[4:-1], cmd[-1])


def split_cmds(data: bytes) -> List[bytes]:
    """Splits a stream of bytes into individual AUX packets based on start byte ';'."""
    cmds = []
    b = 0
    while True:
        try:
            p = data.index(b";", b)
            length = abs(int(data[p + 1]))
            cmds.append(data[p + 1 : p + length + 3])
            b = p + length + 3
        except (ValueError, IndexError):
            return cmds


def make_checksum(data: bytes) -> int:
    """Calculates 2's complement checksum for AUX packet."""
    return (~sum([c for c in bytes(data)]) + 1) & 0xFF


def f2dms(f: float) -> Tuple[int, int, float]:
    """Converts fraction of rotation [0,1] to (Degrees, Minutes, Seconds)."""
    d = 360 * abs(f)
    dd = int(d)
    mm = int((d - dd) * 60)
    ss = (d - dd - mm / 60) * 3600
    return dd, mm, ss


def repr_angle(a: float, signed: bool = False) -> str:
    """Returns a string representation of an angle in DMS format."""
    deg = a * 360.0
    if signed:
        if deg > 180:
            deg -= 360.0
        elif deg < -180:
            deg += 360.0
    else:
        deg = deg % 360.0

    sign = "-" if deg < 0 else " "
    d = abs(deg)
    dd = int(d)
    mm = int((d - dd) * 60)
    ss = (d - dd - mm / 60) * 3600
    return "%s%03d°%02d'%04.1f\"" % (sign if signed else "", dd, mm, ss)


def pack_int3(f: float) -> bytes:
    """Packs a float [0,1] into 3 bytes big-endian (NexStar format)."""
    return struct.pack("!i", int((f % 1.0) * (2**24)))[1:]


def unpack_int3(d: bytes) -> float:
    """Unpacks up to 3 bytes into a float [0,1]."""
    if len(d) < 3:
        d = d.ljust(3, b"\x00")
    return struct.unpack("!i", b"\x00" + d[:3])[0] / 2**24


def unpack_int2(d: bytes) -> int:
    """Unpacks 2 bytes into an integer."""
    return struct.unpack("!i", b"\x00\x00" + d[:2])[0]


class NexStarScope:
    """
    Simulated NexStar Telescope Mount.

    Handles physics of movement, command handlers for motor controllers,
    and optional TUI display.
    """

    __mcfw_ver = (7, 11, 5100 // 256, 5100 % 256)
    __hcfw_ver = (5, 28, 5300 // 256, 5300 % 256)
    __mbfw_ver = (1, 0, 0, 1)

    def __init__(
        self,
        ALT: float = 0.0,
        AZM: float = 0.0,
        tui: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.tui = tui
        self.config = config or {}
        self.alt = ALT
        self.azm = AZM

        # Imperfections state
        imp = self.config.get("simulator", {}).get("imperfections", {})
        self.backlash_steps = imp.get("backlash_steps", 0)
        self.pe_amplitude = imp.get("periodic_error_arcsec", 0.0) / (360.0 * 3600.0)
        self.pe_period = imp.get("periodic_error_period_sec", 480.0)
        self.cone_error = imp.get("cone_error_arcmin", 0.0) / (360.0 * 60.0)
        self.non_perp = imp.get("non_perpendicularity_arcmin", 0.0) / (360.0 * 60.0)
        self.refraction_enabled = imp.get("refraction_enabled", False)
        self.jitter_sigma = imp.get("encoder_jitter_steps", 0) / 16777216.0
        self.clock_drift = imp.get("clock_drift", 0.0)  # e.g. 0.001 for 0.1% drift
        self.sim_time = 0.0

        # Backlash management
        self.azm_last_dir = 0  # 1 for pos, -1 for neg
        self.alt_last_dir = 0
        self.azm_backlash_rem = 0.0
        self.alt_backlash_rem = 0.0

        self.trg_alt = self.alt
        self.trg_azm = self.azm
        self.alt_rate = 0.0
        self.azm_rate = 0.0
        self.alt_approach = 0
        self.azm_approach = 0
        self.last_cmd = ""
        self.slewing = False
        self.guiding = False
        self.goto = False
        self.alt_guiderate = 0.0
        self.azm_guiderate = 0.0
        self.alt_maxrate = 10000  # 10.0 deg/s
        self.azm_maxrate = 10000
        self.use_maxrate = False

        self.cmd_log: Deque[str] = deque(maxlen=30)
        self.msg_log: Deque[str] = deque(maxlen=10)
        self.bat_current = 2468
        self.bat_voltage = 12345678
        self.lt_logo = 64
        self.lt_tray = 128
        self.lt_wifi = 255
        self.charge = False
        self.cordwrap = False
        self.cordwrap_pos = 0.0
        self.alt_min = -22.5 / 360.0  # Default limits for a typical mount
        self.alt_max = 90.0 / 360.0
        self.focus_pos = 100000
        self.gps_lat: Union[List[int], Tuple[int, ...]] = [50, 10, 56, 0]
        self.gps_lon: Union[List[int], Tuple[int, ...]] = [19, 47, 33, 0]
        self.gps_linked = True

        self._other_handlers = {
            0x10: self.cmd_0x10,
            0x18: self.cmd_0x18,
            0x31: self.wifi_cmd_0x31,  # Handle command 0x31 for WiFi device
            0x32: self.wifi_cmd_0x32,  # Handle command 0x32 for WiFi device
            0x3F: self.cmd_0x3f_handler,  # Handle command 0x3F only for supported devices
            0x49: self.wifi_cmd_0x49,  # Handle command 0x49 for WiFi device
            0xFE: self.fw_version,
        }
        self._mc_handlers = {
            0x01: self.get_position,
            0x02: self.goto_fast,
            0x04: self.set_position,
            0x05: self.get_model,
            0x06: self.set_pos_guiderate,
            0x07: self.set_neg_guiderate,
            0x0B: self.level_start,
            0x10: self.set_backlash,
            0x11: self.set_backlash,
            0x12: self.level_done,
            0x13: self.slew_done,
            0x17: self.goto_slow,
            0x18: self.seek_done,
            0x19: self.seek_index,
            0x20: self.set_maxrate,
            0x21: self.get_maxrate,
            0x22: self.enable_maxrate,
            0x23: self.maxrate_enabled,
            0x24: self.move_pos,
            0x25: self.move_neg,
            0x38: self.enable_cordwrap,
            0x39: self.disable_cordwrap,
            0x3A: self.set_cordwrap_pos,
            0x3B: self.get_cordwrap,
            0x3C: self.get_cordwrap_pos,
            0x40: self.get_backlash,
            0x41: self.get_backlash,
            0x47: self.get_autoguide_rate,
            0xFC: self.get_approach,
            0xFD: self.set_approach,
            0xFF: self.get_sky_position_aux,
            0xFE: self.fw_version,
        }
        self._focuser_handlers = {
            0x01: self.get_focus_position,
            0x02: self.goto_focus_fast,
            0xFE: self.fw_version,
        }
        self._gps_handlers = {
            0x01: self.get_gps_lat,
            0x02: self.get_gps_long,
            0x31: self.set_gps_lat,
            0x32: self.set_gps_long,
            0x33: self.get_gps_time,
            0x34: self.set_gps_time,
            0x36: self.get_gps_time_valid,
            0x37: self.get_gps_linked,
            0x38: self.get_gps_sats,
            0x3B: self.get_gps_date,
            0x3C: self.set_gps_date,
            0xFE: self.fw_version,
        }
        self._power_handlers = {
            0x01: self.get_pwr_voltage,
            0x02: self.get_pwr_current,
            0x03: self.get_pwr_status,
            0x10: self.motor_set_command_ack,  # MC_SET_POS_BACKLASH sent to BAT/CHG -> Ack
            0x18: self.motor_query_done_ack,  # MC_SEEK_DONE sent to BAT/CHG -> 0xFF (Done)
            0xFE: self.fw_version,
        }

    def set_maxrate(self, data: bytes, snd: int, rcv: int) -> bytes:
        if rcv == 0x11:
            self.alt_maxrate = unpack_int2(data)
        else:
            self.azm_maxrate = unpack_int2(data)
        return b""

    def get_maxrate(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes.fromhex("0fa01194")

    def enable_maxrate(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.use_maxrate = bool(data[0])
        return b""

    def maxrate_enabled(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01" if self.use_maxrate else b"\x00"

    def cmd_0x10(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Generic handler for 0x10 command (Lighting, Battery, Charging)."""
        if rcv == 0xBF:  # LIGHT
            if len(data) == 2:
                if data[0] == 0:
                    self.lt_tray = data[1]
                    nselog.log_device(logger, f"Set tray light to {self.lt_tray}")
                elif data[0] == 1:
                    self.lt_logo = data[1]
                    nselog.log_device(logger, f"Set logo light to {self.lt_logo}")
                else:
                    self.lt_wifi = data[1]
                    nselog.log_device(logger, f"Set wifi light to {self.lt_wifi}")
                return b""
            elif len(data) == 1:
                if data[0] == 0:
                    return bytes([int(self.lt_tray % 256)])
                elif data[0] == 1:
                    return bytes([int(self.lt_logo % 256)])
                else:
                    return bytes([int(self.lt_wifi % 256)])
        elif rcv == 0xB7:  # CHG
            if len(data):
                self.charge = bool(data[0])
                nselog.log_device(logger, f"Set charging state to {self.charge}")
                return b""
            else:
                return bytes([int(self.charge)])
        elif rcv == 0xB6:  # BAT
            self.bat_voltage = int(self.bat_voltage * 0.99)
            nselog.log_device(logger, f"Battery voltage: {self.bat_voltage / 1e6:.2f}V")
            return bytes.fromhex("0102") + struct.pack("!i", int(self.bat_voltage))
        return b""

    def cmd_0x18(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Generic handler for 0x18 command (Battery current)."""
        if rcv == 0xB6:  # BAT
            if len(data):
                i = data[0] * 256 + data[1]
                self.bat_current = max(2000, min(5000, i))
            return struct.pack("!i", int(self.bat_current))[-2:]
        return b""

    def wifi_cmd_0x31(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Handler for WiFi command 0x31."""
        nselog.log_command(
            logger, f"WIFI_CMD_0x31: from={snd:02x}, to={rcv:02x}, data={data.hex()}"
        )
        # Return a placeholder response to prevent hangs - actual response depends on implementation
        # Based on the data pattern 4248b732419e46aa, this might be a configuration request
        return b""  # Return empty Ack (consistent with other SET commands)

    def wifi_cmd_0x49(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Handler for WiFi command 0x49."""
        nselog.log_command(
            logger, f"WIFI_CMD_0x49: from={snd:02x}, to={rcv:02x}, data={data.hex()}"
        )
        # Return a placeholder response to prevent hangs - actual response depends on implementation
        return b"\x00"  # Return a simple acknowledgment

    def cmd_0x3f_handler(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Handler for command 0x3F that only responds to supported devices."""
        nselog.log_command(
            logger, f"CMD_0x3F: from={snd:02x}, to={rcv:02x}, data={data.hex()}"
        )
        # Only respond to devices that would reasonably support this command
        # Based on context and usage patterns
        if rcv == 0xB9:  # WiFi module - most likely recipient
            return b"\x01"  # Standard success response
        else:
            # Don't respond to other devices (e.g., StarSense 0xB4)
            nselog.log_command(
                logger, f"IGNORING 0x3F cmd to device 0x{rcv:02x}", logging.DEBUG
            )
            return b""

    def motor_set_command_ack(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Handler for motor SET commands (like 0x10) sent to power devices."""
        nselog.log_command(
            logger, f"MOTOR_SET_ACK: Command {snd:02x}->{rcv:02x}, data={data.hex()}"
        )
        return b""  # Return empty Ack

    def motor_query_done_ack(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Handler for motor DONE queries (like 0x18) sent to power devices."""
        nselog.log_command(
            logger, f"MOTOR_DONE_ACK: Command {snd:02x}->{rcv:02x}, data={data.hex()}"
        )
        return b"\xff"  # Return "Done" status

    def wifi_cmd_0x32(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Handler for WiFi command 0x32."""
        nselog.log_command(
            logger, f"WIFI_CMD_0x32: from={snd:02x}, to={rcv:02x}, data={data.hex()}"
        )
        # Return a placeholder response to prevent hangs - actual response depends on implementation
        # This might be a configuration/set command that returns status
        return b"\x01"  # Return success status

    def get_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Returns current MC position as 3-byte fraction with optional jitter."""
        pos = self.alt if rcv == 0x11 else self.azm
        if self.jitter_sigma > 0:
            pos += random.gauss(0, self.jitter_sigma)
        return pack_int3(pos)

    def get_sky_altaz(self) -> Tuple[float, float]:
        """
        Returns the actual pointing position in the sky (fraction of 360)
        considering mechanical and optical imperfections.
        """
        sky_alt = self.alt
        sky_azm = self.azm

        # 1. Cone error (Alt offset)
        sky_alt += self.cone_error

        # 2. Non-perpendicularity
        sky_azm += (
            self.non_perp
            * tan(radians(max(-80.0, min(80.0, self.alt * 360.0))))
            / 360.0
        )

        # 3. Periodic Error (RA/Azm only)
        if self.pe_period > 0:
            sky_azm += self.pe_amplitude * sin(2 * pi * self.sim_time / self.pe_period)

        # 4. Atmospheric Refraction (Approximate formula)
        if self.refraction_enabled:
            h = max(0.1, sky_alt * 360.0)
            from math import tan as mtan

            ref_arcmin = 1.0 / mtan(radians(h + 7.31 / (h + 4.4)))
            sky_alt += ref_arcmin / (60.0 * 360.0)

        return sky_azm % 1.0, sky_alt

    def goto_fast(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Starts a high-speed GOTO movement."""
        target_pos = unpack_int3(data)
        nselog.log_command(logger, f"GOTO_FAST: target={hex(rcv)} pos={target_pos:.6f}")
        nselog.log_motion(
            logger,
            f"Starting GOTO_FAST to {target_pos:.6f} on {'ALT' if rcv == 0x11 else 'AZM'}",
        )

        self.last_cmd = "GOTO_FAST"
        self.slewing = self.goto = True
        self.guiding = False
        self.alt_guiderate = self.azm_guiderate = 0.0
        r = (self.alt_maxrate if rcv == 0x11 else self.azm_maxrate) / (360e3)
        a = target_pos
        if rcv == 0x11:
            if a > 0.5:
                a -= 1.0
            self.trg_alt = a
            self.alt_rate = r if a > self.alt else -r
            nselog.log_motion(
                logger,
                f"ALT: current={self.alt:.6f} target={self.trg_alt:.6f} rate={self.alt_rate:.6f}",
            )
        else:
            self.trg_azm = a % 1.0
            diff = self.trg_azm - self.azm
            if diff > 0.5:
                diff -= 1.0
            if diff < -0.5:
                diff += 1.0
            self.azm_rate = r if diff > 0 else -r
            nselog.log_motion(
                logger,
                f"AZM: current={self.azm:.6f} target={self.trg_azm:.6f} rate={self.azm_rate:.6f}",
            )
        return b""

    def set_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Sets the internal MC position (Sync)."""
        a = unpack_int3(data)
        if rcv == 0x11:
            if a > 0.5:
                a -= 1.0
            self.alt = self.trg_alt = a
        else:
            self.azm = self.trg_azm = a % 1.0
        return b""

    def get_model(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Returns simulated mount model ID (Evolution)."""
        return bytes.fromhex("1687")

    def _set_guiderate(self, data: bytes, snd: int, rcv: int, factor: int) -> bytes:
        """Helper to set guiding rates."""
        val = unpack_int3(data) * (2**24)
        a = (val * factor) / (360.0 * 3600.0 * 1024.0)
        self.guiding = abs(a) > 0
        if rcv == 0x11:
            self.alt_guiderate = a
            nselog.log_motion(
                logger,
                f"Set ALT guide rate to {a:.9f} ({factor * val / 1024.0:.2f} arcsec/s)",
            )
        else:
            self.azm_guiderate = a
            nselog.log_motion(
                logger,
                f"Set AZM guide rate to {a:.9f} ({factor * val / 1024.0:.2f} arcsec/s)",
            )
        return b""

    def set_pos_guiderate(self, data: bytes, snd: int, rcv: int) -> bytes:
        return self._set_guiderate(data, snd, rcv, 1)

    def set_neg_guiderate(self, data: bytes, snd: int, rcv: int) -> bytes:
        return self._set_guiderate(data, snd, rcv, -1)

    def level_start(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Starts a leveling process (simplified to GOTO 0.0)."""
        self.last_cmd = "LEVEL_START"
        self.slewing = self.goto = True
        self.guiding = False
        r = 5.0 / 360
        if rcv == 0x11:
            self.trg_alt = 0.0
            self.alt_rate = -r if self.alt > 0 else r
        else:
            self.trg_azm = 0.0
            diff = -self.azm
            while diff > 0.5:
                diff -= 1.0
            while diff < -0.5:
                diff += 1.0
            self.azm_rate = r if diff > 0 else -r
        return b""

    def seek_index(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Starts a seek-index process (simplified to GOTO 0.0)."""
        self.last_cmd = "SEEK_INDEX"
        self.slewing = self.goto = True
        self.guiding = False
        r = 5.0 / 360
        if rcv == 0x11:
            self.trg_alt = 0.0
            self.alt_rate = -r if self.alt > 0 else r
        else:
            self.trg_azm = 0.0
            diff = -self.azm
            while diff > 0.5:
                diff -= 1.0
            while diff < -0.5:
                diff += 1.0
            self.azm_rate = r if diff > 0 else -r
        return b""

    def goto_slow(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Starts a low-speed precision GOTO movement."""
        self.last_cmd = "GOTO_SLOW"
        self.slewing = self.goto = True
        self.guiding = False
        r = 0.5 / 360
        a = unpack_int3(data)
        if rcv == 0x11:
            if a > 0.5:
                a -= 1.0
            self.trg_alt = a
            self.alt_rate = r if a > self.alt else -r
        else:
            self.trg_azm = a % 1.0
            diff = self.trg_azm - self.azm
            if diff > 0.5:
                diff -= 1.0
            if diff < -0.5:
                diff += 1.0
            self.azm_rate = r if diff > 0 else -r
        return b""

    def slew_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Checks if slew movement is finished."""
        rate = self.alt_rate if rcv == 0x11 else self.azm_rate
        eps = 1e-6 if self.last_cmd != "GOTO_FAST" else 1e-4
        return b"\x00" if abs(rate) > eps else b"\xff"

    def level_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Checks if level movement is finished."""
        done = abs(self.alt) < 0.01 / 360.0
        return b"\xff" if done else b"\x00"

    def seek_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Checks if seek movement is finished."""
        done = abs(self.azm) < 0.01 / 360.0
        return b"\xff" if done else b"\x00"

    def move_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Starts a constant-rate positive movement."""
        rate_idx = int(data[0])
        nselog.log_command(logger, f"MOVE_POS: target={hex(rcv)} rate_idx={rate_idx}")
        nselog.log_motion(
            logger,
            f"Starting positive movement on {'ALT' if rcv == 0x11 else 'AZM'} at rate {RATES.get(rate_idx, 0.0) * 360:.6f} deg/s",
        )

        self.last_cmd = "MOVE_POS"
        self.slewing = True
        self.goto = False
        r = RATES[rate_idx]
        if rcv == 0x11:
            self.alt_rate = r
        else:
            self.azm_rate = r
        return b""

    def move_neg(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Starts a constant-rate negative movement."""
        rate_idx = int(data[0])
        nselog.log_command(logger, f"MOVE_NEG: target={hex(rcv)} rate_idx={rate_idx}")
        nselog.log_motion(
            logger,
            f"Starting negative movement on {'ALT' if rcv == 0x11 else 'AZM'} at rate {-RATES.get(rate_idx, 0.0) * 360:.6f} deg/s",
        )

        self.last_cmd = "MOVE_NEG"
        self.slewing = True
        self.goto = False
        r = RATES[rate_idx]
        if rcv == 0x11:
            self.alt_rate = -r
        else:
            self.azm_rate = -r
        return b""

    def enable_cordwrap(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.cordwrap = True
        return b""

    def disable_cordwrap(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.cordwrap = False
        return b""

    def set_cordwrap_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.cordwrap_pos = unpack_int3(data)
        return b""

    def get_cordwrap(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\xff" if self.cordwrap else b"\x00"

    def get_cordwrap_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        return pack_int3(self.cordwrap_pos)

    def get_autoguide_rate(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Returns the autoguide rate setting."""
        nselog.log_command(
            logger, f"GET_AUTOGUIDE_RATE ({'ALT' if rcv == 0x11 else 'AZM'})"
        )
        # Return a standard value (e.g., 240 for 1x sidereal rate)
        return bytes([240])  # 240 corresponds to 1x sidereal rate

    def get_focus_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        return pack_int3(self.focus_pos / 16777216.0)

    def goto_focus_fast(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.focus_pos = int(unpack_int3(data) * 16777216.0)
        return b""

    def get_gps_lat(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes(self.gps_lat)

    def get_gps_long(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes(self.gps_lon)

    def set_gps_lat(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.gps_lat = list(data)
        return b""

    def set_gps_long(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.gps_lon = list(data)
        return b""

    def get_gps_time_valid(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01"

    def get_gps_linked(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01" if self.gps_linked else b"\x00"

    def get_gps_sats(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x0c"

    def get_gps_time(self, data: bytes, snd: int, rcv: int) -> bytes:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        return bytes([now.hour, now.minute, now.second])

    def set_gps_time(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b""

    def get_gps_date(self, data: bytes, snd: int, rcv: int) -> bytes:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        return bytes([now.month, now.day, now.year % 100])

    def set_gps_date(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b""

    def get_pwr_voltage(self, data: bytes, snd: int, rcv: int) -> bytes:
        return pack_int3(self.bat_voltage / 1000.0)

    def get_pwr_current(self, data: bytes, snd: int, rcv: int) -> bytes:
        current = 200.0
        if self.slewing:
            current += 1000.0
        return pack_int3(current)

    def get_pwr_status(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01" if self.charge else b"\x00"

    def get_approach(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes((self.alt_approach if rcv == 0x11 else self.azm_approach,))

    def set_approach(self, data: bytes, snd: int, rcv: int) -> bytes:
        if rcv == 0x11:
            self.alt_approach = data[0]
        else:
            self.azm_approach = data[0]
        return b""

    def get_backlash(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Returns the backlash compensation steps."""
        val = int(self.backlash_steps) & 0xFF
        nselog.log_command(
            logger, f"GET_BACKLASH ({'ALT' if rcv == 0x11 else 'AZM'}): {val}"
        )
        return bytes([val])

    def set_backlash(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Sets the backlash compensation steps."""
        if len(data) > 0:
            val = int(data[0])
            self.backlash_steps = val
            nselog.log_command(
                logger, f"SET_BACKLASH ({'ALT' if rcv == 0x11 else 'AZM'}): {val}"
            )
        return b""

    def get_sky_position_aux(self, data: bytes, snd: int, rcv: int) -> bytes:
        sky_azm, sky_alt = self.get_sky_altaz()
        pos = sky_alt if rcv == 0x11 else sky_azm
        return pack_int3(pos)

    def fw_version(self, data: bytes, snd: int, rcv: int) -> bytes:
        if rcv in (0x10, 0x11):
            return bytes(NexStarScope.__mcfw_ver)
        if rcv == 0x01:
            return bytes(NexStarScope.__mbfw_ver)
        if rcv in (0x04, 0x0D):
            return bytes(NexStarScope.__hcfw_ver)
        if rcv == 0xB9:  # WiFi Module
            return bytes(NexStarScope.__mcfw_ver)
        if rcv == 0xB6:  # Battery
            return bytes(NexStarScope.__mbfw_ver)
        if rcv == 0xB7:  # Charger
            return bytes(NexStarScope.__mbfw_ver)
        if rcv == 0xBF:  # Light controller
            return bytes(NexStarScope.__mcfw_ver)
        if rcv == 0xB0:  # GPS
            return bytes(NexStarScope.__mcfw_ver)
        # For unknown/unimplemented devices like StarSense (0xB4) or Focuser (0x12), return empty response
        return b""

    def tick(self, interval: float) -> None:
        """Physical model update called on every timer tick."""
        interval *= 1.0 + self.clock_drift
        self.sim_time += interval
        eps = 1e-6 if self.last_cmd != "GOTO_FAST" else 1e-4
        maxrate = 4.5 / 360.0

        # 1. Update Azm with backlash
        azm_move = (self.azm_rate + self.azm_guiderate) * interval
        if abs(azm_move) > 1e-15:
            move_dir = 1 if azm_move > 0 else -1
            if move_dir != self.azm_last_dir:
                self.azm_backlash_rem = float(self.backlash_steps) / 16777216.0
                self.azm_last_dir = move_dir
            if self.azm_backlash_rem > 0:
                consumed = min(abs(azm_move), self.azm_backlash_rem)
                self.azm_backlash_rem -= consumed
                if azm_move > 0:
                    azm_move = max(0.0, azm_move - consumed)
                else:
                    azm_move = min(0.0, azm_move + consumed)
        self.azm = (self.azm + azm_move) % 1.0

        # 2. Update Alt with backlash
        alt_move = (self.alt_rate + self.alt_guiderate) * interval
        if abs(alt_move) > 1e-15:
            move_dir = 1 if alt_move > 0 else -1
            if move_dir != self.alt_last_dir:
                self.alt_backlash_rem = float(self.backlash_steps) / 16777216.0
                self.alt_last_dir = move_dir
            if self.alt_backlash_rem > 0:
                consumed = min(abs(alt_move), self.alt_backlash_rem)
                self.alt_backlash_rem -= consumed
                if alt_move > 0:
                    alt_move = max(0.0, alt_move - consumed)
                else:
                    alt_move = min(0.0, alt_move + consumed)
        self.alt += alt_move

        if self.alt < self.alt_min:
            self.alt = self.alt_min
            if self.alt_rate < 0:
                self.alt_rate = 0.0
        elif self.alt > self.alt_max:
            self.alt = self.alt_max
            if self.alt_rate > 0:
                self.alt_rate = 0.0

        if self.slewing and self.goto:
            for axis in ["azm", "alt"]:
                cur = getattr(self, axis)
                trg = getattr(self, f"trg_{axis}")
                rate_attr = f"{axis}_rate"
                diff = trg - cur
                if axis == "azm":
                    if diff > 0.5:
                        diff -= 1.0
                    elif diff < -0.5:
                        diff += 1.0
                at_limit = False
                if axis == "alt":
                    if (cur <= self.alt_min + 1e-9 and trg < self.alt_min) or (
                        cur >= self.alt_max - 1e-9 and trg > self.alt_max
                    ):
                        at_limit = True
                if abs(diff) < eps or at_limit:
                    setattr(self, rate_attr, 0.0)
                else:
                    s = 1 if diff > 0 else -1
                    r = min(maxrate, abs(float(getattr(self, rate_attr))))
                    if r * interval >= abs(diff):
                        r = abs(diff) / interval
                    setattr(self, rate_attr, s * r)

        if abs(self.azm_rate) < eps and abs(self.alt_rate) < eps:
            self.slewing = self.goto = False

    def print_msg(self, msg: str) -> None:
        """Adds a message to the internal log deque and logs it."""
        if not self.msg_log or msg != self.msg_log[-1]:
            self.msg_log.append(msg)
        logger.info(msg)

    def handle_msg(self, msg: bytes) -> bytes:
        """Main entry point for incoming AUX data stream."""
        nselog.log_protocol(logger, f"RX: {msg.hex()} ({len(msg)} bytes)")

        responses = []
        for cmd in split_cmds(msg):
            try:
                c, f, t, l, d, s = decode_command(cmd)
                checksum_calc = make_checksum(cmd[:-1])

                if checksum_calc != s:
                    err_msg = f"Checksum error in cmd: {cmd.hex()} (expected {checksum_calc:02x}, got {s:02x})"
                    self.print_msg(err_msg)
                    nselog.log_protocol(logger, err_msg, logging.WARNING)
                    continue

                nselog.log_protocol(
                    logger,
                    f"Packet: len={l} src={f:02x} dst={t:02x} cmd={c:02x} data={d.hex()} chk={s:02x}",
                )

                echo = b";" + cmd
                responses.append(echo)

                c_name = cmd_names.get(c, f"0x{c:02x}")
                t_name = trg_names.get(t, f"0x{t:02x}")
                f_name = trg_names.get(f, f"0x{f:02x}")

                nselog.log_command(
                    logger, f"{f_name} -> {t_name}: {c_name} data={d.hex()}"
                )
                self.cmd_log.append(f"{t_name}: {c_name}")

                if t in (0x10, 0x11):
                    handlers = self._mc_handlers
                elif t == 0xB0:
                    handlers = self._gps_handlers
                elif t in (0xB6, 0xB7):
                    handlers = self._power_handlers
                elif t in (0x01, 0x04, 0x0D, 0xB9, 0xBF):
                    handlers = self._other_handlers
                else:
                    # Non-simulated devices (like Focuser 0x12, StarSense 0xB4)
                    handlers = {}

                if c in handlers:
                    resp_data = handlers[c](d, f, t)
                    header = bytes((len(resp_data) + 3, t, f, c))
                    resp_payload = (
                        b";"
                        + header
                        + resp_data
                        + bytes((make_checksum(header + resp_data),))
                    )
                    responses.append(resp_payload)
                    nselog.log_protocol(logger, f"TX response: {resp_payload.hex()}")
                    nselog.log_command(
                        logger,
                        f"{t_name} -> {f_name}: {c_name} response_data={resp_data.hex()}",
                    )
                else:
                    # Don't send any response for unsupported commands to maintain real behavior
                    nselog.log_command(
                        logger,
                        f"No handler for command {c_name} on device {t_name} - no response sent",
                        logging.DEBUG,
                    )
                    # Remove the echo for unsupported commands to match real behavior
                    # We'll remove the echo from responses if no handler exists
                    # Actually, let's keep echo but not add extra response
                    # The echo was already added earlier: responses.append(echo)

            except Exception as e:
                err_msg = f"Error handling cmd: {e}"
                self.print_msg(err_msg)
                logger.exception("Error handling AUX message")
                nselog.log_protocol(
                    logger, f"Exception processing {cmd.hex()}: {e}", logging.ERROR
                )

        full_response = b"".join(responses)
        if full_response:
            nselog.log_protocol(
                logger, f"TX: {full_response.hex()} ({len(full_response)} bytes)"
            )
        return full_response
