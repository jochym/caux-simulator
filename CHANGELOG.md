# Changelog

## [0.2.19] - 2026-01-27
### Fixed
- Guiding Arithmetic: Implemented exact rational scaling (128/10125) for guiderate commands, eliminating the 2.5 arcmin/15min drift caused by previous floating-point approximations.
- Web Console: Fixed a telemetry crash caused by non-serializable `Decimal` objects in the WebSocket broadcast loop.
- Web Console: Improved telemetry robustness with explicit type casting and connection stability fixes.
- Documentation: Added detailed explanations for internal motor constants and geometric scaling factors.

## [0.2.18] - 2026-01-26
### Fixed
- Motor Engine: Fully refactored movement accumulator using `decimal.Decimal` (28-digit precision) to eliminate floating-point rounding drift.
- GOTO: Improved state reset logic to handle SkySafari command re-transmission without stalling.
- Tracking: Standardized high-fidelity tracking scaling using INDI driver reference factor (value/80.0).

## [0.2.17] - 2026-01-26
### Fixed
- Config: Moved all default settings into src/caux_simulator/config.default.toml.
- Config: Standardized the config.toml deep-merge logic.
- UI: Set default camera_distance to 15.0 and default web_host to 0.0.0.0.

## [0.2.16] - 2026-01-26
### Added
- Expanded `config.example.toml` with all adjustable geometry, imperfection, and observer settings.
- Restored default camera zoom to 15.0.

## [0.2.15] - 2026-01-26
### Fixed
- UI: Restored configuration-driven model zoom (adjustable via config.toml).
- Tracking: Verified tracking scaling matches physical mount behavior (1.33x correction).

## [0.2.14] - 2026-01-26
### Fixed
- Tracking: Implemented INDI-compliant guide rate scaling (value/80.0).
- UI: Refined dashboard whitespace and camera overview zoom (15.0 units).

## [0.2.13] - 2026-01-26
### Fixed
- GOTO: Implemented explicit state reset on new target reception to prevent "Transition Stalls".
- Model: Pointing model is now 100% "perfect" geometrically (all imperfections disabled by default).
- UI: Standardized all dashboard fonts to 1.3vw.

## [0.2.12] - 2026-01-26
### Fixed
- Web Console: Hardened broadcast loop with attribute checks and manual HMS/DMS formatter to prevent silent crashes.
- Star Catalog: Added Regulus, Aldebaran, and Fomalhaut to the schematic FOV view.

## [0.2.11] - 2026-01-26
### Fixed
- UI: Switched to tabular fonts and fixed-width layout for telemetry.
- FOV: Added three concentric circles (10, 20, 30 arcmin) to 1-degree FOV view.

## [0.2.10] - 2026-01-26
### Fixed
- Stability: Resolved "Zero display" regression in Web Console.
- Time: Anchored virtual sky to simulation start date for perfect clock sync.
- Epoch: Switched to current epoch (real-time) to match SkySafari 7 default behavior.

## [0.2.9] - 2026-01-26
### Fixed
- Motor Engine: Refactored integer step application to eliminate sub-step rounding accumulation.

## [0.2.8] - 2026-01-26
### Fixed
- Web Console UI: Unified precision for RA/Dec/LST (1 decimal place for seconds).
- Web Console UI: Added dynamic Geographic Location (GEO) display synced from SkySafari.

## [0.2.7] - 2026-01-26
### Fixed
- Web Console UI: Restored state broadcast by adding robust attribute checks.

## [0.2.6] - 2026-01-26
### Fixed
- Reverted tracking rate scaling to /60 divisor to restore reasonable slew speeds.

## [0.2.5] - 2026-01-26
### Fixed
- Disabled wrapping for Altitude axis to prevent "GOTO through Nadir" issues.
- Fixed tracking rate scaling (removed incorrect /60 divisor).
- Improved Web Console telemetry alignment.

## [0.2.4] - 2026-01-25
### Added
- Dynamic observer location sync: Simulator now recognizes and applies coordinates sent by SkySafari 7.

## [0.2.3] - 2026-01-25
### Changed
- Web Console UI: Unified version display into title.
- Web Console UI: Axis speed display changed to arcseconds per second ("/s").

## [0.2.2] - 2026-01-25
### Added
- Comprehensive Mount Dashboard in Web Console.
- Real-time synchronization of Charging state.

## [0.2.1] - 2026-01-25
### Fixed
- Switched East and West cardinal labels in the Web Console.

## [0.2.0] - 2026-01-25
### Added
- High-fidelity 24-bit integer motor engine.
- NexStar Evolution device profile.
- Modular AuxBus and AuxDevice architecture.
- Categorized logging.
- Comprehensive manuals.
