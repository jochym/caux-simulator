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
from ..devices.gps import GPSReceiver
from ..devices.light import LightController
from ..devices.generic import GenericDevice

try:
    from ..nse_telescope import trg_names, cmd_names
except ImportError:
    from nse_telescope import trg_names, cmd_names  # type: ignore

logger = logging.getLogger(__name__)


class NexStarMount:
    """The simulated mount, containing the AUX bus and all simulated hardware."""

    def __init__(self, config: Dict[str, Any], hc_enabled: bool = False):
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

        # Evolution Mount Device Profile (Based on nsevo.log)
        # Note: Devices that do NOT respond in the real log are OMITTED.

        # 1. Motors - Version 7.19.5130 (0x141a = 5146, close enough or check if 5130 is 0x140a)
        # nsevo.log shows 7.19.5130
        self.azm_motor = MotorController(
            0x10,
            config,
            version=(7, 19, 20, 10),  # 20*256 + 10 = 5130
        )
        self.alt_motor = MotorController(0x11, config, version=(7, 19, 20, 10))
        self.bus.register_device(self.azm_motor)
        self.bus.register_device(self.alt_motor)

        # 2. WiFi - Version 0.0.256
        self.bus.register_device(WiFiModule(0xB5, config, version=(0, 0, 1, 0)))

        # 3. Power (Battery/Charger) - Version 1.1.16418 (0x4022 = 16418)
        self.bat_module = PowerModule(0xB6, config, version=(1, 1, 64, 34))
        self.chg_module = PowerModule(0xB7, config, version=(1, 1, 64, 34))
        self.bus.register_device(self.bat_module)
        self.bus.register_device(self.chg_module)

        # 4. Lights - Version 1.1.16418
        self.bus.register_device(LightController(0xBF, config, version=(1, 1, 64, 34)))

        # 5. Optional devices\n        if hc_enabled:\n            # NexStar+ HC - Version 5.35.3177 (0x0D)\n            # nsevo.log scan shows this version\n            self.bus.register_device(GenericDevice(0x0D, config, version=(5, 35, 12, 105))) # 12*256 + 105 = 3177\n\n        # GPS (0xB0), Main Board (0x01), and other HCs are SILENT in nsevo.log scan.\n
        # Sky Model Parameters
        imp = self.config.get("simulator", {}).get("imperfections", {})
        self.cone_error = imp.get("cone_error_arcmin", 0.0) / (360.0 * 60.0)
        self.non_perp = imp.get("non_perpendicularity_arcmin", 0.0) / (360.0 * 60.0)
        self.pe_amplitude = imp.get("periodic_error_arcsec", 0.0) / (360.0 * 3600.0)
        self.pe_period = imp.get("periodic_error_period_sec", 480.0)
        self.refraction_enabled = imp.get("refraction_enabled", False)
        self.clock_drift = imp.get("clock_drift", 0.0)

    # --- UI Compatibility Accessors ---

    @property
    def azm(self) -> float:
        return self.azm_motor.pos

    @azm.setter
    def azm(self, val: float):
        self.azm_motor.pos = val

    @property
    def alt(self) -> float:
        return self.alt_motor.pos

    @alt.setter
    def alt(self, val: float):
        self.alt_motor.pos = val

    @property
    def azm_rate(self) -> float:
        return self.azm_motor.rate

    @property
    def alt_rate(self) -> float:
        return self.alt_motor.rate

    @property
    def azm_guiderate(self) -> float:
        return self.azm_motor.guide_rate

    @property
    def alt_guiderate(self) -> float:
        return self.alt_motor.guide_rate

    @property
    def slewing(self) -> bool:
        return self.azm_motor.slewing or self.alt_motor.slewing

    @slewing.setter
    def slewing(self, val: bool):
        self.azm_motor.slewing = val
        self.alt_motor.slewing = val

    @property
    def goto(self) -> bool:
        return self.azm_motor.goto or self.alt_motor.goto

    @goto.setter
    def goto(self, val: bool):
        self.azm_motor.goto = val
        self.alt_motor.goto = val

    @property
    def trg_alt(self) -> float:
        return self.alt_motor.trg_pos

    @trg_alt.setter
    def trg_alt(self, val: float):
        self.alt_motor.trg_pos = val

    @property
    def trg_azm(self) -> float:
        return self.azm_motor.trg_pos

    @trg_azm.setter
    def trg_azm(self, val: float):
        self.azm_motor.trg_pos = val

    @property
    def guiding(self) -> bool:
        return (
            abs(self.azm_motor.guide_rate) > 1e-15
            or abs(self.alt_motor.guide_rate) > 1e-15
        )

    @property
    def bat_voltage(self) -> int:
        return self.bat_module.voltage

    @property
    def backlash_steps(self) -> int:
        return self.azm_motor.phys_backlash

    @property
    def jitter_sigma(self) -> float:
        return 0.0  # To be re-implemented with integer logic

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
        sky_alt = self.alt_motor.pointing_pos
        sky_azm = self.azm_motor.pointing_pos

        # 1. Cone error (Alt offset)
        sky_alt += self.cone_error

        # 2. Non-perpendicularity (Azm offset scaling with tan(alt))
        # Limit Alt to [-80, 80] to avoid tan() singularity
        safe_alt_deg = max(-80.0, min(80.0, self.alt_motor.pos * 360.0))
        sky_azm += self.non_perp * tan(radians(safe_alt_deg))

        # 3. Periodic Error (Azm/RA and Alt/Dec)
        if self.pe_period > 0:
            error = self.pe_amplitude * sin(2 * pi * self.sim_time / self.pe_period)
            sky_azm += error
            sky_alt += error

        # 4. Atmospheric Refraction (Approximate formula)
        if self.refraction_enabled:
            h = max(0.1, sky_alt * 360.0)
            # Bennett's formula for refraction in arcmin
            ref_arcmin = 1.0 / tan(radians(h + 7.31 / (h + 4.4)))
            sky_alt += ref_arcmin / (60.0 * 360.0)

        return sky_azm % 1.0, sky_alt
