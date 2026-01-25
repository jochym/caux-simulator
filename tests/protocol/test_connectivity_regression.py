#!/usr/bin/env python3
"""
NexStar AUX Simulator: Protocol Compliance Regression Suite
Generated from session logs (SkySafari 7, SkyPortal, Aux Scanner)
"""

import asyncio
import socket
import struct
import unittest
import subprocess
import sys
import time
import os

from caux_simulator.bus.utils import encode_packet, make_checksum

# --- Regression Tests ---


class TestSkySafari7Handshake(unittest.TestCase):
    """Verifies the exact command sequence seen in ss7.log."""

    @classmethod
    def setUpClass(cls):
        # Start simulator in a background process
        cls.sim_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "caux_simulator.nse_simulator",
                "--text",
                "--log-categories",
                "31",
                "--log-file",
                "test_debug.log",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/jochym/Projects/indi/caux-simulator",
            env={**os.environ, "PYTHONPATH": "src"},
        )

        time.sleep(2)  # Wait for startup

    @classmethod
    def tearDownClass(cls):
        cls.sim_proc.terminate()
        cls.sim_proc.wait()

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 2000))
        self.sock.settimeout(1.0)

    def tearDown(self):
        self.sock.close()

    def exchange(self, dest, src, cmd, data=b""):
        pkt = encode_packet(src, dest, cmd, data)
        self.sock.send(pkt)
        time.sleep(0.1)
        resp = self.sock.recv(4096)
        # Verify echo is present
        self.assertTrue(resp.startswith(pkt), f"Missing echo for cmd {hex(cmd)}")
        # Response starts after the echo (len(pkt))
        # The response packet structure: 3B LEN SRC DST CMD DATA... CHK
        # The payload (DATA) starts at index 5 of the response packet
        return resp[len(pkt) :]

    def test_01_wifi_handshake(self):
        """WiFi module (0xB5) initial handshake sequence."""
        # 1. GET_VER - Should return version 0.0.256 (00 00 01 00)
        resp = self.exchange(0xB5, 0x20, 0xFE)
        self.assertEqual(
            resp[5:9], bytes([0, 0, 1, 0]), "WiFi Module should return version 0.0.256"
        )

        # 2. Command 0x49 (Status/Ping)
        resp = self.exchange(0xB5, 0x20, 0x49)
        self.assertEqual(resp[5], 0x00, "WiFi 0x49 should return 0x00")

        # 3. Command 0x32 (Config)
        resp = self.exchange(0xB5, 0x20, 0x32, bytes.fromhex("3106739d"))
        self.assertEqual(resp[5], 0x01, "WiFi 0x32 should return 0x01 (Success)")

        # 4. Command 0x31 (Location)
        resp = self.exchange(0xB5, 0x20, 0x31, bytes.fromhex("4248b72d419e46aa"))
        self.assertEqual(resp[5], 0x01, "WiFi 0x31 should return 0x01 (Success)")

    def test_02_motor_handshake(self):
        """Motor controller (0x10) basic identification."""
        # 1. GET_VER
        resp = self.exchange(0x10, 0x20, 0xFE)
        self.assertEqual(resp[5:9], bytes([7, 19, 20, 10]), "Incorrect AZM MC version")

        # 2. GET_MODEL
        resp = self.exchange(0x10, 0x20, 0x05)
        self.assertEqual(
            resp[5:7],
            bytes.fromhex("1687"),
            "Incorrect Model ID (should be Evolution)",
        )

    def test_03_backlash_protocol(self):
        """Verifies GET/SET backlash formatting."""
        # 1. GET_POS_BACKLASH (AZM)
        resp = self.exchange(0x10, 0x20, 0x40)
        self.assertEqual(
            len(resp),
            7,
            "GET_POS_BACKLASH should return 1 byte payload (7 bytes total)",
        )

        # 2. GET_POS_BACKLASH (ALT)
        resp = self.exchange(0x11, 0x20, 0x40)
        self.assertEqual(
            len(resp), 7, "GET_POS_BACKLASH (ALT) should return 1 byte payload"
        )

    def test_04_battery_protocol(self):
        """Verifies Battery (0xB6) multi-byte data structures."""
        # 1. GET_VOLTAGE_STATUS (SS sends 0x10)
        resp = self.exchange(0xB6, 0x20, 0x10)
        self.assertEqual(
            len(resp),
            12,
            "Battery status must be exactly 6 bytes data payload (12 bytes total)",
        )

    def test_05_accessory_silence(self):
        """Verifies that dropped devices (Focuser, StarSense, HC) are completely silent."""

        def check_silence(dest):
            pkt = encode_packet(0x20, dest, 0xFE)
            self.sock.send(pkt)
            time.sleep(0.1)
            try:
                self.sock.settimeout(0.5)
                resp = self.sock.recv(1024)
                self.fail(
                    f"Device {hex(dest)} should be silent but returned: {resp.hex()}"
                )
            except socket.timeout:
                pass  # Success
            finally:
                self.sock.settimeout(1.0)

        # 1. Focuser (0x12)
        check_silence(0x12)

        # 2. StarSense (0xB4)
        check_silence(0xB4)

        # 3. Hand Controller (0x04)
        check_silence(0x04)


if __name__ == "__main__":
    unittest.main()
