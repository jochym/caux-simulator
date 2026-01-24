# Logging Configuration Guide

The NexStar AUX Simulator provides comprehensive logging capabilities for debugging connection and protocol issues.

## Quick Start

```bash
# Debug SkySafari connection issues
python -m src.nse_simulator -d --log-file skysafari.log --log-categories 7

# Watch the log in real-time
tail -f skysafari.log
```

## Command-Line Options

### Logging Level

| Option | Description | Level |
|--------|-------------|-------|
| (none) | Minimal logging | WARNING |
| `-v, --verbose` | Standard logging | INFO |
| `-d, --debug` | Detailed logging | DEBUG |

### Logging Destination

| Option | Description |
|--------|-------------|
| (none) | Log to stderr |
| `--log-file FILE` | Log to file instead of stderr |
| `--log-stderr` | When using --log-file, also log to stderr |

### Detailed Categories

| Option | Description |
|--------|-------------|
| `--log-categories N` | Enable detailed logging (bitmask, see below) |

## Configuration File

You can also configure logging in `config.toml`:

```toml
[logging]
level = "DEBUG"
file = "caux_sim.log"
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
categories = 7  # Detailed logging bitmask
```

### Category Flags (Bitmask)

| Category | Value | Description |
|----------|-------|-------------|
| CONNECTION | 1 | Connection events (connect, disconnect, client info) |
| PROTOCOL | 2 | Raw AUX protocol packets with hex dumps and checksums |
| COMMAND | 4 | Decoded AUX commands and responses |
| MOTION | 8 | Movement operations (GOTO, slewing, guide rates) |
| DEVICE | 16 | Device state changes (battery, GPS, lights) |

### Common Combinations

**For debugging SkySafari connection:**
```bash
python -m src.nse_simulator -d --log-file skysafari.log --log-categories 7
```
Enables: CONNECTION + PROTOCOL + COMMAND (1+2+4)

**For debugging mount movement:**
```bash
python -m src.nse_simulator -d --log-file motion.log --log-categories 12
```
Enables: COMMAND + MOTION (4+8)

**Enable all detailed logging:**
```bash
python -m src.nse_simulator -d --log-file full.log --log-categories 31
```
Enables: All categories (1+2+4+8+16)

**Disable detailed logging:**
```bash
python -m src.nse_simulator -d --log-file basic.log
```
No categories flag = standard logging only

## Command-Line vs Config File

Command-line options override config file settings:

```bash
# Config file has: level = "INFO", categories = 0
# This enables DEBUG level and categories 7:
python -m src.nse_simulator -d --log-categories 7
```

## Example: Debugging SkySafari Connection

1. Start simulator with protocol logging:
```bash
python -m src.nse_simulator -d --log-file skysafari.log --log-categories 7
```

2. In another terminal, watch the log:
```bash
tail -f skysafari.log
```

3. Connect with SkySafari and observe the protocol interaction in real-time

## Log Output Examples

### With CONNECTION category (1):
```
2025-01-23 10:15:32 - nse_simulator - INFO - [CONN] Client connected from ('192.168.1.100', 54321)
2025-01-23 10:15:45 - nse_simulator - INFO - [CONN] Client ('192.168.1.100', 54321) disconnected
```

### With PROTOCOL category (2):
```
2025-01-23 10:15:33 - nse_telescope - DEBUG - [PROTO] RX: 3b03102001fc (6 bytes)
2025-01-23 10:15:33 - nse_telescope - DEBUG - [PROTO] Packet: len=03 src=20 dst=10 cmd=01 data= chk=fc
2025-01-23 10:15:33 - nse_telescope - DEBUG - [PROTO] TX response: 3b0610200100000000f7
```

### With COMMAND category (4):
```
2025-01-23 10:15:33 - nse_telescope - DEBUG - [CMD] APP -> AZM: MC_GET_POSITION data=
2025-01-23 10:15:33 - nse_telescope - DEBUG - [CMD] AZM -> APP: MC_GET_POSITION response_data=000000
```

### With MOTION category (8):
```
2025-01-23 10:16:12 - nse_telescope - DEBUG - [MOTION] Starting GOTO_FAST to 0.500000 on AZM
2025-01-23 10:16:12 - nse_telescope - DEBUG - [MOTION] AZM: current=0.250000 target=0.500000 rate=0.027778
```

### With DEVICE category (16):
```
2025-01-23 10:17:05 - nse_telescope - DEBUG - [DEVICE] Battery voltage: 12.35V
2025-01-23 10:17:20 - nse_telescope - DEBUG - [DEVICE] Set tray light to 128
```

## Logging in Different Modes

The logging system works identically in all modes:

- **TUI Mode** (default): Logs go to file/stderr, TUI displays in terminal
- **Web Mode** (`--web`): Logs go to file/stderr, web interface in browser  
- **Headless Mode** (`--text`): Logs go to file/stderr only

The TUI's "AUX BUS LOG" pane shows command summaries regardless of logging configuration.

## Logging Behavior

### Default (no log file)
```bash
python -m src.nse_simulator
```
- WARNING level messages to stderr
- TUI/Web interface works normally

### With --log-file
```bash
python -m src.nse_simulator --log-file debug.log
```
- ALL logs go to file ONLY
- stderr is silent
- TUI/Web interface works normally

### With --log-file --log-stderr
```bash
python -m src.nse_simulator --log-file debug.log --log-stderr
```
- Logs go to BOTH file and stderr
- Useful for monitoring while keeping a permanent record

## Performance Considerations

- Categories 0-4 (CONNECTION, PROTOCOL, COMMAND): Minimal overhead
- Category 8 (MOTION): Low overhead, logs only on state changes
- Category 16 (DEVICE): Very low overhead

Enabling all categories (31) is safe for normal operation and essential for debugging.
