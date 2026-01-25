# NexStar AUX Simulator: Architecture & Enhancement Guide

## 1. System Architecture

The simulator is built on a modular, event-driven architecture designed to decouple network handling, protocol parsing, and hardware physics.

### 1.1 Core Components

1.  **`nse_simulator.py` (Entry Point)**
    *   Initializes configuration, logging, and the asyncio event loop.
    *   Manages the TCP server (port 2000) and UDP broadcaster (port 55555).
    *   Dispatches incoming network data to the `NexStarMount`.

2.  **`NexStarMount` (Aggregator)**
    *   Acts as the top-level container for the simulated hardware.
    *   Holds the `AuxBus` instance and instantiates all `AuxDevice` objects (Motors, WiFi, Power).
    *   Maintains the high-level Sky Model (computing RA/Dec from AZM/ALT steps).

3.  **`AuxBus` (The Nervous System)**
    *   **Packet Parsing**: Validates checksums and structure of incoming bytes.
    *   **Routing**: Directs commands to specific devices based on Destination ID (`dst_id`).
    *   **Broadcasting**: Implements the AUX protocol requirement that all valid packets must be echoed back to the bus.
    *   **Silence Strategy**: Filters traffic to non-simulated devices (e.g., StarSense) to ensure accurate timeouts in client software.

4.  **`AuxDevice` (Hardware Abstraction)**
    *   Base class for all components.
    *   Standardizes `handle_command()`, `tick()`, and version reporting.

### 1.2 The Physics Engine (`MotorController`)

The motor controller implementation (`src/caux_simulator/devices/motor.py`) is the most complex component, designed for high fidelity.

*   **Integer Core**: Uses a 24-bit integer (`0` to `16,777,215`) to represent one full revolution of the axis. This avoids floating-point drift and matches the AUX protocol's native format.
*   **Time Step**: The `tick(dt)` method accumulates fractional movements (rate * time) into a float accumulator, but only whole steps are committed to the position register.
*   **GOTO Logic**: Implements a dedicated state machine for slewing:
    *   Calculates signed distance (handling 360-degree wrapping).
    *   Apply snap-to-target when within ±1 step.
    *   Enforces minimum anti-stall speeds.

---

## 2. Enhancement Guide

### 2.1 How to Add a New Device

To simulate a new accessory (e.g., a Focuser or Dew Heater):

1.  **Create the Class**:
    Create a new file in `src/caux_simulator/devices/` (e.g., `focuser.py`).
    ```python
    from .base import AuxDevice

    class Focuser(AuxDevice):
        def __init__(self, device_id, config):
            super().__init__(device_id, (5, 20, 0, 0)) # Firmware Version
            self.position = 30000
            
            # Register handlers
            self.handlers[0x01] = self.get_position
            self.handlers[0x17] = self.goto_position

        def get_position(self, data, snd, rcv):
            return pack_int3_raw(self.position)
            
        def goto_position(self, data, snd, rcv):
            self.position = unpack_int3_raw(data)
            return b"" # Ack
    ```

2.  **Register the Device**:
    In `src/caux_simulator/bus/mount.py`, inside `__init__`:
    ```python
    from ..devices.focuser import Focuser
    
    # ... inside __init__
    self.focuser = Focuser(0x12, config)
    self.bus.register_device(self.focuser)
    ```

### 2.2 How to Implement New Imperfections

Imperfections should be implemented in the `MotorController` physics loop or the `NexStarMount` sky model, depending on their nature.

*   **Mechanical (Backlash, PEC)**: Modify `MotorController.tick()`. Use the `gear_slack` state variable to decouple `self.steps` (encoder) from `self.sky_steps` (optic axis).
*   **Geometrical (Cone Error)**: Modify `NexStarMount.get_sky_altaz()`. Apply transformation matrices to the coordinates returned by the motors.

### 2.3 Debugging Protocol Issues

If a client (SkySafari, INDI) behaves unexpectedly:

1.  Enable full logging: `--log-categories 31`
2.  Look for `[PROTO]` logs to see raw bytes.
3.  Look for `Ignoring command to non-simulated device` warnings. If a client is querying a device you expect to work, ensure it is registered in `mount.py`.
