# Integer-Based Backlash Implementation Plan

This document outlines the high-fidelity backlash model for the NexStar Evolution simulator.

## 1. Core Architecture: Decoupling Encoder from Sky

The `MotorController` will maintain two distinct 24-bit integer state variables:

1.  **`self.steps` (The Encoder Register)**
    *   Represents the rotational position of the motor shaft/worm drive.
    *   Updates immediately when the motor turns.
    *   Returned by `GET_POSITION (0x01)` and set by `SET_POSITION (0x04)`.
2.  **`self.sky_steps` (The Optical Axis)**
    *   Represents the actual pointing direction of the telescope tube.
    *   Only updates when "gear slack" is fully consumed.
    *   Used by `NexStarMount` to calculate RA/Dec for Stellarium and the Web Console.

## 2. The Physical Domain (Mechanical Slop)

A "Hysteresis Model" to simulate the physical gap between gear teeth.

*   **Config**: `imperfections.physical_backlash_steps` (integer constant **P**).
*   **State Variable**: `self.gear_slack` (integer, range `0` to `P`).
*   **Logic (`tick` Loop)**:
    When the motor moves by `delta_steps`:
    1.  **Encoder Updates**: `self.steps += delta_steps`.
    2.  **Slack Absorption**:
        *   **Positive (`delta_steps > 0`)**:
            *   Increase `self.gear_slack` towards `P`.
            *   Overflow beyond `P` is added to `self.sky_steps`.
        *   **Negative (`delta_steps < 0`)**:
            *   Decrease `self.gear_slack` towards `0`.
            *   Underflow below `0` is subtracted from `self.sky_steps`.

## 3. The Firmware Domain (Backlash Compensation)

Simulates how the Motor Controller firmware attempts to hide the mechanical issue.

*   **Register**: `self.backlash_compensation` (integer **C**), set via `SET_POS_BACKLASH (0x10)`.
*   **Logic**:
    When the requested rate changes sign:
    1.  Firmware injects a pulse: `self.steps += C * new_direction`.
    2.  This pulse is passed into the Physical Domain logic, immediately consuming some or all of the slack.

## 4. Verification Scenarios

*   **Under-Compensation (`C < P`)**: Star field lags slightly after reversal.
*   **Over-Compensation (`C > P`)**: Star field "jumps" instantly when reversing.
*   **Perfect Calibration (`C == P`)**: Seamless movement reversal.
