import pytest
from caux_simulator.nse_telescope import NexStarScope


def test_scope_init():
    scope = NexStarScope()
    assert scope.alt == 0.0
    assert scope.azm == 0.0
    assert not scope.slewing
