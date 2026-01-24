# Architecture Refactoring Plan: Modular AUX Bus System

## Goal
Transition from the current monolithic `NexStarScope` class to a modular, bus-based architecture. This will improve maintainability, extensibility, and testing capabilities.

## Proposed Architecture

### 1. Core Components

#### `AuxBus` (Message Router)
The central nervous system of the simulator.
- **Responsibilities:**
  - Manages a registry of connected `AuxDevice` instances.
  - Handles the raw byte stream from the network interface.
  - Validates packet integrity (checksums).
  - Routes valid packets to the appropriate destination device ID.
  - Broadcasts global messages (device ID `0x00`).
  - Distributes simulation "ticks" (time updates) to all devices.

#### `AuxDevice` (Abstract Base Class)
The blueprint for all simulated components.
- **Attributes:**
  - `device_id` (e.g., `0x10`, `0xB0`)
  - `version` (Firmware version tuple)
- **Interface:**
  - `handle_command(sender_id, command_id, data) -> response_bytes`
  - `tick(dt)` (Update internal state, physics)
  - `get_version()` (Standard handler for `0xFE`)

### 2. Device Implementations

Logic currently mixed in `NexStarScope` will be extracted into specialized classes:

*   **`MotorController` (`0x10`, `0x11`)**
    *   **State:** Position (steps/degrees), Slew Rate, Tracking Mode, Backlash, Guide Rate.
    *   **Physics:** Inertia, acceleration, backlash compensation logic.
    *   **Commands:** `MC_MOVE_POS`, `MC_GOTO_FAST`, `MC_GET_POS_BACKLASH`, etc.

*   **`WiFiModule` (`0xB9`)**
    *   **State:** Network config, Connection status.
    *   **Logic:** Handling float-based location updates from apps like SkySafari.
    *   **Commands:** `WIFI_SET_LOCATION` (`0x31`), `0x32`, `0x49`.

*   **`GPSReceiver` (`0xB0`)**
    *   **State:** Lat/Lon, Time, Satellite info.
    *   **Commands:** `GPS_GET_LAT`, `GPS_GET_LONG`, `GPS_GET_TIME`.

*   **`HandController` (`0x04`)** & **`Focuser` (`0x12`)**
    *   Basic response handlers for presence checks.

### 3. File Structure

```
src/
├── nse_simulator.py      # Main entry point (Wiring everything together)
├── nse_logging.py        # Existing logging infrastructure
├── bus/
│   ├── __init__.py
│   ├── aux_bus.py        # AuxBus class implementation
│   └── utils.py          # Shared protocol helpers (checksum, packing)
└── devices/
    ├── __init__.py
    ├── base.py           # AuxDevice abstract class
    ├── motor.py          # MotorController class
    ├── wifi.py           # WiFiModule class
    ├── gps.py            # GPSReceiver class
    └── ...
```

## Migration Strategy

1.  **Preparation**: Move protocol helper functions (`make_checksum`, `pack_int3`, etc.) to `src/bus/utils.py`.
2.  **Foundation**: Implement `AuxBus` and `AuxDevice` base classes.
3.  **Incremental Porting**:
    *   Create `MotorController` and move physics logic from `NexStarScope`.
    *   Create `WiFiModule` and move the new handlers we just added.
    *   Create `GPSReceiver` and move GPS handlers.
4.  **Integration**: Update `nse_simulator.py` to instantiate `AuxBus` instead of `NexStarScope`.
5.  **Validation**: Use the existing test suite (`test_full_sky_safari.py`, etc.) to verify behavioral parity.

## Future Benefits

*   **Multi-Device Simulation**: Easily simulate a setup with 2 focusers, multiple switches, or custom DIY devices.
*   **Protocol Dialects**: Cleaner separation between devices using fixed-point (Motors) vs floating-point (WiFi) data formats.
*   **Unit Testing**: Ability to test the `MotorController` physics in isolation from the network layer.
