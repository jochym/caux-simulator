#!/usr/bin/env python3
"""
Verification Test for Time and Location Synchronization via WiFi.
Sends commands 0x30 and 0x31 to the WiFi device (0xB5) and verifies configuration updates.
"""

import socket
import subprocess
import time
import sys
import os
import struct
import pytest
from datetime import datetime, timezone, timedelta


def send_aux_command(sock, dest, src, cmd, data=b""):
    """Send an AUX command and wait for response."""
    length = len(data) + 3
    header = bytes([length, src, dest, cmd])
    checksum = (~sum(header + data) + 1) & 0xFF
    packet = b";" + header + data + bytes([checksum])
    sock.send(packet)
    time.sleep(0.1)
    return sock.recv(1024)


def test_time_location_sync():
    """Test if sending 0x30 and 0x31 to 0xB5 updates simulator state."""
    log_file = "/tmp/sync_test.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    # Start simulator in headless mode
    sim_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "caux_simulator.nse_simulator",
            "--text",
            "--port",
            "2001",
            "--log-file",
            log_file,
        ],
        cwd=os.getcwd(),
        env={**os.environ, "PYTHONPATH": os.path.join(os.getcwd(), "src")},
    )

    time.sleep(1)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(("127.0.0.1", 2001))

        # 1. Test Location Sync (0x31)
        # Target: 52.2297N, 21.0122E (Warsaw)
        lat, lon = 52.2297, 21.0122
        data_loc = struct.pack("<ff", lat, lon)
        print(f"Sending Location Sync: {lat}, {lon}")
        send_aux_command(sock, 0xB5, 0x20, 0x31, data_loc)

        # 2. Test Time Sync (0x30)
        # Target: 2026-02-01 12:30:45 UTC+1 (Offset=1, DST=0)
        # Format: [SS, MM, HH, DD, MM, YY, Offset, DST]
        target_time = [45, 30, 12, 1, 2, 26, 1, 0]
        print(f"Sending Time Sync: {target_time}")
        send_aux_command(sock, 0xB5, 0x20, 0x30, bytes(target_time))

        sock.close()
        time.sleep(0.5)

        # Verify logs
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()

            assert "WiFi received Location: Lat=52.2297, Lon=21.0122" in log_content
            assert "WiFi received Time:" in log_content
            assert "System clock offset:" in log_content
            print("SUCCESS: Sync commands received and processed correctly.")
        else:
            pytest.fail("Log file not found")

    finally:
        sim_proc.terminate()
        sim_proc.wait()


if __name__ == "__main__":
    test_time_location_sync()
