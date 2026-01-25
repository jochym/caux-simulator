import socket
import subprocess
import sys
import time
import pytest
from caux_simulator.bus.utils import encode_packet, unpack_int3, pack_int3


class TestMotionIntegration:
    @classmethod
    def setup_class(cls):
        # Start simulator in headless mode
        cls.sim_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "caux_simulator.nse_simulator",
                "--text",
                "-p",
                "2002",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/jochym/Projects/indi/caux-simulator",
            env={**os.environ, "PYTHONPATH": "src"},
        )
        time.sleep(2)

    @classmethod
    def teardown_class(cls):
        cls.sim_proc.terminate()
        cls.sim_proc.wait()

    def setup_method(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 2002))
        self.sock.settimeout(1.0)

    def teardown_method(self):
        self.sock.close()

    def exchange(self, dest, cmd, data=b""):
        pkt = encode_packet(0x20, dest, cmd, data)
        self.sock.send(pkt)
        time.sleep(0.1)
        resp = self.sock.recv(4096)
        # Skip echo
        return resp[len(pkt) :]

    def test_goto_sequence(self):
        """Verifies GOTO_FAST and movement monitoring."""
        # 1. Set initial position to 0.0
        self.exchange(0x10, 0x04, b"\x00\x00\x00")

        # 2. Trigger GOTO to 0.25 (90 degrees)
        target = 0.25
        self.exchange(0x10, 0x02, pack_int3(target))

        # 3. Monitor movement
        time.sleep(0.5)
        resp = self.exchange(0x10, 0x01)
        current_pos = unpack_int3(resp[5:8])
        assert current_pos > 0.0, "Mount should have moved"

        # 4. Wait for completion
        max_retries = 60
        for _ in range(max_retries):
            resp = self.exchange(0x10, 0x13)  # SLEW_DONE
            if resp[5] == 0xFF:
                break
            time.sleep(0.5)
        else:
            pytest.fail("GOTO timed out")

        # 5. Verify final position
        resp = self.exchange(0x10, 0x01)
        final_pos = unpack_int3(resp[5:8])
        assert abs(final_pos - target) < 1e-4


import os
