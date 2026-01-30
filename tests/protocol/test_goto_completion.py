#!/usr/bin/env python3
"""
NexStar AUX Simulator: GOTO Completion Tests
Verifies Fast, Slow, and Combined GOTO sequences in 'perfect' mode.
"""

import socket
import struct
import unittest
import subprocess
import sys
import time
import os

from caux_simulator.bus.utils import encode_packet, pack_int3, unpack_int3


class TestGotoCompletion(unittest.TestCase):
    """Verifies that GOTO commands signal completion correctly."""

    @classmethod
    def setUpClass(cls):
        # Start simulator in perfect mode (no backlash/imperfections)
        cls.sim_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "caux_simulator.nse_simulator",
                "--text",
                "--perfect",
                "--log-file",
                "test_goto.log",
                "--log-categories",
                "31",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/jochym/Projects/indi/caux-simulator",
            env={**os.environ, "PYTHONPATH": "src"},
        )
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls.sim_proc.terminate()
        cls.sim_proc.wait()

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 2000))
        self.sock.settimeout(1.0)
        # Reset position to 0
        self.exchange(0x10, 0x20, 0x04, pack_int3(0.0))
        self.exchange(0x11, 0x20, 0x04, pack_int3(0.0))

    def tearDown(self):
        self.sock.close()

    def exchange(self, dest, src, cmd, data=b""):
        pkt = encode_packet(src, dest, cmd, data)
        self.sock.send(pkt)

        # Read the full response (echo + reply)
        resp = b""
        start = time.time()
        while len(resp) < len(pkt) + 5 and time.time() - start < 1.0:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
            except socket.timeout:
                break

        # Find the response
        idx = resp.find(b";", 1)
        if idx != -1:
            return resp[idx:]
        return b""

    def wait_for_goto(self, dest, timeout=15.0):
        """Polls SLEW_DONE (0x13) until it returns 0xFF."""
        start = time.time()
        while time.time() - start < timeout:
            resp = self.exchange(dest, 0x20, 0x13)
            if resp and len(resp) > 5 and resp[5] == 0xFF:
                return True
            time.sleep(0.2)
        return False

    def test_01_fast_goto(self):
        """Fast GOTO (0x02) over large displacement (30deg)."""
        target = 30.0 / 360.0
        print(f"\n   Testing Fast GOTO to {target * 360:.1f}deg...")
        self.exchange(0x10, 0x20, 0x02, pack_int3(target))

        success = self.wait_for_goto(0x10)
        self.assertTrue(success, "Fast GOTO failed to complete within timeout")

        # Verify final position
        resp = self.exchange(0x10, 0x20, 0x01)
        final_pos = unpack_int3(resp[5:8])
        self.assertAlmostEqual(final_pos, target, places=5)

    def test_02_slow_goto(self):
        """Slow GOTO (0x17) over small displacement (1deg)."""
        target = 1.0 / 360.0
        print(f"\n   Testing Slow GOTO to {target * 360:.1f}deg...")
        self.exchange(0x10, 0x20, 0x17, pack_int3(target))

        success = self.wait_for_goto(0x10)
        self.assertTrue(success, "Slow GOTO failed to complete within timeout")

        resp = self.exchange(0x10, 0x20, 0x01)
        final_pos = unpack_int3(resp[5:8])
        self.assertAlmostEqual(final_pos, target, places=5)

    def test_03_combined_goto(self):
        """Fast GOTO followed by Slow GOTO (simulating high-precision alignment)."""
        # 1. Fast GOTO to 10deg
        target_fast = 10.0 / 360.0
        print(
            f"\n   Testing Combined GOTO: Stage 1 (Fast to {target_fast * 360:.1f}deg)..."
        )
        self.exchange(0x10, 0x20, 0x02, pack_int3(target_fast))
        self.assertTrue(self.wait_for_goto(0x10))

        # 2. Slow GOTO to 10.5deg
        target_slow = 10.5 / 360.0
        print(
            f"   Testing Combined GOTO: Stage 2 (Slow to {target_slow * 360:.1f}deg)..."
        )
        self.exchange(0x10, 0x20, 0x17, pack_int3(target_slow))

        success = self.wait_for_goto(0x10)
        self.assertTrue(success, "Combined GOTO Stage 2 failed to complete")

        resp = self.exchange(0x10, 0x20, 0x01)
        final_pos = unpack_int3(resp[5:8])
        self.assertAlmostEqual(final_pos, target_slow, places=5)


if __name__ == "__main__":
    unittest.main()
