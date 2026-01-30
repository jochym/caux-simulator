# Project Status: Mechanical Fidelity Milestone (v0.2.33)

## Current Milestone (Phase 3: Mechanical & Geometrical Fidelity)
- **High-Fidelity Engine**: 24-bit integer motor controller with `decimal.Decimal` sub-step accumulation (bit-perfect tracking logic).
- **Exact Guiding Arithmetic**: Corrected guiding scaling factor to 79.1015625 (1024 units/arcsec), eliminating the 2.5' drift.
- **Advanced Backlash Model**: Integer hysteresis model separating encoder steps from physical pointing, including MC internal compensation jumps.
- **Gravity Bias**: Simulated Altitude axis unbalance that cancels backlash in the direction of gravity.
- **Dual-Axis Periodic Error**: Sinusoidal corrections applied to both RA/Azm and Dec/Alt axes.
- **GOTO Stability**: Hardened state machine with transition logging and anti-stall resets.
- **Dynamic Synchronization**: Automatic dynamic sync of Location (GEO) and Time/Epoch (Current Epoch) from SkySafari.
- **Web Interface**: Modular 3D console with tabular telemetry, FOV monitoring (10/20/30 arcmin circles), and remote (0.0.0.0) accessibility.

## Known Minor Residuals
- **Pointing Error**: ~5-7' discrepancy in Az/Alt despite matching RA/Dec (likely persistent client-side alignment artifacts).

## Roadmap
1. **Phase 2 (Completed)**: Geometrical Imperfections (Cone Error, Non-Perp, Dual-axis PE, Refraction).
2. **Phase 3 (Completed)**: Mechanical Backlash (Integer Hysteresis, Jump Routines, Gravity Bias).

## Documentation
- [User Manual](USER_MANUAL.md)
- [Developer Manual](DEVELOPER_MANUAL.md)
- [Backlash Implementation Plan](BACKLASH_PLAN.md)
