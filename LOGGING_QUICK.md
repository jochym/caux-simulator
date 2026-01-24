# Quick Logging Reference

## Enable Detailed AUX Protocol Logging

For debugging SkySafari or other client connection issues:

```bash
# Method 1: Command line (recommended for quick debugging)
python -m src.nse_simulator -d --log-file skysafari.log --log-categories 7

# Method 2: Configuration file
# Edit config.toml:
[logging]
level = "DEBUG"
file = "skysafari.log"
categories = 7  # CONNECTION + PROTOCOL + COMMAND
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Enable INFO level logging |
| `-d, --debug` | Enable DEBUG level logging |
| `--log-file FILE` | Log to file (stderr is silent unless --log-stderr is used) |
| `--log-stderr` | Also log to stderr when using --log-file |
| `--log-categories N` | Enable detailed logging categories (see bitmask below) |

## Category Bitmask Values

| Flag | Value | What it logs |
|------|-------|--------------|
| CONNECTION | 1 | Client connect/disconnect events |
| PROTOCOL | 2 | Raw AUX packets (hex dumps, checksums) |
| COMMAND | 4 | Decoded command names and data |
| MOTION | 8 | Mount movement (GOTO, slew rates) |
| DEVICE | 16 | Device state (battery, GPS, lights) |

Combine values: `categories = 7` means CONNECTION(1) + PROTOCOL(2) + COMMAND(4)

## Common Usage Examples

```bash
# Full protocol debugging to file (quiet stderr)
python -m src.nse_simulator -d --log-file debug.log --log-categories 7

# Same but also show on stderr
python -m src.nse_simulator -d --log-file debug.log --log-categories 7 --log-stderr

# All logging categories, file only
python -m src.nse_simulator -d --log-file full.log --log-categories 31

# Stderr only, no file
python -m src.nse_simulator -d --log-categories 7

# Watch log file in real-time
python -m src.nse_simulator -d --log-file debug.log --log-categories 7 &
tail -f debug.log
```

## What You'll See

With `-d --log-categories 7`:

```
2026-01-23 10:15:32 - __main__ - INFO - [CONN] Client connected from ('192.168.1.100', 54321)
2026-01-23 10:15:33 - nse_telescope - DEBUG - [PROTO] RX: 3b03102001fc (6 bytes)
2026-01-23 10:15:33 - nse_telescope - DEBUG - [PROTO] Packet: len=3 src=20 dst=10 cmd=01 data= chk=fc
2026-01-23 10:15:33 - nse_telescope - DEBUG - [CMD] APP -> AZM: MC_GET_POSITION data=
2026-01-23 10:15:33 - nse_telescope - DEBUG - [PROTO] TX response: 3b0610200100000000f7
2026-01-23 10:15:33 - nse_telescope - DEBUG - [CMD] AZM -> APP: MC_GET_POSITION response_data=000000
```

This shows exactly what's happening at the protocol level!

## Modes Supported

The logging works in ALL modes:
- TUI mode (default) - logs go to file, TUI shows in terminal
- Web mode (`--web`) - logs go to file, web interface in browser
- Headless mode (`--text`) - logs go to file/stderr only

## Default Behavior

- **No options**: WARNING level to stderr
- **-v**: INFO level to stderr
- **-d**: DEBUG level to stderr
- **--log-file**: Logs to file only (stderr silent)
- **--log-file --log-stderr**: Logs to both file and stderr

See LOGGING.md for full documentation.

