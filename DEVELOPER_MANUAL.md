# NexStar AUX Simulator: Developer Manual

This manual is for developers contributing to the simulator's core physics, bus logic, or device models.

## 1. Architecture

The simulator uses a modular, bus-based architecture:
- **`AuxBus`**: The central router. It handles packet validation, echoing (required by AUX protocol), and routing to registered `AuxDevice` instances.
- **`AuxDevice`**: Base class for all simulated hardware.
- **`MotorController`**: The core physics engine. Uses a 24-bit integer step system to mimic real motor encoders.

## 2. Integer-Based Motion Engine
To maintain bit-perfect compatibility with Celestron hardware:
- **Position**: Stored as a 24-bit integer (`self.steps`).
- **Physics**: Incremental movements are calculated using floats but accumulated into the integer register.
- **GOTO**: Completion is defined as `abs(target_steps - current_steps) <= 1`.

## 3. Backlash Modeling
The simulator implements a decoupled backlash model (see `BACKLASH_PLAN.md`):
- **Physical Domain**: Hysteresis slack that stays between the motor and the sky.
- **Firmware Domain**: Compensation pulses injected by the MC to cross the physical gap.

## 4. Development Workflow

### Running Tests
All logic is verified using `pytest`. Ensure you run them before submitting changes:
```bash
PYTHONPATH=src pytest tests/
```

### Adding New Devices
1. Inherit from `AuxDevice`.
2. Define your command handlers in the `self.handlers` dictionary.
3. Register the device in `NexStarMount.__init__`.

### Logging Categories
Logging is controlled by a bitmask in `src/caux_simulator/nse_logging.py`:
- `0x01`: CONNECTION
- `0x02`: PROTOCOL
- `0x04`: COMMAND
- `0x08`: MOTION
- `0x10`: DEVICE
