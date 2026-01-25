import pytest
from caux_simulator.nse_telescope import make_checksum, split_cmds, decode_command


def test_checksum():
    # Example packet: ; 03 10 04 01 e8 (length 3, src 10, dst 04, cmd 01, cs e8)
    # Header: 03 10 04 01
    header = bytes([0x03, 0x10, 0x04, 0x01])
    cs = make_checksum(header)
    # 0x03 + 0x10 + 0x04 + 0x01 = 0x18 (24)
    # ~0x18 = 0xe7
    # 0xe7 + 1 = 0xe8
    assert cs == 0xE8


def test_split_cmds():
    data = b";\x03\x10\x04\x01\xe8;\x03\x11\x04\x01\xe7"
    cmds = split_cmds(data)
    assert len(cmds) == 2
    assert cmds[0] == b"\x03\x10\x04\x01\xe8"
    assert cmds[1] == b"\x03\x11\x04\x01\xe7"


def test_decode_command():
    cmd = b"\x03\x10\x04\x01\xe8"
    c, f, t, l, d, s = decode_command(cmd)
    assert c == 0x01  # cmd
    assert f == 0x10  # from
    assert t == 0x04  # to
    assert l == 0x03  # length
    assert d == b""  # data
    assert s == 0xE8  # checksum
