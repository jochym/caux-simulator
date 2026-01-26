"""
Base class for simulated AUX bus devices.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple

try:
    from .. import nse_logging as nselog
except ImportError:
    import nse_logging as nselog  # type: ignore

logger = logging.getLogger(__name__)


class AuxDevice(ABC):
    """Abstract base class for all simulated AUX devices."""

    def __init__(
        self, device_id: int, version: Tuple[int, int, int, int], config: Dict[str, Any]
    ):
        self.device_id = device_id
        self.version = version
        self.config = config
        self.handlers: Dict[int, Any] = {0xFE: self.handle_get_version}

    @abstractmethod
    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        """Process an incoming command and return response data payload or None."""
        pass

    def tick(self, interval: float) -> None:
        """Update internal state/physics based on time interval."""
        pass

    def handle_get_version(self, data: bytes, sender_id: int, rcv_id: int) -> bytes:
        """Standard GET_VER (0xFE) handler."""
        return bytes(self.version)

    def log_cmd(self, sender_id: int, cmd_name: str, data: bytes = b""):
        """Utility for consistent command logging."""
        nselog.log_command(
            logger,
            f"[{hex(self.device_id)}] RX from {hex(sender_id)}: {cmd_name} {data.hex() if data else ''}",
        )
