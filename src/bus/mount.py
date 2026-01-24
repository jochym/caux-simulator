"""
NexStar Mount Controller

Aggregates multiple AUX devices and handles high-level mount state and sky model.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from math import pi, sin, tan, radians
from collections import deque
from .aux_bus import AuxBus
from ..devices.motor import MotorController
from ..devices.power import PowerModule
from ..devices.wifi import WiFiModule
from ..devices.generic import GenericDevice

try:
    from ..nse_telescope import trg_names, cmd_names
except ImportError:
    from nse_telescope import trg_names, cmd_names  # type: ignore

logger = logging.getLogger(__name__)


class NexStarMount:
    """The simulated mount, containing the AUX bus and all simulated hardware."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sim_time = 0.0

        # Logging/UI State (Preserved for TUI compatibility)
        self.msg_log = deque(maxlen=10)
        self.cmd_log = deque(maxlen=30)

        def log_to_deque(src, dst, cmd):
            t_name = trg_names.get(dst, f"0x{dst:02x}")
            c_name = cmd_names.get(cmd, f"0x{cmd:02x}")
            self.cmd_log.append(f"{t_name}: {c_name}")

        self.bus = AuxBus(cmd_callback=log_to_deque)

        # 1. Initialize Motors
        self.azm_motor = MotorController(0x10, config)
        self.alt_motor = MotorController(0x11, config)
        self.bus.register_device(self.azm_motor)
        self.bus.register_device(self.alt_motor)

        # 2. Initialize Power
        self.bus.register_device(PowerModule(0xB6, config))  # BAT
        self.bus.register_device(PowerModule(0xB7, config))  # CHG

        # 3. Initialize WiFi
        self.bus.register_device(WiFiModule(0xB9, config))

        # 4. Initialize Core infrastructure
        self.bus.register_device(GenericDevice(0x01, (2, 0, 0, 0)))  # MB
        self.bus.register_device(GenericDevice(0xBF, (7, 11, 0, 0)))  # Lights

        # Sky Model Parameters
        imp = self.config.get("simulator", {}).get("imperfections", {})
        self.cone_error = imp.get("cone_error_arcmin", 0.0) / (360.0 * 60.0)
        self.non_perp = imp.get("non_perpendicularity_arcmin", 0.0) / (360.0 * 60.0)
        self.pe_amplitude = imp.get("periodic_error_arcsec", 0.0) / (360.0 * 3600.0)
        self.pe_period = imp.get("periodic_error_period_sec", 480.0)
        self.refraction_enabled = imp.get("refraction_enabled", False)
        self.clock_drift = imp.get("clock_drift", 0.0)

    def tick(self, dt: float) -> None:
        """Update simulation clock and propagate to all devices."""
        actual_dt = dt * (1.0 + self.clock_drift)
        self.sim_time += actual_dt
        self.bus.tick(actual_dt)

    def handle_msg(self, data: bytes) -> bytes:
        """Process incoming bytes and return responses."""
        # Note: cmd_log update should ideally happen inside the bus or devices
        # but kept here for now to maintain TUI state.
        return self.bus.handle_stream(data)

    def print_msg(self, msg: str) -> None:
        """Log a system message (for UI and logger)."""
        if not self.msg_log or msg != self.msg_log[-1]:
            self.msg_log.append(msg)
        logger.info(msg)

    def get_sky_altaz(self) -> Tuple[float, float]:
        """Calculates actual pointing position including imperfections."""
        sky_alt = self.alt_motor.pos
        sky_azm = self.azm_motor.pos

        # 1. Cone error
        sky_alt += self.cone_error

        # 2. Non-perpendicularity
        sky_azm += (
            self.non_perp * tan(radians(max(-80.0, min(80.0, sky_alt * 360.0)))) / 360.0
        )

        # 3. Periodic Error
        if self.pe_period > 0:
            sky_azm += self.pe_amplitude * sin(2 * pi * self.sim_time / self.pe_period)

        return sky_azm % 1.0, sky_alt
