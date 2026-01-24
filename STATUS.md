# Project Status: SkySafari Connection Verified

## Working State (as of Jan 24, 2026)
The NexStar AUX Simulator has achieved a successful connection handshake with **SkySafari 7 (SS7)** and **Celestron SkyPortal**.

### **Key Solutions Implemented**

#### 1. Initial Handshake Handlers (WiFi Module)
SkySafari 7 performs a mandatory WiFi-to-Serial handshake with device `0xB9` (WiFly module) before initializing motor controllers. We implemented handlers for:
- `0x49`: Get Status (Returns `0x00`)
- `0x32`: Configuration (Returns `0x01`)
- `0x31`: Set Location (Returns `0x01`)

#### 2. Protocol Accuracy for Power Devices
Previously, motor commands (`0x10`, `0x18`) sent to the **Battery (`0xB6`)** and **Charger (`0xB7`)** were causing errors. We implemented:
- `0x10` (GET_VOLTAGE_STATUS): Returns 6 bytes of battery data.
- `0x18` (GET_CURRENT): Returns 2 bytes of current data.

#### 3. Handling of Non-Existent Devices (Silence Strategy)
To prevent SkySafari from trying to interact with accessories we don't simulate (e.g., Focuser `0x12`, StarSense `0xB4`), we implemented **Absolute Silence**:
- The simulator skips both the **echo** and the **response** for these IDs.
- **Effect**: Triggers a standard protocol timeout in SkySafari (3 retries * 3 seconds = 9 seconds per device).
- **Result**: Handshake completes successfully after the 18-second delay, and SkySafari correctly identifies the accessories as missing.

### **Current Simulated Device Support**
| Device ID | Name | Status |
|-----------|------|--------|
| `0x01` | Main Board | Active |
| `0x04/0x0D`| Hand Controller | Active |
| `0x10` | AZM Motor | Fully Functional |
| `0x11` | ALT Motor | Fully Functional |
| `0xB0` | GPS | Active |
| `0xB6` | Battery | Functional (Status/Current) |
| `0xB7` | Charger | Functional |
| `0xB9` | WiFi Module | Handshake Only |
| `0xBF` | Lights | Functional (Tray/Logo/WiFi) |

### **Known Issues / Limitations**
- **18s Handshake Delay**: Caused by SkySafari timeout waiting for Focuser and StarSense. This is the authentic behavior for a mount without these accessories.
- **WiFi Location Parsing**: Command `0x31` returns success but does not yet update the simulator's internal lat/lon (updates planned for refactoring).

## Maintenance & Debugging
- Detailed protocol logging is available via `--log-categories 7`.
- Verification tests (`tests/`) document the expected command sequences.
