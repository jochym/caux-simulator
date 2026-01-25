# Changelog

## [0.2.0] - 2026-01-25
### Added
- High-fidelity 24-bit integer motor engine.
- NexStar Evolution device profile (Versions: Motors 7.19.5130, WiFi 0.0.256).
- Modular `AuxBus` and `AuxDevice` architecture.
- Categorized logging (Connection, Protocol, Command, Motion, Device).
- Integer-based GOTO completion and snapping logic.
- Comprehensive User and Developer manuals.

### Fixed
- SkySafari connection hanging due to StarSense accessory conflicts.
- GOTO commands failing to signal completion in the physics loop.
- Type errors in WiFi module initialization.
- Redundant and obsolete test scripts removed.

### Changed
- Refactored `MotorController` from float-based to integer-step-based.
- Improved "Absolute Silence" strategy for non-simulated devices.
