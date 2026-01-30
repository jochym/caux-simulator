# Implementation Plan: Time Synchronization via WiFi

This document outlines the steps to implement time and date synchronization between the client driver (e.g., SkySafari, INDI) and the simulator via the WiFi module (Device ID `0xB5`).

## 1. Goal
Automatically synchronize the simulator's internal clock and observer location when the driver sends synchronization commands. Location sync (`0x31`) is already partially implemented; Time sync (`0x30`) needs to be added.

## 2. Protocol Analysis (WiFi Module 0xB5)
The Celestron WiFi bridge (Evolution / SkyQLink) supports the following "Set" commands:
- **Command 0x30 (Set Time/Date)**:
    - **Payload**: 8 bytes `[SS, MM, HH, DD, MM, YY, Offset, DST]`
    - **Logic**: YY is Year-2000. Offset is timezone offset.
- **Command 0x31 (Set Location)**:
    - **Payload**: 8 bytes `[Lat_Float_LE, Lon_Float_LE]` (Implemented)

## 3. Implementation Steps

### 3.1. Extend `WiFiModule` (`src/caux_simulator/devices/wifi.py`)
- Register handler for command `0x30`.
- Parse the 8-byte payload.
- Calculate the `datetime` object in UTC.
- Store the time offset between system time and received time in the global `config` or pass it to `NexStarMount`.

### 3.2. Update `NexStarMount` Clock Logic (`src/caux_simulator/bus/mount.py`)
- Introduce a `time_offset` variable (default 0.0).
- Update `tick()` and time-dependent calculations to use `base_time + time_offset + sim_time`.

### 3.3. Unify Time Source
- Ensure `WebConsole` and `SimulatorApp` (TUI) use the synchronized time from `NexStarMount` for RA/Dec and LST calculations.

## 4. Verification
- Create a test script in `tests/protocol/test_sync.py`.
- Send a `0x31` packet with specific coordinates and verify RA/Dec updates.
- Send a `0x30` packet with a specific time and verify LST updates.
