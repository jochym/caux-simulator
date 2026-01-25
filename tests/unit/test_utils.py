import pytest
from caux_simulator.bus.utils import (
    make_checksum,
    split_cmds,
    decode_command,
    pack_int3,
    unpack_int3,
    unpack_int2,
)


def test_checksum():
    # Example packet: ; 03 10 04 01 e8 (length 3, src 10, dst 04, cmd 01, cs e8)
    header = bytes([0x03, 0x10, 0x04, 0x01])
    cs = make_checksum(header)
    assert cs == 0xE8


def test_split_cmds():
    data = b";\x03\x10\x20\x01\xcc;\x03\x11\x20\x01\xcb"
    cmds = split_cmds(data)
    assert len(cmds) == 2
    assert cmds[0] == b"\x03\x10\x20\x01\xcc"
    assert cmds[1] == b"\x03\x11\x20\x01\xcb"


def test_decode_command():
    # 3B 03 20 10 40 8D (GET_POS_BACKLASH to AZM)
    cmd = b"\x03\x20\x10\x40\x8d"
    cmd_id, src, dst, length, data, chk = decode_command(cmd)
    assert cmd_id == 0x40
    assert src == 0x20
    assert dst == 0x10
    assert length == 0x03
    assert data == b""
    assert chk == 0x8D


def test_packing():
    # Test 24-bit fraction packing
    val = 0.5
    packed = pack_int3(val)
    assert packed == b"\x80\x00\x00"
    assert unpack_int3(packed) == 0.5

    # Test round trip
    test_vals = [0.0, 0.12345, 0.999999, 0.5]
    for v in test_vals:
        assert abs(unpack_int3(pack_int3(v)) - v) < 1e-7


def test_unpack_int2():
    assert unpack_int2(b"\x03\xe8") == 1000
    assert unpack_int2(b"\x00\x01") == 1
