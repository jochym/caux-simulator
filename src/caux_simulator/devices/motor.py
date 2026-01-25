"""
Simulated Motor Controller (MC) for AZM and ALT axes.
"""

import random
import logging
from math import pi, sin, tan, radians
from typing import Tuple, Dict, Any, Optional
from .base import AuxDevice
from ..bus.utils import pack_int3, unpack_int3, unpack_int2

try:
    from .. import nse_logging as nselog
except ImportError:
    import nse_logging as nselog  # type: ignore

logger = logging.getLogger(__name__)

# Slew rates mapping (index 0-9 to fraction/sec)
RATES = {
    0: 0.0,
    1: 0.008 / 360,
    2: 0.017 / 360,
    3: 0.033 / 360,
    4: 0.067 / 360,
    5: 0.133 / 360,
    6: 0.5 / 360,
    7: 1.0 / 360,
    8: 2.0 / 360,
    9: 4.0 / 360,
}


class MotorController(AuxDevice):
    """Simulates an AZM or ALT motor controller."""

    def __init__(
        self, device_id: int, config: Dict[str, Any], initial_pos: float = 0.0
    ):
        # Version 7.11 (Standard for NexStar Evolution)
        super().__init__(device_id, (7, 11, 19, 236))

        self.pos = initial_pos
        self.trg_pos = initial_pos
        self.rate = 0.0
        self.guide_rate = 0.0
        self.max_rate = 10000 / 360000.0  # Default 10 deg/s in MC units
        self.use_maxrate = False
        self.approach = 0
        self.slewing = False
        self.goto = False
        self.last_cmd = ""

        # Backlash state
        imp = config.get("simulator", {}).get("imperfections", {})
        self.backlash_steps = imp.get("backlash_steps", 50)
        self.last_dir = 0
        self.backlash_rem = 0.0

        # Jitter
        self.jitter_sigma = imp.get("encoder_jitter_steps", 0) / 16777216.0

        # Register MC specific handlers
        self.handlers.update(
            {
                0x01: self.get_position,
                0x02: self.handle_goto_fast,
                0x04: self.set_position,
                0x05: self.get_model,
                0x06: self.set_pos_guiderate,
                0x07: self.set_neg_guiderate,
                0x13: self.get_slew_done,
                0x24: self.handle_move_pos,
                0x25: self.handle_move_neg,
                0x40: self.get_backlash,
                0x41: self.get_backlash,
                0x47: self.get_autoguide_rate,
                0xFC: self.get_approach,
                0xFD: self.set_approach,
            }
        )

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None  # Signal "not handled" to bus

    # --- MC Command Handlers ---

    def get_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        p = self.pos
        if self.jitter_sigma > 0:
            p += random.gauss(0, self.jitter_sigma)
        return pack_int3(p)

    def set_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.pos = self.trg_pos = unpack_int3(data)
        return b""

    def get_model(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes.fromhex("1687")  # Evolution

    def handle_goto_fast(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.trg_pos = unpack_int3(data)
        self.slewing = self.goto = True
        self.last_cmd = "GOTO_FAST"
        # Determine direction and set initial rate (simplified)
        diff = self.trg_pos - self.pos
        if rcv == 0x10:  # AZM wraps
            if diff > 0.5:
                diff -= 1.0
            elif diff < -0.5:
                diff += 1.0
        self.rate = self.max_rate if diff > 0 else -self.max_rate
        return b""

    def handle_move_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.rate = RATES.get(data[0], 0.0)
        self.slewing = abs(self.rate) > 0
        self.goto = False
        return b""

    def handle_move_neg(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.rate = -RATES.get(data[0], 0.0)
        self.slewing = abs(self.rate) > 0
        self.goto = False
        return b""

    def get_slew_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\xff" if not self.slewing else b"\x00"

    def get_backlash(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([int(self.backlash_steps) & 0xFF])

    def get_autoguide_rate(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([240])

    def get_approach(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([self.approach])

    def set_approach(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.approach = data[0]
        return b""

    def set_pos_guiderate(self, data: bytes, snd: int, rcv: int) -> bytes:
        val = unpack_int3(data) * (2**24)
        self.guide_rate = (val) / (360.0 * 3600.0 * 1024.0)
        return b""

    def set_neg_guiderate(self, data: bytes, snd: int, rcv: int) -> bytes:
        val = unpack_int3(data) * (2**24)
        self.guide_rate = -(val) / (360.0 * 3600.0 * 1024.0)
        return b""

    # --- Physics Tick ---

    def tick(self, interval: float) -> None:
        if not self.slewing and abs(self.guide_rate) < 1e-15:
            return

        # GOTO deceleration logic
        if self.goto:
            diff = self.trg_pos - self.pos
            if self.device_id == 0x10:
                if diff > 0.5:
                    diff -= 1.0
                elif diff < -0.5:
                    diff += 1.0

            # Slow down near target
            s = 1 if diff > 0 else -1
            r = abs(self.rate)
            if r * interval >= abs(diff):
                r = abs(diff) / interval
            self.rate = s * r

        move = (self.rate + self.guide_rate) * interval

        # Backlash Logic
        if abs(move) > 1e-15:
            move_dir = 1 if move > 0 else -1
            if move_dir != self.last_dir:
                self.backlash_rem = float(self.backlash_steps) / 16777216.0
                self.last_dir = move_dir

            if self.backlash_rem > 0:
                consumed = min(abs(move), self.backlash_rem)
                self.backlash_rem -= consumed
                if abs(move) <= consumed:
                    move = 0.0
                else:
                    move = (abs(move) - consumed) * (1 if move > 0 else -1)

        self.pos = self.pos + move
        if self.device_id == 0x10:  # AZM Wraps
            self.pos %= 1.0

        # GOTO completion check
        if self.goto:
            diff = self.trg_pos - self.pos
            if self.device_id == 0x10:
                if diff > 0.5:
                    diff -= 1.0
                elif diff < -0.5:
                    diff += 1.0

            if abs(diff) < 1e-7:
                self.pos = self.trg_pos
                self.rate = 0.0
                self.slewing = self.goto = False
