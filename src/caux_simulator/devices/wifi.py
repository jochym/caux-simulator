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
        super().__init__(device_id, version)

        # Register Handshake handlers
        self.handlers.update(
            {
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

    def handle_set_location(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x31 (Set Location)."""
        self.log_cmd(snd, "WIFI_SET_LOCATION", data)
        return b"\x01"  # Success

    def handle_config(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x32 (Config)."""
        self.log_cmd(snd, "WIFI_CONFIG", data)
        return b"\x01"  # Success

    def handle_ping(self, data: bytes, snd: int, rcv: int) -> bytes:
        """WiFi command 0x49 (Ping/Status)."""
        self.log_cmd(snd, "WIFI_PING", data)
        return b"\x00"  # Success
