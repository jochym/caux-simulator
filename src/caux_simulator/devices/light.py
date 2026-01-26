"""
Simulated Light Controller (0xBF).
"""

import logging
from typing import Dict, Any, Optional
from .base import AuxDevice

logger = logging.getLogger(__name__)


class LightController(AuxDevice):
    """Simulates the mount lighting controller (Tray, WiFi, Logo)."""

    def __init__(self, device_id: int, config: Dict[str, Any], version=(7, 11, 0, 0)):
        # Version 7.11
        super().__init__(device_id, version, config)

        self.lt_tray = 128
        self.lt_wifi = 255
        self.lt_logo = 64

        # Register Light specific handlers
        self.handlers.update(
            {
                0x10: self.handle_cmd_0x10,
            }
        )

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None

    def handle_cmd_0x10(self, data: bytes, snd: int, rcv: int) -> bytes:
        """GET/SET_LEVEL for mount lights."""
        if len(data) == 2:
            # SET logic
            selector = data[0]
            level = data[1]
            if selector == 0:
                self.lt_tray = level
            elif selector == 1:
                self.lt_logo = level
            else:
                self.lt_wifi = level
            self.log_cmd(snd, f"SET_LIGHT({selector})", data[1:2])
            return b""  # Ack
        elif len(data) == 1:
            # GET logic
            selector = data[0]
            if selector == 0:
                val = self.lt_tray
            elif selector == 1:
                val = self.lt_logo
            else:
                val = self.lt_wifi
            return bytes([val])
        return b""
