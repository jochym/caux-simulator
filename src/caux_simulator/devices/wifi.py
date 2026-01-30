"""
Simulated WiFi Module (0xB5).
"""

import logging
from typing import Dict, Any, Optional
from .base import AuxDevice

logger = logging.getLogger(__name__)


class WiFiModule(AuxDevice):
    """Simulates the WiFly / Evolution WiFi bridge."""

    def __init__(self, device_id: int, config: Dict[str, Any], version=(2, 40, 0, 0)):
        # WiFly version 2.40
        super().__init__(device_id, version, config)

        # Register Handshake handlers
        self.handlers.update(
            {
                0x30: self.handle_set_time,
                0x31: self.handle_set_location,
                0x32: self.handle_config,
                0x49: self.handle_ping,
            }
        )

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None

    def handle_set_time(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x30 (Set Time/Date)."""
        from datetime import datetime, timezone, timedelta

        self.log_cmd(snd, "WIFI_SET_TIME", data)
        # Data format: [SS, MM, HH, DD, MM, YY, Offset, DST]
        if len(data) == 8:
            sec, minute, hour, day, month, year, offset, dst = data
            year += 2000

            # Offset is signed char (timezone offset from UTC)
            if offset > 127:
                offset -= 256

            try:
                # Calculate local time
                local_time = datetime(year, month, day, hour, minute, sec)
                # Adjust by offset and DST to get UTC
                # (Celestron protocol: UTC = LocalTime - (Offset + DST))
                utc_time = local_time - timedelta(hours=offset + dst)
                utc_time = utc_time.replace(tzinfo=timezone.utc)

                # Calculate offset from system clock
                now_utc = datetime.now(timezone.utc)
                time_diff = (utc_time - now_utc).total_seconds()

                logger.info(
                    f"WiFi received Time: {local_time} (UTC={utc_time}, offset={offset}, dst={dst})"
                )
                logger.info(f"System clock offset: {time_diff:.1f}s")

                if "observer" not in self.config:
                    self.config["observer"] = {}
                self.config["observer"]["time_offset"] = time_diff

            except Exception as e:
                logger.error(f"Error parsing WiFi time: {e}")

        return b"\x01"  # Success

    def handle_set_location(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x31 (Set Location)."""
        import struct

        self.log_cmd(snd, "WIFI_SET_LOCATION", data)
        # Data format is 2 floats (Little Endian): Latitude, Longitude
        if len(data) == 8:
            lat, lon = struct.unpack("<ff", data)
            logger.info(f"WiFi received Location: Lat={lat:.4f}, Lon={lon:.4f}")
            # Update the global config so NexStarMount/WebConsole can see it
            if "observer" not in self.config:
                self.config["observer"] = {}
            self.config["observer"]["latitude"] = lat
            self.config["observer"]["longitude"] = lon

        return b"\x01"  # Success

    def handle_config(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x32 (Config)."""
        self.log_cmd(snd, "WIFI_CONFIG", data)
        return b"\x01"  # Success

    def handle_ping(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x49 (Ping/Status)."""
        self.log_cmd(snd, "WIFI_PING", data)
        return b"\x00"  # Success
