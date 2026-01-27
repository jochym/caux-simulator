import pytest
from math import pi, sin, tan, radians, degrees
from caux_simulator.bus.mount import NexStarMount


def test_cone_error():
    config = {
        "simulator": {
            "imperfections": {
                "cone_error_arcmin": 10.0  # 10 arcminutes
            }
        }
    }
    mount = NexStarMount(config)
    mount.alt = 0.0
    mount.azm = 0.0

    # 10 arcmin = 10 / (60 * 360) rotations
    expected_alt = 10.0 / (60.0 * 360.0)

    sky_azm, sky_alt = mount.get_sky_altaz()
    assert sky_alt == pytest.approx(expected_alt, rel=1e-6)
    assert sky_azm == 0.0


def test_non_perpendicularity():
    config = {
        "simulator": {
            "imperfections": {
                "non_perpendicularity_arcmin": 10.0  # 10 arcminutes
            }
        }
    }
    mount = NexStarMount(config)

    # Test at Alt = 45 degrees where tan(45) = 1.0
    mount.alt = 45.0 / 360.0
    mount.azm = 0.0

    # Expected Azm offset = (10' * tan(45)) / 360 = 10' / 360
    expected_azm_offset = (10.0 / 60.0) / 360.0

    sky_azm, sky_alt = mount.get_sky_altaz()
    assert sky_azm == pytest.approx(expected_azm_offset, rel=1e-6)


def test_periodic_error():
    # PE amplitude in arcsec, period in sec
    config = {
        "simulator": {
            "imperfections": {
                "periodic_error_arcsec": 3600.0,  # 1 degree for easy math
                "periodic_error_period_sec": 100.0,
            }
        }
    }
    mount = NexStarMount(config)
    mount.alt = 0.0
    mount.azm = 0.0

    # At t = 25s (1/4 period), sin(2*pi*25/100) = sin(pi/2) = 1.0
    mount.sim_time = 25.0

    # Amplitude 3600 arcsec = 1 degree = 1/360 rotation
    expected_error = 1.0 / 360.0

    sky_azm, sky_alt = mount.get_sky_altaz()
    assert sky_azm == pytest.approx(expected_error, rel=1e-6)
    assert sky_alt == pytest.approx(expected_error, rel=1e-6)


def test_refraction():
    config = {"simulator": {"imperfections": {"refraction_enabled": True}}}
    mount = NexStarMount(config)

    # Point at Alt = 45 degrees
    mount.alt = 45.0 / 360.0
    mount.azm = 0.0

    # Bennett's formula for h = 45 deg
    # ref_arcmin = 1.0 / tan(radians(45 + 7.31 / (45 + 4.4)))
    h = 45.0
    ref_arcmin = 1.0 / tan(radians(h + 7.31 / (h + 4.4)))
    expected_alt_offset = ref_arcmin / (60.0 * 360.0)

    sky_azm, sky_alt = mount.get_sky_altaz()
    assert sky_alt == pytest.approx(mount.alt + expected_alt_offset, rel=1e-6)


def test_tan_clamping():
    # Verify Azm correction doesn't explode near zenith
    config = {"simulator": {"imperfections": {"non_perpendicularity_arcmin": 10.0}}}
    mount = NexStarMount(config)

    # Point very close to Zenith (89.9 degrees)
    mount.alt = 89.9 / 360.0
    mount.azm = 0.0

    # It should use tan(80) due to clamping
    expected_azm_offset = (10.0 / 60.0) * tan(radians(80.0)) / 360.0

    sky_azm, sky_alt = mount.get_sky_altaz()
    assert sky_azm == pytest.approx(expected_azm_offset, rel=1e-6)
