# Changelog

## [0.2.0] - 2026-01-24

### Added
- Comprehensive protocol support for SkySafari 7 and Celestron SkyPortal connection.
- Handshake handlers for WiFi module (`0xB9`) commands `0x49`, `0x32`, `0x31`.
- Authentic multi-byte protocol responses for Battery (`0xB6`) and Charger (`0xB7`).
- New bitmask-based logging system with detailed protocol and connection categories.
- "Absolute Silence" strategy for non-simulated devices (Focuser, StarSense) to ensure protocol-correct timeouts.
- Preserved debugging test suite in `tests/debug/`.

### Changed
- Reorganized logging to be more standard and configurable.
- Updated motor controller handlers for better protocol compliance.
- Version number visible in TUI, WebUI, and logs.

## [0.1.0] - 2026-01-22

### Added
- Initial unified release of `caux-simulator`.
- Combined features from `auxdrv` and `indi-celestronaux` simulators.
- New `caux-sim` CLI entry point.
- Textual-based TUI for real-time monitoring.
- 3D Web Console using Three.js and FastAPI.
- Configurable imperfections (periodic error, backlash, cone error).
- Integration scanner script (`tests/integration_scan.py`).
- Standardized logging configuration.
- Comprehensive `pytest` suite.
