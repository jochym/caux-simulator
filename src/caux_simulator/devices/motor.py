"""
Simulated Motor Controller (MC) for AZM and ALT axes.
"""

import logging
from decimal import Decimal, getcontext
from typing import Tuple, Dict, Any, Optional
from .base import AuxDevice
from ..bus.utils import pack_int3_raw, unpack_int3_raw, unpack_int2

try:
    from .. import nse_logging as nselog
except ImportError:
    import nse_logging as nselog  # type: ignore

logger = logging.getLogger(__name__)

# Set precision for decimal math
getcontext().prec = 28

# Steps per full revolution (24-bit resolution).
# Celestron motor controllers use a 24-bit integer to represent position.
# 2^24 = 16777216 steps = 360 degrees.
STEPS_PER_REV = 16777216

# Slew rates mapping (index 0-9 to steps/sec).
# These are standard NexStar slew rates.
# Index 9 is approx 4.0 deg/sec for high-speed GOTO/Manual slew.
RATES = {
    0: 0,
    1: 373,  # 0.008 deg/sec (~2x sidereal)
    2: 792,  # 0.017 deg/sec (~4x sidereal)
    3: 1537,  # 0.033 deg/sec (~8x sidereal)
    4: 3122,  # 0.067 deg/sec (~16x sidereal)
    5: 6198,  # 0.133 deg/sec (~32x sidereal)
    6: 23301,  # 0.5 deg/sec
    7: 46603,  # 1.0 deg/sec
    8: 93206,  # 2.0 deg/sec
    9: 186413,  # 4.0 deg/sec
}


