import pytest
from caux_simulator.nse_telescope import NexStarScope


def test_slew_to_target():
    scope = NexStarScope(ALT=0.0, AZM=0.0)
    # Start a slew
    # GOTO_FAST to ALT=0.1 (fraction)
    # data for ALT=0.1: 0.1 * 2^24 = 1677721.6 -> 0x19999a
    data = bytes.fromhex("19999a")
    scope.goto_fast(data, 0x04, 0x11)  # From HC to ALT

    assert scope.slewing
    assert scope.goto
    assert scope.trg_alt == pytest.approx(0.1, abs=1e-6)

    # Simulate time
    # Max rate is 10000 / 360000 = 0.0277... fraction/sec
    # To move 0.1 fraction, it should take ~3.6 seconds
    scope.tick(1.0)
    assert 0 < scope.alt < 0.1

    # Simulate time in small steps to allow tick logic to stop at target
    for _ in range(100):
        scope.tick(0.1)

    assert scope.alt == pytest.approx(0.1, abs=1e-4)
    assert not scope.slewing


def test_altitude_limits():
    # Default limits: alt_min = -22.5/360, alt_max = 90.0/360
    scope = NexStarScope(ALT=0.0)

    # Try to move below min
    # alt_min = -0.0625. At 4 deg/s (0.011 fraction/s), it takes ~5.6s
    scope.move_neg(bytes([9]), 0x04, 0x11)  # Rate 9 negative
    scope.tick(10.0)  # Move for a long time

    assert scope.alt == pytest.approx(scope.alt_min)
    assert scope.alt_rate == 0.0

    # Try to move above max
    # From -0.0625 to 0.25 is 0.3125. At 0.011/s, it takes ~28s
    scope.move_pos(bytes([9]), 0x04, 0x11)
    scope.tick(40.0)
    assert scope.alt == pytest.approx(scope.alt_max)
    assert scope.alt_rate == 0.0

    # Try to move above max
    scope.move_pos(bytes([9]), 0x04, 0x11)
    scope.tick(20.0)
    assert scope.alt == pytest.approx(scope.alt_max)
    assert scope.alt_rate == 0.0
