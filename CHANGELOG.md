## [0.2.16] - 2026-01-26
### Added
- Expanded `config.example.toml` with all adjustable geometry, imperfection, and observer settings.
- Restored default camera zoom to 15.0.

## [0.2.15] - 2026-01-26
### Fixed
- Web Console UI: Standardized all dashboard fonts to 1.3vw (increased readability).
- Web Console UI: Narrowed dashboard and optimized whitespace.
- Web Console UI: Corrected 3D camera distance (moved significantly back) to reduce model size.
- Web Console UI: Added third concentric circle (20 arcmin) to 1-degree FOV view.
- Stability: Hardened Star coordinate computation to prevent broadcast task crashes.

## [0.2.9] - 2026-01-26
### Fixed
- Stability: Hardened Web Console broadcast to prevent "Zero display" crashes.
- Tracking: Corrected sub-step accumulation logic to resolve subtle tracking drift.
- Time: Anchored virtual sky to simulation start date for perfect clock sync.
- Epoch: Switched to current epoch (real-time) to match SkySafari 7 default behavior.
- UI: Unified RA/Dec precision and restored dashboard font visibility.
- UI: Backed out default 3D camera for a better field of view.

## [0.2.8] - 2026-01-26
### Fixed
- Motor Engine: Refactored integer step application to eliminate sub-step rounding accumulation during tracking.
- Web Console: Anchored simulation time to a fixed start date to prevent time-drift in sky model.
- Web Console UI: Unified precision for RA/Dec/LST (1 decimal place for seconds).
- Web Console UI: Added dynamic Geographic Location (GEO) display synced from SkySafari.
- Web Console UI: Increased velocity precision to 4 decimal places ("/s").
- Web Console UI: Added more bright stars (Regulus, Aldebaran, Fomalhaut) and adjusted default camera zoom.

## [0.2.7] - 2026-01-26
### Fixed
- Web Console UI: Restored state broadcast by adding robust attribute checks for RA/Dec/LST objects.
- Web Console UI: Reduced horizontal space consumption and further decreased font size.
- Web Console UI: Standardized precision for RA/Dec/LST and increased AZM/ALT precision to 4 decimal places.

## [0.2.6] - 2026-01-26
### Fixed
- Reverted tracking rate scaling to /60 divisor to restore reasonable slew speeds.
- Web Console UI: Standardized decimal places for RA/Dec/LST (1 decimal second).
- Web Console UI: Increased precision for AZM/ALT (3 decimal places).
- Web Console UI: Reduced dashboard width and adjusted fonts for better horizontal space efficiency.

## [0.2.5] - 2026-01-26
### Fixed
- Disabled wrapping for Altitude axis to prevent "GOTO through Nadir" issues.
- Fixed tracking rate scaling (removed incorrect /60 divisor) to resolve tracking drift.
- Improved Web Console telemetry alignment using tabular fonts and fixed-width labels.

## [0.2.4] - 2026-01-25
### Added
- Dynamic observer location sync: Simulator now recognizes and applies geographic coordinates sent by SkySafari 7 (WiFi Command 0x31).

## [0.2.3] - 2026-01-25
### Changed
- Web Console UI: Unified version display into title.
- Web Console UI: Improved formatting for Mount Lights and Power status.
- Web Console UI: Axis speed display changed to arcseconds per second ("/s").

## [0.2.2] - 2026-01-25
### Added
- Comprehensive Mount Dashboard in Web Console (Battery, Lights, Coordinates).
- Real-time synchronization of Charging state in Web Console.

## [0.2.1] - 2026-01-25
### Fixed
- Switched East and West cardinal labels in the Web Console to match standard astronomical orientation.

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
