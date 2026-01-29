"""
Simulated GPS Receiver (0xB0).
"""

import logging
from typing import Dict, Any, List, Tuple, Union, Optional
from datetime import datetime, timezone
from .base import AuxDevice

logger = logging.getLogger(__name__)


class GPSReceiver(AuxDevice):
    """Simulates a Celestron GPS module."""

    def __init__(self, device_id: int, config: Dict[str, Any], version=(7, 11, 0, 0)):
        # Version 7.11
        super().__init__(device_id, version, config)

        obs_cfg = config.get("observer", {})

        # Convert degrees to [deg, min, sec, 0] format used by NexStar GPS protocol
        self.lat = self._dec_to_nexstar(float(obs_cfg.get("latitude", 50.0)))
        self.lon = self._dec_to_nexstar(float(obs_cfg.get("longitude", 20.0)))
        self.linked = True

        # Register GPS specific handlers
        self.handlers.update(
            {
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
            }
        )

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None

    def _dec_to_nexstar(self, deg: float) -> List[int]:
        d = abs(deg)
        dd = int(d)
        mm = int((d - dd) * 60)
        ss = int(((d - dd) * 60 - mm) * 60)
        return [dd, mm, ss, 0]

    def get_gps_lat(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes(self.lat)

    def get_gps_long(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes(self.lon)

    def set_gps_lat(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.lat = list(data)
        return b""

    def set_gps_long(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.lon = list(data)
        return b""

    def get_gps_time_valid(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01"

    def get_gps_linked(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01" if self.linked else b"\x00"

    def get_gps_sats(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x0c"

    def get_gps_time(self, data: bytes, snd: int, rcv: int) -> bytes:
        now = datetime.now(timezone.utc)
        return bytes([now.hour, now.minute, now.second])

    def set_gps_time(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b""

    def get_gps_date(self, data: bytes, snd: int, rcv: int) -> bytes:
        now = datetime.now(timezone.utc)
        return bytes([now.month, now.day, now.year % 100])

    def set_gps_date(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b""
