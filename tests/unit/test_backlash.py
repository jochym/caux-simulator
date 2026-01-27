import pytest
from decimal import Decimal
from caux_simulator.devices.motor import MotorController


def test_backlash_hysteresis():
    # Setup MotorController with 100 steps of PHYSICAL backlash
    config = {"simulator": {"imperfections": {"backlash_steps": 100}}}
    mc = MotorController(0x10, config)
    mc.steps = 0
    mc.pointing_steps = 0
    mc._backlash_slack = 0  # Assume started at the "negative" end

    # 1. Move positive by 50 steps
    # Entirely consumed by slack (slack 0 -> 50)
    mc.rate_steps = Decimal(500)  # 500 steps/s
    mc.slewing = True
    mc.tick(0.1)  # 50 steps

    assert mc.steps == 50
    assert mc.pointing_steps == 0
    assert mc._backlash_slack == 50

    # 2. Move positive by another 100 steps
    # 50 consumed by slack (slack 50 -> 100), 50 moved OTA
    mc.tick(0.2)  # 100 steps

    assert mc.steps == 150
    assert mc.pointing_steps == 50
    assert mc._backlash_slack == 100


def test_backlash_jump_correction():
    # Test the MC internal jump routine
    mc = MotorController(0x10, {})
    mc.phys_backlash = 100
    mc.backlash_corr_pos = 80  # MC will jump 80 steps when going positive

    mc.steps = 0
    mc._backlash_slack = 0
    mc.last_direction = -1  # Was going negative

    # Start moving positive
    mc.handle_move_pos(bytes([1]), 0, 0x10)  # Trigger jump
    assert mc._step_accumulator == 80

    mc.tick(0.0)  # Apply jump
    assert mc.steps == 80
    assert mc._backlash_slack == 80
    assert mc.pointing_steps == 0  # Slack still not fully filled (80/100)


def test_alt_unbalance():
    # Test gravity pulling slack back
    config = {
        "simulator": {
            "imperfections": {
                "alt_unbalance": -1,  # Gravity pulls negative
                "alt_backlash_steps": 100,
            }
        }
    }
    mc = MotorController(0x11, config)
    mc._backlash_slack = 100  # Manually set to positive end

    # Stop motor
    mc.slewing = False
    mc.tick(0.1)

    # Gravity should have pulled slack to 0
    assert mc._backlash_slack == 0


def test_backlash_canceling_unbalance():
    # Test that MC jump is skipped when gravity already takes up slack
    config = {
        "simulator": {
            "imperfections": {
                "alt_unbalance": -1,  # Gravity pulls negative
                "alt_backlash_steps": 100,
            }
        }
    }
    mc = MotorController(0x11, config)
    mc.backlash_corr_neg = 50
    mc.last_direction = 1  # Was going positive

    # Reversing to Negative (direction of gravity)
    # The jump should be SKIPPED
    mc.handle_move_neg(bytes([1]), 0, 0x11)
    assert mc._step_accumulator == 0  # Jump was skipped


def test_backlash_protocol():
    mc = MotorController(0x10, {})

    # Set backlash via command (0x10 is SET_POS_BACKLASH)
    mc.set_backlash_pos(bytes([50]), 0, 0x10)
    assert mc.backlash_corr_pos == 50

    # Get backlash via command (0x40 is GET_POS_BACKLASH)
    resp = mc.get_backlash_pos(b"", 0, 0x10)
    assert resp == b"\x32"  # 50 in hex
