# NexStar AUX Simulator: User Manual

This manual is for developers of Celestron AUX bus drivers (INDI, Indigo, SkySafari, etc.) who wish to test their code against a high-fidelity virtual mount.

## 1. Overview
The simulator mimics a NexStar Evolution mount on the AUX bus level. It supports both TCP and UDP discovery, allowing it to work seamlessly with SkySafari and other network-based controllers.

## 2. Getting Started

### Installation
```bash
pip install -e .
```

### Starting the Simulator
Run the simulator to listen on all network interfaces:
```bash
PYTHONPATH=src python3 -m caux_simulator.nse_simulator --text --port 2000
```

### Connection Details
- **Host**: Your machine's IP (or `127.0.0.1` for local tests)
- **Port**: `2000` (Default)
- **Protocol**: Celestron WiFi (NexStar AUX over TCP)

## 3. Supported Features
- **Axis Control**: 24-bit integer precision for AZM and ALT axes.
- **Device Profile**: Correctly identifies as a NexStar Evolution (Firmware 7.19.5130).
- **Movement**: Supports GOTO (Fast/Slow), Fixed-Rate slews (0-9), and Pulse Guiding.
- **Accessories**: Simulates Battery, Power/Charger, and Mount Lights.
- **Handshake**: Full compatibility with SkySafari 7 and SkyPortal connection sequences.

## 4. Testing Imperfections
The simulator can be configured to test driver robustness against non-perfect hardware:
- **`--perfect`**: Disables all mechanical and geometrical errors.
- **Geometrical Errors**: Configurable via `config.toml` (Cone Error, Non-Perpendicularity, Periodic Error).

## 5. Debugging Drivers
Use the categorized logging to see exactly what your driver is sending:
```bash
--log-categories 31  # Enable all logs (Connection, Protocol, Command, Motion, Device)
```
- **PROTOCOL**: Raw byte exchanges.
- **COMMAND**: Decoded AUX commands.
- **MOTION**: Real-time axis movement and GOTO status.
