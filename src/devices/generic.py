"""
Simulated Generic Device (Main Board, Hand Controllers).
"""

from typing import Optional
from .base import AuxDevice


class GenericDevice(AuxDevice):
    """Simple device that only responds to GET_VER (0xFE)."""

    def __init__(self, device_id: int, version=(1, 0, 0, 0)):
        super().__init__(device_id, version)

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None
