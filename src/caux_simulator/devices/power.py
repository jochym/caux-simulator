"""
Simulated Power Module (Battery and Charger).
"""

import struct
import logging
from typing import Dict, Any, Optional
from .base import AuxDevice

logger = logging.getLogger(__name__)


class PowerModule(AuxDevice):
    """Simulates Battery (0xB6) and Charger (0xB7) devices."""

    def __init__(self, device_id: int, config: Dict[str, Any]):
        # Main board version 2.00
        super().__init__(device_id, (2, 0, 0, 0))

        self.voltage = 12345678  # microvolts
        self.current = 2468  # mA
        self.status = 0x02  # HIGH
        self.charging = False

        # Register Power specific handlers
        self.handlers.update(
            {
                0x01: self.get_voltage,
                0x02: self.get_current,
                0x03: self.get_status,
                0x10: self.handle_cmd_0x10,
                0x18: self.handle_cmd_0x18,
            }
        )

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None

    def get_voltage(self, data: bytes, snd: int, rcv: int) -> bytes:
        # Standard voltage query returns 3 bytes
        return struct.pack("!i", self.voltage // 1000)[1:]

    def get_current(self, data: bytes, snd: int, rcv: int) -> bytes:
        return struct.pack("!i", self.current)[2:]

    def get_status(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([1 if self.charging else 0])

    def handle_cmd_0x10(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Evolution-style Battery Status query (6 bytes)."""
        if rcv == 0xB6:  # BAT
            self.voltage = int(self.voltage * 0.999)  # Slow discharge
            # Response: [Charging, Status, Voltage(4 bytes)]
            return bytes([1 if self.charging else 0, self.status]) + struct.pack(
                "!i", self.voltage
            )
        elif rcv == 0xB7:  # CHG
            if len(data) > 0:
                self.charging = bool(data[0])
                return b""  # Ack
            return bytes([1 if self.charging else 0])
        return b""

    def handle_cmd_0x18(self, data: bytes, snd: int, rcv: int) -> bytes:
        """Evolution-style Current query (2 bytes)."""
        if rcv == 0xB6:  # BAT
            return struct.pack("!i", self.current)[2:]
        return b""
