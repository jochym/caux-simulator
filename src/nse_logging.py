"""
Logging utilities for the NexStar AUX Simulator.

Provides categorized logging with bitmask-based filtering for detailed
protocol and connection debugging.
"""

import logging
from typing import Optional

# Logging category flags (bitmask)
LOG_CONNECTION = 0x01  # Connection events (connect, disconnect, clients)
LOG_PROTOCOL = 0x02  # Raw AUX protocol packets (bytes, checksums)
LOG_COMMAND = 0x04  # Decoded commands and responses
LOG_MOTION = 0x08  # Movement and positioning (GOTO, slew, rates)
LOG_DEVICE = 0x10  # Device state (battery, GPS, lights, etc.)

# Global logging category mask
_log_categories = 0


def set_log_categories(categories: int) -> None:
    """
    Sets the global logging category mask.

    Args:
        categories: Bitmask of LOG_* flags to enable
    """
    global _log_categories
    _log_categories = categories


def get_log_categories() -> int:
    """Returns the current logging category mask."""
    return _log_categories


def should_log(category: int) -> bool:
    """
    Checks if a category should be logged based on current mask.

    Args:
        category: One or more LOG_* flags to check

    Returns:
        True if any of the specified categories are enabled
    """
    return bool(_log_categories & category)


def log_connection(
    logger: logging.Logger, message: str, level: int = logging.INFO
) -> None:
    """Logs a connection-related message if CONNECTION category is enabled."""
    if should_log(LOG_CONNECTION):
        logger.log(level, f"[CONN] {message}")


def log_protocol(
    logger: logging.Logger, message: str, level: int = logging.DEBUG
) -> None:
    """Logs a protocol-level message if PROTOCOL category is enabled."""
    if should_log(LOG_PROTOCOL):
        logger.log(level, f"[PROTO] {message}")


def log_command(
    logger: logging.Logger, message: str, level: int = logging.DEBUG
) -> None:
    """Logs a command-level message if COMMAND category is enabled."""
    if should_log(LOG_COMMAND):
        logger.log(level, f"[CMD] {message}")


def log_motion(
    logger: logging.Logger, message: str, level: int = logging.DEBUG
) -> None:
    """Logs a motion-related message if MOTION category is enabled."""
    if should_log(LOG_MOTION):
        logger.log(level, f"[MOTION] {message}")


def log_device(
    logger: logging.Logger, message: str, level: int = logging.DEBUG
) -> None:
    """Logs a device state message if DEVICE category is enabled."""
    if should_log(LOG_DEVICE):
        logger.log(level, f"[DEVICE] {message}")


def format_aux_packet(packet: bytes, direction: str = "RX") -> str:
    """
    Formats an AUX packet for logging with hex representation.

    Args:
        packet: Raw AUX packet bytes
        direction: "RX" for received, "TX" for transmitted

    Returns:
        Formatted string representation of the packet
    """
    if len(packet) < 4:
        return f"{direction}: {packet.hex()} (incomplete packet)"

    # Skip the ';' if present
    start_idx = 1 if packet[0:1] == b";" else 0
    if len(packet) <= start_idx:
        return f"{direction}: {packet.hex()} (empty)"

    length = packet[start_idx] if start_idx < len(packet) else 0

    hex_str = packet.hex()
    if len(packet) > 20:
        hex_str = f"{packet[:20].hex()}... ({len(packet)} bytes)"

    return f"{direction}: {hex_str} (len={length})"


def describe_log_categories(categories: int) -> str:
    """
    Returns a human-readable description of enabled log categories.

    Args:
        categories: Bitmask of LOG_* flags

    Returns:
        Comma-separated string of enabled categories
    """
    enabled = []
    if categories & LOG_CONNECTION:
        enabled.append("CONNECTION")
    if categories & LOG_PROTOCOL:
        enabled.append("PROTOCOL")
    if categories & LOG_COMMAND:
        enabled.append("COMMAND")
    if categories & LOG_MOTION:
        enabled.append("MOTION")
    if categories & LOG_DEVICE:
        enabled.append("DEVICE")

    return ", ".join(enabled) if enabled else "NONE"
