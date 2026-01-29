# Developer Agent Prompt: Using Celestron AUX Simulator

You are tasked with developing or testing an INDI driver for Celestron AUX mounts. To facilitate this, you should use the `caux-simulator` package.

## 1. Environment Setup

The simulator is currently available as a local package. You must install it in your development environment.

### Option A: Install from source (Recommended for development)
If you have access to the simulator's source directory `/home/jochym/Projects/indi/caux-simulator`:
```bash
pip install -e "/home/jochym/Projects/indi/caux-simulator[tui,web]"
```

### Option B: Install from build
If you only have the wheel file:
```bash
pip install caux_simulator-0.1.0-py3-none-any.whl[tui,web]
```

## 2. Running the Simulator

Start the simulator in a separate terminal or as a background process. It listens on TCP port **2000** by default.

### Headless mode (Minimal dependencies, best for CI/automated tests)
```bash
caux-sim -t
```

### Interactive TUI mode (Best for manual debugging)
```bash
caux-sim
```

### 3D Web Console mode (Visualization)
```bash
caux-sim --web
```
Open `http://127.0.0.1:8080` in your browser to see the 3D model of the mount.

## 3. Configuring the Simulator

Create a `config.toml` in your working directory to override defaults (latitude, longitude, or mechanical imperfections).

Example `config.toml`:
```toml
[observer]
latitude = 50.0\nlongitude = 20.0

[simulator.imperfections]
backlash_steps = 100
periodic_error_arcsec = 20.0
```

## 4. Integration with INDI Driver

Configure your INDI driver to connect to `localhost` on port `2000`. The simulator implements the standard Celestron AUX binary protocol over TCP.

### Key Protocol Details for the Driver:
- **Device Discovery**: The simulator broadcasts UDP packets on port 55555.
- **Motor Controllers**: Responds at addresses `0x10` (AZM/RA) and `0x11` (ALT/DEC).
- **Hand Controller**: Emulated at `0x04`.
- **GPS**: Emulated at `0xB0`.
- **Supported Commands**: `MC_GET_POSITION`, `MC_GOTO_FAST`, `MC_SET_POSITION`, `MC_GET_MODEL`, `MC_MOVE_POS/NEG`, etc.

## 5. Verification

You can verify the simulator is responsive by running the included integration scanner:
```bash
python3 /home/jochym/Projects/indi/caux-simulator/tests/integration_scan.py
```
This will probe the virtual bus and report found devices.
