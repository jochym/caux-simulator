import pytest
from caux_simulator.devices.motor import MotorController
from caux_simulator.devices.power import PowerModule
from caux_simulator.devices.wifi import WiFiModule
from caux_simulator.bus.utils import pack_int3, unpack_int3


def test_motor_controller():
    config = {"simulator": {"imperfections": {"backlash_steps": 100}}}
    azm = MotorController(0x10, config)

    # Test version (7.19.20.10)
    assert azm.handle_command(0x20, 0xFE, b"") == bytes([7, 19, 20, 10])

    # Test position setting
    azm.handle_command(0x20, 0x04, b"\x80\x00\x00")  # Set to 0.5
    assert azm.pos == 0.5

    # Test position query
    resp = azm.handle_command(0x20, 0x01, b"")
    assert resp == b"\x80\x00\x00"


def test_power_module():
    config = {}
    bat = PowerModule(0xB6, config)

    # Test voltage query (0x10) - Evolution format
    resp = bat.handle_command(0x20, 0x10, b"")
    assert len(resp) == 6
    assert resp[0] == 0  # Not charging
    assert resp[1] == 2  # Status HIGH

    # Test current query (0x18)
    resp = bat.handle_command(0x20, 0x18, b"")
    assert len(resp) == 2


def test_motor_movement():
    config = {"simulator": {"imperfections": {"backlash_steps": 0}}}
    azm = MotorController(0x10, config)
    azm.pos = 0.0

    # Start GOTO to 0.1
    azm.handle_command(0x20, 0x02, pack_int3(0.1))
    assert azm.slewing is True

    # Tick 1 second. Max rate is ~0.027 fraction/sec
    azm.tick(1.0)
    assert azm.pos > 0.0
    assert azm.pos < 0.1

    # Tick 10 seconds. Should arrive.
    azm.tick(10.0)
    assert abs(azm.pos - 0.1) < 1e-6
    assert azm.slewing is False

    # Test SLEW_DONE
    assert azm.handle_command(0x20, 0x13, b"") == b"\xff"


def test_wifi_module():
    config = {}
    wifi = WiFiModule(0xB9, config)

    # Test Handshake 0x49
    assert wifi.handle_command(0x20, 0x49, b"") == b"\x00"

    # Test Handshake 0x32
    assert wifi.handle_command(0x20, 0x32, b"") == b"\x01"

    # Test Handshake 0x31
    assert wifi.handle_command(0x20, 0x31, b"") == b"\x01"
