# Celestron AUX Mount Simulator (Unified)

This project provides a high-fidelity simulator for telescope mounts using the Celestron AUX binary protocol. It is designed for testing INDI drivers and planetarium software without requiring physical hardware.

It unifies several previous versions into a single, maintainable Python package.

## Features

- **Protocol Support**: Implementation of the Celestron AUX binary protocol (MC, HC, GPS, Focus, Power).
- **Physical Model**: Realistic simulation of motion with backlash, periodic error (PE), cone error, and non-perpendicularity.
- **Atmospheric Refraction**: Optional simulation of atmospheric refraction.
- **Modern TUI**: Interactive Text User Interface built with `Textual`.
- **Web Console**: 3D visualization of the mount using Three.js, including a schematic sky view.
- **Stellarium Support**: Built-in server for Stellarium telescope control protocol.
- **Configurable**: All parameters can be tuned via `config.toml`.

## Installation

Requires Python 3.11+.

### Minimal (for basic testing)
```bash
pip install .
```

### With TUI support
```bash
pip install .[tui]
```

### With Web Console support
```bash
pip install .[web]
```

## Usage

After installation, you can run the simulator using the `caux-sim` command:

```bash
# Headless mode (minimal dependencies)
caux-sim -t

# TUI mode (requires 'tui' extra)
caux-sim

# Web mode (requires 'web' extra)
caux-sim --web

# Enable debug logging to file
caux-sim --debug-log --debug-log-file my_debug.log
```

### Command Line Arguments

- `-t`, `--text`: Use headless mode (no TUI).
- `-p PORT`, `--port PORT`: AUX bus TCP port (default: 2000).
- `-s`, `--stellarium`: Enable Stellarium TCP server.
- `--stellarium-port PORT`: Stellarium TCP port (default: 10001).
- `--web`: Enable 3D Web Console (default: http://127.0.0.1:8080).
- `--perfect`: Disable all mechanical imperfections (backlash, PE, etc.).
- `-d`, `--debug`: Enable debug logging to console.
- `--debug-log`: Enable detailed debug logging to file.

## Configuration

You can override default settings by creating a `config.toml` file in your current working directory, or by using the `-c/--config` command-line argument. The simulator loads `config.default.toml` from the package and then merges it with your specified or local `config.toml`.

Example `config.toml`:
```toml
[observer]
latitude = 52.2297
longitude = 21.0122

[logging]
level = "DEBUG"
file = "simulator.log"
```

## Testing

The project includes a comprehensive test suite using `pytest`.

```bash
# Install development dependencies
pip install .[dev]

# Run tests
pytest
```

### Integration Scanning

A scanner script is provided to verify the simulator's availability and protocol compliance by scanning the virtual bus.

```bash
# Start the simulator in one terminal
caux-sim

# Run the scanner
python3 tests/integration_scan.py
```

This will report all discovered devices (Motor Controllers, Hand Controller, GPS, etc.) and their firmware versions.

## Architecture

The simulator consists of several components:
1.  **NSE Telescope (`nse_telescope.py`)**: The core physics and protocol engine.
2.  **NSE Simulator (`nse_simulator.py`)**: The networking layer and CLI entry point.
3.  **NSE TUI (`nse_tui.py`)**: The Textual-based terminal interface.
4.  **Web Console (`web_console.py`)**: The FastAPI/Three.js based 3D visualization.

## Supported Devices

The simulator emulates the following Celestron AUX devices:
- **Main Board (0x01)**
- **Hand Controller (0x04)**
- **Azimuth Motor (0x10)**: Supports GOTO, SLEW, Sync, Cordwrap
- **Altitude Motor (0x11)**: Supports GOTO, SLEW, Sync
- **GPS (0xB0)**: Provides location and time data
- **Battery (0xB6)**: Reports voltage and status
- **Lights (0xBF)**: Control for mount lighting
