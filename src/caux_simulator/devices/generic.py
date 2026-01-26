"""
Generic/Empty device for the AUX bus.
"""

from typing import Optional, Dict, Any
from .base import AuxDevice


class GenericDevice(AuxDevice):
    """A device that responds to GET_VER but does nothing else."""

    def __init__(self, device_id: int, config: Dict[str, Any], version=(1, 0, 0, 0)):
        super().__init__(device_id, version, config)

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None
