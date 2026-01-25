"""
AUX Protocol Utilities

Common functions for packing, unpacking, and validating NexStar AUX packets.
"""

import struct
from typing import Tuple, List


def make_checksum(data: bytes) -> int:
    """Calculates 2's complement checksum for AUX packet."""
    return (~sum([c for c in bytes(data)]) + 1) & 0xFF


def decode_command(cmd: bytes) -> Tuple[int, int, int, int, bytes, int]:
    """
    Decodes a raw AUX packet into its components.
    Format: [Length, Src, Dst, Cmd, Data..., Checksum]
    Returns: (Cmd, Src, Dst, Length, Data, Checksum)
    """
    return (cmd[3], cmd[1], cmd[2], cmd[0], cmd[4:-1], cmd[-1])


def split_cmds(data: bytes) -> List[bytes]:
    """Splits a stream of bytes into individual AUX packets based on start byte ';'."""
    cmds = []
    b = 0
    while True:
        try:
            p = data.index(b";", b)
            length = abs(int(data[p + 1]))
            cmds.append(data[p + 1 : p + length + 3])
            b = p + length + 3
        except (ValueError, IndexError):
            return cmds


def pack_int3(f: float) -> bytes:
    """Packs a float [0,1] into 3 bytes big-endian (NexStar fraction format)."""
    return struct.pack("!i", int((f % 1.0) * (2**24)))[1:]


def unpack_int3(d: bytes) -> float:
    """Unpacks up to 3 bytes into a float [0,1]."""
    if len(d) < 3:
        d = d.ljust(3, b"\x00")
    return struct.unpack("!i", b"\x00" + d[:3])[0] / 2**24


def pack_int3_raw(steps: int) -> bytes:
    """Packs 24-bit steps into 3 bytes big-endian."""
    return struct.pack("!i", steps & 0xFFFFFF)[1:]


def unpack_int3_raw(d: bytes) -> int:
    """Unpacks up to 3 bytes into a 24-bit integer."""
    if len(d) < 3:
        d = d.ljust(3, b"\x00")
    return struct.unpack("!i", b"\x00" + d[:3])[0]


def unpack_int2(d: bytes) -> int:
    """Unpacks 2 bytes into an integer."""
    if len(d) < 2:
        d = d.ljust(2, b"\x00")
    return struct.unpack("!i", b"\x00\x00" + d[:2])[0]


def f2dms(f: float) -> Tuple[int, int, float]:
    """Converts fraction of rotation [0,1] to (Degrees, Minutes, Seconds)."""
    d = 360 * abs(f)
    dd = int(d)
    mm = int((d - dd) * 60)
    ss = (d - dd - mm / 60) * 3600
    return dd, mm, ss


def encode_packet(src: int, dst: int, cmd: int, data: bytes = b"") -> bytes:
    """Helper to encode a standard AUX packet."""
    length = len(data) + 3
    header = bytes([length, src, dst, cmd])
    payload = header + data
    return b";" + payload + bytes([make_checksum(payload)])