class MotorController(AuxDevice):
    """Simulates an AZM or ALT motor controller using integer step counts."""

    def __init__(
        self,
        device_id: int,
        config: Dict[str, Any],
        initial_pos: float = 0.0,
        version: Tuple[int, int, int, int] = (7, 19, 20, 10),
    ):
        super().__init__(device_id, version, config)

        # Positions stored as 24-bit integers [0, 16777216)
        self.steps = int((initial_pos % 1.0) * STEPS_PER_REV)
        self.trg_steps = self.steps

        # Internal high-precision accumulator for sub-step movements
        self._step_accumulator = Decimal(0)

        self.rate_steps = Decimal(0)  # steps per second
        self.guide_rate_steps = Decimal(0)  # steps per second

        # Max rate (default 10 deg/s in MC units)
        # 10.0 deg/sec * (16777216 / 360) = 466033.77...
        self.max_rate_steps = Decimal(466033)
        self.use_maxrate = False
        self.approach = 0
        self.slewing = False
        self.goto = False
        self.last_cmd = ""
        self.goto_start_time = 0.0

        # Register MC specific handlers
        self.handlers.update(
            {
                0x01: self.get_position,
                0x02: self.handle_goto_fast,
                0x04: self.set_position,
                0x05: self.get_model,
                0x06: self.set_pos_guiderate,
                0x07: self.set_neg_guiderate,
                0x0B: self.handle_level_start,
                0x10: self.set_backlash,
                0x11: self.set_backlash,
                0x12: self.get_level_done,
                0x13: self.get_slew_done,
                0x17: self.handle_goto_slow,
                0x18: self.get_seek_done,
                0x19: self.handle_seek_index,
                0x20: self.handle_set_maxrate,
                0x21: self.get_maxrate,
                0x22: self.handle_enable_maxrate,
                0x23: self.get_maxrate_enabled,
                0x24: self.handle_move_pos,
                0x25: self.handle_move_neg,
                0x38: self.handle_enable_cordwrap,
                0x39: self.handle_disable_cordwrap,
                0x3A: self.handle_set_cordwrap_pos,
                0x3B: self.get_cordwrap_enabled,
                0x3C: self.get_cordwrap_pos,
                0x40: self.get_backlash,
                0x41: self.get_backlash,
                0x47: self.get_autoguide_rate,
                0xFC: self.get_approach,
                0xFD: self.set_approach,
                0xFF: self.get_position,
            }
        )

    @property
    def pos(self) -> float:
        """Returns position as fraction [0, 1] for external compatibility."""
        return float(self.steps) / STEPS_PER_REV

    @pos.setter
    def pos(self, val: float):
        """Sets position from fraction [0, 1]."""
        self.steps = int((val % 1.0) * STEPS_PER_REV)
        self.trg_steps = self.steps
        self._step_accumulator = Decimal(0)

    @property
    def trg_pos(self) -> float:
        return float(self.trg_steps) / STEPS_PER_REV

    @trg_pos.setter
    def trg_pos(self, val: float):
        self.trg_steps = int((val % 1.0) * STEPS_PER_REV)

    @property
    def rate(self) -> float:
        """Rate in fraction/sec."""
        return float(self.rate_steps) / STEPS_PER_REV

    @rate.setter
    def rate(self, val: float):
        self.rate_steps = Decimal(val) * STEPS_PER_REV

    @property
    def guide_rate(self) -> float:
        return float(self.guide_rate_steps) / STEPS_PER_REV

    @guide_rate.setter
    def guide_rate(self, val: float):
        self.guide_rate_steps = Decimal(val) * STEPS_PER_REV

    def handle_command(
        self, sender_id: int, command_id: int, data: bytes
    ) -> Optional[bytes]:
        if command_id in self.handlers:
            return self.handlers[command_id](data, sender_id, self.device_id)
        return None

    # --- MC Command Handlers ---

    def get_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        return pack_int3_raw(self.steps)

    def set_position(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.steps = self.trg_steps = unpack_int3_raw(data)
        self._step_accumulator = Decimal(0)
        return b""

    def get_model(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes.fromhex("1687")  # Evolution

    def handle_goto_fast(self, data: bytes, snd: int, rcv: int) -> bytes:
        new_trg = unpack_int3_raw(data)

        # Log transition if we were already in GOTO mode
        if self.goto and self.slewing:
            logger.debug(
                f"[0x{self.device_id:02x}] Transition: GOTO Re-asserted (Steps {self.steps} -> {new_trg})"
            )

        # Reset anti-stall timer for new movement
        if hasattr(self, "_goto_stuck_start"):
            del self._goto_stuck_start

        # Reset if new target is received, even if busy
        self.trg_steps = new_trg
        self.slewing = self.goto = True
        self.last_cmd = "GOTO_FAST"
        diff = self._get_diff()

        # High speed 4 deg/sec = 186411 steps/sec
        self.rate_steps = Decimal(186411) if diff > 0 else Decimal(-186411)
        self.log_cmd(snd, f"GOTO_FAST to steps={self.trg_steps}")
        return b""

    def handle_goto_slow(self, data: bytes, snd: int, rcv: int) -> bytes:
        new_trg = unpack_int3_raw(data)

        # Log transition from Fast to Slow
        if self.goto and self.slewing:
            logger.debug(
                f"[0x{self.device_id:02x}] Transition: FAST -> SLOW (Steps {self.steps} -> {new_trg})"
            )

        # Reset anti-stall timer for the slow phase
        if hasattr(self, "_goto_stuck_start"):
            del self._goto_stuck_start

        self.trg_steps = new_trg
        self.slewing = self.goto = True
        self.last_cmd = "GOTO_SLOW"
        diff = self._get_diff()

        # Slow rate 0.5 deg/sec = 23301 steps/sec
        r = Decimal(23301)
        self.rate_steps = r if diff > 0 else -r
        self.log_cmd(snd, f"GOTO_SLOW to steps={self.trg_steps}")
        return b""

    def handle_move_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.rate_steps = Decimal(RATES.get(data[0], 0))
        self.slewing = self.rate_steps > 0
        self.goto = False
        return b""

    def handle_move_neg(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.rate_steps = Decimal(-RATES.get(data[0], 0))
        self.slewing = self.rate_steps < 0
        self.goto = False
        return b""

    def get_slew_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\xff" if not self.slewing else b"\x00"

    def handle_level_start(self, data: bytes, snd: int, rcv: int) -> bytes:
        if hasattr(self, "_goto_stuck_start"):
            del self._goto_stuck_start
        self.trg_steps = 0
        self.slewing = self.goto = True
        self.rate_steps = Decimal(23300)  # 5 deg/sec
        return b""

    def get_level_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\xff" if self.steps == 0 else b"\x00"

    def handle_seek_index(self, data: bytes, snd: int, rcv: int) -> bytes:
        if hasattr(self, "_goto_stuck_start"):
            del self._goto_stuck_start
        self.trg_steps = 0
        self.slewing = self.goto = True
        self.rate_steps = Decimal(23300)
        return b""

    def get_seek_done(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\xff" if self.steps == 0 else b"\x00"

    def handle_set_maxrate(self, data: bytes, snd: int, rcv: int) -> bytes:
        val = unpack_int2(data)
        self.max_rate_steps = Decimal(val * STEPS_PER_REV) / Decimal(36000.0)
        return b""

    def get_maxrate(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes.fromhex("0fa01194")

    def handle_enable_maxrate(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.use_maxrate = bool(data[0])
        return b""

    def get_maxrate_enabled(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\x01" if self.use_maxrate else b"\x00"

    def handle_enable_cordwrap(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.cordwrap = True
        return b""

    def handle_disable_cordwrap(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.cordwrap = False
        return b""

    def handle_set_cordwrap_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.cordwrap_steps = unpack_int3_raw(data)
        return b""

    def get_cordwrap_enabled(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b"\xff" if hasattr(self, "cordwrap") and self.cordwrap else b"\x00"

    def get_cordwrap_pos(self, data: bytes, snd: int, rcv: int) -> bytes:
        return pack_int3_raw(getattr(self, "cordwrap_steps", 0))

    def get_backlash(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([0])

    def set_backlash(self, data: bytes, snd: int, rcv: int) -> bytes:
        return b""

    def get_autoguide_rate(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([240])

    def get_approach(self, data: bytes, snd: int, rcv: int) -> bytes:
        return bytes([self.approach])

    def set_approach(self, data: bytes, snd: int, rcv: int) -> bytes:
        self.approach = data[0]
        return b""

    def set_pos_guiderate(self, data: bytes, snd: int, rcv: int) -> bytes:
        # Scaling based on geometric analysis:
        # Logical unit for guiding commands is 1/1024 arcsec/sec.
        # Steps per arcsecond = 16777216 / (360 * 3600) = 16777216 / 1296000
        # Scaling Factor (Units -> Steps/sec) = (1/1024) * (16777216 / 1296000)
        # Factor = 16777216 / (1024 * 1296000) = 16777216 / 1327104000
        # Simplified Rational Factor = 128 / 10125
        # Steps/sec = Value * (128 / 10125)
        val = unpack_int3_raw(data)
        self.guide_rate_steps = (Decimal(val) * 128) / 10125
        return b""

    def set_neg_guiderate(self, data: bytes, snd: int, rcv: int) -> bytes:
        # Inverse of positive guiderate
        val = unpack_int3_raw(data)
        self.guide_rate_steps = -(Decimal(val) * 128) / 10125
        return b""

    def _get_diff(self) -> int:
        """Returns signed step difference to target, handling AZM wrap."""
        diff = self.trg_steps - self.steps
        if self.device_id == 0x10:  # AZM
            if diff > STEPS_PER_REV // 2:
                diff -= STEPS_PER_REV
            elif diff < -STEPS_PER_REV // 2:
                diff += STEPS_PER_REV
        return diff

    # --- Physics Tick ---

    def tick(self, interval: float) -> None:
        interval_dec = Decimal(str(interval))

        if not self.slewing and abs(self.guide_rate_steps) < Decimal("1e-10"):
            return

        if self.goto:
            diff = self._get_diff()

            # Completion check (integer precision)
            if abs(diff) <= 5:
                self.steps = self.trg_steps
                self.rate_steps = Decimal(0)
                self.slewing = self.goto = False
                self._step_accumulator = Decimal(0)
                logger.debug(
                    f"[0x{self.device_id:02x}] GOTO Finished at steps={self.steps}"
                )
                return

            # Deceleration / Speed Adjustment
            s = 1 if diff > 0 else -1
            r = abs(self.rate_steps)

            if r * interval_dec >= abs(diff):
                r = Decimal(abs(diff)) / interval_dec

            # Min speed to avoid stalling
            # Increase min speed to ensure completion logic triggers
            min_r = Decimal(500)
            if r < min_r:
                r = min_r

            # Anti-stall timeout check
            import time

            if not hasattr(self, "_goto_stuck_start"):
                self._goto_stuck_start = time.time()
            elif time.time() - self._goto_stuck_start > 5.0 and abs(diff) < 50:
                # Force finish if stuck near target for > 5s
                logger.warning(
                    f"[0x{self.device_id:02x}] GOTO Anti-Stall Triggered (Steps {self.steps} -> {self.trg_steps})"
                )
                self.steps = self.trg_steps
                self.rate_steps = Decimal(0)
                self.slewing = self.goto = False
                self._step_accumulator = Decimal(0)
                if hasattr(self, "_goto_stuck_start"):
                    del self._goto_stuck_start
                return

            self.rate_steps = s * r
        else:
            if hasattr(self, "_goto_stuck_start"):
                del self._goto_stuck_start

        # Accumulate whole steps from the rate (High Precision)
        move_dec = (self.rate_steps + self.guide_rate_steps) * interval_dec
        self._step_accumulator += move_dec

        # Immediate integer step application
        whole_steps = int(self._step_accumulator)
        if whole_steps != 0:
            self._step_accumulator -= Decimal(whole_steps)
            new_steps = self.steps + whole_steps
            if self.device_id == 0x10:  # AZM Wraps
                self.steps = new_steps % STEPS_PER_REV
            else:  # ALT does NOT wrap
                self.steps = max(0, min(STEPS_PER_REV - 1, new_steps))

        # Final check if GOTO reached target during normal move
        if self.goto:
            diff = self._get_diff()
            if abs(diff) <= 5:
                self.steps = self.trg_steps
                self.rate_steps = Decimal(0)
                self.slewing = self.goto = False
                self._step_accumulator = Decimal(0)
                logger.debug(
                    f"[0x{self.device_id:02x}] GOTO Finished at steps={self.steps}"
                )
